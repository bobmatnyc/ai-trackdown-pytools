"""Unit tests for sync adapter system."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import pytest

from ai_trackdown_pytools.core.models import TaskModel, TaskStatus
from ai_trackdown_pytools.utils.sync import (
    AdapterNotFoundError,
    AdapterRegistry,
    ConfigurationError,
    SyncAdapter,
    SyncConfig,
    SyncDirection,
    SyncResult,
    get_adapter,
    register_adapter,
)
from ai_trackdown_pytools.utils.sync.base import TicketModel
from ai_trackdown_pytools.utils.sync.registry import list_platforms


class MockAdapter(SyncAdapter):
    """Mock adapter for testing."""

    @property
    def platform_name(self) -> str:
        return "mock"

    @property
    def supported_types(self) -> Set[str]:
        return {"task", "issue"}

    async def authenticate(self) -> None:
        if not self.config.auth_config.get("token"):
            raise ConfigurationError(
                "Missing token", platform=self.platform_name, missing_fields=["token"]
            )
        self._authenticated = True

    async def test_connection(self) -> bool:
        return self._authenticated

    async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
        if not self._authenticated:
            raise Exception("Not authenticated")

        # Return mock data
        return [
            TaskModel(
                id="TSK-001",
                title="Mock Task",
                description="Test task",
                status=TaskStatus.OPEN,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"mock_id": "mock-123"},
            )
        ]

    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        if not self._authenticated:
            raise Exception("Not authenticated")

        return {
            "remote_id": "mock-new-123",
            "remote_url": "https://mock.com/items/mock-new-123",
        }

    async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
        if not self._authenticated:
            raise Exception("Not authenticated")

        return {
            "remote_id": remote_id,
            "remote_url": f"https://mock.com/items/{remote_id}",
        }

    async def delete_item(self, remote_id: str) -> None:
        if not self._authenticated:
            raise Exception("Not authenticated")
        pass

    async def get_item(self, remote_id: str) -> Optional[TicketModel]:
        if not self._authenticated:
            raise Exception("Not authenticated")

        if remote_id == "mock-123":
            return TaskModel(
                id="TSK-001",
                title="Mock Task",
                description="Test task",
                status=TaskStatus.OPEN,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"mock_id": remote_id},
            )
        return None


class TestSyncConfig:
    """Test SyncConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SyncConfig(platform="test")

        assert config.platform == "test"
        assert config.direction == SyncDirection.BIDIRECTIONAL
        assert config.dry_run is False
        assert config.batch_size == 50
        assert config.sync_tags is True
        assert config.sync_assignees is True

    def test_config_validation(self):
        """Test configuration validation."""
        # Should raise error if types are both included and excluded
        with pytest.raises(ValueError, match="cannot be both included and excluded"):
            SyncConfig(
                platform="test",
                included_types={"task", "issue"},
                excluded_types={"issue", "bug"},
            )

    def test_custom_config(self):
        """Test custom configuration."""
        config = SyncConfig(
            platform="test",
            direction=SyncDirection.PULL,
            dry_run=True,
            auth_config={"token": "secret"},
            label_mapping={"bug": "defect"},
            batch_size=100,
        )

        assert config.direction == SyncDirection.PULL
        assert config.dry_run is True
        assert config.auth_config["token"] == "secret"
        assert config.label_mapping["bug"] == "defect"
        assert config.batch_size == 100


class TestSyncResult:
    """Test SyncResult dataclass."""

    def test_success_result(self):
        """Test successful sync result."""
        result = SyncResult(
            platform="test", direction=SyncDirection.PUSH, started_at=datetime.now()
        )

        result.items_processed = 10
        result.items_created = 5
        result.items_updated = 5
        result.completed_at = datetime.now()

        assert result.success is True
        assert result.duration is not None
        assert result.duration > 0

    def test_failed_result(self):
        """Test failed sync result."""
        result = SyncResult(
            platform="test", direction=SyncDirection.PULL, started_at=datetime.now()
        )

        result.add_error("item-1", ValueError("Test error"), {"field": "value"})
        result.completed_at = datetime.now()

        assert result.success is False
        assert result.items_failed == 1
        assert len(result.errors) == 1
        assert result.errors[0]["item_id"] == "item-1"
        assert result.errors[0]["error_type"] == "ValueError"


