"""Unit tests for task management functionality."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ai_trackdown_pytools.core.models import TaskModel
from ai_trackdown_pytools.core.task import Task, TaskError, TaskManager


class TestTaskModel:
    """Test TaskModel data model functionality."""

    def test_task_model_creation(self):
        """Test creating a TaskModel."""
        now = datetime.now()
        data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "description": "This is a test task",
            "status": "open",
            "priority": "medium",
            "assignees": ["alice"],
            "tags": ["test", "unit"],
            "created_at": now,
            "updated_at": now,
        }

        model = TaskModel(**data)

        assert model.id == "TSK-0001"
        assert model.title == "Test Task"
        assert model.description == "This is a test task"
        assert model.status == "open"
        assert model.priority == "medium"
        assert "alice" in model.assignees
        assert "test" in model.tags

    def test_task_model_defaults(self):
        """Test TaskModel with default values."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0002", title="Minimal Task", created_at=now, updated_at=now
        )

        assert model.description == ""
        assert model.status == "open"
        assert model.priority == "medium"  # DEFAULT_PRIORITY
        assert model.assignees == []
        assert model.tags == []
        assert model.due_date is None
        assert model.estimated_hours is None

    def test_task_model_datetime_serialization(self):
        """Test datetime serialization in TaskModel."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0003",
            title="Date Test",
            created_at=now,
            updated_at=now,
            due_date=now,
        )

        # Get serialized version
        data = model.model_dump()

        # Check that dates are strings in ISO format
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
        assert isinstance(data["due_date"], str)


class TestTask:
    """Test Task class functionality."""

    def setup_method(self):
        """Setup test environment."""
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
            # Test property accessors
            assert task.id == "TSK-0001"
            assert task.title == "Test Task"
            assert task.description == "This is a test task"
            assert task.status == "open"
            assert task.priority == "medium"

    def test_task_creation_from_dict(self):
        """Test creating task from dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            assert task.model.id == "TSK-0001"
            assert task.model.title == "Test Task"
            assert task.file_path == file_path

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

            with pytest.raises(TaskError, match="No frontmatter found in task file"):
                Task.load(file_path)

    def test_task_update_method(self):
        """Test updating task data using update method."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            original_updated_at = task.updated_at

            # Update using the update method
            task.update(
                status="in_progress", priority="high", description="Updated description"
            )

            assert task.status == "in_progress"
            assert task.priority == "high"
            assert task.description == "Updated description"
            assert task.updated_at > original_updated_at

    def test_task_property_accessors(self):
        """Test task property accessors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"

            # Add more fields to test all properties
            extended_data = self.task_data.copy()
            extended_data.update(
                {
                    "due_date": datetime.now() + timedelta(days=7),
                    "estimated_hours": 8.5,
                    "actual_hours": 6.0,
                    "dependencies": ["TSK-0000"],
                    "parent": "EP-0001",
                    "labels": ["urgent", "backend"],
                    "metadata": {"custom_field": "value"},
                }
            )

            task = Task.from_dict(extended_data, file_path)

            # Test all property accessors
            assert task.id == "TSK-0001"
            assert task.title == "Test Task"
            assert task.description == "This is a test task"
            assert task.status == "open"
            assert task.priority == "medium"
            assert task.assignees == ["alice"]
            assert task.tags == ["test", "unit"]
            assert task.due_date == extended_data["due_date"]
            assert task.estimated_hours == 8.5
            assert task.actual_hours == 6.0
            assert task.dependencies == ["TSK-0000"]
            assert task.parent == "EP-0001"
            assert task.labels == ["urgent", "backend"]
            assert task.metadata == {"custom_field": "value"}

    def test_task_parent_setter(self):
        """Test setting parent property."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_task.md"
            task = Task.from_dict(self.task_data, file_path)

            # Test setting parent
            task.parent = "EP-0002"
            assert task.parent == "EP-0002"
            assert task.data.parent == "EP-0002"

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

    def test_task_extract_frontmatter(self):
        """Test extracting YAML frontmatter from content."""
        content = """---
id: TSK-0001
title: Test Task
---

# Content here
"""
        frontmatter = Task._extract_frontmatter(content)
        assert frontmatter["id"] == "TSK-0001"
        assert frontmatter["title"] == "Test Task"

        # Test with no frontmatter
        content_no_fm = "# Just content"
        assert Task._extract_frontmatter(content_no_fm) is None

        # Test with invalid YAML
        content_invalid = """---
