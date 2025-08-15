"""System utilities for AI Trackdown PyTools."""

import platform
import sys
from pathlib import Path
from typing import Any, Dict

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project


def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    config = Config.load()
    project_root = Project.find_project_root()

    return {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "platform": platform.system(),
        "architecture": platform.machine(),
        "cwd": str(Path.cwd()),
        "git_repo": _check_git_repo(),
        "config_file": str(config.config_path) if config.config_path else "Not found",
        "templates_dir": str(_get_templates_dir()),
        "schema_dir": str(_get_schema_dir()),
        "project_root": str(project_root) if project_root else "Not found",
    }


def _check_git_repo() -> str:
    """Check if current directory is a git repository."""
    from ai_trackdown_pytools.utils.git import GitUtils

    git_utils = GitUtils()
    if git_utils.is_git_repo():
        return "Yes"
    return "No"


def _get_templates_dir() -> Path:
    """Get templates directory path."""
    config = Config.load()
    project_root = config.project_root

    if project_root:
        return project_root / ".ai-trackdown" / "templates"

    # Fallback to package templates
    return Path(__file__).parent.parent / "templates"


def _get_schema_dir() -> Path:
    """Get schema directory path."""
    config = Config.load()
    project_root = config.project_root

    if project_root:
        return project_root / ".ai-trackdown" / "schemas"

    # Fallback to package schemas
    return Path(__file__).parent.parent / "schemas"
