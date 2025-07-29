"""Unit tests for CLI module to increase coverage."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from ai_trackdown_pytools.cli import app


class TestCLICoverage:
    """Test cases to increase CLI coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_version_option(self):
        """Test the --version option."""
        result = self.runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "aitrackdown version" in result.output

    @patch("ai_trackdown_pytools.cli.get_current_project")
    def test_cli_with_project_dir(self, mock_project):
        """Test CLI with project directory."""
        mock_project.return_value = MagicMock()

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(app, ["--project-dir", ".", "info"])
            assert result.exit_code == 0

    def test_cli_help(self):
        """Test CLI help output."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "AI Trackdown" in result.output

    def test_init_command_help(self):
        """Test init command help."""
        result = self.runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize" in result.output

    def test_task_command_help(self):
        """Test task command help."""
        result = self.runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0
        assert "task" in result.output

    def test_issue_command_help(self):
        """Test issue command help."""
        result = self.runner.invoke(app, ["issue", "--help"])
        assert result.exit_code == 0
        assert "issue" in result.output

    def test_epic_command_help(self):
        """Test epic command help."""
        result = self.runner.invoke(app, ["epic", "--help"])
        assert result.exit_code == 0
        assert "epic" in result.output

    def test_comment_command_help(self):
        """Test comment command help."""
        result = self.runner.invoke(app, ["comment", "--help"])
        assert result.exit_code == 0
        assert "comment" in result.output

    def test_search_command_help(self):
        """Test search command help."""
        result = self.runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output

    def test_index_command_help(self):
        """Test index command help."""
        result = self.runner.invoke(app, ["index", "--help"])
        assert result.exit_code == 0
        assert "index" in result.output

    def test_sync_command_help(self):
        """Test sync command help."""
        result = self.runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "sync" in result.output

    @patch("ai_trackdown_pytools.cli.console")
    def test_cli_exception_handling(self, mock_console):
        """Test CLI exception handling."""
        with patch("ai_trackdown_pytools.cli.app") as mock_app:
            mock_app.side_effect = Exception("Test error")

            # Import main to trigger exception
            from ai_trackdown_pytools.cli import main

            with pytest.raises(SystemExit):
                main()

    def test_cli_subcommands_exist(self):
        """Test that all subcommands are registered."""
        # Get the list of commands
        ctx = app.make_context("aitrackdown", [])
        commands = list(app.list_commands(ctx))

        # Check essential commands exist
        essential_commands = [
            "init",
            "task",
            "issue",
            "epic",
            "comment",
            "search",
            "index",
            "sync",
            "info",
            "health",
            "config",
            "doctor",
            "version",
            "edit",
            "validate",
        ]

        for cmd in essential_commands:
            assert cmd in commands

    @patch("ai_trackdown_pytools.cli.Path.cwd")
    def test_cli_current_directory(self, mock_cwd):
        """Test CLI uses current directory."""
        mock_cwd.return_value = Path("/test/dir")

        with patch("ai_trackdown_pytools.cli.get_current_project") as mock_project:
            mock_project.return_value = None
            result = self.runner.invoke(app, ["info"])
            # Should exit with error if no project found
            assert result.exit_code != 0
