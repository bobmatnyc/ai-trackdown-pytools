"""Comprehensive unit tests for Config management functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
import yaml

from ai_trackdown_pytools.core.config import Config, ConfigModel


class TestConfigModel:
    """Test ConfigModel functionality."""

    def test_config_model_creation(self):
        """Test creating ConfigModel with defaults."""
        model = ConfigModel()

        assert model.version == "1.0.0"
        assert model.project == {}
        assert model.editor == {"default": "code"}
        assert model.templates == {"directory": "templates"}
        assert model.tasks == {"directory": "tickets"}
        assert model.git == {"auto_commit": False}
        assert model.plugins == {}

    def test_config_model_custom_values(self):
        """Test creating ConfigModel with custom values."""
        model = ConfigModel(
            version="2.0.0",
            project={"name": "test"},
            editor={"default": "vim"},
            tasks={"directory": "tasks", "auto_id": True},
            git={"auto_commit": True},
            plugins={"test": "plugin"},
        )

        assert model.version == "2.0.0"
        assert model.project == {"name": "test"}
        assert model.editor == {"default": "vim"}
        assert model.tasks == {"directory": "tasks", "auto_id": True}
        assert model.git == {"auto_commit": True}
        assert model.plugins == {"test": "plugin"}

    def test_config_model_extra_fields(self):
        """Test ConfigModel allows extra fields."""
        model = ConfigModel(
            custom_field="custom_value",
            nested={"field": "value"},
        )

        assert model.custom_field == "custom_value"
        assert model.nested == {"field": "value"}

    def test_config_model_serialization(self):
        """Test ConfigModel serialization."""
        model = ConfigModel(
            version="2.0.0",
            project={"name": "test"},
        )

        data = model.model_dump()
        assert data["version"] == "2.0.0"
        assert data["project"] == {"name": "test"}
        assert isinstance(data, dict)


class TestConfigClass:
    """Test Config class functionality."""

    def setUp(self):
        """Set up test environment."""
        # Clear config instances before each test
        Config._instances.clear()

    def tearDown(self):
        """Clean up test environment."""
        # Clear config instances after each test
        Config._instances.clear()

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_singleton_behavior(self, mock_find_root):
        """Test Config singleton behavior per project."""
        mock_find_root.return_value = None
        
        project_path = Path("/test/project")
        
        config1 = Config(project_path)
        config2 = Config(project_path)
        
        # Should be the same instance
        assert config1 is config2

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_different_projects(self, mock_find_root):
        """Test Config creates different instances for different projects."""
        mock_find_root.return_value = None
        
        project1 = Path("/test/project1")
        project2 = Path("/test/project2")
        
        config1 = Config(project1)
        config2 = Config(project2)
        
        # Should be different instances
        assert config1 is not config2

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('builtins.open', new_callable=mock_open, read_data='version: "2.0.0"\nproject:\n  name: "test"')
    @patch('yaml.safe_load')
    def test_config_load_from_file(self, mock_yaml_load, mock_file, mock_find_root):
        """Test loading config from file."""
        mock_find_root.return_value = None
        config_data = {
            "version": "2.0.0",
            "project": {"name": "test"},
        }
        mock_yaml_load.return_value = config_data
        
        config_path = Path("/test/config.yaml")
        
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'stat') as mock_stat:
                mock_stat.return_value.st_mtime = 123456789
                config = Config.load(config_path)
        
        assert config._config.version == "2.0.0"
        assert config._config.project == {"name": "test"}
        assert config._config_path == config_path
        assert config._loaded_at == 123456789

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('ai_trackdown_pytools.core.config.Config.find_config_file')
    def test_config_load_auto_find(self, mock_find_config, mock_find_root):
        """Test loading config with auto-find."""
        mock_find_root.return_value = None
        mock_config_path = Path("/test/config.yaml")
        mock_find_config.return_value = mock_config_path
        
        with patch.object(Path, 'exists', return_value=False):
            config = Config.load()
        
        mock_find_config.assert_called_once()

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_config_create_default(self, mock_yaml_dump, mock_file, mock_find_root):
        """Test creating default configuration."""
        mock_find_root.return_value = None
        
        config_path = Path("/test/project/.ai-trackdown/config.yaml")
        
        with patch.object(Path, 'mkdir'):
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_mtime = 123456789
                    config = Config.create_default(config_path)
        
        # Should create config with project name from path
        assert config._config.project["name"] == "project"
        assert config._config_path == config_path
        mock_yaml_dump.assert_called_once()

    def test_config_find_config_file_current_dir(self):
        """Test finding config file in current directory."""
        with patch('pathlib.Path.cwd', return_value=Path("/test/project")):
            with patch.object(Path, 'exists') as mock_exists:
                # Mock config file exists in current directory
                def exists_side_effect(path):
                    return str(path).endswith(".ai-trackdown/config.yaml")
                mock_exists.side_effect = exists_side_effect
                
                config_path = Config.find_config_file()
                
                assert config_path == Path("/test/project/.ai-trackdown/config.yaml")

    def test_config_find_config_file_parent_dir(self):
        """Test finding config file in parent directory."""
        with patch('pathlib.Path.cwd', return_value=Path("/test/project/subdir")):
            with patch.object(Path, 'exists') as mock_exists:
                # Mock config file exists in parent directory
                def exists_side_effect(path):
                    return str(path) == "/test/project/.ai-trackdown/config.yaml"
                mock_exists.side_effect = exists_side_effect
                
                config_path = Config.find_config_file()
                
                assert config_path == Path("/test/project/.ai-trackdown/config.yaml")

    @patch('pathlib.Path.home')
    def test_config_find_config_file_global(self, mock_home):
        """Test finding global config file."""
        mock_home.return_value = Path("/home/user")
        
        with patch('pathlib.Path.cwd', return_value=Path("/test/project")):
            with patch.object(Path, 'exists') as mock_exists:
                # Mock only global config exists
                def exists_side_effect(path):
                    return str(path) == "/home/user/.ai-trackdown/config.yaml"
                mock_exists.side_effect = exists_side_effect
                
                config_path = Config.find_config_file()
                
                assert config_path == Path("/home/user/.ai-trackdown/config.yaml")

    def test_config_find_config_file_none(self):
        """Test finding config file when none exists."""
        with patch('pathlib.Path.cwd', return_value=Path("/test/project")):
            with patch.object(Path, 'exists', return_value=False):
                config_path = Config.find_config_file()
                
                assert config_path is None

    @patch('pathlib.Path.home')
    def test_config_get_global_config_path(self, mock_home):
        """Test getting global config path."""
        mock_home.return_value = Path("/home/user")
        
        global_path = Config.get_global_config_path()
        
        assert global_path == Path("/home/user/.ai-trackdown/config.yaml")

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_getattr(self, mock_find_root):
        """Test Config __getattr__ method."""
        mock_find_root.return_value = None
        
        config = Config()
        
        # Should access ConfigModel attributes
        assert config.version == "1.0.0"
        assert config.editor == {"default": "code"}

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_getattr_private(self, mock_find_root):
        """Test Config __getattr__ with private attributes."""
        mock_find_root.return_value = None
        
        config = Config()
        
        # Should raise AttributeError for private attributes
        with pytest.raises(AttributeError):
            _ = config._private_attr

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_getattr_missing(self, mock_find_root):
        """Test Config __getattr__ with missing attributes."""
        mock_find_root.return_value = None
        
        config = Config()
        
        # Should raise AttributeError for missing attributes
        with pytest.raises(AttributeError):
            _ = config.missing_attribute

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_get_simple(self, mock_find_root):
        """Test Config get method with simple key."""
        mock_find_root.return_value = None
        
        config = Config()
        
        assert config.get("version") == "1.0.0"
        assert config.get("missing", "default") == "default"

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_get_nested(self, mock_find_root):
        """Test Config get method with nested key."""
        mock_find_root.return_value = None
        
        config = Config()
        
        assert config.get("editor.default") == "code"
        assert config.get("editor.missing", "default") == "default"
        assert config.get("missing.nested", "default") == "default"

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_set_simple(self, mock_find_root):
        """Test Config set method with simple key."""
        mock_find_root.return_value = None
        
        config = Config()
        
        config.set("version", "2.0.0")
        assert config.get("version") == "2.0.0"

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_set_nested(self, mock_find_root):
        """Test Config set method with nested key."""
        mock_find_root.return_value = None
        
        config = Config()
        
        config.set("editor.default", "vim")
        assert config.get("editor.default") == "vim"
        
        config.set("new.nested.key", "value")
        assert config.get("new.nested.key") == "value"

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('builtins.open', new_callable=mock_open)
    @patch('yaml.dump')
    def test_config_save(self, mock_yaml_dump, mock_file, mock_find_root):
        """Test Config save method."""
        mock_find_root.return_value = None
        
        config = Config()
        config._config_path = Path("/test/config.yaml")
        
        with patch.object(Path, 'mkdir'):
            config.save()
        
        mock_file.assert_called_once()
        mock_yaml_dump.assert_called_once()

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_save_no_path(self, mock_find_root):
        """Test Config save method with no config path."""
        mock_find_root.return_value = None
        
        config = Config()
        config._config_path = None
        
        # Should not raise error, just do nothing
        config.save()

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_to_dict(self, mock_find_root):
        """Test Config to_dict method."""
        mock_find_root.return_value = None
        
        config = Config()
        
        data = config.to_dict()
        assert isinstance(data, dict)
        assert data["version"] == "1.0.0"
        assert data["editor"] == {"default": "code"}

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_update_from_dict(self, mock_find_root):
        """Test Config update_from_dict method."""
        mock_find_root.return_value = None
        
        config = Config()
        
        update_data = {
            "version": "2.0.0",
            "new_field": "new_value",
        }
        
        config.update_from_dict(update_data)
        
        assert config.get("version") == "2.0.0"
        assert config.get("new_field") == "new_value"
        # Should preserve existing fields
        assert config.get("editor.default") == "code"

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_config_path_property(self, mock_find_root):
        """Test Config config_path property."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = Path("/test/config.yaml")

        assert config.config_path == Path("/test/config.yaml")

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_project_root_property(self, mock_find_root):
        """Test Config project_root property."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = Path("/test/project/.ai-trackdown/config.yaml")

        assert config.project_root == Path("/test/project")

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_project_root_property_none(self, mock_find_root):
        """Test Config project_root property with no config path."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = None

        assert config.project_root is None

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_is_stale_no_path(self, mock_find_root):
        """Test Config is_stale with no config path."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = None

        assert config.is_stale() is False

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_is_stale_no_loaded_at(self, mock_find_root):
        """Test Config is_stale with no loaded_at time."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = Path("/test/config.yaml")
        config._loaded_at = None

        with patch.object(Path, 'exists', return_value=True):
            assert config.is_stale() is True

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_is_stale_file_newer(self, mock_find_root):
        """Test Config is_stale with newer file."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = Path("/test/config.yaml")
        config._loaded_at = 100

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'stat') as mock_stat:
                mock_stat.return_value.st_mtime = 200  # Newer than loaded_at
                assert config.is_stale() is True

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_is_stale_file_older(self, mock_find_root):
        """Test Config is_stale with older file."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = Path("/test/config.yaml")
        config._loaded_at = 200

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'stat') as mock_stat:
                mock_stat.return_value.st_mtime = 100  # Older than loaded_at
                assert config.is_stale() is False

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('ai_trackdown_pytools.core.config.Config.load')
    def test_config_reload(self, mock_load, mock_find_root):
        """Test Config reload method."""
        mock_find_root.return_value = Path("/test/project")

        project_path = Path("/test/project")

        # Create an existing instance
        config = Config(project_path)
        config._config_path = Path("/test/config.yaml")

        # Mock the load method to return a new config
        new_config = Mock()
        mock_load.return_value = new_config

        result = Config.reload(project_path)

        # Should have called load with the existing config path
        mock_load.assert_called_once_with(
            config_path=Path("/test/config.yaml"),
            project_path=Path("/test/project")
        )
        assert result == new_config

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_clear_cache(self, mock_find_root):
        """Test Config clear_cache method."""
        mock_find_root.return_value = None

        # Create some instances
        config1 = Config(Path("/test/project1"))
        config2 = Config(Path("/test/project2"))

        # Verify instances exist
        assert len(Config._instances) == 2

        # Clear cache
        Config.clear_cache()

        # Verify cache is cleared
        assert len(Config._instances) == 0


