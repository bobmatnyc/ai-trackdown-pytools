"""Epic management commands."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Epic management and tracking")
console = Console()


@app.command()
def create(
    title: Optional[str] = typer.Argument(None, help="Epic title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Epic description",
    ),
    goal: Optional[str] = typer.Option(
        None,
        "--goal",
        "-g",
        help="Epic goal or objective",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Epic template to use",
    ),
    owner: Optional[str] = typer.Option(
        None,
        "--owner",
        "-o",
        help="Epic owner",
    ),
) -> None:
    """Create a new epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    if not title:
        from rich.prompt import Prompt

        title = Prompt.ask("Epic title")

    if not description:
        from rich.prompt import Prompt

        description = Prompt.ask("Epic description", default="")

    if not goal:
        from rich.prompt import Prompt

        goal = Prompt.ask("Epic goal", default="")

    # Apply template if specified
    epic_data = {
        "title": title,
        "description": description,
        "tags": ["epic"],
        "priority": "high",
        "metadata": {
            "type": "epic",
            "goal": goal,
            "owner": owner,
            "subtasks": [],
            "progress": 0,
        },
    }

    if template:
        template_manager = TemplateManager()
        template_data = template_manager.load_template("epic", template)
        if template_data:
            epic_data.update(template_data)
            console.print(f"[green]Applied template: {template}[/green]")

    new_epic = task_manager.create_task(type="epic", **epic_data)

    console.print(
        Panel.fit(
            f"""[bold green]Epic created successfully![/bold green]

[dim]ID:[/dim] {new_epic.id}
[dim]Title:[/dim] {new_epic.title}
[dim]Goal:[/dim] {goal}
[dim]Owner:[/dim] {owner or 'Unassigned'}
[dim]File:[/dim] {new_epic.file_path}

[dim]Next steps:[/dim]
1. Break down into tasks: [cyan]aitrackdown create task --epic {new_epic.id}[/cyan]
2. View epic status: [cyan]aitrackdown epic status {new_epic.id}[/cyan]""",
            title="Epic Created",
            border_style="blue",
        )
    )


@app.command()
def list(
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    owner_filter: Optional[str] = typer.Option(
        None, "--owner", "-o", help="Filter by owner"
    ),
    show_completed: bool = typer.Option(
        False, "--completed", "-c", help="Include completed epics"
    ),
) -> None:
    """List all epics."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Filter epics
    epics = [task for task in all_tasks if "epic" in task.tags]

    if status_filter:
        epics = [epic for epic in epics if epic.status == status_filter]

    if owner_filter:
        epics = [epic for epic in epics if epic.metadata.get("owner") == owner_filter]

    if not show_completed:
        epics = [epic for epic in epics if epic.status != "completed"]

    if not epics:
        console.print("[yellow]No epics found[/yellow]")
        return

    table = Table(title=f"Epics ({len(epics)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Owner", style="blue")
    table.add_column("Progress", style="green")
    table.add_column("Subtasks", style="yellow")

    for epic in epics:
        subtasks = epic.metadata.get("subtasks", [])
        progress = epic.metadata.get("progress", 0)
        owner = epic.metadata.get("owner", "Unassigned")

        table.add_row(
            epic.id,
            epic.title[:40] + "..." if len(epic.title) > 40 else epic.title,
            epic.status,
            owner,
            f"{progress}%",
            str(len(subtasks)),
        )

    console.print(table)


@app.command()
def status(
    epic_id: str = typer.Argument(..., help="Epic ID to show status for"),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed status"
    ),
) -> None:
    """Show epic status and progress."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    epic = task_manager.load_task(epic_id)

    if not epic or "epic" not in epic.tags:
        console.print(f"[red]Epic '{epic_id}' not found[/red]")
        raise typer.Exit(1)

    # Calculate progress based on subtasks
    subtasks = epic.metadata.get("subtasks", [])
    completed_subtasks = 0

    if subtasks:
        for subtask_id in subtasks:
            subtask = task_manager.load_task(subtask_id)
            if subtask and subtask.status == "completed":
                completed_subtasks += 1
        progress = int((completed_subtasks / len(subtasks)) * 100)
    else:
        progress = 0

    console.print(
        Panel.fit(
            f"""[bold blue]Epic Status[/bold blue]

[dim]ID:[/dim] {epic.id}
[dim]Title:[/dim] {epic.title}
[dim]Description:[/dim] {epic.description}
[dim]Goal:[/dim] {epic.metadata.get('goal', 'Not specified')}
[dim]Owner:[/dim] {epic.metadata.get('owner', 'Unassigned')}
[dim]Status:[/dim] {epic.status}
[dim]Priority:[/dim] {epic.priority}
[dim]Progress:[/dim] {progress}% ({completed_subtasks}/{len(subtasks)} subtasks completed)
[dim]Created:[/dim] {epic.created_at.strftime('%Y-%m-%d %H:%M')}
[dim]Updated:[/dim] {epic.updated_at.strftime('%Y-%m-%d %H:%M')}""",
            title="Epic Details",
            border_style="blue",
        )
    )

    if detailed and subtasks:
        console.print("\n[bold]Subtasks:[/bold]")

        table = Table()
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Status", style="magenta")
        table.add_column("Priority", style="yellow")

        for subtask_id in subtasks:
            subtask = task_manager.load_task(subtask_id)
            if subtask:
                table.add_row(
                    subtask.id,
                    (
                        subtask.title[:50] + "..."
                        if len(subtask.title) > 50
                        else subtask.title
                    ),
                    subtask.status,
                    subtask.priority,
                )

        console.print(table)


