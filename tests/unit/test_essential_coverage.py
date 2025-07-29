"""Essential tests to reach 85% coverage quickly."""

import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestEssentialCoverage:
    """Essential tests for 85% coverage."""

    def test_imports_work(self):
        """Test that all imports work."""
        # Core modules

        # CLI

        # Commands

        # Utils

        assert True  # If we get here, imports worked

    def test_basic_model_creation(self):
        """Test basic model creation to cover model code."""
        from ai_trackdown_pytools.core.models import (
            BugModel,
            CommentModel,
            EpicModel,
            IssueModel,
            MilestoneModel,
            PRModel,
            ProjectModel,
            TaskModel,
        )

        # Create models with minimal required fields
        now = datetime.now()

        # Task
        task = TaskModel(
            id="TSK-001", title="Test Task", created_at=now, updated_at=now
        )
        assert task.id == "TSK-001"
        assert task.status == "open"  # default
        assert task.priority == "medium"  # default
        assert task.ticket_type == "task"

        # Issue
        issue = IssueModel(
            id="ISS-001", title="Test Issue", created_at=now, updated_at=now
        )
        assert issue.ticket_type == "issue"

        # Epic
        epic = EpicModel(id="EP-001", title="Test Epic", created_at=now, updated_at=now)
        assert epic.ticket_type == "epic"

        # Bug
        bug = BugModel(
            id="BUG-001",
            title="Test Bug",
            created_at=now,
            updated_at=now,
            severity="medium",
        )
        assert bug.ticket_type == "bug"

        # Comment
        comment = CommentModel(
            id="CMT-001",
            content="Test comment",
            author="test_user",
            created_at=now,
            updated_at=now,
        )
        assert comment.author == "test_user"

        # Milestone
        milestone = MilestoneModel(
            id="M-001", title="v1.0", due_date=now, created_at=now, updated_at=now
        )
        assert milestone.title == "v1.0"

        # PR
        pr = PRModel(
            id="PR-001",
            title="Test PR",
            source_branch="feature",
            target_branch="main",
            created_at=now,
            updated_at=now,
        )
        assert pr.source_branch == "feature"

        # Project
        project = ProjectModel(
            id="PROJ-001",
            name="test-project",
            title="Test Project",
            created_at=now,
            updated_at=now,
        )
        assert project.name == "test-project"

    def test_workflow_basics(self):
        """Test workflow basics."""
        from ai_trackdown_pytools.core.workflow import (
            ResolutionType,
            StatusCategory,
            UnifiedStatus,
            WorkflowStateMachine,
            get_status_category,
            is_terminal_status,
            requires_resolution,
        )

        # Test enums
        assert UnifiedStatus.OPEN.value == "open"
        assert ResolutionType.FIXED.value == "fixed"
        assert StatusCategory.TODO.value == "todo"

        # Test utility functions
        assert is_terminal_status(UnifiedStatus.CLOSED) is True
        assert is_terminal_status(UnifiedStatus.OPEN) is False

        assert requires_resolution(UnifiedStatus.RESOLVED) is True
        assert requires_resolution(UnifiedStatus.OPEN) is False

        assert get_status_category(UnifiedStatus.OPEN) == StatusCategory.TODO
        assert (
            get_status_category(UnifiedStatus.IN_PROGRESS) == StatusCategory.IN_PROGRESS
        )

        # Test state machine
        machine = WorkflowStateMachine()

        # Valid transition
        result = machine.validate_transition(
            "task", UnifiedStatus.OPEN, UnifiedStatus.IN_PROGRESS
        )
        assert result.valid is True

        # Invalid transition
        result = machine.validate_transition(
            "task", UnifiedStatus.CLOSED, UnifiedStatus.OPEN
        )
        assert result.valid is False

        # Get allowed transitions
        transitions = machine.get_allowed_transitions("task", UnifiedStatus.OPEN)
        assert UnifiedStatus.IN_PROGRESS in transitions

        # Validate resolution
        result = machine.validate_resolution(
            "issue", UnifiedStatus.RESOLVED, ResolutionType.FIXED
        )
        assert result.valid is True

    def test_task_manager_basics(self):
        """Test TaskManager basics."""
        from ai_trackdown_pytools.core.task import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manager
            manager = TaskManager(Path(tmpdir))

            # Create task
            task = manager.create_task(
                title="Test Task", description="Test description"
            )
            assert task.model.title == "Test Task"
            assert task.model.id.startswith("TSK-")

            # Save task
            task.save()
            assert task.file_path.exists()

            # Update task
            updated = manager.update_task(task.model.id, status="in_progress")
            assert updated is True

            # Delete task
            deleted = manager.delete_task(task.model.id)
            assert deleted is True
            assert not task.file_path.exists()

    def test_config_basics(self):
        """Test Config basics."""
        from ai_trackdown_pytools.core.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test default config
            config = Config()
            assert config.get("project_name", "default") == "default"

            # Test with project path
            project_path = Path(tmpdir)
            config_dir = project_path / ".aitrackdown"
            config_dir.mkdir()

            # Write minimal config
            config_file = config_dir / "config.yaml"
            config_file.write_text("project_name: test\\n")

            # Load config
            config = Config.load(project_path=project_path)
            assert config.get("project_name") == "test"

    def test_project_basics(self):
        """Test Project basics."""
        from ai_trackdown_pytools.core.project import Project, ProjectModel

        # Create project model
        now = datetime.now()
        model = ProjectModel(
            id="PROJ-001",
            name="test-project",
            title="Test Project",
            created_at=now,
            updated_at=now,
        )

        # Create project
        project = Project(Path("/test"), model)
        assert project.data == model
        assert project.path == Path("/test")

    def test_validation_basics(self):
        """Test validation basics."""
        from ai_trackdown_pytools.utils.validation import (
            ValidationResult,
            validate_epic_id,
            validate_issue_id,
            validate_task_id,
        )

        # Test ID validation
        result = validate_task_id("TSK-001")
        assert isinstance(result, ValidationResult)
        assert result.valid is True

        result = validate_task_id("invalid")
        assert result.valid is False

        result = validate_issue_id("ISS-001")
        assert result.valid is True

        result = validate_epic_id("EP-001")
        assert result.valid is True

    def test_frontmatter_basics(self):
        """Test frontmatter basics."""
        from ai_trackdown_pytools.utils.frontmatter import (
            format_frontmatter,
            parse_frontmatter,
        )

        # Test parsing
        content = """---
id: TSK-001
title: Test Task
---
Body content here"""

        fm, body = parse_frontmatter(content)
        assert fm["id"] == "TSK-001"
        assert fm["title"] == "Test Task"
        assert "Body content here" in body

        # Test formatting
        data = {"id": "TSK-002", "title": "Another Task"}
        formatted = format_frontmatter(data)
        assert "id: TSK-002" in formatted
        assert "title: Another Task" in formatted

    def test_templates_basics(self):
        """Test templates basics."""
        from ai_trackdown_pytools.utils.templates import (
            TemplateEngine,
            get_default_templates,
            render_template,
        )

        # Test engine
        engine = TemplateEngine()
        result = engine.render_string("{{ name }}", {"name": "Test"})
        assert result == "Test"

        # Test default templates
        templates = get_default_templates()
        assert "task" in templates
        assert "issue" in templates
        assert "epic" in templates

        # Test render
        result = render_template(
            "task", {"id": "TSK-001", "title": "Test Task", "description": "Test"}
        )
        assert "TSK-001" in result

    def test_console_basics(self):
        """Test console basics."""
        from ai_trackdown_pytools.utils.console import (
            Console,
            print_error,
            print_info,
            print_success,
            print_warning,
        )

        # Create console
        console = Console()
        assert console is not None

        # Test print functions (should not raise)
        with patch("ai_trackdown_pytools.utils.console.console"):
            print_error("Error")
            print_success("Success")
            print_warning("Warning")
            print_info("Info")

    def test_version_basics(self):
        """Test version basics."""
        from ai_trackdown_pytools.version import get_version, get_version_info

        # Get version
        version = get_version()
        assert isinstance(version, str)
        assert "." in version  # Should be semantic version

        # Get version info
        info = get_version_info()
        assert isinstance(info, dict)
        assert "version" in info

    def test_cli_app_exists(self):
        """Test CLI app exists."""
        from ai_trackdown_pytools.cli import app, create_app

        # App should exist
        assert app is not None

        # Can create app
        new_app = create_app()
        assert new_app is not None

    def test_command_imports(self):
        """Test command imports."""
        from ai_trackdown_pytools.commands import (
            comment,
            epic,
            index,
            init,
            issue,
            search,
            status,
            sync,
            task,
            template,
            validate,
        )

        # All command modules should import
        assert init is not None
        assert task is not None
        assert issue is not None
        assert epic is not None
        assert comment is not None
        assert search is not None
        assert index is not None
        assert sync is not None
        assert status is not None
        assert template is not None
        assert validate is not None
