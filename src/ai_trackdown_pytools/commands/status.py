"""Show project and task status."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ai_trackdown_pytools.core.compatibility import convert_to_unified_status
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.core.workflow import UnifiedStatus
from ai_trackdown_pytools.utils.git import GitUtils

app = typer.Typer(help="Show project and task status")
console = Console()


@app.command()
def project(
    path: Optional[Path] = typer.Argument(
        None,
        help="Project directory path (defaults to current directory)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed information",
    ),
) -> None:
    """Show project status and overview."""
    project_path = path or Path.cwd()

    if not Project.exists(project_path):
        console.print(f"[red]No AI Trackdown project found at {project_path}[/red]")
        console.print("Run 'aitrackdown init project' to initialize")
        raise typer.Exit(1)

    project = Project.load(project_path)
    task_manager = TaskManager(project_path)
    git_utils = GitUtils(project_path)

    # Project overview
    console.print(
        Panel.fit(
            f"""[bold]{project.name}[/bold]
{project.description or '[dim]No description[/dim]'}

[dim]Path:[/dim] {project_path}
[dim]Version:[/dim] {project.version}
[dim]Created:[/dim] {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}""",
            title="Project Overview",
            border_style="blue",
        )
    )

    # Task summary with categories
    tasks = task_manager.list_tasks()

    # Categorize tasks
    epics = [t for t in tasks if "epic" in t.tags]
    issues = [t for t in tasks if "issue" in t.tags]
    prs = [t for t in tasks if "pull-request" in t.tags]
    regular_tasks = [
        t
        for t in tasks
        if not any(tag in t.tags for tag in ["epic", "issue", "pull-request"])
    ]

    # Count tasks by unified status
    def normalize_task_status(task):
        """Normalize task status to UnifiedStatus."""
        return convert_to_unified_status(task.status)

    task_stats = {
        "total": len(tasks),
        "epics": len(epics),
        "issues": len(issues),
        "prs": len(prs),
        "tasks": len(regular_tasks),
        UnifiedStatus.OPEN.value: len(
            [t for t in tasks if normalize_task_status(t) == UnifiedStatus.OPEN]
        ),
        UnifiedStatus.IN_PROGRESS.value: len(
            [t for t in tasks if normalize_task_status(t) == UnifiedStatus.IN_PROGRESS]
        ),
        UnifiedStatus.COMPLETED.value: len(
            [t for t in tasks if normalize_task_status(t) == UnifiedStatus.COMPLETED]
        ),
        UnifiedStatus.BLOCKED.value: len(
            [t for t in tasks if normalize_task_status(t) == UnifiedStatus.BLOCKED]
        ),
    }

    # Type breakdown
    type_table = Table(title="Task Type Summary")
    type_table.add_column("Type", style="cyan")
    type_table.add_column("Count", justify="right", style="magenta")

    type_table.add_row("Total", str(task_stats["total"]))
    type_table.add_row("Epics", str(task_stats["epics"]))
    type_table.add_row("Issues", str(task_stats["issues"]))
    type_table.add_row("Pull Requests", str(task_stats["prs"]))
    type_table.add_row("Tasks", str(task_stats["tasks"]))

    console.print(type_table)

    # Status breakdown
    status_table = Table(title="Status Summary")
    status_table.add_column("Status", style="cyan")
    status_table.add_column("Count", justify="right", style="magenta")

    status_table.add_row("Open", str(task_stats[UnifiedStatus.OPEN.value]))
    status_table.add_row(
        "In Progress", str(task_stats[UnifiedStatus.IN_PROGRESS.value])
    )
    status_table.add_row("Blocked", str(task_stats[UnifiedStatus.BLOCKED.value]))
    status_table.add_row("Completed", str(task_stats[UnifiedStatus.COMPLETED.value]))

    console.print(status_table)

    # Git status if available
    if git_utils.is_git_repo():
        git_status = git_utils.get_status()
        if git_status:
            commit_sha = git_status.get("commit", "unknown")
            if commit_sha != "unknown" and len(commit_sha) > 8:
                commit_sha = commit_sha[:8]
            git_panel = Panel.fit(
                f"""[dim]Branch:[/dim] {git_status.get('branch', 'unknown')}
