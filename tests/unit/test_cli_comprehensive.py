"""Comprehensive unit tests for CLI entry point module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from ai_trackdown_pytools import __version__
from ai_trackdown_pytools.cli import app, main, version_callback


class TestCLIMain:
    """Test main CLI functionality."""

    def test_app_initialization(self):
        """Test that the app is properly initialized."""
        assert app.info.name == "aitrackdown"
        assert "AI Trackdown PyTools" in app.info.help
        assert app.info.context_settings["help_option_names"] == ["-h", "--help"]
        assert app.info.rich_markup_mode == "rich"

    def test_version_callback_shows_version(self):
        """Test version callback displays version and exits."""
        with pytest.raises(typer.Exit):
            version_callback(True)

    def test_version_callback_no_value(self):
        """Test version callback does nothing when False."""
        # Should not raise exception
        version_callback(False)

    @patch("ai_trackdown_pytools.cli.setup_logging")
    @patch("ai_trackdown_pytools.cli.Config")
    def test_main_callback_with_options(self, mock_config, mock_logging, runner):
        """Test main callback with various options."""
        result = runner.invoke(app, ["--verbose", "--config", "test.yaml", "info"])

        # Verify logging was setup with verbose
        mock_logging.assert_called_once_with(True)

        # Verify config was loaded
        mock_config.load.assert_called_once_with("test.yaml")

    @patch("os.chdir")
    @patch("os.getcwd")
    def test_project_dir_option(self, mock_getcwd, mock_chdir, runner):
        """Test project directory option for anywhere-submit."""
        mock_getcwd.return_value = "/original/dir"

        with patch("ai_trackdown_pytools.utils.system.get_system_info") as mock_info:
            mock_info.return_value = {
                "python_version": "3.9.0",
                "platform": "Linux",
                "architecture": "x86_64",
                "cwd": "/test/project",
                "git_repo": True,
                "config_file": None,
                "templates_dir": "/templates",
                "schema_dir": "/schemas",
            }

            result = runner.invoke(app, ["--project-dir", "/test/project", "info"])

            mock_chdir.assert_called_once_with("/test/project")
            assert result.exit_code == 0

    def test_project_dir_invalid(self, runner):
        """Test project directory option with invalid path."""
        result = runner.invoke(app, ["--project-dir", "/invalid/path", "info"])
        assert result.exit_code == 1
        assert "Cannot access project directory" in result.output


class TestCLICommands:
    """Test individual CLI commands."""

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_info_command(self, mock_get_info, runner):
        """Test info command displays system information."""
        mock_get_info.return_value = {
            "python_version": "3.9.0",
            "platform": "Linux",
            "architecture": "x86_64",
            "cwd": "/current/dir",
            "git_repo": True,
            "config_file": "config.yaml",
            "templates_dir": "/templates",
            "schema_dir": "/schemas",
            "project_root": "/project",
        }

        result = runner.invoke(app, ["info"])

        assert result.exit_code == 0
        assert "System Information" in result.output
        assert "Python: 3.9.0" in result.output
        assert "Platform: Linux" in result.output
        mock_get_info.assert_called_once()

    @patch("ai_trackdown_pytools.utils.health.check_health")
    def test_health_command_success(self, mock_check_health, runner):
        """Test health command when all checks pass."""
        mock_check_health.return_value = {
            "overall": True,
            "checks": {
                "python": {"status": True, "message": "Python 3.9.0"},
                "git": {"status": True, "message": "Git available"},
                "templates": {"status": True, "message": "Templates found"},
            },
        }

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 0
        assert "System health check passed" in result.output
        assert "✅" in result.output

    @patch("ai_trackdown_pytools.utils.health.check_health")
    def test_health_command_failure(self, mock_check_health, runner):
        """Test health command when checks fail."""
        mock_check_health.return_value = {
            "overall": False,
            "checks": {
                "python": {"status": True, "message": "Python 3.9.0"},
                "git": {"status": False, "message": "Git not found"},
                "templates": {"status": True, "message": "Templates found"},
            },
        }

        result = runner.invoke(app, ["health"])

        assert result.exit_code == 1
        assert "System health check failed" in result.output
        assert "❌" in result.output
        assert "Git not found" in result.output

    @patch("ai_trackdown_pytools.cli.Config")
    def test_config_list_all(self, mock_config_class, runner):
        """Test config command with --list flag."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {
            "project_root": "/test",
            "tasks.id_format": "TSK-{counter:04d}",
            "tasks.counter": 42,
        }
        mock_config.config_path = "config.yaml"
        mock_config_class.load.return_value = mock_config

        result = runner.invoke(app, ["config", "--list"])

        assert result.exit_code == 0
        assert "Current Configuration" in result.output
        assert "project_root: /test" in result.output
        assert "tasks.id_format: TSK-{counter:04d}" in result.output

    @patch("ai_trackdown_pytools.cli.Config")
    def test_config_get_value(self, mock_config_class, runner):
        """Test config command getting a specific value."""
        mock_config = Mock()
        mock_config.get.return_value = "TSK-{counter:04d}"
        mock_config_class.load.return_value = mock_config

        result = runner.invoke(app, ["config", "tasks.id_format"])

        assert result.exit_code == 0
        assert "tasks.id_format: TSK-{counter:04d}" in result.output

    @patch("ai_trackdown_pytools.cli.Config")
    def test_config_set_value(self, mock_config_class, runner):
        """Test config command setting a value."""
        mock_config = Mock()
        mock_config_class.load.return_value = mock_config

        result = runner.invoke(app, ["config", "tasks.id_format", "TASK-{counter:05d}"])

        assert result.exit_code == 0
        assert "Set tasks.id_format = TASK-{counter:05d}" in result.output
        mock_config.set.assert_called_once_with("tasks.id_format", "TASK-{counter:05d}")
        mock_config.save.assert_called_once()

    @patch("ai_trackdown_pytools.utils.health.check_health")
    @patch("ai_trackdown_pytools.utils.health.check_project_health")
    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.cli.Config")
    @patch("ai_trackdown_pytools.utils.git.GitUtils")
    @patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", True)
    def test_doctor_command(
        self,
        mock_git_utils,
        mock_config_class,
        mock_project,
        mock_project_health,
        mock_check_health,
        runner,
    ):
        """Test doctor command runs comprehensive diagnostics."""
        # Mock system health
        mock_check_health.return_value = {
            "overall": True,
            "checks": {
                "python": {"status": True, "message": "Python 3.9.0"},
                "git": {"status": True, "message": "Git available"},
            },
        }

        # Mock project health
        mock_project.exists.return_value = True
        mock_project_health.return_value = {
            "overall": True,
            "checks": {
                "structure": {"status": True, "message": "Valid structure"},
                "tasks": {"status": True, "message": "5 tasks found"},
            },
        }

        # Mock config
        mock_config = Mock()
        mock_config.config_path = "config.yaml"
        mock_config.project_root = "/project"
        mock_config_class.load.return_value = mock_config

        # Mock git
        mock_git = Mock()
        mock_git.is_git_repo.return_value = True
        mock_git.get_status.return_value = {
            "branch": "main",
            "modified": ["file1.py", "file2.py"],
        }
        mock_git_utils.return_value = mock_git

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0
        assert "Running AI Trackdown PyTools diagnostics" in result.output
        assert "System Health" in result.output
        assert "Project Health" in result.output
        assert "Configuration" in result.output
        assert "Git Integration" in result.output

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_version_command(self, mock_get_info, runner):
        """Test version command displays detailed version info."""
        mock_get_info.return_value = {
            "python_version": "3.9.0",
            "platform": "Linux",
            "architecture": "x86_64",
            "cwd": "/current/dir",
            "git_repo": True,
            "config_file": "config.yaml",
            "templates_dir": "/templates",
            "schema_dir": "/schemas",
            "project_root": "/project",
        }

        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert f"AI Trackdown PyTools[/bold blue] v{__version__}" in result.output
        assert "System Information" in result.output
        assert "Project Status" in result.output
        assert "Package Information" in result.output


