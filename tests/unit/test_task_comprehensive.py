"""Comprehensive unit tests for task management module."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from ai_trackdown_pytools.core.task import Task, TaskError, TaskManager, TaskModel


class TestTaskModel:
    """Test TaskModel functionality."""

    def test_task_model_creation_minimal(self):
        """Test creating TaskModel with minimal data."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0001", title="Test Task", created_at=now, updated_at=now
        )

        assert model.id == "TSK-0001"
        assert model.title == "Test Task"
        assert model.description == ""
        assert model.status == "open"
        assert model.priority == "medium"
        assert model.assignees == []
        assert model.tags == []
        assert model.created_at == now
        assert model.updated_at == now
        assert model.due_date is None

    def test_task_model_creation_full(self):
        """Test creating TaskModel with all fields."""
        now = datetime.now()
        due = now + timedelta(days=7)

        model = TaskModel(
            id="TSK-0002",
            title="Complex Task",
            description="Detailed description",
            status="in-progress",
            priority="high",
            assignees=["user1", "user2"],
            tags=["feature", "urgent"],
            created_at=now,
            updated_at=now,
            due_date=due,
            estimated_hours=8.5,
            actual_hours=2.0,
            dependencies=["TSK-0001"],
            parent="EPIC-001",
            labels=["backend", "api"],
            metadata={"custom": "value"},
        )

        assert model.id == "TSK-0002"
        assert model.title == "Complex Task"
        assert model.description == "Detailed description"
        assert model.status == "in-progress"
        assert model.priority == "high"
        assert model.assignees == ["user1", "user2"]
        assert model.tags == ["feature", "urgent"]
        assert model.due_date == due
        assert model.estimated_hours == 8.5
        assert model.actual_hours == 2.0
        assert model.dependencies == ["TSK-0001"]
        assert model.parent == "EPIC-001"
        assert model.labels == ["backend", "api"]
        assert model.metadata == {"custom": "value"}

    def test_task_model_datetime_serialization(self):
        """Test datetime serialization."""
        now = datetime.now()
        due = now + timedelta(days=7)

        model = TaskModel(
            id="TSK-0003",
            title="Test Task",
            created_at=now,
            updated_at=now,
            due_date=due,
        )

        # Test serialization
        data = model.model_dump()
        assert data["created_at"] == now.isoformat()
        assert data["updated_at"] == now.isoformat()
        assert data["due_date"] == due.isoformat()

    def test_task_model_validation(self):
        """Test TaskModel validation."""
        # Missing required fields should raise error
        with pytest.raises(ValueError):
            TaskModel(id="TSK-0001")  # Missing title and timestamps


class TestTask:
    """Test Task class functionality."""

    def test_task_initialization(self):
        """Test Task initialization."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0001", title="Test Task", created_at=now, updated_at=now
        )
        file_path = Path("/tasks/TSK-0001.md")

        task = Task(model, file_path)

        assert task.data == model
        assert task.file_path == file_path

    def test_task_properties(self):
        """Test Task property accessors."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0001",
            title="Test Task",
            description="Test description",
            status="open",
            priority="high",
            assignees=["user1"],
            tags=["test"],
            created_at=now,
            updated_at=now,
        )

        task = Task(model, Path("/tasks/TSK-0001.md"))

        assert task.id == "TSK-0001"
        assert task.title == "Test Task"
        assert task.description == "Test description"
        assert task.status == "open"
        assert task.priority == "high"
        assert task.assignees == ["user1"]
        assert task.tags == ["test"]
        assert task.created_at == now
        assert task.updated_at == now

    def test_task_load_success(self):
        """Test loading task from file."""
        now = datetime.now()
        file_content = f"""---
id: TSK-0001
title: Test Task
description: Test description
status: open
priority: high
assignees:
  - user1
tags:
  - test
created_at: {now.isoformat()}
updated_at: {now.isoformat()}
---

# Test Task

## Description
Test description"""

        with patch("builtins.open", mock_open(read_data=file_content)):
            task = Task.load(Path("/tasks/TSK-0001.md"))

            assert task.id == "TSK-0001"
            assert task.title == "Test Task"
            assert task.status == "open"

    def test_task_load_invalid_frontmatter(self):
        """Test loading task with invalid frontmatter."""
        file_content = """---
invalid yaml content {{
---

# Test Task"""

        with patch("builtins.open", mock_open(read_data=file_content)):
            with pytest.raises(TaskError) as exc_info:
                Task.load(Path("/tasks/TSK-0001.md"))

            assert "Failed to parse task file" in str(exc_info.value)

    def test_task_load_missing_frontmatter(self):
        """Test loading task without frontmatter."""
        file_content = """# Test Task

Just a regular markdown file without frontmatter."""

        with patch("builtins.open", mock_open(read_data=file_content)):
            with pytest.raises(TaskError) as exc_info:
                Task.load(Path("/tasks/TSK-0001.md"))

            assert "Failed to parse task file" in str(exc_info.value)

    def test_task_update(self):
        """Test updating task data."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0001",
            title="Original Title",
            status="open",
            created_at=now,
            updated_at=now,
        )

        task = Task(model, Path("/tasks/TSK-0001.md"))

        # Update task
        original_updated = task.updated_at
        task.update(title="Updated Title", status="in-progress", priority="high")

        assert task.title == "Updated Title"
        assert task.status == "in-progress"
        assert task.priority == "high"
        assert task.updated_at > original_updated

    def test_task_update_invalid_field(self):
        """Test updating with invalid field doesn't raise error."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0001", title="Test Task", created_at=now, updated_at=now
        )

        task = Task(model, Path("/tasks/TSK-0001.md"))

        # Should not raise error
        task.update(invalid_field="value")

    def test_task_to_dict(self):
        """Test converting task to dictionary."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-0001", title="Test Task", created_at=now, updated_at=now
        )

        task = Task(model, Path("/tasks/TSK-0001.md"))
        data = task.to_dict()

        assert isinstance(data, dict)
        assert data["id"] == "TSK-0001"
        assert data["title"] == "Test Task"
        assert "created_at" in data
        assert "updated_at" in data

    def test_extract_frontmatter_valid(self):
        """Test extracting valid frontmatter."""
        content = """---