@app.command()
def add_issue(
    epic_id: str = typer.Argument(..., help="Epic ID to add issues to"),
    issue_ids: List[str] = typer.Argument(..., help="Issue ID(s) to add to epic"),
) -> None:
    """Add one or more issues to an epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    epic = task_manager.load_task(epic_id)

    if not epic or "epic" not in epic.tags:
        console.print(f"[red]Epic '{epic_id}' not found[/red]")
        raise typer.Exit(1)

    # Get current subtasks
    subtasks = epic.metadata.get("subtasks", [])
    added_issues = []
    already_added = []
    not_found = []

    for issue_id in issue_ids:
        try:
            issue = task_manager.load_task(issue_id)
            if not issue:
                not_found.append(issue_id)
                continue

            if issue_id not in subtasks:
                subtasks.append(issue_id)
                # Update issue's parent field to reference the epic
                updates = {"parent": epic_id}
                task_manager.update_task(issue_id, **updates)
                added_issues.append(issue_id)
            else:
                already_added.append(issue_id)
        except Exception:
            not_found.append(issue_id)

    # Update epic metadata with new subtasks list
    if added_issues:
        epic.metadata["subtasks"] = subtasks
        task_manager.save_task(epic)

    # Report results
    if added_issues:
        console.print(
            f"[green]Added {len(added_issues)} issue(s) to epic {epic_id}:[/green] {', '.join(added_issues)}"
        )
    if already_added:
        console.print(f"[yellow]Already in epic:[/yellow] {', '.join(already_added)}")
    if not_found:
        console.print(f"[red]Issues not found:[/red] {', '.join(not_found)}")


@app.command()
def add_task(
    epic_id: str = typer.Argument(..., help="Epic ID to add task to"),
    task_id: str = typer.Argument(..., help="Task ID to add to epic"),
) -> None:
    """Add a task to an epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    epic = task_manager.load_task(epic_id)
    task = task_manager.load_task(task_id)

    if not epic or "epic" not in epic.tags:
        console.print(f"[red]Epic '{epic_id}' not found[/red]")
        raise typer.Exit(1)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    # Add task to epic's subtasks
    subtasks = epic.metadata.get("subtasks", [])
    if task_id not in subtasks:
        subtasks.append(task_id)

        # Update epic metadata
        epic.metadata["subtasks"] = subtasks
        task_manager.save_task(epic)

        # Add epic reference to task
        task.metadata["epic"] = epic_id
        task_manager.save_task(task)

        console.print(f"[green]Task {task_id} added to epic {epic_id}[/green]")
    else:
        console.print(
            f"[yellow]Task {task_id} is already part of epic {epic_id}[/yellow]"
        )


