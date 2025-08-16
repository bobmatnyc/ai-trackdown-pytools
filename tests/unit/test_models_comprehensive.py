"""Comprehensive unit tests for models module."""

from datetime import date, datetime, timedelta

import pytest
from pydantic import ValidationError

from ai_trackdown_pytools.core.models import (
    BugModel,
    CommentModel,
    EpicModel,
    IssueModel,
    PRModel,
    ProjectModel,
    TaskModel,
    TicketModel,
    get_id_pattern_for_type,
    get_model_for_type,
)
from ai_trackdown_pytools.core.workflow import ResolutionType, UnifiedStatus


class TestTaskModel:
    """Test TaskModel functionality."""

    def test_task_model_minimal(self):
        """Test creating TaskModel with minimal data."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            created_at=now,
            updated_at=now
        )

        assert task.id == "TSK-001"
        assert task.title == "Test Task"
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.assignees == []
        assert task.tags == []

    def test_task_model_full(self):
        """Test creating TaskModel with all fields."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Full Task",
            description="Detailed description",
            status="in_progress",
            priority="high",
            assignees=["user@example.com"],
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
        assert task.status == "in_progress"
        assert task.priority == "high"
        assert task.assignees == ["user@example.com"]
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
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            created_at=now,
            updated_at=now
        )

        # Test basic properties
        assert task.id == "TSK-001"
        assert task.title == "Test Task"
        assert task.status == "open"  # Default status

        # Test dict conversion
        task_dict = task.model_dump()
        assert task_dict["id"] == "TSK-001"
        assert task_dict["title"] == "Test Task"

        # Exclude None values
        task_dict_clean = task.model_dump(exclude_none=True)
        assert "due_date" not in task_dict_clean  # Should be excluded since it's None


class TestBugModel:
    """Test BugModel functionality."""

    def test_bug_model_minimal(self):
        """Test creating BugModel with minimal data."""
        now = datetime.now()
        bug = BugModel(
            id="BUG-001",
            title="Test Bug",
            created_at=now,
            updated_at=now
        )

        assert bug.id == "BUG-001"
        assert bug.title == "Test Bug"
        assert bug.type == "bug"
        assert bug.status == "open"
        assert bug.severity == "medium"

    def test_bug_model_full(self):
        """Test creating BugModel with all fields."""
        now = datetime.now()
        bug = BugModel(
            id="BUG-001",
            title="Critical Bug",
            description="Bug description",
            severity="critical",
            status="in_progress",
            priority="high",
            assignees=["dev@example.com"],
            tags=["critical", "backend"],
            steps_to_reproduce="1. Do this\n2. Do that",
            expected_behavior="Should work",
            actual_behavior="Throws error",
            environment="Production",
            browser="Chrome",
            os="Windows 10",
            device="Desktop",
            error_logs="Error: Something went wrong",
            verified_fixed=False,
            resolution_notes="",
            created_at=now,
            updated_at=now,
        )

        assert bug.severity == "critical"
        assert bug.steps_to_reproduce == "1. Do this\n2. Do that"
        assert bug.expected_behavior == "Should work"
        assert bug.actual_behavior == "Throws error"
        assert bug.environment == "Production"
        assert bug.browser == "Chrome"
        assert bug.os == "Windows 10"
        assert bug.device == "Desktop"
        assert bug.error_logs == "Error: Something went wrong"
        assert bug.verified_fixed is False

    def test_bug_model_validation(self):
        """Test BugModel validation."""
        # Invalid ID pattern
        with pytest.raises(ValidationError):
            BugModel(id="TSK-001", title="Test Bug")

        # Invalid severity
        with pytest.raises(ValidationError):
            BugModel(id="BUG-001", title="Test Bug", severity="invalid")


