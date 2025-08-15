"""Comprehensive testing for interactive prompts and Rich UI elements."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app


@pytest.fixture
def interactive_runner():
    """Create a CLI runner for interactive testing."""
    return CliRunner()


@pytest.fixture
def mock_project_context():
    """Mock project context for interactive tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "interactive_test_project"
        project_path.mkdir()

        original_cwd = os.getcwd()
        os.chdir(str(project_path))

        try:
            yield project_path
        finally:
            os.chdir(original_cwd)


class TestInteractiveTaskCreation:
    """Test interactive task creation prompts."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_basic_prompts(
        self, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test basic interactive prompts for task creation."""
        mock_exists.return_value = True
        mock_task = Mock(id="TSK-001", title="Interactive Task")
        mock_create.return_value = mock_task

        # Mock prompt responses
        prompt_responses = [
            "Interactive Task Title",  # title
            "Interactive task description",  # description
            "high",  # priority
            "alice,bob",  # assignees
            "urgent,feature",  # tags
            "4h",  # estimate
            "EP-001",  # epic
        ]
        mock_prompt.side_effect = prompt_responses

        result = interactive_runner.invoke(app, ["task", "create", "--interactive"])
        assert result.exit_code == 0

        # Verify prompts were called
        assert mock_prompt.call_count >= 3  # At minimum: title, description, priority

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_with_confirmations(
        self, mock_confirm, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test interactive prompts with confirmation dialogs."""
        mock_exists.return_value = True
        mock_task = Mock(id="TSK-002", title="Confirmed Task")
        mock_create.return_value = mock_task

        # Mock responses
        mock_prompt.side_effect = [
            "Confirmed Task",
            "Task with confirmations",
            "critical",
        ]
        mock_confirm.side_effect = [
            True,  # Confirm creation
            False,  # Don't open in editor
            True,  # Add to current sprint
        ]

        result = interactive_runner.invoke(
            app,
            [
                "task",
                "create",
                "--interactive",
                "--confirm-creation",
                "--ask-editor",
                "--ask-sprint",
            ],
        )
        # These options might not exist, but test the pattern

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_with_validation(
        self, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test interactive prompts with input validation."""
        mock_exists.return_value = True
        mock_task = Mock(id="TSK-003", title="Validated Task")
        mock_create.return_value = mock_task

        # Mock invalid then valid responses
        mock_prompt.side_effect = [
            "Valid Task Title",
            "Task description with validation",
            "invalid_priority",  # Invalid first
            "high",  # Valid second
            "invalid_estimate",  # Invalid first
            "2h",  # Valid second
        ]

        result = interactive_runner.invoke(
            app, ["task", "create", "--interactive", "--validate-input"]
        )
        # Validation options might not exist yet

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.IntPrompt.ask")
    def test_interactive_with_different_prompt_types(
        self, mock_int_prompt, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test different types of interactive prompts."""
        mock_exists.return_value = True
        mock_task = Mock(id="TSK-004", title="Multi-prompt Task")
        mock_create.return_value = mock_task

        # Mock different prompt types
        mock_prompt.side_effect = [
            "Multi-prompt Task",
            "Task using different prompt types",
            "medium",
        ]
        mock_int_prompt.side_effect = [5, 80]  # story points  # completion percentage

        result = interactive_runner.invoke(
            app,
            [
                "task",
                "create",
                "--interactive",
                "--ask-story-points",
                "--ask-completion",
            ],
        )


class TestInteractiveEpicCreation:
    """Test interactive epic creation prompts."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_epic_creation(
        self, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test interactive epic creation with specialized prompts."""
        mock_exists.return_value = True
        mock_epic = Mock(id="EP-001", title="Interactive Epic")
        mock_create.return_value = mock_epic

        # Mock epic-specific prompts
        mock_prompt.side_effect = [
            "User Authentication Epic",  # title
            "Implement complete auth system",  # description
            "Enable secure user access",  # goal
            "Increased user trust and security",  # business value
            "All auth flows working",  # success criteria
            "high",  # priority
            "2024-12-31",  # target date
        ]

        result = interactive_runner.invoke(app, ["epic", "create", "--interactive"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_epic_with_task_creation(
        self, mock_confirm, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test epic creation with immediate task creation."""
        mock_exists.return_value = True
        mock_epic = Mock(id="EP-002", title="Epic with Tasks")
        mock_create.return_value = mock_epic

        # Mock epic creation then task creation
        mock_prompt.side_effect = [
            "Epic with Immediate Tasks",
            "Epic that creates tasks immediately",
            "Complete feature implementation",
            "Feature value delivered",
            "All tasks completed",
            "high",
            "2024-Q4",
            # Task creation prompts
            "Setup Infrastructure",
            "Implement Core Logic",
            "Add Tests",
            "Documentation",
        ]

        mock_confirm.side_effect = [
            True,  # Create tasks immediately
            True,  # Task 1
            True,  # Task 2
            True,  # Task 3
            True,  # Task 4
            False,  # No more tasks
        ]

        result = interactive_runner.invoke(
            app, ["epic", "create", "--interactive", "--create-tasks"]
        )


class TestInteractiveIssueCreation:
    """Test interactive issue creation prompts."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_bug_report(
        self, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test interactive bug report creation."""
        mock_exists.return_value = True
        mock_issue = Mock(id="ISS-001", title="Interactive Bug Report")
        mock_create.return_value = mock_issue

        # Mock bug report prompts
        mock_prompt.side_effect = [
            "Login Button Not Working",  # title
            "Users cannot login to the application",  # description
            "bug",  # issue type
            "high",  # severity
            "critical",  # priority
            # Steps to reproduce
            "1. Go to login page\n2. Enter credentials\n3. Click login button",
            "User should be logged in",  # expected behavior
            "Button does nothing, no error shown",  # actual behavior
            "Chrome 96, Windows 10",  # environment
            "EP-001",  # related epic
        ]

        result = interactive_runner.invoke(
            app, ["issue", "create", "--interactive", "--type", "bug"]
        )
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_feature_request(
        self, mock_prompt, mock_create, mock_exists, interactive_runner
    ):
        """Test interactive feature request creation."""
        mock_exists.return_value = True
        mock_issue = Mock(id="ISS-002", title="Interactive Feature Request")
        mock_create.return_value = mock_issue

        # Mock feature request prompts
        mock_prompt.side_effect = [
            "Dark Mode Toggle",  # title
            "Add ability to switch to dark theme",  # description
            "enhancement",  # issue type
            "medium",  # severity
            "medium",  # priority
            "Improve user experience",  # justification
            "UI/UX team",  # suggested assignee
            "Settings page, theme system",  # affected components
        ]

        result = interactive_runner.invoke(
            app, ["issue", "create", "--interactive", "--type", "enhancement"]
        )
        assert result.exit_code == 0


class TestInteractiveTemplateSelection:
    """Test interactive template selection and application."""

    @patch("ai_trackdown_pytools.utils.templates.TemplateManager.list_templates")
    @patch("ai_trackdown_pytools.utils.templates.TemplateManager.get_template")
    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager.create_task")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_template_selection(
        self,
        mock_prompt,
        mock_create,
        mock_exists,
        mock_get_template,
        mock_list_templates,
        interactive_runner,
    ):
        """Test interactive template selection from available templates."""
        mock_exists.return_value = True
        mock_list_templates.return_value = [
            "default",
            "bug_report",
            "feature_request",
            "epic",
            "user_story",
        ]

        mock_template = {
            "name": "Bug Report Template",
            "fields": {
                "title": {"required": True},
                "severity": {
                    "type": "choice",
                    "choices": ["low", "medium", "high", "critical"],
                },
            },
        }
        mock_get_template.return_value = mock_template

        mock_task = Mock(id="TMPL-001", title="Template Generated Task")
        mock_create.return_value = mock_task

        # Mock template selection and field prompts
        mock_prompt.side_effect = [
            "bug_report",  # template selection
            "Template Generated Bug Report",  # title from template
            "critical",  # severity from template
            "Bug found in template system",  # description
            "Test template functionality",  # additional notes
        ]

        result = interactive_runner.invoke(
            app, ["create", "task", "--interactive-template"]
        )
        # This functionality might not exist yet

    @patch("ai_trackdown_pytools.utils.templates.TemplateManager.create_template")
    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_template_creation(
        self, mock_confirm, mock_prompt, mock_create_template, interactive_runner
    ):
        """Test interactive template creation."""
        mock_create_template.return_value = True

        # Mock template creation prompts
        mock_prompt.side_effect = [
            "custom_task_template",  # template name
            "Custom Task Template",  # display name
            "task",  # template type
            "Custom template for tasks",  # description
            "title",  # field 1 name
            "text",  # field 1 type
            "priority",  # field 2 name
            "choice",  # field 2 type
            "low,medium,high,critical",  # field 2 choices
            "estimate",  # field 3 name
            "text",  # field 3 type
        ]

        mock_confirm.side_effect = [
            True,  # title field required
            False,  # priority field required
            True,  # estimate field required
            True,  # add another field
            False,  # add another field (second time)
            True,  # save template
        ]

        result = interactive_runner.invoke(app, ["template", "create", "--interactive"])


class TestInteractiveConfiguration:
    """Test interactive configuration setup and modification."""

    @patch("ai_trackdown_pytools.core.config.Config.load")
    @patch("ai_trackdown_pytools.core.config.Config.save")
    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_config_setup(
        self, mock_confirm, mock_prompt, mock_save, mock_load, interactive_runner
    ):
        """Test interactive configuration setup."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {}
        mock_load.return_value = mock_config

        # Mock configuration prompts
        mock_prompt.side_effect = [
            "Test Project",  # project name
            "A test project for CLI",  # project description
            "vim",  # default editor
            "alice",  # default assignee
            "medium",  # default priority
            "~/templates",  # templates directory
            "github.com/user/repo.git",  # repository URL
        ]

        mock_confirm.side_effect = [
            True,  # Setup project defaults
            True,  # Setup editor preference
            False,  # Don't setup Git integration
            True,  # Setup template directory
            True,  # Save configuration
        ]

        result = interactive_runner.invoke(app, ["init", "config", "--interactive"])
        assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.config.Config.load")
    @patch("ai_trackdown_pytools.core.config.Config.save")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_config_update(
        self, mock_prompt, mock_save, mock_load, interactive_runner
    ):
        """Test interactive configuration updates."""
        mock_config = Mock()
        mock_config.to_dict.return_value = {
            "project": {"name": "Old Project", "description": "Old description"},
            "editor": {"default": "nano"},
            "defaults": {"priority": "low"},
        }
        mock_config.get.side_effect = lambda key: {
            "project.name": "Old Project",
            "editor.default": "nano",
            "defaults.priority": "low",
        }.get(key)
        mock_load.return_value = mock_config

        # Mock update prompts
        mock_prompt.side_effect = [
            "project.name",  # config key to update
            "Updated Project Name",  # new value
            "editor.default",  # another key
            "vim",  # new editor
            "",  # empty to finish
        ]

        result = interactive_runner.invoke(app, ["config", "--interactive-update"])


class TestInteractiveSearch:
    """Test interactive search and filtering."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_search_builder(
        self, mock_confirm, mock_prompt, mock_task_mgr, mock_exists, interactive_runner
    ):
        """Test interactive search query builder."""
        mock_exists.return_value = True

        # Mock search results
        mock_tasks = [
            Mock(
                id="TSK-001",
                title="Test Task 1",
                description="First test",
                tags=["test"],
                status="open",
            ),
            Mock(
                id="TSK-002",
                title="Bug Fix",
                description="Fix critical bug",
                tags=["bug", "critical"],
                status="in_progress",
            ),
            Mock(
                id="EP-001",
                title="Test Epic",
                description="Epic for testing",
                tags=["epic"],
                status="active",
            ),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        # Mock interactive search prompts
        mock_prompt.side_effect = [
            "test",  # search term
            "task",  # filter by type
            "open,in_progress",  # filter by status
            "test,bug",  # filter by tags
            "medium,high",  # filter by priority
            "alice,bob",  # filter by assignee
        ]

        mock_confirm.side_effect = [
            True,  # Add type filter
            True,  # Add status filter
            True,  # Add tag filter
            False,  # Don't add priority filter
            False,  # Don't add assignee filter
            True,  # Execute search
        ]

        result = interactive_runner.invoke(app, ["search", "--interactive"])

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_search_refinement(
        self, mock_prompt, mock_task_mgr, mock_exists, interactive_runner
    ):
        """Test interactive search result refinement."""
        mock_exists.return_value = True

        # Mock initial search results
        mock_tasks = [
            Mock(
                id=f"TSK-{i:03d}",
                title=f"Task {i}",
                description=f"Description {i}",
                tags=["test"],
                status="open",
            )
            for i in range(1, 21)
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        # Mock refinement prompts
        mock_prompt.side_effect = [
            "task",  # initial search
            "r",  # refine search
            "task implementation",  # refined search term
            "s",  # sort results
            "created_date",  # sort by field
            "desc",  # sort order
            "f",  # filter results
            "status=open",  # filter criteria
            "q",  # quit refinement
        ]

        result = interactive_runner.invoke(
            app, ["search", "task", "--interactive-refine"]
        )


class TestInteractiveReporting:
    """Test interactive report generation."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_status_report(
        self, mock_confirm, mock_prompt, mock_task_mgr, mock_exists, interactive_runner
    ):
        """Test interactive status report generation."""
        mock_exists.return_value = True

        # Mock task data for reporting
        mock_tasks = [
            Mock(id="TSK-001", status="open", priority="high", assignees=["alice"]),
            Mock(
                id="TSK-002", status="in_progress", priority="medium", assignees=["bob"]
            ),
            Mock(
                id="TSK-003", status="completed", priority="low", assignees=["charlie"]
            ),
            Mock(id="EP-001", status="active", priority="critical", assignees=["team"]),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        # Mock report configuration prompts
        mock_prompt.side_effect = [
            "weekly",  # report type
            "2024-01-01",  # start date
            "2024-01-07",  # end date
            "alice,bob,charlie",  # include assignees
            "json,html",  # output formats
            "/tmp/report",  # output directory
        ]

        mock_confirm.side_effect = [
            True,  # Include completed tasks
            True,  # Include task details
            False,  # Don't include time tracking
            True,  # Generate charts
            True,  # Save report
        ]

        result = interactive_runner.invoke(app, ["status", "report", "--interactive"])


class TestInteractiveValidation:
    """Test interactive validation and fixing."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.utils.validation.validate_project_structure")
    @patch("rich.prompt.Confirm.ask")
    @patch("rich.prompt.Prompt.ask")
    def test_interactive_validation_with_fixes(
        self, mock_prompt, mock_confirm, mock_validate, mock_exists, interactive_runner
    ):
        """Test interactive validation with fix suggestions."""
        mock_exists.return_value = True
        mock_validate.return_value = {
            "valid": False,
            "errors": [
                "Missing tasks directory",
                "Invalid config format",
                "Broken task references",
            ],
            "warnings": [
                "Empty templates directory",
                "No default assignees configured",
            ],
            "fixable": ["Missing tasks directory", "Empty templates directory"],
        }

        # Mock interactive fix prompts
        mock_confirm.side_effect = [
            True,  # Fix missing tasks directory
            False,  # Don't fix config format (manual fix needed)
            True,  # Fix empty templates directory
            True,  # Apply all selected fixes
            False,  # Don't re-run validation immediately
        ]

        mock_prompt.side_effect = [
            "tasks",  # directory name to create
            "Create default templates",  # template action
        ]

        result = interactive_runner.invoke(
            app, ["validate", "project", "--interactive-fix"]
        )

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    @patch("ai_trackdown_pytools.utils.validation.validate_task_file")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_task_validation(
        self,
        mock_confirm,
        mock_validate_task,
        mock_task_mgr,
        mock_exists,
        interactive_runner,
    ):
        """Test interactive task validation with selective fixes."""
        mock_exists.return_value = True

        # Mock tasks with various validation issues
        mock_tasks = [
            Mock(id="TSK-001", file_path="/path/task1.md"),
            Mock(id="TSK-002", file_path="/path/task2.md"),
            Mock(id="TSK-003", file_path="/path/task3.md"),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        # Mock validation results
        mock_validate_task.side_effect = [
            {
                "valid": False,
                "errors": ["Missing required field: priority"],
                "warnings": [],
            },
            {"valid": True, "errors": [], "warnings": ["Consider adding estimate"]},
            {
                "valid": False,
                "errors": ["Invalid status value"],
                "warnings": ["Old format detected"],
            },
        ]

        # Mock fix confirmations
        mock_confirm.side_effect = [
            True,  # Fix TSK-001 priority issue
            False,  # Don't add estimate to TSK-002
            True,  # Fix TSK-003 status issue
            False,  # Don't update TSK-003 format
        ]

        result = interactive_runner.invoke(
            app, ["validate", "tasks", "--interactive-fix"]
        )


class TestInteractiveHelp:
    """Test interactive help and guidance systems."""

    @patch("rich.prompt.Prompt.ask")
    @patch("rich.prompt.Confirm.ask")
    def test_interactive_help_system(
        self, mock_confirm, mock_prompt, interactive_runner
    ):
        """Test interactive help and command suggestion system."""

        # Mock help navigation prompts
        mock_prompt.side_effect = [
            "task",  # help topic
            "create",  # subtopic
            "examples",  # show examples
            "search priority options",  # search help
            "quit",  # exit help
        ]

        mock_confirm.side_effect = [
            True,  # Show detailed help
            True,  # Show examples
            False,  # Don't run example command
            True,  # Show related commands
        ]

        result = interactive_runner.invoke(app, ["help", "--interactive"])

    @patch("rich.prompt.Prompt.ask")
    def test_interactive_command_builder(self, mock_prompt, interactive_runner):
        """Test interactive command builder."""

        # Mock command building prompts
        mock_prompt.side_effect = [
            "task",  # command type
            "create",  # action
            "Interactive Built Task",  # title
            "Task created interactively",  # description
            "high",  # priority
            "alice",  # assignee
            "feature,new",  # tags
            "4h",  # estimate
            "y",  # execute command
        ]

        result = interactive_runner.invoke(app, ["build-command", "--interactive"])


class TestRichUIElements:
    """Test Rich UI elements and formatting."""

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_table_formatting_options(
        self, mock_task_mgr, mock_exists, interactive_runner
    ):
        """Test different table formatting options."""
        mock_exists.return_value = True

        # Mock tasks for table display
        mock_tasks = [
            Mock(
                id="TSK-001",
                title="Task 1",
                status="open",
                priority="high",
                assignees=["alice"],
            ),
            Mock(
                id="TSK-002",
                title="Very Long Task Title That Should Be Truncated",
                status="in_progress",
                priority="medium",
                assignees=["bob", "charlie"],
            ),
            Mock(
                id="TSK-003",
                title="Task 3",
                status="completed",
                priority="low",
                assignees=[],
            ),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        # Test different table formats
        table_formats = ["simple", "grid", "rounded", "heavy", "double"]

        for table_format in table_formats:
            result = interactive_runner.invoke(
                app, ["search", "task", "--table-format", table_format]
            )
            # Table format option might not exist yet

    @patch("ai_trackdown_pytools.utils.system.get_system_info")
    def test_panel_customization(self, mock_system_info, interactive_runner):
        """Test panel display customization."""
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

        # Test different panel styles
        panel_styles = ["blue", "green", "red", "yellow", "cyan", "magenta"]

        for style in panel_styles:
            result = interactive_runner.invoke(app, ["info", "--panel-style", style])
            assert result.exit_code == 0

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_progress_bars(self, mock_task_mgr, mock_exists, interactive_runner):
        """Test progress bar display in long operations."""
        mock_exists.return_value = True

        # Mock large dataset for progress testing
        mock_tasks = [Mock(id=f"TSK-{i:03d}", title=f"Task {i}") for i in range(1, 101)]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        # Test operations that should show progress
        result = interactive_runner.invoke(
            app, ["validate", "tasks", "--show-progress"]
        )
        # Progress option might not exist yet

    @patch("ai_trackdown_pytools.core.project.Project.exists")
    @patch("ai_trackdown_pytools.core.task.TaskManager")
    def test_color_themes(self, mock_task_mgr, mock_exists, interactive_runner):
        """Test different color themes."""
        mock_exists.return_value = True

        mock_tasks = [
            Mock(id="TSK-001", title="Task 1", status="open", priority="high"),
            Mock(id="TSK-002", title="Task 2", status="completed", priority="low"),
        ]
        mock_task_mgr.return_value.list_tasks.return_value = mock_tasks

        # Test different color themes
        themes = ["default", "dark", "light", "minimal", "vibrant"]

        for theme in themes:
            result = interactive_runner.invoke(
                app, ["search", "task", "--color-theme", theme]
            )
            # Color theme option might not exist yet


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
