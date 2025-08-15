"""Comprehensive CLI option and command testing."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app
from ai_trackdown_pytools.core.project import Project


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_project_dir():
    """Create a temporary directory with a project for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test_project"
        project_path.mkdir()

        # Initialize a test project
        project = Project.create(project_path, name="Test Project")

        # Change to project directory for tests
        original_cwd = os.getcwd()
        os.chdir(str(project_path))

        try:
            yield project_path
        finally:
            os.chdir(original_cwd)


class TestMainCLIOptions:
    """Test main CLI global options and callbacks."""

    def test_version_option_short(self, cli_runner):
        """Test --version / -v option."""
        result = cli_runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert "aitrackdown v" in result.output

    def test_version_option_long(self, cli_runner):
        """Test --version option."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "aitrackdown v" in result.output

    def test_help_option_short(self, cli_runner):
        """Test -h option."""
        result = cli_runner.invoke(app, ["-h"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output

    def test_help_option_long(self, cli_runner):
        """Test --help option."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output

    def test_verbose_option_short(self, cli_runner, temp_project_dir):
        """Test -V verbose option."""
        result = cli_runner.invoke(app, ["-V", "info"])
        assert result.exit_code == 0
        # Verbose logging should be enabled

    def test_verbose_option_long(self, cli_runner, temp_project_dir):
        """Test --verbose option."""
        result = cli_runner.invoke(app, ["--verbose", "info"])
        assert result.exit_code == 0
        # Verbose logging should be enabled

    def test_config_option_short(self, cli_runner):
        """Test -c config file option."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("project:\n  name: Test Config\n")
            config_path = f.name

        try:
            result = cli_runner.invoke(app, ["-c", config_path, "info"])
            assert result.exit_code == 0
        finally:
            os.unlink(config_path)

    def test_config_option_long(self, cli_runner):
        """Test --config option."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("project:\n  name: Test Config\n")
            config_path = f.name

        try:
            result = cli_runner.invoke(app, ["--config", config_path, "info"])
            assert result.exit_code == 0
        finally:
            os.unlink(config_path)

    def test_project_dir_option_short(self, cli_runner, temp_project_dir):
        """Test -d project directory option."""
        result = cli_runner.invoke(app, ["-d", str(temp_project_dir), "info"])
        assert result.exit_code == 0

    def test_project_dir_option_long(self, cli_runner, temp_project_dir):
        """Test --project-dir option."""
        result = cli_runner.invoke(
            app, ["--project-dir", str(temp_project_dir), "info"]
        )
        assert result.exit_code == 0

    def test_project_dir_invalid_path(self, cli_runner):
        """Test --project-dir with invalid path."""
        result = cli_runner.invoke(app, ["--project-dir", "/nonexistent/path", "info"])
        assert result.exit_code == 1
        assert "Cannot access project directory" in result.output


