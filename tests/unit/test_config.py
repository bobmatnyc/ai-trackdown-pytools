"""Unit tests for configuration management."""

from pathlib import Path

import yaml

from ai_trackdown_pytools.core.config import Config, ConfigModel


class TestConfigModel:
    """Test ConfigModel."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ConfigModel()

        assert config.version == "1.0.0"
        assert config.project == {}
        assert config.editor == {"default": "code"}
        assert config.templates == {"directory": "templates"}
        assert config.tasks == {"directory": "tickets"}
        assert config.git == {"auto_commit": False}
        assert config.plugins == {}

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ConfigModel(
            version="2.0.0", project={"name": "test"}, editor={"default": "vim"}
        )

        assert config.version == "2.0.0"
        assert config.project == {"name": "test"}
        assert config.editor == {"default": "vim"}


class TestConfig:
    """Test Config class."""

    def test_project_specific_singleton_pattern(self, temp_dir: Path):
        """Test that Config follows project-specific singleton pattern."""
        # Same project path should return same instance
        config1 = Config(temp_dir)
        config2 = Config(temp_dir)
        assert config1 is config2

        # Different project paths should return different instances
        other_dir = temp_dir / "other_project"
        other_dir.mkdir()
        config3 = Config(other_dir)
        assert config3 is not config1

    def test_create_default_config(self, temp_dir: Path):
        """Test creating default configuration."""
        config_path = temp_dir / ".ai-trackdown" / "config.yaml"
        config = Config.create_default(config_path)

        assert config_path.exists()
        assert config.config_path == config_path

        # Check default values
        assert config.get("version") == "0.9.0"
        assert config.get("project.name") == temp_dir.name
        assert config.get("editor.default") is not None

    def test_load_config_from_file(self, temp_dir: Path):
        """Test loading configuration from file."""
        config_path = temp_dir / "config.yaml"
        config_data = {
            "version": "1.0.0",
            "project": {"name": "test_project"},
            "editor": {"default": "vim"},
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = Config.load(config_path)

        assert config.get("project.name") == "test_project"
        assert config.get("editor.default") == "vim"

    def test_get_nested_values(self, mock_config: Config):
        """Test getting nested configuration values."""
        mock_config.set("project.name", "test")
        mock_config.set("nested.deep.value", "deep_value")

        assert mock_config.get("project.name") == "test"
        assert mock_config.get("nested.deep.value") == "deep_value"
        assert mock_config.get("nonexistent.key", "default") == "default"

    def test_set_nested_values(self, mock_config: Config):
        """Test setting nested configuration values."""
        mock_config.set("new.nested.key", "new_value")

        assert mock_config.get("new.nested.key") == "new_value"

    def test_save_config(self, temp_dir: Path):
        """Test saving configuration to file."""
        config_path = temp_dir / "config.yaml"
        config = Config.create_default(config_path)

        config.set("project.name", "saved_project")
        config.save()

        # Reload and verify
        with open(config_path) as f:
            saved_data = yaml.safe_load(f)

        assert saved_data["project"]["name"] == "saved_project"

    def test_find_config_file(self, temp_dir: Path):
        """Test finding configuration file in hierarchy."""
        # Create config in subdirectory
        sub_dir = temp_dir / "subdir"
        sub_dir.mkdir()
        config_path = temp_dir / ".ai-trackdown" / "config.yaml"
        Config.create_default(config_path)

        # Change to subdirectory and find config
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(sub_dir)
            found_config = Config.find_config_file()
            # Resolve both paths to handle symlinks in temp directories
            assert found_config.resolve() == config_path.resolve()
        finally:
            os.chdir(original_cwd)

    def test_to_dict(self, mock_config: Config):
        """Test converting configuration to dictionary."""
        mock_config.set("test.key", "test_value")
        config_dict = mock_config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["test"]["key"] == "test_value"

    def test_project_root(self, temp_dir: Path):
        """Test getting project root directory."""
        config_path = temp_dir / ".ai-trackdown" / "config.yaml"
        config = Config.create_default(config_path)

        assert config.project_root == temp_dir
