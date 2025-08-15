"""Issue tracking and management commands."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Issue tracking and management")
console = Console()


@app.command()
def create(
    title: Optional[str] = typer.Argument(None, help="Issue title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Issue description",
    ),
    issue_type: Optional[str] = typer.Option(
        "bug",
        "--type",
        help="Issue type (bug, feature, enhancement, documentation)",
    ),
    severity: Optional[str] = typer.Option(
        "medium",
        "--severity",
        "-s",
        help="Issue severity (low, medium, high, critical)",
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Issue assignee",
    ),
    label: Optional[List[str]] = typer.Option(
        None,
        "--label",
        "-l",
        help="Issue label (can be specified multiple times)",
    ),
    component: Optional[str] = typer.Option(
        None,
        "--component",
        "-c",
        help="Affected component",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Issue template to use",
    ),
    relates_to: Optional[str] = typer.Option(
        None,
        "--relates-to",
        help="Related task/issue ID",
    ),
) -> None:
    """Create a new issue."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    if not title:
        from rich.prompt import Prompt

        title = Prompt.ask("Issue title")

    if not description:
        from rich.prompt import Prompt

        description = Prompt.ask("Issue description", default="")

    # Build issue tags
    issue_tags = ["issue", issue_type or "bug"]
    if label:
        issue_tags.extend(label)

    # Apply template if specified
    issue_data = {
        "title": title,
        "description": description,
        "tags": issue_tags,
        "priority": severity or "medium",
        "assignees": [assignee] if assignee else [],
        "metadata": {
            "type": "issue",
            "issue_type": issue_type,
            "severity": severity,
            "component": component,
            "labels": label or [],
            "relates_to": relates_to,
            "resolution": None,
            "reported_by": None,
        },
    }

    if template:
        template_manager = TemplateManager()
        template_data = template_manager.load_template("issue", template)
        if template_data:
            issue_data.update(template_data)
            console.print(f"[green]Applied template: {template}[/green]")

    new_issue = task_manager.create_task(type="issue", **issue_data)

    console.print(
        Panel.fit(
            f"""[bold green]Issue created successfully![/bold green]

[dim]ID:[/dim] {new_issue.id}
[dim]Title:[/dim] {new_issue.title}
[dim]Type:[/dim] {issue_type}
[dim]Severity:[/dim] {severity}
[dim]Component:[/dim] {component or 'None'}
[dim]Assignee:[/dim] {assignee or 'Unassigned'}
[dim]File:[/dim] {new_issue.file_path}""",
            title="Issue Created",
            border_style="red",
        )
    )


