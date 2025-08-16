"""Unit tests for Linear sync adapter."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from gql.transport.exceptions import TransportError

from ai_trackdown_pytools.core.models import Priority, TaskModel, TaskStatus
from ai_trackdown_pytools.utils.sync import SyncConfig, SyncDirection
from ai_trackdown_pytools.utils.sync.exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    RateLimitError,
)
from ai_trackdown_pytools.utils.sync.linear_adapter import LinearAdapter


class TestLinearAdapter:
    """Test suite for Linear adapter.

    WHY: Comprehensive testing ensures the Linear adapter correctly handles
    GraphQL operations, error conditions, and data mapping between Linear
    and our internal models.
    """

    @pytest.fixture
    def config(self):
        """Create test sync configuration."""
        return SyncConfig(
            platform="linear",
            direction=SyncDirection.BIDIRECTIONAL,
            auth_config={
                "api_key": "test_api_key",
                "team_id": "test_team_id",
                "project_id": "test_project_id",
            },
        )

    @pytest.fixture
    def adapter(self, config):
        """Create Linear adapter instance."""
        return LinearAdapter(config)

    def test_platform_name(self, adapter):
        """Test platform name property."""
        assert adapter.platform_name == "linear"

    def test_supported_types(self, adapter):
        """Test supported ticket types."""
        assert adapter.supported_types == {"task", "issue", "bug"}

    def test_validate_config_missing_api_key(self):
        """Test configuration validation with missing API key."""
        config = SyncConfig(platform="linear", auth_config={"team_id": "test_team"})
        adapter = LinearAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "API key not provided" in str(exc_info.value)
        assert exc_info.value.missing_fields == ["api_key"]

    def test_validate_config_missing_team_id(self):
        """Test configuration validation with missing team ID."""
        config = SyncConfig(platform="linear", auth_config={"api_key": "test_key"})
        adapter = LinearAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "team ID not specified" in str(exc_info.value)
        assert exc_info.value.missing_fields == ["team_id"]

    @pytest.mark.asyncio
    async def test_authenticate_success(self, adapter):
        """Test successful authentication."""
        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.AIOHTTPTransport"):
            with patch(
                "ai_trackdown_pytools.utils.sync.linear_adapter.Client"
            ) as mock_client:
                # Mock successful authentication
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(
                    return_value={
                        "viewer": {
                            "id": "user_id",
                            "email": "test@example.com",
                            "name": "Test User",
                        }
                    }
                )
                mock_client.return_value.__aenter__.return_value = mock_session
                mock_client.return_value.__aexit__.return_value = None

                # Mock workflow states fetch
                mock_session.execute.side_effect = [
                    # First call: authentication
                    {
                        "viewer": {
                            "id": "user_id",
                            "email": "test@example.com",
                            "name": "Test User",
                        }
                    },
                    # Second call: workflow states
                    {
                        "team": {
                            "states": {
                                "nodes": [
                                    {"id": "state1", "name": "Todo", "type": "started"},
                                    {
                                        "id": "state2",
                                        "name": "In Progress",
                                        "type": "started",
                                    },
                                    {
                                        "id": "state3",
                                        "name": "Done",
                                        "type": "completed",
                                    },
                                ]
                            }
                        }
                    },
                ]

                await adapter.authenticate()

                assert adapter._authenticated is True
                assert adapter._workflow_states == {
                    "Todo": "state1",
                    "In Progress": "state2",
                    "Done": "state3",
                }

    @pytest.mark.asyncio
    async def test_authenticate_invalid_key(self, adapter):
        """Test authentication with invalid API key."""
        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.AIOHTTPTransport"):
            with patch(
                "ai_trackdown_pytools.utils.sync.linear_adapter.Client"
            ) as mock_client:
                # Mock 401 error
                mock_session = AsyncMock()
                mock_session.execute = AsyncMock(
                    side_effect=TransportError("401 Unauthorized")
                )
                mock_client.return_value.__aenter__.return_value = mock_session
                mock_client.return_value.__aexit__.return_value = None

                with pytest.raises(AuthenticationError) as exc_info:
                    await adapter.authenticate()

                assert "Invalid Linear API key" in str(exc_info.value)
                assert exc_info.value.auth_method == "api_key"

    @pytest.mark.asyncio
    async def test_test_connection_success(self, adapter):
        """Test successful connection test."""
        adapter._authenticated = True
        adapter._client = Mock()

        with patch(
            "ai_trackdown_pytools.utils.sync.linear_adapter.Client"
        ) as mock_client:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value={"organization": {"id": "org_id", "name": "Test Org"}}
            )
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            result = await adapter.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_test_connection_not_authenticated(self, adapter):
        """Test connection test when not authenticated."""
        with pytest.raises(ConnectionError) as exc_info:
            await adapter.test_connection()

        assert "Not authenticated with Linear" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_pull_items_with_pagination(self, adapter):
        """Test pulling items with pagination."""
        adapter._authenticated = True
        adapter._client = Mock()
        adapter._team_id = "test_team"

        # Mock Linear issue data
        issue1 = {
            "id": "issue1",
            "identifier": "LIN-1",
            "title": "Test Issue 1",
            "description": "Description 1",
            "priority": 2,
            "priorityLabel": "High",
            "state": {"id": "state1", "name": "In Progress", "type": "started"},
            "assignee": {"id": "user1", "email": "user1@example.com", "name": "User 1"},
            "labels": {"nodes": [{"id": "label1", "name": "bug"}]},
            "project": {"id": "proj1", "name": "Project 1"},
            "cycle": None,
            "estimate": 5,
            "dueDate": "2024-12-31",
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-02T00:00:00.000Z",
            "url": "https://linear.app/test/issue/LIN-1",
        }

        issue2 = {
            "id": "issue2",
            "identifier": "LIN-2",
            "title": "Test Issue 2",
            "description": "Description 2",
            "priority": 0,
            "priorityLabel": "No priority",
            "state": {"id": "state2", "name": "Todo", "type": "unstarted"},
            "assignee": None,
            "labels": {"nodes": []},
            "project": None,
            "cycle": None,
            "estimate": None,
            "dueDate": None,
            "createdAt": "2024-01-03T00:00:00.000Z",
            "updatedAt": "2024-01-04T00:00:00.000Z",
            "url": "https://linear.app/test/issue/LIN-2",
        }

        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.Client"):
            mock_session = AsyncMock()
            # First page
            mock_session.execute = AsyncMock(
                side_effect=[
                    {
                        "issues": {
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor1"},
                            "nodes": [issue1],
                        }
                    },
                    # Second page
                    {
                        "issues": {
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                            "nodes": [issue2],
                        }
                    },
                ]
            )
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            items = await adapter.pull_items()

            assert len(items) == 2

            # Check first item
            assert items[0].id == "TASK-LIN-1"
            assert items[0].title == "Test Issue 1"
            assert items[0].status == TaskStatus.IN_PROGRESS
            assert items[0].priority == Priority.HIGH
            assert items[0].assignees == ["user1@example.com"]
            assert "bug" in items[0].tags

            # Check second item
            assert items[1].id == "TASK-LIN-2"
            assert items[1].title == "Test Issue 2"
            assert items[1].status == TaskStatus.OPEN
            assert items[1].priority == Priority.MEDIUM
            assert items[1].assignees == []

    @pytest.mark.asyncio
    async def test_pull_items_rate_limit(self, adapter):
        """Test handling rate limit during pull."""
        adapter._authenticated = True
        adapter._client = Mock()

        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.Client"):
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                side_effect=TransportError("429 Too Many Requests")
            )
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            with pytest.raises(RateLimitError) as exc_info:
                await adapter.pull_items()

            assert "rate limit exceeded" in str(exc_info.value)
            assert exc_info.value.retry_after == 60

    @pytest.mark.asyncio
    async def test_push_item_success(self, adapter):
        """Test successful item push."""
        adapter._authenticated = True
        adapter._client = Mock()
        adapter._team_id = "test_team"

        task = TaskModel(
            id="TASK-001",
            title="New Task",
            description="Task description",
            status=TaskStatus.OPEN,
            priority=Priority.HIGH,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.Client"):
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value={
                    "issueCreate": {
                        "success": True,
                        "issue": {
                            "id": "linear_id_123",
                            "identifier": "LIN-123",
                            "url": "https://linear.app/test/issue/LIN-123",
                        },
                    }
                }
            )
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            result = await adapter.push_item(task)

            assert result["remote_id"] == "linear_id_123"
            assert result["remote_key"] == "LIN-123"
            assert result["linear_identifier"] == "LIN-123"

    @pytest.mark.asyncio
    async def test_update_item_success(self, adapter):
        """Test successful item update."""
        adapter._authenticated = True
        adapter._client = Mock()

        task = TaskModel(
            id="TASK-001",
            title="Updated Task",
            description="Updated description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.MEDIUM,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.Client"):
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value={
                    "issueUpdate": {
                        "success": True,
                        "issue": {
                            "id": "linear_id_123",
                            "identifier": "LIN-123",
                            "url": "https://linear.app/test/issue/LIN-123",
                        },
                    }
                }
            )
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            result = await adapter.update_item(task, "linear_id_123")

            assert result["remote_id"] == "linear_id_123"
            assert result["linear_identifier"] == "LIN-123"

    @pytest.mark.asyncio
    async def test_delete_item_success(self, adapter):
        """Test successful item deletion (archiving)."""
        adapter._authenticated = True
        adapter._client = Mock()

        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.Client"):
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value={"issueArchive": {"success": True}}
            )
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            # Should not raise exception
            await adapter.delete_item("linear_id_123")

    @pytest.mark.asyncio
    async def test_get_item_found(self, adapter):
        """Test retrieving a single item."""
        adapter._authenticated = True
        adapter._client = Mock()

        issue_data = {
            "id": "issue1",
            "identifier": "LIN-1",
            "title": "Test Issue",
            "description": "Description",
            "priority": 3,
            "priorityLabel": "Medium",
            "state": {"id": "state1", "name": "Todo", "type": "unstarted"},
            "assignee": None,
            "labels": {"nodes": []},
            "project": None,
            "cycle": None,
            "estimate": None,
            "dueDate": None,
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-02T00:00:00.000Z",
            "url": "https://linear.app/test/issue/LIN-1",
        }

        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.Client"):
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value={"issue": issue_data})
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            item = await adapter.get_item("issue1")

            assert item is not None
            assert item.title == "Test Issue"
            assert item.status == TaskStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_item_not_found(self, adapter):
        """Test retrieving non-existent item."""
        adapter._authenticated = True
        adapter._client = Mock()

        with patch("ai_trackdown_pytools.utils.sync.linear_adapter.Client"):
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value={"issue": None})
            adapter._client.__aenter__.return_value = mock_session
            adapter._client.__aexit__.return_value = None

            item = await adapter.get_item("nonexistent")

            assert item is None

    def test_status_mapping(self, adapter):
        """Test status mapping configuration."""
        # Test forward mapping
        assert "Todo" in adapter.STATUS_TO_LINEAR[TaskStatus.OPEN]
        assert "In Progress" in adapter.STATUS_TO_LINEAR[TaskStatus.IN_PROGRESS]
        assert "Done" in adapter.STATUS_TO_LINEAR[TaskStatus.COMPLETED]

        # Test reverse mapping
        assert adapter.LINEAR_TO_STATUS["todo"] == TaskStatus.OPEN
        assert adapter.LINEAR_TO_STATUS["in progress"] == TaskStatus.IN_PROGRESS
        assert adapter.LINEAR_TO_STATUS["done"] == TaskStatus.COMPLETED

    def test_priority_mapping(self, adapter):
        """Test priority mapping configuration."""
        # Test forward mapping
        assert adapter.PRIORITY_TO_LINEAR[Priority.CRITICAL] == 1
        assert adapter.PRIORITY_TO_LINEAR[Priority.HIGH] == 2
        assert adapter.PRIORITY_TO_LINEAR[Priority.MEDIUM] == 3
        assert adapter.PRIORITY_TO_LINEAR[Priority.LOW] == 4

        # Test reverse mapping
        assert adapter.PRIORITY_FROM_LINEAR[1] == Priority.CRITICAL
        assert adapter.PRIORITY_FROM_LINEAR[0] == Priority.MEDIUM  # No priority
