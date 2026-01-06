"""Utility functions for DiscussionFetcher."""

import time
from typing import Callable, Any, Optional, TypeVar
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from requests.exceptions import Timeout, ConnectionError, HTTPError

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_on_failure(
    max_attempts: int = 3,
    min_wait: int = 2,
    max_wait: int = 10,
    exceptions: tuple = (Timeout, ConnectionError, HTTPError)
) -> Callable:
    """
    Decorator to retry function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        exceptions: Tuple of exceptions to retry on

    Returns:
        Decorated function
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )


class RateLimiter:
    """Adaptive rate limiter to control API request frequency."""

    def __init__(self, calls_per_second: float = 1.0):
        """
        Initialize rate limiter.

        Args:
            calls_per_second: Maximum number of calls per second
        """
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second if calls_per_second > 0 else 0
        self.last_call_time: Optional[float] = None

    def wait_if_needed(self) -> None:
        """Wait if necessary to maintain rate limit."""
        if self.last_call_time is None:
            self.last_call_time = time.time()
            return

        current_time = time.time()
        elapsed = current_time - self.last_call_time

        if elapsed < self.min_interval:
            sleep_time = self.min_interval - elapsed
            time.sleep(sleep_time)

        self.last_call_time = time.time()

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """
        Decorator to rate limit a function.

        Args:
            func: Function to rate limit

        Returns:
            Rate-limited function
        """
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            self.wait_if_needed()
            return func(*args, **kwargs)

        return wrapper


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.

    Args:
        data: Dictionary to get value from
        *keys: Nested keys to traverse
        default: Default value if key not found

    Returns:
        Value at nested key or default

    Example:
        >>> data = {'a': {'b': {'c': 1}}}
        >>> safe_get(data, 'a', 'b', 'c')
        1
        >>> safe_get(data, 'a', 'x', 'y', default=0)
        0
    """
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def batch_items(items: list, batch_size: int):
    """
    Yield batches of items.

    Args:
        items: List of items to batch
        batch_size: Size of each batch

    Yields:
        Batches of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters for filenames
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename
