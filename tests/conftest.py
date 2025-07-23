"""Enhanced pytest configuration and fixtures."""

import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
import sys
from unittest.mock import Mock, patch

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from typer.testing import CliRunner

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.templates import TemplateManager
from ai_trackdown_pytools.utils.validation import SchemaValidator


# ===== BASIC FIXTURES =====


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


# ===== PROJECT FIXTURES =====


@pytest.fixture
def temp_project(temp_dir: Path) -> Generator[Project, None, None]:
    """Create a temporary AI Trackdown project for testing."""
    project_path = temp_dir / "test_project"
    project_path.mkdir()

    # Initialize project
    project = Project.create(project_path, name="Test Project")

    yield project


@pytest.fixture
def populated_project(temp_project: Project) -> Generator[Project, None, None]:
    """Create a project populated with sample data."""
    task_manager = TaskManager(temp_project)

    # Create sample tasks
    sample_tasks = [
        {
            "title": "High Priority Bug Fix",
            "description": "Critical bug that needs immediate attention",
            "priority": "critical",
            "status": "open",
            "assignees": ["alice"],
            "tags": ["bug", "critical", "urgent"],
        },
        {
            "title": "Feature Implementation",
            "description": "Implement new user dashboard",
            "priority": "medium",
            "status": "in_progress",
            "assignees": ["bob"],
            "tags": ["feature", "frontend"],
        },
        {
            "title": "Documentation Update",
            "description": "Update API documentation",
            "priority": "low",
            "status": "open",
            "assignees": ["charlie"],
            "tags": ["documentation", "api"],
        },
        {
            "title": "Completed Task",
            "description": "Previously completed work",
            "priority": "medium",
            "status": "completed",
            "assignees": ["diana"],
            "tags": ["enhancement", "completed"],
        },
    ]

    for task_data in sample_tasks:
        task_manager.create_task(task_data)

    yield temp_project


# ===== CONFIGURATION FIXTURES =====


@pytest.fixture
def mock_config(temp_dir: Path) -> Generator[Config, None, None]:
    """Create a mock configuration for testing."""
    config_path = temp_dir / ".ai-trackdown" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config = Config.create_default(config_path)
    config.set("project.name", "Test Project")
    config.set("project.description", "A project for testing")
    config.save()

    yield config


