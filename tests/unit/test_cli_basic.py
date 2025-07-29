"""Basic unit tests for CLI module focusing on coverage."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from ai_trackdown_pytools import __version__
from ai_trackdown_pytools.cli import app, main, version_callback


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_version_callback_shows_version(self, capsys):
        """Test version callback displays version and exits."""
        with pytest.raises(typer.Exit):
            version_callback(True)

        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_version_callback_no_value(self):
        """Test version callback does nothing when False."""
        # Should not raise exception
        version_callback(False)

    def test_app_has_commands(self):
        """Test that app has expected commands registered."""
        # Check that subcommands are registered
        assert hasattr(app, "registered_groups")
        assert hasattr(app, "registered_commands")

    @patch("ai_trackdown_pytools.cli.setup_logging")
    def test_main_function(self, mock_logging):
        """Test main() function error handling."""
        with patch("ai_trackdown_pytools.cli.app") as mock_app:
            # Test normal execution
            main()
            mock_app.assert_called_once()

            # Test KeyboardInterrupt
            mock_app.side_effect = KeyboardInterrupt()
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

            # Test generic exception
            mock_app.side_effect = RuntimeError("Test error")
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestCLICommands:
    """Test individual CLI commands for coverage."""

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_info_command(self, mock_get_info, runner):
        """Test info command."""
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

    @patch("ai_trackdown_pytools.utils.health.check_health")
    def test_health_command(self, mock_check_health, runner):
        """Test health command."""
        mock_check_health.return_value = {
            "overall": True,
            "checks": {
                "python": {"status": True, "message": "Python 3.9.0"},
                "git": {"status": True, "message": "Git available"},
            },
        }

        result = runner.invoke(app, ["health"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.cli.Config")
    def test_config_command(self, mock_config_class, runner):
        """Test config command."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"test": "value"}
        mock_config.config_path = "config.yaml"
        mock_config.project_root = "/project"
        mock_config.get.return_value = "test_value"
        mock_config_class.load.return_value = mock_config

        # Test list
        result = runner.invoke(app, ["config", "--list"])
        assert result.exit_code == 0

        # Test get
        result = runner.invoke(app, ["config", "test.key"])
        assert result.exit_code == 0

        # Test set
        result = runner.invoke(app, ["config", "test.key", "new_value"])
        assert result.exit_code == 0

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
        """Test doctor command."""
        # Setup mocks
        mock_check_health.return_value = {
            "overall": True,
            "checks": {"python": {"status": True, "message": "OK"}},
        }
        mock_project.exists.return_value = True
        mock_project_health.return_value = {
            "overall": True,
            "checks": {"structure": {"status": True, "message": "OK"}},
        }
        mock_config = Mock()
        mock_config.config_path = "config.yaml"
        mock_config.project_root = "/project"
        mock_config_class.load.return_value = mock_config

        mock_git = Mock()
        mock_git.is_git_repo.return_value = True
        mock_git.get_status.return_value = {"branch": "main", "modified": []}
        mock_git_utils.return_value = mock_git

        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_version_command(self, mock_get_info, runner):
        """Test version command."""
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

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.editor.EditorUtils")
    def test_edit_command(
        self, mock_editor, mock_task_manager_class, mock_project, runner
    ):
        """Test edit command."""
        # Success case
        mock_project.exists.return_value = True
        mock_task = Mock()
        mock_task.file_path = Path("/tasks/TSK-0001.md")
        mock_task_manager = Mock()
        mock_task_manager.load_task.return_value = mock_task
        mock_task_manager_class.return_value = mock_task_manager
        mock_editor.open_file.return_value = True

        result = runner.invoke(app, ["edit", "TSK-0001"])
        assert result.exit_code == 0

        # No project case
        mock_project.exists.return_value = False
        result = runner.invoke(app, ["edit", "TSK-0001"])
        assert result.exit_code == 1

        # Task not found case
        mock_project.exists.return_value = True
        mock_task_manager.load_task.return_value = None
        result = runner.invoke(app, ["edit", "TSK-9999"])
        assert result.exit_code == 1

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_command(self, mock_task_manager_class, mock_project, runner):
        """Test search command."""
        # With results
        mock_project.exists.return_value = True

        task1 = Mock()
        task1.id = "TSK-0001"
        task1.title = "Test task with search keyword"
        task1.description = "Description"
        task1.status = "open"
        task1.tags = ["test"]

        mock_task_manager = Mock()
        mock_task_manager.list_tasks.return_value = [task1]
        mock_task_manager_class.return_value = mock_task_manager

        result = runner.invoke(app, ["search", "keyword"])
        assert result.exit_code == 0

        # No results
        mock_task_manager.list_tasks.return_value = []
        result = runner.invoke(app, ["search", "nonexistent"])
        assert result.exit_code == 0

        # No project
        mock_project.exists.return_value = False
        result = runner.invoke(app, ["search", "test"])
        assert result.exit_code == 1

    @patch("ai_trackdown_pytools.core.project.Project")
    @patch("ai_trackdown_pytools.utils.validation.validate_project_structure")
    @patch("ai_trackdown_pytools.utils.validation.validate_task_file")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.validation.SchemaValidator")
    def test_validate_command(
        self,
        mock_validator_class,
        mock_task_manager_class,
        mock_validate_task,
        mock_validate_project,
        mock_project,
        runner,
    ):
        """Test validate command."""
        # Validate project
        mock_project.exists.return_value = True
        mock_validate_project.return_value = {
            "valid": True,
            "errors": [],
            "warnings": ["Minor warning"],
        }

        result = runner.invoke(app, ["validate", "project"])
        assert result.exit_code == 0

        # Validate tasks
        task = Mock()
        task.id = "TSK-0001"
        task.file_path = Path("/tasks/TSK-0001.md")

        mock_task_manager = Mock()
        mock_task_manager.list_tasks.return_value = [task]
        mock_task_manager_class.return_value = mock_task_manager

        mock_validate_task.return_value = {"valid": True, "errors": [], "warnings": []}

        result = runner.invoke(app, ["validate", "tasks"])
        assert result.exit_code == 0

        # Validate config
        mock_validator = Mock()
        mock_validator.validate_config.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        mock_validator_class.return_value = mock_validator

        result = runner.invoke(app, ["validate", "config"])
        assert result.exit_code == 0

        # Invalid target
        result = runner.invoke(app, ["validate", "unknown"])
        assert result.exit_code == 1


