"""Exceptions for sync adapter system."""

from typing import Any, Dict, List, Optional


class SyncError(Exception):
    """Base exception for all sync-related errors.

    WHY: Provides a common base for all sync exceptions, allowing callers to catch
    all sync-related errors with a single except clause. This follows the pattern
    established in core/exceptions.py for domain-specific exceptions.
    """

    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """Initialize sync error with context.

        Args:
            message: Error message
            platform: Platform where error occurred (optional)
            details: Additional error details (optional)
        """
        super().__init__(message)
        self.platform = platform
        self.details = details or {}


class AdapterNotFoundError(SyncError):
    """Raised when a requested adapter is not found in the registry.

    WHY: Specific exception for missing adapters allows better error handling
    and clearer user messages when a platform isn't supported.
    """

    def __init__(self, platform: str):
        super().__init__(
            f"No adapter found for platform: {platform}", platform=platform
        )


class AuthenticationError(SyncError):
    """Raised when authentication fails for a platform.

    WHY: Authentication failures need special handling as they often require
    user intervention to provide or update credentials.
    """

    def __init__(self, message: str, platform: str, auth_method: Optional[str] = None):
        super().__init__(message, platform)
        self.auth_method = auth_method


class ConfigurationError(SyncError):
    """Raised when adapter configuration is invalid or missing.

    WHY: Configuration errors are common and need clear messaging to help
    users fix their setup. Separate from general errors for better UX.
    """

    def __init__(
        self, message: str, platform: str, missing_fields: Optional[List[str]] = None
    ):
        super().__init__(message, platform)
        self.missing_fields = missing_fields or []


class ConnectionError(SyncError):
    """Raised when connection to external platform fails.

    WHY: Network and connection issues are transient and may need retry logic,
    so they need to be distinguishable from other error types.
    """

    def __init__(self, message: str, platform: str, endpoint: Optional[str] = None):
        super().__init__(message, platform)
        self.endpoint = endpoint


class RateLimitError(SyncError):
    """Raised when API rate limits are exceeded.

    WHY: Rate limiting requires specific handling like backoff strategies.
    Having a dedicated exception allows implementing smart retry logic.
    """

    def __init__(self, message: str, platform: str, retry_after: Optional[int] = None):
        super().__init__(message, platform)
        self.retry_after = retry_after  # Seconds until rate limit resets


class ValidationError(SyncError):
    """Raised when data validation fails during sync.

    WHY: Data validation errors need detailed information about what failed
    to help users fix their data. Separate from general errors for clarity.
    """

    def __init__(
        self, message: str, platform: str, field_errors: Optional[Dict[str, str]] = None
    ):
        super().__init__(message, platform)
        self.field_errors = field_errors or {}
