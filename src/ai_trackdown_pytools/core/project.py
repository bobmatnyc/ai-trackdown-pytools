"""Project management for AI Trackdown PyTools."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict, field_serializer

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.exceptions import ProjectError


class ProjectModel(BaseModel):
    """Project data model."""

    name: str
    description: Optional[str] = None
    version: str = "1.0.0"
    author: Optional[str] = None
    license: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict()

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()


class Project:
    """Project manager for AI Trackdown PyTools."""

    def __init__(self, path: Path, data: ProjectModel):
        """Initialize project."""
        self.path = path
        self.data = data

    @classmethod
    def create(cls, path: Path, **kwargs) -> "Project":
        """Create a new AI Trackdown project."""
        path = Path(path)

        # Check if project already exists
        if cls.exists(path):
            raise ProjectError(f"Directory {path} is already an AI Trackdown project")

        # Create project structure
        cls._create_structure(path)

        # Create project metadata
        now = datetime.now()
        project_data = ProjectModel(
            name=kwargs.get("name", path.name),
            description=kwargs.get("description"),
            version=kwargs.get("version", "1.0.0"),
            author=kwargs.get("author"),
            license=kwargs.get("license"),
            created_at=now,
            updated_at=now,
            metadata=kwargs.get("metadata", {}),
        )

        # Save project file
        project_file = path / ".ai-trackdown" / "project.yaml"
        try:
            with open(project_file, "w", encoding="utf-8") as f:
                # The .dict() method already converts datetime to ISO strings via field_serializer
                data_dict = project_data.model_dump()
                yaml.dump(data_dict, f, default_flow_style=False)
        except Exception as e:
            raise ProjectError(f"Failed to create project configuration: {e}") from e

        # Create default configuration
        config_file = path / ".ai-trackdown" / "config.yaml"
        try:
            Config.create_default(config_file)
        except Exception as e:
            raise ProjectError(f"Failed to create project configuration: {e}") from e

        return cls(path, project_data)

    @classmethod
    def load(cls, path: Path) -> "Project":
        """Load existing AI Trackdown project."""
        path = Path(path)
        project_file = path / ".ai-trackdown" / "project.yaml"

        if not project_file.exists():
            raise ProjectError(f"No project file found at {project_file}")

        with open(project_file, encoding="utf-8") as f:
            project_data = yaml.safe_load(f)

        # Handle empty or invalid project file
        if project_data is None:
            raise ProjectError(f"Project file is empty or invalid at {project_file}")

        # Convert datetime strings back to datetime objects if needed
        if "created_at" in project_data:
            if isinstance(project_data["created_at"], str):
                project_data["created_at"] = datetime.fromisoformat(
                    project_data["created_at"]
                )
            # If it's already a datetime object, keep it as is
        if "updated_at" in project_data:
            if isinstance(project_data["updated_at"], str):
                project_data["updated_at"] = datetime.fromisoformat(
                    project_data["updated_at"]
                )
            # If it's already a datetime object, keep it as is

        return cls(path, ProjectModel(**project_data))

    @classmethod
    def exists(cls, path: Path) -> bool:
        """Check if AI Trackdown project exists at path."""
        path = Path(path)
        return (path / ".ai-trackdown" / "project.yaml").exists()

    @classmethod
    def find_project_root(cls, start_path: Optional[Path] = None) -> Optional[Path]:
        """Find project root by looking for .ai-trackdown directory."""
        if start_path is None:
            start_path = Path.cwd()

        current_path = Path(start_path)

        for path in [current_path] + list(current_path.parents):
            if cls.exists(path):
                return path

        return None

    @staticmethod
    def _create_structure(path: Path) -> None:
        """Create project directory structure."""
        path = Path(path)

        # Create main directories
        directories = [
            ".ai-trackdown",
            ".ai-trackdown/templates",
            ".ai-trackdown/schemas",
            "tickets",
            "docs",
        ]

        for directory in directories:
            (path / directory).mkdir(parents=True, exist_ok=True)

        # Create initial files
        gitignore_content = """# AI Trackdown
.ai-trackdown/cache/
.ai-trackdown/logs/
*.tmp

# Common ignores
.DS_Store
.vscode/
.idea/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/
dist/
build/
*.egg-info/
"""

        gitignore_path = path / ".gitignore"
        if not gitignore_path.exists():
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write(gitignore_content)

        # Create README if it doesn't exist
        readme_path = path / "README.md"
        if not readme_path.exists():
            readme_content = f"""# {path.name}

AI Trackdown project for task and project management.

## Getting Started

1. Check project status: `aitrackdown status project`
2. Create your first task: `aitrackdown create task`
3. List available templates: `aitrackdown template list`

## Project Structure

- `tickets/` - Ticket files and documentation
- `docs/` - Project documentation
- `.ai-trackdown/` - Configuration and templates

## Commands

- `aitrackdown init` - Initialize project
- `aitrackdown status` - Show project status
- `aitrackdown create` - Create tasks, issues, epics
- `aitrackdown template` - Manage templates

For more information, run `aitrackdown --help`.
"""
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)

    def save(self) -> None:
        """Save project metadata."""
        self.data.updated_at = datetime.now()

        project_file = self.path / ".ai-trackdown" / "project.yaml"
        with open(project_file, "w", encoding="utf-8") as f:
            # The .dict() method already converts datetime to ISO strings via field_serializer
            data_dict = self.data.dict()
            yaml.dump(data_dict, f, default_flow_style=False)

    def update(self, **kwargs) -> None:
        """Update project metadata."""
        for key, value in kwargs.items():
            if hasattr(self.data, key):
                setattr(self.data, key, value)

        self.save()

    @property
    def name(self) -> str:
        """Get project name."""
        return self.data.name

    @property
    def description(self) -> Optional[str]:
        """Get project description."""
        return self.data.description

    @property
    def version(self) -> str:
        """Get project version."""
        return self.data.version

    @property
    def created_at(self) -> datetime:
        """Get project creation time."""
        return self.data.created_at

    @property
    def updated_at(self) -> datetime:
        """Get project last update time."""
        return self.data.updated_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert project to dictionary."""
        return self.data.dict()
