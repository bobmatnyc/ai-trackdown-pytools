"""Comprehensive unit tests for models module."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from ai_trackdown_pytools.core.models import (
    EpicModel,
    IssueModel,
    PRModel,
    ProjectModel,
    TaskModel,
    TicketModel,
    get_id_pattern_for_type,
    get_model_for_type,
)


class TestTaskModel:
    """Test TaskModel functionality."""

    def test_task_model_minimal(self):
        """Test creating TaskModel with minimal data."""
        task = TaskModel(id="TSK-001", title="Test Task")

        assert task.id == "TSK-001"
        assert task.title == "Test Task"
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.assignee is None
        assert task.tags == []

    def test_task_model_full(self):
        """Test creating TaskModel with all fields."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Full Task",
            description="Detailed description",
            status="in-progress",
            priority="high",
            assignee="user@example.com",
            tags=["backend", "urgent"],
            parent="EP-001",
            dependencies=["TSK-002", "TSK-003"],
            metadata={"custom": "value"},
            created_at=now,
            updated_at=now,
            due_date=date.today(),
            estimated_hours=8.5,
            actual_hours=5.0,
        )

        assert task.id == "TSK-001"
        assert task.title == "Full Task"
        assert task.description == "Detailed description"
        assert task.status == "in-progress"
        assert task.priority == "high"
        assert task.assignee == "user@example.com"
        assert task.tags == ["backend", "urgent"]
        assert task.parent == "EP-001"
        assert task.dependencies == ["TSK-002", "TSK-003"]
        assert task.metadata == {"custom": "value"}
        assert task.due_date == date.today()
        assert task.estimated_hours == 8.5
        assert task.actual_hours == 5.0

    def test_task_model_validation(self):
        """Test TaskModel validation."""
        # Invalid status
        with pytest.raises(ValidationError) as exc_info:
            TaskModel(id="TSK-001", title="Test", status="invalid-status")
        assert "status" in str(exc_info.value)

        # Invalid priority
        with pytest.raises(ValidationError) as exc_info:
            TaskModel(id="TSK-001", title="Test", priority="super-high")
        assert "priority" in str(exc_info.value)

    def test_task_model_methods(self):
        """Test TaskModel methods."""
        task = TaskModel(id="TSK-001", title="Test Task")

        # Test get_type
        assert task.get_type() == "task"

        # Test to_markdown
        markdown = task.to_markdown()
        assert "# Test Task" in markdown
        assert "TSK-001" in markdown
        assert "Status: open" in markdown

        # Test dict conversion
        task_dict = task.model_dump()
        assert task_dict["id"] == "TSK-001"
        assert task_dict["title"] == "Test Task"

        # Exclude None values
        task_dict_clean = task.model_dump(exclude_none=True)
        assert "assignee" not in task_dict_clean
        assert "parent" not in task_dict_clean


class TestEpicModel:
    """Test EpicModel functionality."""

    def test_epic_model_creation(self):
        """Test creating EpicModel."""
        epic = EpicModel(
            id="EP-001",
            title="Test Epic",
            business_value="High value feature",
            success_criteria="All child tasks completed",
            child_issues=["ISS-001", "ISS-002"],
            child_tasks=["TSK-001", "TSK-002", "TSK-003"],
        )

        assert epic.id == "EP-001"
        assert epic.title == "Test Epic"
        assert epic.business_value == "High value feature"
        assert epic.success_criteria == "All child tasks completed"
        assert len(epic.child_issues) == 2
        assert len(epic.child_tasks) == 3

    def test_epic_model_methods(self):
        """Test EpicModel methods."""
        epic = EpicModel(
            id="EP-001", title="Test Epic", child_tasks=["TSK-001", "TSK-002"]
        )

        assert epic.get_type() == "epic"

        markdown = epic.to_markdown()
        assert "# Test Epic" in markdown
        assert "## Child Tasks" in markdown
        assert "- TSK-001" in markdown