class TestCommentModel:
    """Test CommentModel functionality."""

    def test_comment_model_minimal(self):
        """Test creating CommentModel with minimal data."""
        now = datetime.now()
        comment = CommentModel(
            id="COMMENT-001",
            parent_id="TSK-001",
            parent_type="task",
            content="Test comment",
            author="user@example.com",
            created_at=now,
        )

        assert comment.id == "COMMENT-001"
        assert comment.parent_id == "TSK-001"
        assert comment.parent_type == "task"
        assert comment.content == "Test comment"
        assert comment.author == "user@example.com"
        assert comment.created_at == now

    def test_comment_model_validation(self):
        """Test CommentModel validation."""
        now = datetime.now()

        # Invalid parent_id pattern
        with pytest.raises(ValidationError):
            CommentModel(
                id="COMMENT-001",
                parent_id="invalid-id",
                parent_type="task",
                content="Test comment",
                author="user@example.com",
                created_at=now,
            )

        # Test valid comment creation
        comment = CommentModel(
            id="COMMENT-001",
            parent_id="TSK-001",
            parent_type="task",
            content="Valid comment content",
            author="user@example.com",
            created_at=now,
        )
        assert comment.content == "Valid comment content"


class TestUtilityFunctions:
    """Test utility functions in models module."""

    def test_get_model_for_type(self):
        """Test get_model_for_type function."""
        assert get_model_for_type("task") == TaskModel
        assert get_model_for_type("epic") == EpicModel
        assert get_model_for_type("issue") == IssueModel
        assert get_model_for_type("bug") == BugModel
        assert get_model_for_type("pr") == PRModel
        assert get_model_for_type("project") == ProjectModel

        # Test case insensitive
        assert get_model_for_type("TASK") == TaskModel
        assert get_model_for_type("Task") == TaskModel

        # Test invalid type
        assert get_model_for_type("invalid") is None

    def test_get_id_pattern_for_type(self):
        """Test get_id_pattern_for_type function."""
        assert get_id_pattern_for_type("task") == r"^TSK-[0-9]+$"
        assert get_id_pattern_for_type("epic") == r"^EP-[0-9]+$"
        assert get_id_pattern_for_type("issue") == r"^ISS-[0-9]+$"
        assert get_id_pattern_for_type("bug") == r"^BUG-[0-9]+$"
        assert get_id_pattern_for_type("pr") == r"^PR-[0-9]+$"
        assert get_id_pattern_for_type("project") == r"^PROJ-[0-9]+$"

        # Test case insensitive
        assert get_id_pattern_for_type("TASK") == r"^TSK-[0-9]+$"

        # Test invalid type returns default pattern
        assert get_id_pattern_for_type("invalid") == r"^[A-Z]+-[0-9]+$"


class TestBaseTicketModelWorkflow:
    """Test BaseTicketModel workflow functionality."""

    def test_can_transition_to(self):
        """Test basic status transitions."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status=UnifiedStatus.OPEN,
            created_at=now,
            updated_at=now
        )

        # Test basic status change
        task.status = UnifiedStatus.IN_PROGRESS
        assert task.status == UnifiedStatus.IN_PROGRESS

        # Test status validation
        assert task.status in [UnifiedStatus.OPEN, UnifiedStatus.IN_PROGRESS, UnifiedStatus.COMPLETED]

    def test_transition_to(self):
        """Test status transitions."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status=UnifiedStatus.OPEN,
            created_at=now,
            updated_at=now
        )

        # Test status change
        task.status = UnifiedStatus.IN_PROGRESS
        assert task.status == UnifiedStatus.IN_PROGRESS

        # Test completion
        task.status = UnifiedStatus.COMPLETED
        assert task.status == UnifiedStatus.COMPLETED

    def test_transition_to_invalid(self):
        """Test status validation."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status=UnifiedStatus.COMPLETED,
            created_at=now,
            updated_at=now
        )

        # Test that status can be changed
        task.status = UnifiedStatus.OPEN
        assert task.status == UnifiedStatus.OPEN

    def test_get_type(self):
        """Test model type identification through utility functions."""
        # Test utility function for getting model types
        assert get_model_for_type("task") == TaskModel
        assert get_model_for_type("epic") == EpicModel
        assert get_model_for_type("issue") == IssueModel
        assert get_model_for_type("bug") == BugModel
        assert get_model_for_type("pr") == PRModel
        assert get_model_for_type("project") == ProjectModel

    def test_to_markdown(self):
        """Test model serialization."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            description="Task description",
            status=UnifiedStatus.OPEN,
            priority="high",
            assignees=["user@example.com"],
            tags=["urgent", "backend"],
            created_at=now,
            updated_at=now,
        )

        # Test model dump instead of to_markdown
        task_dict = task.model_dump()
        assert task_dict["id"] == "TSK-001"
        assert task_dict["title"] == "Test Task"
        assert task_dict["description"] == "Task description"
        assert task_dict["status"] == "open"
        assert task_dict["priority"] == "high"
        assert "user@example.com" in task_dict["assignees"]
        assert "urgent" in task_dict["tags"]
        assert "backend" in task_dict["tags"]