id: TSK-0001
title: Test Task
---

# Content"""

        result = Task._extract_frontmatter(content)

        assert result == {"id": "TSK-0001", "title": "Test Task"}

    def test_extract_frontmatter_empty(self):
        """Test extracting empty frontmatter."""
        content = """---
---

# Content"""

        result = Task._extract_frontmatter(content)

        assert result == {}

    def test_extract_frontmatter_invalid_yaml(self):
        """Test extracting invalid YAML frontmatter."""
        content = """---
invalid: yaml {{
---

# Content"""

        result = Task._extract_frontmatter(content)

        assert result is None


class TestTaskManager:
    """Test TaskManager functionality."""

    def test_task_manager_initialization(self):
        """Test TaskManager initialization."""
        with patch("ai_trackdown_pytools.core.config.Config") as mock_config_class:
            mock_config = Mock()
            mock_config_class.load.return_value = mock_config

            project_path = Path("/test/project")
            manager = TaskManager(project_path)

            assert manager.project_path == project_path
            assert manager.tasks_dir == project_path / "tasks"
            assert manager.config == mock_config

    @patch("pathlib.Path.mkdir")
    def test_task_manager_creates_tasks_dir(self, mock_mkdir):
        """Test TaskManager creates tasks directory."""
        with patch("ai_trackdown_pytools.core.config.Config.load"):
            TaskManager(Path("/test/project"))

            mock_mkdir.assert_called_once_with(exist_ok=True)

    @patch("ai_trackdown_pytools.core.config.Config")
    def test_create_task_minimal(self, mock_config_class):
        """Test creating task with minimal data."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.id_format": "TSK-{counter:04d}",
            "tasks.counter": 1,
        }.get(key, default)
        mock_config_class.load.return_value = mock_config

        manager = TaskManager(Path("/test/project"))

        with patch.object(manager, "_find_task_file", return_value=None):
            with patch.object(manager, "_save_task_file") as mock_save:
                task = manager.create_task(title="New Task")

                assert task.id == "TSK-0001"
                assert task.title == "New Task"
                assert task.status == "open"
                assert task.priority == "medium"

                # Verify save was called
                mock_save.assert_called_once()

                # Verify counter was updated
                mock_config.set.assert_called_with("tasks.counter", 2)
                mock_config.save.assert_called_once()

    @patch("ai_trackdown_pytools.core.config.Config")
    def test_create_task_full_data(self, mock_config_class):
        """Test creating task with all data."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.id_format": "TSK-{counter:04d}",
            "tasks.counter": 1,
        }.get(key, default)
        mock_config_class.load.return_value = mock_config

        manager = TaskManager(Path("/test/project"))

        due_date = datetime.now() + timedelta(days=7)

        with patch.object(manager, "_find_task_file", return_value=None):
            with patch.object(manager, "_save_task_file") as mock_save:
                task = manager.create_task(
                    title="Complex Task",
                    description="Detailed description",
                    status="in-progress",
                    priority="high",
                    assignees=["user1", "user2"],
                    tags=["feature", "urgent"],
                    due_date=due_date,
                    estimated_hours=8.5,
                    dependencies=["TSK-0000"],
                    parent="EPIC-001",
                    labels=["backend"],
                    metadata={"custom": "value"},
                )

                assert task.title == "Complex Task"
                assert task.description == "Detailed description"
                assert task.status == "in-progress"
                assert task.priority == "high"
                assert task.assignees == ["user1", "user2"]
                assert task.tags == ["feature", "urgent"]
                assert task.data.due_date == due_date

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_generate_task_id_unique(self, mock_config_load):
        """Test generating unique task IDs."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.id_format": "TSK-{counter:04d}",
            "tasks.counter": 1,
        }.get(key, default)
        mock_config_load.return_value = mock_config

        manager = TaskManager(Path("/test/project"))

        # Mock existing files
        with patch.object(manager, "_find_task_file") as mock_find:
            mock_find.side_effect = [
                Path("/tasks/TSK-0001.md"),  # First ID exists
                Path("/tasks/TSK-0002.md"),  # Second ID exists
                None,  # Third ID is available
            ]

            task_id = manager._generate_task_id()

            assert task_id == "TSK-0003"
            mock_config.set.assert_called_with("tasks.counter", 4)

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_get_task_file_path(self, mock_config_load):
        """Test getting task file path."""
        manager = TaskManager(Path("/test/project"))

        # Test with hyphenated ID
        path = manager._get_task_file_path("TSK-0001")
        assert path == Path("/test/project/tasks/tsk/TSK-0001.md")

        # Test without hyphen
        path = manager._get_task_file_path("TASK001")
        assert path == Path("/test/project/tasks/misc/TASK001.md")

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_find_task_file(self, mock_config_load):
        """Test finding task file."""
        manager = TaskManager(Path("/test/project"))

        with patch.object(manager.tasks_dir, "rglob") as mock_rglob:
            mock_rglob.return_value = [
                Path("/test/project/tasks/tsk/TSK-0001.md"),
                Path("/test/project/tasks/tsk/TSK-0002.md"),
                Path("/test/project/tasks/misc/OTHER-001.md"),
            ]

            # Find existing task
            result = manager._find_task_file("TSK-0002")
            assert result == Path("/test/project/tasks/tsk/TSK-0002.md")

            # Find non-existent task
            result = manager._find_task_file("TSK-9999")
            assert result is None

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_load_task_success(self, mock_config_load):
        """Test loading task successfully."""
        manager = TaskManager(Path("/test/project"))

        task_path = Path("/test/project/tasks/TSK-0001.md")

        with patch.object(manager, "_find_task_file", return_value=task_path):
            with patch.object(manager, "_load_task_file") as mock_load:
                mock_task_data = Mock()
                mock_load.return_value = mock_task_data

                task = manager.load_task("TSK-0001")

                assert isinstance(task, Task)
                assert task.data == mock_task_data
                assert task.file_path == task_path

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_load_task_not_found(self, mock_config_load):
        """Test loading non-existent task."""
        manager = TaskManager(Path("/test/project"))

        with patch.object(manager, "_find_task_file", return_value=None):
            with pytest.raises(TaskError) as exc_info:
                manager.load_task("TSK-9999")

            assert "Task not found: TSK-9999" in str(exc_info.value)

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_list_tasks(self, mock_config_load):
        """Test listing tasks."""
        manager = TaskManager(Path("/test/project"))

        now = datetime.now()

        # Create mock task data
        task1_data = TaskModel(
            id="TSK-0001",
            title="Task 1",
            status="open",
            tags=["bug"],
            created_at=now - timedelta(days=2),
            updated_at=now,
        )

        task2_data = TaskModel(
            id="TSK-0002",
            title="Task 2",
            status="closed",
            tags=["feature"],
            created_at=now - timedelta(days=1),
            updated_at=now,
        )

        with patch.object(manager.tasks_dir, "rglob") as mock_rglob:
            mock_rglob.return_value = [
                Path("/tasks/TSK-0001.md"),
                Path("/tasks/TSK-0002.md"),
            ]

            with patch.object(manager, "_load_task_file") as mock_load:
                mock_load.side_effect = [task1_data, task2_data]

                # List all tasks
                tasks = manager.list_tasks()
                assert len(tasks) == 2
                assert tasks[0].id == "TSK-0002"  # Newer first
                assert tasks[1].id == "TSK-0001"

                # List with status filter
                mock_load.side_effect = [task1_data, task2_data]
                tasks = manager.list_tasks(status="open")
                assert len(tasks) == 1
                assert tasks[0].id == "TSK-0001"

                # List with tag filter
                mock_load.side_effect = [task1_data, task2_data]
                tasks = manager.list_tasks(tag="feature")
                assert len(tasks) == 1
                assert tasks[0].id == "TSK-0002"

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_get_recent_tasks(self, mock_config_load):
        """Test getting recent tasks."""
        manager = TaskManager(Path("/test/project"))

        now = datetime.now()
        tasks_data = []

        # Create 10 tasks with different update times
        for i in range(10):
            task_data = TaskModel(
                id=f"TSK-{i:04d}",
                title=f"Task {i}",
                created_at=now - timedelta(days=10),
                updated_at=now - timedelta(hours=i),
            )
            tasks_data.append(Task(task_data, Path(f"/tasks/TSK-{i:04d}.md")))

        with patch.object(manager, "list_tasks", return_value=tasks_data):
            recent = manager.get_recent_tasks(limit=5)

            assert len(recent) == 5
            assert recent[0].id == "TSK-0000"  # Most recent
            assert recent[4].id == "TSK-0004"

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_update_task(self, mock_config_load):
        """Test updating task."""
        manager = TaskManager(Path("/test/project"))

        mock_task = Mock()

        with patch.object(manager, "load_task", return_value=mock_task) as mock_load:
            with patch.object(manager, "_save_task_file") as mock_save:
                result = manager.update_task(
                    "TSK-0001", title="Updated Title", status="closed"
                )

                assert result is True
                mock_task.update.assert_called_once_with(
                    title="Updated Title", status="closed"
                )
                mock_save.assert_called_once_with(mock_task.data, mock_task.file_path)

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_update_task_not_found(self, mock_config_load):
        """Test updating non-existent task."""
        manager = TaskManager(Path("/test/project"))

        with patch.object(manager, "load_task", return_value=None):
            result = manager.update_task("TSK-9999", title="Updated")

            assert result is False

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_delete_task_success(self, mock_config_load):
        """Test deleting task."""
        manager = TaskManager(Path("/test/project"))

        task_path = Path("/test/project/tasks/TSK-0001.md")
        mock_unlink = Mock()
        task_path.unlink = mock_unlink

        with patch.object(manager, "_find_task_file", return_value=task_path):
            result = manager.delete_task("TSK-0001")

            assert result is True
            mock_unlink.assert_called_once()

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_delete_task_not_found(self, mock_config_load):
        """Test deleting non-existent task."""
        manager = TaskManager(Path("/test/project"))

        with patch.object(manager, "_find_task_file", return_value=None):
            result = manager.delete_task("TSK-9999")

            assert result is False

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_save_task_file(self, mock_config_load):
        """Test saving task file."""
        manager = TaskManager(Path("/test/project"))

        now = datetime.now()
        task_data = TaskModel(
            id="TSK-0001",
            title="Test Task",
            description="Test description",
            status="open",
            priority="high",
            assignees=["user1"],
            tags=["test"],
            created_at=now,
            updated_at=now,
            due_date=now + timedelta(days=7),
        )

        file_path = Path("/test/project/tasks/TSK-0001.md")

        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            with patch.object(file_path.parent, "mkdir") as mock_mkdir:
                manager._save_task_file(task_data, file_path)

                # Verify directory creation
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

                # Verify file was opened for writing
                mock_file.assert_called_once_with(file_path, "w", encoding="utf-8")

                # Verify content was written
                written_content = "".join(
                    call.args[0] for call in mock_file().write.call_args_list
                )

                assert "TSK-0001" in written_content
                assert "Test Task" in written_content
                assert "Test description" in written_content
                assert "Status: open" in written_content
                assert "Priority: high" in written_content

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_load_task_file_datetime_parsing(self, mock_config_load):
        """Test loading task file with datetime parsing."""
        manager = TaskManager(Path("/test/project"))

        now = datetime.now()
        due = now + timedelta(days=7)

        file_content = f"""---
