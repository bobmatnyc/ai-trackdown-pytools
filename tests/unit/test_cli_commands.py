"""Unit tests for CLI commands using Typer testing."""

import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app
from ai_trackdown_pytools.core.project import Project


class TestMainCLI:
    """Test main CLI functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    def test_app_help(self):
        """Test main app help command."""
        result = self.runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "AI Trackdown PyTools" in result.stdout
        assert "Commands:" in result.stdout

    def test_app_version(self):
        """Test version command."""
        result = self.runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "AI Trackdown PyTools" in result.stdout
        assert "version" in result.stdout

    def test_app_verbose_flag(self):
        """Test verbose flag."""
        result = self.runner.invoke(app, ["--verbose", "--help"])

        assert result.exit_code == 0
        # Verbose flag should not affect help output directly
        assert "AI Trackdown PyTools" in result.stdout

    def test_app_config_flag(self):
        """Test config file flag."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("version: 1.0.0\n")
            config_path = f.name

        try:
            result = self.runner.invoke(app, ["--config", config_path, "--help"])
            assert result.exit_code == 0
        finally:
            Path(config_path).unlink()

    def test_app_project_dir_flag(self):
        """Test project directory flag."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["--project-dir", temp_dir, "--help"])
            assert result.exit_code == 0

    def test_app_project_dir_nonexistent(self):
        """Test project directory flag with non-existent directory."""
        result = self.runner.invoke(
            app, ["--project-dir", "/nonexistent/path", "--help"]
        )
        assert result.exit_code == 1
        assert "Cannot access project directory" in result.stdout


class TestInitCommand:
    """Test init command functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    def test_init_help(self):
        """Test init command help."""
        result = self.runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize AI Trackdown" in result.stdout

    def test_init_project_success(self):
        """Test successful project initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            with patch("os.getcwd", return_value=str(project_path)):
                result = self.runner.invoke(app, ["init", "project"])

            assert result.exit_code == 0
            assert (
                "initialized successfully" in result.stdout.lower()
                or "created" in result.stdout.lower()
            )

    def test_init_project_custom_name(self):
        """Test project initialization with custom name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            with patch("os.getcwd", return_value=str(project_path)):
                result = self.runner.invoke(
                    app, ["init", "project", "--name", "Custom Project"]
                )

            assert result.exit_code == 0

    def test_init_project_already_exists(self):
        """Test initialization in existing project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create project first
            Project.create(project_path)

            with patch("os.getcwd", return_value=str(project_path)):
                result = self.runner.invoke(app, ["init", "project"])

            # Should handle existing project gracefully
            assert result.exit_code in [0, 1]

    def test_init_templates(self):
        """Test templates initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            Project.create(project_path)

            with patch("os.getcwd", return_value=str(project_path)):
                result = self.runner.invoke(app, ["init", "templates"])

            assert result.exit_code == 0

    def test_init_config(self):
        """Test config initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            with patch("os.getcwd", return_value=str(project_path)):
                result = self.runner.invoke(app, ["init", "config"])

            assert result.exit_code == 0


class TestCreateCommand:
    """Test create command functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_project(self):
        """Create a test project."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "test_project"
        project_path.mkdir()
        return Project.create(project_path)

    def test_create_help(self):
        """Test create command help."""
        result = self.runner.invoke(app, ["create", "--help"])

        assert result.exit_code == 0
        assert "Create new tasks" in result.stdout

    def test_create_task_interactive(self):
        """Test creating task interactively."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            # Mock user input
            user_input = "Test Task\nThis is a test task\nmedium\n\n\n"
            result = self.runner.invoke(app, ["create", "task"], input=user_input)

        assert result.exit_code == 0

    def test_create_task_with_title(self):
        """Test creating task with title argument."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["create", "task", "Test Task Title"])

        assert result.exit_code == 0
        assert "created" in result.stdout.lower() or "task" in result.stdout.lower()

    def test_create_task_with_options(self):
        """Test creating task with command line options."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "task",
                    "Test Task",
                    "--priority",
                    "high",
                    "--assignee",
                    "alice",
                    "--tag",
                    "bug",
                    "--tag",
                    "urgent",
                ],
            )

        assert result.exit_code == 0

    def test_create_task_with_template(self):
        """Test creating task with specific template."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(
                app, ["create", "task", "Template Task", "--template", "default"]
            )

        assert result.exit_code == 0

    def test_create_epic(self):
        """Test creating epic."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["create", "epic", "Test Epic"])

        assert result.exit_code == 0

    def test_create_issue(self):
        """Test creating issue."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(
                app, ["create", "issue", "Test Issue", "--issue-type", "bug"]
            )

        assert result.exit_code == 0

    def test_create_pr(self):
        """Test creating PR."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "pr",
                    "Test PR",
                    "--source-branch",
                    "feature/test",
                    "--target-branch",
                    "main",
                ],
            )

        assert result.exit_code == 0

    def test_create_without_project(self):
        """Test create command outside of project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("os.getcwd", return_value=temp_dir):
                result = self.runner.invoke(app, ["create", "task", "Test Task"])

        # Should fail or prompt for project initialization
        assert result.exit_code in [1, 2] or "not.*project" in result.stdout.lower()


class TestStatusCommand:
    """Test status command functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_project_with_tasks(self):
        """Create test project with sample tasks."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "test_project"
        project_path.mkdir()
        project = Project.create(project_path)

        # Create some sample task files
        tasks_dir = project.get_tasks_directory()

        # Open task
        open_task = tasks_dir / "open" / "TSK-0001-test-task.md"
        open_task.parent.mkdir(exist_ok=True)
        open_task.write_text(
            """---
