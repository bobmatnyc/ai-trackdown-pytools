"""Task management for AI Trackdown PyTools."""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, field_serializer

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.constants import (
    DEFAULT_PRIORITY,
    DEFAULT_STATUS,
    DEFAULT_TICKET_TYPE,
    PREFIX_TO_SUBDIR,
    TYPE_TO_PREFIX,
    TicketPrefix,
    TicketPriority,
    TicketStatus,
    TicketSubdir,
    TicketType,
)
from ai_trackdown_pytools.core.exceptions import TaskError
from ai_trackdown_pytools.utils.index import update_index_on_file_change

# from ai_trackdown_pytools.core.models import TaskModel as NewTaskModel, get_model_for_type
# from ai_trackdown_pytools.utils.validation import SchemaValidator, ValidationResult




class TaskModel(BaseModel):
    """Task data model."""

    id: str
    title: str
    description: str = ""
    status: str = "open"
    priority: str = DEFAULT_PRIORITY.value
    assignees: List[str] = []
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    dependencies: List[str] = []
    parent: Optional[str] = None
    labels: List[str] = []
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict()

    @field_serializer("created_at", "updated_at", "due_date")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class Task:
    """Task representation."""

    def __init__(self, data: TaskModel, file_path: Path):
        """Initialize task."""
        self.data = data
        self.file_path = file_path

    @property
    def model(self) -> TaskModel:
        """Get task model - backward compatibility alias for data."""
        return self.data

    # Proxy properties to make Task objects work like they have direct attributes
    @property
    def id(self) -> str:
        return self.data.id

    @property
    def title(self) -> str:
        return self.data.title

    @property
    def description(self) -> str:
        return self.data.description

    @property
    def status(self) -> str:
        return self.data.status

    @property
    def priority(self) -> str:
        return self.data.priority

    @property
    def assignees(self) -> List[str]:
        return self.data.assignees

    @property
    def tags(self) -> List[str]:
        return self.data.tags

    @property
    def created_at(self) -> datetime:
        return self.data.created_at

    @property
    def updated_at(self) -> datetime:
        return self.data.updated_at

    @property
    def due_date(self) -> Optional[datetime]:
        return self.data.due_date

    @property
    def parent(self) -> Optional[str]:
        return self.data.parent

    @property
    def estimated_hours(self) -> Optional[float]:
        return self.data.estimated_hours

    @property
    def actual_hours(self) -> Optional[float]:
        return self.data.actual_hours

    @property
    def dependencies(self) -> List[str]:
        return self.data.dependencies

    @property
    def metadata(self) -> Dict[str, Any]:
        return self.data.metadata

    @classmethod
    def from_dict(cls, data: Dict[str, Any], file_path: Path) -> "Task":
        """Create task from dictionary."""
        task_model = TaskModel(**data)
        return cls(task_model, file_path)

    @classmethod
    def load(cls, file_path: Path) -> "Task":
        """Load task from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter
            frontmatter = cls._extract_frontmatter(content)
            if not frontmatter:
                raise TaskError(f"Failed to parse task file: {file_path}")

            # Convert datetime strings back to datetime objects if needed
            if "created_at" in frontmatter:
                if isinstance(frontmatter["created_at"], str):
                    frontmatter["created_at"] = datetime.fromisoformat(
                        frontmatter["created_at"]
                    )
            if "updated_at" in frontmatter:
                if isinstance(frontmatter["updated_at"], str):
                    frontmatter["updated_at"] = datetime.fromisoformat(
                        frontmatter["updated_at"]
                    )
            if "due_date" in frontmatter and frontmatter["due_date"]:
                if isinstance(frontmatter["due_date"], str):
                    frontmatter["due_date"] = datetime.fromisoformat(
                        frontmatter["due_date"]
                    )

            task_data = TaskModel(**frontmatter)
            return cls(task_data, file_path)

        except Exception as e:
            raise TaskError(f"Failed to parse task file: {e}")

    @staticmethod
    def _extract_frontmatter(content: str) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from markdown content."""
        import re

        # Match frontmatter pattern
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None

        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None

    @parent.setter
    def parent(self, value: Optional[str]) -> None:
        """Set task parent."""
        self.data.parent = value

    def update(self, **kwargs) -> None:
        """Update task data."""
        for key, value in kwargs.items():
            if hasattr(self.data, key):
                setattr(self.data, key, value)

        self.data.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return self.data.dict()


