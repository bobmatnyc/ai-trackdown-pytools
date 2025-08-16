"""Portfolio and backlog management commands."""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from ai_trackdown_pytools.core.constants import PRIORITY_ORDER, TicketPriority
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager

app = typer.Typer(help="Portfolio and backlog management")
console = Console()


@app.command()
def overview(
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed statistics"
    ),
    show_completed: bool = typer.Option(
        False, "--completed", "-c", help="Include completed items"
    ),
) -> None:
    """Show portfolio overview and statistics."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    if not show_completed:
        all_tasks = [t for t in all_tasks if t.status != "completed"]

    # Categorize tasks
    epics = [t for t in all_tasks if "epic" in t.tags]
    issues = [t for t in all_tasks if "issue" in t.tags]
    prs = [t for t in all_tasks if "pull-request" in t.tags]
    regular_tasks = [
        t
        for t in all_tasks
        if not any(tag in t.tags for tag in ["epic", "issue", "pull-request"])
    ]

    # Status breakdown
    status_counts = {}
    priority_counts = {}

    for task in all_tasks:
        status_counts[task.status] = status_counts.get(task.status, 0) + 1
        priority_counts[task.priority] = priority_counts.get(task.priority, 0) + 1

    # Calculate epic progress
    epic_progress = []
    for epic in epics:
        subtasks = epic.metadata.get("subtasks", [])
        if subtasks:
            completed = sum(
                1
                for st_id in subtasks
                if task_manager.load_task(st_id)
                and task_manager.load_task(st_id).status == "completed"
            )
            progress = int((completed / len(subtasks)) * 100)
        else:
            progress = 0 if epic.status != "completed" else 100

        epic_progress.append(
            {"epic": epic, "progress": progress, "subtasks": len(subtasks)}
        )

    # Display overview
    console.print(
        Panel.fit(
            f"""[bold blue]Portfolio Overview[/bold blue]

[dim]Total Items:[/dim] {len(all_tasks)}
• Epics: {len(epics)}
• Issues: {len(issues)}
• Pull Requests: {len(prs)}
• Regular Tasks: {len(regular_tasks)}

[dim]Status Breakdown:[/dim]
• Open: {status_counts.get('open', 0)}
• In Progress: {status_counts.get('in_progress', 0)}
• Blocked: {status_counts.get('blocked', 0)}
• Completed: {status_counts.get('completed', 0)}
• Cancelled: {status_counts.get('cancelled', 0)}