@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration singleton between tests."""
    if hasattr(Config, "_instance"):
        Config._instance = None
    yield
    if hasattr(Config, "_instance"):
        Config._instance = None


# ===== MANAGER FIXTURES =====


@pytest.fixture
def task_manager(temp_project: Project) -> TaskManager:
    """Create a TaskManager for testing."""
    return TaskManager(temp_project)


@pytest.fixture
def template_manager(temp_project: Project) -> TemplateManager:
    """Create a TemplateManager for testing."""
    return TemplateManager(temp_project.get_templates_directory())


@pytest.fixture
def schema_validator() -> SchemaValidator:
    """Create a SchemaValidator for testing."""
    return SchemaValidator()


# ===== TEST DATA FIXTURES =====


@pytest.fixture
def sample_task_data() -> Dict[str, Any]:
    """Sample task data for testing."""
    from datetime import datetime

    return {
        "id": "TSK-0001",
        "title": "Test Task",
        "description": "This is a test task for unit testing",
        "assignees": ["testuser"],
        "tags": ["test", "unit"],
        "priority": "medium",
        "status": "open",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_epic_data() -> Dict[str, Any]:
    """Sample epic data for testing."""
    from datetime import datetime, date, timedelta

    return {
        "id": "EP-0001",
        "title": "Test Epic",
        "description": "This is a test epic",
        "goal": "Test epic functionality",
        "business_value": "Enables testing",
        "success_criteria": "All tests pass",
        "status": "planning",
        "priority": "high",
        "target_date": date.today() + timedelta(days=30),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_issue_data() -> Dict[str, Any]:
    """Sample issue data for testing."""
    from datetime import datetime

    return {
        "id": "ISS-0001",
        "title": "Test Issue",
        "description": "This is a test issue",
        "issue_type": "bug",
        "severity": "medium",
        "status": "open",
        "priority": "high",
        "steps_to_reproduce": "1. Do this\n2. Do that",
        "expected_behavior": "Should work",
        "actual_behavior": "Doesn't work",
        "environment": "Test environment",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_pr_data() -> Dict[str, Any]:
    """Sample PR data for testing."""
    from datetime import datetime

    return {
        "id": "PR-0001",
        "title": "Test PR",
        "description": "This is a test PR",
        "pr_type": "feature",
        "status": "open",
        "priority": "medium",
        "source_branch": "feature/test",
        "target_branch": "main",
        "changes_summary": "Added test feature",
        "testing_notes": "Tested manually",
        "breaking_changes": False,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """Sample project data for testing."""
    from datetime import datetime, date, timedelta

    return {
        "id": "PROJ-0001",
        "name": "Test Project",
        "description": "A test project for unit testing",
        "status": "active",
        "priority": "high",
        "team_members": ["alice", "bob", "charlie"],
        "repository": "https://github.com/test/project",
        "start_date": date.today(),
        "target_completion": date.today() + timedelta(days=90),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }


# ===== MOCK FIXTURES =====


@pytest.fixture
def mock_git_repo():
    """Mock a Git repository."""
    with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo:
        mock_instance = Mock()
        mock_repo.return_value = mock_instance
        mock_instance.is_dirty.return_value = False
        mock_instance.active_branch.name = "main"
        mock_instance.heads = [Mock(name="main"), Mock(name="develop")]
        yield mock_instance


@pytest.fixture
def mock_editor():
    """Mock external editor."""
    with patch("ai_trackdown_pytools.utils.editor.launch_editor") as mock_launch:
        mock_launch.return_value = "Edited content"
        yield mock_launch


# ===== VALIDATION FIXTURES =====


@pytest.fixture
def validation_test_data():
    """Data for validation testing."""
    from datetime import datetime

    return {
        "valid_task": {
            "id": "TSK-0001",
            "title": "Valid Task",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        "invalid_task": {
            "id": "INVALID-001",
            "title": "Invalid Task",
            "status": "invalid_status",
            "priority": "invalid_priority",
        },
        "task_with_circular_dependency": {
            "id": "TSK-0002",
            "title": "Circular Task",
            "status": "open",
            "priority": "medium",
            "dependencies": ["TSK-0002"],  # Self-dependency
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
    }


# ===== PERFORMANCE FIXTURES =====


@pytest.fixture
def performance_data():
    """Generate data for performance testing."""
    from datetime import datetime, timedelta

    tasks = []
    for i in range(100):
        task = {
            "id": f"TSK-{i+1:04d}",
            "title": f"Performance Task {i+1}",
            "description": f"Task {i+1} for performance testing",
            "status": ["open", "in_progress", "completed"][i % 3],
            "priority": ["low", "medium", "high", "critical"][i % 4],
            "assignees": [f"user{(i % 5) + 1}"],
            "tags": [f"tag{(i % 10) + 1}", "performance"],
            "created_at": datetime.now() - timedelta(days=i),
            "updated_at": datetime.now() - timedelta(hours=i),
        }
        tasks.append(task)

    return {"tasks": tasks}


# ===== INTEGRATION TEST FIXTURES =====


@pytest.fixture
def integration_project_setup(temp_dir: Path):
    """Set up a complete project for integration testing."""
    project_path = temp_dir / "integration_project"
    project_path.mkdir()

    # Create project
    project = Project.create(project_path, name="Integration Test Project")

    # Set up managers
    task_manager = TaskManager(project)
    template_manager = TemplateManager(project.get_templates_directory())
    validator = SchemaValidator()

    # Create some initial data
    for i in range(5):
        task_data = {
            "title": f"Integration Task {i+1}",
            "priority": ["low", "medium", "high"][i % 3],
            "assignees": [f"user{i+1}"],
            "tags": ["integration", f"group{i % 2}"],
        }
        task_manager.create_task(task_data)

    return {
        "project": project,
        "task_manager": task_manager,
        "template_manager": template_manager,
        "validator": validator,
        "project_path": project_path,
    }


# ===== CLI TESTING FIXTURES =====


@pytest.fixture
def cli_project_context(temp_dir: Path):
    """Set up project context for CLI testing."""
    project_path = temp_dir / "cli_test_project"
    project_path.mkdir()

    # Create project
    project = Project.create(project_path, name="CLI Test Project")

    # Mock os.getcwd to return project path
    with patch("os.getcwd", return_value=str(project_path)):
        yield {
            "project": project,
            "project_path": project_path,
            "cwd_patch": patch("os.getcwd", return_value=str(project_path)),
        }


# ===== CLEANUP AND UTILITY FIXTURES =====


@pytest.fixture(autouse=True)
def ensure_cleanup():
    """Ensure proper cleanup after each test."""
    yield
    # Any global cleanup can go here


# ===== PARAMETRIZED FIXTURES =====


@pytest.fixture(params=["low", "medium", "high", "critical"])
def priority_values(request):
    """Parametrized fixture for testing all priority values."""
    return request.param


@pytest.fixture(params=["open", "in_progress", "blocked", "completed", "cancelled"])
def status_values(request):
    """Parametrized fixture for testing all status values."""
    return request.param


@pytest.fixture(params=["task", "epic", "issue", "pr", "project"])
def ticket_types(request):
    """Parametrized fixture for testing all ticket types."""
    return request.param


# ===== ERROR SIMULATION FIXTURES =====


@pytest.fixture
def file_system_errors():
    """Simulate file system errors."""
    return {
        "permission_error": PermissionError("Permission denied"),
        "file_not_found": FileNotFoundError("File not found"),
        "disk_full": OSError("No space left on device"),
    }


# ===== TEST MARKERS CONFIGURATION =====


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "slow: marks tests as slow running")
    config.addinivalue_line("markers", "performance: marks tests as performance tests")
    config.addinivalue_line("markers", "cli: marks tests as CLI tests")
    config.addinivalue_line("markers", "validation: marks tests as validation tests")


# ===== TEST COLLECTION HOOKS =====


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)

        # Add marker for CLI tests
        if "cli" in str(item.fspath) or "test_cli" in item.name:
            item.add_marker(pytest.mark.cli)

        # Add marker for validation tests
        if "validation" in str(item.fspath) or "validate" in item.name:
            item.add_marker(pytest.mark.validation)

        # Add marker for slow tests
        if hasattr(item, "fixturenames") and "performance_data" in item.fixturenames:
            item.add_marker(pytest.mark.slow)


# ===== CUSTOM ASSERTIONS =====


def assert_task_valid(task_data):
    """Custom assertion for task validity."""
    required_fields = ["id", "title", "status", "priority"]
    for field in required_fields:
        assert field in task_data, f"Task missing required field: {field}"

    valid_statuses = ["open", "in_progress", "blocked", "completed", "cancelled"]
    assert (
        task_data["status"] in valid_statuses
    ), f"Invalid status: {task_data['status']}"

    valid_priorities = ["low", "medium", "high", "critical"]
    assert (
        task_data["priority"] in valid_priorities
    ), f"Invalid priority: {task_data['priority']}"


def assert_file_has_frontmatter(file_path: Path):
    """Custom assertion for frontmatter presence."""
    content = file_path.read_text()
    assert content.startswith(
        "---"
    ), f"File {file_path} does not start with frontmatter"
    assert (
        content.count("---") >= 2
    ), f"File {file_path} does not have complete frontmatter"


# ===== PYTEST PLUGINS =====

pytest_plugins = [
    "pytest_mock",  # For mocking
    "pytest_cov",  # For coverage
]


# ===== GLOBAL TEST CONFIGURATION =====


# Increase timeout for slow tests
@pytest.fixture(autouse=True)
def increase_timeout():
    """Increase timeout for tests that might be slow."""
    # This would be used if we had timeout-sensitive tests
    pass