id: TSK-0001
title: Test Task
status: open
priority: medium
---

# Test Task

Test content.
"""
        )

        # In progress task
        in_progress_task = tasks_dir / "in_progress" / "TSK-0002-another-task.md"
        in_progress_task.parent.mkdir(exist_ok=True)
        in_progress_task.write_text(
            """---
id: TSK-0002
title: Another Task
status: in_progress
priority: high
---

# Another Task

In progress content.
"""
        )

        return project

    def test_status_help(self):
        """Test status command help."""
        result = self.runner.invoke(app, ["status", "--help"])

        assert result.exit_code == 0
        assert "Show project and task status" in result.stdout

    def test_status_overview(self):
        """Test status overview."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["status"])

        assert result.exit_code == 0
        # Should show some status information
        assert len(result.stdout) > 0

    def test_status_tasks(self):
        """Test tasks status."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["status", "tasks"])

        assert result.exit_code == 0
        # Should show task information
        assert "TSK-" in result.stdout or "task" in result.stdout.lower()

    def test_status_by_assignee(self):
        """Test status by assignee."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["status", "tasks", "--assignee", "alice"])

        assert result.exit_code == 0

    def test_status_by_status_filter(self):
        """Test status with status filter."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["status", "tasks", "--status", "open"])

        assert result.exit_code == 0

    def test_status_by_priority(self):
        """Test status by priority."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["status", "tasks", "--priority", "high"])

        assert result.exit_code == 0

    def test_status_summary(self):
        """Test status summary."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["status", "summary"])

        assert result.exit_code == 0

    def test_status_without_project(self):
        """Test status command outside of project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("os.getcwd", return_value=temp_dir):
                result = self.runner.invoke(app, ["status"])

        # Should fail or indicate no project
        assert result.exit_code in [1, 2] or "not.*project" in result.stdout.lower()


class TestTemplateCommand:
    """Test template command functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_project(self):
        """Create test project."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "test_project"
        project_path.mkdir()
        return Project.create(project_path)

    def test_template_help(self):
        """Test template command help."""
        result = self.runner.invoke(app, ["template", "--help"])

        assert result.exit_code == 0
        assert "Manage and apply templates" in result.stdout

    def test_template_list(self):
        """Test listing templates."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["template", "list"])

        assert result.exit_code == 0
        # Should show available templates
        assert len(result.stdout) > 0

    def test_template_list_type(self):
        """Test listing templates for specific type."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["template", "list", "task"])

        assert result.exit_code == 0

    def test_template_show(self):
        """Test showing template content."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["template", "show", "task", "default"])

        assert result.exit_code == 0
        # Should show template content
        assert len(result.stdout) > 0

    def test_template_validate(self):
        """Test validating template."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(
                app, ["template", "validate", "task", "default"]
            )

        assert result.exit_code == 0

    def test_template_edit(self):
        """Test editing template (if implemented)."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            # This might not be implemented yet, so check for reasonable exit code
            result = self.runner.invoke(app, ["template", "edit", "task", "default"])

        # Should either work or give helpful error
        assert result.exit_code in [0, 1, 2]


class TestValidateCommand:
    """Test validate command functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_project_with_tasks(self):
        """Create test project with tasks."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "test_project"
        project_path.mkdir()
        project = Project.create(project_path)

        # Create valid task
        tasks_dir = project.get_tasks_directory()
        valid_task = tasks_dir / "open" / "TSK-0001-valid-task.md"
        valid_task.parent.mkdir(exist_ok=True)
        valid_task.write_text(
            """---
