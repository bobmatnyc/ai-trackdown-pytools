"""Comment management commands for AI Trackdown PyTools."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.utils.comments import CommentManager, add_comment_to_item

app = typer.Typer(help="Manage comments on tasks, issues, and epics")
console = Console()


@app.command()
def add(
    item_id: str = typer.Argument(..., help="Task, issue, or epic ID"),
    content: str = typer.Argument(..., help="Comment content"),
    author: Optional[str] = typer.Option(
        None,
        "--author",
        "-a",
        help="Comment author (defaults to current user)",
    ),
    item_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Item type (task, issue, epic) - auto-detected if not specified",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force adding comment even on closed/terminal tickets",
    ),
) -> None:
    """Add a comment to a task, issue, or epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Auto-detect item type from ID if not specified
    if not item_type:
        if item_id.startswith("TSK-"):
            item_type = "task"
        elif item_id.startswith("ISS-"):
            item_type = "issue"
        elif item_id.startswith("EP-"):
            item_type = "epic"
        else:
            console.print(f"[red]Cannot determine type for ID: {item_id}[/red]")
            console.print("Use --type to specify: task, issue, or epic")
            raise typer.Exit(1)

    # Get author from environment or use default
    if not author:
        author = os.getenv("USER") or os.getenv("USERNAME") or "Unknown"

    # Add the comment
    success = add_comment_to_item(
        item_type, item_id, author, content, project_path, force=force
    )

    if success:
        console.print(
            Panel.fit(
                f"""[bold green]Comment added successfully![/bold green]

[dim]Item:[/dim] {item_id}
[dim]Author:[/dim] {author}
[dim]Content:[/dim] {content[:50]}{'...' if len(content) > 50 else ''}""",
                title="Comment Added",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to add comment to {item_id}[/red]")
        raise typer.Exit(1)


@app.command()
def list(
    item_id: str = typer.Argument(..., help="Task, issue, or epic ID"),
    limit: int = typer.Option(
        10,
        "--limit",
        "-l",
        help="Maximum number of comments to show",
    ),
) -> None:
    """List comments on a task, issue, or epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Find the file
    config = Config.load(project_path=project_path)
    tasks_dir = project_path / config.get("tasks.directory", "tasks")

    # Try multiple patterns to find the file
    patterns = [
        f"**/{item_id}.md",  # Direct match anywhere
        f"*/{item_id}.md",  # In any subdirectory
        f"{item_id}.md",  # In root tasks directory
    ]

    # If we know the prefix, also try specific subdirectory patterns
    if item_id.startswith("TSK-"):
        patterns.insert(0, f"tsk/{item_id}.md")
    elif item_id.startswith("ISS-"):
        patterns.insert(0, f"iss/{item_id}.md")
    elif item_id.startswith("EP-"):
        patterns.insert(0, f"ep/{item_id}.md")

    file_path = None
    for pattern in patterns:
        matches = list(tasks_dir.glob(pattern))
        if matches:
            file_path = matches[0]
            break

    if not file_path:
        console.print(f"[red]Could not find item with ID: {item_id}[/red]")
        raise typer.Exit(1)

    # Get comments
    manager = CommentManager(file_path)
    comments = manager.get_comments()

    if not comments:
        console.print(f"[yellow]No comments found on {item_id}[/yellow]")
        return

    # Create table
    table = Table(title=f"Comments on {item_id}")
    table.add_column("Author", style="cyan")
    table.add_column("Timestamp", style="green")
    table.add_column("Comment", style="white")

    # Add comments (most recent first)
    for comment in reversed(comments[-limit:]):
        timestamp_str = (
            comment["timestamp"].strftime("%Y-%m-%d %H:%M")
            if comment["timestamp"]
            else "Unknown"
        )
        content = comment["content"]

        # Truncate long comments
        if len(content) > 100:
            content = content[:97] + "..."

        table.add_row(comment["author"], timestamp_str, content)

    console.print(table)

    if len(comments) > limit:
        console.print(f"\n[dim]Showing {limit} of {len(comments)} comments[/dim]")


@app.command()
def count(
    item_id: str = typer.Argument(..., help="Task, issue, or epic ID"),
) -> None:
    """Count comments on a task, issue, or epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Find the file
    config = Config.load(project_path=project_path)
    tasks_dir = project_path / config.get("tasks.directory", "tasks")

    # Try multiple patterns to find the file
    patterns = [
        f"**/{item_id}.md",  # Direct match anywhere
        f"*/{item_id}.md",  # In any subdirectory
        f"{item_id}.md",  # In root tasks directory
    ]

    # If we know the prefix, also try specific subdirectory patterns
    if item_id.startswith("TSK-"):
        patterns.insert(0, f"tsk/{item_id}.md")
    elif item_id.startswith("ISS-"):
        patterns.insert(0, f"iss/{item_id}.md")
    elif item_id.startswith("EP-"):
        patterns.insert(0, f"ep/{item_id}.md")

    file_path = None
    for pattern in patterns:
        matches = list(tasks_dir.glob(pattern))
        if matches:
            file_path = matches[0]
            break

    if not file_path:
        console.print(f"[red]Could not find item with ID: {item_id}[/red]")
        raise typer.Exit(1)

    # Count comments
    manager = CommentManager(file_path)
    count = manager.count_comments()

    console.print(
        f"[blue]{item_id} has {count} comment{'s' if count != 1 else ''}[/blue]"
    )


if __name__ == "__main__":
    app()
