"""Comprehensive unit tests for utility modules."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

from ai_trackdown_pytools.utils.editor import EditorUtils
from ai_trackdown_pytools.utils.health import check_health, check_project_health
from ai_trackdown_pytools.utils.logging import setup_logging
from ai_trackdown_pytools.utils.system import get_system_info


class TestEditorUtils:
    """Test EditorUtils functionality."""

    @patch.dict(os.environ, {"EDITOR": "vim"})
    def test_get_editor_from_env(self):
        """Test getting editor from environment variable."""
        editor = EditorUtils.get_editor()
        assert editor == "vim"

    @patch.dict(os.environ, {}, clear=True)
    @patch("ai_trackdown_pytools.core.config.Config")
    def test_get_editor_from_config(self, mock_config_class):
        """Test getting editor from config."""
        mock_config = Mock()
        mock_config.get.return_value = "emacs"
        mock_config_class.load.return_value = mock_config

        editor = EditorUtils.get_editor()
        assert editor == "emacs"

    @patch.dict(os.environ, {}, clear=True)
    @patch("ai_trackdown_pytools.core.config.Config")
    @patch("shutil.which")
    def test_get_editor_fallback(self, mock_which, mock_config_class):
        """Test editor fallback mechanism."""
        mock_config = Mock()
        mock_config.get.side_effect = [None, ["nano", "vi"]]
        mock_config_class.load.return_value = mock_config

        # nano is available
        mock_which.return_value = "/usr/bin/nano"

        editor = EditorUtils.get_editor()
        assert editor == "nano"

    @patch.dict(os.environ, {}, clear=True)
    @patch("ai_trackdown_pytools.core.config.Config")
    @patch("shutil.which")
    def test_get_editor_none_available(self, mock_which, mock_config_class):
        """Test when no editor is available."""
        mock_config = Mock()
        mock_config.get.return_value = None
        mock_config_class.load.return_value = mock_config

        mock_which.return_value = None

        editor = EditorUtils.get_editor()
        assert editor is None

    @patch("subprocess.run")
    @patch.object(EditorUtils, "get_editor")
    def test_open_file_success(self, mock_get_editor, mock_run):
        """Test opening file in editor successfully."""
        mock_get_editor.return_value = "vim"
        mock_run.return_value = Mock(returncode=0)

        result = EditorUtils.open_file(Path("/test/file.txt"))

        assert result is True
        mock_run.assert_called_once_with(["vim", Path("/test/file.txt")], check=False)

    @patch("subprocess.run")
    @patch.object(EditorUtils, "get_editor")
    def test_open_file_with_custom_editor(self, mock_get_editor, mock_run):
        """Test opening file with custom editor."""
        mock_run.return_value = Mock(returncode=0)

        result = EditorUtils.open_file(Path("/test/file.txt"), editor="code")

        assert result is True
        mock_run.assert_called_once_with(["code", Path("/test/file.txt")], check=False)
        mock_get_editor.assert_not_called()

    @patch("subprocess.run")
    @patch.object(EditorUtils, "get_editor")
    def test_open_file_failure(self, mock_get_editor, mock_run):
        """Test opening file when editor fails."""
        mock_get_editor.return_value = "vim"
        mock_run.return_value = Mock(returncode=1)

        result = EditorUtils.open_file(Path("/test/file.txt"))

        assert result is False

    @patch.object(EditorUtils, "get_editor")
    def test_open_file_no_editor(self, mock_get_editor):
        """Test opening file when no editor available."""
        mock_get_editor.return_value = None

        result = EditorUtils.open_file(Path("/test/file.txt"))

        assert result is False


class TestSystemUtils:
    """Test system utility functions."""

    @patch("platform.python_version")
    @patch("platform.system")
    @patch("platform.machine")
    @patch("pathlib.Path.cwd")
    @patch("ai_trackdown_pytools.utils.git.GitUtils")
    @patch("ai_trackdown_pytools.core.config.Config")
    def test_get_system_info(
        self,
        mock_config_class,
        mock_git_utils,
        mock_cwd,
        mock_machine,
        mock_system,
        mock_python_version,
    ):
        """Test getting system information."""
        # Mock system info
        mock_python_version.return_value = "3.9.0"
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"
        mock_cwd.return_value = Path("/current/dir")

        # Mock git
        mock_git = Mock()
        mock_git.is_git_repo.return_value = True
        mock_git_utils.return_value = mock_git

        # Mock config
        mock_config = Mock()
        mock_config.config_path = Path("/config/path")
        mock_config.project_root = Path("/project/root")
        mock_config_class.load.return_value = mock_config

        # Mock paths
        with patch("pathlib.Path.exists", return_value=True):
            info = get_system_info()

        assert info["python_version"] == "3.9.0"
        assert info["platform"] == "Linux"
        assert info["architecture"] == "x86_64"
        assert info["cwd"] == "/current/dir"
        assert info["git_repo"] is True
        assert info["config_file"] == "/config/path"
        assert info["project_root"] == "/project/root"
        assert "templates_dir" in info
        assert "schema_dir" in info


class TestHealthChecks:
    """Test health check functions."""

    @patch("ai_trackdown_pytools.utils.health._check_python_version")
    @patch("ai_trackdown_pytools.utils.health._check_dependencies")
    @patch("ai_trackdown_pytools.utils.health._check_configuration")
    @patch("ai_trackdown_pytools.utils.health._check_git")
    def test_check_health(self, mock_git, mock_config, mock_deps, mock_python):
        """Test overall health check."""
        # All checks pass
        mock_python.return_value = {"status": True, "message": "Python 3.8+"}
        mock_deps.return_value = {
            "status": True,
            "message": "All dependencies installed",
        }
        mock_config.return_value = {"status": True, "message": "Config OK"}
        mock_git.return_value = {"status": True, "message": "Git available"}

        result = check_health()

        assert result["overall"] is True
        assert len(result["checks"]) >= 4

        # One check fails
        mock_git.return_value = {"status": False, "message": "Git not found"}

        result = check_health()

        assert result["overall"] is False

    @patch("ai_trackdown_pytools.utils.health._check_project_exists")
    @patch("ai_trackdown_pytools.utils.health._check_project_structure")
    @patch("ai_trackdown_pytools.utils.health._check_config_validity")
    @patch("ai_trackdown_pytools.utils.health._check_tasks_directory")
    def test_check_project_health(
        self, mock_tasks, mock_config, mock_structure, mock_exists
    ):
        """Test project health check."""
        project_path = Path("/test/project")

        # All checks pass
        mock_exists.return_value = {"status": True, "message": "Project exists"}
        mock_structure.return_value = {"status": True, "message": "Structure OK"}
        mock_config.return_value = {"status": True, "message": "Config valid"}
        mock_tasks.return_value = {"status": True, "message": "Tasks OK"}

        result = check_project_health(project_path)

        assert result["overall"] is True
        assert len(result["checks"]) >= 4

        # One check fails
        mock_tasks.return_value = {"status": False, "message": "No tasks found"}

        result = check_project_health(project_path)

        assert result["overall"] is False


class TestLogging:
    """Test logging utilities."""

    @patch("logging.basicConfig")
    def test_setup_logging_verbose(self, mock_basic_config):
        """Test setting up logging in verbose mode."""
        setup_logging(verbose=True)

        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == 10  # DEBUG

    @patch("logging.basicConfig")
    def test_setup_logging_normal(self, mock_basic_config):
        """Test setting up logging in normal mode."""
        setup_logging(verbose=False)

        mock_basic_config.assert_called_once()
        call_kwargs = mock_basic_config.call_args[1]
        assert call_kwargs["level"] == 20  # INFO

    def test_setup_logging_with_file(self):
        """Test setting up logging with log file."""
        with patch("logging.basicConfig") as mock_basic_config:
            setup_logging(verbose=False, log_file="test.log")

            mock_basic_config.assert_called_once()
            # Should have file handler in config
