"""Configuration management for AI Trackdown PyTools."""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict


class ConfigModel(BaseModel):
    """Configuration data model."""

    version: str = "1.0.0"
    project: Dict[str, Any] = {}
    editor: Dict[str, Any] = {"default": "code"}
    templates: Dict[str, Any] = {"directory": "templates"}
    tasks: Dict[str, Any] = {"directory": "tickets"}
    git: Dict[str, Any] = {"auto_commit": False}
    plugins: Dict[str, Any] = {}

    model_config = ConfigDict(extra="allow")


class Config:
    """Configuration manager for AI Trackdown PyTools."""

    _instances: Dict[Path, "Config"] = {}
    _config: ConfigModel
    _config_path: Optional[Path] = None
    _loaded_at: Optional[float] = None

    def __new__(cls, project_path: Optional[Path] = None) -> "Config":
        """Project-specific configuration instances."""
        # Get the project root for this config
        if project_path is None:
            project_path = Path.cwd()

        # Look for project root from the given path
        from ai_trackdown_pytools.core.project import Project

        actual_project_root = Project.find_project_root(project_path)
        if actual_project_root:
            project_path = actual_project_root

        # Use project-specific instance
        if project_path not in cls._instances:
            instance = super().__new__(cls)
            instance._config = ConfigModel()
            instance._config_path = None
            instance._loaded_at = None
            cls._instances[project_path] = instance

        return cls._instances[project_path]

    @classmethod
    def load(
        cls, config_path: Optional[Path] = None, project_path: Optional[Path] = None
    ) -> "Config":
        """Load configuration from file."""
        instance = cls(project_path)

        # Convert string to Path if needed
        if config_path is not None and not isinstance(config_path, Path):
            config_path = Path(config_path)

        if config_path is None:
            # Try to find config file
            config_path = cls.find_config_file()

        if config_path and config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}

            instance._config = ConfigModel(**config_data)
            instance._config_path = config_path
            instance._loaded_at = config_path.stat().st_mtime

        return instance

    @classmethod
    def create_default(cls, config_path: Path) -> "Config":
        """Create default configuration file."""
        # Get project path from config path
        project_path = (
            config_path.parent.parent
            if config_path.parent.name == ".ai-trackdown"
            else None
        )
        instance = cls(project_path)

        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Create default configuration
        # Get project name from path
        project_name = "my-project"
        if config_path.parent.parent.exists():
            project_name = config_path.parent.parent.name

        default_config = {
            "version": "0.9.0",
            "project": {"name": project_name, "description": "", "version": "0.9.0"},
            "editor": {"default": os.getenv("EDITOR", "code")},
            "templates": {"directory": "templates"},
            "tasks": {
                "directory": "tickets",
                "auto_id": True,
                "id_format": "TSK-{counter:04d}",
            },
            "git": {"auto_commit": False, "commit_prefix": "[ai-trackdown]"},
            "plugins": {},
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        instance._config = ConfigModel(**default_config)
        instance._config_path = config_path
        instance._loaded_at = config_path.stat().st_mtime

        return instance

    @staticmethod
    def find_config_file() -> Optional[Path]:
        """Find configuration file in project hierarchy."""
        current_path = Path.cwd()

        # Look for .ai-trackdown/config.yaml
        for path in [current_path] + list(current_path.parents):
            config_file = path / ".ai-trackdown" / "config.yaml"
            if config_file.exists():
                return config_file

        # Look for global config
        global_config = Config.get_global_config_path()
        if global_config.exists():
            return global_config

        return None

    @staticmethod
    def get_global_config_path() -> Path:
        """Get global configuration file path."""
        return Path.home() / ".ai-trackdown" / "config.yaml"

    def __getattr__(self, name: str) -> Any:
        """Provide attribute access to config values."""
        if name.startswith("_"):
            # Don't intercept private attributes
            raise AttributeError(f"'Config' object has no attribute '{name}'")

        # Check if the attribute exists on the ConfigModel
        if hasattr(self._config, name):
            return getattr(self._config, name)

        raise AttributeError(f"'Config' object has no attribute '{name}'")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split(".")
        value = self._config.model_dump()

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split(".")
        config_dict = self._config.model_dump()
        target = config_dict

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value
        self._config = ConfigModel(**config_dict)

    def save(self) -> None:
        """Save configuration to file."""
        if self._config_path:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config.model_dump(),
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return self._config.model_dump()

    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        # Merge with existing config
        current = self._config.model_dump()
        current.update(data)
        self._config = ConfigModel(**current)

    @property
    def config_path(self) -> Optional[Path]:
        """Get configuration file path."""
        return self._config_path

    @property
    def project_root(self) -> Optional[Path]:
        """Get project root directory."""
        if self._config_path:
            # Assume project root is parent of .ai-trackdown directory
            return self._config_path.parent.parent
        return None

    def is_stale(self) -> bool:
        """Check if the config file has been modified since it was loaded."""
        if not self._config_path or not self._config_path.exists():
            return False

        if self._loaded_at is None:
            return True

        current_mtime = self._config_path.stat().st_mtime
        return current_mtime > self._loaded_at

    @classmethod
    def reload(cls, project_path: Optional[Path] = None) -> "Config":
        """Reload configuration by removing cached instance and creating a fresh one."""
        if project_path is None:
            project_path = Path.cwd()

        # Look for project root from the given path
        from ai_trackdown_pytools.core.project import Project

        actual_project_root = Project.find_project_root(project_path)
        if actual_project_root:
            project_path = actual_project_root

        # Get the config path from the existing instance if available
        config_path = None
        if project_path in cls._instances:
            config_path = cls._instances[project_path]._config_path
            del cls._instances[project_path]

        # Load and return a fresh instance
        return cls.load(config_path=config_path, project_path=project_path)

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached configuration instances."""
        cls._instances.clear()



