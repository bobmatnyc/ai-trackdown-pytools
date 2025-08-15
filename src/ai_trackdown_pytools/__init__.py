"""AI Trackdown PyTools - Python CLI tools for AI project tracking and task management."""

from .core.config import Config
from .core.project import Project
from .core.task import Task
from .version import (
    Version,
    __version__,
    format_version_info,
    get_version,
    get_version_info,
)

__author__ = "AI Trackdown Team"
__email__ = "dev@ai-trackdown.com"

__all__ = [
    "Config",
    "Project",
    "Task",
    "__version__",
    "get_version",
    "get_version_info",
    "format_version_info",
    "Version",
]
