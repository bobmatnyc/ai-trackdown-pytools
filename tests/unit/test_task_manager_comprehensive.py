"""Comprehensive unit tests for Task and TicketManager functionality."""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from ai_trackdown_pytools.core.models import TaskModel
from ai_trackdown_pytools.core.task import Task, TaskError, TicketManager
from ai_trackdown_pytools.exceptions import AiTrackdownError


class TestTaskClass:
    """Test Task class functionality."""

    def test_task_creation_from_model(self):
        """Test creating Task from TaskModel."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            description="Test Description",
            created_at=now,
            updated_at=now,
        )
        file_path = Path("/test/task.md")
        
        task = Task(model, file_path)
        
        assert task.data == model
        assert task.model == model  # Backward compatibility alias
        assert task.file_path == file_path

    def test_task_from_dict(self):
        """Test creating Task from dictionary."""
        now = datetime.now()
        data = {
            "id": "TSK-001",
            "title": "Test Task",
            "description": "Test Description",
            "created_at": now,
            "updated_at": now,
        }
        file_path = Path("/test/task.md")
        
        task = Task.from_dict(data, file_path)
        
        assert task.data.id == "TSK-001"
        assert task.data.title == "Test Task"
        assert task.file_path == file_path

    @patch('ai_trackdown_pytools.utils.frontmatter.parse_ticket_file')
    def test_task_load_from_file(self, mock_parse):
        """Test loading Task from file."""
        now = datetime.now()
        frontmatter = {
            "id": "TSK-001",
            "title": "Test Task",
            "description": "Test Description",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        mock_parse.return_value = (frontmatter, "content")
        
        file_path = Path("/test/task.md")
        with patch.object(file_path, 'exists', return_value=True):
            task = Task.load(file_path)
        
        assert task.data.id == "TSK-001"
        assert task.data.title == "Test Task"
        assert isinstance(task.data.created_at, datetime)

    def test_task_load_file_not_found(self):
        """Test loading Task from non-existent file."""
        file_path = Path("/test/nonexistent.md")
        
        with pytest.raises(TaskError, match="Task file not found"):
            Task.load(file_path)

    @patch('ai_trackdown_pytools.utils.frontmatter.write_ticket_file')
    @patch('ai_trackdown_pytools.utils.index.update_index_on_file_change')
    def test_task_save(self, mock_update_index, mock_write):
        """Test saving Task to file."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            created_at=now,
            updated_at=now,
        )
        file_path = Path("/test/task.md")
        
        mock_result = Mock()
        mock_result.valid = True
        mock_write.return_value = mock_result
        
        task = Task(model, file_path)
        
        with patch.object(file_path.parent, 'mkdir'):
            task.save("content")
        
        mock_write.assert_called_once()
        mock_update_index.assert_called_once_with(file_path, "modified")

    def test_task_update_status(self):
        """Test updating task status."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            status="open",
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task.update_status("in_progress")
        
        assert task.data.status == "in_progress"
        assert task.data.updated_at > now

    def test_task_add_assignee(self):
        """Test adding assignee to task."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            assignees=[],
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task.add_assignee("user@example.com")
        
        assert "user@example.com" in task.data.assignees
        assert task.data.updated_at > now

    def test_task_add_assignee_duplicate(self):
        """Test adding duplicate assignee."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            assignees=["user@example.com"],
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task.add_assignee("user@example.com")
        
        # Should not add duplicate
        assert task.data.assignees.count("user@example.com") == 1

    def test_task_remove_assignee(self):
        """Test removing assignee from task."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            assignees=["user@example.com"],
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task.remove_assignee("user@example.com")
        
        assert "user@example.com" not in task.data.assignees
        assert task.data.updated_at > now

    def test_task_add_tag(self):
        """Test adding tag to task."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            tags=[],
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task.add_tag("urgent")
        
        assert "urgent" in task.data.tags
        assert task.data.updated_at > now

    def test_task_remove_tag(self):
        """Test removing tag from task."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            tags=["urgent"],
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task.remove_tag("urgent")
        
        assert "urgent" not in task.data.tags
        assert task.data.updated_at > now

    def test_task_is_overdue_no_due_date(self):
        """Test is_overdue with no due date."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            due_date=None,
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        assert not task.is_overdue()

    def test_task_is_overdue_completed(self):
        """Test is_overdue with completed task."""
        now = datetime.now()
        past_date = now - timedelta(days=1)
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            status="completed",
            due_date=past_date,
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        assert not task.is_overdue()

    def test_task_is_overdue_past_due(self):
        """Test is_overdue with past due date."""
        now = datetime.now()
        past_date = now - timedelta(days=1)
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            status="open",
            due_date=past_date,
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        assert task.is_overdue()

    def test_task_properties(self):
        """Test task property accessors."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            description="Test Description",
            status="open",
            priority="high",
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        assert task.id == "TSK-001"
        assert task.title == "Test Task"
        assert task.description == "Test Description"
        assert task.status == "open"
        assert task.priority == "high"

    def test_task_update(self):
        """Test task update method."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task.update(title="Updated Task", priority="high")
        
        assert task.data.title == "Updated Task"
        assert task.data.priority == "high"
        assert task.data.updated_at > now

    def test_task_to_dict(self):
        """Test task to_dict method."""
        now = datetime.now()
        model = TaskModel(
            id="TSK-001",
            title="Test Task",
            created_at=now,
            updated_at=now,
        )
        task = Task(model, Path("/test/task.md"))
        
        task_dict = task.to_dict()
        
        assert task_dict["id"] == "TSK-001"
        assert task_dict["title"] == "Test Task"
        assert isinstance(task_dict, dict)


class TestTicketManagerBasics:
    """Test TicketManager basic functionality."""

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_ticket_manager_init_with_path(self, mock_config_load):
        """Test TicketManager initialization with Path."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config
        
        project_path = Path("/test/project")
        
        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)
        
        assert manager.project_path == project_path
        assert manager.project is None
        assert manager.tasks_dir == project_path / "tickets"

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_ticket_manager_init_with_project(self, mock_config_load):
        """Test TicketManager initialization with Project object."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config
        
        mock_project = Mock()
        mock_project.path = "/test/project"
        
        with patch.object(Path, 'mkdir'):
            manager = TicketManager(mock_project)
        
        assert manager.project == mock_project
        assert manager.project_path == Path("/test/project")

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_ticket_manager_creates_tasks_dir(self, mock_config_load):
        """Test TicketManager creates tasks directory."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config
        
        project_path = Path("/test/project")
        
        with patch.object(project_path, 'mkdir') as mock_mkdir:
            with patch.object((project_path / "tickets"), 'mkdir') as mock_tasks_mkdir:
                TicketManager(project_path)
        
        mock_tasks_mkdir.assert_called_once_with(exist_ok=True)