@app.command()
def remove_issue(
    epic_id: str = typer.Argument(..., help="Epic ID to remove issues from"),
    issue_ids: List[str] = typer.Argument(..., help="Issue ID(s) to remove from epic"),
) -> None:
    """Remove one or more issues from an epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    epic = task_manager.load_task(epic_id)

    if not epic or "epic" not in epic.tags:
        console.print(f"[red]Epic '{epic_id}' not found[/red]")
        raise typer.Exit(1)

    # Get current subtasks
    subtasks = epic.metadata.get("subtasks", [])
    removed_issues = []
    not_in_epic = []
    not_found = []

    for issue_id in issue_ids:
        try:
            issue = task_manager.load_task(issue_id)
            if not issue:
                not_found.append(issue_id)
                continue

            if issue_id in subtasks:
                subtasks.remove(issue_id)
                # Clear issue's parent field
                updates = {"parent": None}
                task_manager.update_task(issue_id, **updates)
                removed_issues.append(issue_id)
            else:
                not_in_epic.append(issue_id)
        except Exception:
            not_found.append(issue_id)

    # Update epic metadata with new subtasks list
    if removed_issues:
        epic.metadata["subtasks"] = subtasks
        task_manager.save_task(epic)

    # Report results
    if removed_issues:
        console.print(
            f"[green]Removed {len(removed_issues)} issue(s) from epic {epic_id}:[/green] {', '.join(removed_issues)}"
        )
    if not_in_epic:
        console.print(f"[yellow]Not in epic:[/yellow] {', '.join(not_in_epic)}")
    if not_found:
        console.print(f"[red]Issues not found:[/red] {', '.join(not_found)}")


@app.command()
def remove_task(
    epic_id: str = typer.Argument(..., help="Epic ID to remove task from"),
    task_id: str = typer.Argument(..., help="Task ID to remove from epic"),
) -> None:
    """Remove a task from an epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    epic = task_manager.load_task(epic_id)
    task = task_manager.load_task(task_id)

    if not epic or "epic" not in epic.tags:
        console.print(f"[red]Epic '{epic_id}' not found[/red]")
        raise typer.Exit(1)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    # Remove task from epic's subtasks
    subtasks = epic.metadata.get("subtasks", [])
    if task_id in subtasks:
        subtasks.remove(task_id)

        # Update epic metadata
        epic.metadata["subtasks"] = subtasks
        task_manager.save_task(epic)

        # Remove epic reference from task
        if "epic" in task.metadata:
            del task.metadata["epic"]
            task_manager.save_task(task)

        console.print(f"[green]Task {task_id} removed from epic {epic_id}[/green]")
    else:
        console.print(f"[yellow]Task {task_id} is not part of epic {epic_id}[/yellow]")


@app.command()
def update(
    epic_id: str = typer.Argument(..., help="Epic ID to update"),
    title: Optional[str] = typer.Option(None, "--title", help="Update epic title"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Update epic description"
    ),
    goal: Optional[str] = typer.Option(None, "--goal", "-g", help="Update epic goal"),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Update epic status"
    ),
    owner: Optional[str] = typer.Option(
        None, "--owner", "-o", help="Update epic owner"
    ),
) -> None:
    """Update an existing epic."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    epic = task_manager.load_task(epic_id)

    if not epic or "epic" not in epic.tags:
        console.print(f"[red]Epic '{epic_id}' not found[/red]")
        raise typer.Exit(1)

    # Prepare update data
    updates = {}
    metadata_updates = {}

    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if status:
        if status not in ["open", "in_progress", "completed", "cancelled", "blocked"]:
            console.print(f"[red]Invalid status: {status}[/red]")
            console.print(
                "Valid statuses: open, in_progress, completed, cancelled, blocked"
            )
            raise typer.Exit(1)
        updates["status"] = status
    if goal:
        metadata_updates["goal"] = goal
    if owner:
        metadata_updates["owner"] = owner

    if not updates and not metadata_updates:
        console.print("[yellow]No updates specified[/yellow]")
        return

    # Apply metadata updates
    if metadata_updates:
        epic.metadata.update(metadata_updates)
        updates["metadata"] = epic.metadata

    # Apply updates
    success = task_manager.update_task(epic_id, **updates)

    if success:
        # Build list of what was updated
        updated_fields = [k for k in updates]
        if metadata_updates:
            # Add metadata fields to the list, but avoid duplicating 'metadata'
            if "metadata" in updated_fields:
                updated_fields.remove("metadata")
            updated_fields.extend(k for k in metadata_updates)

        console.print(
            Panel.fit(
                f"""[bold green]Epic updated successfully![/bold green]

[dim]ID:[/dim] {epic_id}
[dim]Updates applied:[/dim] {', '.join(updated_fields)}""",
                title="Epic Updated",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to update epic {epic_id}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
