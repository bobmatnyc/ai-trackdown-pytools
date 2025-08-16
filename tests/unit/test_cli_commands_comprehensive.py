"""Comprehensive unit tests for CLI commands."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app
from ai_trackdown_pytools.commands import init, task, issue, status
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TicketManager


class TestCLIApp:
    """Test main CLI application."""

    def test_app_creation(self):
        """Test that the main app is created correctly."""
        assert isinstance(app, typer.Typer)
        assert app.info.name == "aitrackdown"
        assert "AI-powered project tracking" in app.info.help

    def test_app_has_subcommands(self):
        """Test that subcommands are registered."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        
        # Should show help without error
        assert result.exit_code == 0
        
        # Should contain key subcommands
        help_text = result.stdout
        assert "init" in help_text
        assert "task" in help_text
        assert "issue" in help_text
        assert "status" in help_text

    def test_version_command(self):
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(app, ["version"])

        # Should show version without error
        assert result.exit_code == 0
        assert "v" in result.stdout.lower()  # Should contain version number

    def test_info_command(self):
        """Test info command."""
        runner = CliRunner()
        result = runner.invoke(app, ["info"])
        
        # Should show info without error
        assert result.exit_code == 0


class TestInitCommand:
    """Test init command functionality."""

    def test_init_command_help(self):
        """Test init command help."""
        runner = CliRunner()
        result = runner.invoke(init.app, ["--help"])
        
        assert result.exit_code == 0
        assert "Initialize" in result.stdout

    @patch('ai_trackdown_pytools.commands.init.Project')
    def test_init_command_basic(self, mock_project):
        """Test basic init command."""
        mock_project.exists.return_value = False
        mock_project.create.return_value = True
        
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(init.app, [], input="Test Project\n")
            
            # Should complete without error
            assert result.exit_code == 0

    @patch('ai_trackdown_pytools.commands.init.Project')
    def test_init_command_existing_project(self, mock_project):
        """Test init command with existing project."""
        mock_project.exists.return_value = True
        
        runner = CliRunner()
        result = runner.invoke(init.app, [])
        
        # Should exit with error for existing project
        assert result.exit_code == 1
        assert "already exists" in result.stdout.lower()

    @patch('ai_trackdown_pytools.commands.init.Project')
    def test_init_command_with_options(self, mock_project):
        """Test init command with various options."""
        mock_project.exists.return_value = False
        mock_project.create.return_value = True
        
        runner = CliRunner()
        result = runner.invoke(init.app, [
            "--name", "Test Project",
            "--description", "Test Description",
            "--template", "basic"
        ])
        
        assert result.exit_code == 0


class TestTaskCommand:
    """Test task command functionality."""

    def test_task_command_help(self):
        """Test task command help."""
        runner = CliRunner()
        result = runner.invoke(task.app, ["--help"])
        
        assert result.exit_code == 0
        assert "Task operations" in result.stdout or "task" in result.stdout.lower()

    @patch('ai_trackdown_pytools.commands.task.Project')
    @patch('ai_trackdown_pytools.commands.task.TicketManager')
    def test_task_create_command(self, mock_ticket_manager, mock_project):
        """Test task create command."""
        mock_project.exists.return_value = True
        mock_manager_instance = MagicMock()
        mock_ticket_manager.return_value = mock_manager_instance
        mock_manager_instance.create_task.return_value = "TSK-001"
        
        runner = CliRunner()
        result = runner.invoke(task.app, [
            "create",
            "--title", "Test Task",
            "--description", "Test Description"
        ])
        
        assert result.exit_code == 0

    @patch('ai_trackdown_pytools.commands.task.Project')
    def test_task_create_no_project(self, mock_project):
        """Test task create command without project."""
        mock_project.exists.return_value = False
        
        runner = CliRunner()
        result = runner.invoke(task.app, [
            "create",
            "--title", "Test Task"
        ])
        
        assert result.exit_code == 1
        assert "No AI Trackdown project found" in result.stdout

    @patch('ai_trackdown_pytools.commands.task.Project')
    @patch('ai_trackdown_pytools.commands.task.TicketManager')
    def test_task_list_command(self, mock_ticket_manager, mock_project):
        """Test task list command."""
        mock_project.exists.return_value = True
        mock_manager_instance = MagicMock()
        mock_ticket_manager.return_value = mock_manager_instance
        mock_manager_instance.list_tasks.return_value = []
        
        runner = CliRunner()
        result = runner.invoke(task.app, ["list"])
        
        assert result.exit_code == 0

    @patch('ai_trackdown_pytools.commands.task.Project')
    @patch('ai_trackdown_pytools.commands.task.TicketManager')
    def test_task_show_command(self, mock_ticket_manager, mock_project):
        """Test task show command."""
        mock_project.exists.return_value = True
        mock_manager_instance = MagicMock()
        mock_ticket_manager.return_value = mock_manager_instance
        
        # Mock task object
        mock_task = MagicMock()
        mock_task.id = "TSK-001"
        mock_task.title = "Test Task"
        mock_task.status = "open"
        mock_task.assignees = []
        mock_task.tags = ["task"]
        mock_task.metadata = {}
        mock_manager_instance.load_task.return_value = mock_task
        
        runner = CliRunner()
        result = runner.invoke(task.app, ["show", "TSK-001"])
        
        assert result.exit_code == 0

    @patch('ai_trackdown_pytools.commands.task.Project')
    @patch('ai_trackdown_pytools.commands.task.TicketManager')
    def test_task_show_not_found(self, mock_ticket_manager, mock_project):
        """Test task show command with non-existent task."""
        mock_project.exists.return_value = True
        mock_manager_instance = MagicMock()
        mock_ticket_manager.return_value = mock_manager_instance
        mock_manager_instance.load_task.return_value = None
        
        runner = CliRunner()
        result = runner.invoke(task.app, ["show", "TSK-999"])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestIssueCommand:
    """Test issue command functionality."""

    def test_issue_command_help(self):
        """Test issue command help."""
        runner = CliRunner()
        result = runner.invoke(issue.app, ["--help"])
        
        assert result.exit_code == 0
        assert "Issue" in result.stdout or "issue" in result.stdout.lower()

    @patch('ai_trackdown_pytools.commands.issue.Project')
    @patch('ai_trackdown_pytools.commands.issue.TicketManager')
    def test_issue_create_command(self, mock_ticket_manager, mock_project):
        """Test issue create command."""
        mock_project.exists.return_value = True
        mock_manager_instance = MagicMock()
        mock_ticket_manager.return_value = mock_manager_instance
        mock_manager_instance.create_task.return_value = "ISS-001"
        
        runner = CliRunner()
        result = runner.invoke(issue.app, [
            "create",
            "--title", "Test Issue",
            "--description", "Test Description",
            "--issue-type", "bug"
        ])
        
        assert result.exit_code == 0

    @patch('ai_trackdown_pytools.commands.issue.Project')
    def test_issue_create_no_project(self, mock_project):
        """Test issue create command without project."""
        mock_project.exists.return_value = False
        
        runner = CliRunner()
        result = runner.invoke(issue.app, [
            "create",
            "--title", "Test Issue"
        ])
        
        assert result.exit_code == 1
        assert "No AI Trackdown project found" in result.stdout