[dim]Priority Distribution:[/dim]
• Critical: {priority_counts.get('critical', 0)}
• High: {priority_counts.get('high', 0)}
• Medium: {priority_counts.get('medium', 0)}
• Low: {priority_counts.get('low', 0)}""",
            title="Portfolio Statistics",
            border_style="blue",
        )
    )

    # Show epic progress
    if epics:
        console.print("\n[bold]Epic Progress:[/bold]")

        table = Table()
        table.add_column("Epic", style="blue")
        table.add_column("Progress", style="green")
        table.add_column("Subtasks", style="yellow")
        table.add_column("Status", style="magenta")

        for ep in sorted(epic_progress, key=lambda x: x["progress"], reverse=True):
            epic = ep["epic"]
            progress = ep["progress"]
            subtask_count = ep["subtasks"]

            progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)

            table.add_row(
                epic.title[:30] + "..." if len(epic.title) > 30 else epic.title,
                f"{progress_bar} {progress}%",
                str(subtask_count),
                epic.status,
            )

        console.print(table)

    # Show detailed statistics
    if detailed:
        console.print("\n[bold]Detailed Statistics:[/bold]")

        # Assignee workload
        assignee_counts = {}
        for task in all_tasks:
            for assignee in task.assignees:
                assignee_counts[assignee] = assignee_counts.get(assignee, 0) + 1

        if assignee_counts:
            console.print("\n[dim]Workload by Assignee:[/dim]")
            for assignee, count in sorted(
                assignee_counts.items(), key=lambda x: x[1], reverse=True
            ):
                console.print(f"• {assignee}: {count} tasks")

        # Tag distribution
        tag_counts = {}
        for task in all_tasks:
            for tag in task.tags:
                if tag not in ["epic", "issue", "pull-request"]:  # Skip type tags
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if tag_counts:
            console.print("\n[dim]Most Common Tags:[/dim]")
            for tag, count in sorted(
                tag_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                console.print(f"• {tag}: {count} tasks")


@app.command()
def backlog(
    priority_filter: Optional[str] = typer.Option(
        None, "--priority", "-p", help="Filter by priority"
    ),
    epic_filter: Optional[str] = typer.Option(
        None, "--epic", "-e", help="Filter by epic"
    ),
    assignee_filter: Optional[str] = typer.Option(
        None, "--assignee", "-a", help="Filter by assignee"
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum items to show"),
    grouped: bool = typer.Option(False, "--grouped", "-g", help="Group by priority"),
) -> None:
    """Show prioritized backlog of open tasks."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Filter to open tasks only
    open_tasks = [
        t for t in all_tasks if t.status in ["open", "in_progress", "blocked"]
    ]

    # Apply filters
    if priority_filter:
        open_tasks = [t for t in open_tasks if t.priority == priority_filter]

    if epic_filter:
        open_tasks = [t for t in open_tasks if t.metadata.get("epic") == epic_filter]

    if assignee_filter:
        open_tasks = [t for t in open_tasks if assignee_filter in t.assignees]

    # Sort by priority and creation date
    priority_order = {p.value: v for p, v in PRIORITY_ORDER.items()}
    open_tasks.sort(
        key=lambda t: (priority_order.get(t.priority, 0), t.created_at), reverse=True
    )

    # Limit results
    open_tasks = open_tasks[:limit]

    if not open_tasks:
        console.print("[yellow]No items in backlog[/yellow]")
        return

    if grouped:
        # Group by priority
        priority_groups = {}
        for task in open_tasks:
            priority = task.priority
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(task)

        for priority in [
            p.value
            for p in sorted(
                TicketPriority, key=lambda x: PRIORITY_ORDER[x], reverse=True
            )
        ]:
            if priority in priority_groups:
                tasks = priority_groups[priority]
                console.print(
                    f"\n[bold {_get_priority_color(priority)}]{priority.upper()} PRIORITY ({len(tasks)} items)[/bold {_get_priority_color(priority)}]"
                )

                table = Table(show_header=False)
                table.add_column("", style="cyan", width=8)
                table.add_column("", style="white")
                table.add_column("", style="magenta", width=12)
                table.add_column("", style="blue", width=15)
                table.add_column("", style="dim", width=10)

                for task in tasks:
                    task_type = _get_task_type(task)
                    assignee = (
                        ", ".join(task.assignees[:2])
                        if task.assignees
                        else "Unassigned"
                    )
                    epic = (
                        task.metadata.get("epic", "")[:10]
                        if task.metadata.get("epic")
                        else ""
                    )

                    table.add_row(
                        task.id,
                        task.title[:50] + "..." if len(task.title) > 50 else task.title,
                        task.status,
                        assignee,
                        epic,
                    )

                console.print(table)
    else:
        # Standard backlog view
        table = Table(title=f"Backlog ({len(open_tasks)} items)")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Type", style="blue")
        table.add_column("Priority", style="yellow")
        table.add_column("Status", style="magenta")
        table.add_column("Assignee", style="green")
        table.add_column("Epic", style="dim")

        for task in open_tasks:
            task_type = _get_task_type(task)
            assignee = ", ".join(task.assignees[:2]) if task.assignees else "Unassigned"
            epic = (
                task.metadata.get("epic", "")[:8] if task.metadata.get("epic") else ""
            )

            table.add_row(
                task.id,
                task.title[:40] + "..." if len(task.title) > 40 else task.title,
                task_type,
                task.priority,
                task.status,
                assignee,
                epic,
            )

        console.print(table)


