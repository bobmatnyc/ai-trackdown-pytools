"""Unit tests for ClickUp sync adapter."""

from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_trackdown_pytools.core.models import (
    IssueModel,
    Priority,
    TaskModel,
    TaskStatus,
)
from ai_trackdown_pytools.utils.sync import SyncConfig
from ai_trackdown_pytools.utils.sync.clickup_adapter import ClickUpAdapter
from ai_trackdown_pytools.utils.sync.exceptions import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
)


@pytest.fixture
def valid_config():
    """Create a valid sync configuration for ClickUp."""
    return SyncConfig(
        platform="clickup",
        auth_config={
            "api_token": "test_token_123",
            "list_id": "test_list_123",
            "space_id": "test_space_123",
            "team_id": "test_team_123",
        },
    )


@pytest.fixture
def adapter(valid_config):
    """Create a ClickUp adapter instance."""
    return ClickUpAdapter(valid_config)


@pytest.fixture
def sample_task():
    """Create a sample TaskModel."""
    return TaskModel(
        id="TSK-001",
        title="Test Task",
        description="Test Description",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.HIGH,
        tags=["feature", "backend"],
        assignees=["user@example.com"],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        due_date=date.today(),
        estimated_hours=5.0,
    )


@pytest.fixture
def sample_clickup_task():
    """Create a sample ClickUp API response."""
    return {
        "id": "abc123",
        "name": "Test Task",
        "description": "Test Description",
        "status": {"status": "in progress"},
        "priority": {"priority": 2},
        "tags": [{"name": "feature"}, {"name": "backend"}],
        "assignees": [{"email": "user@example.com", "username": "user"}],
        "date_created": "1640995200000",  # 2022-01-01 in milliseconds
        "date_updated": "1640995200000",
        "due_date": "1641081600000",  # 2022-01-02 in milliseconds
        "time_estimate": 18000000,  # 5 hours in milliseconds
        "url": "https://app.clickup.com/t/abc123",
    }