invalid: yaml: {
---
"""
        assert Task._extract_frontmatter(content_invalid) is None


class TestTaskManager:
    """Test TaskManager class functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_manager(self):
        """Create a test task manager."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir)

        # Create a basic config file
        config_file = project_path / ".ai-trackdown" / "config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text(
            """
version: 1.0.0
tasks:
  directory: tickets
"""
        )

        return TaskManager(project_path)

    def test_task_manager_creation(self):
        """Test creating TaskManager."""
        task_manager = self._create_test_manager()

        assert task_manager.project_path == Path(self.temp_dir)
        assert task_manager.tasks_dir.name == "tickets"
        assert task_manager.tasks_dir.exists()

    def test_create_task(self):
        """Test creating a new task."""
        task_manager = self._create_test_manager()

        task = task_manager.create_task(
            title="New Test Task",
            description="A new task for testing",
            priority="high",
            assignees=["bob"],
        )

        assert task.model.title == "New Test Task"
        assert task.model.priority == "high"
        assert "bob" in task.model.assignees
        assert task.model.status == "open"  # Default status
        assert task.file_path.exists()

    def test_create_task_with_type(self):
        """Test creating task with specific type."""
        task_manager = self._create_test_manager()

        # Create a bug
        bug = task_manager.create_task(type="bug", title="Bug Report", priority="high")

        assert bug.model.id.startswith("BUG-")
        assert bug.model.title == "Bug Report"

    def test_load_task(self):
        """Test loading task by ID."""
        task_manager = self._create_test_manager()

        # Create a task first
        created_task = task_manager.create_task(
            title="Load Test Task", priority="medium"
        )

        task_id = created_task.model.id

        # Load task by ID
        loaded_task = task_manager.load_task(task_id)

        assert loaded_task.model.id == task_id
        assert loaded_task.model.title == "Load Test Task"

    def test_load_task_not_found(self):
        """Test loading non-existent task by ID."""
        task_manager = self._create_test_manager()

        with pytest.raises(TaskError, match="Task not found"):
            task_manager.load_task("TSK-9999")

    def test_list_tasks(self):
        """Test listing all tasks."""
        task_manager = self._create_test_manager()

        # Create multiple tasks
        for i in range(3):
            task_manager.create_task(title=f"Task {i+1}", priority="medium")

        # List all tasks
        all_tasks = task_manager.list_tasks()

        assert len(all_tasks) == 3
        assert all(isinstance(task, Task) for task in all_tasks)

    def test_list_tasks_by_status(self):
        """Test listing tasks by status."""
        task_manager = self._create_test_manager()

        # Create tasks with different statuses
        open_task = task_manager.create_task(title="Open Task", status="open")

        # Create and update another task
        task2 = task_manager.create_task(title="In Progress Task")
        task_manager.update_task(task2.model.id, status="in_progress")

        # Create completed task
        task3 = task_manager.create_task(title="Completed Task")
        task_manager.update_task(task3.model.id, status="completed")

        # List open tasks
        open_tasks = task_manager.list_tasks(status="open")
        assert len(open_tasks) == 1
        assert open_tasks[0].model.title == "Open Task"

        # List completed tasks
        completed_tasks = task_manager.list_tasks(status="completed")
        assert len(completed_tasks) == 1
        assert completed_tasks[0].model.title == "Completed Task"

    def test_list_tasks_by_tag(self):
        """Test listing tasks by tag."""
        task_manager = self._create_test_manager()

        # Create tasks with different tags
        bug_task = task_manager.create_task(title="Bug Task", tags=["bug"])
        feature_task = task_manager.create_task(title="Feature Task", tags=["feature"])
        urgent_bug = task_manager.create_task(
            title="Urgent Bug", tags=["bug", "urgent"]
        )

        # List bug tasks
        bug_tasks = task_manager.list_tasks(tag="bug")
        assert len(bug_tasks) == 2
        bug_titles = [task.model.title for task in bug_tasks]
        assert "Bug Task" in bug_titles
        assert "Urgent Bug" in bug_titles

    def test_update_task(self):
        """Test updating an existing task."""
        task_manager = self._create_test_manager()

        # Create a task
        task = task_manager.create_task(title="Original Title", priority="low")

        task_id = task.model.id

        # Update the task
        success = task_manager.update_task(
            task_id,
            title="Updated Title",
            priority="high",
            description="Added description",
        )

        assert success is True

        # Load and verify updates
        updated_task = task_manager.load_task(task_id)
        assert updated_task.model.title == "Updated Title"
        assert updated_task.model.priority == "high"
        assert updated_task.model.description == "Added description"

    def test_delete_task(self):
        """Test deleting a task."""
        task_manager = self._create_test_manager()

        # Create a task
        task = task_manager.create_task(title="To Delete", priority="medium")

        task_id = task.model.id

        # Verify task exists
        assert task.file_path.exists()

        # Delete the task
        success = task_manager.delete_task(task_id)
        assert success is True

        # Verify task is deleted
        assert not task.file_path.exists()

        # Should not be able to load deleted task
        with pytest.raises(TaskError):
            task_manager.load_task(task_id)

    def test_get_recent_tasks(self):
        """Test getting recent tasks."""
        task_manager = self._create_test_manager()

        # Create multiple tasks
        import time

        for i in range(7):
            task_manager.create_task(title=f"Task {i+1}", priority="medium")
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Get recent tasks (default limit is 5)
        recent_tasks = task_manager.get_recent_tasks()
        assert len(recent_tasks) == 5

        # Get recent tasks with custom limit
        recent_tasks_3 = task_manager.get_recent_tasks(limit=3)
        assert len(recent_tasks_3) == 3

        # Tasks should be sorted by creation date (newest first)
        for i in range(len(recent_tasks) - 1):
            assert recent_tasks[i].created_at >= recent_tasks[i + 1].created_at


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