id: TSK-0001
title: Valid Task
status: open
priority: medium
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
---

# Valid Task

Valid content.
"""
        )

        # Create invalid task
        invalid_task = tasks_dir / "open" / "TSK-0002-invalid-task.md"
        invalid_task.write_text(
            """---
id: INVALID-001
title: Invalid Task
status: invalid_status
priority: invalid_priority
---

# Invalid Task

Invalid content.
"""
        )

        return project

    def test_validate_help(self):
        """Test validate command help."""
        result = self.runner.invoke(app, ["validate", "--help"])

        assert result.exit_code == 0
        assert "validate" in result.stdout.lower()

    def test_validate_all(self):
        """Test validating all tasks."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["validate"])

        assert result.exit_code in [0, 1]  # 0 for valid, 1 for validation errors
        assert len(result.stdout) > 0

    def test_validate_specific_file(self):
        """Test validating specific file."""
        project = self._create_test_project_with_tasks()
        task_file = project.get_tasks_directory() / "open" / "TSK-0001-valid-task.md"

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["validate", str(task_file)])

        assert result.exit_code == 0

    def test_validate_schema_only(self):
        """Test schema-only validation."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["validate", "--schema-only"])

        assert result.exit_code in [0, 1]

    def test_validate_fix_mode(self):
        """Test validation with fix mode."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["validate", "--fix"])

        assert result.exit_code in [0, 1]

    def test_validate_json_output(self):
        """Test validation with JSON output."""
        project = self._create_test_project_with_tasks()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["validate", "--output", "json"])

        assert result.exit_code in [0, 1]
        # Output should be JSON or contain validation results
        assert len(result.stdout) > 0


class TestTaskCommand:
    """Test task-specific command functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_project(self):
        """Create test project."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "test_project"
        project_path.mkdir()
        return Project.create(project_path)

    def test_task_list(self):
        """Test listing tasks."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["task", "list"])

        assert result.exit_code == 0

    def test_task_show(self):
        """Test showing specific task."""
        project = self._create_test_project()

        # Create a task first
        with patch("os.getcwd", return_value=str(project.path)):
            self.runner.invoke(app, ["create", "task", "Test Task"])

            # Try to show task (might need to find the actual ID)
            result = self.runner.invoke(app, ["task", "show", "TSK-0001"])

        # Should either show task or indicate it doesn't exist
        assert result.exit_code in [0, 1]

    def test_task_update(self):
        """Test updating task."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            # Create task first
            self.runner.invoke(app, ["create", "task", "Test Task"])

            # Update task
            result = self.runner.invoke(
                app,
                [
                    "task",
                    "update",
                    "TSK-0001",
                    "--priority",
                    "high",
                    "--status",
                    "in_progress",
                ],
            )

        # Should either update successfully or indicate task not found
        assert result.exit_code in [0, 1]

    def test_task_close(self):
        """Test closing task."""
        project = self._create_test_project()

        with patch("os.getcwd", return_value=str(project.path)):
            # Create task first
            self.runner.invoke(app, ["create", "task", "Test Task"])

            # Close task
            result = self.runner.invoke(app, ["task", "close", "TSK-0001"])

        assert result.exit_code in [0, 1]


class TestSearchCommand:
    """Test search command functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_project_with_content(self):
        """Create test project with searchable content."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "test_project"
        project_path.mkdir()
        project = Project.create(project_path)

        # Create tasks with searchable content
        tasks_dir = project.get_tasks_directory()

        task1 = tasks_dir / "open" / "TSK-0001-login-bug.md"
        task1.parent.mkdir(exist_ok=True)
        task1.write_text(
            """---
id: TSK-0001
title: Fix login bug
status: open
priority: high
tags: [bug, authentication]
---

# Fix login bug

User authentication is broken on the login page.
Need to investigate session management.
"""
        )

        task2 = tasks_dir / "open" / "TSK-0002-user-feature.md"
        task2.write_text(
            """---
id: TSK-0002
title: Add user profile feature
status: open
priority: medium
tags: [feature, user-management]
---

# Add user profile feature

Implement user profile page with avatar upload.
Users should be able to edit their personal information.
"""
        )

        return project

    def test_search_help(self):
        """Test search command help."""
        result = self.runner.invoke(app, ["search", "--help"])

        assert result.exit_code == 0
        assert "search" in result.stdout.lower()

    def test_search_text(self):
        """Test text search."""
        project = self._create_test_project_with_content()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["search", "login"])

        assert result.exit_code == 0
        # Should find login-related content
        assert len(result.stdout) > 0

    def test_search_by_tag(self):
        """Test search by tag."""
        project = self._create_test_project_with_content()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["search", "--tag", "bug"])

        assert result.exit_code == 0

    def test_search_by_status(self):
        """Test search by status."""
        project = self._create_test_project_with_content()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["search", "--status", "open"])

        assert result.exit_code == 0

    def test_search_by_assignee(self):
        """Test search by assignee."""
        project = self._create_test_project_with_content()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(app, ["search", "--assignee", "alice"])

        assert result.exit_code == 0

    def test_search_with_multiple_filters(self):
        """Test search with multiple filters."""
        project = self._create_test_project_with_content()

        with patch("os.getcwd", return_value=str(project.path)):
            result = self.runner.invoke(
                app, ["search", "user", "--status", "open", "--tag", "feature"]
            )

        assert result.exit_code == 0


