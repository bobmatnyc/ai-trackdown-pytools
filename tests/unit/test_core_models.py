"""Unit tests for core data models."""

from datetime import date, datetime, timedelta

import pytest

from ai_trackdown_pytools.core.models import (
    EpicModel,
    IssueModel,
    PRModel,
    ProjectModel,
    TaskModel,
)


class TestBaseModel:
    """Test BaseModel functionality."""

    def test_id_pattern_validation(self):
        """Test ID pattern validation for different ticket types."""
        now = datetime.now()

        # Valid task ID
        task = TaskModel(
            id="TSK-0001",
            title="Test Task",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        )
        assert task.id == "TSK-0001"

        # Invalid task ID should raise validation error
        with pytest.raises(Exception):
            TaskModel(
                id="INVALID-001",
                title="Test Task",
                status="open",
                priority="medium",
                created_at=now,
                updated_at=now,
            )

    def test_timestamp_validation(self):
        """Test timestamp validation."""
        now = datetime.now()
        past = now - timedelta(days=1)

        # updated_at should be >= created_at
        task = TaskModel(
            id="TSK-0001",
            title="Test Task",
            status="open",
            priority="medium",
            created_at=past,
            updated_at=now,
        )
        assert task.created_at == past
        assert task.updated_at == now

        # Invalid: updated_at < created_at
        with pytest.raises(Exception):
            TaskModel(
                id="TSK-0002",
                title="Test Task",
                status="open",
                priority="medium",
                created_at=now,
                updated_at=past,
            )

    def test_tag_validation(self):
        """Test tag validation."""
        now = datetime.now()

        # Valid tags
        task = TaskModel(
            id="TSK-0001",
            title="Test Task",
            status="open",
            priority="medium",
            tags=["bug", "frontend", "urgent"],
            created_at=now,
            updated_at=now,
        )
        assert "bug" in task.tags
        assert len(task.tags) == 3

        # Empty tags should be allowed
        task_no_tags = TaskModel(
            id="TSK-0002",
            title="Test Task",
            status="open",
            priority="medium",
            tags=[],
            created_at=now,
            updated_at=now,
        )
        assert task_no_tags.tags == []

    def test_assignee_validation(self):
        """Test assignee validation."""
        now = datetime.now()

        # Valid assignees
        task = TaskModel(
            id="TSK-0001",
            title="Test Task",
            status="open",
            priority="medium",
            assignees=["alice", "bob"],
            created_at=now,
            updated_at=now,
        )
        assert "alice" in task.assignees
        assert len(task.assignees) == 2


class TestTaskModel:
    """Test TaskModel-specific functionality."""

    def setup_method(self):
        """Setup test data."""
        self.now = datetime.now()
        self.base_task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
            "created_at": self.now,
            "updated_at": self.now,
        }

    def test_minimal_task_creation(self):
        """Test creating task with minimal required fields."""
        task = TaskModel(**self.base_task_data)

        assert task.id == "TSK-0001"
        assert task.title == "Test Task"
        assert task.status == "open"
        assert task.priority == "medium"
        assert task.description == ""
        assert task.assignees == []
        assert task.tags == []

    def test_full_task_creation(self):
        """Test creating task with all fields."""
        task_data = {
            **self.base_task_data,
            "description": "Detailed task description",
            "assignees": ["alice", "bob"],
            "tags": ["bug", "frontend"],
            "parent": "EP-0001",
            "dependencies": ["TSK-0002"],
            "estimated_hours": 8.5,
            "actual_hours": 6.0,
            "due_date": date.today() + timedelta(days=7),
        }

        task = TaskModel(**task_data)

        assert task.description == "Detailed task description"
        assert task.assignees == ["alice", "bob"]
        assert task.tags == ["bug", "frontend"]
        assert task.parent == "EP-0001"
        assert task.dependencies == ["TSK-0002"]
        assert task.estimated_hours == 8.5
        assert task.actual_hours == 6.0
        assert task.due_date is not None

    def test_status_validation(self):
        """Test task status validation."""
        # Valid statuses
        for status in ["open", "in_progress", "blocked", "completed", "cancelled"]:
            task_data = {**self.base_task_data, "status": status}
            task = TaskModel(**task_data)
            assert task.status == status

        # Invalid status
        with pytest.raises(Exception):
            TaskModel(**{**self.base_task_data, "status": "invalid_status"})

    def test_priority_validation(self):
        """Test task priority validation."""
        # Valid priorities
        for priority in ["low", "medium", "high", "critical"]:
            task_data = {**self.base_task_data, "priority": priority}
            task = TaskModel(**task_data)
            assert task.priority == priority

        # Invalid priority
        with pytest.raises(Exception):
            TaskModel(**{**self.base_task_data, "priority": "invalid_priority"})

    def test_estimated_hours_validation(self):
        """Test estimated hours validation."""
        # Valid estimated hours
        task_data = {**self.base_task_data, "estimated_hours": 8.0}
        task = TaskModel(**task_data)
        assert task.estimated_hours == 8.0

        # Negative hours should be invalid
        with pytest.raises(Exception):
            TaskModel(**{**self.base_task_data, "estimated_hours": -1.0})

    def test_dependency_validation(self):
        """Test dependency validation."""
        # Valid dependencies
        task_data = {**self.base_task_data, "dependencies": ["TSK-0002", "TSK-0003"]}
        task = TaskModel(**task_data)
        assert "TSK-0002" in task.dependencies

        # Self-dependency should be handled by validation layer
        # (Model allows it, but validation layer should catch it)
        task_data = {**self.base_task_data, "dependencies": ["TSK-0001"]}
        task = TaskModel(**task_data)
        assert "TSK-0001" in task.dependencies