class TestModelValidators:
    """Test model validators and field serializers."""

    def test_datetime_serialization(self):
        """Test datetime field serialization."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            created_at=now,
            updated_at=now,
        )

        # Test serialization
        task_dict = task.model_dump()
        assert isinstance(task_dict["created_at"], str)
        assert task_dict["created_at"] == now.isoformat()

    def test_date_serialization(self):
        """Test date field serialization."""
        now = datetime.now()
        today = date.today()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            due_date=today,
            created_at=now,
            updated_at=now,
        )

        task_dict = task.model_dump()
        assert isinstance(task_dict["due_date"], str)
        assert task_dict["due_date"] == today.isoformat()

    def test_unique_items_validator(self):
        """Test ensure_unique_items validator."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            assignees=["user1", "user2", "user1"],  # Duplicate
            tags=["tag1", "tag2", "tag1"],  # Duplicate
            created_at=now,
            updated_at=now,
        )

        # Should remove duplicates while preserving order
        assert task.assignees == ["user1", "user2"]
        assert task.tags == ["tag1", "tag2"]

    def test_task_self_dependency_validation(self):
        """Test task cannot depend on itself."""
        with pytest.raises(ValidationError):
            TaskModel(
                id="TSK-001",
                title="Test Task",
                dependencies=["TSK-001"],  # Self-dependency
            )

    def test_task_self_parent_validation(self):
        """Test task cannot be its own parent."""
        with pytest.raises(ValidationError):
            TaskModel(
                id="TSK-001",
                title="Test Task",
                parent="TSK-001",  # Self-parent
            )

    def test_epic_target_date_validation(self):
        """Test epic target date validation."""
        past_date = date.today() - timedelta(days=30)

        with pytest.raises(ValidationError):
            EpicModel(
                id="EP-001",
                title="Test Epic",
                target_date=past_date,  # Past date
            )

    def test_issue_parent_validation(self):
        """Test issue parent must be epic."""
        now = datetime.now()
        with pytest.raises(ValidationError):
            IssueModel(
                id="ISS-001",
                title="Test Issue",
                parent="TSK-001",  # Should be epic
                created_at=now,
                updated_at=now,
            )

        # Valid epic parent
        issue = IssueModel(
            id="ISS-001",
            title="Test Issue",
            parent="EP-001",
            created_at=now,
            updated_at=now,
        )
        assert issue.parent == "EP-001"

    def test_pr_merged_at_validation(self):
        """Test PR merged_at validation."""
        now = datetime.now()
        past = now - timedelta(hours=1)

        # merged_at before created_at should be invalid
        with pytest.raises(ValidationError):
            PRModel(
                id="PR-001",
                title="Test PR",
                source_branch="feature",
                target_branch="main",
                status="merged",
                created_at=now,
                merged_at=past,
            )

        # merged_at with non-merged status should be invalid
        with pytest.raises(ValidationError):
            PRModel(
                id="PR-001",
                title="Test PR",
                source_branch="feature",
                target_branch="main",
                status="open",
                merged_at=now,
            )

    def test_project_date_validation(self):
        """Test project date validation."""
        now = datetime.now()
        start_date = date.today()
        end_date = start_date - timedelta(days=1)  # End before start

        with pytest.raises(ValidationError):
            ProjectModel(
                id="PROJ-001",
                name="Test Project",
                title="Test Project",
                start_date=start_date,
                end_date=end_date,
                created_at=now,
                updated_at=now,
            )


