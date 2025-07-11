"""Main CLI entry point for ai-trackdown-pytools."""

import sys
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install

from . import __version__
from .commands import (
    ai, create, epic, init, issue, migrate, portfolio, pr, 
    search, status, sync, task, template
)
from .commands import validate_typer as validate
from .core.config import Config
from .utils.logging import setup_logging

# Install rich traceback handler for better error display
install(show_locals=False)

app = typer.Typer(
    name="aitrackdown",
    help="AI Trackdown PyTools - Python CLI for AI project tracking and task management",
    context_settings={"help_option_names": ["-h", "--help"]},
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    """Show version information."""
    if value:
        console.print(f"[bold blue]AI Trackdown PyTools[/bold blue] version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
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
        help="Path to configuration file",
    ),
    project_dir: Optional[str] = typer.Option(
        None,
        "--project-dir",
        "-d",
        help="Project directory (enables anywhere-submit functionality)",
    ),
    ctx: typer.Context = typer.Option(None),
) -> None:
    """AI Trackdown PyTools - Python CLI for AI project tracking and task management.
    
    Features:
    • Create and manage tasks, issues, and epics
    • Template-based content generation
    • Git integration and project management
    • Rich terminal output and interactive prompts
    • Anywhere-submit functionality with --project-dir
    
    Examples:
      aitrackdown init project                    Initialize new project
      aitrackdown create task "Fix bug"          Create a new task
      aitrackdown status tasks                   Show task overview
      aitrackdown template list                  List available templates
      aitrackdown --project-dir ~/myproject create task "Remote task"
    """
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
                ctx.obj['original_cwd'] = original_cwd
        except (FileNotFoundError, PermissionError):
            console.print(f"[red]Error: Cannot access project directory: {project_dir}[/red]")
            raise typer.Exit(1)
    
    # Load configuration
    if config_file:
        Config.load(config_file)


# Add subcommands - Core functionality
app.add_typer(init.app, name="init", help="Initialize AI Trackdown project structure")
app.add_typer(status.app, name="status", help="Show project and task status")
app.add_typer(create.app, name="create", help="Create new tasks, projects, or issues")
app.add_typer(template.app, name="template", help="Manage and apply templates")
app.add_typer(validate.app, name="validate", help="Validate tickets, schemas, and relationships")

# Add task management commands
app.add_typer(task.app, name="task", help="Task management and operations")
app.add_typer(issue.app, name="issue", help="Issue tracking and management")
app.add_typer(epic.app, name="epic", help="Epic management and tracking")
app.add_typer(pr.app, name="pr", help="Pull request management and tracking")

# Add advanced functionality
app.add_typer(search.app, name="search", help="Advanced search and filtering")
app.add_typer(portfolio.app, name="portfolio", help="Portfolio and backlog management")
app.add_typer(sync.app, name="sync", help="Sync with external platforms (GitHub, GitLab)")
app.add_typer(ai.app, name="ai", help="AI-specific commands for tracking and context")
app.add_typer(migrate.app, name="migrate", help="Migration and upgrade utilities")


@app.command()
def info() -> None:
    """Show system information."""
    from ai_trackdown_pytools.utils.system import get_system_info
    
    info_data = get_system_info()
    
    console.print(Panel.fit(
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
        border_style="blue"
    ))


@app.command()
def health() -> None:
    """Check system health and dependencies."""
    from ai_trackdown_pytools.utils.health import check_health
    
    health_status = check_health()
    
    if health_status['overall']:
        console.print("[green]✅ System health check passed[/green]")
    else:
        console.print("[red]❌ System health check failed[/red]")
        
    for check, result in health_status['checks'].items():
        status_icon = "✅" if result['status'] else "❌"
        console.print(f"  {status_icon} {check}: {result['message']}")
        
    if not health_status['overall']:
        sys.exit(1)


@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="Configuration key to view or set"),
    value: Optional[str] = typer.Argument(None, help="Configuration value to set"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all configuration"),
    global_config: bool = typer.Option(False, "--global", "-g", help="Use global configuration"),
) -> None:
    """View or modify configuration settings."""
    config = Config.load()
    
    if list_all:
        # Show all configuration
        config_dict = config.to_dict()
        console.print(Panel.fit(
            f"Configuration from: {config.config_path or 'defaults'}\n\n" +
            "\n".join([f"{k}: {v}" for k, v in config_dict.items()]),
            title="Current Configuration",
            border_style="blue"
        ))
        return
    
    if not key:
        # Show basic configuration info
        console.print(f"Configuration file: {config.config_path or 'Not found'}")
        console.print(f"Project root: {config.project_root or 'Not found'}")
        console.print("\nUse --list to see all configuration or specify a key to view/set")
        return
    
    if value is None:
        # Get configuration value
        val = config.get(key)
        if val is not None:
            console.print(f"{key}: {val}")
        else:
            console.print(f"[yellow]Configuration key '{key}' not found[/yellow]")
    else:
        # Set configuration value
        config.set(key, value)
        config.save()
        console.print(f"[green]Set {key} = {value}[/green]")


