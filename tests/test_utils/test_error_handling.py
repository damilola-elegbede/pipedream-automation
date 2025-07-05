"""
Tests for error handling utilities.

This module tests the error handling decorators, exception classes,
and utility functions for consistent error management.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from requests.exceptions import RequestException, HTTPError, Timeout

from src.utils.error_handling import (
    PipedreamError,
    AuthenticationError,
    ValidationError,
    APIError,
    RateLimitError,
    pipedream_error_handler,
    handle_api_response,
    safe_api_call,
    format_error_response,
)


class TestExceptionClasses:
    """Test custom exception classes."""

    def test_pipedream_error_initialization(self):
        """Test PipedreamError initialization."""
        error = PipedreamError("Test error", {"key": "value"})
        assert str(error) == "Test error"
        assert error.details == {"key": "value"}

    def test_pipedream_error_to_dict(self):
        """Test PipedreamError to_dict method."""
        error = PipedreamError("Test error", {"key": "value"})
        result = error.to_dict()
        assert result == {
            "error": "Test error",
            "type": "PipedreamError",
            "details": {"key": "value"}
        }

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError("Auth failed")
        result = error.to_dict()
        assert result["type"] == "AuthenticationError"
        assert result["error"] == "Auth failed"

    def test_validation_error(self):
        """Test ValidationError."""
        error = ValidationError("Invalid input", {"field": "email"})
        result = error.to_dict()
        assert result["type"] == "ValidationError"
        assert result["details"] == {"field": "email"}

    def test_api_error(self):
        """Test APIError."""
        error = APIError("API call failed", status_code=404)
        result = error.to_dict()
        assert result["type"] == "APIError"
        assert result["details"]["status_code"] == 404

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError(retry_after=60)
        result = error.to_dict()
        assert result["type"] == "RateLimitError"
        assert result["details"]["retry_after"] == 60


class TestPipedreamErrorHandler:
    """Test the pipedream_error_handler decorator."""

    def test_successful_handler(self):
        """Test decorator with successful function."""
        @pipedream_error_handler
        def handler(pd):
            return {"success": True}

        pd = Mock()
        result = handler(pd)
        assert result == {"success": True}

    def test_pipedream_error_handling(self):
        """Test decorator handling PipedreamError."""
        @pipedream_error_handler
        def handler(pd):
            raise PipedreamError("Custom error", {"detail": "info"})

        pd = Mock()
        result = handler(pd)
        assert "error" in result
        assert result["error"] == "An error occurred processing your request"

    def test_authentication_error_handling(self):
        """Test decorator handling AuthenticationError."""
        @pipedream_error_handler
        def handler(pd):
            raise AuthenticationError("Invalid token")

        pd = Mock()
        result = handler(pd)
        assert "error" in result
        assert "authentication" in result["error"].lower()

    def test_validation_error_handling(self):
        """Test decorator handling ValidationError."""
        @pipedream_error_handler
        def handler(pd):
            raise ValidationError("Invalid email")

        pd = Mock()
        result = handler(pd)
        assert "error" in result
        assert result["error"] == "Invalid email"

    def test_generic_exception_handling(self):
        """Test decorator handling generic exceptions."""
        @pipedream_error_handler
        def handler(pd):
            raise Exception("Unexpected error")

        pd = Mock()
        result = handler(pd)
        assert "error" in result
        assert result["error"] == "An error occurred processing your request"


class TestHandleApiResponse:
    """Test handle_api_response function."""

    def test_successful_response(self):
        """Test handling successful API response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"data": "value"}
        
        result = handle_api_response(response)
        assert result == {"data": "value"}

    def test_401_unauthorized(self):
        """Test handling 401 response."""
        response = Mock()
        response.status_code = 401
        response.raise_for_status.side_effect = HTTPError()
        
        with pytest.raises(AuthenticationError):
            handle_api_response(response)

    def test_403_forbidden(self):
        """Test handling 403 response."""
        response = Mock()
        response.status_code = 403
        response.raise_for_status.side_effect = HTTPError()
        
        with pytest.raises(AuthenticationError):
            handle_api_response(response)

    def test_404_not_found(self):
        """Test handling 404 response."""
        response = Mock()
        response.status_code = 404
        response.raise_for_status.side_effect = HTTPError()
        response.text = "Not found"
        
        with pytest.raises(APIError) as exc_info:
            handle_api_response(response)
        assert exc_info.value.status_code == 404

    def test_429_rate_limit(self):
        """Test handling 429 response."""
        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "60"}
        response.raise_for_status.side_effect = HTTPError()
        
        with pytest.raises(RateLimitError) as exc_info:
            handle_api_response(response)
        assert exc_info.value.details["retry_after"] == 60

    def test_500_server_error(self):
        """Test handling 500 response."""
        response = Mock()
        response.status_code = 500
        response.raise_for_status.side_effect = HTTPError()
        response.text = "Server error"
        
        with pytest.raises(APIError) as exc_info:
            handle_api_response(response)
        assert exc_info.value.status_code == 500