class TestAdapterRegistry:
    """Test adapter registry functionality."""

    def test_register_adapter(self):
        """Test adapter registration."""
        registry = AdapterRegistry()
        registry.register("test", MockAdapter)

        assert registry.is_registered("test")
        assert "test" in registry.list_platforms()

    def test_register_duplicate(self):
        """Test registering duplicate adapter."""
        registry = AdapterRegistry()
        registry.register("test", MockAdapter)

        with pytest.raises(ValueError, match="already registered"):
            registry.register("test", MockAdapter)

    def test_register_invalid_adapter(self):
        """Test registering invalid adapter."""
        registry = AdapterRegistry()

        # Not a class
        with pytest.raises(ValueError, match="must be a class"):
            registry.register("test", "not a class")

        # Not a SyncAdapter subclass
        class NotAnAdapter:
            pass

        with pytest.raises(ValueError, match="must inherit from SyncAdapter"):
            registry.register("test", NotAnAdapter)

    def test_get_adapter(self):
        """Test getting adapter instance."""
        registry = AdapterRegistry()
        registry.register("test", MockAdapter)

        config = SyncConfig(platform="test", auth_config={"token": "test"})
        adapter = registry.get_adapter("test", config)

        assert isinstance(adapter, MockAdapter)
        assert adapter.config == config

    def test_get_nonexistent_adapter(self):
        """Test getting non-existent adapter."""
        registry = AdapterRegistry()
        config = SyncConfig(platform="unknown")

        with pytest.raises(AdapterNotFoundError) as exc_info:
            registry.get_adapter("unknown", config)

        assert "unknown" in str(exc_info.value)

    def test_unregister_adapter(self):
        """Test unregistering adapter."""
        registry = AdapterRegistry()
        registry.register("test", MockAdapter)

        assert registry.is_registered("test")

        registry.unregister("test")

        assert not registry.is_registered("test")

    def test_get_adapter_info(self):
        """Test getting adapter information."""
        registry = AdapterRegistry()
        registry.register("test", MockAdapter)

        info = registry.get_adapter_info("test")

        assert info["platform"] == "test"
        assert info["class_name"] == "MockAdapter"
        assert "task" in info["supported_types"]
        assert "issue" in info["supported_types"]


class TestSyncAdapter:
    """Test sync adapter base functionality."""

    @pytest.mark.asyncio
    async def test_authenticate(self):
        """Test adapter authentication."""
        config = SyncConfig(platform="mock", auth_config={"token": "test"})
        adapter = MockAdapter(config)

        assert adapter._authenticated is False

        await adapter.authenticate()

        assert adapter._authenticated is True
        assert await adapter.test_connection() is True

    @pytest.mark.asyncio
    async def test_authenticate_missing_config(self):
        """Test authentication with missing config."""
        config = SyncConfig(platform="mock", auth_config={})
        adapter = MockAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            await adapter.authenticate()

        assert "Missing token" in str(exc_info.value)
        assert exc_info.value.missing_fields == ["token"]

    def test_status_mapping(self):
        """Test status mapping functionality."""
        config = SyncConfig(
            platform="mock",
            status_mapping={
                "open": "todo",
                "in_progress": "doing",
                "completed": "done",
            },
        )
        adapter = MockAdapter(config)

        # Map to external
        assert adapter.map_status("open", to_external=True) == "todo"
        assert adapter.map_status("in_progress", to_external=True) == "doing"
        assert adapter.map_status("unknown", to_external=True) == "unknown"

        # Map from external
        assert adapter.map_status("todo", to_external=False) == "open"
        assert adapter.map_status("doing", to_external=False) == "in_progress"
        assert adapter.map_status("unknown", to_external=False) == "unknown"

    def test_label_mapping(self):
        """Test label mapping functionality."""
        config = SyncConfig(
            platform="mock", label_mapping={"bug": "defect", "feature": "enhancement"}
        )
        adapter = MockAdapter(config)

        # Map to external
        labels = adapter.map_labels(["bug", "feature", "other"], to_external=True)
        assert labels == ["defect", "enhancement", "other"]

        # Map from external
        labels = adapter.map_labels(
            ["defect", "enhancement", "other"], to_external=False
        )
        assert labels == ["bug", "feature", "other"]

    def test_filter_item_type(self):
        """Test item type filtering."""
        # Test with included types
        config = SyncConfig(platform="mock", included_types={"task", "issue"})
        adapter = MockAdapter(config)

        assert adapter.filter_item_type("task") is True
        assert adapter.filter_item_type("issue") is True
        assert adapter.filter_item_type("bug") is False

        # Test with excluded types
        config = SyncConfig(platform="mock", excluded_types={"bug", "pr"})
        adapter = MockAdapter(config)

        assert adapter.filter_item_type("task") is True
        assert adapter.filter_item_type("issue") is True
        assert adapter.filter_item_type("bug") is False
        assert adapter.filter_item_type("pr") is False

        # Test with no filtering
        config = SyncConfig(platform="mock")
        adapter = MockAdapter(config)

        assert adapter.filter_item_type("anything") is True


class TestModuleFunctions:
    """Test module-level functions."""

    def test_global_registry(self):
        """Test global registry functions."""
        # Clear any existing registrations
        from ai_trackdown_pytools.utils.sync.registry import _default_registry

        _default_registry._adapters.clear()

        # Register adapter
        register_adapter("global_test", MockAdapter)

        # Get adapter
        config = SyncConfig(platform="global_test", auth_config={"token": "test"})
        adapter = get_adapter("global_test", config)

        assert isinstance(adapter, MockAdapter)
        assert "global_test" in list_platforms()
