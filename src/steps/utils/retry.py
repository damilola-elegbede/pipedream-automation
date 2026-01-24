"""
Shared retry utilities with exponential backoff.

Provides consistent retry behavior across all API integrations.
"""
import time
import random
import requests


class MaxRetriesExceededError(Exception):
    """Raised when maximum retry attempts have been exhausted."""
    pass


def retry_with_backoff(request_func, max_retries=5):
    """
    Execute request with exponential backoff for rate limits and timeouts.

    Handles:
    - HTTP 429 (Too Many Requests) and 503 (Service Unavailable) errors
    - Connection timeouts and read timeouts
    Retries with exponential backoff. Respects Retry-After header.

    Args:
        request_func: Callable that returns a requests.Response object
        max_retries: Maximum number of retry attempts (default: 5)

    Returns:
        requests.Response object on success

    Raises:
        MaxRetriesExceededError: When all retries have been exhausted
        requests.HTTPError: For non-retryable HTTP errors
        requests.Timeout: When timeout occurs on final attempt
        requests.ConnectionError: When connection fails on final attempt
    """
    for attempt in range(max_retries):
        try:
            response = request_func()
            response.raise_for_status()
            return response
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt < max_retries - 1:
                wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Timeout/connection error: {e}. Waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code in (429, 503) and attempt < max_retries - 1:
                retry_after = e.response.headers.get('Retry-After')
                if retry_after:
                    try:
                        wait = float(retry_after)
                    except ValueError:
                        wait = (2 ** attempt) + random.uniform(0, 1)
                else:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                print(f"Rate limited. Waiting {wait:.1f}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                raise
    raise MaxRetriesExceededError(f"Max retries ({max_retries}) exceeded")
