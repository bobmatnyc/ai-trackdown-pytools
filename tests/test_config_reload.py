"""Test configuration reload and cache management functionality."""

import time

import yaml

from ai_trackdown_pytools.core.config import Config


class TestConfigReload:
    """Test config reload functionality."""

    def test_is_stale(self, tmp_path):
        """Test is_stale method."""
        project_path = tmp_path
        config_dir = project_path / ".ai-trackdown"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        # Create initial config
        initial_config = {
            "version": "1.0.0",
            "project": {"name": "test-project", "value": "initial"},
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Load config
        config = Config.load(config_path=config_file, project_path=project_path)

        # Should not be stale initially
        assert not config.is_stale()

        # Wait a moment to ensure file modification time is different
        time.sleep(0.1)

        # Modify the config file
        modified_config = {
            "version": "1.0.0",
            "project": {"name": "test-project", "value": "modified"},
        }

        with open(config_file, "w") as f:
            yaml.dump(modified_config, f)

        # Should now be stale
        assert config.is_stale()

    def test_reload(self, tmp_path):
        """Test reload method."""
        project_path = tmp_path
        config_dir = project_path / ".ai-trackdown"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        # Create initial config
        initial_config = {
            "version": "1.0.0",
            "project": {"name": "test-project", "value": "initial"},
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Load config
        config1 = Config.load(config_path=config_file, project_path=project_path)
        assert config1.get("project.value") == "initial"

        # Wait to ensure different modification time
        time.sleep(0.1)

        # Modify the config file
        modified_config = {
            "version": "1.0.0",
            "project": {"name": "test-project", "value": "modified"},
        }

        with open(config_file, "w") as f:
            yaml.dump(modified_config, f)

        # Getting the same instance should still have old value
        config2 = Config(project_path)
        assert config2.get("project.value") == "initial"
        assert config2 is config1  # Same instance

        # Reload should give us the new value
        config3 = Config.reload(project_path)
        assert config3.get("project.value") == "modified"
        assert config3 is not config1  # Different instance

        # Now getting the instance should give us the new one
        config4 = Config(project_path)
        assert config4 is config3
        assert config4.get("project.value") == "modified"

    def test_clear_cache(self, tmp_path):
        """Test clear_cache method."""
        # Create two temporary project directories
        project1 = tmp_path / "project1"
        project2 = tmp_path / "project2"

        # Create configs for two projects
        for project, name in [(project1, "project1"), (project2, "project2")]:
            config_dir = project / ".ai-trackdown"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_file = config_dir / "config.yaml"

            config_data = {"version": "1.0.0", "project": {"name": name}}

            with open(config_file, "w") as f:
                yaml.dump(config_data, f)

        # Load both configs
        config1 = Config.load(
            config_path=project1 / ".ai-trackdown" / "config.yaml",
            project_path=project1,
        )
        config2 = Config.load(
            config_path=project2 / ".ai-trackdown" / "config.yaml",
            project_path=project2,
        )

        assert config1.get("project.name") == "project1"
        assert config2.get("project.name") == "project2"

        # Verify they're cached
        assert Config(project1) is config1
        assert Config(project2) is config2

        # Clear cache
        Config.clear_cache()

        # Getting configs again should create new instances
        config1_new = Config.load(
            config_path=project1 / ".ai-trackdown" / "config.yaml",
            project_path=project1,
        )
        config2_new = Config.load(
            config_path=project2 / ".ai-trackdown" / "config.yaml",
            project_path=project2,
        )

        assert config1_new is not config1
        assert config2_new is not config2
        assert config1_new.get("project.name") == "project1"
        assert config2_new.get("project.name") == "project2"

    def test_is_stale_no_config_file(self, tmp_path):
        """Test is_stale when config file doesn't exist."""
        config = Config(tmp_path)
        # Should return False when no config file exists
        assert not config.is_stale()

    def test_is_stale_no_loaded_at(self, tmp_path):
        """Test is_stale when _loaded_at is None."""
        project_path = tmp_path
        config_dir = project_path / ".ai-trackdown"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.yaml"

        # Create config file
        config_data = {"version": "1.0.0"}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Load config and manually set _loaded_at to None
        config = Config.load(config_path=config_file, project_path=project_path)
        config._loaded_at = None

        # Should return True when _loaded_at is None but file exists
        assert config.is_stale()
