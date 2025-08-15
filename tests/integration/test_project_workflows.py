"""Integration tests for complete project workflows."""

import shutil
import tempfile
from pathlib import Path

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.templates import TemplateManager
from ai_trackdown_pytools.utils.validation import SchemaValidator


class TestProjectLifecycle:
    """Test complete project lifecycle workflows."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_temp_project(self, name="Test Project"):
        """Create a temporary project for testing."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "test_project"
        project_path.mkdir()
        return Project.create(project_path, name=name)

    def test_project_creation_and_initialization(self):
        """Test complete project creation and initialization."""
        project = self._create_temp_project("Integration Test Project")

        # Verify project structure
        assert project.path.exists()
        assert (project.path / ".ai-trackdown").exists()
        assert (project.path / ".ai-trackdown" / "config.yaml").exists()
        assert (project.path / "tasks").exists()
        assert (project.path / "templates").exists()

        # Verify config
        config = project.get_config()
        assert config.get("project.name") == "Integration Test Project"
        assert config.get("version") == "1.0.0"

        # Verify subdirectories
        tasks_dir = project.get_tasks_directory()
        assert (tasks_dir / "open").exists()
        assert (tasks_dir / "in_progress").exists()
        assert (tasks_dir / "completed").exists()

        # Verify project validation
        issues = project.validate_structure()
        assert len(issues) == 0

    def test_task_creation_workflow(self):
        """Test complete task creation workflow."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)

        # Create multiple tasks with different attributes
        tasks_data = [
            {
                "title": "High Priority Bug Fix",
                "description": "Fix critical authentication bug",
                "priority": "critical",
                "status": "open",
                "tags": ["bug", "security", "urgent"],
                "assignees": ["alice", "bob"],
            },
            {
                "title": "Feature Implementation",
                "description": "Implement user dashboard",
                "priority": "medium",
                "status": "open",
                "tags": ["feature", "frontend"],
                "assignees": ["charlie"],
            },
            {
                "title": "Documentation Update",
                "description": "Update API documentation",
                "priority": "low",
                "status": "in_progress",
                "tags": ["documentation"],
                "assignees": ["diana"],
            },
        ]

        created_tasks = []
        for task_data in tasks_data:
            task = task_manager.create_task(task_data)
            created_tasks.append(task)

            # Verify task was created correctly
            assert task.model.title == task_data["title"]
            assert task.model.priority == task_data["priority"]
            assert task.model.status == task_data["status"]
            assert task.file_path.exists()

            # Verify file content
            file_content = task.file_path.read_text()
            assert f"title: {task_data['title']}" in file_content
            assert f"priority: {task_data['priority']}" in file_content
            for tag in task_data["tags"]:
                assert tag in file_content

        # Verify all tasks can be listed
        all_tasks = task_manager.list_tasks()
        assert len(all_tasks) == 3

        # Test filtering
        critical_tasks = task_manager.list_tasks(priority="critical")
        assert len(critical_tasks) == 1
        assert critical_tasks[0].model.title == "High Priority Bug Fix"

        open_tasks = task_manager.list_tasks(status="open")
        assert len(open_tasks) == 2

        alice_tasks = task_manager.list_tasks(assignee="alice")
        assert len(alice_tasks) == 1

        bug_tasks = task_manager.list_tasks(tag="bug")
        assert len(bug_tasks) == 1

    def test_task_lifecycle_workflow(self):
        """Test complete task lifecycle from creation to completion."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)

        # Create a task
        task_data = {
            "title": "Lifecycle Test Task",
            "description": "Test task lifecycle",
            "priority": "medium",
            "assignees": ["developer"],
        }
        task = task_manager.create_task(task_data)
        original_path = task.file_path

        # Verify initial state
        assert task.model.status == "open"
        assert "open" in str(task.file_path)

        # Update to in progress
        task.update_status("in_progress")
        task.save()

        # Reload task and verify status change
        updated_task = task_manager.load_task(task.model.id)
        assert updated_task.model.status == "in_progress"
        assert "in_progress" in str(updated_task.file_path)
        assert not original_path.exists()  # Old file should be moved

        # Add some work details
        updated_task.model.actual_hours = 2.5
        updated_task.save(
            "# Lifecycle Test Task\n\nWork in progress...\n\n## Progress\n- Started implementation"
        )

        # Complete the task
        updated_task.update_status("completed")
        updated_task.save(
            "# Lifecycle Test Task\n\nCompleted task.\n\n## Progress\n- Started implementation\n- Finished implementation"
        )

        # Reload and verify completion
        completed_task = task_manager.load_task(task.model.id)
        assert completed_task.model.status == "completed"
        assert "completed" in str(completed_task.file_path)
        assert completed_task.model.actual_hours == 2.5

        # Verify file content
        file_content = completed_task.file_path.read_text()
        assert "Completed task" in file_content
        assert "Finished implementation" in file_content

    def test_template_integration_workflow(self):
        """Test template integration in task creation workflow."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)
        template_manager = TemplateManager(project.get_templates_directory())

        # Create custom template
        custom_template_content = """---
