#!/usr/bin/env python3
"""
Error handling decorators and validation utilities for the Text-to-GraphQL MCP Server.

This module provides decorators and utilities for input validation and standardized
error response formatting, integrating with the custom exception hierarchy.
"""

import json
import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Type, Union

try:
    from .exceptions import (
        BaseMCPException,
        ValidationError,
        InternalError,
        handle_exception,
        format_error_response
    )
    from .logger import logger
except ImportError:
    # Handle imports when running as main module
    from exceptions import (
        BaseMCPException,
        ValidationError,
        InternalError,
        handle_exception,
        format_error_response
    )
    from logger import logger


class ParameterValidator:
    """Parameter validation utilities for MCP tools."""
    
    @staticmethod
    def validate_required(value: Any, name: str) -> Any:
        """Validate that a required parameter is provided and not empty."""
        if value is None:
            raise ValidationError(
                message=f"Required parameter '{name}' is missing",
                field=name,
                value=None,
                expected_type="non-null"
            )
        
        if isinstance(value, str) and not value.strip():
            raise ValidationError(
                message=f"Required parameter '{name}' cannot be empty",
                field=name,
                value=value,
                expected_type="non-empty string"
            )
        
        return value
    
    @staticmethod
    def validate_string(value: Any, name: str, min_length: int = 0, max_length: Optional[int] = None, required: bool = True) -> Optional[str]:
        """Validate string parameters."""
        if value is None:
            if required:
                raise ValidationError(
                    message=f"Required string parameter '{name}' is missing",
                    field=name,
                    value=None,
                    expected_type="string"
                )
            return None
        
        if not isinstance(value, str):
            raise ValidationError(
                message=f"Parameter '{name}' must be a string",
                field=name,
                value=str(value),
                expected_type="string"
            )
        
        if len(value) < min_length:
            raise ValidationError(
                message=f"Parameter '{name}' must be at least {min_length} characters long",
                field=name,
                value=value,
                expected_type=f"string with min length {min_length}"
            )
        
        if max_length and len(value) > max_length:
            raise ValidationError(
                message=f"Parameter '{name}' must be at most {max_length} characters long",
                field=name,
                value=value[:50] + "..." if len(value) > 50 else value,
                expected_type=f"string with max length {max_length}"
            )
        
        return value
    
    @staticmethod
    def validate_dict(value: Any, name: str, required: bool = True) -> Optional[Dict[str, Any]]:
        """Validate dictionary parameters."""
        if value is None:
            if required:
                raise ValidationError(
                    message=f"Required dictionary parameter '{name}' is missing",
                    field=name,
                    value=None,
                    expected_type="dictionary"
                )
            return None
        
        if not isinstance(value, dict):
            raise ValidationError(
                message=f"Parameter '{name}' must be a dictionary",
                field=name,
                value=str(value),
                expected_type="dictionary"
            )
        
        return value
    
    @staticmethod
    def validate_graphql_query(query: str, name: str = "graphql_query") -> str:
        """Validate GraphQL query format."""
        ParameterValidator.validate_string(query, name, min_length=1, required=True)
        
        # Basic GraphQL syntax validation
        query = query.strip()
        
        # Check for basic GraphQL structure
        if not (query.startswith('query') or query.startswith('mutation') or 
                query.startswith('subscription') or query.startswith('{')):
            raise ValidationError(
                message=f"Invalid GraphQL query format in '{name}'",
                field=name,
                value=query[:100] + "..." if len(query) > 100 else query,
                expected_type="valid GraphQL query (query/mutation/subscription or anonymous)",
                details={"syntax_hint": "Query should start with 'query', 'mutation', 'subscription', or '{'"}
            )
        
        # Check for balanced braces
        open_braces = query.count('{')
        close_braces = query.count('}')
        if open_braces != close_braces:
            raise ValidationError(
                message=f"Unbalanced braces in GraphQL query '{name}'",
                field=name,
                value=query[:100] + "..." if len(query) > 100 else query,
                expected_type="valid GraphQL query with balanced braces",
                details={"open_braces": open_braces, "close_braces": close_braces}
            )
        
        return query
    
    @staticmethod
    def validate_history_id(history_id: Any, name: str = "history_id") -> Optional[str]:
        """Validate history ID format."""
        if history_id is None:
            return None
        
        if not isinstance(history_id, str):
            raise ValidationError(
                message=f"Parameter '{name}' must be a string",
                field=name,
                value=str(history_id),
                expected_type="string"
            )
        
        # Basic format validation - should be alphanumeric with possible hyphens/underscores
        if not history_id.replace('-', '').replace('_', '').isalnum():
            raise ValidationError(
                message=f"Invalid history ID format in '{name}'",
                field=name,
                value=history_id,
                expected_type="alphanumeric string with optional hyphens/underscores"
            )
        
        return history_id


