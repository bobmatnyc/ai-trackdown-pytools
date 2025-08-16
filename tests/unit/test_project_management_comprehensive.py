"""Comprehensive unit tests for Project management functionality."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

from ai_trackdown_pytools.core.project import Project, ProjectModel
from ai_trackdown_pytools.exceptions import ProjectError


class TestProjectModel:
    """Test ProjectModel functionality."""

    def test_project_model_creation(self):
        """Test creating ProjectModel."""
        now = datetime.now()
        model = ProjectModel(
            name="Test Project",
            description="A test project",
            version="1.0.0",
            author="Test Author",
            license="MIT",
            created_at=now,
            updated_at=now,
            metadata={"key": "value"},
        )

        assert model.name == "Test Project"
        assert model.description == "A test project"
        assert model.version == "1.0.0"
        assert model.author == "Test Author"
        assert model.license == "MIT"
        assert model.created_at == now
        assert model.updated_at == now
        assert model.metadata == {"key": "value"}

    def test_project_model_minimal(self):
        """Test creating ProjectModel with minimal data."""
        now = datetime.now()
        model = ProjectModel(
            name="Minimal Project",
            created_at=now,
            updated_at=now,
        )

        assert model.name == "Minimal Project"
        assert model.description is None
        assert model.version == "1.0.0"  # Default
        assert model.author is None
        assert model.license is None
        assert model.metadata == {}  # Default

    def test_project_model_serialization(self):
        """Test ProjectModel serialization."""
        now = datetime.now()
        model = ProjectModel(
            name="Test Project",
            created_at=now,
            updated_at=now,
        )

        data = model.model_dump()
        assert data["name"] == "Test Project"
        assert data["created_at"] == now.isoformat()
        assert data["updated_at"] == now.isoformat()


class TestProjectClass:
    """Test Project class functionality."""

    def test_project_initialization(self):
        """Test Project initialization."""
        now = datetime.now()
        model = ProjectModel(
            name="Test Project",
            created_at=now,
            updated_at=now,
        )
        path = Path("/test/project")

        project = Project(path, model)

        assert project.path == path
        assert project.data == model
        assert project.name == "Test Project"

    @patch('ai_trackdown_pytools.core.project.Project.exists')
    @patch('ai_trackdown_pytools.core.project.Project._create_structure')
    @patch('ai_trackdown_pytools.core.config.Config.create_default')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_project_create_basic(self, mock_yaml_dump, mock_file, mock_config_create, mock_create_structure, mock_exists):
        """Test creating a basic project."""
        mock_exists.return_value = False
        
        project_path = Path("/test/project")
        
        project = Project.create(project_path, name="Test Project")
        
        # Verify structure creation was called
        mock_create_structure.assert_called_once_with(project_path)
        
        # Verify config creation was called
        mock_config_create.assert_called_once()
        
        # Verify project file was written
        mock_file.assert_called()
        mock_yaml_dump.assert_called()
        
        assert project.name == "Test Project"
        assert project.path == project_path

    @patch('ai_trackdown_pytools.core.project.Project.exists')
    @patch('ai_trackdown_pytools.core.project.Project._create_structure')
    @patch('ai_trackdown_pytools.core.config.Config.create_default')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_project_create_full(self, mock_yaml_dump, mock_file, mock_config_create, mock_create_structure, mock_exists):
        """Test creating a project with all options."""
        mock_exists.return_value = False
        
        project_path = Path("/test/project")
        
        project = Project.create(
            project_path,
            name="Full Project",
            description="A full project",
            version="2.0.0",
            author="Test Author",
            license="MIT",
            metadata={"custom": "value"},
        )
        
        assert project.name == "Full Project"
        assert project.data.description == "A full project"
        assert project.data.version == "2.0.0"
        assert project.data.author == "Test Author"
        assert project.data.license == "MIT"
        assert project.data.metadata == {"custom": "value"}

    @patch('ai_trackdown_pytools.core.project.Project.exists')
    def test_project_create_already_exists(self, mock_exists):
        """Test creating project when it already exists."""
        mock_exists.return_value = True
        
        project_path = Path("/test/project")
        
        with pytest.raises(ProjectError, match="already an AI Trackdown project"):
            Project.create(project_path)

    @patch('builtins.open', new_callable=mock_open, read_data='name: "Test Project"\ncreated_at: "2023-01-01T00:00:00"\nupdated_at: "2023-01-01T00:00:00"')
    @patch('yaml.safe_load')
    def test_project_load_success(self, mock_yaml_load, mock_file):
        """Test loading existing project."""
        project_data = {
            "name": "Test Project",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
        }
        mock_yaml_load.return_value = project_data
        
        project_path = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=True):
            project = Project.load(project_path)
        
        assert project.name == "Test Project"
        assert isinstance(project.data.created_at, datetime)
        assert isinstance(project.data.updated_at, datetime)

    def test_project_load_file_not_found(self):
        """Test loading project when file doesn't exist."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=False):
            with pytest.raises(ProjectError, match="No project file found"):
                Project.load(project_path)

    @patch('builtins.open', new_callable=mock_open, read_data='')
    @patch('yaml.safe_load')
    def test_project_load_empty_file(self, mock_yaml_load, mock_file):
        """Test loading project with empty file."""
        mock_yaml_load.return_value = None
        
        project_path = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(ProjectError, match="Project file is empty or invalid"):
                Project.load(project_path)

    def test_project_exists_true(self):
        """Test project exists check when project exists."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=True):
            assert Project.exists(project_path) is True

    def test_project_exists_false(self):
        """Test project exists check when project doesn't exist."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=False):
            assert Project.exists(project_path) is False

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_project_save(self, mock_yaml_dump, mock_file):
        """Test saving project."""
        now = datetime.now()
        model = ProjectModel(
            name="Test Project",
            created_at=now,
            updated_at=now,
        )
        project = Project(Path("/test/project"), model)
        
        with patch.object(model, 'dict', return_value={"name": "Test Project"}):
            project.save()
        
        mock_file.assert_called_once()
        mock_yaml_dump.assert_called_once()
        # updated_at should be updated
        assert project.data.updated_at > now

    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_project_update(self, mock_yaml_dump, mock_file):
        """Test updating project."""
        now = datetime.now()
        model = ProjectModel(
            name="Test Project",
            description="Old description",
            created_at=now,
            updated_at=now,
        )
        project = Project(Path("/test/project"), model)
        
        with patch.object(model, 'dict', return_value={"name": "Updated Project"}):
            project.update(name="Updated Project", description="New description")
        
        assert project.data.name == "Updated Project"
        assert project.data.description == "New description"
        mock_yaml_dump.assert_called_once()

    def test_project_name_property(self):
        """Test project name property."""
        now = datetime.now()
        model = ProjectModel(
            name="Test Project",
            created_at=now,
            updated_at=now,
        )
        project = Project(Path("/test/project"), model)
        
        assert project.name == "Test Project"


