"""Main CLI entry point for ai-trackdown-pytools."""

import sys
from typing import Optional

import typer

# from rich.console import Console as RichConsole
# from rich.panel import Panel
from rich.traceback import install

from . import __version__
from .commands import (
    ai,
    comment,
    create,
    epic,
    init,
    issue,
    migrate,
    portfolio,
    pr,
    search,
    status,
    sync,
    task,
    template,
)
from .commands import validate_typer as validate
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
        Config.load(config_file)


# Add subcommands - Core functionality
app.add_typer(init.app, name="init", help="Initialize project")
app.add_typer(status.app, name="status", help="Show status")
app.add_typer(create.app, name="create", help="Create tasks/issues")
app.add_typer(template.app, name="template", help="Manage templates")
app.add_typer(validate.app, name="validate", help="Validate data")

# Add task management commands
app.add_typer(task.app, name="task", help="Task operations")
app.add_typer(issue.app, name="issue", help="Issue tracking")
app.add_typer(epic.app, name="epic", help="Epic management")
app.add_typer(pr.app, name="pr", help="Pull requests")
app.add_typer(comment.app, name="comment", help="Comments")

# Add advanced functionality
app.add_typer(search.app, name="search", help="Search")
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


def main() -> None:
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
    main()
