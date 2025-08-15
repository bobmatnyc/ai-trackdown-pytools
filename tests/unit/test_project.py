"""Unit tests for project management functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project, ProjectError


class TestProject:
    """Test Project class functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_new_project(self):
        """Test creating a new project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create project
            project = Project.create(project_path)

            # Verify project structure
            assert project.path == project_path
            assert (project_path / ".ai-trackdown").exists()
            assert (project_path / ".ai-trackdown" / "config.yaml").exists()
            assert (project_path / "tasks").exists()
            assert (project_path / "templates").exists()

    def test_create_project_with_custom_name(self):
        """Test creating project with custom name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path, name="Custom Project Name")

            # Load config to verify name
            config = Config.load(project_path / ".ai-trackdown" / "config.yaml")
            assert config.get("project.name") == "Custom Project Name"

    def test_create_project_existing_directory_error(self):
        """Test error when creating project in existing AI Trackdown directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create first project
            Project.create(project_path)

            # Attempt to create another project in same directory
            with pytest.raises(ProjectError, match="already an AI Trackdown project"):
                Project.create(project_path)

    def test_load_existing_project(self):
        """Test loading an existing project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create project first
            Project.create(project_path)

            # Load existing project
            project = Project.load(project_path)

            assert project.path == project_path
            assert project.config is not None
            assert project.is_initialized()

    def test_load_non_existent_project(self):
        """Test error when loading non-existent project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "non_existent"

            with pytest.raises(ProjectError, match="not an AI Trackdown project"):
                Project.load(project_path)

    def test_load_directory_without_ai_trackdown(self):
        """Test error when loading directory without .ai-trackdown."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "not_a_project"
            project_path.mkdir()

            with pytest.raises(ProjectError, match="not an AI Trackdown project"):
                Project.load(project_path)

    def test_find_project_root_from_subdirectory(self):
        """Test finding project root from subdirectory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create project
            Project.create(project_path)

            # Create subdirectory
            sub_dir = project_path / "subdir" / "deep"
            sub_dir.mkdir(parents=True)

            # Find project root from subdirectory
            found_project = Project.find_root(sub_dir)

            assert found_project.path == project_path

    def test_find_project_root_no_project(self):
        """Test finding project root when no project exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            some_dir = Path(temp_dir) / "no_project"
            some_dir.mkdir()

            found_project = Project.find_root(some_dir)
            assert found_project is None

    def test_is_initialized_true(self):
        """Test is_initialized returns True for valid project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)
            assert project.is_initialized() is True

    def test_is_initialized_false(self):
        """Test is_initialized returns False for invalid project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"

            project = Project(project_path)
            assert project.is_initialized() is False

    def test_get_tasks_directory(self):
        """Test getting tasks directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)
            tasks_dir = project.get_tasks_directory()

            assert tasks_dir == project_path / "tasks"
            assert tasks_dir.exists()

    def test_get_tasks_directory_custom_path(self):
        """Test getting tasks directory with custom path in config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Modify config to use custom tasks directory
            project.config.set("tasks.directory", "custom_tasks")
            project.config.save()

            tasks_dir = project.get_tasks_directory()
            assert tasks_dir == project_path / "custom_tasks"

    def test_get_templates_directory(self):
        """Test getting templates directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)
            templates_dir = project.get_templates_directory()

            assert templates_dir == project_path / "templates"
            assert templates_dir.exists()

    def test_create_directory_structure(self):
        """Test creating complete directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Check all required directories exist
            assert (project_path / ".ai-trackdown").exists()
            assert (project_path / "tasks").exists()
            assert (project_path / "templates").exists()

            # Check subdirectories in tasks
            assert (project_path / "tasks" / "open").exists()
            assert (project_path / "tasks" / "in_progress").exists()
            assert (project_path / "tasks" / "completed").exists()

    def test_validate_project_structure(self):
        """Test validating project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Valid project should validate successfully
            issues = project.validate_structure()
            assert len(issues) == 0

    def test_validate_project_structure_missing_directories(self):
        """Test validation with missing directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Remove a required directory
            import shutil

            shutil.rmtree(project_path / "tasks")

            # Validation should find issues
            issues = project.validate_structure()
            assert len(issues) > 0
            assert any("tasks directory" in issue for issue in issues)

    def test_validate_project_structure_missing_config(self):
        """Test validation with missing config file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Remove config file
            (project_path / ".ai-trackdown" / "config.yaml").unlink()

            # Validation should find issues
            issues = project.validate_structure()
            assert len(issues) > 0
            assert any("config" in issue.lower() for issue in issues)

    def test_get_config(self):
        """Test getting project configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path, name="Test Config Project")
            config = project.get_config()

            assert config is not None
            assert config.get("project.name") == "Test Config Project"

    def test_update_config(self):
        """Test updating project configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Update configuration
            project.config.set("project.description", "Updated description")
            project.config.save()

            # Reload project and verify change
            reloaded_project = Project.load(project_path)
            assert (
                reloaded_project.config.get("project.description")
                == "Updated description"
            )

    def test_project_properties(self):
        """Test project properties."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path, name="Property Test Project")

            assert project.name == "Property Test Project"
            assert project.path == project_path
            assert project.config_path == project_path / ".ai-trackdown" / "config.yaml"

    def test_project_with_git_repository(self):
        """Test project creation in Git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Initialize Git repository
            import subprocess

            subprocess.run(["git", "init"], cwd=project_path, capture_output=True)

            project = Project.create(project_path)

            # Should detect Git repository
            assert project.is_git_repository()

    def test_project_without_git_repository(self):
        """Test project creation without Git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Should not detect Git repository
            assert not project.is_git_repository()

    @patch("ai_trackdown_pytools.core.project.Config")
    def test_project_config_error_handling(self, mock_config):
        """Test project handling of config errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Mock config to raise an error
            mock_config.create_default.side_effect = Exception("Config error")

            with pytest.raises(
                ProjectError, match="Failed to create project configuration"
            ):
                Project.create(project_path)

    def test_project_str_representation(self):
        """Test project string representation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path, name="String Test Project")

            project_str = str(project)
            assert "String Test Project" in project_str
            assert str(project_path) in project_str

    def test_project_repr(self):
        """Test project repr representation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            project_repr = repr(project)
            assert "Project" in project_repr
            assert str(project_path) in project_repr


class TestProjectError:
    """Test ProjectError exception."""

    def test_project_error_creation(self):
        """Test creating ProjectError."""
        error = ProjectError("Test error message")
        assert str(error) == "Test error message"

    def test_project_error_inheritance(self):
        """Test ProjectError inheritance."""
        error = ProjectError("Test error")
        assert isinstance(error, Exception)


class TestProjectUtilityMethods:
    """Test utility methods in Project class."""

    def test_ensure_directory_exists(self):
        """Test ensuring directory exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project(project_path)
            test_dir = project_path / "test_dir"

            # Directory doesn't exist
            assert not test_dir.exists()

            # Ensure it exists
            project._ensure_directory(test_dir)
            assert test_dir.exists()

            # Should not error if already exists
            project._ensure_directory(test_dir)
            assert test_dir.exists()

    def test_copy_template_files(self):
        """Test copying template files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            project = Project.create(project_path)

            # Check that template files were copied
            templates_dir = project.get_templates_directory()
            assert (templates_dir / "task.yaml").exists() or len(
                list(templates_dir.glob("*.yaml"))
            ) > 0
