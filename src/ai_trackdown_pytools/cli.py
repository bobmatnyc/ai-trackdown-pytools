"""Main CLI entry point for ai-trackdown-pytools."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import typer
from rich.panel import Panel
from rich.table import Table
from rich.traceback import install

from . import __version__
from .commands import (
    ai,
    bug,
    comment,
    create,
    epic,
    index,
    init,
    issue,
    migrate,
    portfolio,
    pr,
    status,
    sync,
    task,
    template,
)
from .commands import search as search_cmd
from .commands import validate_typer as validate_cmd
from .core.config import Config
from .core.project import Project
from .core.task import Task, TaskManager
from .exceptions import (
    AiTrackdownError,
    FileOperationError,
    ProjectError,
    TicketNotFoundError,
)
from .utils.console import Console, get_console
from .utils.health import check_health
from .utils.logging import setup_logging
from .utils.system import get_system_info
from .utils.tickets import infer_ticket_type, normalize_ticket_id
from .utils.validation import (
    SchemaValidator,
    validate_project_structure,
    validate_task_file,
)

# Install rich traceback handler for better error display
install(show_locals=False)

app = typer.Typer(
    name="aitrackdown",
    help="AI-powered project tracking and task management",
    context_settings={"help_option_names": ["-h", "--help"]},
    rich_markup_mode="rich",
)

# Global console instance (will be updated based on --plain flag)
console: Console = get_console()


# ============================================================================
# Helper Functions - Validation and Common Operations
# ============================================================================


def validate_project_exists(project_path: Path) -> None:
    """
    Validate that an AI Trackdown project exists at the given path.

    WHY: Centralized project validation reduces code duplication across commands.
    Each command was checking this independently, leading to repeated code.

    DESIGN DECISION: Raises typer.Exit(1) instead of returning bool to maintain
    consistent error handling pattern across CLI commands.

    Args:
        project_path: Path to check for project existence

    Raises:
        typer.Exit: If project doesn't exist
    """
    if not Project.exists(project_path):
        raise ProjectError(
            "No AI Trackdown project found in current directory",
            project_path=project_path,
            missing_components=["config", "tickets directory"],
        )


def validate_and_normalize_ticket_id(ticket_id: str) -> Tuple[str, str]:
    """
    Validate and normalize a ticket ID, returning normalized ID and ticket type.

    WHY: Multiple commands need to validate and normalize ticket IDs with the same
    error messages. Centralizing this reduces duplication and ensures consistency.

    Args:
        ticket_id: Raw ticket ID from user input

    Returns:
        Tuple of (normalized_id, ticket_type)

    Raises:
        typer.Exit: If ticket ID is invalid or type unknown
    """
    normalized_id = normalize_ticket_id(ticket_id)
    if not normalized_id:
        raise TicketNotFoundError(ticket_id, search_path=Path.cwd() / "tickets")

    ticket_type = infer_ticket_type(normalized_id)
    if not ticket_type:
        # Create a more specific error for unknown ticket type
        error = TicketNotFoundError(normalized_id, search_path=Path.cwd() / "tickets")
        error.suggestions = [
            "Valid prefixes: EP (epic), ISS (issue), TSK (task), PR (pull request), COM (comment)",
            "Check the ticket ID format: PREFIX-NUMBER (e.g., TSK-001)",
        ]
        raise error

    return normalized_id, ticket_type


def load_ticket_safely(
    task_manager: TaskManager, normalized_id: str, ticket_type: str
) -> Task:
    """
    Load a ticket with proper error handling.

    WHY: Ticket loading with error handling was repeated in many commands.
    This centralizes the loading logic and error messaging.

    Args:
        task_manager: TaskManager instance
        normalized_id: Normalized ticket ID
        ticket_type: Type of ticket for error messages

    Returns:
        Loaded Task object

    Raises:
        typer.Exit: If ticket cannot be loaded
    """
    try:
        task = task_manager.load_task(normalized_id)
        if not task:
            raise TicketNotFoundError(
                normalized_id,
                ticket_type=ticket_type,
                search_path=Path.cwd() / "tickets",
            )
        return task
    except FileNotFoundError as e:
        raise TicketNotFoundError(
            normalized_id, ticket_type=ticket_type, search_path=Path.cwd() / "tickets"
        ) from e
    except OSError as e:
        raise FileOperationError(
            f"Failed to read {ticket_type} file",
            file_path=Path.cwd()
            / "tickets"
            / ticket_type.lower()
            / f"{normalized_id}.md",
            operation="read",
            original_error=e,
        ) from e
    except Exception as e:
        # Re-raise AiTrackdownError subclasses as-is
        if isinstance(e, AiTrackdownError):
            raise
        # Wrap other exceptions
        raise FileOperationError(
            f"Unexpected error loading {ticket_type} '{normalized_id}'",
            operation="parse",
            original_error=e,
        ) from e


def update_ticket_references(
    task_manager: TaskManager,
    old_id: str,
    new_id: Optional[str] = None,
    remove_only: bool = False,
) -> list:
    """
    Update or remove ticket references in related tickets.

    WHY: Multiple commands (archive, delete, convert) need to update references
    when tickets are moved or removed. This centralizes that logic.

    Args:
        task_manager: TaskManager instance
        old_id: Original ticket ID to replace
        new_id: New ticket ID to use (if replacing)
        remove_only: If True, only remove references without replacement

    Returns:
        List of ticket IDs that were updated
    """
    all_tasks = task_manager.list_tasks()
    updated_tickets = []

    for task_item in all_tasks:
        updated = False

        # Update parent references
        if task_item.parent == old_id:
            if remove_only:
                task_item.data.parent = None
            elif new_id:
                task_item.data.parent = new_id
            updated = True

        # Update dependencies
        if old_id in task_item.dependencies:
            if remove_only:
                task_item.data.dependencies = [
                    dep for dep in task_item.dependencies if dep != old_id
                ]
            elif new_id:
                task_item.data.dependencies = [
                    new_id if dep == old_id else dep for dep in task_item.dependencies
                ]
            updated = True

        if updated:
            task_manager.save_task(task_item)
            updated_tickets.append(task_item.id)

    return updated_tickets


# ============================================================================
# Helper Functions - Display and Formatting
# ============================================================================


def display_system_info(info_data: Dict[str, Any]) -> None:
    """
    Display system information in plain or rich format.

    WHY: System info display was duplicated between info() and version() commands.
    This consolidates the formatting logic.

    Args:
        info_data: Dictionary containing system information
    """
    if console.is_plain:
        print(f"aitrackdown v{__version__}")
        print(f"Python {info_data['python_version']}")
        print(f"{info_data['platform']} {info_data['architecture']}")
    else:
        console.print_panel(
            f"""[bold blue]AI Trackdown PyTools[/bold blue] v{__version__}

