"""Adapter registry for dynamic adapter loading and management."""

import inspect
from typing import Any, Dict, List, Type

from .base import SyncAdapter, SyncConfig
from .exceptions import AdapterNotFoundError


class AdapterRegistry:
    """Registry for sync adapters.

    WHY: The registry pattern allows for dynamic adapter discovery and loading.
    This design makes it easy to add new platform adapters without modifying
    core sync logic, following the Open/Closed Principle.

    DESIGN DECISION: Using a class-based registry instead of module-level
    variables for better encapsulation and testability.
    """

    def __init__(self) -> None:
        """Initialize the adapter registry."""
        self._adapters: Dict[str, Type[SyncAdapter]] = {}
        self._instances: Dict[str, SyncAdapter] = {}

    def register(self, platform: str, adapter_class: Type[SyncAdapter]) -> None:
        """Register an adapter for a platform.

        WHY: Manual registration gives us control over which adapters are
        available and allows for adapter validation at registration time.

        Args:
            platform: Platform identifier (e.g., "github", "clickup")
            adapter_class: Adapter class to register

        Raises:
            ValueError: If platform is already registered or adapter is invalid
        """
        platform = platform.lower()

        if platform in self._adapters:
            raise ValueError(f"Adapter for platform '{platform}' is already registered")

        if not inspect.isclass(adapter_class):
            raise ValueError("Adapter must be a class")

        if not issubclass(adapter_class, SyncAdapter):
            raise ValueError("Adapter must inherit from SyncAdapter")

        self._adapters[platform] = adapter_class

    def unregister(self, platform: str) -> None:
        """Unregister an adapter.

        WHY: Allows for dynamic adapter management, useful for testing
        and plugin systems.

        Args:
            platform: Platform identifier to unregister
        """
        platform = platform.lower()
        self._adapters.pop(platform, None)
        self._instances.pop(platform, None)

    def get_adapter(self, platform: str, config: SyncConfig) -> SyncAdapter:
        """Get an adapter instance for a platform.

        WHY: Factory method pattern ensures consistent adapter creation
        and allows for adapter instance caching if needed.

        Args:
            platform: Platform identifier
            config: Sync configuration

        Returns:
            Configured adapter instance

        Raises:
            AdapterNotFoundError: If no adapter is registered for the platform
        """
        platform = platform.lower()

        if platform not in self._adapters:
            available = ", ".join(sorted(self._adapters.keys()))
            raise AdapterNotFoundError(
                f"No adapter registered for platform: {platform}. "
                f"Available platforms: {available}"
            )

        # Create new instance with provided config
        # WHY: Not caching instances because each sync operation might have
        # different configuration. This ensures clean state for each sync.
        adapter_class = self._adapters[platform]
        return adapter_class(config)

    def list_platforms(self) -> List[str]:
        """Get list of registered platforms.

        Returns:
            Sorted list of platform names
        """
        return sorted(self._adapters.keys())

    def is_registered(self, platform: str) -> bool:
        """Check if a platform has a registered adapter.

        Args:
            platform: Platform identifier

        Returns:
            True if platform has a registered adapter
        """
        return platform.lower() in self._adapters

    def get_adapter_info(self, platform: str) -> Dict[str, Any]:
        """Get information about a registered adapter.

        WHY: Useful for debugging and generating documentation about
        available adapters and their capabilities.

        Args:
            platform: Platform identifier

        Returns:
            Dictionary with adapter information

        Raises:
            AdapterNotFoundError: If no adapter is registered for the platform
        """
        platform = platform.lower()

        if platform not in self._adapters:
            raise AdapterNotFoundError(platform)

        adapter_class = self._adapters[platform]

        # Create temporary instance to get runtime info
        temp_config = SyncConfig(platform=platform)
        temp_instance = adapter_class(temp_config)

        return {
            "platform": platform,
            "class_name": adapter_class.__name__,
            "module": adapter_class.__module__,
            "supported_types": list(temp_instance.supported_types),
            "docstring": inspect.getdoc(adapter_class),
        }


# Global registry instance
# WHY: Single global registry simplifies adapter management while still
# allowing for custom registries in tests or special use cases.
_default_registry = AdapterRegistry()


def register_adapter(platform: str, adapter_class: Type[SyncAdapter]) -> None:
    """Register an adapter with the default registry.

    Args:
        platform: Platform identifier
        adapter_class: Adapter class to register
    """
    _default_registry.register(platform, adapter_class)


def get_adapter(platform: str, config: SyncConfig) -> SyncAdapter:
    """Get an adapter from the default registry.

    Args:
        platform: Platform identifier
        config: Sync configuration

    Returns:
        Configured adapter instance
    """
    return _default_registry.get_adapter(platform, config)


def get_adapter_class(platform: str) -> Type[SyncAdapter]:
    """Get an adapter class from the default registry.

    Args:
        platform: Platform identifier

    Returns:
        Adapter class

    Raises:
        AdapterNotFoundError: If platform not registered
    """
    if platform not in _default_registry._adapters:
        raise AdapterNotFoundError(f"No adapter registered for platform: {platform}")
    return _default_registry._adapters[platform]


def list_platforms() -> List[str]:
    """List platforms in the default registry.

    Returns:
        List of registered platform names
    """
    return _default_registry.list_platforms()


def get_registry() -> AdapterRegistry:
    """Get the default registry instance.

    WHY: Allows access to the registry for advanced use cases while
    keeping the common case simple with module-level functions.

    Returns:
        The default registry instance
    """
    return _default_registry