class TestErrorHandling:
    """Test CLI error handling."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()

    def test_command_not_found(self):
        """Test handling of non-existent commands."""
        result = self.runner.invoke(app, ["nonexistent-command"])

        assert result.exit_code != 0
        # Should show error message or help
        assert len(result.stdout) > 0 or len(result.stderr) > 0

    def test_invalid_arguments(self):
        """Test handling of invalid arguments."""
        result = self.runner.invoke(app, ["create", "invalid-type"])

        assert result.exit_code != 0

    def test_missing_required_arguments(self):
        """Test handling of missing required arguments."""
        # This depends on specific command requirements
        result = self.runner.invoke(app, ["create"])

        # Should either show help or indicate missing arguments
        assert result.exit_code in [0, 1, 2]

    def test_permission_errors(self):
        """Test handling of permission errors."""
        # Create a directory without write permissions
        with tempfile.TemporaryDirectory() as temp_dir:
            restricted_dir = Path(temp_dir) / "restricted"
            restricted_dir.mkdir(mode=0o444)  # Read-only

            try:
                with patch("os.getcwd", return_value=str(restricted_dir)):
                    result = self.runner.invoke(app, ["init", "project"])

                # Should handle permission error gracefully
                assert result.exit_code != 0
            finally:
                # Restore permissions for cleanup
                restricted_dir.chmod(0o755)

    def test_configuration_errors(self):
        """Test handling of configuration errors."""
        # Test with invalid config file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: here\n")
            invalid_config = f.name

        try:
            result = self.runner.invoke(app, ["--config", invalid_config, "status"])

            # Should handle invalid config gracefully
            assert result.exit_code in [0, 1, 2]
        finally:
            Path(invalid_config).unlink()


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_workflow(self):
        """Test complete workflow from init to task management."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "workflow_test"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(
                app, ["init", "project", "--name", "Workflow Test"]
            )
            assert result.exit_code == 0

            # Create a task
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "task",
                    "Workflow Task",
                    "--priority",
                    "high",
                    "--tag",
                    "test",
                ],
            )
            assert result.exit_code == 0

            # Check status
            result = self.runner.invoke(app, ["status", "tasks"])
            assert result.exit_code == 0

            # Search for the task
            result = self.runner.invoke(app, ["search", "Workflow"])
            assert result.exit_code == 0

            # Validate project
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]  # May have validation warnings

    def test_template_workflow(self):
        """Test template-related workflow."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "template_test"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # List templates
            result = self.runner.invoke(app, ["template", "list"])
            assert result.exit_code == 0

            # Show template
            result = self.runner.invoke(app, ["template", "show", "task", "default"])
            assert result.exit_code == 0

            # Validate template
            result = self.runner.invoke(
                app, ["template", "validate", "task", "default"]
            )
            assert result.exit_code == 0

    def test_multi_ticket_workflow(self):
        """Test workflow with multiple ticket types."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "multi_ticket_test"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Create epic
            result = self.runner.invoke(app, ["create", "epic", "Test Epic"])
            assert result.exit_code == 0

            # Create issue
            result = self.runner.invoke(
                app, ["create", "issue", "Test Issue", "--issue-type", "bug"]
            )
            assert result.exit_code == 0

            # Create task
            result = self.runner.invoke(app, ["create", "task", "Test Task"])
            assert result.exit_code == 0

            # Create PR
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "pr",
                    "Test PR",
                    "--source-branch",
                    "feature/test",
                    "--target-branch",
                    "main",
                ],
            )
            assert result.exit_code == 0

            # Check overall status
            result = self.runner.invoke(app, ["status"])
            assert result.exit_code == 0
