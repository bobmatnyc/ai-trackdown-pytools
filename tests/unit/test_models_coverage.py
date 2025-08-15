"""Unit tests for models module to increase coverage."""

from datetime import datetime, timedelta

from ai_trackdown_pytools.core.models import (
    BaseTicketModel,
    BugModel,
    CommentModel,
    EpicModel,
    IssueModel,
    IssueStatus,
    MilestoneModel,
    Priority,
    PRModel,
    ProjectModel,
    TaskModel,
    TaskStatus,
)


class TestModelsCoverage:
    """Test cases to increase models coverage."""

    def test_task_model_basic(self):
        """Test basic TaskModel creation."""
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            description="A test task",
            status="open",
            priority="medium",
        )

        assert task.id == "TSK-001"
        assert task.title == "Test Task"
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.ticket_type == "task"

    def test_task_model_with_dates(self):
        """Test TaskModel with date fields."""
        now = datetime.now()
        due = now + timedelta(days=7)

        task = TaskModel(
            id="TSK-002",
            title="Task with dates",
            created_at=now,
            updated_at=now,
            due_date=due,
        )

        assert task.created_at == now
        assert task.updated_at == now
        assert task.due_date == due

    def test_task_model_with_hours(self):
        """Test TaskModel with hour tracking."""
        task = TaskModel(
            id="TSK-003", title="Task with hours", estimated_hours=8.0, actual_hours=6.5
        )

        assert task.estimated_hours == 8.0
        assert task.actual_hours == 6.5

    def test_task_model_validation(self):
        """Test TaskModel validation."""
        # Test with valid statuses
        task = TaskModel(id="TSK-004", title="Valid task", status="open")
        assert task.status == "open"

        # Test priority validation
        task2 = TaskModel(id="TSK-005", title="Priority task", priority="high")
        assert task2.priority == "high"

    def test_issue_model_basic(self):
        """Test basic IssueModel creation."""
        issue = IssueModel(
            id="ISS-001",
            title="Test Issue",
            description="A test issue",
            status="open",
            priority="high",
        )

        assert issue.id == "ISS-001"
        assert issue.title == "Test Issue"
        assert issue.ticket_type == "issue"

    def test_issue_model_with_resolution(self):
        """Test IssueModel with resolution."""
        issue = IssueModel(
            id="ISS-002", title="Resolved Issue", status="closed", resolution="fixed"
        )

        assert issue.resolution == "fixed"
        assert issue.status == "closed"

    def test_issue_model_with_tasks(self):
        """Test IssueModel with related tasks."""
        issue = IssueModel(
            id="ISS-003",
            title="Issue with tasks",
            tasks=["TSK-001", "TSK-002", "TSK-003"],
        )

        assert len(issue.tasks) == 3
        assert "TSK-001" in issue.tasks

    def test_epic_model_basic(self):
        """Test basic EpicModel creation."""
        epic = EpicModel(
            id="EP-001",
            title="Test Epic",
            description="A test epic",
            status="open",
            priority="high",
        )

        assert epic.id == "EP-001"
        assert epic.title == "Test Epic"
        assert epic.ticket_type == "epic"

    def test_epic_model_with_issues(self):
        """Test EpicModel with related issues."""
        epic = EpicModel(
            id="EP-002",
            title="Epic with issues",
            issues=["ISS-001", "ISS-002", "ISS-003"],
        )

        assert len(epic.issues) == 3
        assert "ISS-001" in epic.issues

    def test_comment_model(self):
        """Test CommentModel creation."""
        now = datetime.now()
        comment = CommentModel(
            id="CMT-001",
            content="This is a test comment",
            author="test_user",
            created_at=now,
            updated_at=now,
        )

        assert comment.id == "CMT-001"
        assert comment.content == "This is a test comment"
        assert comment.author == "test_user"

    def test_bug_model(self):
        """Test BugModel creation."""
        bug = BugModel(
            id="BUG-001",
            title="Test Bug",
            description="A test bug",
            status="open",
            priority="high",
            severity="major",
        )

        assert bug.id == "BUG-001"
        assert bug.ticket_type == "bug"
        assert bug.severity == "major"

    def test_milestone_model(self):
        """Test MilestoneModel creation."""
        now = datetime.now()
        milestone = MilestoneModel(
            id="M-001",
            title="Version 1.0",
            description="First release",
            due_date=now + timedelta(days=30),
            created_at=now,
        )

        assert milestone.id == "M-001"
        assert milestone.title == "Version 1.0"

    def test_task_status_enum(self):
        """Test TaskStatus enum."""
        assert TaskStatus.OPEN.value == "open"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.CLOSED.value == "closed"
        assert TaskStatus.BLOCKED.value == "blocked"

    def test_priority_enum(self):
        """Test Priority enum."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"

    def test_issue_status_enum(self):
        """Test IssueStatus enum."""
        assert IssueStatus.OPEN.value == "open"
        assert IssueStatus.IN_PROGRESS.value == "in_progress"
        assert IssueStatus.RESOLVED.value == "resolved"
        assert IssueStatus.CLOSED.value == "closed"

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        task = TaskModel(
            id="TSK-006",
            title="Serialization test",
            tags=["python", "testing"],
            assignees=["user1", "user2"],
        )

        # Test model_dump
        data = task.model_dump(mode="json")
        assert data["id"] == "TSK-006"
        assert data["tags"] == ["python", "testing"]
        assert isinstance(data["created_at"], str)  # Datetime serialized to string

    def test_model_field_defaults(self):
        """Test model field defaults."""
        task = TaskModel(id="TSK-007", title="Default test")

        # Check defaults
        assert task.description == ""
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.tags == []
        assert task.assignees == []
        assert task.dependencies == []
        assert task.metadata == {}

    def test_model_metadata(self):
        """Test model metadata field."""
        metadata = {
            "custom_field": "value",
            "another_field": 123,
            "nested": {"key": "value"},
        }

        task = TaskModel(id="TSK-008", title="Metadata test", metadata=metadata)

        assert task.metadata["custom_field"] == "value"
        assert task.metadata["another_field"] == 123
        assert task.metadata["nested"]["key"] == "value"

    def test_pr_model(self):
        """Test PRModel creation."""
        pr = PRModel(
            id="PR-001",
            title="Fix bug in login",
            description="Fixes issue #123",
            status="open",
            source_branch="fix/login-bug",
            target_branch="main",
        )

        assert pr.id == "PR-001"
        assert pr.source_branch == "fix/login-bug"
        assert pr.target_branch == "main"

    def test_project_model(self):
        """Test ProjectModel creation."""
        project = ProjectModel(
            id="PROJ-001",
            title="AI Trackdown",
            description="Project management tool",
            status="active",
        )

        assert project.id == "PROJ-001"
        assert project.status == "active"

    def test_base_ticket_model_inheritance(self):
        """Test BaseTicketModel inheritance."""
        # All ticket types should inherit from BaseTicketModel
        task = TaskModel(id="T-1", title="Task")
        assert isinstance(task, BaseTicketModel)

        issue = IssueModel(id="I-1", title="Issue")
        assert isinstance(issue, BaseTicketModel)

        epic = EpicModel(id="E-1", title="Epic")
        assert isinstance(epic, BaseTicketModel)