class TestSafeApiCall:
    """Test safe_api_call function."""

    @patch('time.sleep')
    def test_successful_call(self, mock_sleep):
        """Test successful API call."""
        mock_func = Mock(return_value="success")
        
        result = safe_api_call(mock_func, "arg1", kwarg="value")
        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg="value")

    @patch('time.sleep')
    def test_retry_on_timeout(self, mock_sleep):
        """Test retry logic on timeout."""
        mock_func = Mock(side_effect=[Timeout(), Timeout(), "success"])
        
        result = safe_api_call(mock_func, max_retries=3)
        assert result == "success"
        assert mock_func.call_count == 3

    @patch('time.sleep')
    def test_retry_on_connection_error(self, mock_sleep):
        """Test retry logic on connection error."""
        mock_func = Mock(side_effect=[RequestException("Connection error"), "success"])
        
        result = safe_api_call(mock_func, max_retries=2)
        assert result == "success"
        assert mock_func.call_count == 2

    @patch('time.sleep')
    def test_max_retries_exceeded(self, mock_sleep):
        """Test max retries exceeded."""
        mock_func = Mock(side_effect=Timeout())
        
        with pytest.raises(APIError) as exc_info:
            safe_api_call(mock_func, max_retries=3)
        assert mock_func.call_count == 3
        assert "Max retries" in str(exc_info.value)

    @patch('time.sleep')
    def test_non_retryable_error(self, mock_sleep):
        """Test non-retryable error."""
        mock_func = Mock(side_effect=ValueError("Invalid input"))
        
        with pytest.raises(ValueError):
            safe_api_call(mock_func)
        assert mock_func.call_count == 1


class TestFormatErrorResponse:
    """Test format_error_response function."""

    def test_format_pipedream_error(self):
        """Test formatting PipedreamError."""
        error = PipedreamError("Test error", {"key": "value"})
        result = format_error_response(error)
        assert result == {"error": "An error occurred processing your request"}

    def test_format_authentication_error(self):
        """Test formatting AuthenticationError."""
        error = AuthenticationError("Invalid token")
        result = format_error_response(error)
        assert "error" in result
        assert "authentication" in result["error"].lower()

    def test_format_validation_error(self):
        """Test formatting ValidationError."""
        error = ValidationError("Invalid email format")
        result = format_error_response(error)
        assert result == {"error": "Invalid email format"}

    def test_format_api_error(self):
        """Test formatting APIError."""
        error = APIError("API call failed", status_code=500)
        result = format_error_response(error)
        assert result == {"error": "An error occurred processing your request"}

    def test_format_rate_limit_error(self):
        """Test formatting RateLimitError."""
        error = RateLimitError(retry_after=60)
        result = format_error_response(error)
        assert "error" in result
        assert "rate limit" in result["error"].lower()

    def test_format_generic_exception(self):
        """Test formatting generic exception."""
        error = Exception("Unexpected error")
        result = format_error_response(error)
        assert result == {"error": "An error occurred processing your request"}

    def test_include_details_flag(self):
        """Test include_details parameter."""
        error = ValidationError("Invalid input", {"field": "email"})
        result = format_error_response(error, include_details=True)
        assert "details" in result
        assert result["details"] == {"field": "email"}