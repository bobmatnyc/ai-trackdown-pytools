"""Main CLI entry point for ai-trackdown-pytools."""

import sys
from typing import Optional
from pathlib import Path

import typer

# from rich.console import Console as RichConsole
# from rich.panel import Panel
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
    search as search_cmd,
    status,
    sync,
    task,
    template,
)
from .commands import validate_typer as validate_cmd
from .core.config import Config
from .utils.logging import setup_logging
from .utils.console import get_console, Console

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


def version_callback(value: bool) -> None:
    """Show version information."""
    if value:
        if console.is_plain:
            print(f"aitrackdown v{__version__}")
        else:
            console.print(f"[bold blue]AI Trackdown PyTools[/bold blue] v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
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
    config_file: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file",
    ),
    project_dir: Optional[str] = typer.Option(
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
        except (FileNotFoundError, PermissionError):
            console.print(
                f"[red]Error: Cannot access project directory: {project_dir}[/red]"
            )
            raise typer.Exit(1)

    # Load configuration
    if config_file:
        Config.load(Path(config_file))


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
    from ai_trackdown_pytools.utils.system import get_system_info

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
    from ai_trackdown_pytools.utils.health import check_health

    health_status = check_health()

    if health_status["overall"]:
        console.print_success("System health check passed")
    else:
        console.print_error("System health check failed")

    for check, result in health_status["checks"].items():
        if result["status"]:
            console.print_success(f"{check}: {result['message']}")
        else:
            console.print_error(f"{check}: {result['message']}")

    if not health_status["overall"]:
        sys.exit(1)


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Config key"),
    value: Optional[str] = typer.Argument(None, help="Config value"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all"),
    global_config: bool = typer.Option(False, "--global", "-g", help="Use global"),
) -> None:
    """View or modify configuration."""
    config = Config.load()

    if list_all:
        # Show all configuration
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
        return

    if not key:
        # Show basic configuration info
        console.print(f"Config file: {config.config_path or 'Not found'}")
        console.print(f"Project root: {config.project_root or 'Not found'}")
        if not console.is_plain:
            console.print("\nUse --list to see all configuration")
        return

    if value is None:
        # Get configuration value
        val = config.get(key)
        if val is not None:
            console.print(f"{key}: {val}")
        else:
            console.print_warning(f"Key '{key}' not found")
    else:
        # Set configuration value
        config.set(key, value)
        config.save()
        console.print_success(f"Set {key} = {value}")


@app.command()
def doctor() -> None:
    """Run system diagnostics."""
    from ai_trackdown_pytools.utils.health import check_health, check_project_health
    from pathlib import Path

    console.print_info("Running diagnostics...")
    print()  # Blank line for readability

    # System health check
    if not console.is_plain:
        console.print("[bold]System Health[/bold]")
    else:
        print("System Health:")

    health_status = check_health()

    for check, result in health_status["checks"].items():
        if result["status"]:
            console.print_success(f"{check}: {result['message']}")
        else:
            console.print_error(f"{check}: {result['message']}")

    print()

    # Project health check if in project
    project_path = Path.cwd()
    from ai_trackdown_pytools.core.project import Project

    if Project.exists(project_path):
        if not console.is_plain:
            console.print("[bold]Project Health[/bold]")
        else:
            print("Project Health:")

        project_health = check_project_health(project_path)

        for check, result in project_health["checks"].items():
            if result["status"]:
                console.print_success(f"{check}: {result['message']}")
            else:
                console.print_error(f"{check}: {result['message']}")
    else:
        console.print("No project found in current directory")

    print()

    # Configuration check
    if not console.is_plain:
        console.print("[bold]Configuration[/bold]")
    else:
        print("Configuration:")
    config = Config.load()
    console.print(f"  Config: {config.config_path or 'Using defaults'}")
    console.print(f"  Project: {config.project_root or 'Not in project'}")

    # Git check
    print()
    if not console.is_plain:
        console.print("[bold]Git Integration[/bold]")
    else:
        print("Git Integration:")
    from ai_trackdown_pytools.utils.git import GitUtils, GIT_AVAILABLE

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
    from ai_trackdown_pytools.utils.system import get_system_info

    info = get_system_info()

    if console.is_plain:
        print(f"aitrackdown v{__version__}")
        print(f"Python {info['python_version']}")
        print(f"{info['platform']} {info['architecture']}")
    else:
        console.print_panel(
            f"""[bold blue]AI Trackdown PyTools[/bold blue] v{__version__}

[dim]System:[/dim]
• Python: {info['python_version']}
• Platform: {info['platform']} ({info['architecture']})

[dim]Project:[/dim]
• Git: {info['git_repo']}
• Config: {info['config_file']}""",
            title="Version",
        )


@app.command()
def edit(
    task_id: str = typer.Argument(..., help="Task ID to edit"),
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Editor to use"),
) -> None:
    """Edit a task file in your default editor."""
    from pathlib import Path
    from ai_trackdown_pytools.core.project import Project
    from ai_trackdown_pytools.core.task import TaskManager
    from ai_trackdown_pytools.utils.editor import EditorUtils

    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

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
    from ai_trackdown_pytools.core.project import Project
    from ai_trackdown_pytools.core.task import TaskManager
    from rich.table import Table

    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Simple text search in title and description
    matching_tasks = []
    query_lower = query.lower()

    for task_item in all_tasks:
        if (
            query_lower in task_item.title.lower()
            or query_lower in task_item.description.lower()
            or any(query_lower in tag.lower() for tag in task_item.tags)
        ):

            # Apply filters
            if task_type:
                task_tags = [tag.lower() for tag in task_item.tags]
                if task_type.lower() not in task_tags:
                    continue

            if status_filter and task_item.status != status_filter:
                continue

            matching_tasks.append(task_item)

    matching_tasks = matching_tasks[:limit]

    if not matching_tasks:
        console.print(f"[yellow]No tasks found matching '{query}'[/yellow]")
        return

    table = Table(title=f"Search Results: '{query}' ({len(matching_tasks)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Tags", style="blue")

    for task_item in matching_tasks:
        table.add_row(
            task_item.id,
            (
                task_item.title[:50] + "..."
                if len(task_item.title) > 50
                else task_item.title
            ),
            task_item.status,
            ", ".join(task_item.tags[:3]) + ("..." if len(task_item.tags) > 3 else ""),
        )

    console.print(table)


@app.command()
def show(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to show (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
) -> None:
    """Show details of any ticket (epic, issue, task, or PR)."""
    from pathlib import Path
    from ai_trackdown_pytools.core.project import Project
    from ai_trackdown_pytools.core.task import TaskManager
    from ai_trackdown_pytools.utils.tickets import (
        infer_ticket_type,
        normalize_ticket_id,
    )
    from rich.panel import Panel
    from rich.table import Table

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
        raise typer.Exit(1)

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
    from datetime import datetime
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
        raise typer.Exit(1)

    # Check if already closed
    if ticket.status.lower() in ["completed", "closed", "done"]:
        console.print_warning(
            f"{ticket_type.title()} '{normalized_id}' is already closed (status: {ticket.status})"
        )
        raise typer.Exit(0)

    # Update the ticket
    update_data = {
        "status": "completed",
        "metadata": ticket.metadata.copy(),  # Copy existing metadata
    }

    # Add closed_at timestamp to metadata
    update_data["metadata"]["closed_at"] = datetime.now().isoformat()

    # Add closing comment if provided
    if comment:
        update_data["metadata"]["closing_comment"] = comment

    # Update the ticket
    success = task_manager.update_task(normalized_id, **update_data)

    if success:
        if console.is_plain:
            print(f"Closed {ticket_type} {normalized_id}")
            if comment:
                print(f"Comment: {comment}")
        else:
            console.print_success(
                f"✅ Closed {ticket_type} [cyan]{normalized_id}[/cyan]: {ticket.title}"
            )
            if comment:
                console.print(f"  Comment: {comment}")
    else:
        console.print_error(f"Failed to close {ticket_type} '{normalized_id}'")
        raise typer.Exit(1)


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
    from datetime import datetime
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

    # Check if this is a comment (comments don't have status/workflow)
    if normalized_id.startswith("COM-"):
        console.print_error("Comments do not have status or workflow states")
        console.print_info("Comments are append-only and cannot be transitioned")
        raise typer.Exit(1)

    # Validate workflow state
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

    # Load the ticket using TaskManager
    task_manager = TaskManager(project_path)

    try:
        ticket = task_manager.load_task(normalized_id)
    except Exception as e:
        console.print_error(f"Failed to load {ticket_type} '{normalized_id}': {e}")
        raise typer.Exit(1)

    # Get the old status for display
    old_status = ticket.status

    # Map workflow state to internal status
    new_status = workflow_states[state_lower]

    # Prepare update data
    update_data = {
        "status": new_status,
        "metadata": ticket.metadata.copy(),  # Copy existing metadata
    }

    # Add transition timestamp to metadata
    update_data["metadata"][
        f"transitioned_to_{state_lower}_at"
    ] = datetime.now().isoformat()

    # For "tested" state, set a special metadata flag
    if state_lower == "tested":
        update_data["metadata"]["tested"] = True
        update_data["metadata"]["tested_at"] = datetime.now().isoformat()

    # Add transition comment if provided
    if comment:
        update_data["metadata"][f"transition_{state_lower}_comment"] = comment

    # Update the ticket
    success = task_manager.update_task(normalized_id, **update_data)

    if success:
        if console.is_plain:
            print(
                f"Transitioned {ticket_type} {normalized_id} from '{old_status}' to '{state}' (internal: {new_status})"
            )
            if comment:
                print(f"Comment: {comment}")
        else:
            console.print_success(
                f"✅ Transitioned {ticket_type} [cyan]{normalized_id}[/cyan]"
            )
            console.print(f"   {ticket.title}")
            console.print(
                f"   [dim]Status:[/dim] {old_status} → [green]{state}[/green] (internal: {new_status})"
            )
            if comment:
                console.print(f"   [dim]Comment:[/dim] {comment}")
    else:
        console.print_error(f"Failed to transition {ticket_type} '{normalized_id}'")
        raise typer.Exit(1)


@app.command()
def archive(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to archive (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
) -> None:
    """Archive any ticket by moving it to an archive subdirectory."""
    from pathlib import Path
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
        raise typer.Exit(1)

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

    # Create new file path in archive
    archive_file_path = archive_dir / ticket.file_path.name

    # Check if already archived
    if ticket.file_path.parent.name == "archive":
        console.print_warning(
            f"{ticket_type.title()} '{normalized_id}' is already archived"
        )
        raise typer.Exit(0)

    # Move the file
    try:
        ticket.file_path.rename(archive_file_path)

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
        for task in all_tasks:
            if task.parent == normalized_id:
                # Update child to have no parent
                task.data.parent = None
                task_manager.save_task(task)

        if console.is_plain:
            print(f"Archived {ticket_type} {normalized_id}")
            print(f"Moved to: {archive_file_path.relative_to(project_path)}")
        else:
            console.print_success(
                f"✅ Archived {ticket_type} [cyan]{normalized_id}[/cyan]: {ticket.title}"
            )
            console.print(
                f"   [dim]Moved to:[/dim] {archive_file_path.relative_to(project_path)}"
            )

    except Exception as e:
        console.print_error(f"Failed to archive {ticket_type} '{normalized_id}': {e}")
        raise typer.Exit(1)


@app.command()
def delete(
    ticket_id: str = typer.Argument(
        ..., help="Ticket ID to delete (any type: EP-001, ISS-002, TSK-003, PR-004)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """Permanently delete any ticket (with confirmation)."""
    from pathlib import Path
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
        raise typer.Exit(1)

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
    for task in all_tasks:
        if task.parent == normalized_id:
            # Update child to have no parent
            task.data.parent = None
            task_manager.save_task(task)
            children_updated.append(task.id)

    # Delete the ticket
    success = task_manager.delete_task(normalized_id)

    if success:
        if console.is_plain:
            print(f"Deleted {ticket_type} {normalized_id}")
            if children_updated:
                print(f"Updated children: {', '.join(children_updated)}")
        else:
            console.print_success(
                f"✅ Permanently deleted {ticket_type} [cyan]{normalized_id}[/cyan]: {ticket.title}"
            )
            if children_updated:
                console.print(
                    f"   [dim]Updated {len(children_updated)} child tickets[/dim]"
                )
    else:
        console.print_error(f"Failed to delete {ticket_type} '{normalized_id}'")
        raise typer.Exit(1)


@app.command()
def validate(
    target: Optional[str] = typer.Argument(
        None, help="What to validate (project, task, config, template)"
    ),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Path to validate"),
    fix: bool = typer.Option(
        False, "--fix", "-f", help="Attempt to fix validation issues"
    ),
) -> None:
    """Validate project structure, tasks, or configuration."""
    from pathlib import Path
    from ai_trackdown_pytools.utils.validation import (
        validate_project_structure,
        validate_task_file,
        SchemaValidator,
    )
    from ai_trackdown_pytools.core.project import Project
    from ai_trackdown_pytools.core.task import TaskManager
    from rich.table import Table

    if not target:
        # Default: validate current project
        target = "project"

    if target == "project":
        project_path = Path(path) if path else Path.cwd()

        if not Project.exists(project_path):
            console.print(f"[red]No AI Trackdown project found at {project_path}[/red]")
            raise typer.Exit(1)

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

    elif target == "tasks":
        project_path = Path(path) if path else Path.cwd()

        if not Project.exists(project_path):
            console.print(f"[red]No AI Trackdown project found at {project_path}[/red]")
            raise typer.Exit(1)

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

    elif target == "config":
        from ai_trackdown_pytools.core.config import Config

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

    else:
        console.print(f"[red]Unknown validation target: {target}[/red]")
        console.print("Valid targets: project, tasks, config")
        raise typer.Exit(1)


def run_cli() -> None:
    """Main entry point with error handling."""
    try:
        app()
    except KeyboardInterrupt:
        if console and hasattr(console, "print_warning"):
            console.print_warning("\nOperation cancelled")
        else:
            print("\nOperation cancelled")
        sys.exit(1)
    except Exception as e:
        if console and hasattr(console, "print_error"):
            console.print_error(f"\nError: {e}")
            if not console.is_plain:
                console.print("\nFor help, run: [cyan]aitrackdown doctor[/cyan]")
        else:
            print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_cli()
