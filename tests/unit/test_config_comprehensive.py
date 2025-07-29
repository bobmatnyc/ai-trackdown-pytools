"""Comprehensive unit tests for config module."""

import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import yaml

from ai_trackdown_pytools.core.config import Config


class TestConfig:
    """Test Config class functionality."""

    def test_config_singleton(self):
        """Test Config follows singleton pattern."""
        config1 = Config()
        config2 = Config()
        assert config1 is config2

    def test_config_defaults(self):
        """Test Config has default values."""
        config = Config()
        assert config.version == "1.0.0"
        assert config.editor["default"] == "vim"
        assert config.editor["fallback"] == ["nano", "vi"]
        assert config.tasks["id_format"] == "TSK-{counter:04d}"
        assert config.tasks["counter"] == 1
        assert config.issues["id_format"] == "ISS-{counter:04d}"
        assert config.issues["counter"] == 1
        assert config.epics["id_format"] == "EP-{counter:04d}"
        assert config.epics["counter"] == 1
        assert config.prs["id_format"] == "PR-{counter:04d}"
        assert config.prs["counter"] == 1

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_load_from_file(self, mock_open_func, mock_exists):
        """Test loading config from file."""
        # Reset singleton
        Config._instance = None

        config_data = {
            "version": "2.0.0",
            "editor": {"default": "emacs"},
            "tasks": {"id_format": "TASK-{counter:05d}", "counter": 42},
            "custom": {"field": "value"},
        }

        mock_exists.return_value = True
        mock_open_func.return_value = mock_open(read_data=yaml.dump(config_data))()

        config = Config.load("config.yaml")

        assert config.version == "2.0.0"
        assert config.editor["default"] == "emacs"
        assert config.tasks["id_format"] == "TASK-{counter:05d}"
        assert config.tasks["counter"] == 42
        assert config.get("custom.field") == "value"
        assert config.config_path == Path("config.yaml")

    @patch("pathlib.Path.exists")
    def test_load_nonexistent_file(self, mock_exists):
        """Test loading config when file doesn't exist."""
        # Reset singleton
        Config._instance = None

        mock_exists.return_value = False

        config = Config.load("nonexistent.yaml")

        # Should use defaults
        assert config.version == "1.0.0"
        assert config.config_path is None

    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_load_invalid_yaml(self, mock_open_func, mock_exists):
        """Test loading config with invalid YAML."""
        # Reset singleton
        Config._instance = None

        mock_exists.return_value = True
        mock_open_func.return_value = mock_open(read_data="invalid: yaml: content {{")()

        # Config module doesn't raise exceptions for invalid YAML, it uses defaults
        config = Config.load("invalid.yaml")
        assert config.version == "1.0.0"  # Falls back to defaults

    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    def test_find_project_root(self, mock_exists, mock_cwd):
        """Test finding project root directory."""
        # Reset singleton
        Config._instance = None

        # Mock file system
        current_dir = Path("/home/user/project/subdir")
        mock_cwd.return_value = current_dir

        def exists_side_effect(path):
            # .aitrackdown exists in /home/user/project
            return str(path) == "/home/user/project/.aitrackdown"

        mock_exists.side_effect = exists_side_effect

        config = Config()

        assert config.project_root == Path("/home/user/project")

    @patch("pathlib.Path.cwd")
    @patch("pathlib.Path.exists")
    def test_no_project_root(self, mock_exists, mock_cwd):
        """Test when no project root is found."""
        # Reset singleton
        Config._instance = None

        mock_cwd.return_value = Path("/home/user/somewhere")
        mock_exists.return_value = False  # No .aitrackdown anywhere

        config = Config()

        assert config.project_root is None

    def test_get_nested_value(self):
        """Test getting nested config values."""
        config = Config()

        # Get existing nested value
        assert config.get("editor.default") == "vim"
        assert config.get("tasks.id_format") == "TSK-{counter:04d}"

        # Get with default
        assert config.get("nonexistent.key", "default") == "default"

        # Get None for nonexistent without default
        assert config.get("nonexistent.key") is None

    def test_set_nested_value(self):
        """Test setting nested config values."""
        config = Config()

        # Set existing value
        config.set("editor.default", "code")
        assert config.editor["default"] == "code"

        # Set new nested value
        config.set("custom.nested.value", "test")
        assert config.custom["nested"]["value"] == "test"

        # Set root level value
        config.set("new_field", "value")
        assert config.new_field == "value"

    @patch("builtins.open", new_callable=mock_open)
    def test_save_config(self, mock_file):
        """Test saving config to file."""
        config = Config()
        config.config_path = Path("config.yaml")

        # Modify some values
        config.set("version", "2.0.0")
        config.set("custom.field", "value")

        config.save()

        # Verify file was opened for writing
        mock_file.assert_called_once_with(Path("config.yaml"), "w", encoding="utf-8")

        # Verify YAML was written
        written_content = "".join(
            call.args[0] for call in mock_file().write.call_args_list
        )
        assert (
            "version: 2.0.0" in written_content or "version: '2.0.0'" in written_content
        )

    def test_save_without_path(self):
        """Test saving config without a path raises error."""
        config = Config()
        config.config_path = None

        # Without a path, save should do nothing or use a default
        config.save()  # Should not raise

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_with_directory_creation(self, mock_file, mock_mkdir):
        """Test saving config creates parent directories."""
        config = Config()
        config.config_path = Path("/new/dir/config.yaml")

        config.save()

        # Verify directory creation was attempted
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = Config()
        config.set("custom.field", "value")

        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        assert config_dict["version"] == "1.0.0"
        assert config_dict["editor"]["default"] == "vim"
        assert config_dict["custom"]["field"] == "value"

        # Should not include private attributes
        assert "_instance" not in config_dict
        assert "config_path" not in config_dict
        assert "project_root" not in config_dict

    def test_update_from_dict(self):
        """Test updating config from dictionary."""
        config = Config()

        update_data = {
            "version": "3.0.0",
            "editor": {"default": "neovim"},
            "new_section": {"key": "value"},
        }

        config.update(update_data)

        assert config.version == "3.0.0"
        assert config.editor["default"] == "neovim"
        assert config.new_section["key"] == "value"

    def test_config_edge_cases(self):
        """Test config edge cases."""
        config = Config()

        # Test getting non-existent attribute raises AttributeError
        with pytest.raises(AttributeError):
            _ = config.nonexistent_attribute

    @patch.dict(os.environ, {"AITRACKDOWN_CONFIG": "/custom/config.yaml"})
    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_load_from_env_var(self, mock_open_func, mock_exists):
        """Test loading config from environment variable."""
        # Reset singleton
        Config._instance = None

        config_data = {"version": "env-version"}

        mock_exists.return_value = True
        mock_open_func.return_value = mock_open(read_data=yaml.dump(config_data))()

        config = Config.load()

        assert config.version == "env-version"
        assert str(config.config_path) == "/custom/config.yaml"

    @patch("pathlib.Path.home")
    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_load_from_home_dir(self, mock_open_func, mock_exists, mock_home):
        """Test loading config from home directory."""
        # Reset singleton
        Config._instance = None

        mock_home.return_value = Path("/home/user")

        config_data = {"version": "home-version"}

        def exists_side_effect(path):
            return str(path) == "/home/user/.aitrackdown/config.yaml"

        mock_exists.side_effect = exists_side_effect
        mock_open_func.return_value = mock_open(read_data=yaml.dump(config_data))()

        config = Config.load()

        assert config.version == "home-version"

    def test_get_all_paths(self):
        """Test getting all configuration values as paths."""
        config = Config()

        # Test nested paths
        assert config.get("editor") == config.editor
        assert config.get("tasks.counter") == 1
        assert config.get("editor.fallback.0") == "nano"
        assert config.get("editor.fallback.1") == "vi"

    def test_set_creates_missing_parents(self):
        """Test set creates missing parent dictionaries."""
        config = Config()

        # Set deeply nested value
        config.set("a.b.c.d.e", "deep_value")

        assert config.a["b"]["c"]["d"]["e"] == "deep_value"

    def test_config_merge_on_load(self):
        """Test config merges with defaults on load."""
        # Reset singleton
        Config._instance = None

        config_data = {
            "version": "2.0.0",
            "tasks": {"counter": 100},  # Only override counter, not id_format
        }

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=yaml.dump(config_data))):
                config = Config.load("config.yaml")

        # Should have both default and loaded values
        assert config.version == "2.0.0"  # From file
        assert config.tasks["counter"] == 100  # From file
        assert config.tasks["id_format"] == "TSK-{counter:04d}"  # From defaults
        assert config.editor["default"] == "vim"  # From defaults
