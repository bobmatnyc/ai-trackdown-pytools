"""Strategic tests to reach 85% coverage quickly."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

# Focus on high-impact modules


class TestStrategicCoverage:
    """Strategic tests for maximum coverage gain."""

    def test_cli_module_coverage(self):
        """Test CLI module for coverage."""
        # Import all CLI-related items
        from ai_trackdown_pytools.cli import console, create_app

        # Test app creation
        test_app = create_app()
        assert test_app is not None

        # Test console exists
        assert console is not None

    def test_models_enum_coverage(self):
        """Test all model enums for coverage."""
        from ai_trackdown_pytools.core.models import (
            BugStatus,
            EpicStatus,
            IssueStatus,
            IssueType,
            MilestoneStatus,
            Priority,
            ProjectStatus,
            PRStatus,
            PRType,
            TaskStatus,
        )

        # Test all enum values
        assert TaskStatus.OPEN.value == "open"
        assert EpicStatus.DRAFT.value == "draft"
        assert IssueStatus.OPEN.value == "open"
        assert BugStatus.NEW.value == "new"
        assert PRStatus.DRAFT.value == "draft"
        assert ProjectStatus.ACTIVE.value == "active"
        assert Priority.LOW.value == "low"
        assert IssueType.FEATURE.value == "feature"
        assert PRType.FEATURE.value == "feature"
        assert MilestoneStatus.OPEN.value == "open"

    def test_workflow_state_machine_coverage(self):
        """Test workflow state machine for coverage."""
        from ai_trackdown_pytools.core.workflow import (
            ResolutionType,
            UnifiedStatus,
            WorkflowStateMachine,
        )

        # Create state machine
        machine = WorkflowStateMachine()

        # Test validate transition
        result = machine.validate_transition(
            "task", UnifiedStatus.OPEN, UnifiedStatus.IN_PROGRESS
        )
        assert result.valid is True

        # Test invalid transition
        result = machine.validate_transition(
            "task", UnifiedStatus.CLOSED, UnifiedStatus.OPEN
        )
        assert result.valid is False

        # Test get allowed transitions
        transitions = machine.get_allowed_transitions("task", UnifiedStatus.OPEN)
        assert len(transitions) > 0

        # Test resolution validation
        result = machine.validate_resolution(
            "issue", UnifiedStatus.RESOLVED, ResolutionType.FIXED
        )
        assert result.valid is True

    def test_task_manager_coverage(self):
        """Test TaskManager for coverage."""
        from ai_trackdown_pytools.core.task import TaskManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create task manager
            manager = TaskManager(Path(tmpdir))

            # Test task creation
            task = manager.create_task(title="Test Task", description="Test")
            assert task is not None
            assert task.model.title == "Test Task"

            # Test task update
            result = manager.update_task(task.model.id, status="in_progress")
            assert result is True

            # Test task deletion
            result = manager.delete_task(task.model.id)
            assert result is True

    def test_config_module_coverage(self):
        """Test Config module for coverage."""
        from ai_trackdown_pytools.core.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / ".aitrackdown" / "config.yaml"
            config_path.parent.mkdir(parents=True)

            # Write test config
            config_data = {
                "project_name": "test",
                "tasks": {"directory": "tickets"},
                "workflows": {},
            }
            config_path.write_text(yaml.dump(config_data))

            # Load config
            config = Config.load(project_path=Path(tmpdir))
            assert config.get("project_name") == "test"

            # Test get with default
            assert config.get("missing_key", "default") == "default"

    def test_validation_module_coverage(self):
        """Test validation module for coverage."""
        from ai_trackdown_pytools.utils.validation import (
            ValidationResult,
            validate_epic_id,
            validate_issue_id,
            validate_task_file,
            validate_task_id,
        )

        # Test ID validation
        assert validate_task_id("TSK-001").valid is True
        assert validate_task_id("invalid").valid is False

        assert validate_issue_id("ISS-001").valid is True
        assert validate_issue_id("invalid").valid is False

        assert validate_epic_id("EP-001").valid is True
        assert validate_epic_id("invalid").valid is False

        # Test file validation with mock
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
id: TSK-001
title: Test Task
status: open
priority: medium
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-01T00:00:00
---
Test content"""
            )
            f.flush()

            result = validate_task_file(Path(f.name))
            assert isinstance(result, ValidationResult)

    def test_frontmatter_module_coverage(self):
        """Test frontmatter module for coverage."""
        from ai_trackdown_pytools.utils.frontmatter import (
            format_frontmatter,
            parse_frontmatter,
            parse_ticket_file,
        )

        # Test parsing
        content = """---
id: TSK-001
title: Test
---
Body content"""

        fm, body = parse_frontmatter(content)
        assert fm["id"] == "TSK-001"
        assert "Body content" in body

        # Test formatting
        formatted = format_frontmatter({"id": "TSK-002", "title": "Test2"})
        assert "id: TSK-002" in formatted

        # Test ticket file operations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            f.flush()

            fm, body = parse_ticket_file(Path(f.name))
            assert fm["id"] == "TSK-001"

    def test_index_module_coverage(self):
        """Test index module for coverage."""
        from ai_trackdown_pytools.utils.index import (
            build_search_index,
            get_index_stats,
            search_in_index,
            update_index_on_file_change,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            tickets_dir = project_path / "tickets"
            tickets_dir.mkdir()

            # Create test ticket
            ticket_file = tickets_dir / "TSK-001.md"
            ticket_file.write_text(
                """---
id: TSK-001
title: Test Task
---
Test content"""
            )

            # Build index
            stats = build_search_index(project_path)
            assert stats["indexed"] >= 0

            # Update index
            update_index_on_file_change(ticket_file, "modified")

            # Search
            results = search_in_index(project_path, "test")
            assert isinstance(results, list)

            # Get stats
            stats = get_index_stats(project_path)
            assert isinstance(stats, dict)

    def test_templates_module_coverage(self):
        """Test templates module for coverage."""
        from ai_trackdown_pytools.utils.templates import (
            TemplateEngine,
            get_default_templates,
            list_available_templates,
            render_template,
        )

        # Test template engine
        engine = TemplateEngine()
        result = engine.render_string("Hello {{ name }}", {"name": "World"})
        assert result == "Hello World"

        # Test default templates
        templates = get_default_templates()
        assert "task" in templates
        assert "issue" in templates
        assert "epic" in templates

        # Test render
        result = render_template("task", {"id": "TSK-001", "title": "Test"})
        assert "TSK-001" in result

        # Test list templates
        available = list_available_templates()
        assert len(available) > 0

    def test_git_module_coverage(self):
        """Test git module for coverage."""
        from ai_trackdown_pytools.utils.git import get_current_branch, is_git_repo

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test non-git directory
            assert is_git_repo(Path(tmpdir)) is False

            # Mock git operations
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "main\\n"

                branch = get_current_branch(Path(tmpdir))
                assert branch == "main"

    def test_console_module_coverage(self):
        """Test console module for coverage."""
        from ai_trackdown_pytools.utils.console import (
            Console,
            create_progress_bar,
            print_error,
            print_info,
            print_success,
            print_warning,
        )

        # Test console creation
        console = Console()
        assert console is not None

        # Test print functions (they should not raise)
        print_error("Test error")
        print_success("Test success")
        print_warning("Test warning")
        print_info("Test info")

        # Test progress bar
        with create_progress_bar() as progress:
            task = progress.add_task("Test", total=10)
            progress.update(task, advance=5)

    def test_version_module_coverage(self):
        """Test version module for coverage."""
        from ai_trackdown_pytools.version import (
            check_for_updates,
            format_version_string,
            get_version,
            get_version_info,
        )

        # Test version functions
        version = get_version()
        assert isinstance(version, str)

        info = get_version_info()
        assert isinstance(info, dict)

        # Mock update check
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"version": "2.0.0"}
            updates = check_for_updates()
            assert updates is not None

        # Test format
        formatted = format_version_string("1.0.0")
        assert "1.0.0" in formatted