class TestClickUpAdapter:
    """Test ClickUp adapter functionality."""

    def test_platform_name(self, adapter):
        """Test platform name property."""
        assert adapter.platform_name == "clickup"

    def test_supported_types(self, adapter):
        """Test supported types property."""
        assert adapter.supported_types == {"task", "issue"}

    def test_validate_config_missing_token(self):
        """Test config validation with missing API token."""
        config = SyncConfig(
            platform="clickup",
            auth_config={"list_id": "test_list"},
        )
        adapter = ClickUpAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "API token not provided" in str(exc_info.value)

    def test_validate_config_missing_list_id(self):
        """Test config validation with missing list ID."""
        config = SyncConfig(
            platform="clickup",
            auth_config={"api_token": "test_token"},
        )
        adapter = ClickUpAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "list ID not specified" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, adapter):
        """Test successful authentication."""
        with patch.object(adapter, "_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.get.return_value.__aenter__.return_value = mock_response

            await adapter.authenticate()

            assert adapter._authenticated is True

    @pytest.mark.asyncio
    async def test_authenticate_invalid_token(self, adapter):
        """Test authentication with invalid token."""
        # Mock aiohttp.ClientSession
        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create mock session and response
            mock_response = AsyncMock()
            mock_response.status = 401

            # Create async context manager for the response
            mock_get = AsyncMock()
            mock_get.__aenter__.return_value = mock_response
            mock_get.__aexit__.return_value = None

            # Create mock session with get method
            mock_session = MagicMock()
            mock_session.get.return_value = mock_get

            # Make ClientSession return our mock
            mock_session_class.return_value = mock_session

            with pytest.raises(AuthenticationError) as exc_info:
                await adapter.authenticate()

            assert "Invalid ClickUp API token" in str(exc_info.value)

    def test_clickup_task_to_model(self, adapter, sample_clickup_task):
        """Test converting ClickUp task to internal model."""
        model = adapter._clickup_task_to_model(sample_clickup_task)

        # ID will be generated from hash, so just check pattern
        assert model.id.startswith("TSK-")
        assert model.id[4:].isdigit()
        assert model.title == "Test Task"
        assert model.description == "Test Description"
        assert model.status == TaskStatus.IN_PROGRESS
        assert model.priority == Priority.HIGH
        assert model.tags == ["feature", "backend"]
        assert model.assignees == ["user@example.com"]
        assert model.metadata["clickup_id"] == "abc123"
        assert model.metadata["clickup_url"] == "https://app.clickup.com/t/abc123"
        assert model.estimated_hours == 5.0

    def test_clickup_task_to_issue_model(self, adapter, sample_clickup_task):
        """Test converting ClickUp task to IssueModel when it has bug tag."""
        sample_clickup_task["tags"].append({"name": "bug"})

        model = adapter._clickup_task_to_model(sample_clickup_task)

        assert isinstance(model, IssueModel)
        # ID will be generated from hash, so just check pattern
        assert model.id.startswith("ISS-")
        assert model.id[4:].isdigit()
        assert "bug" in model.tags

    def test_model_to_clickup_task(self, adapter, sample_task):
        """Test converting internal model to ClickUp format."""
        clickup_data = adapter._model_to_clickup_task(sample_task)

        assert clickup_data["name"] == "Test Task"
        assert clickup_data["description"] == "Test Description"
        assert clickup_data["status"] == "in progress"
        assert clickup_data["priority"] == 2
        assert clickup_data["tags"] == ["feature", "backend"]
        assert "due_date" in clickup_data
        assert clickup_data["time_estimate"] == 18000000  # 5 hours in milliseconds

    def test_status_mapping(self, adapter):
        """Test status mapping between internal and ClickUp."""
        # Test to ClickUp
        assert adapter.STATUS_TO_CLICKUP[TaskStatus.OPEN] == "open"
        assert adapter.STATUS_TO_CLICKUP[TaskStatus.IN_PROGRESS] == "in progress"
        assert adapter.STATUS_TO_CLICKUP[TaskStatus.COMPLETED] == "complete"
        assert adapter.STATUS_TO_CLICKUP[TaskStatus.CANCELLED] == "closed"
        assert adapter.STATUS_TO_CLICKUP[TaskStatus.BLOCKED] == "blocked"

        # Test from ClickUp
        assert adapter.STATUS_FROM_CLICKUP["open"] == TaskStatus.OPEN
        assert adapter.STATUS_FROM_CLICKUP["in progress"] == TaskStatus.IN_PROGRESS
        assert adapter.STATUS_FROM_CLICKUP["complete"] == TaskStatus.COMPLETED
        assert adapter.STATUS_FROM_CLICKUP["closed"] == TaskStatus.CANCELLED
        assert adapter.STATUS_FROM_CLICKUP["blocked"] == TaskStatus.BLOCKED

    def test_priority_mapping(self, adapter):
        """Test priority mapping between internal and ClickUp."""
        # Test to ClickUp
        assert adapter.PRIORITY_TO_CLICKUP[Priority.CRITICAL] == 1
        assert adapter.PRIORITY_TO_CLICKUP[Priority.HIGH] == 2
        assert adapter.PRIORITY_TO_CLICKUP[Priority.MEDIUM] == 3
        assert adapter.PRIORITY_TO_CLICKUP[Priority.LOW] == 4

        # Test from ClickUp
        assert adapter.PRIORITY_FROM_CLICKUP[1] == Priority.CRITICAL
        assert adapter.PRIORITY_FROM_CLICKUP[2] == Priority.HIGH
        assert adapter.PRIORITY_FROM_CLICKUP[3] == Priority.MEDIUM
        assert adapter.PRIORITY_FROM_CLICKUP[4] == Priority.LOW
        assert adapter.PRIORITY_FROM_CLICKUP[None] == Priority.MEDIUM

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, adapter):
        """Test rate limit error handling."""
        adapter._authenticated = True

        with patch.object(adapter, "_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_session.get.return_value.__aenter__.return_value = mock_response

            with pytest.raises(RateLimitError) as exc_info:
                await adapter.pull_items()

            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_pull_items_with_date_filter(self, adapter, sample_clickup_task):
        """Test pulling items with date filter."""
        adapter._authenticated = True
        since = datetime(2022, 1, 1)

        with patch.object(adapter, "_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {}
            mock_response.json = AsyncMock(
                return_value={"tasks": [sample_clickup_task]}
            )
            mock_session.get.return_value.__aenter__.return_value = mock_response

            items = await adapter.pull_items(since=since)

            # Verify the request was made with date filter
            mock_session.get.assert_called()
            call_args = mock_session.get.call_args
            assert "params" in call_args[1]
            assert "date_updated_gt" in call_args[1]["params"]
            assert call_args[1]["params"]["date_updated_gt"] == int(
                since.timestamp() * 1000
            )

            # Verify the result
            assert len(items) == 1
            assert items[0].id.startswith("TSK-")

    @pytest.mark.asyncio
    async def test_push_item_success(self, adapter, sample_task):
        """Test successful item push."""
        adapter._authenticated = True

        with patch.object(adapter, "_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.headers = {}
            mock_response.json = AsyncMock(
                return_value={
                    "id": "new_task_id",
                    "url": "https://app.clickup.com/t/new_task_id",
                }
            )
            mock_session.post.return_value.__aenter__.return_value = mock_response

            result = await adapter.push_item(sample_task)

            assert result["remote_id"] == "new_task_id"
            assert result["remote_url"] == "https://app.clickup.com/t/new_task_id"

    @pytest.mark.asyncio
    async def test_close_session(self, adapter):
        """Test closing the HTTP session."""
        mock_session = AsyncMock()
        adapter._session = mock_session

        await adapter.close()

        mock_session.close.assert_called_once()
        assert adapter._session is None