def mcp_error_handler(func: Callable) -> Callable:
    """
    Decorator to handle exceptions and return standardized MCP error responses.
    
    This decorator catches all exceptions and converts them to standardized JSON
    error responses using the custom exception hierarchy.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> str:
        try:
            # Call the original function
            result = await func(*args, **kwargs)
            return result
            
        except BaseMCPException as e:
            # Our custom exceptions are already properly formatted
            logger.error(f"MCP error in {func.__name__}: {e.error_code}", extra={
                "function": func.__name__,
                "error_code": e.error_code,
                "category": e.category.value,
                "severity": e.severity.value,
                "context": e.context
            })
            return e.to_json()
            
        except Exception as e:
            # Convert generic exceptions to our custom exception format
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True, extra={
                "function": func.__name__,
                "error_type": type(e).__name__
            })
            
            # Create context from function call
            context = {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()) if kwargs else []
            }
            
            mcp_exception = handle_exception(e, context)
            return mcp_exception.to_json()
    
    return wrapper


def validate_mcp_parameters(**validation_rules) -> Callable:
    """
    Decorator to validate MCP tool parameters before execution.
    
    Args:
        **validation_rules: Dictionary of parameter validation rules
        
    Example:
        @validate_mcp_parameters(
            query={"type": "string", "required": True, "min_length": 1},
            history_id={"type": "string", "required": False}
        )
        async def my_tool(query: str, history_id: Optional[str] = None):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Get function signature to map positional args to parameter names
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Validate each parameter according to its rules
            for param_name, rules in validation_rules.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    
                    # Apply validation based on rules
                    param_type = rules.get("type", "any")
                    required = rules.get("required", False)
                    
                    try:
                        if param_type == "string":
                            min_length = rules.get("min_length", 0)
                            max_length = rules.get("max_length")
                            validated_value = ParameterValidator.validate_string(
                                value, param_name, min_length, max_length, required
                            )
                        elif param_type == "dict":
                            validated_value = ParameterValidator.validate_dict(value, param_name, required)
                        elif param_type == "graphql_query":
                            validated_value = ParameterValidator.validate_graphql_query(value, param_name)
                        elif param_type == "history_id":
                            validated_value = ParameterValidator.validate_history_id(value, param_name)
                        elif required:
                            validated_value = ParameterValidator.validate_required(value, param_name)
                        else:
                            validated_value = value
                        
                        # Update the bound arguments with validated value
                        bound_args.arguments[param_name] = validated_value
                        
                    except ValidationError:
                        # Re-raise validation errors as-is
                        raise
                    except Exception as e:
                        # Convert other validation errors
                        raise ValidationError(
                            message=f"Validation failed for parameter '{param_name}': {str(e)}",
                            field=param_name,
                            value=str(value) if value is not None else None,
                            cause=e
                        )
            
            # Call the function with validated parameters
            return await func(*bound_args.args, **bound_args.kwargs)
        
        return wrapper
    return decorator


def log_mcp_call(func: Callable) -> Callable:
    """
    Decorator to log MCP tool calls for debugging and monitoring.
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Log the function call
        logger.info(f"MCP tool called: {func.__name__}", extra={
            "tool": func.__name__,
            "args_count": len(args),
            "has_kwargs": bool(kwargs)
        })
        
        # Get parameter names for logging (without sensitive values)
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        # Log non-sensitive parameter info
        param_info = {}
        for param_name, value in bound_args.arguments.items():
            if param_name in ["query", "natural_language_query"]:
                # Log query length and first few words
                if isinstance(value, str):
                    words = value.split()[:3]
                    param_info[param_name] = {
                        "length": len(value),
                        "preview": " ".join(words) + ("..." if len(words) >= 3 else "")
                    }
            elif param_name in ["graphql_query"]:
                # Log GraphQL query info
                if isinstance(value, str):
                    query_type = "unknown"
                    if value.strip().startswith("query"):
                        query_type = "query"
                    elif value.strip().startswith("mutation"):
                        query_type = "mutation"
                    elif value.strip().startswith("subscription"):
                        query_type = "subscription"
                    elif value.strip().startswith("{"):
                        query_type = "anonymous"
                    
                    param_info[param_name] = {
                        "length": len(value),
                        "type": query_type
                    }
            elif param_name == "variables":
                # Log variable count and keys
                if isinstance(value, dict):
                    param_info[param_name] = {
                        "count": len(value),
                        "keys": list(value.keys())
                    }
            else:
                # For other parameters, log basic info
                param_info[param_name] = {
                    "type": type(value).__name__,
                    "is_none": value is None
                }
        
        logger.debug(f"MCP tool parameters: {func.__name__}", extra={
            "tool": func.__name__,
            "parameters": param_info
        })
        
        # Execute the function
        try:
            result = await func(*args, **kwargs)
            
            # Log successful completion
            logger.info(f"MCP tool completed: {func.__name__}", extra={
                "tool": func.__name__,
                "success": True
            })
            
            return result
            
        except Exception as e:
            # Log the error (error details will be logged by error handler)
            logger.error(f"MCP tool failed: {func.__name__}", extra={
                "tool": func.__name__,
                "success": False,
                "error_type": type(e).__name__
            })
            raise
    
    return wrapper


# Convenience decorator that combines common decorators
def validated(validation_rules: Optional[Dict[str, Dict[str, Any]]] = None) -> Callable:
    """
    Convenience decorator that combines parameter validation, error handling, and logging.
    
    Args:
        validation_rules: Optional parameter validation rules
        
    Example:
        @validated({
            "query": {"type": "string", "required": True, "min_length": 1},
            "history_id": {"type": "string", "required": False}
        })
        async def my_tool(query: str, history_id: Optional[str] = None):
            ...
    """
    def decorator(func: Callable) -> Callable:
        # Apply decorators in the right order
        decorated = func
        
        # Add validation if rules provided
        if validation_rules:
            decorated = validate_mcp_parameters(**validation_rules)(decorated)
        
        # Add logging
        decorated = log_mcp_call(decorated)
        
        # Add error handling (outermost decorator)
        decorated = mcp_error_handler(decorated)
        
        return decorated
    
    return decorator


# Backwards compatibility alias (deprecated)
mcp_tool = validated