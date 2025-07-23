"""Unit tests for task management functionality."""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, mock_open

from ai_trackdown_pytools.core.task import Task, TaskManager, TaskError
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.models import TaskModel


class TestTask:
    """Test Task class functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None
        self.now = datetime.now()
        self.task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "description": "This is a test task",
            "status": "open",
            "priority": "medium",
            "assignees": ["alice"],
            "tags": ["test", "unit"],
            "created_at": self.now,
            "updated_at": self.now,
        }

    def test_task_creation_from_model(self):
        """Test creating task from TaskModel."""
        model = TaskModel(**self.task_data)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task(model, file_path)

            assert task.model.id == "TSK-0001"
            assert task.model.title == "Test Task"
            assert task.file_path == file_path

    def test_task_creation_from_dict(self):
        """Test creating task from dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            assert task.model.id == "TSK-0001"
            assert task.model.title == "Test Task"
            assert task.file_path == file_path

    def test_task_save_to_file(self):
        """Test saving task to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Add some content
            content = "# Test Task\n\nThis is the task description."

            # Save task
            task.save(content)

            # Verify file exists and has content
            assert file_path.exists()
            file_content = file_path.read_text()
            assert "id: TSK-0001" in file_content
            assert "title: Test Task" in file_content
            assert "# Test Task" in file_content

    def test_task_load_from_file(self):
        """Test loading task from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"

            # Create file with frontmatter and content
            file_content = """---
id: TSK-0001
title: Test Task
description: This is a test task
status: open
priority: medium
assignees:
  - alice
tags:
  - test
  - unit
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
---

# Test Task

This is the task description.
"""
            file_path.write_text(file_content)

            # Load task
            task = Task.load(file_path)

            assert task.model.id == "TSK-0001"
            assert task.model.title == "Test Task"
            assert task.model.status == "open"
            assert "alice" in task.model.assignees
            assert "test" in task.model.tags

    def test_task_load_invalid_file(self):
        """Test loading task from invalid file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "invalid_task.md"

            # Create file with invalid frontmatter
            file_content = """---
invalid: yaml: content
---

# Invalid Task
"""
            file_path.write_text(file_content)

            with pytest.raises(TaskError, match="Failed to parse task file"):
                Task.load(file_path)

    def test_task_update_status(self):
        """Test updating task status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Update status
            task.update_status("in_progress")

            assert task.model.status == "in_progress"
            assert task.model.updated_at > self.now

    def test_task_add_assignee(self):
        """Test adding assignee to task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Add new assignee
            task.add_assignee("bob")

            assert "bob" in task.model.assignees
            assert "alice" in task.model.assignees  # Original should still be there
            assert task.model.updated_at > self.now

    def test_task_remove_assignee(self):
        """Test removing assignee from task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Remove assignee
            task.remove_assignee("alice")

            assert "alice" not in task.model.assignees
            assert task.model.updated_at > self.now

    def test_task_remove_nonexistent_assignee(self):
        """Test removing non-existent assignee."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Try to remove non-existent assignee (should not error)
            task.remove_assignee("nonexistent")

            assert "alice" in task.model.assignees  # Original should still be there

    def test_task_add_tag(self):
        """Test adding tag to task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Add new tag
            task.add_tag("bug")

            assert "bug" in task.model.tags
            assert "test" in task.model.tags  # Original should still be there
            assert task.model.updated_at > self.now

    def test_task_remove_tag(self):
        """Test removing tag from task."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Remove tag
            task.remove_tag("test")

            assert "test" not in task.model.tags
            assert "unit" in task.model.tags  # Other tag should still be there
            assert task.model.updated_at > self.now

    def test_task_set_priority(self):
        """Test setting task priority."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Set new priority
            task.set_priority("high")

            assert task.model.priority == "high"
            assert task.model.updated_at > self.now

    def test_task_set_estimated_hours(self):
        """Test setting estimated hours."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Set estimated hours
            task.set_estimated_hours(8.5)

            assert task.model.estimated_hours == 8.5
            assert task.model.updated_at > self.now

    def test_task_set_due_date(self):
        """Test setting due date."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Set due date
            due_date = date.today() + timedelta(days=7)
            task.set_due_date(due_date)

            assert task.model.due_date == due_date
            assert task.model.updated_at > self.now

    def test_task_is_overdue(self):
        """Test checking if task is overdue."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Not overdue without due date
            assert not task.is_overdue()

            # Set past due date
            past_date = date.today() - timedelta(days=1)
            task.set_due_date(past_date)
            assert task.is_overdue()

            # Set future due date
            future_date = date.today() + timedelta(days=1)
            task.set_due_date(future_date)
            assert not task.is_overdue()

            # Completed task should not be overdue
            task.set_due_date(past_date)
            task.update_status("completed")
            assert not task.is_overdue()

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            task_dict = task.to_dict()

            assert task_dict["id"] == "TSK-0001"
            assert task_dict["title"] == "Test Task"
            assert task_dict["status"] == "open"
            assert "alice" in task_dict["assignees"]

    def test_task_str_representation(self):
        """Test task string representation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            task_str = str(task)
            assert "TSK-0001" in task_str
            assert "Test Task" in task_str