class TestEpicModel:
    """Test EpicModel-specific functionality."""

    def setup_method(self):
        """Setup test data."""
        self.now = datetime.now()
        self.base_epic_data = {
            "id": "EP-0001",
            "title": "Test Epic",
            "status": "planning",
            "priority": "high",
            "created_at": self.now,
            "updated_at": self.now,
        }

    def test_minimal_epic_creation(self):
        """Test creating epic with minimal required fields."""
        epic = EpicModel(**self.base_epic_data)

        assert epic.id == "EP-0001"
        assert epic.title == "Test Epic"
        assert epic.status == "planning"
        assert epic.priority == "high"

    def test_full_epic_creation(self):
        """Test creating epic with all fields."""
        epic_data = {
            **self.base_epic_data,
            "description": "Epic description",
            "goal": "Achieve specific objective",
            "business_value": "High customer value",
            "success_criteria": "All acceptance criteria met",
            "target_date": date.today() + timedelta(days=30),
            "child_issues": ["ISS-0001", "ISS-0002"],
            "child_tasks": ["TSK-0001", "TSK-0002"],
        }

        epic = EpicModel(**epic_data)

        assert epic.goal == "Achieve specific objective"
        assert epic.business_value == "High customer value"
        assert epic.success_criteria == "All acceptance criteria met"
        assert epic.target_date is not None
        assert "ISS-0001" in epic.child_issues
        assert "TSK-0001" in epic.child_tasks

    def test_epic_status_validation(self):
        """Test epic status validation."""
        # Valid epic statuses
        for status in ["planning", "in_progress", "on_hold", "completed", "cancelled"]:
            epic_data = {**self.base_epic_data, "status": status}
            epic = EpicModel(**epic_data)
            assert epic.status == status

    def test_target_date_validation(self):
        """Test target date validation."""
        # Future date should be valid
        future_date = date.today() + timedelta(days=30)
        epic_data = {**self.base_epic_data, "target_date": future_date}
        epic = EpicModel(**epic_data)
        assert epic.target_date == future_date

        # Past date should raise validation error
        past_date = date.today() - timedelta(days=30)
        with pytest.raises(Exception):
            EpicModel(**{**self.base_epic_data, "target_date": past_date})


class TestIssueModel:
    """Test IssueModel-specific functionality."""

    def setup_method(self):
        """Setup test data."""
        self.now = datetime.now()
        self.base_issue_data = {
            "id": "ISS-0001",
            "title": "Test Issue",
            "issue_type": "bug",
            "status": "open",
            "priority": "high",
            "created_at": self.now,
            "updated_at": self.now,
        }

    def test_bug_issue_creation(self):
        """Test creating bug issue."""
        issue_data = {
            **self.base_issue_data,
            "severity": "critical",
            "steps_to_reproduce": "1. Do this\n2. Do that",
            "expected_behavior": "Should work correctly",
            "actual_behavior": "Throws error",
            "environment": "Production",
        }

        issue = IssueModel(**issue_data)

        assert issue.issue_type == "bug"
        assert issue.severity == "critical"
        assert issue.steps_to_reproduce == "1. Do this\n2. Do that"
        assert issue.expected_behavior == "Should work correctly"
        assert issue.actual_behavior == "Throws error"
        assert issue.environment == "Production"

    def test_feature_request_creation(self):
        """Test creating feature request."""
        issue_data = {
            **self.base_issue_data,
            "issue_type": "feature_request",
            "user_story": "As a user, I want to...",
            "acceptance_criteria": "Given... When... Then...",
            "business_value": "Increases user engagement",
        }

        issue = IssueModel(**issue_data)

        assert issue.issue_type == "feature_request"
        assert issue.user_story == "As a user, I want to..."
        assert issue.acceptance_criteria == "Given... When... Then..."
        assert issue.business_value == "Increases user engagement"

    def test_issue_type_validation(self):
        """Test issue type validation."""
        # Valid issue types
        for issue_type in [
            "bug",
            "feature_request",
            "enhancement",
            "task",
            "documentation",
        ]:
            issue_data = {**self.base_issue_data, "issue_type": issue_type}
            issue = IssueModel(**issue_data)
            assert issue.issue_type == issue_type

    def test_severity_validation(self):
        """Test severity validation."""
        # Valid severities
        for severity in ["low", "medium", "high", "critical"]:
            issue_data = {**self.base_issue_data, "severity": severity}
            issue = IssueModel(**issue_data)
            assert issue.severity == severity


