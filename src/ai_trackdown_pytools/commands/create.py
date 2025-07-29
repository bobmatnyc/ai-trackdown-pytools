"""Create new tasks, projects, or issues."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ai_trackdown_pytools.core.constants import (
    DEFAULT_PRIORITY,
    VALID_STATUSES,
    TicketPriority,
    TicketType,
)
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.editor import EditorUtils
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Create new tasks, projects, or issues")
console = Console()


@app.command()
def task(
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
        DEFAULT_PRIORITY.value,
        "--priority",
        "-p",
        help=f"Task priority ({', '.join([p.value for p in TicketPriority])})",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Task template to use",
    ),
    issue: Optional[str] = typer.Option(
        None,
        "--issue",
        help="Associate task with an issue (issue ID)",
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
        "-e",
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

    # Validate issue if provided
    issue_task = None
    if issue:
        try:
            issue_task = task_manager.load_task(issue)
            # Verify it's actually an issue
            if issue_task.metadata.get("type") != "issue":
                console.print(f"[red]Error: {issue} is not an issue[/red]")
                raise typer.Exit(1)
        except Exception as err:
            console.print(f"[red]Error: Issue {issue} not found[/red]")
            raise typer.Exit(1) from err

    # Interactive mode
    if interactive or not title:
        title = title or Prompt.ask("Task title")
        description = description or Prompt.ask("Task description", default="")
        priority = Prompt.ask(
            "Priority",
            choices=[p.value for p in TicketPriority],
            default=priority or DEFAULT_PRIORITY.value,
        )

        assignee_input = Prompt.ask("Assignees (comma-separated)", default="")
        if assignee_input:
            assignee = [a.strip() for a in assignee_input.split(",")]

        tag_input = Prompt.ask("Tags (comma-separated)", default="")
        if tag_input:
            tag = [t.strip() for t in tag_input.split(",")]

    # Create task
    task_data = {
        "title": title,
        "description": description or "",
        "assignees": assignee or [],
        "tags": tag or [],
        "priority": priority or DEFAULT_PRIORITY.value,
    }

    # Set parent if issue is provided
    if issue:
        task_data["parent"] = issue

    # Apply template if specified
    if template:
        template_manager = TemplateManager()
        template_data = template_manager.load_template("task", template)
        if template_data:
            task_data.update(template_data)
            console.print(f"[green]Applied template: {template}[/green]")

    new_task = task_manager.create_task(**task_data)

    # Update issue's subtasks list if associated with an issue
    if issue and issue_task:
        # Get current subtasks list from issue metadata
        issue_metadata = issue_task.metadata.copy()
        subtasks = issue_metadata.get("subtasks", [])

        # Add new task to subtasks if not already there
        if new_task.id not in subtasks:
            subtasks.append(new_task.id)
            issue_metadata["subtasks"] = subtasks

            # Update the issue with new metadata
            task_manager.update_task(issue, metadata=issue_metadata)

    # Build display message
    display_parts = [
        f"""[bold green]Task created successfully![/bold green]

[dim]ID:[/dim] {new_task.id}
[dim]Title:[/dim] {new_task.title}
[dim]Priority:[/dim] {new_task.priority}
[dim]Status:[/dim] {new_task.status}"""
    ]

    if issue:
        display_parts.append(f"[dim]Issue:[/dim] {issue}")

    display_parts.append(f"[dim]File:[/dim] {new_task.file_path}")

    console.print(
        Panel.fit(
            "\n".join(display_parts),
            title="Task Created",
            border_style="green",
        )
    )

    # Open in editor if requested
    if edit:
        EditorUtils.open_file(new_task.file_path)


@app.command()
def issue(
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
    label: Optional[List[str]] = typer.Option(
        None,
        "--label",
        "-l",
        help="Issue label (can be specified multiple times)",
    ),
    _template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Issue template to use",
    ),
    epic: Optional[str] = typer.Option(
        None,
        "--epic",
        help="Associate issue with an epic (epic ID)",
    ),
) -> None:
    """Create a new issue."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # For now, create as a task with issue-specific metadata
    task_manager = TaskManager(project_path)

    # Validate epic if provided
    epic_task = None
    if epic:
        try:
            epic_task = task_manager.load_task(epic)
            # Verify it's actually an epic
            if epic_task.metadata.get("type") != "epic":
                console.print(f"[red]Error: {epic} is not an epic[/red]")
                raise typer.Exit(1)
        except Exception as err:
            console.print(f"[red]Error: Epic {epic} not found[/red]")
            raise typer.Exit(1) from err

    if not title:
        title = Prompt.ask("Issue title")

    if not description:
        description = Prompt.ask("Issue description", default="")

    # Create issue as a task with specific tags
    issue_tags = ["issue", issue_type or "bug"]
    if label:
        issue_tags.extend(label)

    # Add epic to metadata and set parent if epic is provided
    issue_metadata = {
        "type": TicketType.ISSUE.value,
        "issue_type": issue_type,
        "severity": severity,
    }

    create_kwargs = {
        "type": TicketType.ISSUE.value,
        "title": title,
        "description": description,
        "tags": issue_tags,
        "priority": severity or DEFAULT_PRIORITY.value,
        "metadata": issue_metadata,
    }

    # Set parent if epic is provided
    if epic:
        create_kwargs["parent"] = epic

    new_issue = task_manager.create_task(**create_kwargs)

    # Update epic's subtasks list if associated with an epic
    if epic and epic_task:
        # Get current subtasks list from epic metadata
        epic_metadata = epic_task.metadata.copy()
        subtasks = epic_metadata.get("subtasks", [])

        # Add new issue to subtasks if not already there
        if new_issue.id not in subtasks:
            subtasks.append(new_issue.id)
            epic_metadata["subtasks"] = subtasks

            # Update the epic with new metadata
            task_manager.update_task(epic, metadata=epic_metadata)

    # Build display message
    display_parts = [
        f"""[bold green]Issue created successfully![/bold green]

[dim]ID:[/dim] {new_issue.id}
[dim]Title:[/dim] {new_issue.title}
[dim]Type:[/dim] {issue_type}
[dim]Severity:[/dim] {severity}"""
    ]

    if epic:
        display_parts.append(f"[dim]Epic:[/dim] {epic}")

    display_parts.append(f"[dim]File:[/dim] {new_issue.file_path}")

    console.print(
        Panel.fit(
            "\n".join(display_parts),
            title="Issue Created",
            border_style="red",
        )
    )


