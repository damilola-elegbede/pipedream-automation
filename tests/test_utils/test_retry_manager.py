"""Tests for RetryManager module."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.utils.retry_manager import RetryManager, with_retry, retry_api_call


class TestRetryManager:
    """Test cases for RetryManager class."""
    
    def test_init_default_config(self):
        """Test RetryManager initialization with default config."""
        manager = RetryManager()
        
        assert manager.config['max_attempts'] == 3
        assert manager.config['base_delay'] == 1.0
        assert manager.config['max_delay'] == 60.0
        assert manager.config['exponential_base'] == 2.0
        assert manager.config['jitter'] is True
    
    def test_init_service_config(self):
        """Test RetryManager initialization with service-specific config."""
        manager = RetryManager(service='notion')
        
        assert manager.config['max_attempts'] == 5
        assert manager.config['base_delay'] == 2.0
        assert manager.config['max_delay'] == 30.0
        assert manager.config['retryable_status_codes'] == [429, 502, 503, 504]
    
    def test_init_custom_config(self):
        """Test RetryManager initialization with custom config."""
        manager = RetryManager(max_attempts=10, base_delay=5.0)
        
        assert manager.config['max_attempts'] == 10
        assert manager.config['base_delay'] == 5.0
    
    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        manager = RetryManager(jitter=False)
        
        # Test exponential growth
        assert manager.calculate_delay(1) == 1.0  # 1 * 2^0
        assert manager.calculate_delay(2) == 2.0  # 1 * 2^1
        assert manager.calculate_delay(3) == 4.0  # 1 * 2^2
        assert manager.calculate_delay(4) == 8.0  # 1 * 2^3
    
    def test_calculate_delay_max_cap(self):
        """Test that delay is capped at max_delay."""
        manager = RetryManager(jitter=False, max_delay=5.0)
        
        # Should be capped at 5.0
        assert manager.calculate_delay(10) == 5.0
    
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        manager = RetryManager(jitter=True, base_delay=10.0)
        
        # Run multiple times to test randomness
        delays = [manager.calculate_delay(2) for _ in range(10)]
        
        # All delays should be around 20.0 (10 * 2^1) ± 25%
        for delay in delays:
            assert 15.0 <= delay <= 25.0
        
        # Delays should vary due to jitter
        assert len(set(delays)) > 1
    
    def test_should_retry_max_attempts(self):
        """Test that retry stops at max attempts."""
        manager = RetryManager(max_attempts=3)
        
        exc = Exception("Test error")
        assert manager.should_retry(exc, 1) is False  # Unknown exception
        assert manager.should_retry(exc, 3) is False  # At max attempts
    
    def test_should_retry_retryable_exceptions(self):
        """Test retry for configured exception types."""
        manager = RetryManager(service='notion')
        
        # Retryable exceptions
        assert manager.should_retry(ConnectionError(), 1) is True
        assert manager.should_retry(TimeoutError(), 1) is True
        
        # Non-retryable exception
        assert manager.should_retry(ValueError(), 1) is False
    
    def test_should_retry_status_codes(self):
        """Test retry for HTTP status codes."""
        manager = RetryManager(service='notion')
        
        # Mock HTTP exception with status code
        exc_429 = Mock()
        exc_429.response = Mock(status_code=429)
        assert manager.should_retry(exc_429, 1) is True
        
        exc_404 = Mock()
        exc_404.response = Mock(status_code=404)
        assert manager.should_retry(exc_404, 1) is False
    
    def test_extract_retry_after_disabled(self):
        """Test that Retry-After is ignored when disabled."""
        manager = RetryManager(respect_retry_after=False)
        
        exc = Mock()
        exc.response = Mock(headers={'Retry-After': '10'})
        
        assert manager.extract_retry_after(exc) is None
    
    def test_extract_retry_after_seconds(self):
        """Test extracting Retry-After as seconds."""
        manager = RetryManager(respect_retry_after=True)
        
        exc = Mock()
        exc.response = Mock(headers={'Retry-After': '10'})
        
        assert manager.extract_retry_after(exc) == 10.0
    
    @patch('src.utils.retry_manager.datetime')
    def test_extract_retry_after_date(self, mock_datetime):
        """Test extracting Retry-After as HTTP date."""
        manager = RetryManager(respect_retry_after=True)
        
        # Mock current time and future time
        from datetime import datetime as dt, timedelta
        mock_now = dt(2025, 1, 6, 12, 0, 0)
        mock_future = dt(2025, 1, 6, 12, 0, 30)
        
        mock_datetime.utcnow.return_value = mock_now
        mock_datetime.strptime.return_value = mock_future
        
        exc = Mock()
        exc.response = Mock(headers={'Retry-After': 'Wed, 21 Oct 2025 07:28:00 GMT'})
        
        result = manager.extract_retry_after(exc)
        
        # Should return 30 seconds
        assert result == 30.0
        mock_datetime.strptime.assert_called_once_with(
            'Wed, 21 Oct 2025 07:28:00 GMT',
            '%a, %d %b %Y %H:%M:%S GMT'
        )
    
    def test_with_retry_success(self):
        """Test successful function execution with retry decorator."""
        manager = RetryManager()
        
        mock_func = Mock(return_value="success")
        wrapped_func = manager.with_retry(mock_func)
        
        result = wrapped_func()
        assert result == "success"
        assert mock_func.call_count == 1
        assert manager.metrics['total_attempts'] == 1
        assert manager.metrics['successful_retries'] == 0
    
    def test_with_retry_eventual_success(self):
        """Test function that succeeds after retries."""
        manager = RetryManager(service='notion')
        
        # Fail twice, then succeed
        mock_func = Mock(side_effect=[ConnectionError(), ConnectionError(), "success"])
        mock_func.__name__ = "mock_function"  # Add __name__ attribute for logging
        wrapped_func = manager.with_retry(mock_func)
        
        result = wrapped_func()
        assert result == "success"
        assert mock_func.call_count == 3
        assert manager.metrics['total_attempts'] == 3
        assert manager.metrics['successful_retries'] == 1
    
    @patch('time.sleep')
    def test_with_retry_all_failures(self, mock_sleep):
        """Test function that fails all retry attempts."""
        manager = RetryManager(max_attempts=3)
        manager.config['retryable_exceptions'] = (ValueError,)
        
        mock_func = Mock(side_effect=ValueError("Test error"))
        mock_func.__name__ = "failing_function"
        wrapped_func = manager.with_retry(mock_func)
        
        with pytest.raises(ValueError, match="Test error"):
            wrapped_func()
        
        assert mock_func.call_count == 3
        assert manager.metrics['total_attempts'] == 3
        # failed_retries is 0 because the final attempt is not counted as a "retry"
        # (it hits the max attempts check and raises immediately)
        assert manager.metrics['failed_retries'] == 0
        
        # Verify delays between retries
        assert mock_sleep.call_count == 2  # 2 retries = 2 delays
    
    def test_with_retry_non_retryable(self):
        """Test function with non-retryable exception."""
        manager = RetryManager(retryable_exceptions=(ConnectionError,))
        
        mock_func = Mock(side_effect=ValueError("Not retryable"))
        mock_func.__name__ = "non_retryable_function"
        wrapped_func = manager.with_retry(mock_func)
        
        with pytest.raises(ValueError, match="Not retryable"):
            wrapped_func()
        
        # Should not retry
        assert mock_func.call_count == 1
        assert manager.metrics['total_attempts'] == 1
    
    def test_retry_with_context(self):
        """Test retry with additional context."""
        manager = RetryManager()
        
        mock_func = Mock(return_value="success")
        context = {'endpoint': 'test', 'method': 'GET'}
        
        result = manager.retry_with_context(mock_func, context, "arg1", key="value")
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", key="value")
    
    def test_get_metrics(self):
        """Test metrics calculation."""
        manager = RetryManager()
        
        # Simulate some operations
        manager.metrics = {
            'total_attempts': 10,
            'successful_retries': 3,
            'failed_retries': 1,
            'total_delay_time': 15.0,
        }
        
        metrics = manager.get_metrics()
        
        assert metrics['total_attempts'] == 10
        assert metrics['retry_rate'] == 0.4  # (3+1)/10
        assert metrics['retry_success_rate'] == 0.75  # 3/(3+1)
        assert metrics['average_delay'] == 1.5  # 15/10
    
    def test_get_metrics_no_attempts(self):
        """Test metrics when no attempts have been made."""
        manager = RetryManager()
        
        metrics = manager.get_metrics()
        
        assert metrics['retry_rate'] == 0.0
        assert metrics['retry_success_rate'] == 0.0
        assert metrics['average_delay'] == 0.0
    
    def test_reset_metrics(self):
        """Test resetting metrics."""
        manager = RetryManager()
        
        # Set some metrics
        manager.metrics['total_attempts'] = 10
        
        # Reset
        manager.reset_metrics()
        
        assert manager.metrics['total_attempts'] == 0
        assert manager.metrics['successful_retries'] == 0
        assert manager.metrics['failed_retries'] == 0
        assert manager.metrics['total_delay_time'] == 0.0


class TestConvenienceFunctions:
    """Test convenience functions for retry functionality."""
    
    def test_with_retry_decorator(self):
        """Test @with_retry decorator."""
        @with_retry(service='gmail', max_attempts=2)
        def test_func():
            return "decorated result"
        
        result = test_func()
        assert result == "decorated result"
    
    def test_with_retry_decorator_with_failures(self):
        """Test @with_retry decorator with retries."""
        attempt_count = 0
        
        @with_retry(max_attempts=3, retryable_exceptions=(ValueError,))
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Retry me")
            return "success after retries"
        
        result = test_func()
        assert result == "success after retries"
        assert attempt_count == 3
    
    @patch('time.sleep')
    def test_retry_api_call(self, mock_sleep):
        """Test retry_api_call function."""
        mock_func = Mock(side_effect=[ConnectionError(), "api result"])
        mock_func.__name__ = "api_function"
        
        result = retry_api_call(
            mock_func,
            service='notion',
            context={'endpoint': 'pages'}
        )
        
        assert result == "api result"
        assert mock_func.call_count == 2
    
    def test_retry_api_call_no_context(self):
        """Test retry_api_call without context."""
        mock_func = Mock(return_value="direct result")
        
        result = retry_api_call(mock_func)
        
        assert result == "direct result"
        assert mock_func.call_count == 1


class TestIntegrationScenarios:
    """Integration tests for real-world retry scenarios."""
    
    @patch('time.sleep')
    def test_api_rate_limit_scenario(self, mock_sleep):
        """Test handling API rate limits with retries."""
        manager = RetryManager(service='openai')
        
        # Create a proper exception with response attribute
        class RateLimitError(Exception):
            def __init__(self):
                super().__init__("Rate limited")
                self.response = Mock(status_code=429, headers={'Retry-After': '2'})
        
        mock_api = Mock(side_effect=[RateLimitError(), "success"])
        mock_api.__name__ = "api_call"
        wrapped_api = manager.with_retry(mock_api)
        
        result = wrapped_api()
        assert result == "success"
        assert mock_api.call_count == 2
        
        # Verify that Retry-After was respected
        mock_sleep.assert_called_with(2.0)
    
    @patch('time.sleep')
    def test_network_instability_scenario(self, mock_sleep):
        """Test handling network instability with retries."""
        manager = RetryManager(
            max_attempts=5,
            base_delay=0.5,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )
        
        # Simulate intermittent network issues
        mock_request = Mock(side_effect=[
            ConnectionError("Network unreachable"),
            TimeoutError("Request timeout"),
            ConnectionError("Connection reset"),
            "response data"
        ])
        mock_request.__name__ = "network_request"
        
        wrapped_request = manager.with_retry(mock_request)
        
        result = wrapped_request()
        assert result == "response data"
        assert mock_request.call_count == 4
        assert manager.metrics['successful_retries'] == 1
    
    def test_non_idempotent_operation(self):
        """Test that non-idempotent operations fail fast on certain errors."""
        manager = RetryManager(
            retryable_exceptions=(TimeoutError,),  # Only retry timeouts
            max_attempts=3
        )
        
        # Create a custom exception class for testing
        class ConflictError(Exception):
            def __init__(self):
                super().__init__("409 Conflict")
                self.response = Mock(status_code=409)
        
        mock_post = Mock(side_effect=ConflictError())
        mock_post.__name__ = "post_request"
        wrapped_post = manager.with_retry(mock_post)
        
        with pytest.raises(ConflictError):
            wrapped_post()
        
        # Should not retry on 409
        assert mock_post.call_count == 1