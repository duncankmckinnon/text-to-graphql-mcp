#!/usr/bin/env python3
"""
Unit tests for the custom exception classes in the Text-to-GraphQL MCP Server.
"""

import json
import time
import pytest
from unittest.mock import Mock

from src.text_to_graphql_mcp.exceptions import (
    BaseMCPException,
    ValidationError,
    AuthenticationError,
    ExternalAPIError,
    GraphQLSchemaError,
    GraphQLQueryError,
    GraphQLExecutionError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    InternalError,
    ErrorSeverity,
    ErrorCategory,
    handle_exception,
    format_error_response,
    EXCEPTION_REGISTRY
)


class TestBaseMCPException:
    """Test the base MCP exception class."""
    
    def test_basic_initialization(self):
        """Test basic exception initialization."""
        error = BaseMCPException(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.INTERNAL
        )
        
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.category == ErrorCategory.INTERNAL
        assert error.severity == ErrorSeverity.MEDIUM  # default
        assert isinstance(error.timestamp, float)
        assert "Internal server error occurred" in error.user_message
    
    def test_full_initialization(self):
        """Test exception initialization with all parameters."""
        context = {"test_key": "test_value"}
        details = {"error_detail": "detailed info"}
        
        error = BaseMCPException(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            context=context,
            user_message="Custom user message",
            details=details
        )
        
        assert error.message == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == context
        assert error.user_message == "Custom user message"
        assert error.details == details
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        error = BaseMCPException(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW
        )
        
        result = error.to_dict()
        
        assert result["error"] is True
        assert result["error_code"] == "TEST_ERROR"
        assert result["message"] == "Test error"
        assert result["category"] == "validation"
        assert result["severity"] == "low"
        assert "timestamp" in result
    
    def test_to_json(self):
        """Test conversion to JSON string."""
        error = BaseMCPException(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION
        )
        
        result = error.to_json()
        parsed = json.loads(result)
        
        assert parsed["error"] is True
        assert parsed["error_code"] == "TEST_ERROR"
        assert parsed["message"] == "Test error"
    
    def test_to_mcp_error(self):
        """Test conversion to MCP protocol format."""
        error = BaseMCPException(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.VALIDATION,
            user_message="User friendly message"
        )
        
        result = error.to_mcp_error()
        
        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "User friendly message"
        assert "data" in result["error"]
        assert result["error"]["data"]["category"] == "validation"
    
    def test_to_graphql_error(self):
        """Test conversion to GraphQL error format."""
        error = BaseMCPException(
            message="Test error",
            error_code="TEST_ERROR",
            category=ErrorCategory.QUERY,
            user_message="GraphQL error message"
        )
        
        result = error.to_graphql_error()
        
        assert result["message"] == "GraphQL error message"
        assert "extensions" in result
        assert result["extensions"]["code"] == "TEST_ERROR"
        assert result["extensions"]["category"] == "query"


class TestSpecificExceptions:
    """Test specific exception types."""
    
    def test_validation_error(self):
        """Test ValidationError with field information."""
        error = ValidationError(
            message="Invalid field value",
            field="username",
            value="test@",
            expected_type="string"
        )
        
        assert error.error_code == "VALIDATION_ERROR"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.context["field"] == "username"
        assert error.context["value"] == "test@"
        assert error.context["expected_type"] == "string"
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError(
            message="Invalid credentials",
            auth_type="bearer_token"
        )
        
        assert error.error_code == "AUTH_ERROR"
        assert error.category == ErrorCategory.AUTHENTICATION
        assert error.severity == ErrorSeverity.HIGH
        assert error.context["auth_type"] == "bearer_token"
    
    def test_external_api_error(self):
        """Test ExternalAPIError with API details."""
        error = ExternalAPIError(
            message="API request failed",
            api_endpoint="https://api.example.com/graphql",
            status_code=500,
            response_body="Internal Server Error"
        )
        
        assert error.error_code == "EXTERNAL_API_ERROR"
        assert error.category == ErrorCategory.EXTERNAL_API
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.context["api_endpoint"] == "https://api.example.com/graphql"
        assert error.context["status_code"] == 500
        assert error.context["response_body"] == "Internal Server Error"
    
    def test_graphql_schema_error(self):
        """Test GraphQLSchemaError."""
        error = GraphQLSchemaError(
            message="Invalid schema type",
            schema_source="introspection",
            invalid_type="UnknownType"
        )
        
        assert error.error_code == "SCHEMA_ERROR"
        assert error.category == ErrorCategory.SCHEMA
        assert error.context["schema_source"] == "introspection"
        assert error.context["invalid_type"] == "UnknownType"
    
    def test_graphql_query_error(self):
        """Test GraphQLQueryError."""
        error = GraphQLQueryError(
            message="Query syntax error",
            query="query { user { invalid } }",
            query_type="query",
            syntax_error="Field 'invalid' not found"
        )
        
        assert error.error_code == "QUERY_ERROR"
        assert error.category == ErrorCategory.QUERY
        assert error.context["query"] == "query { user { invalid } }"
        assert error.context["syntax_error"] == "Field 'invalid' not found"
    
    def test_graphql_execution_error(self):
        """Test GraphQLExecutionError."""
        error = GraphQLExecutionError(
            message="Query execution failed",
            query="query { users }",
            variables={"limit": 10},
            execution_time=1.5
        )
        
        assert error.error_code == "EXECUTION_ERROR"
        assert error.category == ErrorCategory.EXECUTION
        assert error.context["query"] == "query { users }"
        assert error.context["variables"] == {"limit": 10}
        assert error.context["execution_time"] == 1.5
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        reset_time = time.time() + 3600
        error = RateLimitError(
            message="Rate limit exceeded",
            limit=100,
            reset_time=reset_time
        )
        
        assert error.error_code == "RATE_LIMIT_ERROR"
        assert error.category == ErrorCategory.RATE_LIMIT
        assert error.context["limit"] == 100
        assert error.context["reset_time"] == reset_time