class TestIssueModel:
    """Test IssueModel functionality."""

    def test_issue_model_bug(self):
        """Test creating bug issue."""
        issue = IssueModel(
            id="ISS-001",
            title="Bug Issue",
            issue_type="bug",
            severity="high",
            steps_to_reproduce="1. Do this\n2. Do that",
            expected_behavior="Should work",
            actual_behavior="Doesn't work",
            environment="Production",
        )

        assert issue.id == "ISS-001"
        assert issue.issue_type == "bug"
        assert issue.severity == "high"
        assert issue.steps_to_reproduce == "1. Do this\n2. Do that"

    def test_issue_model_feature(self):
        """Test creating feature issue."""
        issue = IssueModel(
            id="ISS-002",
            title="Feature Request",
            issue_type="feature",
            acceptance_criteria="Must have X, Y, Z",
        )

        assert issue.issue_type == "feature"
        assert issue.acceptance_criteria == "Must have X, Y, Z"

    def test_issue_model_validation(self):
        """Test IssueModel validation."""
        # Invalid issue type
        with pytest.raises(ValidationError):
            IssueModel(id="ISS-001", title="Test", issue_type="invalid-type")

        # Invalid severity
        with pytest.raises(ValidationError):
            IssueModel(
                id="ISS-001", title="Test", issue_type="bug", severity="super-critical"
            )

    def test_issue_model_methods(self):
        """Test IssueModel methods."""
        issue = IssueModel(
            id="ISS-001", title="Test Issue", issue_type="bug", severity="high"
        )

        assert issue.get_type() == "issue"

        markdown = issue.to_markdown()
        assert "Type: bug" in markdown
        assert "Severity: high" in markdown


class TestPRModel:
    """Test PRModel functionality."""

    def test_pr_model_creation(self):
        """Test creating PRModel."""
        pr = PRModel(
            id="PR-001",
            title="Fix bug in authentication",
            branch="fix/auth-bug",
            base_branch="main",
            reviewers=["user1", "user2"],
            lines_added=50,
            lines_deleted=20,
            files_changed=3,
            commits=5,
            closes_issues=["ISS-001", "ISS-002"],
        )

        assert pr.id == "PR-001"
        assert pr.branch == "fix/auth-bug"
        assert pr.base_branch == "main"
        assert len(pr.reviewers) == 2
        assert pr.lines_added == 50
        assert pr.lines_deleted == 20

    def test_pr_model_merged(self):
        """Test merged PR."""
        merged_at = datetime.now()
        pr = PRModel(
            id="PR-001",
            title="Merged PR",
            status="merged",
            merged_at=merged_at,
            merge_commit="abc123",
        )

        assert pr.status == "merged"
        assert pr.merged_at == merged_at
        assert pr.merge_commit == "abc123"

    def test_pr_model_methods(self):
        """Test PRModel methods."""
        pr = PRModel(
            id="PR-001",
            title="Test PR",
            branch="feature/test",
            lines_added=100,
            lines_deleted=50,
        )

        assert pr.get_type() == "pr"

        markdown = pr.to_markdown()
        assert "Branch: feature/test" in markdown
        assert "Lines: +100 -50" in markdown


class TestProjectModel:
    """Test ProjectModel functionality."""

    def test_project_model_creation(self):
        """Test creating ProjectModel."""
        project = ProjectModel(
            id="PROJ-001",
            name="Test Project",
            code="TP",
            team_members=["user1", "user2", "user3"],
            tech_stack=["Python", "React", "PostgreSQL"],
            repository_url="https://github.com/org/repo",
            documentation_url="https://docs.example.com",
            epics=["EP-001", "EP-002"],
            milestones=["v1.0", "v2.0"],
        )

        assert project.id == "PROJ-001"
        assert project.name == "Test Project"
        assert project.code == "TP"
        assert len(project.team_members) == 3
        assert "Python" in project.tech_stack

    def test_project_model_budget(self):
        """Test project with budget information."""
        start = date.today()
        end = date(2024, 12, 31)

        project = ProjectModel(
            id="PROJ-001",
            name="Budget Project",
            budget=100000.0,
            budget_spent=25000.0,
            start_date=start,
            end_date=end,
            estimated_hours=1000,
            actual_hours=250,
        )

        assert project.budget == 100000.0
        assert project.budget_spent == 25000.0
        assert project.start_date == start
        assert project.end_date == end

    def test_project_model_methods(self):
        """Test ProjectModel methods."""
        project = ProjectModel(id="PROJ-001", name="Test Project", status="active")

        assert project.get_type() == "project"

        markdown = project.to_markdown()
        assert "# Test Project" in markdown
        assert "Status: active" in markdown


