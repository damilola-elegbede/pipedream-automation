"""
Retry Manager with exponential backoff and service-specific policies.

This module provides intelligent retry logic with exponential backoff, jitter,
and service-specific retry policies for improved reliability in API calls.
"""

import time
import random
import logging
from typing import Callable, Dict, Any, Optional, TypeVar, Union
from functools import wraps
from datetime import datetime, timedelta

# Type variable for generic function return types
T = TypeVar('T')

class RetryManager:
    """
    Manages retry logic with exponential backoff and service-specific policies.
    
    Features:
    - Exponential backoff with jitter to prevent thundering herd
    - Service-specific retry policies
    - Configurable max attempts and backoff parameters
    - Detailed retry metrics and logging
    """
    
    # Default retry configuration
    DEFAULT_CONFIG = {
        'max_attempts': 3,
        'base_delay': 1.0,  # seconds
        'max_delay': 60.0,  # seconds
        'exponential_base': 2.0,
        'jitter': True,
    }
    
    # Service-specific retry policies
    SERVICE_POLICIES = {
        'notion': {
            'max_attempts': 5,
            'base_delay': 2.0,
            'max_delay': 30.0,
            'retryable_status_codes': [429, 502, 503, 504],
            'retryable_exceptions': (ConnectionError, TimeoutError),
        },
        'gmail': {
            'max_attempts': 3,
            'base_delay': 1.0,
            'max_delay': 20.0,
            'retryable_status_codes': [429, 500, 502, 503],
            'retryable_exceptions': (ConnectionError, TimeoutError),
        },
        'openai': {
            'max_attempts': 4,
            'base_delay': 1.0,
            'max_delay': 60.0,
            'retryable_status_codes': [429, 500, 502, 503],
            'retryable_exceptions': (ConnectionError, TimeoutError),
            'respect_retry_after': True,
        },
        'shopify': {
            'max_attempts': 3,
            'base_delay': 1.0,
            'max_delay': 10.0,
            'retryable_status_codes': [429, 502, 503],
            'retryable_exceptions': (ConnectionError, TimeoutError),
        },
    }
    
    def __init__(self, service: Optional[str] = None, **custom_config):
        """
        Initialize RetryManager with service-specific or custom configuration.
        
        Args:
            service: Service name for specific retry policy (e.g., 'notion', 'gmail')
            **custom_config: Custom retry configuration to override defaults
        """
        # Start with default configuration
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Apply service-specific policy if provided
        if service and service in self.SERVICE_POLICIES:
            self.config.update(self.SERVICE_POLICIES[service])
        
        # Apply any custom configuration
        self.config.update(custom_config)
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Metrics tracking
        self.metrics = {
            'total_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'total_delay_time': 0.0,
        }
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number with exponential backoff.
        
        Args:
            attempt: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        # Calculate exponential backoff
        delay = min(
            self.config['base_delay'] * (self.config['exponential_base'] ** (attempt - 1)),
            self.config['max_delay']
        )
        
        # Add jitter if enabled
        if self.config.get('jitter', True):
            # Add random jitter between 0% and 25% of the delay
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay)  # Ensure minimum delay
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Args:
            exception: The exception that occurred
            attempt: Current attempt number
            
        Returns:
            True if should retry, False otherwise
        """
        # Check if we've exceeded max attempts
        if attempt >= self.config['max_attempts']:
            return False
        
        # Check retryable exceptions
        retryable_exceptions = self.config.get('retryable_exceptions', ())
        if isinstance(exception, retryable_exceptions):
            return True
        
        # Check for HTTP status codes in exception
        if hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
            status_code = exception.response.status_code
            retryable_codes = self.config.get('retryable_status_codes', [])
            return status_code in retryable_codes
        
        # Default: don't retry unknown exceptions
        return False
    
    def extract_retry_after(self, exception: Exception) -> Optional[float]:
        """
        Extract Retry-After header value from exception if available.
        
        Args:
            exception: The exception that occurred
            
        Returns:
            Retry-After value in seconds, or None if not available
        """
        if not self.config.get('respect_retry_after', False):
            return None
        
        if hasattr(exception, 'response') and hasattr(exception.response, 'headers'):
            retry_after = exception.response.headers.get('Retry-After')
            if retry_after:
                try:
                    # Try parsing as integer (seconds)
                    return float(retry_after)
                except ValueError:
                    # Try parsing as HTTP date
                    try:
                        retry_date = datetime.strptime(retry_after, '%a, %d %b %Y %H:%M:%S GMT')
                        return (retry_date - datetime.utcnow()).total_seconds()
                    except ValueError:
                        pass
        
        return None
    
    def with_retry(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to add retry logic to a function.
        
        Args:
            func: Function to wrap with retry logic
            
        Returns:
            Wrapped function with retry capability
        """
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            """Execute function with retry logic."""
            attempt = 0
            last_exception = None
            
            while attempt < self.config['max_attempts']:
                attempt += 1
                self.metrics['total_attempts'] += 1
                
                try:
                    # Log attempt
                    if attempt > 1:
                        self.logger.info(
                            f"Retry attempt {attempt}/{self.config['max_attempts']} "
                            f"for {func.__name__}"
                        )
                    
                    # Execute function
                    result = func(*args, **kwargs)
                    
                    # Success - update metrics if this was a retry
                    if attempt > 1:
                        self.metrics['successful_retries'] += 1
                        self.logger.info(
                            f"Retry successful for {func.__name__} "
                            f"after {attempt} attempts"
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if we should retry
                    if not self.should_retry(e, attempt):
                        self.logger.error(
                            f"Non-retryable error in {func.__name__}: {str(e)}"
                        )
                        raise
                    
                    # Check for Retry-After header
                    retry_after = self.extract_retry_after(e)
                    if retry_after:
                        delay = max(retry_after, 0.1)
                        self.logger.info(
                            f"Respecting Retry-After header: {delay:.1f}s"
                        )
                    else:
                        # Calculate exponential backoff delay
                        delay = self.calculate_delay(attempt)
                    
                    # Log retry decision
                    self.logger.warning(
                        f"Retryable error in {func.__name__} (attempt {attempt}): "
                        f"{type(e).__name__}: {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    # Update metrics
                    self.metrics['total_delay_time'] += delay
                    
                    # Wait before retry
                    time.sleep(delay)
            
            # All attempts exhausted
            # Only count as a failed retry if we actually tried to retry (more than 1 attempt)
            if attempt > 1:
                self.metrics['failed_retries'] += 1
            self.logger.error(
                f"All {attempt} retry attempts failed for {func.__name__}"
            )
            raise last_exception
        
        return wrapper
    
    def retry_with_context(
        self,
        func: Callable[..., T],
        context: Dict[str, Any],
        *args,
        **kwargs
    ) -> T:
        """
        Execute a function with retry logic and additional context.
        
        Args:
            func: Function to execute
            context: Additional context for logging/debugging
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func execution
        """
        # Add context to logger
        context_str = ', '.join(f"{k}={v}" for k, v in context.items())
        self.logger = logging.LoggerAdapter(
            self.logger,
            {'context': context_str}
        )
        
        # Execute with retry
        wrapped_func = self.with_retry(func)
        return wrapped_func(*args, **kwargs)
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get retry metrics for monitoring and debugging.
        
        Returns:
            Dictionary of retry metrics
        """
        metrics = self.metrics.copy()
        
        # Calculate derived metrics
        if metrics['total_attempts'] > 0:
            metrics['retry_rate'] = (
                metrics['successful_retries'] + metrics['failed_retries']
            ) / metrics['total_attempts']
            
            if metrics['successful_retries'] + metrics['failed_retries'] > 0:
                metrics['retry_success_rate'] = (
                    metrics['successful_retries'] / 
                    (metrics['successful_retries'] + metrics['failed_retries'])
                )
            else:
                metrics['retry_success_rate'] = 0.0
        else:
            metrics['retry_rate'] = 0.0
            metrics['retry_success_rate'] = 0.0
        
        metrics['average_delay'] = (
            metrics['total_delay_time'] / metrics['total_attempts']
            if metrics['total_attempts'] > 0 else 0.0
        )
        
        return metrics
    
    def reset_metrics(self):
        """Reset retry metrics."""
        self.metrics = {
            'total_attempts': 0,
            'successful_retries': 0,
            'failed_retries': 0,
            'total_delay_time': 0.0,
        }


# Convenience functions for common use cases
def with_retry(
    service: Optional[str] = None,
    max_attempts: Optional[int] = None,
    **kwargs
) -> Callable:
    """
    Decorator factory for adding retry logic to functions.
    
    Args:
        service: Service name for specific retry policy
        max_attempts: Override max retry attempts
        **kwargs: Additional configuration options
        
    Returns:
        Decorator function
        
    Example:
        @with_retry(service='notion', max_attempts=5)
        def fetch_notion_data():
            # API call that might fail
            pass
    """
    config = kwargs.copy()
    if max_attempts:
        config['max_attempts'] = max_attempts
    
    retry_manager = RetryManager(service=service, **config)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        return retry_manager.with_retry(func)
    
    return decorator


def retry_api_call(
    func: Callable[..., T],
    service: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> T:
    """
    Execute an API call with retry logic.
    
    Args:
        func: Function to execute
        service: Service name for specific retry policy
        context: Additional context for logging
        **kwargs: Additional configuration options
        
    Returns:
        Result of func execution
        
    Example:
        result = retry_api_call(
            lambda: requests.get(url),
            service='notion',
            context={'endpoint': 'pages', 'method': 'GET'}
        )
    """
    retry_manager = RetryManager(service=service, **kwargs)
    
    if context:
        return retry_manager.retry_with_context(func, context)
    else:
        wrapped_func = retry_manager.with_retry(func)
        return wrapped_func()