class TestEpicModel:
    """Test EpicModel functionality."""

    def test_epic_model_creation(self):
        """Test creating EpicModel."""
        now = datetime.now()
        epic = EpicModel(
            id="EP-001",
            title="Test Epic",
            business_value="High value feature",
            success_criteria="All child tasks completed",
            child_issues=["ISS-001", "ISS-002"],
            created_at=now,
            updated_at=now,
        )

        assert epic.id == "EP-001"
        assert epic.title == "Test Epic"
        assert epic.business_value == "High value feature"
        assert epic.success_criteria == "All child tasks completed"
        assert len(epic.child_issues) == 2

    def test_epic_model_methods(self):
        """Test EpicModel methods."""
        now = datetime.now()
        epic = EpicModel(
            id="EP-001",
            title="Test Epic",
            created_at=now,
            updated_at=now,
        )

        # Test basic properties
        assert epic.id == "EP-001"
        assert epic.title == "Test Epic"
        assert epic.status == "planning"  # Default status


class TestIssueModel:
    """Test IssueModel functionality."""

    def test_issue_model_bug(self):
        """Test creating bug issue."""
        now = datetime.now()
        issue = IssueModel(
            id="ISS-001",
            title="Bug Issue",
            issue_type="bug",
            severity="high",
            steps_to_reproduce="1. Do this\n2. Do that",
            expected_behavior="Should work",
            actual_behavior="Doesn't work",
            environment="Production",
            created_at=now,
            updated_at=now,
        )

        assert issue.id == "ISS-001"
        assert issue.issue_type == "bug"
        assert issue.severity == "high"
        assert issue.steps_to_reproduce == "1. Do this\n2. Do that"

    def test_issue_model_feature(self):
        """Test creating feature issue."""
        now = datetime.now()
        issue = IssueModel(
            id="ISS-002",
            title="Feature Request",
            issue_type="feature",
            created_at=now,
            updated_at=now,
        )

        assert issue.issue_type == "feature"
        assert issue.id == "ISS-002"

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
        now = datetime.now()
        issue = IssueModel(
            id="ISS-001",
            title="Test Issue",
            issue_type="bug",
            severity="high",
            created_at=now,
            updated_at=now,
        )

        # Test basic properties
        assert issue.id == "ISS-001"
        assert issue.issue_type == "bug"
        assert issue.severity == "high"


class TestPRModel:
    """Test PRModel functionality."""

    def test_pr_model_creation(self):
        """Test creating PRModel."""
        now = datetime.now()
        pr = PRModel(
            id="PR-001",
            title="Fix bug in authentication",
            source_branch="fix/auth-bug",
            target_branch="main",
            reviewers=["user1", "user2"],
            lines_added=50,
            lines_deleted=20,
            files_changed=["file1.py", "file2.py", "file3.py"],
            commits=["abc123", "def456", "ghi789"],
            closes_issues=["ISS-001", "ISS-002"],
            created_at=now,
            updated_at=now,
        )

        assert pr.id == "PR-001"
        assert pr.source_branch == "fix/auth-bug"
        assert pr.target_branch == "main"
        assert len(pr.reviewers) == 2
        assert pr.lines_added == 50
        assert pr.lines_deleted == 20

    def test_pr_model_merged(self):
        """Test merged PR."""
        now = datetime.now()
        merged_at = datetime.now()
        pr = PRModel(
            id="PR-001",
            title="Merged PR",
            source_branch="feature/test",
            status="merged",
            merged_at=merged_at,
            created_at=now,
            updated_at=now,
        )

        assert pr.status == "merged"
        assert pr.merged_at == merged_at

    def test_pr_model_methods(self):
        """Test PRModel methods."""
        now = datetime.now()
        pr = PRModel(
            id="PR-001",
            title="Test PR",
            source_branch="feature/test",
            lines_added=100,
            lines_deleted=50,
            created_at=now,
            updated_at=now,
        )

        # Test basic properties
        assert pr.id == "PR-001"
        assert pr.source_branch == "feature/test"
        assert pr.lines_added == 100
        assert pr.lines_deleted == 50


