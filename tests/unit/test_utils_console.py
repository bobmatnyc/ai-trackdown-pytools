"""Tests for console utilities."""

import os
from unittest.mock import patch

from rich.table import Table

from ai_trackdown_pytools.utils.console import Console, get_console


class TestConsole:
    """Test console utilities."""

    def test_console_plain_mode_flag(self):
        """Test console initializes in plain mode with flag."""
        console = Console(force_plain=True)
        assert console.is_plain is True

    def test_console_rich_mode_default(self):
        """Test console defaults to rich mode."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("os.isatty", return_value=True):
                console = Console()
                assert console.is_plain is False

    def test_console_plain_mode_env_aitrackdown(self):
        """Test AITRACKDOWN_PLAIN environment variable."""
        with patch.dict(os.environ, {"AITRACKDOWN_PLAIN": "1"}):
            console = Console()
            assert console.is_plain is True

        with patch.dict(os.environ, {"AITRACKDOWN_PLAIN": "true"}):
            console = Console()
            assert console.is_plain is True

        with patch.dict(os.environ, {"AITRACKDOWN_PLAIN": "yes"}):
            console = Console()
            assert console.is_plain is True

    def test_console_plain_mode_env_no_color(self):
        """Test NO_COLOR environment variable."""
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            console = Console()
            assert console.is_plain is True

    def test_console_plain_mode_env_ci(self):
        """Test CI environment variable."""
        with patch.dict(os.environ, {"CI": "1"}):
            console = Console()
            assert console.is_plain is True

    def test_console_plain_mode_non_tty(self):
        """Test plain mode when output is not a TTY."""
        with patch("os.isatty", return_value=False):
            console = Console()
            assert console.is_plain is True

    def test_print_plain_mode(self, capsys):
        """Test print in plain mode."""
        console = Console(force_plain=True)
        console.print("[bold]Hello[/bold] [red]World[/red]")

        captured = capsys.readouterr()
        assert captured.out == "Hello World\n"
        assert "[bold]" not in captured.out
        assert "[red]" not in captured.out

    def test_print_rich_mode(self):
        """Test print in rich mode preserves markup."""
        console = Console(force_plain=False)
        # We can't easily test rich output, but we can verify it doesn't crash
        console.print("[bold]Hello[/bold] [red]World[/red]")

    def test_print_panel_plain_mode(self, capsys):
        """Test panel printing in plain mode."""
        console = Console(force_plain=True)
        console.print_panel("Panel content", title="Test Panel")

        captured = capsys.readouterr()
        assert "Test Panel" in captured.out
        assert "Panel content" in captured.out
        assert "─" not in captured.out  # No box drawing characters

    def test_print_table_plain_mode(self, capsys):
        """Test table printing in plain mode."""
        console = Console(force_plain=True)

        table = Table(title="Test Table")
        table.add_column("Name")
        table.add_column("Value")
        table.add_row("Item 1", "Value 1")
        table.add_row("Item 2", "Value 2")

        console.print_table(table)

        captured = capsys.readouterr()
        assert "Test Table" in captured.out
        assert "Name | Value" in captured.out
        assert "Item 1 | Value 1" in captured.out
        assert "Item 2 | Value 2" in captured.out

    def test_print_success(self, capsys):
        """Test success message printing."""
        # Plain mode
        console = Console(force_plain=True)
        console.print_success("Operation completed")
        captured = capsys.readouterr()
        assert captured.out == "SUCCESS: Operation completed\n"

        # Rich mode (can't test exact output but verify no crash)
        console = Console(force_plain=False)
        console.print_success("Operation completed")

    def test_print_error(self, capsys):
        """Test error message printing."""
        # Plain mode
        console = Console(force_plain=True)
        console.print_error("Something went wrong")
        captured = capsys.readouterr()
        assert captured.out == "ERROR: Something went wrong\n"

    def test_print_warning(self, capsys):
        """Test warning message printing."""
        # Plain mode
        console = Console(force_plain=True)
        console.print_warning("Be careful")
        captured = capsys.readouterr()
        assert captured.out == "WARNING: Be careful\n"

    def test_print_info(self, capsys):
        """Test info message printing."""
        # Plain mode
        console = Console(force_plain=True)
        console.print_info("For your information")
        captured = capsys.readouterr()
        assert captured.out == "INFO: For your information\n"

    def test_strip_markup(self):
        """Test markup stripping."""
        console = Console(force_plain=True)

        # Test color stripping
        assert console._strip_markup("[red]Hello[/red]") == "Hello"
        assert console._strip_markup("[bold blue]Text[/bold blue]") == "Text"

        # Test style stripping
        assert console._strip_markup("[bold]Bold[/bold]") == "Bold"
        assert console._strip_markup("[dim]Dim[/dim]") == "Dim"
        assert console._strip_markup("[italic]Italic[/italic]") == "Italic"

        # Test link stripping
        assert console._strip_markup("[link=http://example.com]Link[/link]") == "Link"

        # Test complex markup
        text = "[bold red]Important:[/bold red] [dim]Check this[/dim]"
        assert console._strip_markup(text) == "Important: Check this"

    def test_get_console(self):
        """Test get_console helper function."""
        console1 = get_console()
        assert isinstance(console1, Console)

        console2 = get_console(force_plain=True)
        assert isinstance(console2, Console)
        assert console2.is_plain is True