class TestProjectStructureCreation:
    """Test project structure creation functionality."""

    @patch('builtins.open', new_callable=mock_open)
    def test_create_structure_directories(self, mock_file):
        """Test creating project directory structure."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'mkdir') as mock_mkdir:
            Project._create_structure(project_path)
        
        # Should create multiple directories
        assert mock_mkdir.call_count >= 5  # At least the main directories
        
        # Should create files
        assert mock_file.call_count >= 2  # .gitignore and README.md

    @patch('builtins.open', new_callable=mock_open)
    def test_create_structure_gitignore_content(self, mock_file):
        """Test .gitignore content creation."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'mkdir'):
            with patch.object(Path, 'exists', return_value=False):
                Project._create_structure(project_path)
        
        # Check that .gitignore was written with correct content
        calls = mock_file.call_args_list
        gitignore_call = None
        for call in calls:
            if ".gitignore" in str(call):
                gitignore_call = call
                break
        
        assert gitignore_call is not None

    @patch('builtins.open', new_callable=mock_open)
    def test_create_structure_readme_content(self, mock_file):
        """Test README.md content creation."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'mkdir'):
            with patch.object(Path, 'exists', return_value=False):
                Project._create_structure(project_path)
        
        # Check that README.md was written
        calls = mock_file.call_args_list
        readme_call = None
        for call in calls:
            if "README.md" in str(call):
                readme_call = call
                break
        
        assert readme_call is not None

    @patch('builtins.open', new_callable=mock_open)
    def test_create_structure_existing_files(self, mock_file):
        """Test structure creation with existing files."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'mkdir'):
            with patch.object(Path, 'exists', return_value=True):  # Files already exist
                Project._create_structure(project_path)
        
        # Should not write files that already exist
        assert mock_file.call_count == 0


class TestProjectErrorHandling:
    """Test project error handling."""

    def test_project_error_creation(self):
        """Test ProjectError creation."""
        error = ProjectError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    @patch('ai_trackdown_pytools.core.project.Project._create_structure')
    @patch('ai_trackdown_pytools.core.config.Config.create_default')
    @patch('builtins.open', side_effect=IOError("File write error"))
    def test_project_create_file_error(self, mock_file, mock_config_create, mock_create_structure):
        """Test project creation with file write error."""
        project_path = Path("/test/project")
        
        with patch.object(Project, 'exists', return_value=False):
            with pytest.raises(ProjectError, match="Failed to create project configuration"):
                Project.create(project_path)

    @patch('ai_trackdown_pytools.core.project.Project._create_structure')
    @patch('ai_trackdown_pytools.core.config.Config.create_default', side_effect=Exception("Config error"))
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_project_create_config_error(self, mock_yaml_dump, mock_file, mock_config_create, mock_create_structure):
        """Test project creation with config creation error."""
        project_path = Path("/test/project")
        
        with patch.object(Project, 'exists', return_value=False):
            with pytest.raises(ProjectError, match="Failed to create project configuration"):
                Project.create(project_path)

    @patch('builtins.open', new_callable=mock_open, read_data='invalid: yaml: content:')
    @patch('yaml.safe_load', side_effect=yaml.YAMLError("Invalid YAML"))
    def test_project_load_yaml_error(self, mock_yaml_load, mock_file):
        """Test loading project with YAML parsing error."""
        project_path = Path("/test/project")
        
        with patch.object(Path, 'exists', return_value=True):
            with pytest.raises(yaml.YAMLError):
                Project.load(project_path)
