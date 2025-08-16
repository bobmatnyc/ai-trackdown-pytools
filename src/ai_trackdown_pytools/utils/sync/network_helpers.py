"""Network helper utilities for sync adapters.

This module provides common network operations with proper error handling,
retry logic, and rate limiting support for sync adapters.

WHY: All sync adapters need robust network error handling and retry logic.
Centralizing these utilities reduces code duplication and ensures consistent
behavior across all adapters.
"""

import asyncio
import time
from functools import wraps
from typing import Awaitable, Callable, Dict, Optional, TypeVar

import aiohttp

from ai_trackdown_pytools.exceptions import NetworkError
from ai_trackdown_pytools.utils.retry import RetryConfig

from .exceptions import ConnectionError as SyncConnectionError
from .exceptions import RateLimitError

T = TypeVar("T")


class NetworkRetryConfig(RetryConfig):
    """Network-specific retry configuration.

    WHY: Network operations have specific retry requirements different from
    file operations. This config provides sensible defaults for API calls.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on_status: Optional[set] = None,
    ):
        """Initialize network retry config.

        Args:
            retry_on_status: Set of HTTP status codes to retry on
        """
        super().__init__(
            max_attempts=max_attempts,
            initial_delay=initial_delay,
            max_delay=max_delay,
            exponential_base=exponential_base,
            jitter=jitter,
            exceptions=(
                aiohttp.ClientError,
                NetworkError,
                SyncConnectionError,
                asyncio.TimeoutError,
            ),
        )
        # Default retryable status codes
        self.retry_on_status = retry_on_status or {429, 502, 503, 504}


async def retry_with_backoff_async(
    func: Callable[..., Awaitable[T]],
    args: tuple = (),
    kwargs: Optional[dict] = None,
    config: Optional[NetworkRetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> T:
    """Execute an async function with retry logic.

    WHY: Async operations need special handling for retries. This function
    provides exponential backoff with jitter for async network calls.

    Args:
        func: Async function to execute
        args: Positional arguments
        kwargs: Keyword arguments
        config: Retry configuration
        on_retry: Callback before each retry

    Returns:
        Result of the function call

    Raises:
        The last exception if all retries fail
    """
    if kwargs is None:
        kwargs = {}

    if config is None:
        config = NetworkRetryConfig()

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            result = await func(*args, **kwargs)

            # Check if it's an HTTP response we should retry
            if hasattr(result, "status") and result.status in config.retry_on_status:
                if result.status == 429:
                    # Handle rate limiting specially
                    retry_after = result.headers.get(
                        "Retry-After", config.calculate_delay(attempt)
                    )
                    if isinstance(retry_after, str):
                        retry_after = int(retry_after)

                    raise RateLimitError(
                        "Rate limit exceeded",
                        platform="unknown",
                        retry_after=retry_after,
                    )
                else:
                    raise NetworkError(
                        f"HTTP {result.status} error", status_code=result.status
                    )

            return result

        except config.exceptions as e:
            last_exception = e

            # Check if it's a rate limit error with specific retry time
            if isinstance(e, RateLimitError) and e.retry_after:
                delay = e.retry_after
            else:
                delay = config.calculate_delay(attempt)

            if attempt < config.max_attempts - 1:
                if on_retry:
                    on_retry(e, attempt + 1)

                await asyncio.sleep(delay)
            else:
                raise

    if last_exception:
        raise last_exception


def with_network_retry(
    config: Optional[NetworkRetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """Decorator for adding retry logic to async network functions.

    WHY: Decorators make it easy to add retry logic to any async function
    without modifying its core logic.

    Args:
        config: Retry configuration
        on_retry: Callback before each retry

    Example:
        @with_network_retry(NetworkRetryConfig(max_attempts=5))
        async def fetch_data(url):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """
    if config is None:
        config = NetworkRetryConfig()

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff_async(
                func, args=args, kwargs=kwargs, config=config, on_retry=on_retry
            )

        return wrapper

    return decorator


async def make_api_request(
    session: aiohttp.ClientSession, method: str, url: str, **kwargs
) -> aiohttp.ClientResponse:
    """Make an API request with proper error handling.

    WHY: All API requests need consistent error handling and retry logic.
    This function centralizes that logic for reuse across adapters.

    Args:
        session: aiohttp client session
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        **kwargs: Additional arguments for the request

    Returns:
        Response object

    Raises:
        NetworkError: For network-related failures
        RateLimitError: When rate limited
    """
    retry_config = NetworkRetryConfig()

    async def _make_request():
        try:
            async with session.request(method, url, **kwargs) as response:
                # Handle rate limiting
                if response.status == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        retry_after = (
                            int(retry_after)
                            if isinstance(retry_after, str)
                            else retry_after
                        )
                    raise RateLimitError(
                        "Rate limit exceeded", platform="api", retry_after=retry_after
                    )

                # Handle other HTTP errors
                if response.status >= 500:
                    raise NetworkError(
                        f"Server error: HTTP {response.status}",
                        url=url,
                        status_code=response.status,
                    )
                elif response.status >= 400:
                    text = await response.text()
                    raise NetworkError(
                        f"Client error: HTTP {response.status} - {text}",
                        url=url,
                        status_code=response.status,
                    )

                return response

        except aiohttp.ClientError as e:
            raise NetworkError(
                f"Network request failed: {str(e)}", url=url, original_error=e
            )
        except asyncio.TimeoutError as e:
            raise NetworkError("Request timed out", url=url, original_error=e)

    return await retry_with_backoff_async(_make_request, config=retry_config)


class RateLimiter:
    """Rate limiter for API requests.

    WHY: Many APIs have rate limits. This class helps track and respect
    those limits to avoid getting blocked or banned.
    """

    def __init__(self, requests_per_second: float = 10.0):
        """Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
        """
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Wait if necessary to respect rate limit.

        WHY: This ensures we don't exceed the API's rate limit by
        spacing out requests appropriately.
        """
        async with self._lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()

    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update rate limit from response headers.

        WHY: Many APIs provide rate limit information in response headers.
        This allows dynamic adjustment based on actual limits.

        Args:
            headers: Response headers
        """
        # Check for common rate limit headers
        if "X-RateLimit-Limit" in headers:
            try:
                limit = int(headers["X-RateLimit-Limit"])
                # Assume this is per minute, convert to per second
                self.requests_per_second = limit / 60.0
                self.min_interval = 1.0 / self.requests_per_second
            except (ValueError, ZeroDivisionError):
                pass

        if "X-RateLimit-Remaining" in headers and "X-RateLimit-Reset" in headers:
            try:
                remaining = int(headers["X-RateLimit-Remaining"])
                reset_time = int(headers["X-RateLimit-Reset"])
                current_time = time.time()

                if remaining > 0 and reset_time > current_time:
                    # Calculate optimal rate to use remaining requests
                    time_until_reset = reset_time - current_time
                    self.requests_per_second = remaining / time_until_reset
                    self.min_interval = 1.0 / self.requests_per_second
            except (ValueError, ZeroDivisionError):
                pass


__all__ = [
    "NetworkRetryConfig",
    "retry_with_backoff_async",
    "with_network_retry",
    "make_api_request",
    "RateLimiter",
]