id: TSK-0001
title: Test Task
created_at: {now.isoformat()}
updated_at: {now.isoformat()}
due_date: {due.isoformat()}
---"""

        with patch("builtins.open", mock_open(read_data=file_content)):
            task_data = manager._load_task_file(Path("/tasks/TSK-0001.md"))

            assert isinstance(task_data.created_at, datetime)
            assert isinstance(task_data.updated_at, datetime)
            assert isinstance(task_data.due_date, datetime)

    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_load_task_file_error_handling(self, mock_config_load):
        """Test loading task file with errors."""
        manager = TaskManager(Path("/test/project"))

        # Test file read error
        with patch("builtins.open", side_effect=OSError("File not found")):
            result = manager._load_task_file(Path("/tasks/TSK-0001.md"))
            assert result is None

        # Test invalid YAML
        with patch("builtins.open", mock_open(read_data="Invalid content")):
            result = manager._load_task_file(Path("/tasks/TSK-0001.md"))
            assert result is None


class TestTaskError:
    """Test TaskError exception."""

    def test_task_error_message(self):
        """Test TaskError carries message."""
        error = TaskError("Test error message")
        assert str(error) == "Test error message"

    def test_task_error_inheritance(self):
        """Test TaskError inherits from Exception."""
        error = TaskError("Test")
        assert isinstance(error, Exception)