class TestStatusCommand:
    """Test status command functionality."""

    def test_status_command_help(self):
        """Test status command help."""
        runner = CliRunner()
        result = runner.invoke(status.app, ["--help"])
        
        assert result.exit_code == 0

    @patch('ai_trackdown_pytools.commands.status.Project')
    @patch('ai_trackdown_pytools.commands.status.TicketManager')
    def test_status_command_basic(self, mock_ticket_manager, mock_project):
        """Test basic status command."""
        mock_project.exists.return_value = True
        mock_manager_instance = MagicMock()
        mock_ticket_manager.return_value = mock_manager_instance
        mock_manager_instance.list_tasks.return_value = []
        
        runner = CliRunner()
        result = runner.invoke(status.app, [])
        
        assert result.exit_code == 0

    @patch('ai_trackdown_pytools.commands.status.Project')
    def test_status_command_no_project(self, mock_project):
        """Test status command without project."""
        mock_project.exists.return_value = False
        
        runner = CliRunner()
        result = runner.invoke(status.app, [])
        
        assert result.exit_code == 1
        assert "No AI Trackdown project found" in result.stdout


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_invalid_command(self):
        """Test invalid command handling."""
        runner = CliRunner()
        result = runner.invoke(app, ["invalid-command"])
        
        # Should exit with error
        assert result.exit_code != 0

    def test_missing_required_argument(self):
        """Test missing required argument handling."""
        runner = CliRunner()
        result = runner.invoke(task.app, ["show"])  # Missing task ID
        
        # Should exit with error
        assert result.exit_code != 0

    @patch('ai_trackdown_pytools.commands.task.Project')
    def test_project_not_found_error(self, mock_project):
        """Test project not found error handling."""
        mock_project.exists.return_value = False
        
        runner = CliRunner()
        result = runner.invoke(task.app, ["list"])
        
        assert result.exit_code == 1
        assert "No AI Trackdown project found" in result.stdout


class TestCLIUtilityFunctions:
    """Test CLI utility functions."""

    def test_health_command(self):
        """Test health command."""
        runner = CliRunner()
        result = runner.invoke(app, ["health"])
        
        # Should complete (may have warnings but shouldn't crash)
        assert result.exit_code in [0, 1]  # May exit 1 if health checks fail

    def test_doctor_command(self):
        """Test doctor command."""
        runner = CliRunner()
        result = runner.invoke(app, ["doctor"])
        
        # Should complete (may have warnings but shouldn't crash)
        assert result.exit_code in [0, 1]  # May exit 1 if issues found

    def test_config_command(self):
        """Test config command."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "--help"])
        
        assert result.exit_code == 0