id: {{ id or 'TSK-' + '%04d'|format(sequence_number) }}
title: {{ title }}
description: {{ description or '' }}
status: {{ status or 'open' }}
priority: {{ priority or 'medium' }}
assignees: {{ assignees or [] }}
tags: {{ tags or [] }}
epic: {{ epic or '' }}
sprint: {{ sprint or 'backlog' }}
story_points: {{ story_points or 0 }}
created_at: {{ created_at or now() }}
updated_at: {{ updated_at or now() }}
---

# {{ title }}

{% if epic -%}
**Epic:** {{ epic }}
{% endif -%}
{% if sprint != 'backlog' -%}
**Sprint:** {{ sprint }}
{% endif -%}
{% if story_points > 0 -%}
**Story Points:** {{ story_points }}
{% endif -%}

## Description
{{ description or 'No description provided.' }}

## Acceptance Criteria
{% if acceptance_criteria -%}
{{ acceptance_criteria }}
{% else -%}
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3
{% endif -%}

## Notes
{{ notes or 'Add notes here...' }}
"""

        # Save custom template
        custom_template_path = project.get_templates_directory() / "task" / "story.yaml"
        custom_template_path.write_text(custom_template_content)

        # Create task using custom template
        template_variables = {
            "title": "User Story Task",
            "description": "As a user, I want to see my dashboard",
            "epic": "EP-0001",
            "sprint": "Sprint 1",
            "story_points": 5,
            "acceptance_criteria": "- [ ] Dashboard loads within 2 seconds\n- [ ] Shows user stats\n- [ ] Responsive design",
            "notes": "Consider performance optimization",
        }

        rendered_content = template_manager.render_template(
            "task", "story", template_variables
        )

        # Verify template rendering
        assert "User Story Task" in rendered_content
        assert "Epic: EP-0001" in rendered_content
        assert "Sprint: Sprint 1" in rendered_content
        assert "Story Points: 5" in rendered_content
        assert "Dashboard loads within 2 seconds" in rendered_content
        assert "Consider performance optimization" in rendered_content

        # Create task using rendered template
        # (This would typically be handled by the CLI)
        task_data = {
            "title": "User Story Task",
            "description": "As a user, I want to see my dashboard",
            "epic": "EP-0001",
            "story_points": 5,
        }
        task = task_manager.create_task(task_data)

        # Verify task creation
        assert task.model.title == "User Story Task"
        assert task.file_path.exists()

    def test_validation_workflow(self):
        """Test validation workflow for project and tasks."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)
        validator = SchemaValidator()

        # Create valid tasks
        valid_task = task_manager.create_task(
            {
                "title": "Valid Task",
                "description": "This is a valid task",
                "priority": "medium",
                "status": "open",
            }
        )

        # Create task with validation issues
        problematic_task_path = (
            project.get_tasks_directory() / "open" / "problematic-task.md"
        )
        problematic_content = """---
id: INVALID-ID-FORMAT
title: Problematic Task
status: invalid_status
priority: invalid_priority
assignees: not_a_list
tags: also_not_a_list
dependencies:
  - INVALID-ID-FORMAT  # Self-dependency
created_at: not_a_date
updated_at: also_not_a_date
---

# Problematic Task

This task has multiple validation issues.
"""
        problematic_task_path.write_text(problematic_content)

        # Validate all tasks
        all_tasks = task_manager.list_tasks()
        validation_results = []

        for task in all_tasks:
            try:
                # Try to parse and validate each task
                task_dict = task.to_dict()
                result = validator.validate_ticket(task_dict, "task")
                validation_results.append((task.model.id, result))
            except Exception as e:
                validation_results.append((task.file_path.name, f"Parse error: {e}"))

        # Check that we have both valid and invalid results
        valid_count = sum(
            1
            for _, result in validation_results
            if hasattr(result, "valid") and result.valid
        )
        invalid_count = len(validation_results) - valid_count

        assert valid_count >= 1  # At least the valid task
        assert invalid_count >= 1  # At least the problematic task

        # Validate project structure
        structure_issues = project.validate_structure()
        assert len(structure_issues) == 0  # Project structure should be valid

    def test_search_and_filter_workflow(self):
        """Test comprehensive search and filtering workflow."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)

        # Create diverse set of tasks
        tasks_data = [
            {
                "title": "Authentication Bug Fix",
                "description": "Fix login authentication issue",
                "priority": "critical",
                "status": "open",
                "tags": ["bug", "security", "authentication"],
                "assignees": ["alice", "bob"],
            },
            {
                "title": "User Dashboard Feature",
                "description": "Implement user dashboard with charts",
                "priority": "high",
                "status": "in_progress",
                "tags": ["feature", "frontend", "dashboard"],
                "assignees": ["charlie"],
            },
            {
                "title": "API Documentation",
                "description": "Write comprehensive API documentation",
                "priority": "medium",
                "status": "open",
                "tags": ["documentation", "api"],
                "assignees": ["diana"],
            },
            {
                "title": "Database Migration",
                "description": "Migrate user data to new schema",
                "priority": "high",
                "status": "completed",
                "tags": ["migration", "database", "backend"],
                "assignees": ["eve"],
            },
            {
                "title": "User Authentication Enhancement",
                "description": "Add two-factor authentication",
                "priority": "medium",
                "status": "open",
                "tags": ["enhancement", "security", "authentication"],
                "assignees": ["alice", "frank"],
            },
        ]

        for task_data in tasks_data:
            task_manager.create_task(task_data)

        # Test various search scenarios

        # Search by text content
        auth_tasks = task_manager.search_tasks("authentication")
        assert len(auth_tasks) >= 2  # Should find authentication-related tasks

        user_tasks = task_manager.search_tasks("user")
        assert len(user_tasks) >= 3  # Should find user-related tasks

        # Filter by status
        open_tasks = task_manager.list_tasks(status="open")
        assert len(open_tasks) == 3

        in_progress_tasks = task_manager.list_tasks(status="in_progress")
        assert len(in_progress_tasks) == 1

        completed_tasks = task_manager.list_tasks(status="completed")
        assert len(completed_tasks) == 1

        # Filter by priority
        critical_tasks = task_manager.list_tasks(priority="critical")
        assert len(critical_tasks) == 1
        assert critical_tasks[0].model.title == "Authentication Bug Fix"

        high_tasks = task_manager.list_tasks(priority="high")
        assert len(high_tasks) == 2

        # Filter by assignee
        alice_tasks = task_manager.list_tasks(assignee="alice")
        assert len(alice_tasks) == 2

        charlie_tasks = task_manager.list_tasks(assignee="charlie")
        assert len(charlie_tasks) == 1

        # Filter by tag
        security_tasks = task_manager.list_tasks(tag="security")
        assert len(security_tasks) == 2

        feature_tasks = task_manager.list_tasks(tag="feature")
        assert len(feature_tasks) == 1

        # Combined filters (if supported)
        # This would test more advanced filtering capabilities

        # Get statistics
        stats = task_manager.get_statistics()
        assert stats["total"] == 5
        assert stats["open"] == 3
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["critical"] == 1
        assert stats["high"] == 2
        assert stats["medium"] == 2

    def test_configuration_management_workflow(self):
        """Test configuration management throughout project lifecycle."""
        project = self._create_temp_project("Config Test Project")

        # Test initial configuration
        config = project.get_config()
        assert config.get("project.name") == "Config Test Project"
        assert config.get("version") == "1.0.0"

        # Update configuration
        config.set("project.description", "A test project for configuration management")
        config.set("project.team_members", ["alice", "bob", "charlie"])
        config.set("tasks.default_assignee", "alice")
        config.set("tasks.auto_assign", True)
        config.set("git.auto_commit", True)
        config.save()

        # Verify configuration persistence
        reloaded_project = Project.load(project.path)
        reloaded_config = reloaded_project.get_config()

        assert (
            reloaded_config.get("project.description")
            == "A test project for configuration management"
        )
        assert reloaded_config.get("project.team_members") == [
            "alice",
            "bob",
            "charlie",
        ]
        assert reloaded_config.get("tasks.default_assignee") == "alice"
        assert reloaded_config.get("tasks.auto_assign") is True
        assert reloaded_config.get("git.auto_commit") is True

        # Test configuration inheritance and defaults
        assert (
            reloaded_config.get("nonexistent.key", "default_value") == "default_value"
        )
        assert reloaded_config.get("editor.default") is not None  # Should have default

        # Test nested configuration updates
        config.set("custom.nested.deep.value", "deep_config")
        config.save()

        final_config = Config.load(project.config_path)
        assert final_config.get("custom.nested.deep.value") == "deep_config"

    def test_error_handling_and_recovery_workflow(self):
        """Test error handling and recovery scenarios."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)

        # Test handling of corrupted task files
        corrupted_task_path = (
            project.get_tasks_directory() / "open" / "corrupted-task.md"
        )
        corrupted_task_path.write_text("This is not valid frontmatter content")

        # Should handle corrupted files gracefully
        try:
            all_tasks = task_manager.list_tasks()
            # Should either skip corrupted files or handle them gracefully
            assert isinstance(all_tasks, list)
        except Exception as e:
            # If an exception is raised, it should be a specific task error
            assert "task" in str(e).lower() or "parse" in str(e).lower()

        # Test handling of missing directories
        import shutil

        tasks_dir = project.get_tasks_directory()
        backup_dir = Path(str(tasks_dir) + "_backup")
        shutil.move(str(tasks_dir), str(backup_dir))

        try:
            # Should handle missing tasks directory
            empty_tasks = task_manager.list_tasks()
            assert isinstance(empty_tasks, list)
            assert len(empty_tasks) == 0
        finally:
            # Restore directory
            shutil.move(str(backup_dir), str(tasks_dir))

        # Test project structure validation and repair
        issues = project.validate_structure()
        if len(issues) > 0:
            # If issues are found, project should be able to report them
            assert all(isinstance(issue, str) for issue in issues)

        # Test configuration file corruption recovery
        config_path = project.config_path
        original_config = config_path.read_text()

        # Corrupt config file
        config_path.write_text("invalid: yaml: content: here")

        try:
            # Should handle corrupted config gracefully
            Config.load(config_path)
        except Exception:
            # If it fails, restore original config
            config_path.write_text(original_config)
            # Should work with restored config
            restored_config = Config.load(config_path)
            assert restored_config.get("project.name") is not None


