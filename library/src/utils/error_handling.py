"""
Error handling utilities for Pipedream automation.

This module provides decorators and functions for consistent error handling
across all integration modules.
"""

import functools
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from src.config.constants import (
    ERROR_API_REQUEST,
    ERROR_TIMEOUT,
    ERROR_RATE_LIMIT,
    ERROR_INVALID_RESPONSE
)


class PipedreamError(Exception):
    """Base exception for Pipedream-related errors."""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": self.message,
            "code": self.code,
            "details": self.details,
            "timestamp": datetime.utcnow().isoformat()
        }


class AuthenticationError(PipedreamError):
    """Raised when authentication fails."""
    def __init__(self, message: str, service: Optional[str] = None):
        super().__init__(message, code="AUTH_ERROR", details={"service": service})


class ValidationError(PipedreamError):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, code="VALIDATION_ERROR", details={"field": field})


class APIError(PipedreamError):
    """Raised when external API calls fail."""
    def __init__(self, message: str, status_code: Optional[int] = None, service: Optional[str] = None):
        super().__init__(
            message, 
            code="API_ERROR", 
            details={"status_code": status_code, "service": service}
        )


class RateLimitError(PipedreamError):
    """Raised when rate limits are exceeded."""
    def __init__(self, message: str = ERROR_RATE_LIMIT, retry_after: Optional[int] = None):
        super().__init__(
            message, 
            code="RATE_LIMIT", 
            details={"retry_after": retry_after}
        )


def pipedream_error_handler(func: Callable) -> Callable:
    """
    Decorator for consistent error handling in Pipedream handlers.
    
    This decorator catches all exceptions and returns them in a consistent
    format that Pipedream can process.
    """
    @functools.wraps(func)
    def wrapper(pd: Any) -> Dict[str, Any]:
        try:
            # Validate basic structure
            if not hasattr(pd, 'inputs') and not isinstance(pd, dict):
                return {"error": "Invalid Pipedream context", "code": "INVALID_CONTEXT"}
            
            # Run the actual function
            result = func(pd)
            
            # Ensure we return a dictionary
            if not isinstance(result, dict):
                return {"success": result}
            
            return result
            
        except PipedreamError as e:
            # Handle our custom exceptions
            logging.error(f"Pipedream error in {func.__name__}: {e.message}")
            return e.to_dict()
            
        except KeyError as e:
            # Handle missing keys
            error_msg = f"Missing required field: {str(e)}"
            logging.error(f"KeyError in {func.__name__}: {error_msg}")
            return {
                "error": error_msg,
                "code": "MISSING_FIELD",
                "field": str(e).strip("'\"")
            }
            
        except ValueError as e:
            # Handle value errors
            error_msg = f"Invalid value: {str(e)}"
            logging.error(f"ValueError in {func.__name__}: {error_msg}")
            return {
                "error": error_msg,
                "code": "INVALID_VALUE"
            }
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Internal error: {str(e)}"
            logging.error(f"Unexpected error in {func.__name__}: {error_msg}")
            logging.debug(traceback.format_exc())
            
            # Don't expose internal details in production
            return {
                "error": "An unexpected error occurred",
                "code": "INTERNAL_ERROR",
                "reference": str(e)[:100]  # Limited error detail
            }
    
    return wrapper


def handle_api_response(response: Any, service: str = "API") -> Dict[str, Any]:
    """
    Handle API response and raise appropriate errors.
    
    Args:
        response: HTTP response object
        service: Name of the service for error messages
        
    Returns:
        Parsed JSON response
        
    Raises:
        APIError: If the response indicates an error
        RateLimitError: If rate limited
    """
    import requests
    
    try:
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        status_code = response.status_code
        
        # Handle rate limiting
        if status_code == 429:
            retry_after = response.headers.get('Retry-After')
            raise RateLimitError(retry_after=int(retry_after) if retry_after else None)
        
        # Handle authentication errors
        if status_code in (401, 403):
            raise AuthenticationError(f"{service} authentication failed", service=service)
        
        # Handle other HTTP errors
        try:
            error_detail = response.json().get('message', str(e))
        except:
            error_detail = str(e)
        
        raise APIError(
            ERROR_API_REQUEST.format(error_detail),
            status_code=status_code,
            service=service
        )
    except requests.exceptions.Timeout:
        raise APIError(ERROR_TIMEOUT.format(30), service=service)
    except requests.exceptions.RequestException as e:
        raise APIError(ERROR_API_REQUEST.format(str(e)), service=service)
    except ValueError as e:
        raise APIError(ERROR_INVALID_RESPONSE.format(str(e)), service=service)


def safe_api_call(
    func: Callable,
    service: str = "API",
    max_retries: int = 3,
    retry_delay: int = 1
) -> Any:
    """
    Safely execute an API call with retry logic.
    
    Args:
        func: Function to execute
        service: Service name for error messages
        max_retries: Maximum number of retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        Result of the function call
        
    Raises:
        APIError: If all retries fail
    """
    import time
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            # Respect rate limit retry-after if provided
            wait_time = e.details.get('retry_after', retry_delay * (attempt + 1))
            if attempt < max_retries - 1:
                time.sleep(wait_time)
                continue
            last_error = e
        except APIError as e:
            # Retry on 5xx errors
            if e.details.get('status_code', 0) >= 500 and attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
                continue
            last_error = e
        except Exception as e:
            last_error = APIError(str(e), service=service)
    
    raise last_error


def format_error_response(error: Exception, include_trace: bool = False) -> Dict[str, Any]:
    """
    Format an exception into a standardized error response.
    
    Args:
        error: The exception to format
        include_trace: Whether to include stack trace
        
    Returns:
        Formatted error dictionary
    """
    if isinstance(error, PipedreamError):
        return error.to_dict()
    
    response = {
        "error": str(error),
        "type": type(error).__name__,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if include_trace:
        response["trace"] = traceback.format_exc()
    
    return response