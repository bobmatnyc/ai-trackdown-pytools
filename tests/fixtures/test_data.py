"""Test data fixtures and mock data generators."""

import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import pytest

from ai_trackdown_pytools.core.models import TaskModel
from ai_trackdown_pytools.core.project import Project


class TestDataGenerator:
    """Generate test data for various scenarios."""

    @staticmethod
    def generate_task_data(
        task_id: Optional[str] = None, title: Optional[str] = None, **overrides
    ) -> Dict[str, Any]:
        """Generate realistic task data."""
        base_data = {
            "id": task_id or "TSK-0001",
            "title": title or "Sample Task",
            "description": "This is a sample task for testing purposes",
            "status": "open",
            "priority": "medium",
            "assignees": ["developer"],
            "tags": ["test", "sample"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        base_data.update(overrides)
        return base_data

    @staticmethod
    def generate_epic_data(
        epic_id: Optional[str] = None, title: Optional[str] = None, **overrides
    ) -> Dict[str, Any]:
        """Generate realistic epic data."""
        base_data = {
            "id": epic_id or "EP-0001",
            "title": title or "Sample Epic",
            "description": "This is a sample epic for testing purposes",
            "goal": "Achieve testing objective",
            "business_value": "Provides testing capability",
            "success_criteria": "All tests pass",
            "status": "planning",
            "priority": "high",
            "target_date": date.today() + timedelta(days=30),
            "child_issues": [],
            "child_tasks": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        base_data.update(overrides)
        return base_data

    @staticmethod
    def generate_issue_data(
        issue_id: Optional[str] = None, title: Optional[str] = None, **overrides
    ) -> Dict[str, Any]:
        """Generate realistic issue data."""
        base_data = {
            "id": issue_id or "ISS-0001",
            "title": title or "Sample Issue",
            "description": "This is a sample issue for testing purposes",
            "issue_type": "bug",
            "severity": "medium",
            "status": "open",
            "priority": "high",
            "steps_to_reproduce": "1. Do this\n2. Do that\n3. See error",
            "expected_behavior": "Should work correctly",
            "actual_behavior": "Throws an error",
            "environment": "Testing environment",
            "assignees": ["developer"],
            "tags": ["bug", "test"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        base_data.update(overrides)
        return base_data

    @staticmethod
    def generate_pr_data(
        pr_id: Optional[str] = None, title: Optional[str] = None, **overrides
    ) -> Dict[str, Any]:
        """Generate realistic PR data."""
        base_data = {
            "id": pr_id or "PR-0001",
            "title": title or "Sample Pull Request",
            "description": "This is a sample PR for testing purposes",
            "pr_type": "feature",
            "status": "open",
            "priority": "medium",
            "source_branch": "feature/sample",
            "target_branch": "main",
            "changes_summary": "Added new feature",
            "testing_notes": "Tested with unit tests",
            "breaking_changes": False,
            "related_issues": [],
            "assignees": ["developer"],
            "tags": ["feature", "test"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        base_data.update(overrides)
        return base_data

    @staticmethod
    def generate_project_data(
        project_id: Optional[str] = None, name: Optional[str] = None, **overrides
    ) -> Dict[str, Any]:
        """Generate realistic project data."""
        base_data = {
            "id": project_id or "PROJ-0001",
            "name": name or "Sample Project",
            "description": "This is a sample project for testing purposes",
            "status": "active",
            "priority": "high",
            "team_members": ["alice", "bob", "charlie"],
            "repository": "https://github.com/example/sample-project",
            "start_date": date.today(),
            "target_completion": date.today() + timedelta(days=90),
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        base_data.update(overrides)
        return base_data

    @classmethod
    def generate_task_collection(cls, count: int = 5) -> List[Dict[str, Any]]:
        """Generate a collection of diverse tasks."""
        tasks = []
        priorities = ["low", "medium", "high", "critical"]
        statuses = ["open", "in_progress", "blocked", "completed", "cancelled"]
        assignees = ["alice", "bob", "charlie", "diana", "eve"]
        tag_groups = [
            ["bug", "frontend"],
            ["feature", "backend"],
            ["enhancement", "ui"],
            ["bug", "security"],
            ["documentation", "api"],
            ["testing", "automation"],
            ["refactor", "performance"],
            ["migration", "database"],
        ]

        for i in range(count):
            task_data = cls.generate_task_data(
                task_id=f"TSK-{i+1:04d}",
                title=f"Task {i+1}: {['Fix', 'Implement', 'Update', 'Add', 'Remove'][i % 5]} Feature {chr(65 + i)}",
                priority=priorities[i % len(priorities)],
                status=statuses[i % len(statuses)],
                assignees=[assignees[i % len(assignees)]],
                tags=tag_groups[i % len(tag_groups)],
                created_at=datetime.now() - timedelta(days=i),
                updated_at=datetime.now() - timedelta(hours=i),
            )
            tasks.append(task_data)

        return tasks

    @classmethod
    def generate_epic_collection(cls, count: int = 3) -> List[Dict[str, Any]]:
        """Generate a collection of diverse epics."""
        epics = []
        statuses = ["planning", "in_progress", "on_hold", "completed"]

        for i in range(count):
            epic_data = cls.generate_epic_data(
                epic_id=f"EP-{i+1:04d}",
                title=f"Epic {i+1}: {['User Management', 'Payment System', 'Reporting Dashboard'][i % 3]}",
                status=statuses[i % len(statuses)],
                target_date=date.today() + timedelta(days=30 * (i + 1)),
                created_at=datetime.now() - timedelta(days=i * 7),
            )
            epics.append(epic_data)

        return epics

    @classmethod
    def generate_full_project_data(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Generate a complete project with all ticket types."""
        return {
            "tasks": cls.generate_task_collection(10),
            "epics": cls.generate_epic_collection(3),
            "issues": [
                cls.generate_issue_data(
                    issue_id=f"ISS-{i+1:04d}",
                    title=f"Issue {i+1}: {['Login Bug', 'UI Problem', 'Performance Issue'][i % 3]}",
                    issue_type=["bug", "enhancement", "feature_request"][i % 3],
                )
                for i in range(5)
            ],
            "prs": [
                cls.generate_pr_data(
                    pr_id=f"PR-{i+1:04d}",
                    title=f"PR {i+1}: {['Fix Bug', 'Add Feature', 'Update Docs'][i % 3]}",
                    source_branch=f"{'feature' if i % 2 == 0 else 'bugfix'}/branch-{i}",
                    pr_type=["feature", "bugfix", "enhancement"][i % 3],
                )
                for i in range(4)
            ],
        }


class MockFactory:
    """Factory for creating mock objects."""

    @staticmethod
    def create_mock_project(temp_dir: Optional[Path] = None) -> Mock:
        """Create a mock project object."""
        if temp_dir is None:
            temp_dir = Path(tempfile.mkdtemp())

        mock_project = Mock(spec=Project)
        mock_project.path = temp_dir
        mock_project.config_path = temp_dir / ".ai-trackdown" / "config.yaml"
        mock_project.name = "Mock Project"

        # Mock methods
        mock_project.get_tasks_directory.return_value = temp_dir / "tasks"
        mock_project.get_templates_directory.return_value = temp_dir / "templates"
        mock_project.is_initialized.return_value = True
        mock_project.is_git_repository.return_value = False
        mock_project.validate_structure.return_value = []

        return mock_project

    @staticmethod
    def create_mock_config() -> Mock:
        """Create a mock configuration object."""
        mock_config = Mock()

        # Default configuration values
        config_data = {
            "version": "1.0.0",
            "project": {
                "name": "Mock Project",
                "description": "A mock project for testing",
            },
            "editor": {"default": "code"},
            "tasks": {"directory": "tasks", "default_assignee": None},
            "templates": {"directory": "templates"},
        }

        def mock_get(key, default=None):
            keys = key.split(".")
            value = config_data
            try:
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default

        def mock_set(key, value):
            keys = key.split(".")
            target = config_data
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            target[keys[-1]] = value

        mock_config.get.side_effect = mock_get
        mock_config.set.side_effect = mock_set
        mock_config.save.return_value = None
        mock_config.to_dict.return_value = config_data

        return mock_config

    @staticmethod
    def create_mock_task_manager() -> Mock:
        """Create a mock task manager."""
        mock_manager = Mock()

        # Generate sample tasks
        sample_tasks = TestDataGenerator.generate_task_collection(5)

        mock_manager.list_tasks.return_value = [
            Mock(
                model=TaskModel(**task_data),
                file_path=Path(f"/mock/path/{task_data['id']}.md"),
            )
            for task_data in sample_tasks
        ]

        mock_manager.create_task.return_value = Mock(
            model=TaskModel(**TestDataGenerator.generate_task_data()),
            file_path=Path("/mock/path/new_task.md"),
        )

        mock_manager.get_statistics.return_value = {
            "total": 5,
            "open": 2,
            "in_progress": 1,
            "completed": 2,
            "cancelled": 0,
        }

        return mock_manager

    @staticmethod
    def create_mock_validation_result(
        valid: bool = True, errors: List[str] = None, warnings: List[str] = None
    ):
        """Create a mock validation result."""
        mock_result = Mock()
        mock_result.valid = valid
        mock_result.errors = errors or []
        mock_result.warnings = warnings or []
        return mock_result


@pytest.fixture
def sample_task_data():
    """Fixture providing sample task data."""
    return TestDataGenerator.generate_task_data()


@pytest.fixture
def sample_epic_data():
    """Fixture providing sample epic data."""
    return TestDataGenerator.generate_epic_data()


@pytest.fixture
def sample_issue_data():
    """Fixture providing sample issue data."""
    return TestDataGenerator.generate_issue_data()


@pytest.fixture
def sample_pr_data():
    """Fixture providing sample PR data."""
    return TestDataGenerator.generate_pr_data()


@pytest.fixture
def sample_project_data():
    """Fixture providing sample project data."""
    return TestDataGenerator.generate_project_data()


@pytest.fixture
def task_collection():
    """Fixture providing a collection of tasks."""
    return TestDataGenerator.generate_task_collection(10)


@pytest.fixture
def full_project_data():
    """Fixture providing complete project data."""
    return TestDataGenerator.generate_full_project_data()


@pytest.fixture
def mock_project():
    """Fixture providing a mock project."""
    return MockFactory.create_mock_project()


@pytest.fixture
def mock_config():
    """Fixture providing a mock configuration."""
    return MockFactory.create_mock_config()


@pytest.fixture
def mock_task_manager():
    """Fixture providing a mock task manager."""
    return MockFactory.create_mock_task_manager()


@pytest.fixture
def temporary_project_structure():
    """Fixture providing a temporary project structure."""
    temp_dir = Path(tempfile.mkdtemp())

    # Create project structure
    (temp_dir / ".ai-trackdown").mkdir()
    (temp_dir / "tasks").mkdir()
    (temp_dir / "tasks" / "open").mkdir()
    (temp_dir / "tasks" / "in_progress").mkdir()
    (temp_dir / "tasks" / "completed").mkdir()
    (temp_dir / "templates").mkdir()

    # Create config file
    config_content = """version: 1.0.0
project:
  name: Temporary Test Project
  description: A temporary project for testing
editor:
  default: code
tasks:
  directory: tasks
templates:
  directory: templates
"""
    (temp_dir / ".ai-trackdown" / "config.yaml").write_text(config_content)

    # Create sample templates
    task_template = """---
id: {{ id or 'TSK-' + '%04d'|format(sequence_number) }}
title: {{ title }}
status: {{ status or 'open' }}
priority: {{ priority or 'medium' }}
---

# {{ title }}

{{ description or 'Task description here.' }}
"""
    (temp_dir / "templates" / "task.yaml").write_text(task_template)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def populated_project_structure(temporary_project_structure):
    """Fixture providing a project structure with sample data."""
    project_dir = temporary_project_structure
    tasks_dir = project_dir / "tasks"

    # Create sample tasks
    sample_tasks = TestDataGenerator.generate_task_collection(5)

    for i, task_data in enumerate(sample_tasks):
        status_dir = tasks_dir / task_data["status"]
        status_dir.mkdir(exist_ok=True)

        task_file = (
            status_dir
            / f"{task_data['id']}-{task_data['title'].lower().replace(' ', '-')}.md"
        )

        # Create frontmatter
        frontmatter_lines = []
        for key, value in task_data.items():
            if key in ["created_at", "updated_at"] and isinstance(value, datetime):
                frontmatter_lines.append(f"{key}: {value.isoformat()}")
            elif isinstance(value, list):
                frontmatter_lines.append(f"{key}:")
                for item in value:
                    frontmatter_lines.append(f"  - {item}")
            else:
                frontmatter_lines.append(f"{key}: {value}")

        frontmatter = "---\n" + "\n".join(frontmatter_lines) + "\n---\n"
        content = f"\n# {task_data['title']}\n\n{task_data.get('description', 'Task content.')}\n"

        task_file.write_text(frontmatter + content)

    yield project_dir


class TestScenarios:
    """Pre-defined test scenarios for complex testing."""

    @staticmethod
    def agile_sprint_scenario():
        """Generate data for agile sprint scenario."""
        return {
            "sprint_name": "Sprint 15",
            "start_date": date.today(),
            "end_date": date.today() + timedelta(days=14),
            "tasks": [
                TestDataGenerator.generate_task_data(
                    task_id="TSK-0101",
                    title="User story: Login with OAuth",
                    priority="high",
                    tags=["user-story", "authentication", "oauth"],
                    assignees=["frontend_dev"],
                    status="in_progress",
                ),
                TestDataGenerator.generate_task_data(
                    task_id="TSK-0102",
                    title="Bug: Login button not responsive",
                    priority="medium",
                    tags=["bug", "ui", "responsive"],
                    assignees=["frontend_dev"],
                    status="open",
                ),
                TestDataGenerator.generate_task_data(
                    task_id="TSK-0103",
                    title="Technical: Setup OAuth provider",
                    priority="high",
                    tags=["technical", "backend", "oauth"],
                    assignees=["backend_dev"],
                    status="completed",
                ),
            ],
            "goals": [
                "Complete user authentication epic",
                "Fix critical UI bugs",
                "Improve user experience",
            ],
        }

    @staticmethod
    def release_preparation_scenario():
        """Generate data for release preparation scenario."""
        return {
            "release_version": "v2.1.0",
            "release_date": date.today() + timedelta(days=7),
            "tasks": [
                TestDataGenerator.generate_task_data(
                    task_id="TSK-0201",
                    title="Update changelog for v2.1.0",
                    priority="high",
                    tags=["release", "documentation"],
                    assignees=["tech_writer"],
                    status="open",
                ),
                TestDataGenerator.generate_task_data(
                    task_id="TSK-0202",
                    title="Run full regression test suite",
                    priority="critical",
                    tags=["release", "testing", "qa"],
                    assignees=["qa_engineer"],
                    status="in_progress",
                ),
                TestDataGenerator.generate_task_data(
                    task_id="TSK-0203",
                    title="Deploy to staging environment",
                    priority="high",
                    tags=["release", "deployment", "devops"],
                    assignees=["devops_engineer"],
                    status="completed",
                ),
            ],
            "blockers": [],
            "critical_issues": [],
        }

    @staticmethod
    def bug_triage_scenario():
        """Generate data for bug triage scenario."""
        return {
            "triage_date": date.today(),
            "issues": [
                TestDataGenerator.generate_issue_data(
                    issue_id="ISS-0301",
                    title="Critical: Data loss in user profiles",
                    issue_type="bug",
                    severity="critical",
                    priority="critical",
                    status="open",
                ),
                TestDataGenerator.generate_issue_data(
                    issue_id="ISS-0302",
                    title="High: Performance degradation in search",
                    issue_type="bug",
                    severity="high",
                    priority="high",
                    status="open",
                ),
                TestDataGenerator.generate_issue_data(
                    issue_id="ISS-0303",
                    title="Medium: UI alignment issues on mobile",
                    issue_type="bug",
                    severity="medium",
                    priority="medium",
                    status="open",
                ),
            ],
            "assignment_matrix": {
                "critical": ["senior_dev", "team_lead"],
                "high": ["senior_dev"],
                "medium": ["junior_dev"],
            },
        }


@pytest.fixture
def agile_sprint_data():
    """Fixture providing agile sprint scenario data."""
    return TestScenarios.agile_sprint_scenario()


@pytest.fixture
def release_preparation_data():
    """Fixture providing release preparation scenario data."""
    return TestScenarios.release_preparation_scenario()


@pytest.fixture
def bug_triage_data():
    """Fixture providing bug triage scenario data."""
    return TestScenarios.bug_triage_scenario()
