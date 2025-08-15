"""Index management commands for AI Trackdown PyTools."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.utils.index import IndexManager

app = typer.Typer(help="Manage search index for tasks, issues, and epics")
console = Console()


@app.command()
def rebuild(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force rebuild even if index is recent",
    ),
) -> None:
    """Rebuild the search index from scratch."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    manager = IndexManager(project_path)

    if not force and not manager.needs_update():
        console.print(
            "[yellow]Index is up to date. Use --force to rebuild anyway.[/yellow]"
        )
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Rebuilding index...", total=None)

        stats = manager.rebuild_index()

        progress.update(task, completed=True)

    console.print(
        Panel.fit(
            f"""[bold green]Index rebuilt successfully![/bold green]

[dim]Files indexed:[/dim] {stats['indexed']}
[dim]Errors:[/dim] {stats['errors']}""",
            title="Index Rebuilt",
            border_style="green",
        )
    )


@app.command()
def update(
    _verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed update information",
    ),
) -> None:
    """Update index with changed files only."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    manager = IndexManager(project_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Updating index...", total=None)

        stats = manager.update_changed_files()

        progress.update(task, completed=True)

    if any(stats.values()):
        console.print(
            Panel.fit(
                f"""[bold green]Index updated successfully![/bold green]

[dim]Files added:[/dim] {stats['added']}
[dim]Files updated:[/dim] {stats['updated']}
[dim]Files removed:[/dim] {stats['removed']}""",
                title="Index Updated",
                border_style="green",
            )
        )
    else:
        console.print("[blue]No changes detected - index is up to date[/blue]")


@app.command()
def stats(
    detailed: bool = typer.Option(
        False,
        "--detailed",
        "-d",
        help="Show detailed statistics",
    ),
) -> None:
    """Show index statistics."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    manager = IndexManager(project_path)
    stats = manager.get_statistics()

    # Overview table
    overview_table = Table(title="Index Overview")
    overview_table.add_column("Type", style="cyan")
    overview_table.add_column("Count", style="green", justify="right")

    overview_table.add_row("Tasks", str(stats.get("total_tasks", 0)))
    overview_table.add_row("Issues", str(stats.get("total_issues", 0)))
    overview_table.add_row("Epics", str(stats.get("total_epics", 0)))
    overview_table.add_row("Pull Requests", str(stats.get("total_prs", 0)))

    console.print(overview_table)

    if detailed:
        # Status breakdown
        if stats.get("by_status"):
            status_table = Table(title="\nBy Status")
            status_table.add_column("Status", style="cyan")
            status_table.add_column("Count", style="green", justify="right")

            for status, count in sorted(stats["by_status"].items()):
                status_table.add_row(status, str(count))

            console.print(status_table)

        # Priority breakdown
        if stats.get("by_priority"):
            priority_table = Table(title="\nBy Priority")
            priority_table.add_column("Priority", style="cyan")
            priority_table.add_column("Count", style="green", justify="right")

            priority_order = ["critical", "high", "medium", "low"]
            for priority in priority_order:
                if priority in stats["by_priority"]:
                    priority_table.add_row(
                        priority, str(stats["by_priority"][priority])
                    )

            console.print(priority_table)

        # Assignee breakdown
        if stats.get("by_assignee"):
            assignee_table = Table(title="\nBy Assignee")
            assignee_table.add_column("Assignee", style="cyan")
            assignee_table.add_column("Count", style="green", justify="right")

            for assignee, count in sorted(
                stats["by_assignee"].items(), key=lambda x: x[1], reverse=True
            ):
                assignee_table.add_row(assignee, str(count))

            console.print(assignee_table)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    item_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by type (task, issue, epic, pr)",
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status",
    ),
    priority: Optional[str] = typer.Option(
        None,
        "--priority",
        "-p",
        help="Filter by priority",
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Filter by assignee",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum results to show",
    ),
) -> None:
    """Search the index with filters."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    manager = IndexManager(project_path)

    # Build filters
    filters = {}
    if item_type:
        filters["type"] = item_type
    if status:
        filters["status"] = status
    if priority:
        filters["priority"] = priority
    if assignee:
        filters["assignee"] = assignee

    # Search
    results = manager.search(query, filters)

    if not results:
        console.print(f"[yellow]No results found for '{query}'[/yellow]")
        return

    # Display results
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Priority", style="yellow")

    for result in results[:limit]:
        table.add_row(
            result.get("id", ""),
            result.get("type", ""),
            (
                result.get("title", "")[:50] + "..."
                if len(result.get("title", "")) > 50
                else result.get("title", "")
            ),
            result.get("status", ""),
            result.get("priority", ""),
        )

    console.print(table)

    if len(results) > limit:
        console.print(f"\n[dim]Showing {limit} of {len(results)} results[/dim]")


if __name__ == "__main__":
    app()