[dim]System:[/dim]
• Python: {info_data['python_version']}
• Platform: {info_data['platform']} ({info_data['architecture']})

[dim]Project:[/dim]
• Git: {info_data['git_repo']}
• Config: {info_data['config_file']}""",
            title="Version",
        )


def display_ticket_details(ticket: Task, ticket_type: str, normalized_id: str) -> None:
    """
    Display ticket details in plain or rich format.

    WHY: The show() command had 100+ lines of display logic that was hard to test
    and maintain. This extracts that logic into a focused function.

    Args:
        ticket: Task object to display
        ticket_type: Type of ticket for display
        normalized_id: Normalized ticket ID
    """
    if console.is_plain:
        _display_ticket_plain(ticket, ticket_type, normalized_id)
    else:
        _display_ticket_rich(ticket, ticket_type, normalized_id)


def _display_ticket_plain(ticket: Task, ticket_type: str, normalized_id: str) -> None:
    """Display ticket in plain text format for AI tools."""
    print(f"{ticket_type.upper()}: {normalized_id}")
    print(f"Title: {ticket.title}")
    print(f"Status: {ticket.status}")
    print(f"Priority: {ticket.priority}")
    print(f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Updated: {ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

    if ticket.assignees:
        print(f"Assignees: {', '.join(ticket.assignees)}")
    if ticket.tags:
        print(f"Tags: {', '.join(ticket.tags)}")
    if ticket.parent:
        print(f"Parent: {ticket.parent}")
    if ticket.due_date:
        print(f"Due Date: {ticket.due_date.strftime('%Y-%m-%d')}")
    if ticket.estimated_hours is not None:
        print(f"Estimated Hours: {ticket.estimated_hours}")
    if ticket.actual_hours is not None:
        print(f"Actual Hours: {ticket.actual_hours}")
    if ticket.dependencies:
        print(f"Dependencies: {', '.join(ticket.dependencies)}")

    print()
    print("Description:")
    print(ticket.description or "No description provided.")

    if ticket.metadata:
        print()
        print("Metadata:")
        for key, value in ticket.metadata.items():
            print(f"  {key}: {value}")


def _display_ticket_rich(ticket: Task, ticket_type: str, normalized_id: str) -> None:
    """Display ticket with rich formatting."""
    title = f"[bold]{ticket_type.title()} {normalized_id}[/bold]: {ticket.title}"

    # Create details table
    details = Table(show_header=False, box=None, padding=(0, 1))
    details.add_column("Field", style="dim")
    details.add_column("Value")

    # Add status with color
    status_color = _get_status_color(ticket.status)
    details.add_row("Status", f"[{status_color}]{ticket.status}[/{status_color}]")

    # Add priority with color
    priority_color = _get_priority_color(ticket.priority)
    details.add_row(
        "Priority", f"[{priority_color}]{ticket.priority}[/{priority_color}]"
    )

    # Add timestamps
    details.add_row("Created", ticket.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    details.add_row("Updated", ticket.updated_at.strftime("%Y-%m-%d %H:%M:%S"))

    # Add optional fields
    _add_optional_ticket_fields(details, ticket)

    # Display main panel
    console.print_panel(title, title=ticket_type.title())
    console.print(details)

    # Add description panel if present
    if ticket.description:
        description_panel = Panel(
            ticket.description,
            title="Description",
            border_style="dim",
        )
        console.print(description_panel)

    # Add metadata table if present
    if ticket.metadata:
        _display_metadata_table(ticket.metadata)

    # Show file location
    console.print(f"\n[dim]File: {ticket.file_path}[/dim]")


def _get_status_color(status: str) -> str:
    """Get color for status display."""
    return {
        "open": "yellow",
        "in-progress": "blue",
        "done": "green",
        "closed": "green",
        "cancelled": "red",
    }.get(status.lower(), "white")


def _get_priority_color(priority: str) -> str:
    """Get color for priority display."""
    return {
        "low": "dim",
        "medium": "yellow",
        "high": "red",
        "critical": "bold red",
    }.get(priority.lower(), "white")


def _add_optional_ticket_fields(details: Table, ticket: Task) -> None:
    """Add optional fields to ticket details table."""
    if ticket.assignees:
        details.add_row("Assignees", ", ".join(ticket.assignees))
    if ticket.tags:
        details.add_row("Tags", ", ".join(f"[cyan]{tag}[/cyan]" for tag in ticket.tags))
    if ticket.parent:
        details.add_row("Parent", f"[cyan]{ticket.parent}[/cyan]")
    if ticket.due_date:
        details.add_row("Due Date", ticket.due_date.strftime("%Y-%m-%d"))
    if ticket.estimated_hours is not None:
        details.add_row("Estimated", f"{ticket.estimated_hours} hours")
    if ticket.actual_hours is not None:
        details.add_row("Actual", f"{ticket.actual_hours} hours")
    if ticket.dependencies:
        details.add_row(
            "Dependencies",
            ", ".join(f"[cyan]{dep}[/cyan]" for dep in ticket.dependencies),
        )


def _display_metadata_table(metadata: Dict[str, Any]) -> None:
    """Display metadata in a formatted table."""
    meta_table = Table(title="Metadata", show_header=True)
    meta_table.add_column("Key", style="cyan")
    meta_table.add_column("Value")

    for key, value in metadata.items():
        meta_table.add_row(key, str(value))

    console.print(meta_table)


# ============================================================================
# Helper Functions - Project and Config Operations
# ============================================================================


def setup_project_directory(project_dir: Optional[str], ctx: typer.Context) -> None:
    """
    Change to project directory if specified.

    WHY: The main() callback had complex directory handling logic that made it
    hard to test and understand. This extracts that logic.

    Args:
        project_dir: Optional project directory to change to
        ctx: Typer context for storing original directory
    """
    if not project_dir:
        return

    import os

    original_cwd = os.getcwd()

    try:
        os.chdir(project_dir)
        # Store original directory in context for cleanup
        if ctx:
            ctx.ensure_object(dict)
            ctx.obj["original_cwd"] = original_cwd
    except (FileNotFoundError, PermissionError) as e:
        console.print(
            f"[red]Error: Cannot access project directory: {project_dir}[/red]"
        )
        raise typer.Exit(1) from e


def display_config_list(config: Config) -> None:
    """Display all configuration values."""
    config_dict = config.to_dict()

    if console.is_plain:
        print(f"Config: {config.config_path or 'defaults'}")
        for k, v in config_dict.items():
            print(f"  {k}: {v}")
    else:
        console.print_panel(
            f"Configuration from: {config.config_path or 'defaults'}\n\n"
            + "\n".join([f"{k}: {v}" for k, v in config_dict.items()]),
            title="Current Configuration",
        )


def display_health_check_results(
    health_status: Dict[str, Any], title: str = "System Health"
) -> None:
    """
    Display health check results.

    WHY: Health check display was duplicated between health() and doctor() commands.

    Args:
        health_status: Health check results dictionary
        title: Title to display
    """
    if not console.is_plain:
        console.print(f"[bold]{title}[/bold]")
    else:
        print(f"{title}:")

    for check, result in health_status["checks"].items():
        if result["status"]:
            console.print_success(f"{check}: {result['message']}")
        else:
            console.print_error(f"{check}: {result['message']}")


# ============================================================================
# CLI Callbacks and Commands
# ============================================================================


def version_callback(value: bool) -> None:
    """Show version information."""
    if value:
        if console.is_plain:
            print(f"aitrackdown v{__version__}")
        else:
            console.print(f"[bold blue]AI Trackdown PyTools[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback()
def callback(
    _version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        "-p",
        help="Plain output (no colors/formatting)",
        is_eager=True,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-V",
        help="Enable verbose output",
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
    project_dir: Optional[Path] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory",
    ),
    ctx: typer.Context = typer.Option(None),
) -> None:
    """AI-powered project tracking and task management.

    Common commands:
      init project         Initialize new project
      create task "text"   Create a new task
      show ISS-001         Show any ticket details
      transition TSK-003 in-progress  Change ticket workflow state
      close TSK-003        Close any ticket
      status tasks         Show task overview
      template list        List templates

    Use --plain for AI-friendly output without formatting.
    """
    # Update global console based on plain flag
    global console
    console = get_console(force_plain=plain)

    # Setup logging based on verbosity
    setup_logging(verbose)

    # Handle project directory for anywhere-submit
    if project_dir:
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            # Store original directory in context for cleanup
            if ctx:
                ctx.ensure_object(dict)
                ctx.obj["original_cwd"] = original_cwd
        except (FileNotFoundError, PermissionError) as err:
            console.print(
                f"[red]Error: Cannot access project directory: {project_dir}[/red]"
            )
            raise typer.Exit(1) from err

    # Load configuration
    if config_file:
        Config.load(config_file)


# Add subcommands - Core functionality
app.add_typer(init.app, name="init", help="Initialize project")
app.add_typer(status.app, name="status", help="Show status")
app.add_typer(create.app, name="create", help="Create tasks/issues")
app.add_typer(template.app, name="template", help="Manage templates")
app.add_typer(validate_cmd.app, name="validate", help="Validate data")

# Add task management commands
app.add_typer(task.app, name="task", help="Task operations")
app.add_typer(issue.app, name="issue", help="Issue tracking")
app.add_typer(bug.app, name="bug", help="Bug tracking")
app.add_typer(epic.app, name="epic", help="Epic management")
app.add_typer(pr.app, name="pr", help="Pull requests")
app.add_typer(comment.app, name="comment", help="Comments")

# Add advanced functionality
app.add_typer(search_cmd.app, name="search", help="Search")
app.add_typer(index.app, name="index", help="Search index management")
app.add_typer(portfolio.app, name="portfolio", help="Portfolio mgmt")
app.add_typer(sync.app, name="sync", help="Sync platforms")
app.add_typer(ai.app, name="ai", help="AI commands")
app.add_typer(migrate.app, name="migrate", help="Migration")


@app.command()
def info() -> None:
    """Show system information."""
    info_data = get_system_info()

    if console.is_plain:
        print(f"aitrackdown v{__version__}")
        print()
        print("System:")
        print(f"  Python: {info_data['python_version']}")
        print(f"  Platform: {info_data['platform']}")
        print(f"  Architecture: {info_data['architecture']}")
        print(f"  Working Dir: {info_data['cwd']}")
        print(f"  Git Repo: {info_data['git_repo']}")
        print()
        print("Configuration:")
        print(f"  Config: {info_data['config_file']}")
        print(f"  Templates: {info_data['templates_dir']}")
        print(f"  Schema: {info_data['schema_dir']}")
    else:
        console.print_panel(
            f"""[bold]AI Trackdown PyTools[/bold] v{__version__}