class TestEditCommand:
    """Test edit command functionality."""

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.editor.EditorUtils")
    def test_edit_task_success(
        self, mock_editor, mock_task_manager_class, mock_project, runner
    ):
        """Test successful task editing."""
        # Mock project exists
        mock_project.exists.return_value = True

        # Mock task manager and task
        mock_task = Mock()
        mock_task.file_path = Path("/project/tasks/TSK-0001.md")
        mock_task_manager = Mock()
        mock_task_manager.load_task.return_value = mock_task
        mock_task_manager_class.return_value = mock_task_manager

        # Mock editor opens successfully
        mock_editor.open_file.return_value = True

        result = runner.invoke(app, ["edit", "TSK-0001"])

        assert result.exit_code == 0
        assert "Opened task TSK-0001 in editor" in result.output
        mock_editor.open_file.assert_called_once_with(
            Path("/project/tasks/TSK-0001.md"), None
        )

    @patch("ai_trackdown_pytools.core.project.Project")
    def test_edit_no_project(self, mock_project, runner):
        """Test edit command when no project exists."""
        mock_project.exists.return_value = False

        result = runner.invoke(app, ["edit", "TSK-0001"])

        assert result.exit_code == 1
        assert "No AI Trackdown project found" in result.output

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_edit_task_not_found(self, mock_task_manager_class, mock_project, runner):
        """Test edit command when task doesn't exist."""
        mock_project.exists.return_value = True

        mock_task_manager = Mock()
        mock_task_manager.load_task.return_value = None
        mock_task_manager_class.return_value = mock_task_manager

        result = runner.invoke(app, ["edit", "TSK-9999"])

        assert result.exit_code == 1
        assert "Task 'TSK-9999' not found" in result.output