class TestConfigErrorHandling:
    """Test Config error handling."""

    def setUp(self):
        """Set up test environment."""
        Config._instances.clear()

    def tearDown(self):
        """Clean up test environment."""
        Config._instances.clear()

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('builtins.open', new_callable=mock_open, read_data='')
    @patch('yaml.safe_load')
    def test_config_load_empty_file(self, mock_yaml_load, mock_file, mock_find_root):
        """Test loading config from empty file."""
        mock_find_root.return_value = None
        mock_yaml_load.return_value = None  # Empty file

        config_path = Path("/test/config.yaml")

        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'stat') as mock_stat:
                mock_stat.return_value.st_mtime = 123456789
                config = Config.load(config_path)

        # Should use default config
        assert config._config.version == "1.0.0"

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('builtins.open', new_callable=mock_open, read_data='invalid: yaml: content {{')
    @patch('yaml.safe_load')
    def test_config_load_invalid_yaml(self, mock_yaml_load, mock_file, mock_find_root):
        """Test loading config with invalid YAML."""
        mock_find_root.return_value = None
        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")

        config_path = Path("/test/config.yaml")

        with patch.object(Path, 'exists', return_value=True):
            # Should raise the YAML error
            with pytest.raises(yaml.YAMLError):
                Config.load(config_path)

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('builtins.open', side_effect=IOError("File read error"))
    def test_config_load_file_error(self, mock_file, mock_find_root):
        """Test loading config with file read error."""
        mock_find_root.return_value = None

        config_path = Path("/test/config.yaml")

        with patch.object(Path, 'exists', return_value=True):
            # Should raise the IO error
            with pytest.raises(IOError):
                Config.load(config_path)

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch('builtins.open', side_effect=IOError("File write error"))
    def test_config_save_file_error(self, mock_file, mock_find_root):
        """Test saving config with file write error."""
        mock_find_root.return_value = None

        config = Config()
        config._config_path = Path("/test/config.yaml")

        with patch.object(Path, 'mkdir'):
            # Should raise the IO error
            with pytest.raises(IOError):
                config.save()


