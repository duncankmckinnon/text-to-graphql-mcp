#!/usr/bin/env python3
"""
Exception classes for the Text-to-GraphQL MCP Server.

This module defines a comprehensive hierarchy of custom exceptions tailored to
MCP-specific and GraphQL error scenarios, enabling precise error categorization,
context preservation, and standardized error responses.
"""

import json
import time
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ErrorSeverity(Enum):
    """Error severity levels for categorizing the impact of errors."""
    LOW = "low"           # Non-critical errors that don't affect main functionality
    MEDIUM = "medium"     # Errors that affect some functionality but allow degraded operation
    HIGH = "high"         # Critical errors that significantly impact functionality
    CRITICAL = "critical" # System-level errors that prevent operation


class ErrorCategory(Enum):
    """Categories of errors for better organization and handling."""
    VALIDATION = "validation"         # Input validation and parameter errors
    AUTHENTICATION = "authentication" # Authentication and authorization errors
    EXTERNAL_API = "external_api"     # External service communication errors
    SCHEMA = "schema"                 # GraphQL schema related errors
    QUERY = "query"                   # GraphQL query construction/validation errors
    EXECUTION = "execution"           # Query execution errors
    CONFIGURATION = "configuration"   # Configuration and setup errors
    NETWORK = "network"               # Network and connectivity errors
    INTERNAL = "internal"             # Internal system errors
    RATE_LIMIT = "rate_limit"         # Rate limiting and quota errors


class BaseMCPException(Exception):
    """
    Base exception class for all MCP server errors.
    
    Provides structured error information including error codes, severity,
    context data, and user-friendly messages for both debugging and client responses.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        user_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.user_message = user_message or self._generate_user_message()
        self.details = details or {}
        self.cause = cause
        self.timestamp = time.time()
        self.traceback_str = traceback.format_exc() if cause else None
    
    def _generate_user_message(self) -> str:
        """Generate a user-friendly error message based on the error category."""
        category_messages = {
            ErrorCategory.VALIDATION: "Invalid input provided. Please check your request parameters.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please verify your credentials.",
            ErrorCategory.EXTERNAL_API: "External service temporarily unavailable. Please try again later.",
            ErrorCategory.SCHEMA: "GraphQL schema error. The requested operation is not supported.",
            ErrorCategory.QUERY: "Invalid GraphQL query. Please check your query syntax.",
            ErrorCategory.EXECUTION: "Query execution failed. Please review your query parameters.",
            ErrorCategory.CONFIGURATION: "Service configuration error. Please contact support.",
            ErrorCategory.NETWORK: "Network connectivity issue. Please check your connection.",
            ErrorCategory.INTERNAL: "Internal server error occurred. Please try again later.",
            ErrorCategory.RATE_LIMIT: "Rate limit exceeded. Please wait before making more requests."
        }
        return category_messages.get(self.category, "An error occurred while processing your request.")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        return {
            "error": True,
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "context": self.context,
            "details": self.details,
            "cause": str(self.cause) if self.cause else None
        }
    
    def to_json(self) -> str:
        """Convert exception to JSON string for MCP responses."""
        return json.dumps(self.to_dict(), indent=2, default=str)
    
    def to_mcp_error(self) -> Dict[str, Any]:
        """Convert to MCP protocol error format."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.user_message,
                "data": {
                    "category": self.category.value,
                    "severity": self.severity.value,
                    "details": self.details,
                    "context": self.context,
                    "timestamp": self.timestamp
                }
            }
        }
    
    def to_graphql_error(self) -> Dict[str, Any]:
        """Convert to GraphQL error format."""
        return {
            "message": self.user_message,
            "extensions": {
                "code": self.error_code,
                "category": self.category.value,
                "severity": self.severity.value,
                "timestamp": self.timestamp,
                "context": self.context,
                "details": self.details
            }
        }


class ValidationError(BaseMCPException):
    """Exception for input validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        expected_type: Optional[str] = None,
        **kwargs
    ):
        context = {
            "field": field,
            "value": str(value) if value is not None else None,
            "expected_type": expected_type
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class AuthenticationError(BaseMCPException):
    """Exception for authentication and authorization errors."""
    
    def __init__(self, message: str, auth_type: Optional[str] = None, **kwargs):
        context = {"auth_type": auth_type}
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class ExternalAPIError(BaseMCPException):
    """Exception for external API communication errors."""
    
    def __init__(
        self,
        message: str,
        api_endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ):
        context = {
            "api_endpoint": api_endpoint,
            "status_code": status_code,
            "response_body": response_body
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="EXTERNAL_API_ERROR",
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class GraphQLSchemaError(BaseMCPException):
    """Exception for GraphQL schema related errors."""
    
    def __init__(
        self,
        message: str,
        schema_source: Optional[str] = None,
        invalid_type: Optional[str] = None,
        **kwargs
    ):
        context = {
            "schema_source": schema_source,
            "invalid_type": invalid_type
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="SCHEMA_ERROR",
            category=ErrorCategory.SCHEMA,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class GraphQLQueryError(BaseMCPException):
    """Exception for GraphQL query construction and validation errors."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        query_type: Optional[str] = None,
        syntax_error: Optional[str] = None,
        **kwargs
    ):
        context = {
            "query": query,
            "query_type": query_type,
            "syntax_error": syntax_error
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="QUERY_ERROR",
            category=ErrorCategory.QUERY,
            severity=ErrorSeverity.LOW,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class GraphQLExecutionError(BaseMCPException):
    """Exception for GraphQL query execution errors."""
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        variables: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None,
        **kwargs
    ):
        context = {
            "query": query,
            "variables": variables,
            "execution_time": execution_time
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="EXECUTION_ERROR",
            category=ErrorCategory.EXECUTION,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class ConfigurationError(BaseMCPException):
    """Exception for configuration and setup errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        context = {
            "config_key": config_key,
            "config_file": config_file
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class NetworkError(BaseMCPException):
    """Exception for network and connectivity errors."""
    
    def __init__(
        self,
        message: str,
        endpoint: Optional[str] = None,
        timeout: Optional[float] = None,
        **kwargs
    ):
        context = {
            "endpoint": endpoint,
            "timeout": timeout
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="NETWORK_ERROR",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class RateLimitError(BaseMCPException):
    """Exception for rate limiting and quota errors."""
    
    def __init__(
        self,
        message: str,
        limit: Optional[int] = None,
        reset_time: Optional[float] = None,
        **kwargs
    ):
        context = {
            "limit": limit,
            "reset_time": reset_time
        }
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            category=ErrorCategory.RATE_LIMIT,
            severity=ErrorSeverity.LOW,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


class InternalError(BaseMCPException):
    """Exception for internal system errors."""
    
    def __init__(self, message: str, component: Optional[str] = None, **kwargs):
        context = {"component": component}
        context.update(kwargs.get("context", {}))
        
        super().__init__(
            message=message,
            error_code="INTERNAL_ERROR",
            category=ErrorCategory.INTERNAL,
            severity=ErrorSeverity.CRITICAL,
            context=context,
            **{k: v for k, v in kwargs.items() if k != "context"}
        )


# Convenience functions for error handling
def handle_exception(e: Exception, context: Optional[Dict[str, Any]] = None) -> BaseMCPException:
    """
    Convert a generic exception to an appropriate MCP exception.
    
    Args:
        e: The original exception
        context: Additional context information
        
    Returns:
        BaseMCPException: Appropriate MCP exception based on the original exception type
    """
    context = context or {}
    
    # Map common exception types to MCP exceptions
    if isinstance(e, ValueError):
        return ValidationError(
            message=str(e),
            context=context,
            cause=e
        )
    elif isinstance(e, ConnectionError):
        return NetworkError(
            message=f"Network connection failed: {str(e)}",
            context=context,
            cause=e
        )
    elif isinstance(e, TimeoutError):
        return NetworkError(
            message=f"Request timed out: {str(e)}",
            context=context,
            cause=e
        )
    elif isinstance(e, KeyError):
        return ConfigurationError(
            message=f"Missing configuration key: {str(e)}",
            config_key=str(e),
            context=context,
            cause=e
        )
    elif isinstance(e, PermissionError):
        return AuthenticationError(
            message=f"Permission denied: {str(e)}",
            context=context,
            cause=e
        )
    else:
        return InternalError(
            message=f"Unexpected error: {str(e)}",
            component="unknown",
            context=context,
            cause=e
        )


def format_error_response(error: BaseMCPException, format_type: str = "mcp") -> Dict[str, Any]:
    """
    Format an error for different response types.
    
    Args:
        error: The MCP exception to format
        format_type: The format type ("mcp", "graphql", or "json")
        
    Returns:
        Dict: Formatted error response
    """
    if format_type == "mcp":
        return error.to_mcp_error()
    elif format_type == "graphql":
        return error.to_graphql_error()
    else:
        return error.to_dict()


# Exception registry for error code lookup
EXCEPTION_REGISTRY = {
    "VALIDATION_ERROR": ValidationError,
    "AUTH_ERROR": AuthenticationError,
    "EXTERNAL_API_ERROR": ExternalAPIError,
    "SCHEMA_ERROR": GraphQLSchemaError,
    "QUERY_ERROR": GraphQLQueryError,
    "EXECUTION_ERROR": GraphQLExecutionError,
    "CONFIG_ERROR": ConfigurationError,
    "NETWORK_ERROR": NetworkError,
    "RATE_LIMIT_ERROR": RateLimitError,
    "INTERNAL_ERROR": InternalError
} 