class TestSearchCommand:
    """Test search command functionality."""

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_with_results(self, mock_task_manager_class, mock_project, runner):
        """Test search command finds matching tasks."""
        mock_project.exists.return_value = True

        # Create mock tasks
        task1 = Mock()
        task1.id = "TSK-0001"
        task1.title = "Fix bug in search functionality"
        task1.description = "The search feature is broken"
        task1.status = "open"
        task1.tags = ["bug", "search"]

        task2 = Mock()
        task2.id = "TSK-0002"
        task2.title = "Add new feature"
        task2.description = "Implement search filters"
        task2.status = "in-progress"
        task2.tags = ["feature", "search"]

        mock_task_manager = Mock()
        mock_task_manager.list_tasks.return_value = [task1, task2]
        mock_task_manager_class.return_value = mock_task_manager

        result = runner.invoke(app, ["search", "search"])

        assert result.exit_code == 0
        assert "Search Results" in result.output
        assert "TSK-0001" in result.output
        assert "TSK-0002" in result.output

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_with_filters(self, mock_task_manager_class, mock_project, runner):
        """Test search command with status and type filters."""
        mock_project.exists.return_value = True

        # Create mock tasks
        task1 = Mock()
        task1.id = "TSK-0001"
        task1.title = "Bug fix"
        task1.description = "Fix issue"
        task1.status = "open"
        task1.tags = ["bug"]

        task2 = Mock()
        task2.id = "TSK-0002"
        task2.title = "Bug feature"
        task2.description = "Add feature"
        task2.status = "closed"
        task2.tags = ["feature"]

        mock_task_manager = Mock()
        mock_task_manager.list_tasks.return_value = [task1, task2]
        mock_task_manager_class.return_value = mock_task_manager

        result = runner.invoke(
            app, ["search", "bug", "--status", "open", "--type", "bug"]
        )

        assert result.exit_code == 0
        assert "TSK-0001" in result.output
        assert "TSK-0002" not in result.output  # Filtered out

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_no_results(self, mock_task_manager_class, mock_project, runner):
        """Test search command with no matching results."""
        mock_project.exists.return_value = True

        mock_task_manager = Mock()
        mock_task_manager.list_tasks.return_value = []
        mock_task_manager_class.return_value = mock_task_manager

        result = runner.invoke(app, ["search", "nonexistent"])

        assert result.exit_code == 0
        assert "No tasks found matching 'nonexistent'" in result.output