@app.command()
def list(
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    type_filter: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by issue type"
    ),
    severity_filter: Optional[str] = typer.Option(
        None, "--severity", help="Filter by severity"
    ),
    assignee_filter: Optional[str] = typer.Option(
        None, "--assignee", "-a", help="Filter by assignee"
    ),
    component_filter: Optional[str] = typer.Option(
        None, "--component", "-c", help="Filter by component"
    ),
    show_closed: bool = typer.Option(False, "--closed", help="Include closed issues"),
    limit: int = typer.Option(
        50, "--limit", "-l", help="Maximum number of issues to show"
    ),
) -> None:
    """List issues with optional filtering."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Filter issues
    issues = [task for task in all_tasks if "issue" in task.tags]

    # Apply filters
    if status_filter:
        issues = [issue for issue in issues if issue.status == status_filter]

    if type_filter:
        issues = [
            issue for issue in issues if issue.metadata.get("issue_type") == type_filter
        ]

    if severity_filter:
        issues = [
            issue
            for issue in issues
            if issue.metadata.get("severity") == severity_filter
        ]

    if assignee_filter:
        issues = [issue for issue in issues if assignee_filter in issue.assignees]

    if component_filter:
        issues = [
            issue
            for issue in issues
            if issue.metadata.get("component") == component_filter
        ]

    if not show_closed:
        issues = [
            issue for issue in issues if issue.status not in ["completed", "cancelled"]
        ]

    # Limit results
    issues = issues[:limit]

    if not issues:
        console.print("[yellow]No issues found[/yellow]")
        return

    table = Table(title=f"Issues ({len(issues)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Type", style="blue")
    table.add_column("Severity", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Assignee", style="yellow")
    table.add_column("Component", style="dim")

    for issue in issues:
        assignee = ", ".join(issue.assignees) if issue.assignees else "Unassigned"

        table.add_row(
            issue.id,
            issue.title[:30] + "..." if len(issue.title) > 30 else issue.title,
            issue.metadata.get("issue_type", "unknown"),
            issue.metadata.get("severity", "unknown"),
            issue.status,
            assignee[:15] + "..." if len(assignee) > 15 else assignee,
            issue.metadata.get("component", ""),
        )

    console.print(table)


@app.command()
def show(
    issue_id: str = typer.Argument(..., help="Issue ID to display"),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed information"
    ),
) -> None:
    """Show detailed issue information."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    issue = task_manager.load_task(issue_id)

    if not issue or "issue" not in issue.tags:
        console.print(f"[red]Issue '{issue_id}' not found[/red]")
        raise typer.Exit(1)

    assignees = ", ".join(issue.assignees) if issue.assignees else "Unassigned"
    labels = (
        ", ".join(issue.metadata.get("labels", []))
        if issue.metadata.get("labels")
        else "None"
    )

    info_text = f"""[bold red]Issue Details[/bold red]

[dim]ID:[/dim] {issue.id}
[dim]Title:[/dim] {issue.title}
[dim]Type:[/dim] {issue.metadata.get('issue_type', 'unknown')}
[dim]Severity:[/dim] {issue.metadata.get('severity', 'unknown')}
[dim]Status:[/dim] {issue.status}
[dim]Priority:[/dim] {issue.priority}
[dim]Component:[/dim] {issue.metadata.get('component', 'None')}
[dim]Assignees:[/dim] {assignees}
[dim]Labels:[/dim] {labels}
[dim]Created:[/dim] {issue.created_at.strftime('%Y-%m-%d %H:%M')}
[dim]Updated:[/dim] {issue.updated_at.strftime('%Y-%m-%d %H:%M')}"""

    if issue.metadata.get("relates_to"):
        info_text += f"\n[dim]Related to:[/dim] {issue.metadata.get('relates_to')}"

    if issue.metadata.get("resolution"):
        info_text += f"\n[dim]Resolution:[/dim] {issue.metadata.get('resolution')}"

    # Show subtasks if they exist
    if issue.metadata.get("subtasks"):
        subtasks_count = len(issue.metadata["subtasks"])
        info_text += f"\n[dim]Subtasks:[/dim] {subtasks_count} task(s)"
        if detailed:
            info_text += f" - {', '.join(issue.metadata['subtasks'])}"

    if detailed:
        info_text += f"\n\n[dim]Description:[/dim]\n{issue.description}"

        if issue.metadata.get("reported_by"):
            info_text += (
                f"\n\n[dim]Reported by:[/dim] {issue.metadata.get('reported_by')}"
            )

    console.print(Panel.fit(info_text, title="Issue Information", border_style="red"))