class TestCommandGroups:
    """Test command group help and structure."""

    def test_init_command_help(self, cli_runner):
        """Test init command group help."""
        result = cli_runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize project" in result.output

    def test_status_command_help(self, cli_runner):
        """Test status command group help."""
        result = cli_runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show status" in result.output

    def test_create_command_help(self, cli_runner):
        """Test create command group help."""
        result = cli_runner.invoke(app, ["create", "--help"])
        assert result.exit_code == 0
        assert "Create tasks/issues" in result.output

    def test_template_command_help(self, cli_runner):
        """Test template command group help."""
        result = cli_runner.invoke(app, ["template", "--help"])
        assert result.exit_code == 0
        assert "Manage templates" in result.output

    def test_validate_command_help(self, cli_runner):
        """Test validate command group help."""
        result = cli_runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate data" in result.output

    def test_task_command_help(self, cli_runner):
        """Test task command group help."""
        result = cli_runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0
        assert "Task operations" in result.output

    def test_issue_command_help(self, cli_runner):
        """Test issue command group help."""
        result = cli_runner.invoke(app, ["issue", "--help"])
        assert result.exit_code == 0
        assert "Issue tracking" in result.output

    def test_epic_command_help(self, cli_runner):
        """Test epic command group help."""
        result = cli_runner.invoke(app, ["epic", "--help"])
        assert result.exit_code == 0
        assert "Epic management" in result.output

    def test_pr_command_help(self, cli_runner):
        """Test pr command group help."""
        result = cli_runner.invoke(app, ["pr", "--help"])
        assert result.exit_code == 0
        assert "Pull requests" in result.output

    def test_search_command_help(self, cli_runner):
        """Test search command group help."""
        result = cli_runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search" in result.output

    def test_portfolio_command_help(self, cli_runner):
        """Test portfolio command group help."""
        result = cli_runner.invoke(app, ["portfolio", "--help"])
        assert result.exit_code == 0
        assert "Portfolio mgmt" in result.output

    def test_sync_command_help(self, cli_runner):
        """Test sync command group help."""
        result = cli_runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "Sync platforms" in result.output

    def test_ai_command_help(self, cli_runner):
        """Test ai command group help."""
        result = cli_runner.invoke(app, ["ai", "--help"])
        assert result.exit_code == 0
        assert "AI commands" in result.output

    def test_migrate_command_help(self, cli_runner):
        """Test migrate command group help."""
        result = cli_runner.invoke(app, ["migrate", "--help"])
        assert result.exit_code == 0
        assert "Migration" in result.output


class TestInitCommandOptions:
    """Test init command options and subcommands."""

    def test_init_project_basic(self, cli_runner):
        """Test basic project initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "new_project"
            result = cli_runner.invoke(app, ["init", "project", str(project_path)])
            assert result.exit_code == 0
            assert "Project initialized successfully" in result.output
            assert (project_path / ".ai-trackdown").exists()

    def test_init_project_with_template(self, cli_runner):
        """Test project initialization with template."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "new_project"
            result = cli_runner.invoke(
                app, ["init", "project", str(project_path), "--template", "default"]
            )
            assert result.exit_code == 0

    def test_init_project_force_option(self, cli_runner):
        """Test project initialization with --force option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "force_project"
            # First create a project
            Project.create(project_path, name="Test Project")
            # Then test force reinitialization
            result = cli_runner.invoke(
                app, ["init", "project", str(project_path), "--force"]
            )
            assert result.exit_code == 0

    def test_init_project_no_git(self, cli_runner):
        """Test project initialization with --no-git option."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "new_project"
            result = cli_runner.invoke(
                app, ["init", "project", str(project_path), "--no-git"]
            )
            assert result.exit_code == 0

    def test_init_config_global(self, cli_runner):
        """Test config initialization with --global option."""
        result = cli_runner.invoke(app, ["init", "config", "--global"])
        assert result.exit_code == 0

    def test_init_config_with_editor(self, cli_runner):
        """Test config initialization with --editor option."""
        result = cli_runner.invoke(app, ["init", "config", "--editor", "vim"])
        assert result.exit_code == 0


class TestCreateCommandOptions:
    """Test create command options."""

    def test_create_task_help(self, cli_runner):
        """Test create task command help."""
        result = cli_runner.invoke(app, ["create", "task", "--help"])
        assert result.exit_code == 0
        assert "Create a new task" in result.output

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_create_task_basic(self, mock_create, mock_exists, cli_runner):
        """Test basic task creation."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(app, ["create", "task", "Test Task"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_create_task_with_description(self, mock_create, mock_exists, cli_runner):
        """Test task creation with description option."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(
            app, ["create", "task", "Test Task", "--description", "This is a test task"]
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_create_task_with_assignee(self, mock_create, mock_exists, cli_runner):
        """Test task creation with assignee option."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(
            app,
            ["create", "task", "Test Task", "--assignee", "alice", "--assignee", "bob"],
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_create_task_with_tags(self, mock_create, mock_exists, cli_runner):
        """Test task creation with tag options."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(
            app, ["create", "task", "Test Task", "--tag", "urgent", "--tag", "bug"]
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_create_task_with_priority(self, mock_create, mock_exists, cli_runner):
        """Test task creation with priority option."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        for priority in ["low", "medium", "high", "critical"]:
            result = cli_runner.invoke(
                app, ["create", "task", f"Test Task {priority}", "--priority", priority]
            )
            assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_create_task_with_template(self, mock_create, mock_exists, cli_runner):
        """Test task creation with template option."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(
            app, ["create", "task", "Test Task", "--template", "default"]
        )
        assert result.exit_code == 0


