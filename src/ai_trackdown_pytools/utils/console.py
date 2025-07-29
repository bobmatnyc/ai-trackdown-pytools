"""Console output utilities for AI-friendly and plain output modes."""

import os
from typing import Any, Dict, List, Optional

from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.table import Table


class Console:
    """Enhanced console that supports plain output mode for AI tools."""

    def __init__(self, force_plain: bool = False):
        """Initialize console.

        Args:
            force_plain: Force plain output mode (no rich formatting)
        """
        # Check environment variables for plain mode
        self.plain_mode = (
            force_plain
            or os.getenv("AITRACKDOWN_PLAIN", "").lower() in ("1", "true", "yes")
            or os.getenv("NO_COLOR", "").lower() in ("1", "true", "yes")
            or os.getenv("CI", "").lower() in ("1", "true", "yes")
            or not os.isatty(1)  # Not a terminal (piped output)
        )

        # Create Rich console with appropriate settings
        self.rich_console = RichConsole(
            force_terminal=False if self.plain_mode else None,
            no_color=self.plain_mode,
            width=120 if self.plain_mode else None,
            legacy_windows=False,
        )

    def print(self, *args: Any, **kwargs: Any) -> None:
        """Print to console, stripping markup in plain mode."""
        if self.plain_mode and args:
            # Strip rich markup from first argument if it's a string
            if isinstance(args[0], str):
                text = self._strip_markup(args[0])
                args = (text,) + args[1:]

        self.rich_console.print(*args, **kwargs)

    def print_panel(
        self, content: str, title: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Print a panel, or plain text with title in plain mode."""
        if self.plain_mode:
            if title:
                print(f"\n{title}")
                print("-" * len(title))
            print(self._strip_markup(content))
            print()
        else:
            self.rich_console.print(Panel.fit(content, title=title, **kwargs))

    def print_table(self, table: Table) -> None:
        """Print a table, or simple text format in plain mode."""
        if self.plain_mode:
            # Convert table to simple text format
            if table.title:
                print(f"\n{table.title}")
                print("=" * len(str(table.title)))

            # Print headers
            headers = [str(col.header) for col in table.columns]
            if headers:
                print(" | ".join(headers))
                print("-" * (sum(len(h) for h in headers) + len(headers) * 3))

            # Print rows - Rich tables store cells in columns
            if table.columns and table.row_count > 0:
                # Get cells from each column
                column_cells = []
                for col in table.columns:
                    if hasattr(col, "_cells"):
                        column_cells.append(col._cells)
                    else:
                        # Fallback: try to get cells through the cells property
                        try:
                            column_cells.append(list(col.cells))
                        except Exception:
                            column_cells.append([])

                # Transpose to get rows
                if column_cells and all(column_cells):
                    for row_idx in range(table.row_count):
                        row_data = []
                        for col_idx in range(len(column_cells)):
                            if row_idx < len(column_cells[col_idx]):
                                cell_value = column_cells[col_idx][row_idx]
                                row_data.append(self._strip_markup(str(cell_value)))
                            else:
                                row_data.append("")
                        if row_data:
                            print(" | ".join(row_data))
            print()
        else:
            self.rich_console.print(table)

    def print_success(self, message: str) -> None:
        """Print success message."""
        if self.plain_mode:
            print(f"SUCCESS: {self._strip_markup(message)}")
        else:
            self.print(f"[green]✅ {message}[/green]")

    def print_error(self, message: str) -> None:
        """Print error message."""
        if self.plain_mode:
            print(f"ERROR: {self._strip_markup(message)}")
        else:
            self.print(f"[red]❌ {message}[/red]")

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        if self.plain_mode:
            print(f"WARNING: {self._strip_markup(message)}")
        else:
            self.print(f"[yellow]⚠️  {message}[/yellow]")

    def print_info(self, message: str) -> None:
        """Print info message."""
        if self.plain_mode:
            print(f"INFO: {self._strip_markup(message)}")
        else:
            self.print(f"[blue]ℹ️  {message}[/blue]")

    def _strip_markup(self, text: str) -> str:
        """Strip Rich markup from text."""
        # Simple regex-based stripping of common Rich markup
        import re

        # Remove style tags with spaces (e.g., [bold blue])
        text = re.sub(r"\[/?[a-z_\s]+\]", "", text)
        # Remove links
        text = re.sub(r"\[link[^]]*\]", "", text)
        text = re.sub(r"\[/link\]", "", text)

        return text

    @property
    def is_plain(self) -> bool:
        """Check if console is in plain mode."""
        return self.plain_mode


def get_console(force_plain: bool = False) -> Console:
    """Get a console instance.

    Args:
        force_plain: Force plain output mode

    Returns:
        Console instance
    """
    return Console(force_plain=force_plain)


def print_help_header(console: Console, app_name: str, version: str) -> None:
    """Print help header in appropriate format."""
    if console.is_plain:
        print(f"{app_name} v{version}")
        print()
    else:
        console.print(f"[bold blue]{app_name}[/bold blue] v{version}")
        console.print()


def format_option(name: str, help_text: str, default: Any = None) -> Dict[str, str]:
    """Format option for help display."""
    return {
        "name": name,
        "help": help_text,
        "default": str(default) if default is not None else "",
    }


def print_options(
    console: Console, options: List[Dict[str, str]], title: str = "Options"
) -> None:
    """Print options in appropriate format."""
    if console.is_plain:
        print(f"{title}:")
        for opt in options:
            default_text = f" (default: {opt['default']})" if opt.get("default") else ""
            print(f"  {opt['name']}: {opt['help']}{default_text}")
        print()
    else:
        table = Table(title=title, show_header=True)
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        table.add_column("Default", style="dim")

        for opt in options:
            table.add_row(opt["name"], opt["help"], opt.get("default", ""))

        console.print_table(table)
