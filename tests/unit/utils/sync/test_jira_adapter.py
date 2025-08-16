"""Unit tests for JIRA sync adapter."""

from datetime import date
from unittest.mock import Mock, patch

import pytest
from jira import JIRAError

from ai_trackdown_pytools.core.models import (
    BugModel,
    IssueModel,
    Priority,
    TaskModel,
    TaskStatus,
)
from ai_trackdown_pytools.utils.sync.base import SyncConfig
from ai_trackdown_pytools.utils.sync.exceptions import (
    AuthenticationError,
    ConfigurationError,
    RateLimitError,
)
from ai_trackdown_pytools.utils.sync.jira_adapter import JiraAdapter


class TestJiraAdapter:
    """Test suite for JIRA adapter.

    WHY: Comprehensive testing ensures the JIRA adapter handles all edge cases
    and integrates properly with the JIRA API. We mock the jira-python library
    to avoid actual API calls in unit tests.
    """

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SyncConfig(
            platform="jira",
            auth_config={
                "server": "https://example.atlassian.net",
                "email": "test@example.com",
                "api_token": "test-token",
                "project_key": "TEST",
            },
        )

    @pytest.fixture
    def adapter(self, config):
        """Create adapter instance."""
        return JiraAdapter(config)

    def test_platform_name(self, adapter):
        """Test platform name property."""
        assert adapter.platform_name == "jira"

    def test_supported_types(self, adapter):
        """Test supported types property."""
        assert adapter.supported_types == {"task", "issue", "bug", "epic"}

    def test_validate_config_missing_server(self, config):
        """Test config validation with missing server."""
        config.auth_config = {"email": "test@example.com", "api_token": "token"}
        adapter = JiraAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "JIRA server URL not provided" in str(exc_info.value)
        assert exc_info.value.platform == "jira"

    def test_validate_config_invalid_server_format(self, config):
        """Test config validation with invalid server URL."""
        config.auth_config["server"] = "invalid-url"
        adapter = JiraAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "Invalid server URL format" in str(exc_info.value)

    def test_validate_config_missing_auth(self, config):
        """Test config validation with missing authentication."""
        config.auth_config = {"server": "https://example.atlassian.net"}
        adapter = JiraAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "email and API token required" in str(exc_info.value)

    def test_validate_config_missing_project(self, config):
        """Test config validation with missing project key."""
        del config.auth_config["project_key"]
        adapter = JiraAdapter(config)

        with pytest.raises(ConfigurationError) as exc_info:
            adapter.validate_config()

        assert "project key not specified" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("ai_trackdown_pytools.utils.sync.jira_adapter.JIRA")
    async def test_authenticate_success(self, mock_jira_class, adapter):
        """Test successful authentication."""
        # Mock JIRA client
        mock_jira = Mock()
        mock_jira.current_user = Mock(return_value="test-user")
        mock_jira.fields = Mock(return_value=[])
        mock_jira_class.return_value = mock_jira

        await adapter.authenticate()

        assert adapter._authenticated is True
        assert adapter._jira_client == mock_jira

        # Verify JIRA client was created with correct params
        mock_jira_class.assert_called_once()
        call_args = mock_jira_class.call_args
        assert call_args[0] == ()  # No positional args
        assert call_args[1]["server"] == "https://example.atlassian.net"
        assert call_args[1]["basic_auth"] == ("test@example.com", "test-token")

    @pytest.mark.asyncio
    @patch("ai_trackdown_pytools.utils.sync.jira_adapter.JIRA")
    async def test_authenticate_invalid_credentials(self, mock_jira_class, adapter):
        """Test authentication with invalid credentials."""
        # Mock JIRA error
        error = JIRAError("Invalid credentials")
        error.status_code = 401
        mock_jira_class.side_effect = error

        with pytest.raises(AuthenticationError) as exc_info:
            await adapter.authenticate()

        assert "Invalid JIRA credentials" in str(exc_info.value)
        assert exc_info.value.platform == "jira"

    @pytest.mark.asyncio
    @patch("ai_trackdown_pytools.utils.sync.jira_adapter.JIRA")
    async def test_test_connection_success(self, mock_jira_class, adapter):
        """Test successful connection test."""
        # Mock JIRA client
        mock_jira = Mock()
        mock_jira.current_user = Mock(return_value="test-user")
        mock_jira.fields = Mock(return_value=[])
        mock_jira.project = Mock(return_value={"key": "TEST", "name": "Test Project"})
        mock_jira_class.return_value = mock_jira

        result = await adapter.test_connection()

        assert result is True
        mock_jira.project.assert_called_once_with("TEST")

    @pytest.mark.asyncio
    async def test_pull_items(self, adapter):
        """Test pulling items from JIRA."""
        # Mock JIRA client
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        # Mock JIRA issues
        mock_issue1 = Mock()
        mock_issue1.id = "10001"
        mock_issue1.key = "TEST-1"
        mock_issue1.fields = Mock(
            summary="Test Task",
            description="Test description",
            issuetype=Mock(name="Task"),
            status=Mock(name="To Do"),
            priority=Mock(name="Medium"),
            labels=["backend", "api"],
            assignee=Mock(emailAddress="dev@example.com", displayName="Developer"),
            created="2024-01-01T10:00:00.000+0000",
            updated="2024-01-02T10:00:00.000+0000",
            duedate="2024-01-15",
            timeoriginalestimate=7200,  # 2 hours in seconds
            project=Mock(key="TEST", name="Test Project"),
        )

        mock_issue2 = Mock()
        mock_issue2.id = "10002"
        mock_issue2.key = "TEST-2"
        mock_issue2.fields = Mock(
            summary="Test Bug",
            description="Bug description",
            issuetype=Mock(name="Bug"),
            status=Mock(name="In Progress"),
            priority=Mock(name="High"),
            labels=["bug", "critical"],
            assignee=None,
            created="2024-01-03T10:00:00.000+0000",
            updated="2024-01-04T10:00:00.000+0000",
            duedate=None,
            timeoriginalestimate=None,
            project=Mock(key="TEST", name="Test Project"),
        )

        # Mock search results
        mock_jira.search_issues = Mock(
            side_effect=[
                [mock_issue1, mock_issue2],  # First page
                [],  # No more results
            ]
        )

        items = await adapter.pull_items()

        assert len(items) == 2

        # Check first item (Task)
        task = items[0]
        assert isinstance(task, TaskModel)
        assert task.title == "Test Task"
        assert task.description == "Test description"
        assert task.status == TaskStatus.OPEN
        assert task.priority == Priority.MEDIUM
        assert "backend" in task.tags
        assert "api" in task.tags
        assert task.assignees == ["dev@example.com"]
        assert task.due_date == date(2024, 1, 15)
        assert task.estimated_hours == 2.0

        # Check second item (Bug)
        bug = items[1]
        assert isinstance(bug, BugModel)
        assert bug.title == "Test Bug"
        assert bug.status == TaskStatus.IN_PROGRESS
        assert bug.severity == "high"
        assert "bug" in bug.tags
        assert "critical" in bug.tags
        assert bug.assignees == []

    @pytest.mark.asyncio
    async def test_push_item_task(self, adapter):
        """Test pushing a task to JIRA."""
        # Mock JIRA client
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        # Mock created issue
        mock_created = Mock(
            id="10003", key="TEST-3", fields=Mock(status=Mock(name="To Do"))
        )
        mock_jira.create_issue = Mock(return_value=mock_created)
        mock_jira.transitions = Mock(return_value=[])

        # Create task to push
        task = TaskModel(
            id="TASK-001",
            title="New Task",
            description="Task description",
            status=TaskStatus.OPEN,
            priority=Priority.HIGH,
            tags=["feature", "frontend"],
            assignees=["dev@example.com"],
            due_date=date(2024, 2, 1),
            estimated_hours=5.0,
        )

        result = await adapter.push_item(task)

        assert result["remote_id"] == "10003"
        assert result["remote_key"] == "TEST-3"
        assert "browse/TEST-3" in result["remote_url"]

        # Verify create_issue was called with correct fields
        mock_jira.create_issue.assert_called_once()
        fields = mock_jira.create_issue.call_args[1]["fields"]
        assert fields["summary"] == "New Task"
        assert fields["description"] == "Task description"
        assert fields["project"]["key"] == "TEST"
        assert fields["issuetype"]["name"] == "Task"
        assert fields["priority"]["name"] == "High"
        assert fields["labels"] == ["feature", "frontend"]
        assert fields["duedate"] == "2024-02-01"
        assert fields["timeoriginalestimate"] == 18000  # 5 hours in seconds

    @pytest.mark.asyncio
    async def test_update_item(self, adapter):
        """Test updating an item in JIRA."""
        # Mock JIRA client and issue
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        mock_issue = Mock(
            id="10001", key="TEST-1", fields=Mock(status=Mock(name="To Do"))
        )
        mock_issue.update = Mock()
        mock_jira.issue = Mock(return_value=mock_issue)
        mock_jira.transitions = Mock(
            return_value=[
                {"id": "11", "to": {"name": "In Progress"}},
                {"id": "21", "to": {"name": "Done"}},
            ]
        )
        mock_jira.transition_issue = Mock()

        # Update task
        task = TaskModel(
            id="TASK-001",
            title="Updated Task",
            description="Updated description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.CRITICAL,
            tags=["urgent"],
            assignees=[],
        )

        result = await adapter.update_item(task, "TEST-1")

        assert result["remote_key"] == "TEST-1"

        # Verify update was called
        mock_issue.update.assert_called_once()
        fields = mock_issue.update.call_args[1]["fields"]
        assert fields["summary"] == "Updated Task"
        assert fields["description"] == "Updated description"
        assert fields["priority"]["name"] == "Highest"
        assert fields["labels"] == ["urgent"]
        assert fields["assignee"] is None  # Unassigned

        # Verify status transition
        mock_jira.transition_issue.assert_called_once_with(mock_issue, "11")

    @pytest.mark.asyncio
    async def test_delete_item_with_permission(self, adapter):
        """Test deleting an item with delete permission."""
        # Mock JIRA client
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        mock_issue = Mock()
        mock_issue.delete = Mock()
        mock_jira.issue = Mock(return_value=mock_issue)

        await adapter.delete_item("TEST-1")

        mock_issue.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_item_without_permission(self, adapter):
        """Test deleting an item without delete permission (fallback to transition)."""
        # Mock JIRA client
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        # Mock delete failure
        mock_issue = Mock()
        error = JIRAError("No permission")
        error.status_code = 403
        mock_issue.delete = Mock(side_effect=error)
        mock_jira.issue = Mock(return_value=mock_issue)

        # Mock transitions
        mock_jira.transitions = Mock(
            return_value=[
                {"id": "31", "name": "Cancel"},
                {"id": "41", "name": "Close"},
            ]
        )
        mock_jira.transition_issue = Mock()

        await adapter.delete_item("TEST-1")

        # Should try to transition instead
        mock_jira.transition_issue.assert_called_once_with(mock_issue, "31")

    @pytest.mark.asyncio
    async def test_get_item_exists(self, adapter):
        """Test getting an existing item."""
        # Mock JIRA client
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        # Mock issue
        mock_issue = Mock()
        mock_issue.id = "10001"
        mock_issue.key = "TEST-1"
        mock_issue.fields = Mock(
            summary="Test Issue",
            description="Issue description",
            issuetype=Mock(name="Issue"),
            status=Mock(name="Open"),
            priority=Mock(name="Medium"),
            labels=["backend"],
            assignee=None,
            created="2024-01-01T10:00:00.000+0000",
            updated="2024-01-02T10:00:00.000+0000",
            project=Mock(key="TEST", name="Test Project"),
        )

        mock_jira.issue = Mock(return_value=mock_issue)

        item = await adapter.get_item("TEST-1")

        assert item is not None
        assert isinstance(item, IssueModel)
        assert item.title == "Test Issue"
        assert item.metadata["jira_key"] == "TEST-1"

    @pytest.mark.asyncio
    async def test_get_item_not_found(self, adapter):
        """Test getting a non-existent item."""
        # Mock JIRA client
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        # Mock 404 error
        error = JIRAError("Not found")
        error.status_code = 404
        mock_jira.issue = Mock(side_effect=error)

        item = await adapter.get_item("TEST-999")

        assert item is None

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, adapter):
        """Test rate limit error handling."""
        # Mock JIRA client
        mock_jira = Mock()
        adapter._jira_client = mock_jira
        adapter._authenticated = True

        # Mock rate limit error
        error = JIRAError("Rate limit exceeded")
        error.status_code = 429
        error.response = Mock(headers={"Retry-After": "120"})
        mock_jira.search_issues = Mock(side_effect=error)

        with pytest.raises(RateLimitError) as exc_info:
            await adapter.pull_items()

        assert exc_info.value.platform == "jira"
        assert exc_info.value.retry_after == 120

    def test_status_mapping(self, adapter):
        """Test status mapping between internal and JIRA."""
        # Test to JIRA
        assert adapter.STATUS_TO_JIRA[TaskStatus.OPEN] == "To Do"
        assert adapter.STATUS_TO_JIRA[TaskStatus.IN_PROGRESS] == "In Progress"
        assert adapter.STATUS_TO_JIRA[TaskStatus.COMPLETED] == "Done"

        # Test from JIRA
        assert adapter.STATUS_FROM_JIRA["to do"] == TaskStatus.OPEN
        assert adapter.STATUS_FROM_JIRA["in progress"] == TaskStatus.IN_PROGRESS
        assert adapter.STATUS_FROM_JIRA["done"] == TaskStatus.COMPLETED
        assert adapter.STATUS_FROM_JIRA["blocked"] == TaskStatus.BLOCKED

    def test_priority_mapping(self, adapter):
        """Test priority mapping between internal and JIRA."""
        # Test to JIRA
        assert adapter.PRIORITY_TO_JIRA[Priority.CRITICAL] == "Highest"
        assert adapter.PRIORITY_TO_JIRA[Priority.HIGH] == "High"
        assert adapter.PRIORITY_TO_JIRA[Priority.MEDIUM] == "Medium"
        assert adapter.PRIORITY_TO_JIRA[Priority.LOW] == "Low"

        # Test from JIRA
        assert adapter.PRIORITY_FROM_JIRA["highest"] == Priority.CRITICAL
        assert adapter.PRIORITY_FROM_JIRA["high"] == Priority.HIGH
        assert adapter.PRIORITY_FROM_JIRA["medium"] == Priority.MEDIUM
        assert adapter.PRIORITY_FROM_JIRA["low"] == Priority.LOW