class TestMainCallback:
    """Test main callback functionality."""

    @patch("ai_trackdown_pytools.cli.setup_logging")
    @patch("ai_trackdown_pytools.cli.Config")
    @patch("os.chdir")
    @patch("os.getcwd")
    def test_main_callback_with_project_dir(
        self, mock_getcwd, mock_chdir, mock_config, mock_logging, runner
    ):
        """Test main callback with project directory option."""
        mock_getcwd.return_value = "/original/dir"

        # Create a command that will succeed
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
                "project_root": "/project",
            }

            result = runner.invoke(app, ["--project-dir", "/test/project", "info"])

            mock_chdir.assert_called_with("/test/project")
            assert result.exit_code == 0

    @patch("ai_trackdown_pytools.cli.setup_logging")
    @patch("ai_trackdown_pytools.cli.Config")
    def test_main_callback_with_config_file(
        self, mock_config_class, mock_logging, runner
    ):
        """Test main callback with config file option."""
        mock_config_class.load.return_value = Mock()

        with patch("ai_trackdown_pytools.utils.system.get_system_info") as mock_info:
            mock_info.return_value = {
                "python_version": "3.9.0",
                "platform": "Linux",
                "architecture": "x86_64",
                "cwd": "/current",
                "git_repo": True,
                "config_file": "custom.yaml",
                "templates_dir": "/templates",
                "schema_dir": "/schemas",
                "project_root": "/project",
            }

            result = runner.invoke(app, ["--config", "custom.yaml", "info"])

            mock_config_class.load.assert_called_with("custom.yaml")
            assert result.exit_code == 0


class TestErrorHandling:
    """Test error handling in CLI."""

    def test_main_handles_exceptions(self):
        """Test main() handles various exceptions."""
        with patch("ai_trackdown_pytools.cli.app") as mock_app:
            # KeyboardInterrupt
            mock_app.side_effect = KeyboardInterrupt()
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

            # Generic exception
            mock_app.side_effect = Exception("Test error")
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