class TestConfigIntegration:
    """Test Config integration scenarios."""

    def setUp(self):
        """Set up test environment."""
        Config._instances.clear()

    def tearDown(self):
        """Clean up test environment."""
        Config._instances.clear()

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    @patch.dict(os.environ, {'EDITOR': 'nano'})
    def test_config_create_default_with_env_editor(self, mock_find_root):
        """Test creating default config with EDITOR environment variable."""
        mock_find_root.return_value = None

        config_path = Path("/test/project/.ai-trackdown/config.yaml")

        with patch.object(Path, 'mkdir'):
            with patch.object(Path, 'exists', return_value=True):
                with patch('builtins.open', new_callable=mock_open):
                    with patch('yaml.dump'):
                        with patch.object(Path, 'stat') as mock_stat:
                            mock_stat.return_value.st_mtime = 123456789
                            config = Config.create_default(config_path)

        # Should use EDITOR environment variable
        assert config._config.editor["default"] == "nano"

    @patch('ai_trackdown_pytools.core.project.Project.find_project_root')
    def test_config_workflow_load_modify_save(self, mock_find_root):
        """Test complete workflow: load, modify, save."""
        mock_find_root.return_value = None

        config_path = Path("/test/config.yaml")
        initial_data = {
            "version": "1.0.0",
            "project": {"name": "test"},
        }

        # Load config
        with patch.object(Path, 'exists', return_value=True):
            with patch('builtins.open', new_callable=mock_open, read_data=yaml.dump(initial_data)):
                with patch('yaml.safe_load', return_value=initial_data):
                    with patch.object(Path, 'stat') as mock_stat:
                        mock_stat.return_value.st_mtime = 123456789
                        config = Config.load(config_path)

        # Modify config
        config.set("project.description", "Updated description")
        config.set("new.field", "new value")

        # Save config
        with patch.object(Path, 'mkdir'):
            with patch('builtins.open', new_callable=mock_open) as mock_file:
                with patch('yaml.dump') as mock_yaml_dump:
                    config.save()

        # Verify save was called
        mock_file.assert_called_once()
        mock_yaml_dump.assert_called_once()

        # Verify data was updated
        assert config.get("project.description") == "Updated description"
        assert config.get("new.field") == "new value"