class TaskManager:
    """Task manager for AI Trackdown projects."""

    def __init__(self, project_path: Path):
        """Initialize task manager."""
        self.project_path = Path(project_path)
        self.config = Config.load(project_path=self.project_path)
        self.tasks_dir = self.project_path / self.config.get("tasks.directory", "tickets")

        # Ensure tasks directory exists
        self.tasks_dir.mkdir(exist_ok=True)

    def create_task(self, **kwargs) -> Task:
        """Create a new task."""
        now = datetime.now()

        # Determine type (default to task)
        task_type = kwargs.get("type", DEFAULT_TICKET_TYPE.value)

        # Generate task ID based on type
        task_id = self._generate_task_id(task_type)

        # Create task data
        task_data = TaskModel(
            id=task_id,
            title=kwargs.get("title", f"Untitled {task_type.title()}"),
            description=kwargs.get("description", ""),
            status=kwargs.get("status", DEFAULT_STATUS.value),
            priority=kwargs.get("priority", DEFAULT_PRIORITY.value),
            assignees=kwargs.get("assignees", []),
            tags=kwargs.get("tags", []),
            created_at=now,
            updated_at=now,
            due_date=kwargs.get("due_date"),
            estimated_hours=kwargs.get("estimated_hours"),
            actual_hours=kwargs.get("actual_hours"),
            dependencies=kwargs.get("dependencies", []),
            parent=kwargs.get("parent"),
            labels=kwargs.get("labels", []),
            metadata=kwargs.get("metadata", {}),
        )

        # Create task file
        task_file = self._get_task_file_path(task_id)
        self._save_task_file(task_data, task_file)

        # Update index
        update_index_on_file_change(self.project_path, task_file)

        return Task(task_data, task_file)

    def load_task(self, task_id: str) -> Task:
        """Load task by ID."""
        task_file = self._find_task_file(task_id)
        if not task_file:
            raise TaskError(f"Task not found: {task_id}")

        task_data = self._load_task_file(task_file)
        if not task_data:
            raise TaskError(f"Failed to parse task file: {task_file}")

        return Task(task_data, task_file)

    def list_tasks(
        self, status: Optional[str] = None, tag: Optional[str] = None
    ) -> List[Task]:
        """List all tasks with optional filtering."""
        tasks = []

        for task_file in self.tasks_dir.rglob("*.md"):
            task_data = self._load_task_file(task_file)
            if task_data:
                # Apply filters
                if status and task_data.status != status:
                    continue
                if tag and tag not in task_data.tags:
                    continue

                tasks.append(Task(task_data, task_file))

        # Sort by creation date (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks

    def get_recent_tasks(self, limit: int = 5) -> List[Task]:
        """Get recently updated tasks."""
        tasks = self.list_tasks()
        tasks.sort(key=lambda t: t.updated_at, reverse=True)
        return tasks[:limit]

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update task by ID."""
        task = self.load_task(task_id)
        if not task:
            return False

        task.update(**kwargs)
        self._save_task_file(task.data, task.file_path)

        # Update index
        update_index_on_file_change(self.project_path, task.file_path)

        return True

    def delete_task(self, task_id: str) -> bool:
        """Delete task by ID."""
        task_file = self._find_task_file(task_id)
        if not task_file:
            return False

        task_file.unlink()
        return True

    def save_task(self, task: Task) -> None:
        """Save task to file."""
        self._save_task_file(task.data, task.file_path)

        # Update index
        update_index_on_file_change(self.project_path, task.file_path)

    def _generate_task_id(self, task_type: str = None) -> str:
        """Generate unique task ID based on type."""
        if task_type is None:
            task_type = DEFAULT_TICKET_TYPE.value
            
        # Determine prefix and counter key based on type
        type_config = {
            TicketType.EPIC.value: {"prefix": TicketPrefix.EPIC.value, "counter_key": "epics.counter"},
            TicketType.ISSUE.value: {"prefix": TicketPrefix.ISSUE.value, "counter_key": "issues.counter"},
            TicketType.TASK.value: {"prefix": TicketPrefix.TASK.value, "counter_key": "tasks.counter"},
            TicketType.PR.value: {"prefix": TicketPrefix.PR.value, "counter_key": "prs.counter"},
        }

        config = type_config.get(task_type, type_config[TicketType.TASK.value])
        prefix = config["prefix"]
        counter_key = config["counter_key"]

        # Get counter from config
        counter = self.config.get(counter_key, 1)

        # Ensure ID is unique
        while True:
            task_id = f"{prefix}-{counter:04d}"
            if not self._find_task_file(task_id):
                break
            counter += 1

        # Update counter in config
        self.config.set(counter_key, counter + 1)
        self.config.save()

        return task_id

    def _get_task_file_path(self, task_id: str, title: Optional[str] = None) -> Path:
        """Get task file path for task ID."""
        # Determine directory based on prefix
        prefix = task_id.split("-")[0] if "-" in task_id else None

        # Get subdirectory from mapping or use misc
        subdir_name = TicketSubdir.MISC
        for ticket_prefix, ticket_subdir in PREFIX_TO_SUBDIR.items():
            if prefix == ticket_prefix.value:
                subdir_name = ticket_subdir
                break

        subdir = self.tasks_dir / subdir_name.value
        subdir.mkdir(exist_ok=True)

        # Use just the ID for the filename to avoid issues with special characters
        return subdir / f"{task_id}.md"

    def _find_task_file(self, task_id: str) -> Optional[Path]:
        """Find task file by ID."""
        for task_file in self.tasks_dir.rglob("*.md"):
            if task_file.stem == task_id:
                return task_file
        return None

    def _load_task_file(self, file_path: Path) -> Optional[TaskModel]:
        """Load task data from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter
            frontmatter = self._extract_frontmatter(content)
            if not frontmatter:
                return None

            # Convert datetime strings back to datetime objects if needed
            if "created_at" in frontmatter:
                if isinstance(frontmatter["created_at"], str):
                    frontmatter["created_at"] = datetime.fromisoformat(
                        frontmatter["created_at"]
                    )
            if "updated_at" in frontmatter:
                if isinstance(frontmatter["updated_at"], str):
                    frontmatter["updated_at"] = datetime.fromisoformat(
                        frontmatter["updated_at"]
                    )
            if "due_date" in frontmatter and frontmatter["due_date"]:
                if isinstance(frontmatter["due_date"], str):
                    frontmatter["due_date"] = datetime.fromisoformat(
                        frontmatter["due_date"]
                    )

            return TaskModel(**frontmatter)

        except Exception:
            return None

    def _save_task_file(self, task_data: TaskModel, file_path: Path) -> None:
        """Save task data to file."""
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create frontmatter - dict() already converts datetime objects to ISO strings
        frontmatter = task_data.dict()

        # Generate markdown content
        # The yaml.dump function will handle escaping automatically, no need to pre-escape

        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)}---

# {task_data.title}

## Description
{task_data.description or "No description provided."}

## Details
- **Status**: {task_data.status}
- **Priority**: {task_data.priority}
- **Assignees**: {', '.join(task_data.assignees) if task_data.assignees else 'None'}
- **Tags**: {', '.join(task_data.tags) if task_data.tags else 'None'}
- **Created**: {task_data.created_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Updated**: {task_data.updated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Tasks
- [ ] Add task items here

## Notes
_Add any additional notes or context here._
"""

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def _extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from markdown content."""
        # Match frontmatter pattern
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None

        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None
