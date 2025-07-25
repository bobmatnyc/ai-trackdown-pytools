"""AI Trackdown PyTools - Python CLI tools for AI project tracking and task management."""

import os
from pathlib import Path


# Read version from VERSION file
def _get_version():
    """Read version from VERSION file."""
    # Try to find VERSION file in several locations
    possible_paths = [
        Path(__file__).parent / "VERSION",  # Packaged install (primary)
        Path(__file__).parent.parent.parent / "VERSION",  # Development install
        Path(os.getcwd()) / "VERSION",  # Current directory
    ]

    for version_path in possible_paths:
        if version_path.exists():
            return version_path.read_text().strip()

    # Fallback version if VERSION file not found
    return "1.2.0"


__version__ = _get_version()
__author__ = "AI Trackdown Team"
__email__ = "dev@ai-trackdown.com"

from .core.config import Config
from .core.project import Project
from .core.task import Task
from .version import get_version, get_version_info, format_version_info, Version

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
