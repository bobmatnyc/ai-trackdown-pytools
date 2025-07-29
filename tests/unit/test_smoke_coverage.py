"""Smoke tests to increase coverage quickly."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from ai_trackdown_pytools import cli, version

# Import modules to increase coverage
from ai_trackdown_pytools.core import config, models, project, task, workflow
from ai_trackdown_pytools.utils import frontmatter, index, templates, validation


class TestSmokeCoverage:
    """Smoke tests for coverage increase."""

    def test_imports_work(self):
        """Test that imports work."""
        assert models is not None
        assert workflow is not None
        assert task is not None
        assert project is not None
        assert config is not None
        assert validation is not None
        assert frontmatter is not None
        assert index is not None
        assert templates is not None
        assert cli is not None
        assert version is not None

    def test_version_module(self):
        """Test version module."""
        from ai_trackdown_pytools.version import get_version

        # Get version should return a string
        v = get_version()
        assert isinstance(v, str)
        assert "." in v  # Should have version format

    def test_workflow_enums(self):
        """Test workflow enums exist."""
        from ai_trackdown_pytools.core.workflow import ResolutionType, UnifiedStatus

        # Test some enum values
        assert UnifiedStatus.OPEN
        assert UnifiedStatus.CLOSED
        assert ResolutionType.FIXED
        assert ResolutionType.WONT_FIX

    def test_model_enums(self):
        """Test model enums exist."""
        from ai_trackdown_pytools.core.models import Priority, TaskStatus

        # Test enum values
        assert TaskStatus.OPEN
        assert Priority.HIGH
        assert Priority.MEDIUM
        assert Priority.LOW

    def test_config_module(self):
        """Test config module."""
        from ai_trackdown_pytools.core.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test default config
            config = Config()
            assert config is not None
            assert hasattr(config, "get")

    def test_project_module(self):
        """Test project module."""
        from datetime import datetime

        from ai_trackdown_pytools.core.project import Project, ProjectModel

        # Create project with model - include required fields
        now = datetime.now()
        model = ProjectModel(
            id="PROJ-001",
            name="test-project",
            title="Test Project",
            status="active",
            created_at=now,
            updated_at=now,
        )
        project = Project(Path("/test"), model)
        assert project.data == model

    def test_validation_functions(self):
        """Test validation module functions."""
        from ai_trackdown_pytools.utils.validation import validate_task_id

        # Test ID validation
        result = validate_task_id("TSK-001")
        assert result.valid is True

        result = validate_task_id("invalid")
        assert result.valid is False

    def test_frontmatter_functions(self):
        """Test frontmatter module."""
        from ai_trackdown_pytools.utils.frontmatter import parse_frontmatter

        # Test basic frontmatter parsing
        content = """---
id: TSK-001
title: Test Task
---
Content here"""

        fm, body = parse_frontmatter(content)
        assert fm["id"] == "TSK-001"
        assert fm["title"] == "Test Task"
        assert "Content here" in body

    def test_templates_module(self):
        """Test templates module."""
        from ai_trackdown_pytools.utils.templates import TemplateEngine

        # Test template engine creation
        engine = TemplateEngine()
        assert engine is not None

        # Test render_string method
        result = engine.render_string("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

    def test_cli_app_exists(self):
        """Test CLI app exists."""
        from ai_trackdown_pytools.cli import app

        assert app is not None
        # Typer apps have different attributes
        assert hasattr(app, "callback")

    @patch("ai_trackdown_pytools.core.task.Task")
    def test_task_creation_mock(self, mock_task):
        """Test task creation with mocks."""
        from ai_trackdown_pytools.core.task import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock the task creation
            mock_task.return_value.model.id = "TSK-001"

            manager = TaskManager(Path(tmpdir))
            assert manager is not None

    def test_workflow_functions(self):
        """Test workflow utility functions."""
        from ai_trackdown_pytools.core.workflow import (
            UnifiedStatus,
            is_terminal_status,
            requires_resolution,
        )

        # Test terminal status
        assert is_terminal_status(UnifiedStatus.CLOSED) is True
        assert is_terminal_status(UnifiedStatus.OPEN) is False

        # Test resolution requirement
        assert requires_resolution(UnifiedStatus.RESOLVED) is True
        assert requires_resolution(UnifiedStatus.OPEN) is False

    def test_index_module(self):
        """Test index module."""
        from ai_trackdown_pytools.utils.index import build_search_index

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test index building
            project_path = Path(tmpdir)
            (project_path / "tickets").mkdir()

            result = build_search_index(project_path)
            assert result is not None

    def test_validation_result_creation(self):
        """Test validation result creation."""
        # Import base validation result from models
        from ai_trackdown_pytools.core.models import BaseModel

        # Create a simple model to test validation
        class TestResult(BaseModel):
            valid: bool
            errors: list = []
            warnings: list = []

        result = TestResult(valid=True, errors=[], warnings=["test warning"])

        assert result.valid is True
        assert len(result.warnings) == 1

    def test_model_creation_with_minimal_fields(self):
        """Test model creation with minimal required fields."""
        from ai_trackdown_pytools.core.models import (
            BugModel,
            CommentModel,
            EpicModel,
            IssueModel,
            MilestoneModel,
            TaskModel,
        )

        # These should work with minimal fields
        task = TaskModel(id="TSK-001", title="Test")
        assert task.id == "TSK-001"
        assert task.ticket_type == "task"

        issue = IssueModel(id="ISS-001", title="Test")
        assert issue.id == "ISS-001"
        assert issue.ticket_type == "issue"

        epic = EpicModel(id="EP-001", title="Test")
        assert epic.id == "EP-001"
        assert epic.ticket_type == "epic"

        bug = BugModel(id="BUG-001", title="Test")
        assert bug.id == "BUG-001"
        assert bug.ticket_type == "bug"

        # Comment and milestone
        comment = CommentModel(id="CMT-001", content="Test comment", author="test_user")
        assert comment.id == "CMT-001"

        milestone = MilestoneModel(id="M-001", title="v1.0", due_date=datetime.now())
        assert milestone.id == "M-001"