@app.command()
def roadmap(
    epic_only: bool = typer.Option(False, "--epics-only", "-e", help="Show epics only"),
    _timeline: Optional[str] = typer.Option(
        None, "--timeline", "-t", help="Timeline filter (quarter, month)"
    ),
    format: str = typer.Option(
        "tree", "--format", "-f", help="Output format (tree, table)"
    ),
) -> None:
    """Show project roadmap with epics and milestones."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Get epics and their subtasks
    epics = [t for t in all_tasks if "epic" in t.tags]

    if not epics:
        console.print("[yellow]No epics found for roadmap[/yellow]")
        return

    # Sort epics by priority and creation date
    priority_order = {p.value: v for p, v in PRIORITY_ORDER.items()}
    epics.sort(
        key=lambda t: (priority_order.get(t.priority, 0), t.created_at), reverse=True
    )

    if format == "tree":
        # Tree format roadmap
        tree = Tree("[bold blue]Project Roadmap[/bold blue]")

        for epic in epics:
            # Calculate epic progress
            subtasks = epic.metadata.get("subtasks", [])
            if subtasks:
                completed = sum(
                    1
                    for st_id in subtasks
                    if task_manager.load_task(st_id)
                    and task_manager.load_task(st_id).status == "completed"
                )
                progress = int((completed / len(subtasks)) * 100)
            else:
                progress = 0 if epic.status != "completed" else 100

            epic_label = f"[bold]{epic.title}[/bold] ({progress}% complete)"
            epic_node = tree.add(epic_label)

            # Add epic details
            epic_node.add(f"[dim]Status:[/dim] {epic.status}")
            epic_node.add(f"[dim]Priority:[/dim] {epic.priority}")
            if epic.metadata.get("goal"):
                epic_node.add(f"[dim]Goal:[/dim] {epic.metadata.get('goal')}")

            # Add subtasks if not epic-only
            if not epic_only and subtasks:
                subtasks_node = epic_node.add(f"[dim]Subtasks ({len(subtasks)}):[/dim]")

                for subtask_id in subtasks[:10]:  # Limit to first 10 subtasks
                    subtask = task_manager.load_task(subtask_id)
                    if subtask:
                        status_icon = (
                            "✅"
                            if subtask.status == "completed"
                            else "🔄"
                            if subtask.status == "in_progress"
                            else "⭕"
                        )
                        subtasks_node.add(f"{status_icon} {subtask.title[:40]}...")

                if len(subtasks) > 10:
                    subtasks_node.add(f"[dim]... and {len(subtasks) - 10} more[/dim]")

        console.print(tree)

    else:
        # Table format roadmap
        table = Table(title="Project Roadmap")
        table.add_column("Epic", style="blue")
        table.add_column("Goal", style="white")
        table.add_column("Status", style="magenta")
        table.add_column("Priority", style="yellow")
        table.add_column("Progress", style="green")
        table.add_column("Subtasks", style="dim")

        for epic in epics:
            subtasks = epic.metadata.get("subtasks", [])
            if subtasks:
                completed = sum(
                    1
                    for st_id in subtasks
                    if task_manager.load_task(st_id)
                    and task_manager.load_task(st_id).status == "completed"
                )
                progress = int((completed / len(subtasks)) * 100)
            else:
                progress = 0 if epic.status != "completed" else 100

            progress_bar = "█" * (progress // 10) + "░" * (10 - progress // 10)

            table.add_row(
                epic.title[:30] + "..." if len(epic.title) > 30 else epic.title,
                (
                    epic.metadata.get("goal", "")[:40] + "..."
                    if len(epic.metadata.get("goal", "")) > 40
                    else epic.metadata.get("goal", "")
                ),
                epic.status,
                epic.priority,
                f"{progress_bar} {progress}%",
                str(len(subtasks)),
            )

        console.print(table)


@app.command()
def sprint(
    action: str = typer.Argument(..., help="Action (create, show, close, tasks)"),
    sprint_name: Optional[str] = typer.Argument(None, help="Sprint name or number"),
    duration: int = typer.Option(
        14, "--duration", "-d", help="Sprint duration in days"
    ),
    capacity: Optional[int] = typer.Option(
        None, "--capacity", "-c", help="Sprint capacity in story points"
    ),
) -> None:
    """Manage sprints and sprint planning."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Sprint data storage
    sprint_dir = project_path / ".aitrackdown" / "sprints"
    sprint_dir.mkdir(parents=True, exist_ok=True)

    sprints_file = sprint_dir / "sprints.json"

    # Load existing sprints
    if sprints_file.exists():
        with open(sprints_file) as f:
            sprints_data = json.load(f)
    else:
        sprints_data = {"sprints": [], "current_sprint": None}

    task_manager = TaskManager(project_path)

    if action == "create":
        if not sprint_name:
            from datetime import datetime

            sprint_name = f"Sprint-{datetime.now().strftime('%Y%m%d')}"

        # Check if sprint already exists
        existing = next(
            (s for s in sprints_data["sprints"] if s["name"] == sprint_name), None
        )
        if existing:
            console.print(f"[red]Sprint '{sprint_name}' already exists[/red]")
            raise typer.Exit(1)

        from datetime import datetime, timedelta

        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration)

        new_sprint = {
            "name": sprint_name,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "duration": duration,
            "capacity": capacity,
            "status": "active",
            "tasks": [],
            "created_at": start_date.isoformat(),
        }

        sprints_data["sprints"].append(new_sprint)
        sprints_data["current_sprint"] = sprint_name

        # Save sprints data
        with open(sprints_file, "w") as f:
            json.dump(sprints_data, f, indent=2)

        console.print(
            Panel.fit(
                f"""[bold green]Sprint created successfully![/bold green]

[dim]Name:[/dim] {sprint_name}
[dim]Duration:[/dim] {duration} days
[dim]Start Date:[/dim] {start_date.strftime('%Y-%m-%d')}
[dim]End Date:[/dim] {end_date.strftime('%Y-%m-%d')}
[dim]Capacity:[/dim] {capacity or 'Not set'}""",
                title="Sprint Created",
                border_style="green",
            )
        )

    elif action == "show":
        current_sprint_name = sprint_name or sprints_data.get("current_sprint")
        if not current_sprint_name:
            console.print("[yellow]No current sprint found[/yellow]")
            return

        sprint = next(
            (s for s in sprints_data["sprints"] if s["name"] == current_sprint_name),
            None,
        )
        if not sprint:
            console.print(f"[red]Sprint '{current_sprint_name}' not found[/red]")
            raise typer.Exit(1)

        # Calculate sprint progress
        from datetime import datetime

        start_date = datetime.fromisoformat(sprint["start_date"])
        end_date = datetime.fromisoformat(sprint["end_date"])
        now = datetime.now()

        if now < start_date:
            progress = 0
        elif now > end_date:
            progress = 100
        else:
            total_duration = (end_date - start_date).days
            elapsed = (now - start_date).days
            progress = int((elapsed / total_duration) * 100)

        # Get sprint tasks
        sprint_tasks = []
        for task_id in sprint.get("tasks", []):
            task = task_manager.load_task(task_id)
            if task:
                sprint_tasks.append(task)

        completed_tasks = [t for t in sprint_tasks if t.status == "completed"]

        console.print(
            Panel.fit(
                f"""[bold blue]Sprint: {sprint['name']}[/bold blue]

[dim]Status:[/dim] {sprint['status']}
[dim]Duration:[/dim] {sprint['duration']} days
[dim]Start:[/dim] {start_date.strftime('%Y-%m-%d')}
[dim]End:[/dim] {end_date.strftime('%Y-%m-%d')}
[dim]Progress:[/dim] {progress}% complete
[dim]Capacity:[/dim] {sprint.get('capacity', 'Not set')}

[dim]Tasks:[/dim] {len(sprint_tasks)} total, {len(completed_tasks)} completed""",
                title="Sprint Details",
                border_style="blue",
            )
        )

        if sprint_tasks:
            console.print("\n[bold]Sprint Tasks:[/bold]")

            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("Title", style="white")
            table.add_column("Status", style="magenta")
            table.add_column("Priority", style="yellow")
            table.add_column("Assignee", style="green")

            for task in sprint_tasks:
                assignee = ", ".join(task.assignees) if task.assignees else "Unassigned"

                table.add_row(
                    task.id,
                    task.title[:40] + "..." if len(task.title) > 40 else task.title,
                    task.status,
                    task.priority,
                    assignee,
                )

            console.print(table)

    elif action == "tasks":
        # Add/remove tasks from sprint
        current_sprint_name = sprint_name or sprints_data.get("current_sprint")
        if not current_sprint_name:
            console.print("[yellow]No current sprint found[/yellow]")
            return

        console.print(f"[blue]Managing tasks for sprint: {current_sprint_name}[/blue]")
        console.print("This feature allows interactive task management for sprints")
        console.print("Implementation: Add tasks to sprint backlog, remove tasks, etc.")

    elif action == "close":
        current_sprint_name = sprint_name or sprints_data.get("current_sprint")
        if not current_sprint_name:
            console.print("[yellow]No current sprint found[/yellow]")
            return

        # Find and close sprint
        for sprint in sprints_data["sprints"]:
            if sprint["name"] == current_sprint_name:
                sprint["status"] = "closed"
                sprint["closed_at"] = datetime.now().isoformat()
                break

        sprints_data["current_sprint"] = None

        # Save sprints data
        with open(sprints_file, "w") as f:
            json.dump(sprints_data, f, indent=2)

        console.print(
            f"[green]Sprint '{current_sprint_name}' closed successfully[/green]"
        )

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Valid actions: create, show, close, tasks")
        raise typer.Exit(1)


def _get_task_type(task) -> str:
    """Get display type for a task."""
    if "epic" in task.tags:
        return "Epic"
    elif "issue" in task.tags:
        return "Issue"
    elif "pull-request" in task.tags:
        return "PR"
    else:
        return "Task"


def _get_priority_color(priority: str) -> str:
    """Get color for priority display."""
    colors = {
        TicketPriority.CRITICAL.value: "red",
        TicketPriority.HIGH.value: "yellow",
        TicketPriority.MEDIUM.value: "blue",
        TicketPriority.LOW.value: "green",
    }
    return colors.get(priority, "white")


if __name__ == "__main__":
    app()