class TestValidateCommand:
    """Test validate command functionality."""

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.utils.validation.validate_project_structure")
    def test_validate_project_success(
        self, mock_validate_structure, mock_project, runner
    ):
        """Test project validation when valid."""
        mock_project.exists.return_value = True
        mock_validate_structure.return_value = {
            "valid": True,
            "errors": [],
            "warnings": ["Minor issue with README"],
        }

        result = runner.invoke(app, ["validate", "project"])

        assert result.exit_code == 0
        assert "Project structure is valid" in result.output
        assert "Warnings:" in result.output
        assert "Minor issue with README" in result.output

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.utils.validation.validate_project_structure")
    def test_validate_project_failure(
        self, mock_validate_structure, mock_project, runner
    ):
        """Test project validation when invalid."""
        mock_project.exists.return_value = True
        mock_validate_structure.return_value = {
            "valid": False,
            "errors": ["Missing tasks directory", "Invalid config file"],
            "warnings": [],
        }

        result = runner.invoke(app, ["validate", "project"])

        assert result.exit_code == 0  # Command itself doesn't fail
        assert "Project structure validation failed" in result.output
        assert "Missing tasks directory" in result.output
        assert "Invalid config file" in result.output

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.validation.validate_task_file")
    def test_validate_tasks(
        self, mock_validate_task, mock_task_manager_class, mock_project, runner
    ):
        """Test task validation."""
        mock_project.exists.return_value = True

        # Create mock tasks
        task1 = Mock()
        task1.id = "TSK-0001"
        task1.file_path = Path("/tasks/TSK-0001.md")

        task2 = Mock()
        task2.id = "TSK-0002"
        task2.file_path = Path("/tasks/TSK-0002.md")

        mock_task_manager = Mock()
        mock_task_manager.list_tasks.return_value = [task1, task2]
        mock_task_manager_class.return_value = mock_task_manager

        # Mock validation results
        mock_validate_task.side_effect = [
            {"valid": True, "errors": [], "warnings": []},
            {
                "valid": False,
                "errors": ["Invalid schema"],
                "warnings": ["Missing description"],
            },
        ]

        result = runner.invoke(app, ["validate", "tasks"])

        assert result.exit_code == 0
        assert "Validating 2 tasks" in result.output
        assert "TSK-0001" in result.output
        assert "TSK-0002" in result.output
        assert "Invalid schema" in result.output

    @patch("ai_trackdown_pytools.cli.Config")
    @patch("ai_trackdown_pytools.utils.validation.SchemaValidator")
    def test_validate_config(self, mock_validator_class, mock_config_class, runner):
        """Test config validation."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"project_root": "/test"}
        mock_config_class.load.return_value = mock_config

        mock_validator = Mock()
        mock_validator.validate_config.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(app, ["validate", "config"])

        assert result.exit_code == 0
        assert "Configuration is valid" in result.output


class TestMainEntryPoint:
    """Test main entry point and error handling."""

    @patch("ai_trackdown_pytools.cli.app")
    def test_main_normal_execution(self, mock_app):
        """Test main() executes app normally."""
        mock_app.return_value = None

        # Should not raise exception
        main()

        mock_app.assert_called_once()

    @patch("ai_trackdown_pytools.cli.app")
    @patch("ai_trackdown_pytools.cli.console")
    def test_main_keyboard_interrupt(self, mock_console, mock_app):
        """Test main() handles keyboard interrupt."""
        mock_app.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        mock_console.print.assert_called_with(
            "\n[yellow]Operation cancelled by user[/yellow]"
        )

    @patch("ai_trackdown_pytools.cli.app")
    @patch("ai_trackdown_pytools.cli.console")
    def test_main_unexpected_error(self, mock_console, mock_app):
        """Test main() handles unexpected errors."""
        mock_app.side_effect = RuntimeError("Unexpected error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        # Check that error message was printed
        calls = mock_console.print.call_args_list
        assert any("Unexpected error: Unexpected error" in str(call) for call in calls)
        assert any("aitrackdown doctor" in str(call) for call in calls)


class TestSubcommandRegistration:
    """Test that all subcommands are properly registered."""

    def test_all_subcommands_registered(self):
        """Test that all expected subcommands are registered."""
        expected_commands = [
            "init",
            "status",
            "create",
            "template",
            "validate",
            "task",
            "issue",
            "epic",
            "pr",
            "search",
            "portfolio",
            "sync",
            "ai",
            "migrate",
            "info",
            "health",
            "config",
            "doctor",
            "version",
            "edit",
        ]

        # Get registered commands
        registered_commands = list(app.registered_commands.keys())

        for cmd in expected_commands:
            assert cmd in registered_commands, f"Command '{cmd}' not registered"

    def test_subcommand_help_text(self):
        """Test that subcommands have proper help text."""
        # Check main commands have help text
        assert (
            app.registered_groups["init"].help
            == "Initialize AI Trackdown project structure"
        )
        assert app.registered_groups["status"].help == "Show project and task status"
        assert (
            app.registered_groups["create"].help
            == "Create new tasks, projects, or issues"
        )
        assert app.registered_groups["template"].help == "Manage and apply templates"
        assert (
            app.registered_groups["validate"].help
            == "Validate tickets, schemas, and relationships"
        )


class TestErrorHandling:
    """Test error handling throughout the CLI."""

    @patch("os.chdir")
    def test_project_dir_permission_error(self, mock_chdir, runner):
        """Test handling of permission errors when changing directory."""
        mock_chdir.side_effect = PermissionError("Access denied")

        result = runner.invoke(app, ["--project-dir", "/restricted", "info"])

        assert result.exit_code == 1
        assert "Cannot access project directory" in result.output

    @patch("ai_trackdown_pytools.cli.Config")
    def test_config_get_nonexistent_key(self, mock_config_class, runner):
        """Test config get with non-existent key."""
        mock_config = Mock()
        mock_config.get.return_value = None
        mock_config_class.load.return_value = mock_config

        result = runner.invoke(app, ["config", "nonexistent.key"])

        assert result.exit_code == 0
        assert "Configuration key 'nonexistent.key' not found" in result.output

    def test_validate_unknown_target(self, runner):
        """Test validate command with unknown target."""
        result = runner.invoke(app, ["validate", "unknown"])

        assert result.exit_code == 1
        assert "Unknown validation target: unknown" in result.output
        assert "Valid targets: project, tasks, config" in result.output