class TestTaskCommandOptions:
    """Test task command options."""

    def test_task_create_help(self, cli_runner):
        """Test task create command help."""
        result = cli_runner.invoke(app, ["task", "create", "--help"])
        assert result.exit_code == 0
        assert "Create a new task" in result.output

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_task_create_with_estimate(self, mock_create, mock_exists, cli_runner):
        """Test task creation with estimate option."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(
            app, ["task", "create", "Test Task", "--estimate", "2h"]
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_task_create_with_epic(self, mock_create, mock_exists, cli_runner):
        """Test task creation with epic option."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(
            app, ["task", "create", "Test Task", "--epic", "EP-001"]
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_task_create_with_parent(self, mock_create, mock_exists, cli_runner):
        """Test task creation with parent option."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        result = cli_runner.invoke(
            app, ["task", "create", "Test Task", "--parent", "TSK-000"]
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    def test_task_create_interactive_flag(self, mock_create, mock_exists, cli_runner):
        """Test task creation with interactive flag."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")

        # Mock interactive prompts
        with patch("rich.prompt.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["Test Task", "Test Description", "medium"]
            result = cli_runner.invoke(app, ["task", "create", "--interactive"])
            assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("ai_trackdown_pytools.utils.editor.EditorUtils.open_file")
    def test_task_create_edit_flag(
        self, mock_editor, mock_create, mock_exists, cli_runner
    ):
        """Test task creation with edit flag."""
        mock_exists.return_value = True
        mock_task = Mock(id="TSK-001", file_path="/path/to/task.md")
        mock_create.return_value = mock_task
        mock_editor.return_value = True

        result = cli_runner.invoke(app, ["task", "create", "Test Task", "--edit"])
        assert result.exit_code == 0
        mock_editor.assert_called_once()


class TestStatusCommandOptions:
    """Test status command options."""

    def test_status_project_help(self, cli_runner):
        """Test status project command help."""
        result = cli_runner.invoke(app, ["status", "project", "--help"])
        assert result.exit_code == 0
        assert "Show project status" in result.output

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.project.Project.load")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.git.GitUtils")
    def test_status_project_basic(
        self, mock_git, mock_task_mgr, mock_load, mock_exists, cli_runner
    ):
        """Test basic project status."""
        mock_exists.return_value = True
        mock_project = Mock(name="Test Project", description="Test Description")
        mock_load.return_value = mock_project

        result = cli_runner.invoke(app, ["status", "project"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.project.Project.load")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.git.GitUtils")
    def test_status_project_verbose(
        self, mock_git, mock_task_mgr, mock_load, mock_exists, cli_runner
    ):
        """Test project status with verbose option."""
        mock_exists.return_value = True
        mock_project = Mock(name="Test Project", description="Test Description")
        mock_load.return_value = mock_project

        result = cli_runner.invoke(app, ["status", "project", "--verbose"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.project.Project.load")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.git.GitUtils")
    def test_status_project_custom_path(
        self,
        mock_git,
        mock_task_mgr,
        mock_load,
        mock_exists,
        cli_runner,
        temp_project_dir,
    ):
        """Test project status with custom path."""
        mock_exists.return_value = True
        mock_project = Mock(name="Test Project", description="Test Description")
        mock_load.return_value = mock_project

        result = cli_runner.invoke(app, ["status", "project", str(temp_project_dir)])
        assert result.exit_code == 0


class TestSearchCommandOptions:
    """Test search command options."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_basic_query(self, mock_task_mgr, mock_exists, cli_runner):
        """Test basic search query."""
        mock_exists.return_value = True
        mock_tasks = [
            Mock(
                id="TSK-001",
                title="Test Task",
                description="Test description",
                tags=["test"],
                status="open",
            ),
            Mock(
                id="TSK-002",
                title="Another Task",
                description="Another description",
                tags=["feature"],
                status="in_progress",
            ),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        result = cli_runner.invoke(app, ["search", "test"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_with_type_filter(self, mock_task_mgr, mock_exists, cli_runner):
        """Test search with type filter."""
        mock_exists.return_value = True
        mock_tasks = [
            Mock(
                id="TSK-001",
                title="Test Task",
                description="Test description",
                tags=["test", "task"],
                status="open",
            ),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        result = cli_runner.invoke(app, ["search", "test", "--type", "task"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_with_status_filter(self, mock_task_mgr, mock_exists, cli_runner):
        """Test search with status filter."""
        mock_exists.return_value = True
        mock_tasks = [
            Mock(
                id="TSK-001",
                title="Test Task",
                description="Test description",
                tags=["test"],
                status="open",
            ),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        result = cli_runner.invoke(app, ["search", "test", "--status", "open"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_search_with_limit(self, mock_task_mgr, mock_exists, cli_runner):
        """Test search with limit option."""
        mock_exists.return_value = True
        mock_tasks = [
            Mock(
                id=f"TSK-{i:03d}",
                title=f"Task {i}",
                description="Test",
                tags=["test"],
                status="open",
            )
            for i in range(20)
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        result = cli_runner.invoke(app, ["search", "test", "--limit", "5"])
        assert result.exit_code == 0


class TestEditCommandOptions:
    """Test edit command options."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.editor.EditorUtils.open_file")
    def test_edit_task_basic(self, mock_editor, mock_task_mgr, mock_exists, cli_runner):
        """Test basic task editing."""
        mock_exists.return_value = True
        mock_task = Mock(id="TSK-001", file_path="/path/to/task.md")
        mock_task_mgr.return_value.load_task.return_value = mock_task
        mock_editor.return_value = True

        result = cli_runner.invoke(app, ["edit", "TSK-001"])
        assert result.exit_code == 0
        mock_editor.assert_called_once()

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.editor.EditorUtils.open_file")
    def test_edit_task_with_editor(
        self, mock_editor, mock_task_mgr, mock_exists, cli_runner
    ):
        """Test task editing with specific editor."""
        mock_exists.return_value = True
        mock_task = Mock(id="TSK-001", file_path="/path/to/task.md")
        mock_task_mgr.return_value.load_task.return_value = mock_task
        mock_editor.return_value = True

        result = cli_runner.invoke(app, ["edit", "TSK-001", "--editor", "vim"])
        assert result.exit_code == 0
        mock_editor.assert_called_once()


class TestConfigCommandOptions:
    """Test config command options."""

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_config_list_all(self, mock_load, cli_runner):
        """Test config list all option."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"test": "value"}
        mock_config.config_path = "/path/to/config"
        mock_load.return_value = mock_config

        result = cli_runner.invoke(app, ["config", "--list"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_config_get_value(self, mock_load, cli_runner):
        """Test getting configuration value."""
        mock_config = Mock()
        mock_config.get.return_value = "test_value"
        mock_load.return_value = mock_config

        result = cli_runner.invoke(app, ["config", "test_key"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_config_set_value(self, mock_load, cli_runner):
        """Test setting configuration value."""
        mock_config = Mock()
        mock_load.return_value = mock_config

        result = cli_runner.invoke(app, ["config", "test_key", "test_value"])
        assert result.exit_code == 0
        mock_config.set.assert_called_once_with("test_key", "test_value")
        mock_config.save.assert_called_once()

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_config_global_flag(self, mock_load, cli_runner):
        """Test config with global flag."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"test": "value"}
        mock_config.config_path = "/path/to/config"
        mock_load.return_value = mock_config

        result = cli_runner.invoke(app, ["config", "--global", "--list"])
        assert result.exit_code == 0


class TestValidateCommandOptions:
    """Test validate command options."""

    def test_validate_help(self, cli_runner):
        """Test validate command help."""
        result = cli_runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        assert "Validate project structure" in result.output

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.utils.validation.validate_project_structure")
    def test_validate_project(self, mock_validate, mock_exists, cli_runner):
        """Test project validation."""
        mock_exists.return_value = True
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}

        result = cli_runner.invoke(app, ["validate", "project"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.validation.validate_task_file")
    def test_validate_tasks(
        self, mock_validate_task, mock_task_mgr, mock_exists, cli_runner
    ):
        """Test task validation."""
        mock_exists.return_value = True
        mock_tasks = [Mock(id="TSK-001", file_path="/path/to/task.md")]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks
        mock_validate_task.return_value = {"valid": True, "errors": [], "warnings": []}

        result = cli_runner.invoke(app, ["validate", "tasks"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.config.Config.load")
    @patch("ai_trackdown_pytools.utils.validation.SchemaValidator")
    def test_validate_config(self, mock_validator_class, mock_load, cli_runner):
        """Test config validation."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {"test": "value"}
        mock_load.return_value = mock_config

        mock_validator = Mock()
        mock_validator.validate_config.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        mock_validator_class.return_value = mock_validator

        result = cli_runner.invoke(app, ["validate", "config"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.utils.validation.validate_project_structure")
    def test_validate_with_custom_path(
        self, mock_validate, mock_exists, cli_runner, temp_project_dir
    ):
        """Test validation with custom path."""
        mock_exists.return_value = True
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}

        result = cli_runner.invoke(
            app, ["validate", "project", "--path", str(temp_project_dir)]
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.utils.validation.validate_project_structure")
    def test_validate_with_fix_flag(self, mock_validate, mock_exists, cli_runner):
        """Test validation with fix flag."""
        mock_exists.return_value = True
        mock_validate.return_value = {"valid": True, "errors": [], "warnings": []}

        result = cli_runner.invoke(app, ["validate", "project", "--fix"])
        assert result.exit_code == 0


class TestBuiltinCommands:
    """Test built-in commands (info, health, doctor, version)."""

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_info_command(self, mock_system_info, cli_runner):
        """Test info command."""
        mock_system_info.return_value = {
            "python_version": "3.9.0",
            "platform": "Linux",
            "architecture": "x86_64",
            "cwd": "/test",
            "git_repo": "Yes",
            "config_file": "/test/config.yaml",
            "templates_dir": "/test/templates",
            "schema_dir": "/test/schemas",
        }

        result = cli_runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "System Information" in result.output

    @patch("ai_trackdown_pytools.utils.health.check_health")
    def test_health_command_pass(self, mock_health, cli_runner):
        """Test health command when checks pass."""
        mock_health.return_value = {
            "overall": True,
            "checks": {
                "dependencies": {
                    "status": True,
                    "message": "All dependencies available",
                }
            },
        }

        result = cli_runner.invoke(app, ["health"])
        assert result.exit_code == 0
        assert "health check passed" in result.output

    @patch("ai_trackdown_pytools.utils.health.check_health")
    def test_health_command_fail(self, mock_health, cli_runner):
        """Test health command when checks fail."""
        mock_health.return_value = {
            "overall": False,
            "checks": {
                "dependencies": {"status": False, "message": "Missing dependency"}
            },
        }

        result = cli_runner.invoke(app, ["health"])
        assert result.exit_code == 1
        assert "health check failed" in result.output

    @patch("ai_trackdown_pytools.utils.health.check_health")
    @patch("ai_trackdown_pytools.utils.health.check_project_health")
    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.config.Config.load")
    @patch("ai_trackdown_pytools.utils.git.GitUtils")
    def test_doctor_command(
        self,
        mock_git,
        mock_config,
        mock_exists,
        mock_project_health,
        mock_health,
        cli_runner,
    ):
        """Test doctor command."""
        mock_health.return_value = {
            "overall": True,
            "checks": {"dependencies": {"status": True, "message": "OK"}},
        }
        mock_exists.return_value = True
        mock_project_health.return_value = {
            "checks": {"structure": {"status": True, "message": "OK"}}
        }
        mock_config.return_value = Mock(
            config_path="/test/config", project_root="/test"
        )

        result = cli_runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "System Health" in result.output

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_version_command(self, mock_system_info, cli_runner):
        """Test version command."""
        mock_system_info.return_value = {
            "python_version": "3.9.0",
            "platform": "Linux",
            "architecture": "x86_64",
            "cwd": "/test",
            "git_repo": "Yes",
            "config_file": "/test/config.yaml",
            "project_root": "/test",
            "templates_dir": "/test/templates",
            "schema_dir": "/test/schemas",
        }

        result = cli_runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Version Information" in result.output


class TestInteractivePrompts:
    """Test interactive prompt functionality."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_task_creation(
        self, mock_prompt, mock_create, mock_exists, cli_runner
    ):
        """Test interactive task creation prompts."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")
        mock_prompt.side_effect = ["Interactive Task", "Test description", "high"]

        result = cli_runner.invoke(app, ["task", "create", "--interactive"])
        assert result.exit_code == 0
        assert mock_prompt.call_count == 3

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_task_creation_no_title(
        self, mock_prompt, mock_create, mock_exists, cli_runner
    ):
        """Test interactive task creation when no title provided."""
        mock_exists.return_value = True
        mock_create.return_value = Mock(id="TSK-001")
        mock_prompt.side_effect = ["Prompted Task", "Prompted description", "medium"]

        result = cli_runner.invoke(app, ["task", "create"])
        assert result.exit_code == 0
        assert mock_prompt.call_count >= 1


class TestErrorConditions:
    """Test error conditions and invalid inputs."""

    def test_command_without_project_context(self, cli_runner):
        """Test commands that require project context when no project exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)

            result = cli_runner.invoke(app, ["task", "create", "Test Task"])
            assert result.exit_code == 1
            assert "No AI Trackdown project found" in result.output

    def test_invalid_priority_value(self, cli_runner, temp_project_dir):
        """Test invalid priority value handling."""
        # Note: Typer handles choice validation automatically
        # This test might need to be adjusted based on actual validation behavior
        pass

    def test_nonexistent_task_id(self, cli_runner, temp_project_dir):
        """Test editing nonexistent task."""
        result = cli_runner.invoke(app, ["edit", "NONEXISTENT-001"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_invalid_config_file(self, cli_runner):
        """Test invalid config file path."""
        result = cli_runner.invoke(
            app, ["--config", "/nonexistent/config.yaml", "info"]
        )
        # Config loading failure should be handled gracefully
        # Actual behavior depends on implementation

    def test_missing_required_argument(self, cli_runner):
        """Test missing required arguments."""
        result = cli_runner.invoke(app, ["edit"])
        assert result.exit_code != 0  # Should show usage/help


class TestOutputFormats:
    """Test different output formats and display options."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_table_output_format(self, mock_task_mgr, mock_exists, cli_runner):
        """Test table output format in search results."""
        mock_exists.return_value = True
        mock_tasks = [
            Mock(
                id="TSK-001",
                title="Task 1",
                description="Desc 1",
                tags=["test"],
                status="open",
            ),
            Mock(
                id="TSK-002",
                title="Task 2",
                description="Desc 2",
                tags=["feature"],
                status="done",
            ),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        result = cli_runner.invoke(app, ["search", "task"])
        assert result.exit_code == 0
        # Check that table-like output is present
        assert "TSK-001" in result.output
        assert "TSK-002" in result.output

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_panel_output_format(self, mock_system_info, cli_runner):
        """Test panel output format in info command."""
        mock_system_info.return_value = {
            "python_version": "3.9.0",
            "platform": "Linux",
            "architecture": "x86_64",
            "cwd": "/test",
            "git_repo": "Yes",
            "config_file": "/test/config.yaml",
            "templates_dir": "/test/templates",
            "schema_dir": "/test/schemas",
        }

        result = cli_runner.invoke(app, ["info"])
        assert result.exit_code == 0
        # Rich panel should create bordered output
        assert "Python:" in result.output


class TestCLIWorkflows:
    """Test multi-command workflows and state persistence."""

    def test_init_then_create_workflow(self, cli_runner):
        """Test initializing project then creating task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "workflow_project"

            # Initialize project
            result1 = cli_runner.invoke(app, ["init", "project", str(project_path)])
            assert result1.exit_code == 0

            # Change to project directory
            os.chdir(str(project_path))

            # Create task
            with patch(
                "ai_trackdown_pytools.core.task.TaskManager.create_task"
            ) as mock_create:
                mock_create.return_value = Mock(id="TSK-001")
                result2 = cli_runner.invoke(app, ["task", "create", "Workflow Task"])
                assert result2.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_create_then_search_workflow(self, mock_task_mgr, mock_exists, cli_runner):
        """Test creating task then searching for it."""
        mock_exists.return_value = True

        # Mock task creation
        created_task = Mock(
            id="TSK-001",
            title="Created Task",
            description="Test",
            tags=["test"],
            status="open",
        )
        mock_task_mgr.return_value.create_task.return_value = created_task
        mock_task_mgr.return_value.list_tasks.return_value = [created_task]

        # Create task
        result1 = cli_runner.invoke(app, ["task", "create", "Created Task"])
        assert result1.exit_code == 0

        # Search for task
        result2 = cli_runner.invoke(app, ["search", "Created"])
        assert result2.exit_code == 0
        assert "TSK-001" in result2.output


class TestGlobalOptionCombinations:
    """Test combinations of global options."""

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_verbose_with_config_file(self, mock_system_info, cli_runner):
        """Test verbose flag with custom config file."""
        mock_system_info.return_value = {
            "python_version": "3.9.0",
            "platform": "Linux",
            "architecture": "x86_64",
            "cwd": "/test",
            "git_repo": "Yes",
            "config_file": "/test/config.yaml",
            "templates_dir": "/test/templates",
            "schema_dir": "/test/schemas",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("project:\n  name: Test Config\n")
            config_path = f.name

        try:
            result = cli_runner.invoke(
                app, ["--verbose", "--config", config_path, "info"]
            )
            assert result.exit_code == 0
        finally:
            os.unlink(config_path)

    def test_verbose_with_project_dir(self, cli_runner, temp_project_dir):
        """Test verbose flag with project directory."""
        with patch("ai_trackdown_pytools.utils.system.get_system_info") as mock_info:
            mock_info.return_value = {
                "python_version": "3.9.0",
                "platform": "Linux",
                "architecture": "x86_64",
                "cwd": str(temp_project_dir),
                "git_repo": "Yes",
                "config_file": "/test/config.yaml",
                "templates_dir": "/test/templates",
                "schema_dir": "/test/schemas",
            }

            result = cli_runner.invoke(
                app, ["--verbose", "--project-dir", str(temp_project_dir), "info"]
            )
            assert result.exit_code == 0

    def test_all_global_options_combined(self, cli_runner, temp_project_dir):
        """Test all global options used together."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("project:\n  name: Combined Test\n")
            config_path = f.name

        try:
            with patch(
                "ai_trackdown_pytools.utils.system.get_system_info"
            ) as mock_info:
                mock_info.return_value = {
                    "python_version": "3.9.0",
                    "platform": "Linux",
                    "architecture": "x86_64",
                    "cwd": str(temp_project_dir),
                    "git_repo": "Yes",
                    "config_file": config_path,
                    "templates_dir": "/test/templates",
                    "schema_dir": "/test/schemas",
                }

                result = cli_runner.invoke(
                    app,
                    [
                        "--verbose",
                        "--config",
                        config_path,
                        "--project-dir",
                        str(temp_project_dir),
                        "info",
                    ],
                )
                assert result.exit_code == 0
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    pytest.main([__file__])