[dim]Commit:[/dim] {commit_sha}
[dim]Modified Files:[/dim] {len(git_status.get('modified', []))}
[dim]Untracked Files:[/dim] {len(git_status.get('untracked', []))}""",
                title="Git Status",
                border_style="green",
            )
            console.print(git_panel)
        else:
            console.print("[yellow]Git status information not available[/yellow]")

    if verbose:
        # Show recent tasks (sorted by updated_at)
        recent_tasks = sorted(tasks, key=lambda t: t.updated_at, reverse=True)[:5]
        if recent_tasks:
            task_tree = Tree("Recent Tasks")
            for task in recent_tasks:
                unified_status = convert_to_unified_status(task.status)
                status_color = {
                    UnifiedStatus.OPEN: "red",
                    UnifiedStatus.IN_PROGRESS: "yellow",
                    UnifiedStatus.COMPLETED: "green",
                    UnifiedStatus.BLOCKED: "magenta",
                    UnifiedStatus.CLOSED: "dim",
                    UnifiedStatus.RESOLVED: "green",
                    UnifiedStatus.CANCELLED: "red",
                }.get(unified_status, "white")
                task_tree.add(
                    f"[{status_color}]{task.title}[/{status_color}] ({task.status})"
                )
            console.print(task_tree)

        # Show epic progress if epics exist
        if epics:
            console.print("\n[bold]Epic Progress:[/bold]")
            for epic in epics[:3]:  # Show top 3 epics
                subtasks = epic.metadata.get("subtasks", [])
                if subtasks:
                    completed = sum(
                        1
                        for st_id in subtasks
                        if task_manager.load_task(st_id)
                        and convert_to_unified_status(
                            task_manager.load_task(st_id).status
                        )
                        == UnifiedStatus.COMPLETED
                    )
                    progress = int((completed / len(subtasks)) * 100)
                else:
                    progress = (
                        0
                        if convert_to_unified_status(epic.status)
                        != UnifiedStatus.COMPLETED
                        else 100
                    )

                progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)
                console.print(f"  • {epic.title[:30]}... {progress_bar} {progress}%")


@app.command()
def tasks(
    status_filter: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter tasks by status (open, in_progress, completed)",
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Filter tasks by assignee",
    ),
    tag: Optional[str] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Filter tasks by tag",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum number of tasks to show",
    ),
) -> None:
    """Show task status with filtering options."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    tasks = task_manager.list_tasks()

    # Apply filters
    if status_filter:
        tasks = [t for t in tasks if t.status == status_filter]
    if assignee:
        tasks = [t for t in tasks if assignee in t.assignees]
    if tag:
        tasks = [t for t in tasks if tag in t.tags]

    # Limit results
    tasks = tasks[:limit]

    if not tasks:
        console.print("[yellow]No tasks found matching criteria[/yellow]")
        return

    # Display tasks table
    table = Table(title=f"Tasks ({len(tasks)} shown)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Assignee", style="green")
    table.add_column("Tags", style="blue")
    table.add_column("Updated", style="dim")

    for task in tasks:
        unified_status = convert_to_unified_status(task.status)
        status_style = {
            UnifiedStatus.OPEN: "[red]open[/red]",
            UnifiedStatus.IN_PROGRESS: "[yellow]in_progress[/yellow]",
            UnifiedStatus.COMPLETED: "[green]completed[/green]",
            UnifiedStatus.BLOCKED: "[magenta]blocked[/magenta]",
            UnifiedStatus.CLOSED: "[dim]closed[/dim]",
            UnifiedStatus.RESOLVED: "[green]resolved[/green]",
            UnifiedStatus.CANCELLED: "[red]cancelled[/red]",
        }.get(unified_status, f"[white]{unified_status.value}[/white]")

        table.add_row(
            task.id,
            task.title,
            status_style,
            ", ".join(task.assignees) if task.assignees else "-",
            ", ".join(task.tags) if task.tags else "-",
            task.updated_at.strftime("%Y-%m-%d"),
        )

    console.print(table)


@app.command()
def health() -> None:
    """Check project health and dependencies."""
    from ai_trackdown_pytools.utils.health import check_project_health

    project_path = Path.cwd()
    health_status = check_project_health(project_path)

    if health_status["overall"]:
        console.print("[green]✅ Project health check passed[/green]")
    else:
        console.print("[red]❌ Project health check failed[/red]")

    for check, result in health_status["checks"].items():
        status_icon = "✅" if result["status"] else "❌"
        console.print(f"  {status_icon} {check}: {result['message']}")


if __name__ == "__main__":
    app()