@app.command()
def epic(
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
    _template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Epic template to use",
    ),
) -> None:
    """Create a new epic (large feature or initiative)."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    if not title:
        title = Prompt.ask("Epic title")

    if not description:
        description = Prompt.ask("Epic description", default="")

    if not goal:
        goal = Prompt.ask("Epic goal", default="")

    # Create epic as a task with specific metadata
    new_epic = task_manager.create_task(
        type=TicketType.EPIC.value,
        title=title,
        description=description,
        tags=["epic"],
        priority="high",
        metadata={
            "type": "epic",
            "goal": goal,
            "subtasks": [],
        },
    )

    console.print(
        Panel.fit(
            f"""[bold green]Epic created successfully![/bold green]

[dim]ID:[/dim] {new_epic.id}
[dim]Title:[/dim] {new_epic.title}
[dim]Goal:[/dim] {goal}
[dim]File:[/dim] {new_epic.file_path}

[dim]Next steps:[/dim]
1. Break down into tasks: [cyan]aitrackdown create task --epic {new_epic.id}[/cyan]
2. View epic status: [cyan]aitrackdown status epic {new_epic.id}[/cyan]""",
            title="Epic Created",
            border_style="blue",
        )
    )


@app.command()
def pr(
    title: Optional[str] = typer.Argument(None, help="Pull request title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Pull request description",
    ),
    branch: Optional[str] = typer.Option(
        None,
        "--branch",
        "-b",
        help="Source branch for pull request",
    ),
    target: Optional[str] = typer.Option(
        "main",
        "--target",
        "-t",
        help="Target branch for pull request",
    ),
    _template: Optional[str] = typer.Option(
        None,
        "--template",
        help="PR template to use",
    ),
) -> None:
    """Create a new pull request template."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    from ai_trackdown_pytools.utils.git import GitUtils

    git_utils = GitUtils(project_path)

    if not git_utils.is_git_repo():
        console.print("[red]Not a git repository[/red]")
        raise typer.Exit(1)

    # Get current branch if not specified
    if not branch:
        branch = git_utils.get_current_branch()

    if not title:
        title = Prompt.ask("Pull request title")

    if not description:
        description = Prompt.ask("Pull request description", default="")

    # Create PR as a task with specific metadata
    task_manager = TaskManager(project_path)

    new_pr = task_manager.create_task(
        type=TicketType.PR.value,  # Specify PR type for correct ID generation
        title=f"PR: {title}",
        description=description,
        tags=["pull-request", "review"],
        priority=DEFAULT_PRIORITY.value,
        metadata={
            "type": "pull_request",
            "source_branch": branch,
            "target_branch": target,
            "status": "draft",
        },
    )

    console.print(
        Panel.fit(
            f"""[bold green]Pull request task created![/bold green]

[dim]ID:[/dim] {new_pr.id}
[dim]Title:[/dim] {title}
[dim]Source:[/dim] {branch}
[dim]Target:[/dim] {target}
[dim]File:[/dim] {new_pr.file_path}

[dim]Next steps:[/dim]
1. Review changes: [cyan]git diff {target}..{branch}[/cyan]
2. Update PR description in task file
3. Mark ready when complete: [cyan]aitrackdown task update {new_pr.id} --status ready[/cyan]""",
            title="PR Task Created",
            border_style="purple",
        )
    )


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

    if title:
        updates["title"] = title
    if description:
        updates["description"] = description
    if status:
        valid_statuses = [s.value for s in VALID_STATUSES.get(TicketType.TASK, [])]
        if status not in valid_statuses:
            console.print(f"[red]Invalid status: {status}[/red]")
            console.print(
                "Valid statuses: open, in_progress, completed, cancelled, blocked"
            )
            raise typer.Exit(1)
        updates["status"] = status
    if priority:
        if priority not in [p.value for p in TicketPriority]:
            console.print(f"[red]Invalid priority: {priority}[/red]")
            console.print("Valid priorities: low, medium, high, critical")
            raise typer.Exit(1)
        updates["priority"] = priority
    if assignee is not None:
        updates["assignees"] = assignee

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

    if not updates:
        console.print("[yellow]No updates specified[/yellow]")
        return

    # Apply updates
    success = task_manager.update_task(task_id, **updates)

    if success:
        console.print(
            Panel.fit(
                f"""[bold green]Task updated successfully![/bold green]

[dim]ID:[/dim] {task_id}
[dim]Updates applied:[/dim] {', '.join(updates.keys())}""",
                title="Task Updated",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to update task {task_id}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