@app.command()
def doctor() -> None:
    """Run comprehensive system diagnostics."""
    from ai_trackdown_pytools.utils.health import check_health, check_project_health
    from pathlib import Path
    
    console.print("[blue]Running AI Trackdown PyTools diagnostics...[/blue]\n")
    
    # System health check
    console.print("[bold]System Health[/bold]")
    health_status = check_health()
    
    for check, result in health_status['checks'].items():
        status_icon = "✅" if result['status'] else "❌"
        console.print(f"  {status_icon} {check}: {result['message']}")
    
    console.print()
    
    # Project health check if in project
    project_path = Path.cwd()
    from ai_trackdown_pytools.core.project import Project
    
    if Project.exists(project_path):
        console.print("[bold]Project Health[/bold]")
        project_health = check_project_health(project_path)
        
        for check, result in project_health['checks'].items():
            status_icon = "✅" if result['status'] else "❌"
            console.print(f"  {status_icon} {check}: {result['message']}")
    else:
        console.print("[dim]No AI Trackdown project found in current directory[/dim]")
    
    console.print()
    
    # Configuration check
    console.print("[bold]Configuration[/bold]")
    config = Config.load()
    console.print(f"  • Config file: {config.config_path or 'Using defaults'}")
    console.print(f"  • Project root: {config.project_root or 'Not in project'}")
    
    # Git check
    console.print()
    console.print("[bold]Git Integration[/bold]")
    from ai_trackdown_pytools.utils.git import GitUtils, GIT_AVAILABLE
    
    if GIT_AVAILABLE:
        git_utils = GitUtils()
        if git_utils.is_git_repo():
            git_status = git_utils.get_status()
            console.print(f"  ✅ Git repository detected")
            console.print(f"  • Branch: {git_status.get('branch', 'unknown')}")
            console.print(f"  • Modified files: {len(git_status.get('modified', []))}")
        else:
            console.print("  • Not a git repository")
    else:
        console.print("  ❌ GitPython not available")


@app.command()
def version() -> None:
    """Show detailed version information."""
    from ai_trackdown_pytools.utils.system import get_system_info
    
    info = get_system_info()
    
    console.print(Panel.fit(
        f"""[bold blue]AI Trackdown PyTools[/bold blue] v{__version__}

[dim]System Information:[/dim]
• Python: {info['python_version']}
• Platform: {info['platform']} ({info['architecture']})
• Working Directory: {info['cwd']}

[dim]Project Status:[/dim]
• Git Repository: {info['git_repo']}
• Config File: {info['config_file']}
• Project Root: {info['project_root']}

[dim]Package Information:[/dim]
• Templates: {info['templates_dir']}
• Schemas: {info['schema_dir']}""",
        title="Version Information",
        border_style="blue"
    ))


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
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type (task, issue, epic, pr)"),
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
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
    
    for task in all_tasks:
        if (query_lower in task.title.lower() or 
            query_lower in task.description.lower() or
            any(query_lower in tag.lower() for tag in task.tags)):
            
            # Apply filters
            if task_type:
                task_tags = [tag.lower() for tag in task.tags]
                if task_type.lower() not in task_tags:
                    continue
            
            if status_filter and task.status != status_filter:
                continue
            
            matching_tasks.append(task)
    
    matching_tasks = matching_tasks[:limit]
    
    if not matching_tasks:
        console.print(f"[yellow]No tasks found matching '{query}'[/yellow]")
        return
    
    table = Table(title=f"Search Results: '{query}' ({len(matching_tasks)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Tags", style="blue")
    
    for task in matching_tasks:
        table.add_row(
            task.id,
            task.title[:50] + "..." if len(task.title) > 50 else task.title,
            task.status,
            ", ".join(task.tags[:3]) + ("..." if len(task.tags) > 3 else "")
        )
    
    console.print(table)


@app.command()
def validate(
    target: Optional[str] = typer.Argument(None, help="What to validate (project, task, config, template)"),
    path: Optional[str] = typer.Option(None, "--path", "-p", help="Path to validate"),
    fix: bool = typer.Option(False, "--fix", "-f", help="Attempt to fix validation issues"),
) -> None:
    """Validate project structure, tasks, or configuration."""
    from pathlib import Path
    from ai_trackdown_pytools.utils.validation import (
        validate_project_structure, 
        validate_task_file, 
        SchemaValidator
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
        
        if result['valid']:
            console.print("[green]✅ Project structure is valid[/green]")
        else:
            console.print("[red]❌ Project structure validation failed[/red]")
            for error in result['errors']:
                console.print(f"  • [red]{error}[/red]")
        
        if result['warnings']:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for warning in result['warnings']:
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
        
        for task in tasks:
            result = validate_task_file(task.file_path)
            
            status = "✅ Valid" if result['valid'] else "❌ Invalid"
            issues = []
            
            if result['errors']:
                issues.extend([f"Error: {e}" for e in result['errors']])
                total_errors += len(result['errors'])
            
            if result['warnings']:
                issues.extend([f"Warning: {w}" for w in result['warnings']])
                total_warnings += len(result['warnings'])
            
            table.add_row(
                task.id,
                status,
                "\n".join(issues) if issues else "None"
            )
        
        console.print(table)
        console.print(f"\nSummary: {total_errors} errors, {total_warnings} warnings")
    
    elif target == "config":
        from ai_trackdown_pytools.core.config import Config
        
        config = Config.load()
        validator = SchemaValidator()
        
        console.print("[blue]Validating configuration[/blue]\n")
        
        result = validator.validate_config(config.to_dict())
        
        if result['valid']:
            console.print("[green]✅ Configuration is valid[/green]")
        else:
            console.print("[red]❌ Configuration validation failed[/red]")
            for error in result['errors']:
                console.print(f"  • [red]{error}[/red]")
        
        if result['warnings']:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for warning in result['warnings']:
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
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        console.print("\nFor help, run: [cyan]aitrackdown doctor[/cyan]")
        sys.exit(1)


if __name__ == "__main__":
    main()