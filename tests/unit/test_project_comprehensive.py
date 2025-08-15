"""Comprehensive unit tests for project module."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import yaml

from ai_trackdown_pytools.core.project import Project, ProjectError


class TestProject:
    """Test Project class functionality."""

    def test_project_initialization(self):
        """Test Project initialization."""
        project_path = Path("/test/project")
        project = Project(project_path)

        assert project.path == project_path
        assert project.config_dir == project_path / ".aitrackdown"
        assert project.config_file == project_path / ".aitrackdown" / "config.yaml"
        assert project.tasks_dir == project_path / "tasks"
        assert project.issues_dir == project_path / "issues"
        assert project.epics_dir == project_path / "epics"
        assert project.prs_dir == project_path / "prs"
        assert project.templates_dir == project_path / "templates"

    @patch("pathlib.Path.exists")
    def test_exists_true(self, mock_exists):
        """Test checking if project exists."""
        project_path = Path("/test/project")

        def exists_side_effect(path):
            # .aitrackdown directory exists
            return str(path).endswith(".aitrackdown")

        mock_exists.side_effect = exists_side_effect

        assert Project.exists(project_path) is True

    @patch("pathlib.Path.exists")
    def test_exists_false(self, mock_exists):
        """Test checking if project doesn't exist."""
        project_path = Path("/test/project")
        mock_exists.return_value = False

        assert Project.exists(project_path) is False

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    @patch("ai_trackdown_pytools.core.config.Config")
    def test_create_project(self, mock_config_class, mock_file, mock_mkdir):
        """Test creating a new project."""
        project_path = Path("/test/project")

        # Mock config
        mock_config = Mock()
        mock_config.config_path = None
        mock_config.project_root = None
        mock_config_class.return_value = mock_config

        # Create project
        project = Project.create(
            project_path,
            name="Test Project",
            description="A test project",
            author="Test Author",
        )

        assert isinstance(project, Project)

        # Verify directories were created
        expected_dirs = [
            project_path / ".aitrackdown",
            project_path / "tasks",
            project_path / "issues",
            project_path / "epics",
            project_path / "prs",
            project_path / "templates",
        ]

        for expected_dir in expected_dirs:
            assert any(call[0][0] == expected_dir for call in mock_mkdir.call_args_list)

        # Verify config was saved
        mock_config.save.assert_called_once()

        # Verify README was created
        mock_file.assert_called()
        readme_written = False
        for call in mock_file.call_args_list:
            if "README.md" in str(call[0][0]):
                readme_written = True
                break
        assert readme_written

    @patch("pathlib.Path.exists")
    def test_create_existing_project_fails(self, mock_exists):
        """Test creating project in existing location fails."""
        project_path = Path("/test/project")
        mock_exists.return_value = True

        with pytest.raises(ProjectError) as exc_info:
            Project.create(project_path)

        assert "already exists" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    @patch("ai_trackdown_pytools.core.config.Config.load")
    def test_load_project(self, mock_config_load, mock_open_func, mock_exists):
        """Test loading an existing project."""
        project_path = Path("/test/project")

        # Mock file system
        mock_exists.return_value = True

        # Mock project info file
        project_info = {
            "name": "Loaded Project",
            "description": "A loaded project",
            "author": "Test Author",
            "created_at": "2023-01-01T00:00:00",
            "metadata": {"custom": "value"},
        }
        mock_open_func.return_value = mock_open(read_data=yaml.dump(project_info))()

        # Mock config
        mock_config = Mock()
        mock_config_load.return_value = mock_config

        # Load project
        project = Project.load(project_path)

        assert isinstance(project, Project)
        assert project.name == "Loaded Project"
        assert project.description == "A loaded project"
        assert project.author == "Test Author"
        assert project.metadata["custom"] == "value"

    @patch("pathlib.Path.exists")
    def test_load_nonexistent_project(self, mock_exists):
        """Test loading non-existent project fails."""
        project_path = Path("/test/project")
        mock_exists.return_value = False

        with pytest.raises(ProjectError) as exc_info:
            Project.load(project_path)

        assert "not found" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_load_project_invalid_yaml(self, mock_open_func, mock_exists):
        """Test loading project with invalid YAML."""
        project_path = Path("/test/project")
        mock_exists.return_value = True

        # Invalid YAML
        mock_open_func.return_value = mock_open(read_data="invalid: yaml: {{")()

        with pytest.raises(ProjectError) as exc_info:
            Project.load(project_path)

        assert "Failed to load project info" in str(exc_info.value)

    @patch("builtins.open", new_callable=mock_open)
    def test_save_project_info(self, mock_file):
        """Test saving project info."""
        project = Project(Path("/test/project"))
        project.name = "Test Project"
        project.description = "Test Description"
        project.author = "Test Author"
        project.created_at = datetime(2023, 1, 1, 0, 0, 0)
        project.metadata = {"key": "value"}

        project.save()

        # Verify file was written
        mock_file.assert_called_once()

        # Verify content
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert "name: Test Project" in written_content
        assert "description: Test Description" in written_content
        assert "author: Test Author" in written_content

    def test_get_statistics(self):
        """Test getting project statistics."""
        project = Project(Path("/test/project"))

        with patch.object(project, "_count_files") as mock_count:
            # Mock file counts
            def count_side_effect(directory):
                counts = {
                    project.tasks_dir: 10,
                    project.issues_dir: 5,
                    project.epics_dir: 2,
                    project.prs_dir: 3,
                }
                return counts.get(directory, 0)

            mock_count.side_effect = count_side_effect

            stats = project.get_statistics()

            assert stats["tasks"] == 10
            assert stats["issues"] == 5
            assert stats["epics"] == 2
            assert stats["prs"] == 3
            assert stats["total"] == 20

    @patch("pathlib.Path.rglob")
    def test_count_files(self, mock_rglob):
        """Test counting files in directory."""
        project = Project(Path("/test/project"))

        # Mock files
        mock_rglob.return_value = [
            Path("file1.md"),
            Path("file2.md"),
            Path("file3.txt"),  # Non-markdown file
        ]

        count = project._count_files(project.tasks_dir)

        assert count == 2  # Only .md files

    def test_get_recent_items(self):
        """Test getting recent items from project."""
        project = Project(Path("/test/project"))

        # Mock file system
        mock_files = []
        for i in range(10):
            mock_file = Mock()
            mock_file.stat.return_value.st_mtime = 1000000 + i
            mock_file.name = f"file{i}.md"
            mock_files.append(mock_file)

        with patch("pathlib.Path.rglob", return_value=mock_files):
            recent = project.get_recent_items(limit=5)

            assert len(recent) == 5
            # Should be sorted by modification time (newest first)
            assert recent[0]["name"] == "file9.md"
            assert recent[4]["name"] == "file5.md"

    @patch("ai_trackdown_pytools.core.config.Config")
    def test_get_config(self, mock_config_class):
        """Test getting project config."""
        project = Project(Path("/test/project"))

        mock_config = Mock()
        mock_config_class.load.return_value = mock_config

        config = project.get_config()

        assert config == mock_config
        mock_config_class.load.assert_called_once_with(project.config_file)

    @patch("shutil.copytree")
    def test_create_from_template(self, mock_copytree):
        """Test creating project from template."""
        project_path = Path("/test/project")
        template_path = Path("/templates/basic")

        with patch.object(Project, "create") as mock_create:
            mock_project = Mock()
            mock_create.return_value = mock_project

            project = Project.create_from_template(
                project_path, template_path, name="Template Project"
            )

            # Verify template was copied
            mock_copytree.assert_called_once()

            # Verify project was created
            mock_create.assert_called_once()
            assert project == mock_project

    def test_project_error(self):
        """Test ProjectError exception."""
        error = ProjectError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_project_properties(self):
        """Test project property getters."""
        project = Project(Path("/test/project"))
        project.name = "Test"
        project.description = "Desc"
        project.author = "Author"
        project.created_at = datetime(2023, 1, 1)
        project.metadata = {"key": "value"}

        assert project.name == "Test"
        assert project.description == "Desc"
        assert project.author == "Author"
        assert project.created_at == datetime(2023, 1, 1)
        assert project.metadata == {"key": "value"}

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    def test_ensure_directories(self, mock_mkdir, mock_exists):
        """Test ensuring project directories exist."""
        project = Project(Path("/test/project"))

        # Some directories don't exist
        def exists_side_effect(path):
            return "tasks" in str(path) or "issues" in str(path)

        mock_exists.side_effect = exists_side_effect

        project._ensure_directories()

        # Should create missing directories
        assert (
            mock_mkdir.call_count >= 4
        )  # At least epics, prs, templates, .aitrackdown

    def test_to_dict(self):
        """Test converting project to dictionary."""
        project = Project(Path("/test/project"))
        project.name = "Test Project"
        project.description = "Test Description"
        project.author = "Test Author"
        project.created_at = datetime(2023, 1, 1, 0, 0, 0)
        project.metadata = {"custom": "value"}

        project_dict = project.to_dict()

        assert project_dict["name"] == "Test Project"
        assert project_dict["description"] == "Test Description"
        assert project_dict["author"] == "Test Author"
        assert project_dict["created_at"] == "2023-01-01T00:00:00"
        assert project_dict["metadata"] == {"custom": "value"}
        assert project_dict["path"] == str(Path("/test/project"))

    @patch("pathlib.Path.exists")
    def test_find_project_root_from_subdir(self, mock_exists):
        """Test finding project root from subdirectory."""
        # Mock being in /test/project/tasks/subtask
        current_path = Path("/test/project/tasks/subtask")

        def exists_side_effect(path):
            # .aitrackdown exists at /test/project
            return str(path) == "/test/project/.aitrackdown"

        mock_exists.side_effect = exists_side_effect

        root = Project.find_root(current_path)

        assert root == Path("/test/project")

    @patch("pathlib.Path.exists")
    def test_find_project_root_not_found(self, mock_exists):
        """Test finding project root when not in project."""
        mock_exists.return_value = False

        root = Project.find_root(Path("/somewhere/else"))

        assert root is None
