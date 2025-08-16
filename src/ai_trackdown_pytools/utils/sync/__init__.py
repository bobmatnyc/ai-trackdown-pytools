"""Sync adapter system for multi-platform integration.

This module provides a flexible adapter system for syncing with external platforms
like GitHub, ClickUp, Linear, and JIRA. It follows the adapter pattern to allow
easy extension and configuration of new platforms.
"""

# Import adapters to trigger registration
# Import adapters with warning suppression for missing optional dependencies
import warnings

from .base import SyncAdapter, SyncConfig, SyncDirection, SyncResult
from .exceptions import (
    AdapterNotFoundError,
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    RateLimitError,
    SyncError,
    ValidationError,
)
from .registry import (
    AdapterRegistry,
    get_adapter,
    get_adapter_class,
    list_platforms,
    register_adapter,
)

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=ImportWarning)
    from . import adapters

__all__ = [
    # Base classes and types
    "SyncAdapter",
    "SyncConfig",
    "SyncResult",
    "SyncDirection",
    # Registry
    "AdapterRegistry",
    "register_adapter",
    "get_adapter",
    "get_adapter_class",
    "list_platforms",
    # Exceptions
    "SyncError",
    "AdapterNotFoundError",
    "AuthenticationError",
    "ConfigurationError",
    "ConnectionError",
    "RateLimitError",
    "ValidationError",
]