[dim]System Information:[/dim]
• Python: {info_data['python_version']}
• Platform: {info_data['platform']}
• Architecture: {info_data['architecture']}
• Working Directory: {info_data['cwd']}
• Git Repository: {info_data['git_repo']}

[dim]Configuration:[/dim]
• Config File: {info_data['config_file']}
• Templates Directory: {info_data['templates_dir']}
• Schema Directory: {info_data['schema_dir']}""",
            title="System Info",
        )


@app.command()
def health() -> None:
    """Check system health."""
    health_status = check_health()

    if health_status["overall"]:
        console.print_success("System health check passed")
    else:
        console.print_error("System health check failed")

    display_health_check_results(health_status)

    if not health_status["overall"]:
        sys.exit(1)


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all"),
    _global_config: bool = typer.Option(False, "--global", "-g", help="Use global"),
) -> None:
    """View or modify configuration."""
    config_obj = Config.load()

    if list_all:
        display_config_list(config_obj)
        return

    if not key:
        # Show basic configuration info
        console.print(f"Config file: {config_obj.config_path or 'Not found'}")
        console.print(f"Project root: {config_obj.project_root or 'Not found'}")
        if not console.is_plain:
            console.print("\nUse --list to see all configuration")
        return

    if value is None:
        # Get configuration value
        val = config_obj.get(key)
        if val is not None:
            console.print(f"{key}: {val}")
        else:
            console.print_warning(f"Key '{key}' not found")
    else:
        # Set configuration value
        config_obj.set(key, value)
        config_obj.save()
        console.print_success(f"Set {key} = {value}")


@app.command()
def doctor() -> None:
    """Run system diagnostics."""
    from pathlib import Path

    from ai_trackdown_pytools.utils.health import check_health, check_project_health

    console.print_info("Running diagnostics...")
    print()  # Blank line for readability

    # System health check
    health_status = check_health()
    display_health_check_results(health_status, "System Health")
    print()

    # Project health check if in project
    project_path = Path.cwd()
    if Project.exists(project_path):
        project_health = check_project_health(project_path)
        display_health_check_results(project_health, "Project Health")
    else:
        console.print("No project found in current directory")
    print()

    # Configuration check
    _display_configuration_info()

    # Git check
    print()
    _display_git_info()


def _display_configuration_info() -> None:
    """Display configuration information for doctor command."""
    if not console.is_plain:
        console.print("[bold]Configuration[/bold]")
    else:
        print("Configuration:")

    config_obj = Config.load()
    console.print(f"  Config: {config_obj.config_path or 'Using defaults'}")
    console.print(f"  Project: {config_obj.project_root or 'Not in project'}")


def _display_git_info() -> None:
    """Display Git integration information for doctor command."""
    if not console.is_plain:
        console.print("[bold]Git Integration[/bold]")
    else:
        print("Git Integration:")
    from ai_trackdown_pytools.utils.git import GIT_AVAILABLE, GitUtils

    if GIT_AVAILABLE:
        git_utils = GitUtils()
        if git_utils.is_git_repo():
            git_status = git_utils.get_status()
            console.print_success("Git repository detected")
            console.print(f"  Branch: {git_status.get('branch', 'unknown')}")
            console.print(f"  Modified: {len(git_status.get('modified', []))} files")
        else:
            console.print("  Not a git repository")
    else:
        console.print_error("GitPython not available")


@app.command()
def version() -> None:
    """Show version info."""
    info = get_system_info()
    display_system_info(info)


@app.command()
def edit(
    task_id: str = typer.Argument(..., help="Task ID to edit"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to use"),
) -> None:
    """Edit a task file in your default editor."""
    from pathlib import Path

    from ai_trackdown_pytools.core.task import TaskManager
    from ai_trackdown_pytools.utils.editor import EditorUtils

    project_path = Path.cwd()
    validate_project_exists(project_path)

    task_manager = TaskManager(project_path)
    task = task_manager.load_task(task_id)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    if EditorUtils.open_file(task.file_path, editor):
        console.print(f"[green]Opened task {task_id} in editor[/green]")
    else:
        console.print(f"[red]Failed to open task {task_id} in editor[/red]")
        raise typer.Exit(1)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    task_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by type (task, issue, epic, pr)"
    ),
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results to show"),
) -> None:
    """Search tasks and content."""
    from pathlib import Path

    from ai_trackdown_pytools.core.task import TaskManager

    project_path = Path.cwd()
    validate_project_exists(project_path)

    task_manager = TaskManager(project_path)
    results = _search_tasks(task_manager, query, task_type, status_filter, limit)

    if not results:
        console.print(f"[yellow]No tasks found matching '{query}'[/yellow]")
        return

    _display_search_results(results, query)


def _search_tasks(
    task_manager: TaskManager,
    query: str,
    task_type: Optional[str],
    status_filter: Optional[str],
    limit: int,
) -> list:
    """
    Search for tasks matching criteria.

    WHY: The search logic was embedded in the command handler, making it hard
    to test and reuse. This extracts the search logic.
    """
    all_tasks = task_manager.list_tasks()
    matching_tasks = []
    query_lower = query.lower()

    for task_item in all_tasks:
        # Check if query matches
        if not _task_matches_query(task_item, query_lower):
            continue

        # Apply type filter
        if task_type and not _task_matches_type(task_item, task_type):
            continue

        # Apply status filter
        if status_filter and task_item.status != status_filter:
            continue

        matching_tasks.append(task_item)

        if len(matching_tasks) >= limit:
            break

    return matching_tasks


def _task_matches_query(task_item: Task, query_lower: str) -> bool:
    """Check if task matches search query."""
    return (
        query_lower in task_item.title.lower()
        or query_lower in task_item.description.lower()
        or any(query_lower in tag.lower() for tag in task_item.tags)
    )


def _task_matches_type(task_item: Task, task_type: str) -> bool:
    """Check if task matches type filter."""
    task_tags = [tag.lower() for tag in task_item.tags]
    return task_type.lower() in task_tags


def _display_search_results(results: list, query: str) -> None:
    """Display search results in a table."""
    table = Table(title=f"Search Results: '{query}' ({len(results)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Tags", style="blue")

    for task_item in results:
        table.add_row(
            task_item.id,
            _truncate_text(task_item.title, 50),
            task_item.status,
            _format_tags(task_item.tags),
        )

    console.print(table)


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to maximum length with ellipsis."""
    return text[:max_length] + "..." if len(text) > max_length else text