class TestTaskManager:
    """Test TaskManager class functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None
        self.project = None

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
        self.project = Project.create(project_path)
        return TaskManager(self.project)

    def test_task_manager_creation(self):
        """Test creating TaskManager."""
        task_manager = self._create_test_project()

        assert task_manager.project == self.project
        assert task_manager.tasks_dir == self.project.get_tasks_directory()

    def test_create_task(self):
        """Test creating a new task."""
        task_manager = self._create_test_project()

        task_data = {
            "title": "New Test Task",
            "description": "A new task for testing",
            "priority": "high",
            "assignees": ["bob"],
        }

        task = task_manager.create_task(task_data)

        assert task.model.title == "New Test Task"
        assert task.model.priority == "high"
        assert "bob" in task.model.assignees
        assert task.model.status == "open"  # Default status
        assert task.file_path.exists()

    def test_create_task_with_custom_id(self):
        """Test creating task with custom ID."""
        task_manager = self._create_test_project()

        task_data = {"id": "TSK-9999", "title": "Custom ID Task", "priority": "medium"}

        task = task_manager.create_task(task_data)

        assert task.model.id == "TSK-9999"
        assert task.file_path.name.startswith("TSK-9999")

    def test_create_task_auto_id_generation(self):
        """Test automatic ID generation."""
        task_manager = self._create_test_project()

        task_data = {"title": "Auto ID Task", "priority": "low"}

        task = task_manager.create_task(task_data)

        # Should have generated an ID
        assert task.model.id.startswith("TSK-")
        assert len(task.model.id) > 4

    def test_load_task_by_id(self):
        """Test loading task by ID."""
        task_manager = self._create_test_project()

        # Create a task first
        task_data = {"id": "TSK-0001", "title": "Load Test Task", "priority": "medium"}
        created_task = task_manager.create_task(task_data)

        # Load task by ID
        loaded_task = task_manager.load_task("TSK-0001")

        assert loaded_task.model.id == "TSK-0001"
        assert loaded_task.model.title == "Load Test Task"

    def test_load_task_by_id_not_found(self):
        """Test loading non-existent task by ID."""
        task_manager = self._create_test_project()

        with pytest.raises(TaskError, match="Task not found"):
            task_manager.load_task("TSK-9999")

    def test_load_task_by_file_path(self):
        """Test loading task by file path."""
        task_manager = self._create_test_project()

        # Create a task first
        task_data = {"id": "TSK-0001", "title": "Path Load Test", "priority": "medium"}
        created_task = task_manager.create_task(task_data)

        # Load task by file path
        loaded_task = task_manager.load_task_from_file(created_task.file_path)

        assert loaded_task.model.id == "TSK-0001"
        assert loaded_task.model.title == "Path Load Test"

    def test_list_all_tasks(self):
        """Test listing all tasks."""
        task_manager = self._create_test_project()

        # Create multiple tasks
        for i in range(3):
            task_data = {"title": f"Task {i+1}", "priority": "medium"}
            task_manager.create_task(task_data)

        # List all tasks
        all_tasks = task_manager.list_tasks()

        assert len(all_tasks) == 3
        assert all(isinstance(task, Task) for task in all_tasks)

    def test_list_tasks_by_status(self):
        """Test listing tasks by status."""
        task_manager = self._create_test_project()

        # Create tasks with different statuses
        open_task = task_manager.create_task({"title": "Open Task", "status": "open"})
        in_progress_task = task_manager.create_task(
            {"title": "In Progress Task", "status": "in_progress"}
        )
        completed_task = task_manager.create_task(
            {"title": "Completed Task", "status": "completed"}
        )

        # List open tasks
        open_tasks = task_manager.list_tasks(status="open")
        assert len(open_tasks) == 1
        assert open_tasks[0].model.title == "Open Task"

        # List completed tasks
        completed_tasks = task_manager.list_tasks(status="completed")
        assert len(completed_tasks) == 1
        assert completed_tasks[0].model.title == "Completed Task"

    def test_list_tasks_by_assignee(self):
        """Test listing tasks by assignee."""
        task_manager = self._create_test_project()

        # Create tasks with different assignees
        alice_task = task_manager.create_task(
            {"title": "Alice Task", "assignees": ["alice"]}
        )
        bob_task = task_manager.create_task({"title": "Bob Task", "assignees": ["bob"]})
        shared_task = task_manager.create_task(
            {"title": "Shared Task", "assignees": ["alice", "bob"]}
        )

        # List Alice's tasks
        alice_tasks = task_manager.list_tasks(assignee="alice")
        assert len(alice_tasks) == 2
        alice_titles = [task.model.title for task in alice_tasks]
        assert "Alice Task" in alice_titles
        assert "Shared Task" in alice_titles

        # List Bob's tasks
        bob_tasks = task_manager.list_tasks(assignee="bob")
        assert len(bob_tasks) == 2
        bob_titles = [task.model.title for task in bob_tasks]
        assert "Bob Task" in bob_titles
        assert "Shared Task" in bob_titles

    def test_list_tasks_by_tag(self):
        """Test listing tasks by tag."""
        task_manager = self._create_test_project()

        # Create tasks with different tags
        bug_task = task_manager.create_task({"title": "Bug Task", "tags": ["bug"]})
        feature_task = task_manager.create_task(
            {"title": "Feature Task", "tags": ["feature"]}
        )
        urgent_bug = task_manager.create_task(
            {"title": "Urgent Bug", "tags": ["bug", "urgent"]}
        )

        # List bug tasks
        bug_tasks = task_manager.list_tasks(tag="bug")
        assert len(bug_tasks) == 2
        bug_titles = [task.model.title for task in bug_tasks]
        assert "Bug Task" in bug_titles
        assert "Urgent Bug" in bug_titles

    def test_update_task(self):
        """Test updating an existing task."""
        task_manager = self._create_test_project()

        # Create a task
        task = task_manager.create_task(
            {"id": "TSK-0001", "title": "Original Title", "priority": "low"}
        )

        # Update the task
        updates = {
            "title": "Updated Title",
            "priority": "high",
            "description": "Added description",
        }
        updated_task = task_manager.update_task("TSK-0001", updates)

        assert updated_task.model.title == "Updated Title"
        assert updated_task.model.priority == "high"
        assert updated_task.model.description == "Added description"

    def test_delete_task(self):
        """Test deleting a task."""
        task_manager = self._create_test_project()

        # Create a task
        task = task_manager.create_task(
            {"id": "TSK-0001", "title": "To Delete", "priority": "medium"}
        )

        # Verify task exists
        assert task.file_path.exists()

        # Delete the task
        task_manager.delete_task("TSK-0001")

        # Verify task is deleted
        assert not task.file_path.exists()

        # Should not be able to load deleted task
        with pytest.raises(TaskError):
            task_manager.load_task("TSK-0001")

    def test_search_tasks(self):
        """Test searching tasks."""
        task_manager = self._create_test_project()

        # Create tasks with searchable content
        task_manager.create_task(
            {"title": "Fix login bug", "description": "User authentication is broken"}
        )
        task_manager.create_task(
            {
                "title": "Add login feature",
                "description": "Implement OAuth authentication",
            }
        )
        task_manager.create_task(
            {"title": "Update documentation", "description": "Fix typos in user guide"}
        )

        # Search for "login"
        login_tasks = task_manager.search_tasks("login")
        assert len(login_tasks) == 2

        # Search for "authentication"
        auth_tasks = task_manager.search_tasks("authentication")
        assert len(auth_tasks) == 2

        # Search for "documentation"
        doc_tasks = task_manager.search_tasks("documentation")
        assert len(doc_tasks) == 1

    def test_get_task_statistics(self):
        """Test getting task statistics."""
        task_manager = self._create_test_project()

        # Create tasks with different statuses
        task_manager.create_task({"title": "Open 1", "status": "open"})
        task_manager.create_task({"title": "Open 2", "status": "open"})
        task_manager.create_task({"title": "In Progress", "status": "in_progress"})
        task_manager.create_task({"title": "Completed", "status": "completed"})

        # Get statistics
        stats = task_manager.get_statistics()

        assert stats["total"] == 4
        assert stats["open"] == 2
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["cancelled"] == 0

    def test_move_task_to_status_directory(self):
        """Test moving task to status-based directory."""
        task_manager = self._create_test_project()

        # Create a task
        task = task_manager.create_task(
            {"id": "TSK-0001", "title": "Move Test", "status": "open"}
        )

        # Should be in open directory
        assert "open" in str(task.file_path)

        # Update status
        updated_task = task_manager.update_task("TSK-0001", {"status": "in_progress"})

        # Should now be in in_progress directory
        assert "in_progress" in str(updated_task.file_path)
        assert not task.file_path.exists()  # Old file should be moved


class TestTaskError:
    """Test TaskError exception."""

    def test_task_error_creation(self):
        """Test creating TaskError."""
        error = TaskError("Test error message")
        assert str(error) == "Test error message"

    def test_task_error_inheritance(self):
        """Test TaskError inheritance."""
        error = TaskError("Test error")
        assert isinstance(error, Exception)