class TestTicketManagerCRUD:
    """Test TicketManager CRUD operations."""

    @patch('ai_trackdown_pytools.core.config.Config.load')
    @patch('ai_trackdown_pytools.utils.index.update_index_on_file_change')
    def test_create_task_minimal(self, mock_update_index, mock_config_load):
        """Test creating task with minimal data."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.directory": "tickets",
            "tasks.counter": 1,
        }.get(key, default)
        mock_config.set = Mock()
        mock_config.save = Mock()
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        with patch.object(manager, '_save_task_file') as mock_save:
            with patch.object(manager, '_find_task_file', return_value=None):
                task = manager.create_task(title="Test Task")

        assert task.data.title == "Test Task"
        assert task.data.id.startswith("TSK-")
        assert task.data.status == "open"
        mock_save.assert_called_once()
        mock_update_index.assert_called_once()

    @patch('ai_trackdown_pytools.core.config.Config.load')
    @patch('ai_trackdown_pytools.utils.index.update_index_on_file_change')
    def test_create_task_full(self, mock_update_index, mock_config_load):
        """Test creating task with full data."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.directory": "tickets",
            "tasks.counter": 1,
        }.get(key, default)
        mock_config.set = Mock()
        mock_config.save = Mock()
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        with patch.object(manager, '_save_task_file') as mock_save:
            with patch.object(manager, '_find_task_file', return_value=None):
                task = manager.create_task(
                    title="Full Task",
                    description="Full description",
                    priority="high",
                    assignees=["user@example.com"],
                    tags=["urgent", "backend"],
                    estimated_hours=8.0,
                )

        assert task.data.title == "Full Task"
        assert task.data.description == "Full description"
        assert task.data.priority == "high"
        assert "user@example.com" in task.data.assignees
        assert "urgent" in task.data.tags
        assert task.data.estimated_hours == 8.0

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_create_task_with_task_data_dict(self, mock_config_load):
        """Test creating task with task_data dictionary."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.directory": "tickets",
            "tasks.counter": 1,
        }.get(key, default)
        mock_config.set = Mock()
        mock_config.save = Mock()
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        task_data = {"title": "Dict Task", "priority": "low"}

        with patch.object(manager, '_save_task_file') as mock_save:
            with patch.object(manager, '_find_task_file', return_value=None):
                task = manager.create_task(task_data=task_data, description="Added desc")

        assert task.data.title == "Dict Task"
        assert task.data.priority == "low"
        assert task.data.description == "Added desc"

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_load_task_success(self, mock_config_load):
        """Test loading task successfully."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        mock_task_file = Path("/test/project/tickets/TSK-001.md")
        mock_task_data = TaskModel(
            id="TSK-001",
            title="Test Task",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch.object(manager, '_find_task_file', return_value=mock_task_file):
            with patch.object(manager, '_load_task_file', return_value=mock_task_data):
                task = manager.load_task("TSK-001")

        assert task is not None
        assert task.data.id == "TSK-001"
        assert task.file_path == mock_task_file

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_load_task_not_found(self, mock_config_load):
        """Test loading non-existent task."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        with patch.object(manager, '_find_task_file', return_value=None):
            task = manager.load_task("TSK-999")

        assert task is None

    @patch('ai_trackdown_pytools.core.config.Config.load')
    @patch('ai_trackdown_pytools.utils.index.update_index_on_file_change')
    def test_update_task_success(self, mock_update_index, mock_config_load):
        """Test updating task successfully."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        mock_task = Mock()
        mock_task.data = Mock()
        mock_task.file_path = Path("/test/task.md")

        with patch.object(manager, 'load_task', return_value=mock_task):
            with patch.object(manager, '_save_task_file') as mock_save:
                result = manager.update_task("TSK-001", title="Updated Title")

        assert result is True
        mock_task.update.assert_called_once_with(title="Updated Title")
        mock_save.assert_called_once_with(mock_task.data, mock_task.file_path)
        mock_update_index.assert_called_once()

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_update_task_not_found(self, mock_config_load):
        """Test updating non-existent task."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        with patch.object(manager, 'load_task', return_value=None):
            result = manager.update_task("TSK-999", title="Updated Title")

        assert result is False

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_delete_task_success(self, mock_config_load):
        """Test deleting task successfully."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        mock_task_file = Mock()
        mock_task_file.unlink = Mock()

        with patch.object(manager, '_find_task_file', return_value=mock_task_file):
            result = manager.delete_task("TSK-001")

        assert result is True
        mock_task_file.unlink.assert_called_once()

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_delete_task_not_found(self, mock_config_load):
        """Test deleting non-existent task."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        with patch.object(manager, '_find_task_file', return_value=None):
            result = manager.delete_task("TSK-999")

        assert result is False


class TestTicketManagerListing:
    """Test TicketManager listing and filtering functionality."""

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_list_tasks_all(self, mock_config_load):
        """Test listing all tasks."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        # Mock task files
        mock_files = [
            Path("/test/project/tickets/TSK-001.md"),
            Path("/test/project/tickets/TSK-002.md"),
        ]

        # Mock task data
        now = datetime.now()
        mock_tasks = [
            TaskModel(id="TSK-001", title="Task 1", created_at=now, updated_at=now),
            TaskModel(id="TSK-002", title="Task 2", created_at=now, updated_at=now),
        ]

        with patch.object(manager.tasks_dir, 'rglob', return_value=mock_files):
            with patch.object(manager, '_load_task_file', side_effect=mock_tasks):
                tasks = manager.list_tasks()

        assert len(tasks) == 2
        assert tasks[0].data.id == "TSK-001"
        assert tasks[1].data.id == "TSK-002"

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_list_tasks_filtered_by_status(self, mock_config_load):
        """Test listing tasks filtered by status."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        # Mock task files
        mock_files = [
            Path("/test/project/tickets/TSK-001.md"),
            Path("/test/project/tickets/TSK-002.md"),
        ]

        # Mock task data with different statuses
        now = datetime.now()
        mock_tasks = [
            TaskModel(id="TSK-001", title="Task 1", status="open", created_at=now, updated_at=now),
            TaskModel(id="TSK-002", title="Task 2", status="completed", created_at=now, updated_at=now),
        ]

        with patch.object(manager.tasks_dir, 'rglob', return_value=mock_files):
            with patch.object(manager, '_load_task_file', side_effect=mock_tasks):
                open_tasks = manager.list_tasks(status="open")

        assert len(open_tasks) == 1
        assert open_tasks[0].data.status == "open"

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_list_tasks_filtered_by_tag(self, mock_config_load):
        """Test listing tasks filtered by tag."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        # Mock task files
        mock_files = [
            Path("/test/project/tickets/TSK-001.md"),
            Path("/test/project/tickets/TSK-002.md"),
        ]

        # Mock task data with different tags
        now = datetime.now()
        mock_tasks = [
            TaskModel(id="TSK-001", title="Task 1", tags=["urgent"], created_at=now, updated_at=now),
            TaskModel(id="TSK-002", title="Task 2", tags=["normal"], created_at=now, updated_at=now),
        ]

        with patch.object(manager.tasks_dir, 'rglob', return_value=mock_files):
            with patch.object(manager, '_load_task_file', side_effect=mock_tasks):
                urgent_tasks = manager.list_tasks(tag="urgent")

        assert len(urgent_tasks) == 1
        assert "urgent" in urgent_tasks[0].data.tags

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_get_recent_tasks(self, mock_config_load):
        """Test getting recent tasks."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        # Mock list_tasks to return tasks
        now = datetime.now()
        mock_tasks = [
            Mock(updated_at=now - timedelta(hours=1)),
            Mock(updated_at=now - timedelta(hours=2)),
            Mock(updated_at=now - timedelta(hours=3)),
        ]

        with patch.object(manager, 'list_tasks', return_value=mock_tasks):
            recent_tasks = manager.get_recent_tasks(limit=2)

        assert len(recent_tasks) == 2
        # Should be sorted by updated_at descending
        assert recent_tasks[0].updated_at > recent_tasks[1].updated_at

    @patch('ai_trackdown_pytools.core.config.Config.load')
    @patch('ai_trackdown_pytools.utils.index.update_index_on_file_change')
    def test_save_task(self, mock_update_index, mock_config_load):
        """Test saving task."""
        mock_config = Mock()
        mock_config.get.return_value = "tickets"
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        mock_task = Mock()
        mock_task.data = Mock()
        mock_task.file_path = Path("/test/task.md")

        with patch.object(manager, '_save_task_file') as mock_save:
            manager.save_task(mock_task)

        mock_save.assert_called_once_with(mock_task.data, mock_task.file_path)
        mock_update_index.assert_called_once()


class TestTicketManagerIDGeneration:
    """Test TicketManager ID generation functionality."""

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_generate_task_id_default(self, mock_config_load):
        """Test generating task ID with default type."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.directory": "tickets",
            "tasks.counter": 5,
        }.get(key, default)
        mock_config.set = Mock()
        mock_config.save = Mock()
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        with patch.object(manager, '_find_task_file', return_value=None):
            task_id = manager._generate_task_id()

        assert task_id == "TSK-0005"
        mock_config.set.assert_called_with("tasks.counter", 6)
        mock_config.save.assert_called_once()

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_generate_task_id_epic(self, mock_config_load):
        """Test generating epic ID."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.directory": "tickets",
            "epics.counter": 2,
        }.get(key, default)
        mock_config.set = Mock()
        mock_config.save = Mock()
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        with patch.object(manager, '_find_task_file', return_value=None):
            task_id = manager._generate_task_id("epic")

        assert task_id == "EP-0002"
        mock_config.set.assert_called_with("epics.counter", 3)

    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_generate_task_id_collision_handling(self, mock_config_load):
        """Test handling ID collisions."""
        mock_config = Mock()
        mock_config.get.side_effect = lambda key, default: {
            "tasks.directory": "tickets",
            "tasks.counter": 1,
        }.get(key, default)
        mock_config.set = Mock()
        mock_config.save = Mock()
        mock_config_load.return_value = mock_config

        project_path = Path("/test/project")

        with patch.object(Path, 'mkdir'):
            manager = TicketManager(project_path)

        # Mock finding existing file for first ID, but not second
        def mock_find_task_file(task_id):
            if task_id == "TSK-0001":
                return Path("/existing/file.md")
            return None

        with patch.object(manager, '_find_task_file', side_effect=mock_find_task_file):
            task_id = manager._generate_task_id()

        assert task_id == "TSK-0002"
        mock_config.set.assert_called_with("tasks.counter", 3)  # Should increment to 3
