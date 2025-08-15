"""Unit tests for CLI functionality."""

from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app


class TestCLI:
    """Test CLI commands."""

    def test_help_command(self, runner: CliRunner):
        """Test help command."""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "AI-powered project tracking and task management" in result.output
        assert "Commands" in result.output

    def test_version_command(self, runner: CliRunner):
        """Test version command."""
        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "aitrackdown v" in result.output

    def test_info_command(self, runner: CliRunner):
        """Test info command."""
        result = runner.invoke(app, ["info"])

        assert result.exit_code == 0
        assert "System:" in result.output
        assert "Python:" in result.output

    def test_health_command(self, runner: CliRunner):
        """Test health command."""
        result = runner.invoke(app, ["health"])

        assert result.exit_code in [0, 1]  # May fail if dependencies missing
        assert "health check" in result.output

    def test_init_help(self, runner: CliRunner):
        """Test init command help."""
        result = runner.invoke(app, ["init", "--help"])

        assert result.exit_code == 0
        assert "Initialize project" in result.output

    def test_status_help(self, runner: CliRunner):
        """Test status command help."""
        result = runner.invoke(app, ["status", "--help"])

        assert result.exit_code == 0
        assert "Show status" in result.output

    def test_create_help(self, runner: CliRunner):
        """Test create command help."""
        result = runner.invoke(app, ["create", "--help"])

        assert result.exit_code == 0
        assert "Create tasks/issues" in result.output

    def test_template_help(self, runner: CliRunner):
        """Test template command help."""
        result = runner.invoke(app, ["template", "--help"])

        assert result.exit_code == 0
        assert "Manage templates" in result.output
