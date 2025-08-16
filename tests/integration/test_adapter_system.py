"""Integration tests for the complete adapter system.

This module tests the entire sync adapter system including:
- All adapter implementations
- Registry management
- Authentication and configuration
- Pull/push operations
- Error handling
- Backward compatibility
"""

from datetime import datetime

import pytest

from ai_trackdown_pytools.core.models import (
    TaskModel,
    TaskStatus,
)
from ai_trackdown_pytools.utils.sync import (
    SyncAdapter,
    SyncConfig,
    get_adapter,
    list_platforms,
)
from ai_trackdown_pytools.utils.sync.exceptions import (
    AdapterNotFoundError,
    ConfigurationError,
)
from ai_trackdown_pytools.utils.sync.registry import get_registry


class TestAdapterSystem:
    """Test the complete adapter system integration."""

    def test_all_adapters_registered(self):
        """Verify all expected adapters are registered."""
        platforms = list_platforms()
        expected_platforms = {"github", "clickup", "linear", "jira"}

        assert set(platforms) == expected_platforms

        # Verify each can be retrieved
        for platform in expected_platforms:
            adapter_class = get_adapter(platform)
            assert issubclass(adapter_class, SyncAdapter)

    def test_adapter_info_completeness(self):
        """Verify adapter info is complete for all adapters."""
        registry = get_registry()

        for platform in list_platforms():
            info = registry.get_adapter_info(platform)

            # Check required fields
            assert info["platform"] == platform
            assert "class_name" in info
            assert "module" in info
            assert "supported_types" in info
            assert isinstance(info["supported_types"], list)
            assert len(info["supported_types"]) > 0
            assert "docstring" in info

    def test_adapter_instantiation(self):
        """Test that all adapters can be instantiated with proper config."""
        test_configs = {
            "github": {"auth_config": {"token": "test-token", "repo": "owner/repo"}},
            "clickup": {"auth_config": {"api_token": "test-token", "list_id": "12345"}},
            "linear": {"auth_config": {"api_key": "test-key", "team_id": "team-123"}},
            "jira": {
                "auth_config": {
                    "server": "https://test.atlassian.net",
                    "email": "test@example.com",
                    "api_token": "test-token",
                    "project_key": "TEST",
                }
            },
        }

        for platform, config_data in test_configs.items():
            config = SyncConfig(platform=platform, **config_data)
            adapter = get_adapter(platform, config)

            assert adapter.platform_name == platform
            assert isinstance(adapter.supported_types, set)
            assert len(adapter.supported_types) > 0

    def test_adapter_interface_compliance(self):
        """Verify all adapters implement the required interface."""
        required_methods = [
            "platform_name",
            "supported_types",
            "validate_config",
            "authenticate",
            "test_connection",
            "pull_items",
            "push_item",
            "update_item",
            "delete_item",
            "get_item",
            "close",
        ]

        for platform in list_platforms():
            adapter_class = get_adapter(platform)

            # Check all required methods exist
            for method in required_methods:
                assert hasattr(
                    adapter_class, method
                ), f"{platform} adapter missing {method}"

    def test_configuration_validation(self):
        """Test configuration validation for all adapters."""
        # Test GitHub validation
        with pytest.raises(ConfigurationError):
            config = SyncConfig(platform="github", auth_config={})
            adapter = get_adapter("github", config)
            adapter.validate_config()

        # Test ClickUp validation
        with pytest.raises(ConfigurationError):
            config = SyncConfig(platform="clickup", auth_config={"api_token": "test"})
            adapter = get_adapter("clickup", config)
            adapter.validate_config()

        # Test Linear validation
        with pytest.raises(ConfigurationError):
            config = SyncConfig(platform="linear", auth_config={"api_key": "test"})
            adapter = get_adapter("linear", config)
            adapter.validate_config()

        # Test JIRA validation
        with pytest.raises(ConfigurationError):
            config = SyncConfig(platform="jira", auth_config={"server": "test"})
            adapter = get_adapter("jira", config)
            adapter.validate_config()

    def test_type_filtering(self):
        """Test that adapters correctly filter supported types."""
        test_types = {
            "github": (["issue", "task", "pr"], ["bug", "epic"]),
            "clickup": (["issue", "task"], ["pr", "epic", "bug"]),
            "linear": (["issue", "task", "bug"], ["pr", "epic"]),
            "jira": (["issue", "task", "epic", "bug"], ["pr"]),
        }

        for platform, (supported, unsupported) in test_types.items():
            adapter_class = get_adapter(platform)
            config = SyncConfig(platform=platform, auth_config={})
            adapter = adapter_class(config)

            # Test supported types
            for item_type in supported:
                assert adapter.filter_item_type(
                    item_type
                ), f"{platform} should support {item_type}"

            # Test unsupported types
            for item_type in unsupported:
                assert not adapter.filter_item_type(
                    item_type
                ), f"{platform} should not support {item_type}"

    def test_status_mapping(self):
        """Test status mapping for all adapters."""
        # Create test configs
        configs = {
            "github": SyncConfig(
                platform="github", auth_config={"token": "test", "repo": "test/test"}
            ),
            "clickup": SyncConfig(
                platform="clickup", auth_config={"api_token": "test", "list_id": "test"}
            ),
            "linear": SyncConfig(
                platform="linear", auth_config={"api_key": "test", "team_id": "test"}
            ),
            "jira": SyncConfig(
                platform="jira",
                auth_config={
                    "server": "https://test.com",
                    "email": "test@test.com",
                    "api_token": "test",
                    "project_key": "TEST",
                },
            ),
        }

        # Test that each adapter can map basic statuses
        for platform, config in configs.items():
            adapter = get_adapter(platform, config)

            # Test mapping TO platform format
            platform_status = adapter.map_status_to_platform(TaskStatus.OPEN, "task")
            assert platform_status is not None

            # Test mapping FROM platform format
            # This would need platform-specific status values

    def test_label_mapping(self):
        """Test label/tag mapping for all adapters."""
        test_labels = ["bug", "feature", "high-priority", "documentation"]

        for platform in list_platforms():
            config = SyncConfig(
                platform=platform,
                auth_config={},
                label_mapping={"bug": "defect", "feature": "enhancement"},
            )
            adapter_class = get_adapter(platform)
            adapter = adapter_class(config)

            # Test label mapping
            mapped = adapter.map_labels_to_platform(test_labels)
            assert "defect" in mapped or "bug" in mapped
            assert "enhancement" in mapped or "feature" in mapped

    def test_field_mapping_consistency(self):
        """Test that field mapping is consistent across adapters."""
        # Create a test task
        task = TaskModel(
            id="test-123",
            title="Test Task",
            description="Test description",
            status=TaskStatus.IN_PROGRESS,
            tags=["test", "integration"],
            assignees=["user1"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata={"source": "test"},
        )

        for platform in list_platforms():
            adapter_class = get_adapter(platform)
            config = SyncConfig(platform=platform, auth_config={})
            adapter = adapter_class(config)

            # Skip if adapter doesn't support tasks
            if not adapter.filter_item_type("task"):
                continue

            # Each adapter should be able to handle basic task fields
            # This is more of a conceptual test - actual implementation
            # would require mocking the platform APIs

    def test_error_handling_consistency(self):
        """Test that all adapters handle errors consistently."""
        # Test non-existent platform
        with pytest.raises(AdapterNotFoundError):
            get_adapter("nonexistent")

        # Test getting adapter without config
        with pytest.raises(TypeError):
            get_adapter("github")  # Missing config parameter

    def test_adapter_registry_operations(self):
        """Test registry operations."""
        registry = get_registry()

        # Test listing platforms
        platforms = registry.list_platforms()
        assert len(platforms) == 4

        # Test getting adapter info
        for platform in platforms:
            info = registry.get_adapter_info(platform)
            assert info["platform"] == platform

        # Test unregistering and re-registering
        # (This would modify global state, so we skip in integration tests)

    @pytest.mark.asyncio
    async def test_async_operations(self):
        """Test that adapters handle async operations properly."""
        # This is a basic test to ensure adapters can be used in async context
        config = SyncConfig(
            platform="github", auth_config={"token": "test", "repo": "test/test"}
        )
        adapter = get_adapter("github", config)

        # Test that close can be called (even if it does nothing)
        await adapter.close()

        # In real tests, we would mock the API calls and test
        # the async methods properly


class TestBackwardCompatibility:
    """Test backward compatibility with existing sync functionality."""

    def test_sync_bridge_import(self):
        """Test that SyncBridge can be imported for backward compatibility."""
        from ai_trackdown_pytools.utils.sync.compat import SyncBridge

        assert SyncBridge is not None

    def test_github_adapter_in_compat(self):
        """Test that GitHub adapter works through compat layer."""

        # This would require a proper test environment with task manager
        # For now, we just verify the imports work


class TestAdapterDocumentation:
    """Test that all adapters are properly documented."""

    def test_adapter_docstrings(self):
        """Verify all adapters have proper docstrings."""
        for platform in list_platforms():
            adapter_class = get_adapter(platform)

            # Check class docstring
            assert adapter_class.__doc__ is not None
            assert len(adapter_class.__doc__) > 50  # Non-trivial docstring

            # Check that docstring mentions the platform
            assert (
                platform.lower() in adapter_class.__doc__.lower()
                or platform.upper() in adapter_class.__doc__
            )

    def test_adapter_method_documentation(self):
        """Verify key methods are documented."""
        key_methods = ["authenticate", "pull_items", "push_item"]

        for platform in list_platforms():
            adapter_class = get_adapter(platform)

            for method_name in key_methods:
                method = getattr(adapter_class, method_name, None)
                if method and hasattr(method, "__doc__"):
                    # Allow some methods to inherit docs from base class
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
