"""Health check utilities for AI Trackdown PyTools."""

import importlib
import sys
from pathlib import Path
from typing import Any, Dict

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project


def check_health() -> Dict[str, Any]:
    """Check system health and dependencies."""
    checks = {}
    overall_status = True

    # Check Python version
    checks["python_version"] = _check_python_version()
    if not checks["python_version"]["status"]:
        overall_status = False

    # Check required dependencies
    checks["dependencies"] = _check_dependencies()
    if not checks["dependencies"]["status"]:
        overall_status = False

    # Check configuration
    checks["configuration"] = _check_configuration()
    if not checks["configuration"]["status"]:
        overall_status = False

    # Check Git availability
    checks["git"] = _check_git()
    # Git is optional, so don't fail overall health check

    return {"overall": overall_status, "checks": checks}


def check_project_health(project_path: Path) -> Dict[str, Any]:
    """Check project-specific health."""
    checks = {}
    overall_status = True

    # Check if project exists
    checks["project_exists"] = _check_project_exists(project_path)
    if not checks["project_exists"]["status"]:
        overall_status = False

    # Check project structure
    checks["project_structure"] = _check_project_structure(project_path)
    if not checks["project_structure"]["status"]:
        overall_status = False

    # Check configuration validity
    checks["config_valid"] = _check_config_validity(project_path)
    if not checks["config_valid"]["status"]:
        overall_status = False

    # Check task directory
    checks["tasks_directory"] = _check_tasks_directory(project_path)
    if not checks["tasks_directory"]["status"]:
        overall_status = False

    return {"overall": overall_status, "checks": checks}


def _check_python_version() -> Dict[str, Any]:
    """Check Python version compatibility."""
    min_version = (3, 8)
    current_version = sys.version_info[:2]

    if current_version >= min_version:
        return {
            "status": True,
            "message": f"Python {current_version[0]}.{current_version[1]} (compatible)",
        }
    else:
        return {
            "status": False,
            "message": f"Python {current_version[0]}.{current_version[1]} (requires >= {min_version[0]}.{min_version[1]})",
        }


def _check_dependencies() -> Dict[str, Any]:
    """Check required dependencies."""
    required_deps = [
        "typer",
        "rich",
        "pydantic",
        "yaml",  # pyyaml imports as 'yaml'
        "click",
        "jinja2",
        "jsonschema",
        "toml",
        "pathspec",
    ]

    missing_deps = []

    for dep in required_deps:
        try:
            importlib.import_module(dep)
        except ImportError:
            missing_deps.append(dep)

    if not missing_deps:
        return {"status": True, "message": "All required dependencies available"}
    else:
        return {
            "status": False,
            "message": f"Missing dependencies: {', '.join(missing_deps)}",
        }


def _check_configuration() -> Dict[str, Any]:
    """Check configuration validity."""
    try:
        config = Config.load()
        return {
            "status": True,
            "message": f"Configuration loaded from {config.config_path or 'defaults'}",
        }
    except Exception as e:
        return {"status": False, "message": f"Configuration error: {e}"}


def _check_git() -> Dict[str, Any]:
    """Check Git availability."""
    try:
        from ai_trackdown_pytools.utils.git import GIT_AVAILABLE, GitUtils

        if not GIT_AVAILABLE:
            return {
                "status": False,
                "message": "GitPython not available (install with: pip install GitPython)",
            }

        git_utils = GitUtils()
        if git_utils.is_git_repo():
            return {"status": True, "message": "Git repository detected"}
        else:
            return {
                "status": True,
                "message": "Git available (no repository in current directory)",
            }
    except Exception as e:
        return {"status": False, "message": f"Git check failed: {e}"}


def _check_project_exists(project_path: Path) -> Dict[str, Any]:
    """Check if AI Trackdown project exists."""
    if Project.exists(project_path):
        return {"status": True, "message": "AI Trackdown project found"}
    else:
        return {
            "status": False,
            "message": "No AI Trackdown project found (run 'aitrackdown init project')",
        }


def _check_project_structure(project_path: Path) -> Dict[str, Any]:
    """Check project directory structure."""
    required_dirs = [".ai-trackdown", "tasks"]

    missing_dirs = []
    for dir_name in required_dirs:
        if not (project_path / dir_name).exists():
            missing_dirs.append(dir_name)

    if not missing_dirs:
        return {"status": True, "message": "Project structure is valid"}
    else:
        return {
            "status": False,
            "message": f"Missing directories: {', '.join(missing_dirs)}",
        }


def _check_config_validity(project_path: Path) -> Dict[str, Any]:
    """Check project configuration validity."""
    config_file = project_path / ".ai-trackdown" / "config.yaml"

    if not config_file.exists():
        return {"status": False, "message": "Configuration file not found"}

    try:
        Config.load(config_file)
        return {"status": True, "message": "Configuration is valid"}
    except Exception as e:
        return {"status": False, "message": f"Configuration error: {e}"}


def _check_tasks_directory(project_path: Path) -> Dict[str, Any]:
    """Check tasks directory."""
    from ai_trackdown_pytools.core.config import Config

    config = Config.load(project_path=project_path)
    tasks_dir = project_path / config.get("tasks.directory", "tasks")

    if not tasks_dir.exists():
        return {"status": False, "message": "Tasks directory not found"}

    if not tasks_dir.is_dir():
        return {"status": False, "message": "Tasks path is not a directory"}

    return {
        "status": True,
        "message": f"Tasks directory found with {len(list(tasks_dir.rglob('*.md')))} task files",
    }