class TestPRModel:
    """Test PRModel-specific functionality."""

    def setup_method(self):
        """Setup test data."""
        self.now = datetime.now()
        self.base_pr_data = {
            "id": "PR-0001",
            "title": "Test PR",
            "pr_type": "feature",
            "status": "draft",
            "priority": "medium",
            "source_branch": "feature/test",
            "target_branch": "main",
            "created_at": self.now,
            "updated_at": self.now,
        }

    def test_feature_pr_creation(self):
        """Test creating feature PR."""
        pr_data = {
            **self.base_pr_data,
            "description": "Adds new feature",
            "changes_summary": "Added new API endpoint",
            "testing_notes": "Tested with unit tests",
            "breaking_changes": False,
            "related_issues": ["ISS-0001"],
        }

        pr = PRModel(**pr_data)

        assert pr.pr_type == "feature"
        assert pr.source_branch == "feature/test"
        assert pr.target_branch == "main"
        assert pr.breaking_changes is False
        assert "ISS-0001" in pr.related_issues

    def test_breaking_change_pr(self):
        """Test creating breaking change PR."""
        pr_data = {
            **self.base_pr_data,
            "pr_type": "breaking_change",
            "breaking_changes": True,
            "breaking_change_description": "Changes API signature",
        }

        pr = PRModel(**pr_data)

        assert pr.pr_type == "breaking_change"
        assert pr.breaking_changes is True
        assert pr.breaking_change_description == "Changes API signature"

    def test_pr_type_validation(self):
        """Test PR type validation."""
        # Valid PR types
        for pr_type in [
            "feature",
            "bugfix",
            "hotfix",
            "refactor",
            "breaking_change",
            "documentation",
        ]:
            pr_data = {**self.base_pr_data, "pr_type": pr_type}
            pr = PRModel(**pr_data)
            assert pr.pr_type == pr_type

    def test_pr_status_validation(self):
        """Test PR status validation."""
        # Valid PR statuses
        for status in ["draft", "open", "approved", "merged", "closed", "cancelled"]:
            pr_data = {**self.base_pr_data, "status": status}
            pr = PRModel(**pr_data)
            assert pr.status == status


class TestProjectModel:
    """Test ProjectModel-specific functionality."""

    def setup_method(self):
        """Setup test data."""
        self.now = datetime.now()
        self.base_project_data = {
            "id": "PROJ-0001",
            "name": "Test Project",
            "status": "active",
            "priority": "high",
            "created_at": self.now,
            "updated_at": self.now,
        }

    def test_project_creation(self):
        """Test creating project."""
        project_data = {
            **self.base_project_data,
            "description": "Test project description",
            "repository": "https://github.com/test/project",
            "team_members": ["alice", "bob", "charlie"],
            "start_date": date.today(),
            "target_completion": date.today() + timedelta(days=90),
        }

        project = ProjectModel(**project_data)

        assert project.name == "Test Project"
        assert project.description == "Test project description"
        assert project.repository == "https://github.com/test/project"
        assert len(project.team_members) == 3
        assert "alice" in project.team_members

    def test_project_status_validation(self):
        """Test project status validation."""
        # Valid project statuses
        for status in ["planning", "active", "on_hold", "completed", "cancelled"]:
            project_data = {**self.base_project_data, "status": status}
            project = ProjectModel(**project_data)
            assert project.status == status

    def test_date_validation(self):
        """Test project date validation."""
        start_date = date.today()
        target_date = start_date + timedelta(days=90)

        project_data = {
            **self.base_project_data,
            "start_date": start_date,
            "target_completion": target_date,
        }

        project = ProjectModel(**project_data)
        assert project.start_date == start_date
        assert project.target_completion == target_date

        # Invalid: target_completion before start_date
        with pytest.raises(Exception):
            ProjectModel(
                **{
                    **self.base_project_data,
                    "start_date": target_date,
                    "target_completion": start_date,
                }
            )


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_task_json_serialization(self):
        """Test task JSON serialization."""
        now = datetime.now()
        task = TaskModel(
            id="TSK-0001",
            title="Test Task",
            status="open",
            priority="medium",
            created_at=now,
            updated_at=now,
        )

        # Test dict conversion
        task_dict = task.model_dump()
        assert task_dict["id"] == "TSK-0001"
        assert task_dict["title"] == "Test Task"

        # Test JSON serialization
        task_json = task.model_dump_json()
        assert '"id":"TSK-0001"' in task_json

        # Test deserialization
        new_task = TaskModel.model_validate(task_dict)
        assert new_task.id == task.id
        assert new_task.title == task.title

    def test_model_validation_from_dict(self):
        """Test model validation from dictionary."""
        now = datetime.now()
        task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        # Should handle ISO string dates
        task = TaskModel.model_validate(task_data)
        assert task.id == "TSK-0001"
        assert isinstance(task.created_at, datetime)
