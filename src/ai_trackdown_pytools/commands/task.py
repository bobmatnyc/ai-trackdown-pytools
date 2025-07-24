"""Task management commands."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.editor import EditorUtils
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Task management and operations")
console = Console()


@app.command()
def create(
    title: Optional[str] = typer.Argument(None, help="Task title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Task description",
    ),
    assignee: Optional[List[str]] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Task assignee (can be specified multiple times)",
    ),
    tag: Optional[List[str]] = typer.Option(
        None,
        "--tag",
        "-t",
        help="Task tag (can be specified multiple times)",
    ),
    priority: Optional[str] = typer.Option(
        "medium",
        "--priority",
        "-p",
        help="Task priority (low, medium, high, critical)",
    ),
    estimate: Optional[str] = typer.Option(
        None,
        "--estimate",
        "-e",
        help="Time estimate (e.g., '2h', '1d', '1w')",
    ),
    epic: Optional[str] = typer.Option(
        None,
        "--epic",
        help="Epic ID to associate with this task",
    ),
    parent: Optional[str] = typer.Option(
        None,
        "--parent",
        help="Parent task ID for subtasks",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Task template to use",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Interactive task creation",
    ),
    edit: bool = typer.Option(
        False,
        "--edit",
        help="Open task in editor after creation",
    ),
) -> None:
    """Create a new task."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        console.print("Run 'aitrackdown init project' to initialize")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    # Interactive mode
    if interactive or not title:
        from rich.prompt import Prompt

        title = title or Prompt.ask("Task title")
        description = description or Prompt.ask("Task description", default="")
        priority = Prompt.ask(
            "Priority",
            choices=["low", "medium", "high", "critical"],
            default=priority or "medium",
        )

        assignee_input = Prompt.ask("Assignees (comma-separated)", default="")
        if assignee_input:
            assignee = [a.strip() for a in assignee_input.split(",")]

        tag_input = Prompt.ask("Tags (comma-separated)", default="")
        if tag_input:
            tag = [t.strip() for t in tag_input.split(",")]

        estimate = estimate or Prompt.ask("Time estimate (optional)", default="")

    # Validate epic if specified
    if epic:
        epic_task = task_manager.load_task(epic)
        if not epic_task or "epic" not in epic_task.tags:
            console.print(f"[red]Epic '{epic}' not found[/red]")
            raise typer.Exit(1)

    # Validate parent if specified
    if parent:
        parent_task = task_manager.load_task(parent)
        if not parent_task:
            console.print(f"[red]Parent task '{parent}' not found[/red]")
            raise typer.Exit(1)

    # Create task
    task_data = {
        "title": title,
        "description": description or "",
        "assignees": assignee or [],
        "tags": tag or [],
        "priority": priority or "medium",
        "metadata": {
            "estimate": estimate,
            "epic": epic,
            "parent": parent,
            "subtasks": [],
            "blocked_by": [],
            "blocks": [],
        },
    }

    # Apply template if specified
    if template:
        template_manager = TemplateManager()
        template_data = template_manager.load_template("task", template)
        if template_data:
            task_data.update(template_data)
            console.print(f"[green]Applied template: {template}[/green]")

    new_task = task_manager.create_task(**task_data)

    # Update epic if specified
    if epic:
        epic_task = task_manager.load_task(epic)
        subtasks = epic_task.metadata.get("subtasks", [])
        subtasks.append(new_task.id)
        epic_task.metadata["subtasks"] = subtasks
        task_manager.save_task(epic_task)

    # Update parent if specified
    if parent:
        parent_task = task_manager.load_task(parent)
        subtasks = parent_task.metadata.get("subtasks", [])
        subtasks.append(new_task.id)
        parent_task.metadata["subtasks"] = subtasks
        task_manager.save_task(parent_task)

    console.print(
        Panel.fit(
            f"""[bold green]Task created successfully![/bold green]

[dim]ID:[/dim] {new_task.id}
[dim]Title:[/dim] {new_task.title}
[dim]Priority:[/dim] {new_task.priority}
[dim]Status:[/dim] {new_task.status}
[dim]Estimate:[/dim] {estimate or 'Not specified'}
[dim]Epic:[/dim] {epic or 'None'}
[dim]Parent:[/dim] {parent or 'None'}
[dim]File:[/dim] {new_task.file_path}""",
            title="Task Created",
            border_style="green",
        )
    )

    # Open in editor if requested
    if edit:
        EditorUtils.open_file(new_task.file_path)


@app.command()
def list(
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    assignee_filter: Optional[str] = typer.Option(
        None, "--assignee", "-a", help="Filter by assignee"
    ),
    tag_filter: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    priority_filter: Optional[str] = typer.Option(
        None, "--priority", "-p", help="Filter by priority"
    ),
    epic_filter: Optional[str] = typer.Option(
        None, "--epic", "-e", help="Filter by epic"
    ),
    show_completed: bool = typer.Option(
        False, "--completed", "-c", help="Include completed tasks"
    ),
    show_subtasks: bool = typer.Option(False, "--subtasks", help="Include subtasks"),
    limit: int = typer.Option(
        50, "--limit", "-l", help="Maximum number of tasks to show"
    ),
) -> None:
    """List tasks with optional filtering."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Filter regular tasks (exclude epics, issues, PRs)
    tasks = [
        task
        for task in all_tasks
        if not any(tag in task.tags for tag in ["epic", "issue", "pull-request"])
    ]

    # Apply filters
    if status_filter:
        tasks = [task for task in tasks if task.status == status_filter]

    if assignee_filter:
        tasks = [task for task in tasks if assignee_filter in task.assignees]

    if tag_filter:
        tasks = [task for task in tasks if tag_filter in task.tags]

    if priority_filter:
        tasks = [task for task in tasks if task.priority == priority_filter]

    if epic_filter:
        tasks = [task for task in tasks if task.metadata.get("epic") == epic_filter]

    if not show_completed:
        tasks = [task for task in tasks if task.status != "completed"]

    if not show_subtasks:
        tasks = [task for task in tasks if not task.metadata.get("parent")]

    # Limit results
    # Handle case where limit might be passed as OptionInfo object
    if hasattr(limit, "default"):
        # This is a typer OptionInfo object, use its default value
        limit_value = limit.default
    elif isinstance(limit, int):
        limit_value = limit
    else:
        # Fallback to default
        limit_value = 50

    tasks = tasks[:limit_value]

    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        return

    table = Table(title=f"Tasks ({len(tasks)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="magenta")
    table.add_column("Priority", style="yellow")
    table.add_column("Assignee", style="blue")
    table.add_column("Estimate", style="green")
    table.add_column("Epic", style="dim")

    for task in tasks:
        assignee = ", ".join(task.assignees) if task.assignees else "Unassigned"
        estimate = task.metadata.get("estimate", "")
        epic = task.metadata.get("epic", "")

        table.add_row(
            task.id,
            task.title[:40] + "..." if len(task.title) > 40 else task.title,
            task.status,
            task.priority,
            assignee[:15] + "..." if len(assignee) > 15 else assignee,
            estimate,
            epic,
        )

    console.print(table)


@app.command()
def show(
    task_id: str = typer.Argument(..., help="Task ID to display"),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed information"
    ),
) -> None:
    """Show detailed task information."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    task = task_manager.load_task(task_id)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    assignees = ", ".join(task.assignees) if task.assignees else "Unassigned"
    tags = ", ".join(task.tags) if task.tags else "None"

    info_text = f"""[bold green]Task Details[/bold green]

[dim]ID:[/dim] {task.id}
[dim]Title:[/dim] {task.title}
[dim]Status:[/dim] {task.status}
[dim]Priority:[/dim] {task.priority}
[dim]Assignees:[/dim] {assignees}
[dim]Tags:[/dim] {tags}
[dim]Estimate:[/dim] {task.metadata.get('estimate', 'Not specified')}
[dim]Created:[/dim] {task.created_at.strftime('%Y-%m-%d %H:%M')}
[dim]Updated:[/dim] {task.updated_at.strftime('%Y-%m-%d %H:%M')}"""

    if task.metadata.get("epic"):
        info_text += f"\n[dim]Epic:[/dim] {task.metadata.get('epic')}"

    if task.parent:
        info_text += f"\n[dim]Parent:[/dim] {task.parent}"

    subtasks = task.metadata.get("subtasks", [])
    if subtasks:
        info_text += f"\n[dim]Subtasks:[/dim] {len(subtasks)} task(s)"

    blocked_by = task.metadata.get("blocked_by", [])
    if blocked_by:
        info_text += f"\n[dim]Blocked by:[/dim] {', '.join(blocked_by)}"

    blocks = task.metadata.get("blocks", [])
    if blocks:
        info_text += f"\n[dim]Blocks:[/dim] {', '.join(blocks)}"

    if detailed:
        info_text += f"\n\n[dim]Description:[/dim]\n{task.description}"

    console.print(Panel.fit(info_text, title="Task Information", border_style="green"))

    # Show subtasks if detailed and exist
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
def update(
    task_id: str = typer.Argument(..., help="Task ID to update"),
    title: Optional[str] = typer.Option(None, "--title", help="Update task title"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Update task description"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Update task status"
    ),
    priority: Optional[str] = typer.Option(
        None, "--priority", "-p", help="Update task priority"
    ),
    assignee: Optional[List[str]] = typer.Option(
        None, "--assignee", "-a", help="Update task assignees"
    ),
    estimate: Optional[str] = typer.Option(
        None, "--estimate", "-e", help="Update time estimate"
    ),
    epic: Optional[str] = typer.Option(None, "--epic", help="Link task to epic"),
    tag: Optional[List[str]] = typer.Option(
        None, "--tag", "-t", help="Update task tags"
    ),
    add_tag: Optional[List[str]] = typer.Option(
        None, "--add-tag", help="Add tags to task"
    ),
    remove_tag: Optional[List[str]] = typer.Option(
        None, "--remove-tag", help="Remove tags from task"
    ),
) -> None:
    """Update an existing task."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    task = task_manager.load_task(task_id)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
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
    if priority:
        if priority not in ["low", "medium", "high", "critical"]:
            console.print(f"[red]Invalid priority: {priority}[/red]")
            console.print("Valid priorities: low, medium, high, critical")
            raise typer.Exit(1)
        updates["priority"] = priority
    if assignee is not None:
        updates["assignees"] = assignee
    if estimate:
        metadata_updates["estimate"] = estimate

    # Handle tag updates
    if tag is not None:
        updates["tags"] = tag
    elif add_tag or remove_tag:
        current_tags = set(task.tags)
        if add_tag:
            current_tags.update(add_tag)
        if remove_tag:
            current_tags.difference_update(remove_tag)
        updates["tags"] = list(current_tags)

    # Handle epic linking
    if epic is not None:
        if epic:  # If epic is specified (not empty string)
            # Validate epic exists
            epic_task = task_manager.load_task(epic)
            if not epic_task or "epic" not in epic_task.tags:
                console.print(f"[red]Epic '{epic}' not found[/red]")
                raise typer.Exit(1)

            # Remove from old epic if linked
            old_epic_id = task.metadata.get("epic")
            if old_epic_id and old_epic_id != epic:
                old_epic = task_manager.load_task(old_epic_id)
                if old_epic:
                    subtasks = old_epic.metadata.get("subtasks", [])
                    if task_id in subtasks:
                        subtasks.remove(task_id)
                        old_epic.metadata["subtasks"] = subtasks
                        task_manager.save_task(old_epic)

            # Add to new epic
            subtasks = epic_task.metadata.get("subtasks", [])
            if task_id not in subtasks:
                subtasks.append(task_id)
                epic_task.metadata["subtasks"] = subtasks
                task_manager.save_task(epic_task)

            metadata_updates["epic"] = epic
        else:  # If epic is empty string, remove epic link
            # Remove from old epic if linked
            old_epic_id = task.metadata.get("epic")
            if old_epic_id:
                old_epic = task_manager.load_task(old_epic_id)
                if old_epic:
                    subtasks = old_epic.metadata.get("subtasks", [])
                    if task_id in subtasks:
                        subtasks.remove(task_id)
                        old_epic.metadata["subtasks"] = subtasks
                        task_manager.save_task(old_epic)

            metadata_updates["epic"] = None

    if not updates and not metadata_updates:
        console.print("[yellow]No updates specified[/yellow]")
        return

    # Apply metadata updates
    if metadata_updates:
        task.metadata.update(metadata_updates)
        updates["metadata"] = task.metadata

    # Apply updates
    success = task_manager.update_task(task_id, **updates)

    if success:
        console.print(
            Panel.fit(
                f"""[bold green]Task updated successfully![/bold green]

[dim]ID:[/dim] {task_id}""",
                title="Task Updated",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to update task {task_id}[/red]")
        raise typer.Exit(1)


@app.command()
def block(
    task_id: str = typer.Argument(..., help="Task ID to mark as blocked"),
    blocked_by: str = typer.Argument(..., help="Task ID that is blocking this task"),
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r", help="Reason for blocking"
    ),
) -> None:
    """Mark a task as blocked by another task."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    task = task_manager.load_task(task_id)
    blocking_task = task_manager.load_task(blocked_by)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    if not blocking_task:
        console.print(f"[red]Blocking task '{blocked_by}' not found[/red]")
        raise typer.Exit(1)

    # Update blocked task
    blocked_by_list = task.metadata.get("blocked_by", [])
    if blocked_by not in blocked_by_list:
        blocked_by_list.append(blocked_by)
        task.metadata["blocked_by"] = blocked_by_list
        if reason:
            task.metadata["block_reason"] = reason
        task_manager.update_task(task_id, status="blocked", metadata=task.metadata)

    # Update blocking task
    blocks_list = blocking_task.metadata.get("blocks", [])
    if task_id not in blocks_list:
        blocks_list.append(task_id)
        blocking_task.metadata["blocks"] = blocks_list
        task_manager.save_task(blocking_task)

    console.print(f"[yellow]Task {task_id} is now blocked by {blocked_by}[/yellow]")
    if reason:
        console.print(f"[dim]Reason: {reason}[/dim]")


@app.command()
def unblock(
    task_id: str = typer.Argument(..., help="Task ID to unblock"),
    blocked_by: Optional[str] = typer.Argument(
        None, help="Specific blocking task to remove"
    ),
) -> None:
    """Unblock a task."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    task = task_manager.load_task(task_id)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    blocked_by_list = task.metadata.get("blocked_by", [])

    if not blocked_by_list:
        console.print(f"[yellow]Task {task_id} is not blocked[/yellow]")
        return

    if blocked_by:
        # Remove specific blocking task
        if blocked_by in blocked_by_list:
            blocked_by_list.remove(blocked_by)

            # Update blocking task
            blocking_task = task_manager.load_task(blocked_by)
            if blocking_task:
                blocks_list = blocking_task.metadata.get("blocks", [])
                if task_id in blocks_list:
                    blocks_list.remove(task_id)
                    blocking_task.metadata["blocks"] = blocks_list
                    task_manager.save_task(blocking_task)
        else:
            console.print(
                f"[yellow]Task {task_id} is not blocked by {blocked_by}[/yellow]"
            )
            return
    else:
        # Remove all blocking tasks
        for blocking_id in blocked_by_list:
            blocking_task = task_manager.load_task(blocking_id)
            if blocking_task:
                blocks_list = blocking_task.metadata.get("blocks", [])
                if task_id in blocks_list:
                    blocks_list.remove(task_id)
                    blocking_task.metadata["blocks"] = blocks_list
                    task_manager.save_task(blocking_task)

        blocked_by_list = []

    # Update task
    task.metadata["blocked_by"] = blocked_by_list
    if "block_reason" in task.metadata and not blocked_by_list:
        del task.metadata["block_reason"]

    new_status = "open" if not blocked_by_list else "blocked"
    task_manager.update_task(task_id, status=new_status, metadata=task.metadata)

    if blocked_by_list:
        console.print(f"[green]Removed blocking dependency from task {task_id}[/green]")
    else:
        console.print(f"[green]Task {task_id} is no longer blocked[/green]")


@app.command()
def complete(
    task_id: str = typer.Argument(..., help="Task ID to mark as completed"),
    comment: Optional[str] = typer.Option(
        None, "--comment", "-c", help="Completion comment"
    ),
) -> None:
    """Mark a task as completed."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    task = task_manager.load_task(task_id)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    # Add completion metadata
    if comment:
        task.metadata["completion_comment"] = comment
    task.metadata["completed_at"] = task.updated_at.isoformat()

    success = task_manager.update_task(
        task_id, status="completed", metadata=task.metadata
    )

    if success:
        console.print(f"[green]Task {task_id} marked as completed[/green]")
        if comment:
            console.print(f"[dim]Comment: {comment}[/dim]")
    else:
        console.print(f"[red]Failed to complete task {task_id}[/red]")
        raise typer.Exit(1)


@app.command()
def start(
    task_id: str = typer.Argument(..., help="Task ID to start working on"),
    comment: Optional[str] = typer.Option(
        None, "--comment", "-c", help="Start comment"
    ),
) -> None:
    """Start working on a task."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    task = task_manager.load_task(task_id)

    if not task:
        console.print(f"[red]Task '{task_id}' not found[/red]")
        raise typer.Exit(1)

    if task.status == "blocked":
        console.print(f"[red]Cannot start blocked task {task_id}[/red]")
        blocked_by = task.metadata.get("blocked_by", [])
        if blocked_by:
            console.print(f"[dim]Blocked by: {', '.join(blocked_by)}[/dim]")
        raise typer.Exit(1)

    # Add start metadata
    if comment:
        task.metadata["start_comment"] = comment
    task.metadata["started_at"] = task.updated_at.isoformat()

    success = task_manager.update_task(
        task_id, status="in_progress", metadata=task.metadata
    )

    if success:
        console.print(f"[green]Started working on task {task_id}[/green]")
        if comment:
            console.print(f"[dim]Comment: {comment}[/dim]")
    else:
        console.print(f"[red]Failed to start task {task_id}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