@app.command()
def update(
    issue_id: str = typer.Argument(..., help="Issue ID to update"),
    title: Optional[str] = typer.Option(None, "--title", help="Update issue title"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Update issue description"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Update issue status"
    ),
    severity: Optional[str] = typer.Option(
        None, "--severity", help="Update issue severity"
    ),
    assignee: Optional[str] = typer.Option(
        None, "--assignee", "-a", help="Update issue assignee"
    ),
    component: Optional[str] = typer.Option(
        None, "--component", "-c", help="Update affected component"
    ),
    resolution: Optional[str] = typer.Option(
        None, "--resolution", "-r", help="Set issue resolution"
    ),
    epic: Optional[str] = typer.Option(None, "--epic", "-e", help="Link issue to epic"),
    add_label: Optional[List[str]] = typer.Option(
        None, "--add-label", help="Add labels to issue"
    ),
    remove_label: Optional[List[str]] = typer.Option(
        None, "--remove-label", help="Remove labels from issue"
    ),
) -> None:
    """Update an existing issue."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    issue = task_manager.load_task(issue_id)

    if not issue or "issue" not in issue.tags:
        console.print(f"[red]Issue '{issue_id}' not found[/red]")
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
    if severity:
        if severity not in ["low", "medium", "high", "critical"]:
            console.print(f"[red]Invalid severity: {severity}[/red]")
            console.print("Valid severities: low, medium, high, critical")
            raise typer.Exit(1)
        metadata_updates["severity"] = severity
        updates["priority"] = severity  # Sync priority with severity
    if assignee:
        updates["assignees"] = [assignee] if assignee else []
    if component:
        metadata_updates["component"] = component
    if resolution:
        metadata_updates["resolution"] = resolution

    # Handle label updates
    if add_label or remove_label:
        current_labels = set(issue.metadata.get("labels", []))
        if add_label:
            current_labels.update(add_label)
        if remove_label:
            current_labels.difference_update(remove_label)
        metadata_updates["labels"] = list(current_labels)

    # Handle epic linking
    if epic is not None:
        if epic:  # If epic is specified (not empty string)
            # Validate epic exists
            epic_task = task_manager.load_task(epic)
            if not epic_task or "epic" not in epic_task.tags:
                console.print(f"[red]Epic '{epic}' not found[/red]")
                raise typer.Exit(1)

            # Remove from old epic if linked
            old_epic_id = issue.metadata.get("epic")
            if old_epic_id and old_epic_id != epic:
                old_epic = task_manager.load_task(old_epic_id)
                if old_epic:
                    subtasks = old_epic.metadata.get("subtasks", [])
                    if issue_id in subtasks:
                        subtasks.remove(issue_id)
                        old_epic.metadata["subtasks"] = subtasks
                        task_manager.save_task(old_epic)

            # Add to new epic
            subtasks = epic_task.metadata.get("subtasks", [])
            if issue_id not in subtasks:
                subtasks.append(issue_id)
                epic_task.metadata["subtasks"] = subtasks
                task_manager.save_task(epic_task)

            metadata_updates["epic"] = epic
        else:  # If epic is empty string, remove epic link
            # Remove from old epic if linked
            old_epic_id = issue.metadata.get("epic")
            if old_epic_id:
                old_epic = task_manager.load_task(old_epic_id)
                if old_epic:
                    subtasks = old_epic.metadata.get("subtasks", [])
                    if issue_id in subtasks:
                        subtasks.remove(issue_id)
                        old_epic.metadata["subtasks"] = subtasks
                        task_manager.save_task(old_epic)

            metadata_updates["epic"] = None

    if not updates and not metadata_updates:
        console.print("[yellow]No updates specified[/yellow]")
        return

    # Apply metadata updates
    if metadata_updates:
        issue.metadata.update(metadata_updates)
        updates["metadata"] = issue.metadata

    # Apply updates
    success = task_manager.update_task(issue_id, **updates)

    if success:
        console.print(
            Panel.fit(
                f"""[bold green]Issue updated successfully![/bold green]