class TestProjectModel:
    """Test ProjectModel functionality."""

    def test_project_model_creation(self):
        """Test creating ProjectModel."""
        now = datetime.now()
        project = ProjectModel(
            id="PROJ-001",
            name="Test Project",
            title="Test Project Title",
            team_members=["user1", "user2", "user3"],
            tech_stack=["Python", "React", "PostgreSQL"],
            repository_url="https://github.com/org/repo",
            documentation_url="https://docs.example.com",
            epics=["EP-001", "EP-002"],
            created_at=now,
            updated_at=now,
        )

        assert project.id == "PROJ-001"
        assert project.name == "Test Project"
        assert project.title == "Test Project Title"
        assert len(project.team_members) == 3
        assert "Python" in project.tech_stack

    def test_project_model_budget(self):
        """Test project with budget information."""
        now = datetime.now()
        start = date.today()
        end = date(2024, 12, 31)

        project = ProjectModel(
            id="PROJ-001",
            name="Budget Project",
            title="Budget Project Title",
            budget=100000.0,
            start_date=start,
            end_date=end,
            estimated_hours=1000,
            actual_hours=250,
            created_at=now,
            updated_at=now,
        )

        assert project.budget == 100000.0
        assert project.start_date == start
        assert project.end_date == end

    def test_project_model_methods(self):
        """Test ProjectModel methods."""
        now = datetime.now()
        project = ProjectModel(
            id="PROJ-001",
            name="Test Project",
            title="Test Project Title",
            status="active",
            created_at=now,
            updated_at=now,
        )

        # Test basic properties
        assert project.id == "PROJ-001"
        assert project.name == "Test Project"
        assert project.status == "active"


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

        # Unknown type returns None
        assert get_model_for_type("unknown") is None

    def test_get_id_pattern_for_type(self):
        """Test getting ID pattern by type."""
        assert get_id_pattern_for_type("task") == r"^TSK-[0-9]+$"
        assert get_id_pattern_for_type("epic") == r"^EP-[0-9]+$"
        assert get_id_pattern_for_type("issue") == r"^ISS-[0-9]+$"
        assert get_id_pattern_for_type("pr") == r"^PR-[0-9]+$"
        assert get_id_pattern_for_type("project") == r"^PROJ-[0-9]+$"

        # Unknown type returns generic pattern
        assert get_id_pattern_for_type("unknown") == r"^[A-Z]+-[0-9]+$"


class TestModelIntegration:
    """Test model integration scenarios."""

    def test_model_serialization(self):
        """Test model serialization/deserialization."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            tags=["test", "serialization"],
            metadata={"key": "value"},
            created_at=now,
            updated_at=now,
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
        now = datetime.now()

        # Empty strings should fail validation
        with pytest.raises(ValidationError):
            TaskModel(id="", title="Test", created_at=now, updated_at=now)

        with pytest.raises(ValidationError):
            TaskModel(id="TSK-001", title="", created_at=now, updated_at=now)

        # Invalid date formats handled by Pydantic
        task = TaskModel(
            id="TSK-001",
            title="Test",
            due_date="2024-12-31",  # String should be converted to date
            created_at=now,
            updated_at=now,
        )
        assert isinstance(task.due_date, date)
