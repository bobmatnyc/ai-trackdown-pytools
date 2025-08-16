"""Retry logic and error recovery utilities.

This module provides retry decorators and utilities for handling transient failures
with exponential backoff, jitter, and configurable retry strategies.

WHY: Many operations (network calls, file I/O with locks) can fail transiently.
Smart retry logic improves reliability without manual intervention.
"""

import functools
import random
import time
from pathlib import Path
from typing import Any, Callable, Optional, Tuple, Type, Union

from ..exceptions import FileOperationError, NetworkError


class RetryConfig:
    """Configuration for retry behavior.

    WHY: Centralized retry configuration allows consistent behavior across
    the application while remaining customizable for specific use cases.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            initial_delay: Initial delay in seconds between retries
            max_delay: Maximum delay in seconds between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            exceptions: Tuple of exceptions to retry on
        """
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.exceptions = exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number.

        WHY: Exponential backoff with jitter prevents thundering herd problems
        and reduces load on failing services.

        Args:
            attempt: The attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = min(
            self.initial_delay * (self.exponential_base**attempt), self.max_delay
        )

        if self.jitter:
            # Add up to 25% jitter
            delay = delay * (0.75 + random.random() * 0.5)

        return delay


# Predefined retry configurations for common scenarios
NETWORK_RETRY = RetryConfig(
    max_attempts=5,
    initial_delay=1.0,
    max_delay=30.0,
    exceptions=(NetworkError, ConnectionError, TimeoutError),
)

FILE_RETRY = RetryConfig(
    max_attempts=3,
    initial_delay=0.5,
    max_delay=5.0,
    exceptions=(FileOperationError, PermissionError, OSError),
)

QUICK_RETRY = RetryConfig(max_attempts=3, initial_delay=0.1, max_delay=1.0)


def retry(
    config: Optional[RetryConfig] = None,
    *,
    max_attempts: Optional[int] = None,
    exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    """Decorator for adding retry logic to functions.

    WHY: A decorator approach makes it easy to add retry logic to any function
    without modifying its core logic. This promotes separation of concerns.

    Args:
        config: RetryConfig object or None for defaults
        max_attempts: Override max attempts from config
        exceptions: Override exceptions to retry on
        on_retry: Callback function called before each retry

    Returns:
        Decorated function with retry logic

    Example:
        @retry(NETWORK_RETRY)
        def fetch_data(url):
            return requests.get(url)

        @retry(max_attempts=5, exceptions=(ValueError,))
        def process_data(data):
            return transform(data)
    """
    if config is None:
        config = RetryConfig()

    if max_attempts is not None:
        config = RetryConfig(
            max_attempts=max_attempts,
            initial_delay=config.initial_delay,
            max_delay=config.max_delay,
            exponential_base=config.exponential_base,
            jitter=config.jitter,
            exceptions=exceptions or config.exceptions,
        )
    elif exceptions is not None:
        config = RetryConfig(
            max_attempts=config.max_attempts,
            initial_delay=config.initial_delay,
            max_delay=config.max_delay,
            exponential_base=config.exponential_base,
            jitter=config.jitter,
            exceptions=exceptions,
        )

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except config.exceptions as e:
                    last_exception = e

                    if attempt < config.max_attempts - 1:
                        delay = config.calculate_delay(attempt)

                        if on_retry:
                            on_retry(e, attempt + 1)

                        time.sleep(delay)
                    else:
                        # Last attempt failed, re-raise
                        raise

            # Should not reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def retry_with_backoff(
    func: Callable,
    args: tuple = (),
    kwargs: Optional[dict] = None,
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Any:
    """Execute a function with retry logic.

    WHY: Sometimes you need retry logic for functions you don't control
    or for one-off operations where a decorator isn't appropriate.

    Args:
        func: Function to execute
        args: Positional arguments for the function
        kwargs: Keyword arguments for the function
        config: RetryConfig object or None for defaults
        on_retry: Callback function called before each retry

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries fail

    Example:
        result = retry_with_backoff(
            requests.get,
            args=('https://api.example.com/data',),
            config=NETWORK_RETRY
        )
    """
    if kwargs is None:
        kwargs = {}

    if config is None:
        config = RetryConfig()

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return func(*args, **kwargs)
        except config.exceptions as e:
            last_exception = e

            if attempt < config.max_attempts - 1:
                delay = config.calculate_delay(attempt)

                if on_retry:
                    on_retry(e, attempt + 1)

                time.sleep(delay)
            else:
                raise

    if last_exception:
        raise last_exception


class RetryableFileOperation:
    """Context manager for retryable file operations.

    WHY: File operations can fail due to temporary locks or permission issues.
    This context manager provides automatic retry with proper cleanup.

    Example:
        with RetryableFileOperation('data.json', 'w') as f:
            json.dump(data, f)
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        mode: str = "r",
        config: Optional[RetryConfig] = None,
        **kwargs: Any,
    ):
        """Initialize retryable file operation.

        Args:
            file_path: Path to the file
            mode: File open mode
            config: RetryConfig or None for FILE_RETRY defaults
            **kwargs: Additional arguments for open()
        """
        self.file_path = Path(file_path)
        self.mode = mode
        self.config = config or FILE_RETRY
        self.kwargs = kwargs
        self.file_handle = None

    def __enter__(self) -> Any:
        """Open file with retry logic."""

        def open_file():
            return open(self.file_path, self.mode, **self.kwargs)

        self.file_handle = retry_with_backoff(open_file, config=self.config)
        return self.file_handle

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Close file handle."""
        if self.file_handle:
            self.file_handle.close()


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable.

    WHY: Not all errors should trigger retries. This function helps identify
    transient errors that are worth retrying.

    Args:
        error: The exception to check

    Returns:
        True if the error is likely transient and worth retrying
    """
    # Network errors that are retryable
    if isinstance(error, (NetworkError, ConnectionError, TimeoutError)):
        return True

    # File errors that might be transient
    if isinstance(error, (FileOperationError, OSError, IOError)):
        error_str = str(error).lower()
        retryable_patterns = ["locked", "in use", "temporary", "retry", "again", "busy"]
        return any(pattern in error_str for pattern in retryable_patterns)

    # HTTP status codes that are retryable
    if hasattr(error, "response") and hasattr(error.response, "status_code"):
        status_code = error.response.status_code
        # Retry on 429 (rate limit), 502 (bad gateway), 503 (service unavailable), 504 (timeout)
        return status_code in {429, 502, 503, 504}

    return False


__all__ = [
    "RetryConfig",
    "NETWORK_RETRY",
    "FILE_RETRY",
    "QUICK_RETRY",
    "retry",
    "retry_with_backoff",
    "RetryableFileOperation",
    "is_retryable_error",
]