[dim]ID:[/dim] {issue_id}""",
                title="Issue Updated",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to update issue {issue_id}[/red]")
        raise typer.Exit(1)


@app.command()
def resolve(
    issue_id: str = typer.Argument(..., help="Issue ID to resolve"),
    resolution: str = typer.Option(
        ..., "--resolution", "-r", help="Resolution description"
    ),
    resolution_type: str = typer.Option(
        "fixed",
        "--type",
        "-t",
        help="Resolution type (fixed, wontfix, duplicate, invalid)",
    ),
) -> None:
    """Resolve an issue with a specific resolution."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    issue = task_manager.load_task(issue_id)

    if not issue or "issue" not in issue.tags:
        console.print(f"[red]Issue '{issue_id}' not found[/red]")
        raise typer.Exit(1)

    # Update issue with resolution
    issue.metadata.update(
        {
            "resolution": resolution,
            "resolution_type": resolution_type,
            "resolved_at": issue.updated_at.isoformat(),
        }
    )

    status = "completed" if resolution_type == "fixed" else "cancelled"

    success = task_manager.update_task(issue_id, status=status, metadata=issue.metadata)

    if success:
        console.print(
            Panel.fit(
                f"""[bold green]Issue resolved successfully![/bold green]

[dim]ID:[/dim] {issue_id}
[dim]Status:[/dim] {status}
[dim]Resolution:[/dim] {resolution}
[dim]Type:[/dim] {resolution_type}""",
                title="Issue Resolved",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to resolve issue {issue_id}[/red]")
        raise typer.Exit(1)


@app.command()
def close(
    issue_id: str = typer.Argument(..., help="Issue ID to close"),
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r", help="Reason for closing"
    ),
) -> None:
    """Close an issue."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    issue = task_manager.load_task(issue_id)

    if not issue or "issue" not in issue.tags:
        console.print(f"[red]Issue '{issue_id}' not found[/red]")
        raise typer.Exit(1)

    # Update issue metadata
    if reason:
        issue.metadata["close_reason"] = reason
    issue.metadata["closed_at"] = issue.updated_at.isoformat()

    success = task_manager.update_task(
        issue_id, status="completed", metadata=issue.metadata
    )

    if success:
        console.print(f"[green]Issue {issue_id} closed successfully[/green]")
        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")
    else:
        console.print(f"[red]Failed to close issue {issue_id}[/red]")
        raise typer.Exit(1)


@app.command()
def reopen(
    issue_id: str = typer.Argument(..., help="Issue ID to reopen"),
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r", help="Reason for reopening"
    ),
) -> None:
    """Reopen a closed issue."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    issue = task_manager.load_task(issue_id)

    if not issue or "issue" not in issue.tags:
        console.print(f"[red]Issue '{issue_id}' not found[/red]")
        raise typer.Exit(1)

    if issue.status not in ["completed", "cancelled"]:
        console.print(f"[yellow]Issue {issue_id} is not closed[/yellow]")
        return

    # Update issue metadata
    if reason:
        issue.metadata["reopen_reason"] = reason
    issue.metadata["reopened_at"] = issue.updated_at.isoformat()

    # Clear resolution if exists
    if "resolution" in issue.metadata:
        del issue.metadata["resolution"]
    if "resolution_type" in issue.metadata:
        del issue.metadata["resolution_type"]

    success = task_manager.update_task(issue_id, status="open", metadata=issue.metadata)

    if success:
        console.print(f"[green]Issue {issue_id} reopened successfully[/green]")
        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")
    else:
        console.print(f"[red]Failed to reopen issue {issue_id}[/red]")
        raise typer.Exit(1)


@app.command(name="add-task")
def add_task(
    issue_id: str = typer.Argument(..., help="Issue ID to add tasks to"),
    task_ids: List[str] = typer.Argument(..., help="Task IDs to add to the issue"),
) -> None:
    """Add tasks to an issue."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    # Load and validate issue
    issue = task_manager.load_task(issue_id)
    if not issue or "issue" not in issue.tags:
        console.print(f"[red]Issue '{issue_id}' not found[/red]")
        raise typer.Exit(1)

    # Initialize subtasks list if not present
    if "subtasks" not in issue.metadata:
        issue.metadata["subtasks"] = []

    # Track successfully added tasks
    added_tasks = []
    failed_tasks = []

    # Process each task
    for task_id in task_ids:
        try:
            task = task_manager.load_task(task_id)
        except Exception:
            console.print(
                f"[yellow]Warning: Task '{task_id}' not found, skipping[/yellow]"
            )
            failed_tasks.append(task_id)
            continue

        # Check if task is already linked to this issue
        if task_id in issue.metadata["subtasks"]:
            console.print(
                f"[yellow]Task '{task_id}' is already linked to issue '{issue_id}'[/yellow]"
            )
            continue

        # Update task's parent field
        task.parent = issue_id
        if task_manager.update_task(task_id, parent=issue_id):
            # Add task to issue's subtasks
            issue.metadata["subtasks"].append(task_id)
            added_tasks.append(task_id)
        else:
            console.print(f"[red]Failed to update task '{task_id}'[/red]")
            failed_tasks.append(task_id)

    # Update issue with new subtasks list
    if added_tasks:
        success = task_manager.update_task(issue_id, metadata=issue.metadata)

        if success:
            console.print(
                Panel.fit(
                    f"""[bold green]Tasks added successfully![/bold green]

[dim]Issue:[/dim] {issue_id}
[dim]Added tasks:[/dim] {', '.join(added_tasks)}
[dim]Total subtasks:[/dim] {len(issue.metadata['subtasks'])}""",
                    title="Tasks Added",
                    border_style="green",
                )
            )
        else:
            console.print(f"[red]Failed to update issue {issue_id}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]No tasks were added[/yellow]")

    if failed_tasks:
        console.print(f"[red]Failed tasks: {', '.join(failed_tasks)}[/red]")


@app.command(name="remove-task")
def remove_task(
    issue_id: str = typer.Argument(..., help="Issue ID to remove tasks from"),
    task_ids: List[str] = typer.Argument(..., help="Task IDs to remove from the issue"),
) -> None:
    """Remove tasks from an issue."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    # Load and validate issue
    issue = task_manager.load_task(issue_id)
    if not issue or "issue" not in issue.tags:
        console.print(f"[red]Issue '{issue_id}' not found[/red]")
        raise typer.Exit(1)

    # Check if issue has subtasks
    if "subtasks" not in issue.metadata or not issue.metadata["subtasks"]:
        console.print(f"[yellow]Issue '{issue_id}' has no subtasks[/yellow]")
        return

    # Track successfully removed tasks
    removed_tasks = []
    failed_tasks = []
    not_found_tasks = []

    # Process each task
    for task_id in task_ids:
        # Check if task is in issue's subtasks
        if task_id not in issue.metadata["subtasks"]:
            console.print(
                f"[yellow]Task '{task_id}' is not linked to issue '{issue_id}'[/yellow]"
            )
            not_found_tasks.append(task_id)
            continue

        # Load task to update its parent field
        try:
            task = task_manager.load_task(task_id)
        except Exception:
            console.print(
                f"[yellow]Warning: Task '{task_id}' not found in database[/yellow]"
            )
            # Still remove from issue's subtasks list
            issue.metadata["subtasks"].remove(task_id)
            removed_tasks.append(task_id)
            continue

        # Clear task's parent field
        task.parent = None
        if task_manager.update_task(task_id, parent=None):
            # Remove task from issue's subtasks
            issue.metadata["subtasks"].remove(task_id)
            removed_tasks.append(task_id)
        else:
            console.print(f"[red]Failed to update task '{task_id}'[/red]")
            failed_tasks.append(task_id)

    # Update issue with new subtasks list
    if removed_tasks:
        success = task_manager.update_task(issue_id, metadata=issue.metadata)

        if success:
            console.print(
                Panel.fit(
                    f"""[bold green]Tasks removed successfully![/bold green]

[dim]Issue:[/dim] {issue_id}
[dim]Removed tasks:[/dim] {', '.join(removed_tasks)}
[dim]Remaining subtasks:[/dim] {len(issue.metadata['subtasks'])}""",
                    title="Tasks Removed",
                    border_style="green",
                )
            )
        else:
            console.print(f"[red]Failed to update issue {issue_id}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]No tasks were removed[/yellow]")

    if failed_tasks:
        console.print(f"[red]Failed to update tasks: {', '.join(failed_tasks)}[/red]")

    if not_found_tasks:
        console.print(
            f"[dim]Tasks not linked to issue: {', '.join(not_found_tasks)}[/dim]"
        )


if __name__ == "__main__":
    app()