class TestErrorHandling:
    """Test error handling utilities."""
    
    def test_handle_value_error(self):
        """Test handling of ValueError."""
        original_error = ValueError("Invalid value")
        handled = handle_exception(original_error, {"source": "test"})
        
        assert isinstance(handled, ValidationError)
        assert handled.message == "Invalid value"
        assert handled.context["source"] == "test"
        assert handled.cause == original_error
    
    def test_handle_connection_error(self):
        """Test handling of ConnectionError."""
        original_error = ConnectionError("Connection failed")
        handled = handle_exception(original_error)
        
        assert isinstance(handled, NetworkError)
        assert "Network connection failed" in handled.message
        assert handled.cause == original_error
    
    def test_handle_timeout_error(self):
        """Test handling of TimeoutError."""
        original_error = TimeoutError("Request timed out")
        handled = handle_exception(original_error)
        
        assert isinstance(handled, NetworkError)
        assert "Request timed out" in handled.message
    
    def test_handle_key_error(self):
        """Test handling of KeyError."""
        original_error = KeyError("missing_key")
        handled = handle_exception(original_error)
        
        assert isinstance(handled, ConfigurationError)
        assert "Missing configuration key" in handled.message
        assert handled.context["config_key"] == "'missing_key'"
    
    def test_handle_permission_error(self):
        """Test handling of PermissionError."""
        original_error = PermissionError("Access denied")
        handled = handle_exception(original_error)
        
        assert isinstance(handled, AuthenticationError)
        assert "Permission denied" in handled.message
    
    def test_handle_unknown_error(self):
        """Test handling of unknown exception types."""
        original_error = RuntimeError("Unknown error")
        handled = handle_exception(original_error)
        
        assert isinstance(handled, InternalError)
        assert "Unexpected error" in handled.message
        assert handled.context["component"] == "unknown"


class TestErrorFormatting:
    """Test error formatting utilities."""
    
    def test_format_mcp_response(self):
        """Test formatting error for MCP response."""
        error = ValidationError(
            message="Test validation error",
            field="test_field"
        )
        
        result = format_error_response(error, "mcp")
        
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "data" in result["error"]
    
    def test_format_graphql_response(self):
        """Test formatting error for GraphQL response."""
        error = GraphQLQueryError(
            message="Test query error",
            query="invalid query"
        )
        
        result = format_error_response(error, "graphql")
        
        assert "message" in result
        assert "extensions" in result
        assert result["extensions"]["code"] == "QUERY_ERROR"
    
    def test_format_json_response(self):
        """Test formatting error for generic JSON response."""
        error = InternalError(
            message="Test internal error",
            component="test_component"
        )
        
        result = format_error_response(error, "json")
        
        assert result["error"] is True
        assert result["error_code"] == "INTERNAL_ERROR"
        assert result["category"] == "internal"


class TestExceptionRegistry:
    """Test the exception registry."""
    
    def test_registry_completeness(self):
        """Test that all exception types are in the registry."""
        expected_codes = {
            "VALIDATION_ERROR",
            "AUTH_ERROR",
            "EXTERNAL_API_ERROR",
            "SCHEMA_ERROR",
            "QUERY_ERROR",
            "EXECUTION_ERROR",
            "CONFIG_ERROR",
            "NETWORK_ERROR",
            "RATE_LIMIT_ERROR",
            "INTERNAL_ERROR"
        }
        
        assert set(EXCEPTION_REGISTRY.keys()) == expected_codes
    
    def test_registry_mapping(self):
        """Test that registry maps correctly to exception classes."""
        assert EXCEPTION_REGISTRY["VALIDATION_ERROR"] == ValidationError
        assert EXCEPTION_REGISTRY["AUTH_ERROR"] == AuthenticationError
        assert EXCEPTION_REGISTRY["QUERY_ERROR"] == GraphQLQueryError


if __name__ == "__main__":
    pytest.main([__file__]) 