def _format_tags(tags: list, max_tags: int = 3) -> str:
    """Format tags for display, limiting to max_tags."""
    if len(tags) <= max_tags:
        return ", ".join(tags)
    return ", ".join(tags[:max_tags]) + "..."


@app.command()
def show(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to show (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
) -> None:
    """Show details of any ticket (epic, issue, task, or PR)."""
    from pathlib import Path

    from rich.panel import Panel
    from rich.table import Table

    from ai_trackdown_pytools.core.task import TaskManager

    project_path = Path.cwd()
    validate_project_exists(project_path)

    normalized_id, ticket_type = validate_and_normalize_ticket_id(ticket_id)

    task_manager = TaskManager(project_path)

    try:
        ticket = task_manager.load_task(normalized_id)
    except Exception as e:
        console.print_error(f"Failed to load {ticket_type} '{normalized_id}': {e}")
        raise typer.Exit(1) from e

    # Display the ticket details
    if console.is_plain:
        # Plain output for AI tools
        print(f"{ticket_type.upper()}: {normalized_id}")
        print(f"Title: {ticket.title}")
        print(f"Status: {ticket.status}")
        print(f"Priority: {ticket.priority}")
        print(f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Updated: {ticket.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if ticket.assignees:
            print(f"Assignees: {', '.join(ticket.assignees)}")
        if ticket.tags:
            print(f"Tags: {', '.join(ticket.tags)}")
        if ticket.parent:
            print(f"Parent: {ticket.parent}")
        if ticket.due_date:
            print(f"Due Date: {ticket.due_date.strftime('%Y-%m-%d')}")
        if ticket.estimated_hours is not None:
            print(f"Estimated Hours: {ticket.estimated_hours}")
        if ticket.actual_hours is not None:
            print(f"Actual Hours: {ticket.actual_hours}")
        if ticket.dependencies:
            print(f"Dependencies: {', '.join(ticket.dependencies)}")

        print()
        print("Description:")
        print(ticket.description or "No description provided.")

        if ticket.metadata:
            print()
            print("Metadata:")
            for key, value in ticket.metadata.items():
                print(f"  {key}: {value}")
    else:
        # Rich output with formatting
        title = f"[bold]{ticket_type.title()} {normalized_id}[/bold]: {ticket.title}"

        # Create details table
        details = Table(show_header=False, box=None, padding=(0, 1))
        details.add_column("Field", style="dim")
        details.add_column("Value")

        # Status with color
        status_color = {
            "open": "yellow",
            "in-progress": "blue",
            "done": "green",
            "closed": "green",
            "cancelled": "red",
        }.get(ticket.status.lower(), "white")
        details.add_row("Status", f"[{status_color}]{ticket.status}[/{status_color}]")

        # Priority with color
        priority_color = {
            "low": "dim",
            "medium": "yellow",
            "high": "red",
            "critical": "bold red",
        }.get(ticket.priority.lower(), "white")
        details.add_row(
            "Priority", f"[{priority_color}]{ticket.priority}[/{priority_color}]"
        )

        details.add_row("Created", ticket.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        details.add_row("Updated", ticket.updated_at.strftime("%Y-%m-%d %H:%M:%S"))

        if ticket.assignees:
            details.add_row("Assignees", ", ".join(ticket.assignees))
        if ticket.tags:
            details.add_row(
                "Tags", ", ".join(f"[cyan]{tag}[/cyan]" for tag in ticket.tags)
            )
        if ticket.parent:
            details.add_row("Parent", f"[cyan]{ticket.parent}[/cyan]")
        if ticket.due_date:
            details.add_row("Due Date", ticket.due_date.strftime("%Y-%m-%d"))
        if ticket.estimated_hours is not None:
            details.add_row("Estimated", f"{ticket.estimated_hours} hours")
        if ticket.actual_hours is not None:
            details.add_row("Actual", f"{ticket.actual_hours} hours")
        if ticket.dependencies:
            details.add_row(
                "Dependencies",
                ", ".join(f"[cyan]{dep}[/cyan]" for dep in ticket.dependencies),
            )

        # Main panel content
        content = details

        # Add description if present
        if ticket.description:
            description_panel = Panel(
                ticket.description,
                title="Description",
                border_style="dim",
            )
            console.print_panel(title, title=ticket_type.title())
            console.print(content)
            console.print(description_panel)
        else:
            console.print_panel(title, title=ticket_type.title())
            console.print(content)

        # Add metadata if present
        if ticket.metadata:
            meta_table = Table(title="Metadata", show_header=True)
            meta_table.add_column("Key", style="cyan")
            meta_table.add_column("Value")

            for key, value in ticket.metadata.items():
                meta_table.add_row(key, str(value))

            console.print(meta_table)

        # Show file location
        console.print(f"\n[dim]File: {ticket.file_path}[/dim]")


@app.command()
def close(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to close (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
    comment: Optional[str] = typer.Option(
        None, "--comment", "-c", help="Add a closing comment"
    ),
) -> None:
    """Close any ticket (epic, issue, task, or PR)."""
    from pathlib import Path

    from ai_trackdown_pytools.core.task import TaskManager

    project_path = Path.cwd()
    validate_project_exists(project_path)

    normalized_id, ticket_type = validate_and_normalize_ticket_id(ticket_id)

    task_manager = TaskManager(project_path)

    try:
        ticket = task_manager.load_task(normalized_id)
    except Exception as e:
        console.print_error(f"Failed to load {ticket_type} '{normalized_id}': {e}")
        raise typer.Exit(1) from e

    # Check if already closed
    if ticket.status.lower() in ["completed", "closed", "done"]:
        console.print_warning(
            f"{ticket_type.title()} '{normalized_id}' is already closed "
            f"(status: {ticket.status})"
        )
        raise typer.Exit(0)

    # Update the ticket
    update_data = _prepare_close_update_data(ticket, comment)
    success = task_manager.update_task(normalized_id, **update_data)

    if success:
        _display_close_success(ticket_type, normalized_id, ticket.title, comment)
    else:
        console.print_error(f"Failed to close {ticket_type} '{normalized_id}'")
        raise typer.Exit(1)


def _prepare_close_update_data(ticket: Task, comment: Optional[str]) -> Dict[str, Any]:
    """Prepare update data for closing a ticket."""
    update_data = {
        "status": "completed",
        "metadata": ticket.metadata.copy(),
    }

    # Add closed_at timestamp
    update_data["metadata"]["closed_at"] = datetime.now().isoformat()

    # Add closing comment if provided
    if comment:
        update_data["metadata"]["closing_comment"] = comment

    return update_data


def _prepare_transition_update_data(
    ticket: Task, state: str, new_status: str, comment: Optional[str]
) -> Dict[str, Any]:
    """Prepare update data for transitioning a ticket."""
    update_data = {
        "status": new_status,
        "metadata": ticket.metadata.copy(),
    }

    # Add transition timestamp
    state_lower = state.lower()
    update_data["metadata"][
        f"transitioned_to_{state_lower}_at"
    ] = datetime.now().isoformat()

    # For "tested" state, set special metadata
    if state_lower == "tested":
        update_data["metadata"]["tested"] = True
        update_data["metadata"]["tested_at"] = datetime.now().isoformat()

    # Add transition comment if provided
    if comment:
        update_data["metadata"][f"{state_lower}_comment"] = comment

    return update_data


def _display_close_success(
    ticket_type: str, normalized_id: str, title: str, comment: Optional[str]
) -> None:
    """Display success message for closing a ticket."""
    if console.is_plain:
        print(f"Closed {ticket_type} {normalized_id}")
        if comment:
            print(f"Comment: {comment}")
    else:
        console.print_success(
            f"✅ Closed {ticket_type} [cyan]{normalized_id}[/cyan]: {title}"
        )
        if comment:
            console.print(f"  Comment: {comment}")


@app.command()
def transition(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to transition (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
    state: str = typer.Argument(
        ..., help="New workflow state: waiting, in-progress, ready, tested"
    ),
    comment: Optional[str] = typer.Option(
        None, "--comment", "-c", help="Add a transition comment"
    ),
) -> None:
    """Transition any ticket to a new workflow state."""
    from pathlib import Path

    from ai_trackdown_pytools.core.task import TaskManager

    project_path = Path.cwd()
    validate_project_exists(project_path)

    normalized_id, ticket_type = validate_and_normalize_ticket_id(ticket_id)

    # Check if this is a comment (comments don't have status/workflow)
    if normalized_id.startswith("COM-"):
        console.print_error("Comments do not have status or workflow states")
        console.print_info("Comments are append-only and cannot be transitioned")
        raise typer.Exit(1)

    # Validate and map workflow state
    new_status = _validate_workflow_state(state)

    task_manager = TaskManager(project_path)
    ticket = load_ticket_safely(task_manager, normalized_id, ticket_type)

    # Update the ticket
    old_status = ticket.status
    update_data = _prepare_transition_update_data(ticket, state, new_status, comment)
    success = task_manager.update_task(normalized_id, **update_data)

    if success:
        _display_transition_success(
            ticket_type,
            normalized_id,
            ticket.title,
            old_status,
            state,
            new_status,
            comment,
        )
    else:
        console.print_error(f"Failed to transition {ticket_type} '{normalized_id}'")
        raise typer.Exit(1)


def _validate_workflow_state(state: str) -> str:
    """Validate workflow state and return internal status."""
    workflow_states = {
        "waiting": "open",
        "in-progress": "in_progress",
        "ready": "completed",
        "tested": "completed",
    }

    state_lower = state.lower()
    if state_lower not in workflow_states:
        console.print_error(f"Invalid workflow state: {state}")
        console.print_info("Valid workflow states: waiting, in-progress, ready, tested")
        raise typer.Exit(1)

    return workflow_states[state_lower]


def _display_transition_success(
    ticket_type: str,
    normalized_id: str,
    title: str,
    old_status: str,
    state: str,
    new_status: str,
    comment: Optional[str],
) -> None:
    """Display success message for transitioning a ticket."""
    if console.is_plain:
        print(
            f"Transitioned {ticket_type} {normalized_id} from '{old_status}' "
            f"to '{state}' (internal: {new_status})"
        )
        if comment:
            print(f"Comment: {comment}")
    else:
        console.print_success(
            f"✅ Transitioned {ticket_type} [cyan]{normalized_id}[/cyan]"
        )
        console.print(f"   {title}")
        console.print(
            f"   [dim]Status:[/dim] {old_status} → [green]{state}[/green] "
            f"(internal: {new_status})"
        )
        if comment:
            console.print(f"   [dim]Comment:[/dim] {comment}")


@app.command()
def archive(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to archive (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
) -> None:
    """Archive any ticket by moving it to an archive subdirectory."""

    from ai_trackdown_pytools.core.project import Project
    from ai_trackdown_pytools.core.task import TaskManager
    from ai_trackdown_pytools.utils.tickets import (
        infer_ticket_type,
        normalize_ticket_id,
    )

    project_path = Path.cwd()
    if not Project.exists(project_path):
        console.print_error("No AI Trackdown project found")
        raise typer.Exit(1)

    # Normalize the ticket ID (convert to uppercase prefix)
    normalized_id = normalize_ticket_id(ticket_id)
    if not normalized_id:
        console.print_error(f"Invalid ticket ID format: {ticket_id}")
        console.print_info("Valid formats: EP-001, ISS-002, TSK-003, PR-004, COM-005")
        raise typer.Exit(1)

    # Infer the ticket type
    ticket_type = infer_ticket_type(normalized_id)
    if not ticket_type:
        console.print_error(f"Unknown ticket type for ID: {ticket_id}")
        console.print_info(
            "Valid prefixes: EP (epic), ISS (issue), TSK (task), PR (pull request), COM (comment)"
        )
        raise typer.Exit(1)

    # Load the ticket using TaskManager
    task_manager = TaskManager(project_path)

    try:
        ticket = task_manager.load_task(normalized_id)
    except Exception as e:
        console.print_error(f"Failed to load {ticket_type} '{normalized_id}': {e}")
        raise typer.Exit(1) from e

    # Determine archive directory structure
    # Map ticket types to archive subdirectories
    type_dir_map = {
        "epic": "epics",
        "issue": "issues",
        "task": "tasks",
        "pr": "prs",
        "comment": "comments",
    }

    type_subdir = type_dir_map.get(ticket_type, "misc")
    archive_dir = task_manager.tasks_dir / type_subdir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_file_path = archive_dir / ticket.file_path.name

    try:
        ticket.file_path.rename(archive_file_path)
        return archive_file_path
    except Exception as e:
        console.print_error(f"Failed to archive {ticket_type} '{normalized_id}': {e}")
        raise typer.Exit(1) from e


def _handle_archive_references(
    task_manager: TaskManager, normalized_id: str, ticket: Task
) -> None:
    """Update references when archiving a ticket."""
    # Update parent references if this is a child ticket
    if ticket.parent:
        try:
            parent_task = task_manager.load_task(ticket.parent)
            if normalized_id in parent_task.dependencies:
                parent_task.dependencies.remove(normalized_id)
                task_manager.save_task(parent_task)
        except Exception:
            pass  # Parent might not exist or be accessible

    # Update child references if this ticket has children
    all_tasks = task_manager.list_tasks()
    for task_item in all_tasks:
        if task_item.parent == normalized_id:
            task_item.data.parent = None
            task_manager.save_task(task_item)


def _display_archive_success(
    ticket_type: str,
    normalized_id: str,
    title: str,
    archive_path: Path,
    project_path: Path,
) -> None:
    """Display success message for archiving a ticket."""
    if console.is_plain:
        print(f"Archived {ticket_type} {normalized_id}")
        print(f"Moved to: {archive_path.relative_to(project_path)}")
    else:
        console.print_success(
            f"✅ Archived {ticket_type} [cyan]{normalized_id}[/cyan]: {title}"
        )
        console.print(
            f"   [dim]Moved to:[/dim] {archive_path.relative_to(project_path)}"
        )


@app.command()
def convert(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to convert (e.g., TSK-001, ISS-002, EP-003)"
    ),
    to_type: str = typer.Option(
        ..., "--to", help="Target ticket type (task, issue, or epic)"
    ),
    archive: bool = typer.Option(
        True, "--archive/--no-archive", help="Archive original ticket after conversion"
    ),
) -> None:
    """Convert a ticket from one type to another.

    Supports conversions:
    - task <-> issue (bidirectional)
    - issue <-> epic (bidirectional)

    All metadata is preserved during conversion.
    The original ticket is archived by default.

    Examples:
        aitrackdown convert TSK-001 --to issue
        aitrackdown convert ISS-002 --to epic
        aitrackdown convert EP-003 --to issue
        aitrackdown convert ISS-004 --to task --no-archive
    """
    project_path = Path.cwd()
    validate_project_exists(project_path)

    normalized_id, source_type = validate_and_normalize_ticket_id(ticket_id)

    # Validate conversion
    target_type_lower = _validate_conversion(source_type, to_type)

    task_manager = TaskManager(project_path)
    source_ticket = load_ticket_safely(task_manager, normalized_id, source_type)

    # Perform conversion
    new_ticket = _create_converted_ticket(
        task_manager, source_ticket, source_type, target_type_lower
    )

    # Update references
    references_updated = update_ticket_references(
        task_manager, normalized_id, new_ticket.id
    )

    # Handle original ticket
    if archive:
        _archive_original_ticket(task_manager, source_ticket, source_type)
    else:
        task_manager.delete_task(normalized_id)

    # Display success
    _display_conversion_success(
        source_type,
        normalized_id,
        target_type_lower,
        new_ticket,
        archive,
        references_updated,
        project_path,
    )


def _validate_conversion(source_type: str, to_type: str) -> str:
    """Validate ticket type conversion."""
    target_type_lower = to_type.lower()
    valid_target_types = ["task", "issue", "epic"]

    if target_type_lower not in valid_target_types:
        console.print_error(f"Invalid target type: {to_type}")
        console.print_info(f"Valid target types: {', '.join(valid_target_types)}")
        raise typer.Exit(1)

    # Check for valid conversion paths
    valid_conversions = {
        ("task", "issue"),
        ("issue", "task"),
        ("issue", "epic"),
        ("epic", "issue"),
    }

    conversion = (source_type, target_type_lower)
    if conversion not in valid_conversions:
        console.print_error(f"Invalid conversion: {source_type} -> {target_type_lower}")
        console.print_info("Valid conversions:")
        console.print_info("  - task <-> issue")
        console.print_info("  - issue <-> epic")
        raise typer.Exit(1)

    # Don't convert to same type
    if source_type == target_type_lower:
        console.print_warning(f"Ticket is already a {source_type}")
        raise typer.Exit(0)

    return target_type_lower


def _create_converted_ticket(
    task_manager: TaskManager, source_ticket: Task, source_type: str, target_type: str
) -> Task:
    """Create a new ticket from conversion."""
    new_ticket_data = {
        "type": target_type,
        "title": source_ticket.title,
        "description": source_ticket.description,
        "status": source_ticket.status,
        "priority": source_ticket.priority,
        "assignees": source_ticket.assignees,
        "tags": source_ticket.tags,
        "due_date": source_ticket.due_date,
        "estimated_hours": source_ticket.estimated_hours,
        "actual_hours": source_ticket.actual_hours,
        "dependencies": source_ticket.dependencies,
        "parent": source_ticket.parent,
        "labels": source_ticket.labels,
        "metadata": source_ticket.metadata.copy(),
    }

    # Add conversion metadata
    now = datetime.now()
    new_ticket_data["metadata"]["converted_from"] = source_ticket.id
    new_ticket_data["metadata"]["converted_from_type"] = source_type
    new_ticket_data["metadata"]["converted_at"] = now.isoformat()
    new_ticket_data["metadata"]["conversion"] = f"{source_type} -> {target_type}"
    new_ticket_data["metadata"][
        "original_created_at"
    ] = source_ticket.created_at.isoformat()

    try:
        return task_manager.create_task(**new_ticket_data)
    except Exception as e:
        console.print_error(f"Failed to create converted ticket: {e}")
        raise typer.Exit(1) from e


def _archive_original_ticket(
    task_manager: TaskManager, source_ticket: Task, source_type: str
) -> Path:
    """Archive the original ticket after conversion."""
    type_dir_map = {
        "epic": "epics",
        "issue": "issues",
        "task": "tasks",
        "pr": "prs",
        "comment": "comments",
    }

    type_subdir = type_dir_map.get(source_type, "misc")
    archive_dir = task_manager.tasks_dir / type_subdir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_file_path = archive_dir / source_ticket.file_path.name
    source_ticket.file_path.rename(archive_file_path)

    return archive_file_path


def _display_conversion_success(
    source_type: str,
    normalized_id: str,
    target_type: str,
    new_ticket: Task,
    archived: bool,
    references_updated: list,
    project_path: Path,
) -> None:
    """Display success message for ticket conversion."""
    if console.is_plain:
        print(
            f"Converted {source_type} {normalized_id} to {target_type} {new_ticket.id}"
        )
        if archived:
            print("Original ticket archived")
        else:
            print("Original ticket deleted (not archived)")
        if references_updated:
            print(f"Updated references in: {', '.join(references_updated)}")
    else:
        console.print_success(
            f"✅ Converted {source_type} [cyan]{normalized_id}[/cyan] "
            f"to {target_type} [green]{new_ticket.id}[/green]"
        )
        console.print(f"   Title: {new_ticket.title}")

        if archived:
            console.print("   [dim]Original ticket archived[/dim]")
        else:
            console.print("   [dim]Original ticket deleted (not archived)[/dim]")

        if references_updated:
            console.print(f"   [dim]Updated {len(references_updated)} references[/dim]")

        console.print(
            f"\n[dim]New ticket file:[/dim] "
            f"{new_ticket.file_path.relative_to(project_path)}"
        )


@app.command()
def delete(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to delete (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Permanently delete any ticket (with confirmation)."""
    from pathlib import Path

    from ai_trackdown_pytools.core.task import TaskManager

    project_path = Path.cwd()
    validate_project_exists(project_path)

    normalized_id, ticket_type = validate_and_normalize_ticket_id(ticket_id)

    task_manager = TaskManager(project_path)

    try:
        ticket = task_manager.load_task(normalized_id)
    except Exception as e:
        console.print_error(f"Failed to load {ticket_type} '{normalized_id}': {e}")
        raise typer.Exit(1) from e

    # Show ticket details and ask for confirmation
    if not force:
        if console.is_plain:
            print(f"\n{ticket_type.upper()}: {normalized_id}")
            print(f"Title: {ticket.title}")
            print(f"Status: {ticket.status}")
            print(f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if ticket.parent:
                print(f"Parent: {ticket.parent}")
            print(f"\nThis will permanently delete the {ticket_type}.")
            response = input("Are you sure? Type 'yes' to confirm: ")
        else:
            console.print_panel(
                f"[bold red]⚠️  WARNING: Permanent Deletion[/bold red]\n\n"
                f"[bold]{ticket_type.title()} {normalized_id}[/bold]: {ticket.title}\n"
                f"Status: {ticket.status}\n"
                f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                + (f"Parent: {ticket.parent}\n" if ticket.parent else "")
                + "\n[red]This action cannot be undone![/red]",
                title="Delete Confirmation",
                border_style="red",
            )
            response = typer.prompt(
                "Are you sure you want to delete this ticket? Type 'yes' to confirm",
                default="no",
            )

        if response.lower() != "yes":
            console.print_info("Deletion cancelled")
            raise typer.Exit(0)

    # Update any parent references if this is a child ticket
    if ticket.parent:
        try:
            parent_task = task_manager.load_task(ticket.parent)
            # Remove this task from parent's dependencies if present
            if normalized_id in parent_task.dependencies:
                parent_task.dependencies.remove(normalized_id)
                task_manager.save_task(parent_task)
        except Exception:
            # Parent might not exist or be accessible
            pass

    # Update any child references if this ticket has children
    all_tasks = task_manager.list_tasks()
    children_updated = []
    for task_item in all_tasks:
        if task_item.parent == normalized_id:
            # Update child to have no parent
            task_item.data.parent = None
            task_manager.save_task(task_item)
            children_updated.append(task_item.id)

    # Delete the ticket
    success = task_manager.delete_task(normalized_id)

    if success:
        _display_delete_success(
            ticket_type, normalized_id, ticket.title, children_updated
        )
    else:
        console.print_error(f"Failed to delete {ticket_type} '{normalized_id}'")
        raise typer.Exit(1)


def _confirm_deletion(ticket: Task, ticket_type: str, normalized_id: str) -> bool:
    """Prompt user to confirm deletion."""
    if console.is_plain:
        print(f"\n{ticket_type.upper()}: {normalized_id}")
        print(f"Title: {ticket.title}")
        print(f"Status: {ticket.status}")
        print(f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if ticket.parent:
            print(f"Parent: {ticket.parent}")
        print(f"\nThis will permanently delete the {ticket_type}.")
        response = input("Are you sure? Type 'yes' to confirm: ")
    else:
        console.print_panel(
            f"[bold red]⚠️  WARNING: Permanent Deletion[/bold red]\n\n"
            f"[bold]{ticket_type.title()} {normalized_id}[/bold]: {ticket.title}\n"
            f"Status: {ticket.status}\n"
            f"Created: {ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            + (f"Parent: {ticket.parent}\n" if ticket.parent else "")
            + "\n[red]This action cannot be undone![/red]",
            title="Delete Confirmation",
            border_style="red",
        )
        response = typer.prompt(
            "Are you sure you want to delete this ticket? Type 'yes' to confirm",
            default="no",
        )

    return response.lower() == "yes"


def _display_delete_success(
    ticket_type: str, normalized_id: str, title: str, children_updated: list
) -> None:
    """Display success message for deleting a ticket."""
    if console.is_plain:
        print(f"Deleted {ticket_type} {normalized_id}")
        if children_updated:
            print(f"Updated children: {', '.join(children_updated)}")
    else:
        console.print_success(
            f"✅ Permanently deleted {ticket_type} [cyan]{normalized_id}[/cyan]: {title}"
        )
        if children_updated:
            console.print(
                f"   [dim]Updated {len(children_updated)} child tickets[/dim]"
            )


@app.command()
def validate(
    target: Optional[str] = typer.Argument(
        None, help="What to validate (project, task, config, template)"
    ),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Path to validate"),
    _fix: bool = typer.Option(
        False, "--fix", "-f", help="Attempt to fix validation issues"
    ),
) -> None:
    """Validate project structure, tasks, or configuration."""



    if not target:
        target = "project"

    if target == "project":
        _validate_project(path, _fix)
    elif target == "tasks":
        _validate_tasks(path)
    elif target == "config":
        _validate_config()
    else:
        console.print(f"[red]Unknown validation target: {target}[/red]")
        console.print("Valid targets: project, tasks, config")
        raise typer.Exit(1)


def _validate_project(path: Optional[str], fix: bool) -> None:  # noqa: ARG001
    """Validate project structure."""
    # TODO: Implement fix functionality
    project_path = Path(path) if path else Path.cwd()
    validate_project_exists(project_path)

    console.print(f"[blue]Validating project at {project_path}[/blue]\n")

    result = validate_project_structure(project_path)

    if result["valid"]:
        console.print("[green]✅ Project structure is valid[/green]")
    else:
        console.print("[red]❌ Project structure validation failed[/red]")
        for error in result["errors"]:
            console.print(f"  • [red]{error}[/red]")

    if result["warnings"]:
        console.print("\n[yellow]⚠️  Warnings:[/yellow]")
        for warning in result["warnings"]:
            console.print(f"  • [yellow]{warning}[/yellow]")


def _validate_tasks(path: Optional[str]) -> None:
    """Validate all tasks in project."""
    project_path = Path(path) if path else Path.cwd()
    validate_project_exists(project_path)

    task_manager = TaskManager(project_path)
    tasks = task_manager.list_tasks()

    console.print(f"[blue]Validating {len(tasks)} tasks[/blue]\n")

    table = Table(title="Task Validation Results")
    table.add_column("Task ID", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Issues", style="red")

    total_errors = 0
    total_warnings = 0

    for task_item in tasks:
        result = validate_task_file(task_item.file_path)

        status = "✅ Valid" if result["valid"] else "❌ Invalid"
        issues = []

        if result["errors"]:
            issues.extend([f"Error: {e}" for e in result["errors"]])
            total_errors += len(result["errors"])

        if result["warnings"]:
            issues.extend([f"Warning: {w}" for w in result["warnings"]])
            total_warnings += len(result["warnings"])

        table.add_row(task_item.id, status, "\n".join(issues) if issues else "None")

    console.print(table)
    console.print(f"\nSummary: {total_errors} errors, {total_warnings} warnings")


def _validate_config() -> None:
    """Validate configuration."""
    config = Config.load()
    validator = SchemaValidator()

    console.print("[blue]Validating configuration[/blue]\n")

    result = validator.validate_config(config.to_dict())

    if result["valid"]:
        console.print("[green]✅ Configuration is valid[/green]")
    else:
        console.print("[red]❌ Configuration validation failed[/red]")
        for error in result["errors"]:
            console.print(f"  • [red]{error}[/red]")

    if result["warnings"]:
        console.print("\n[yellow]⚠️  Warnings:[/yellow]")
        for warning in result["warnings"]:
            console.print(f"  • [yellow]{warning}[/yellow]")


def run_cli() -> None:
    """Main entry point with enhanced error handling.

    WHY: Provides user-friendly error messages with actionable suggestions
    based on the specific exception type. This improves the user experience
    by helping them understand and resolve issues quickly.
    """
    try:
        app()
    except KeyboardInterrupt:
        if console and hasattr(console, "print_warning"):
            console.print_warning("\nOperation cancelled")
        else:
            print("\nOperation cancelled")
        sys.exit(1)
    except AiTrackdownError as e:
        # Handle our custom exceptions with rich error information
        if console and hasattr(console, "print_error"):
            console.print_error(f"\n{e.message}")

            # Print context if available
            if e.context:
                console.print_info("Details:")
                for key, value in e.context.items():
                    console.print_info(f"  {key}: {value}")

            # Print suggestions if available
            if e.suggestions:
                console.print_info("\nHow to fix:")
                for suggestion in e.suggestions:
                    console.print_info(f"  • {suggestion}")

            if not console.is_plain:
                console.print("\nFor more help: [cyan]aitrackdown doctor[/cyan]")
        else:
            print(f"\nError: {e}")
        sys.exit(1)
    except Exception as e:
        # Handle unexpected exceptions
        if console and hasattr(console, "print_error"):
            console.print_error(f"\nUnexpected error: {e}")
            console.print_info("\nThis appears to be an unexpected error.")
            console.print_info("Please report this issue with the following details:")
            console.print_info(f"  • Error type: {type(e).__name__}")
            console.print_info(f"  • Error message: {str(e)}")
            console.print_info("  • Command that caused the error")

            if not console.is_plain:
                console.print("\nFor diagnostics: [cyan]aitrackdown doctor[/cyan]")
                console.print(
                    "For debug mode: [cyan]aitrackdown --debug <command>[/cyan]"
                )
        else:
            print(f"\nUnexpected error: {e}")
        sys.exit(1)


def main():
    """Main entry point for the CLI."""
    run_cli()


if __name__ == "__main__":
    main()