class TestTicketModel:
    """Test base TicketModel functionality."""

    def test_ticket_model_abstract(self):
        """Test that TicketModel is abstract."""
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            TicketModel(id="TEST-001", title="Test")

    def test_ticket_model_subclass(self):
        """Test TicketModel subclassing."""
        # All model classes should inherit from TicketModel
        assert issubclass(TaskModel, TicketModel)
        assert issubclass(EpicModel, TicketModel)
        assert issubclass(IssueModel, TicketModel)
        assert issubclass(PRModel, TicketModel)
        assert issubclass(ProjectModel, TicketModel)


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_model_for_type(self):
        """Test getting model class by type."""
        assert get_model_for_type("task") == TaskModel
        assert get_model_for_type("epic") == EpicModel
        assert get_model_for_type("issue") == IssueModel
        assert get_model_for_type("pr") == PRModel
        assert get_model_for_type("project") == ProjectModel

        # Unknown type
        with pytest.raises(ValueError) as exc_info:
            get_model_for_type("unknown")
        assert "Unknown ticket type" in str(exc_info.value)

    def test_get_id_pattern_for_type(self):
        """Test getting ID pattern by type."""
        assert get_id_pattern_for_type("task") == r"^TSK-\d+$"
        assert get_id_pattern_for_type("epic") == r"^EP-\d+$"
        assert get_id_pattern_for_type("issue") == r"^ISS-\d+$"
        assert get_id_pattern_for_type("pr") == r"^PR-\d+$"
        assert get_id_pattern_for_type("project") == r"^PROJ-\d+$"

        # Unknown type returns generic pattern
        assert get_id_pattern_for_type("unknown") == r"^[A-Z]+-\d+$"


class TestModelIntegration:
    """Test model integration scenarios."""

    def test_task_epic_relationship(self):
        """Test task-epic parent-child relationship."""
        epic = EpicModel(
            id="EP-001", title="Parent Epic", child_tasks=["TSK-001", "TSK-002"]
        )

        task = TaskModel(id="TSK-001", title="Child Task", parent="EP-001")

        assert task.parent == epic.id
        assert task.id in epic.child_tasks

    def test_pr_issue_relationship(self):
        """Test PR closing issues."""
        issue1 = IssueModel(id="ISS-001", title="Bug 1", issue_type="bug")
        issue2 = IssueModel(id="ISS-002", title="Bug 2", issue_type="bug")

        pr = PRModel(
            id="PR-001", title="Fix bugs", closes_issues=["ISS-001", "ISS-002"]
        )

        assert issue1.id in pr.closes_issues
        assert issue2.id in pr.closes_issues

    def test_model_serialization(self):
        """Test model serialization/deserialization."""
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            tags=["test", "serialization"],
            metadata={"key": "value"},
        )

        # Serialize to dict
        task_dict = task.model_dump()

        # Deserialize back
        task2 = TaskModel(**task_dict)

        assert task2.id == task.id
        assert task2.title == task.title
        assert task2.tags == task.tags
        assert task2.metadata == task.metadata

    def test_model_validation_edge_cases(self):
        """Test model validation edge cases."""
        # Empty strings
        with pytest.raises(ValidationError):
            TaskModel(id="", title="Test")

        with pytest.raises(ValidationError):
            TaskModel(id="TSK-001", title="")

        # Invalid date formats handled by Pydantic
        task = TaskModel(
            id="TSK-001",
            title="Test",
            due_date="2024-12-31",  # String should be converted to date
        )
        assert isinstance(task.due_date, date)