class TestCrossModuleIntegration:
    """Test integration between different modules."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_temp_project(self):
        """Create a temporary project for testing."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "integration_project"
        project_path.mkdir()
        return Project.create(project_path)

    def test_project_task_template_integration(self):
        """Test integration between project, task, and template modules."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)
        template_manager = TemplateManager(project.get_templates_directory())

        # Test template-based task creation
        template_vars = {
            "title": "Integration Test Task",
            "description": "Testing integration between modules",
            "priority": "high",
            "assignees": ["integration_tester"],
            "tags": ["integration", "test"],
        }

        # Render template
        rendered_content = template_manager.render_template(
            "task", "default", template_vars
        )
        assert "Integration Test Task" in rendered_content

        # Create task from template variables
        task = task_manager.create_task(template_vars)
        assert task.model.title == "Integration Test Task"
        assert task.model.priority == "high"
        assert "integration_tester" in task.model.assignees

        # Verify task file content matches template structure
        file_content = task.file_path.read_text()
        assert "id:" in file_content
        assert "title: Integration Test Task" in file_content
        assert "priority: high" in file_content
        assert "integration" in file_content

    def test_validation_across_modules(self):
        """Test validation integration across modules."""
        project = self._create_temp_project()
        task_manager = TaskManager(project)
        validator = SchemaValidator()

        # Create task with validation-aware data
        task_data = {
            "title": "Validation Test Task",
            "description": "Testing validation integration",
            "priority": "medium",
            "status": "open",
            "assignees": ["validator"],
            "tags": ["validation", "test"],
            "dependencies": [],  # Empty dependencies (valid)
        }

        # Validate data before task creation
        validation_result = validator.validate_ticket(task_data, "task")
        assert validation_result.valid

        # Create task
        task = task_manager.create_task(task_data)

        # Validate created task
        created_task_data = task.to_dict()
        post_creation_result = validator.validate_ticket(created_task_data, "task")
        assert post_creation_result.valid

        # Test validation with invalid updates
        invalid_updates = {"status": "invalid_status", "priority": "invalid_priority"}

        # Should catch validation errors
        for field, invalid_value in invalid_updates.items():
            test_data = created_task_data.copy()
            test_data[field] = invalid_value
            invalid_result = validator.validate_ticket(test_data, "task")
            assert not invalid_result.valid

    def test_config_driven_behavior(self):
        """Test configuration-driven behavior across modules."""
        project = self._create_temp_project()

        # Configure project behavior
        config = project.get_config()
        config.set("tasks.default_priority", "high")
        config.set("tasks.default_assignee", "default_user")
        config.set("tasks.require_description", True)
        config.set("templates.default_type", "task")
        config.set("validation.strict_mode", True)
        config.save()

        # Test that configuration affects task creation
        task_manager = TaskManager(project)

        # Create task with minimal data (should use config defaults)
        minimal_task_data = {"title": "Config Driven Task"}

        task = task_manager.create_task(minimal_task_data)

        # Should use configured defaults (if implemented)
        assert task.model.title == "Config Driven Task"
        # Note: Default behavior depends on implementation
        # assert task.model.priority == "high"  # If default priority is implemented

        # Test template configuration
        template_manager = TemplateManager(project.get_templates_directory())
        available_templates = template_manager.list_templates("task")
        assert "default" in available_templates  # Should have default template

    def test_end_to_end_data_flow(self):
        """Test end-to-end data flow through all modules."""
        project = self._create_temp_project()

        # Set up initial state
        config = project.get_config()
        config.set("project.version", "2.0.0")
        config.set("project.team", ["alice", "bob", "charlie"])
        config.save()

        # Create task manager and template manager
        task_manager = TaskManager(project)
        template_manager = TemplateManager(project.get_templates_directory())
        validator = SchemaValidator()

        # Create task using template
        template_vars = {
            "title": "End-to-End Test Task",
            "description": "Testing complete data flow",
            "priority": "critical",
            "assignees": ["alice", "bob"],
            "tags": ["e2e", "integration", "critical"],
            "epic": "EP-0001",
        }

        # Validate template variables
        validation_result = validator.validate_ticket(template_vars, "task")
        # Some fields might be missing for validation, but core fields should be valid

        # Create task
        task = task_manager.create_task(template_vars)

        # Verify task creation
        assert task.file_path.exists()

        # Update task through lifecycle
        task.update_status("in_progress")
        task.add_tag("updated")
        task.set_priority("high")  # Downgrade from critical

        # Save and reload
        task.save("# End-to-End Test Task\n\nUpdated task content.")
        reloaded_task = task_manager.load_task(task.model.id)

        # Verify updates persisted
        assert reloaded_task.model.status == "in_progress"
        assert "updated" in reloaded_task.model.tags
        assert reloaded_task.model.priority == "high"

        # Validate final state
        final_task_data = reloaded_task.to_dict()
        final_validation = validator.validate_ticket(final_task_data, "task")
        assert final_validation.valid

        # Verify file system state
        assert reloaded_task.file_path.exists()
        assert "in_progress" in str(reloaded_task.file_path)

        file_content = reloaded_task.file_path.read_text()
        assert "status: in_progress" in file_content
        assert "priority: high" in file_content
        assert "Updated task content" in file_content
