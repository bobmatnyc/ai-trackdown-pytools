"""Task management for AI Trackdown PyTools."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml
from pydantic import BaseModel, ConfigDict, field_serializer

from ai_trackdown_pytools.core.config import Config
# from ai_trackdown_pytools.core.models import TaskModel as NewTaskModel, get_model_for_type
# from ai_trackdown_pytools.utils.validation import SchemaValidator, ValidationResult


class TaskError(Exception):
    """Exception raised for task-related errors."""
    pass


class TaskModel(BaseModel):
    """Task data model."""
    
    id: str
    title: str
    description: str = ""
    status: str = "open"
    priority: str = "medium"
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
    
    @field_serializer('created_at', 'updated_at', 'due_date')
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None


class Task:
    """Task representation."""
    
    def __init__(self, data: TaskModel, file_path: Path):
        """Initialize task."""
        self.data = data
        self.file_path = file_path
    
    @classmethod
    def load(cls, file_path: Path) -> 'Task':
        """Load task from file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract frontmatter
            frontmatter = cls._extract_frontmatter(content)
            if not frontmatter:
                raise TaskError(f"Failed to parse task file: {file_path}")
            
            # Convert datetime strings back to datetime objects if needed
            if 'created_at' in frontmatter:
                if isinstance(frontmatter['created_at'], str):
                    frontmatter['created_at'] = datetime.fromisoformat(frontmatter['created_at'])
            if 'updated_at' in frontmatter:
                if isinstance(frontmatter['updated_at'], str):
                    frontmatter['updated_at'] = datetime.fromisoformat(frontmatter['updated_at'])
            if 'due_date' in frontmatter and frontmatter['due_date']:
                if isinstance(frontmatter['due_date'], str):
                    frontmatter['due_date'] = datetime.fromisoformat(frontmatter['due_date'])
            
            task_data = TaskModel(**frontmatter)
            return cls(task_data, file_path)
            
        except Exception as e:
            raise TaskError(f"Failed to parse task file: {e}")
    
    @staticmethod
    def _extract_frontmatter(content: str) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from markdown content."""
        import re
        # Match frontmatter pattern
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            return None
        
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None
    
    @property
    def id(self) -> str:
        """Get task ID."""
        return self.data.id
    
    @property
    def title(self) -> str:
        """Get task title."""
        return self.data.title
    
    @property
    def description(self) -> str:
        """Get task description."""
        return self.data.description
    
    @property
    def status(self) -> str:
        """Get task status."""
        return self.data.status
    
    @property
    def priority(self) -> str:
        """Get task priority."""
        return self.data.priority
    
    @property
    def assignees(self) -> List[str]:
        """Get task assignees."""
        return self.data.assignees
    
    @property
    def tags(self) -> List[str]:
        """Get task tags."""
        return self.data.tags
    
    @property
    def created_at(self) -> datetime:
        """Get task creation time."""
        return self.data.created_at
    
    @property
    def updated_at(self) -> datetime:
        """Get task last update time."""
        return self.data.updated_at
    
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
        self.tasks_dir = self.project_path / "tasks"
        self.config = Config.load()
        
        # Ensure tasks directory exists
        self.tasks_dir.mkdir(exist_ok=True)
    
    def create_task(self, **kwargs) -> Task:
        """Create a new task."""
        now = datetime.now()
        
        # Generate task ID
        task_id = self._generate_task_id()
        
        # Create task data
        task_data = TaskModel(
            id=task_id,
            title=kwargs.get('title', 'Untitled Task'),
            description=kwargs.get('description', ''),
            status=kwargs.get('status', 'open'),
            priority=kwargs.get('priority', 'medium'),
            assignees=kwargs.get('assignees', []),
            tags=kwargs.get('tags', []),
            created_at=now,
            updated_at=now,
            due_date=kwargs.get('due_date'),
            estimated_hours=kwargs.get('estimated_hours'),
            actual_hours=kwargs.get('actual_hours'),
            dependencies=kwargs.get('dependencies', []),
            parent=kwargs.get('parent'),
            labels=kwargs.get('labels', []),
            metadata=kwargs.get('metadata', {})
        )
        
        # Create task file
        task_file = self._get_task_file_path(task_id)
        self._save_task_file(task_data, task_file)
        
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
    
    def list_tasks(self, status: Optional[str] = None, tag: Optional[str] = None) -> List[Task]:
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
        return True
    
    def delete_task(self, task_id: str) -> bool:
        """Delete task by ID."""
        task_file = self._find_task_file(task_id)
        if not task_file:
            return False
        
        task_file.unlink()
        return True
    
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        id_format = self.config.get("tasks.id_format", "TSK-{counter:04d}")
        
        # Get counter from config or calculate from existing tasks
        counter = self.config.get("tasks.counter", 1)
        
        # Ensure ID is unique
        while True:
            task_id = id_format.format(counter=counter)
            if not self._find_task_file(task_id):
                break
            counter += 1
        
        # Update counter in config
        self.config.set("tasks.counter", counter + 1)
        self.config.save()
        
        return task_id
    
    def _get_task_file_path(self, task_id: str) -> Path:
        """Get task file path for task ID."""
        # Create subdirectory based on task ID prefix
        prefix = task_id.split('-')[0] if '-' in task_id else 'misc'
        subdir = self.tasks_dir / prefix.lower()
        subdir.mkdir(exist_ok=True)
        
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
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract frontmatter
            frontmatter = self._extract_frontmatter(content)
            if not frontmatter:
                return None
            
            # Convert datetime strings back to datetime objects if needed
            if 'created_at' in frontmatter:
                if isinstance(frontmatter['created_at'], str):
                    frontmatter['created_at'] = datetime.fromisoformat(frontmatter['created_at'])
            if 'updated_at' in frontmatter:
                if isinstance(frontmatter['updated_at'], str):
                    frontmatter['updated_at'] = datetime.fromisoformat(frontmatter['updated_at'])
            if 'due_date' in frontmatter and frontmatter['due_date']:
                if isinstance(frontmatter['due_date'], str):
                    frontmatter['due_date'] = datetime.fromisoformat(frontmatter['due_date'])
            
            return TaskModel(**frontmatter)
            
        except Exception:
            return None
    
    def _save_task_file(self, task_data: TaskModel, file_path: Path) -> None:
        """Save task data to file."""
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create frontmatter - convert datetime objects to ISO strings
        frontmatter = task_data.dict()
        frontmatter['created_at'] = frontmatter['created_at'].isoformat()
        frontmatter['updated_at'] = frontmatter['updated_at'].isoformat()
        if frontmatter.get('due_date'):
            frontmatter['due_date'] = frontmatter['due_date'].isoformat()
        
        # Generate markdown content
        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

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
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _extract_frontmatter(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract YAML frontmatter from markdown content."""
        # Match frontmatter pattern
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)
        
        if not match:
            return None
        
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None