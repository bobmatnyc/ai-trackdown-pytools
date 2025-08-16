"""Bug tracking and management commands."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Bug tracking and management")
console = Console()


@app.command()
def create(
    title: Optional[str] = typer.Argument(None, help="Bug title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Bug description",
    ),
    severity: Optional[str] = typer.Option(
        "medium",
        "--severity",
        "-s",
        help="Bug severity (critical, high, medium, low)",
    ),
    environment: Optional[str] = typer.Option(
        None,
        "--environment",
        "-e",
        help="Environment where bug occurs (production, staging, development, etc.)",
    ),
    steps_to_reproduce: Optional[str] = typer.Option(
        None,
        "--steps",
        help="Steps to reproduce the bug",
    ),
    expected_behavior: Optional[str] = typer.Option(
        None,
        "--expected",
        help="Expected behavior",
    ),
    actual_behavior: Optional[str] = typer.Option(
        None,
        "--actual",
        help="Actual behavior",
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Bug assignee",
    ),
    label: Optional[List[str]] = typer.Option(
        None,
        "--label",
        "-l",
        help="Bug label (can be specified multiple times)",
    ),
    affects_version: Optional[List[str]] = typer.Option(
        None,
        "--affects-version",
        help="Affected version(s) (can be specified multiple times)",
    ),
    regression: bool = typer.Option(
        False,
        "--regression",
        help="Mark as regression bug",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="Bug template to use",
    ),
    relates_to: Optional[str] = typer.Option(
        None,
        "--relates-to",
        help="Related issue/bug ID",
    ),
) -> None:
    """Create a new bug report."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    if not title:
        from rich.prompt import Prompt

        title = Prompt.ask("Bug title")

    if not description:
        from rich.prompt import Prompt

        description = Prompt.ask("Bug description", default="")

    # Build bug tags
    bug_tags = ["bug"]
    if regression:
        bug_tags.append("regression")
    if label:
        bug_tags.extend(label)

    # Apply template if specified
    bug_data = {
        "title": title,
        "description": description,
        "tags": bug_tags,
        "priority": severity or "medium",
        "assignees": [assignee] if assignee else [],
        "metadata": {
            "type": "bug",
            "severity": severity or "medium",
            "environment": environment or "",
            "steps_to_reproduce": steps_to_reproduce or "",
            "expected_behavior": expected_behavior or "",
            "actual_behavior": actual_behavior or "",
            "affected_versions": affects_version or [],
            "is_regression": regression,
        },
    }

    if relates_to:
        bug_data["metadata"]["related_issues"] = [relates_to]

    if template:
        template_manager = TemplateManager(project_path)
        template_path = template_manager.get_template_path("bug", template)
        if template_path:
            bug_data = template_manager.apply_template(template_path, bug_data)

    # Create the bug
    bug_id = task_manager.create_task(
        title=bug_data["title"],
        description=bug_data.get("description", ""),
        ticket_type="bug",
        tags=bug_data.get("tags", []),
        priority=bug_data.get("priority", "medium"),
        assignees=bug_data.get("assignees", []),
        metadata=bug_data.get("metadata", {}),
    )

    if bug_id:
        console.print(
            Panel(
                f"[green]Created bug {bug_id}[/green]\n"
                f"Title: {title}\n"
                f"Severity: {severity or 'medium'}",
                title="Bug Created",
                border_style="green",
            )
        )
    else:
        console.print("[red]Failed to create bug[/red]")
        raise typer.Exit(1)


@app.command()
def list(
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (open, in_progress, completed, closed, etc.)",
    ),
    severity: Optional[str] = typer.Option(
        None,
        "--severity",
        help="Filter by severity (critical, high, medium, low)",
    ),
    assignee: Optional[str] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="Filter by assignee",
    ),
    regression: Optional[bool] = typer.Option(
        None,
        "--regression",
        help="Filter regression bugs only",
    ),
    verified: Optional[bool] = typer.Option(
        None,
        "--verified",
        help="Filter by verification status",
    ),
    format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format (table, json, csv)",
    ),
) -> None:
    """List bugs with optional filters."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    # Get all bugs
    bugs = task_manager.list_tasks(ticket_type="bug")

    # Apply filters
    if status:
        bugs = [b for b in bugs if b.get("status", "").lower() == status.lower()]

    if severity:
        bugs = [
            b
            for b in bugs
            if b.get("metadata", {}).get("severity", "").lower() == severity.lower()
        ]

    if assignee:
        bugs = [b for b in bugs if assignee in b.get("assignees", [])]

    if regression is not None:
        bugs = [
            b
            for b in bugs
            if b.get("metadata", {}).get("is_regression", False) == regression
        ]

    if verified is not None:
        bugs = [
            b
            for b in bugs
            if b.get("metadata", {}).get("verified_fixed", False) == verified
        ]

    if format == "json":
        import json

        console.print(json.dumps(bugs, indent=2))
    elif format == "csv":
        import csv
        import sys

        writer = csv.writer(sys.stdout)
        writer.writerow(
            [
                "ID",
                "Title",
                "Status",
                "Severity",
                "Assignee",
                "Environment",
                "Regression",
            ]
        )
        for bug in bugs:
            writer.writerow(
                [
                    bug.get("id", ""),
                    bug.get("title", ""),
                    bug.get("status", ""),
                    bug.get("metadata", {}).get("severity", ""),
                    ", ".join(bug.get("assignees", [])),
                    bug.get("metadata", {}).get("environment", ""),
                    "Yes" if bug.get("metadata", {}).get("is_regression") else "No",
                ]
            )
    else:
        # Table format
        table = Table(title=f"Bugs ({len(bugs)} found)")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Severity", style="magenta")
        table.add_column("Assignee", style="green")
        table.add_column("Regression", style="red")

        for bug in bugs:
            severity = bug.get("metadata", {}).get("severity", "medium")
            severity_color = {
                "critical": "[red]",
                "high": "[yellow]",
                "medium": "[blue]",
                "low": "[green]",
            }.get(severity.lower(), "[white]")

            table.add_row(
                bug.get("id", ""),
                bug.get("title", ""),
                bug.get("status", ""),
                f"{severity_color}{severity}[/]",
                ", ".join(bug.get("assignees", [])),
                "✓" if bug.get("metadata", {}).get("is_regression") else "",
            )

        console.print(table)


@app.command()
def show(
    bug_id: str = typer.Argument(help="Bug ID to show"),
    format: str = typer.Option(
        "panel",
        "--format",
        "-f",
        help="Output format (panel, json, markdown)",
    ),
) -> None:
    """Show detailed information about a bug."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    bug = task_manager.load_task(bug_id)

    if not bug:
        console.print(f"[red]Bug {bug_id} not found[/red]")
        raise typer.Exit(1)

    if format == "json":
        import json

        console.print(json.dumps(bug, indent=2))
    elif format == "markdown":
        # Markdown format
        md = f"# Bug {bug.get('id', '')}: {bug.get('title', '')}\n\n"
        md += f"**Status:** {bug.get('status', '')}\n"
        md += f"**Severity:** {bug.get('metadata', {}).get('severity', '')}\n"
        md += f"**Assignee:** {', '.join(bug.get('assignees', []))}\n\n"

        if bug.get("description"):
            md += f"## Description\n\n{bug.get('description')}\n\n"

        metadata = bug.get("metadata", {})
        if metadata.get("environment"):
            md += f"## Environment\n\n{metadata.get('environment')}\n\n"

        if metadata.get("steps_to_reproduce"):
            md += f"## Steps to Reproduce\n\n{metadata.get('steps_to_reproduce')}\n\n"

        if metadata.get("expected_behavior"):
            md += f"## Expected Behavior\n\n{metadata.get('expected_behavior')}\n\n"

        if metadata.get("actual_behavior"):
            md += f"## Actual Behavior\n\n{metadata.get('actual_behavior')}\n\n"

        console.print(md)
    else:
        # Panel format
        metadata = bug.get("metadata", {})
        content = f"[bold]Title:[/bold] {bug.get('title', '')}\n"
        content += f"[bold]Status:[/bold] {bug.get('status', '')}\n"
        content += f"[bold]Severity:[/bold] {metadata.get('severity', '')}\n"
        content += f"[bold]Assignee:[/bold] {', '.join(bug.get('assignees', []))}\n"

        if metadata.get("environment"):
            content += f"[bold]Environment:[/bold] {metadata.get('environment')}\n"

        if metadata.get("is_regression"):
            content += "[bold red]REGRESSION BUG[/bold red]\n"

        if bug.get("description"):
            content += f"\n[bold]Description:[/bold]\n{bug.get('description')}\n"

        if metadata.get("steps_to_reproduce"):
            content += f"\n[bold]Steps to Reproduce:[/bold]\n{metadata.get('steps_to_reproduce')}\n"

        if metadata.get("expected_behavior"):
            content += f"\n[bold]Expected Behavior:[/bold]\n{metadata.get('expected_behavior')}\n"

        if metadata.get("actual_behavior"):
            content += (
                f"\n[bold]Actual Behavior:[/bold]\n{metadata.get('actual_behavior')}\n"
            )

        if metadata.get("affected_versions"):
            content += f"\n[bold]Affected Versions:[/bold] {', '.join(metadata.get('affected_versions', []))}\n"

        if metadata.get("fixed_in_version"):
            content += (
                f"[bold]Fixed in Version:[/bold] {metadata.get('fixed_in_version')}\n"
            )

        console.print(
            Panel(
                content,
                title=f"Bug {bug.get('id', '')}",
                border_style="red" if metadata.get("is_regression") else "cyan",
            )
        )


@app.command()
def update(
    bug_id: str = typer.Argument(help="Bug ID to update"),
    title: Optional[str] = typer.Option(None, "--title", help="New title"),
    description: Optional[str] = typer.Option(
        None, "--description", help="New description"
    ),
    status: Optional[str] = typer.Option(None, "--status", help="New status"),
    severity: Optional[str] = typer.Option(None, "--severity", help="New severity"),
    assignee: Optional[str] = typer.Option(None, "--assignee", help="New assignee"),
    add_label: Optional[List[str]] = typer.Option(
        None, "--add-label", help="Add label"
    ),
    remove_label: Optional[List[str]] = typer.Option(
        None, "--remove-label", help="Remove label"
    ),
    environment: Optional[str] = typer.Option(
        None, "--environment", help="Update environment"
    ),
    fixed_version: Optional[str] = typer.Option(
        None, "--fixed-version", help="Version where bug is fixed"
    ),
    verified: Optional[bool] = typer.Option(
        None, "--verified", help="Mark as verified fixed"
    ),
) -> None:
    """Update bug information."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    bug = task_manager.load_task(bug_id)

    if not bug:
        console.print(f"[red]Bug {bug_id} not found[/red]")
        raise typer.Exit(1)

    # Prepare updates
    updates = {}

    if title:
        updates["title"] = title

    if description:
        updates["description"] = description

    if status:
        updates["status"] = status

    if severity:
        if "metadata" not in updates:
            updates["metadata"] = bug.get("metadata", {})
        updates["metadata"]["severity"] = severity

    if assignee:
        updates["assignees"] = [assignee]

    if add_label:
        current_tags = bug.get("tags", [])
        updates["tags"] = list(set(current_tags + add_label))

    if remove_label:
        current_tags = bug.get("tags", [])
        updates["tags"] = [t for t in current_tags if t not in remove_label]

    if environment:
        if "metadata" not in updates:
            updates["metadata"] = bug.get("metadata", {})
        updates["metadata"]["environment"] = environment

    if fixed_version:
        if "metadata" not in updates:
            updates["metadata"] = bug.get("metadata", {})
        updates["metadata"]["fixed_in_version"] = fixed_version

    if verified is not None:
        if "metadata" not in updates:
            updates["metadata"] = bug.get("metadata", {})
        updates["metadata"]["verified_fixed"] = verified

    if updates:
        success = task_manager.update_task(bug_id, updates)
        if success:
            console.print(f"[green]Bug {bug_id} updated successfully[/green]")
        else:
            console.print(f"[red]Failed to update bug {bug_id}[/red]")
            raise typer.Exit(1)
    else:
        console.print("[yellow]No updates specified[/yellow]")


@app.command()
def close(
    bug_id: str = typer.Argument(help="Bug ID to close"),
    resolution: str = typer.Option(
        "fixed",
        "--resolution",
        "-r",
        help="Resolution type (fixed, wontfix, duplicate, cannot_reproduce)",
    ),
    fixed_version: Optional[str] = typer.Option(
        None,
        "--fixed-version",
        help="Version where bug is fixed",
    ),
    notes: Optional[str] = typer.Option(
        None,
        "--notes",
        help="Resolution notes",
    ),
) -> None:
    """Close a bug with resolution."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    bug = task_manager.load_task(bug_id)

    if not bug:
        console.print(f"[red]Bug {bug_id} not found[/red]")
        raise typer.Exit(1)

    # Prepare updates
    updates = {
        "status": "closed",
        "metadata": bug.metadata.copy(),
    }

    updates["metadata"]["resolution"] = resolution

    if fixed_version:
        updates["metadata"]["fixed_in_version"] = fixed_version

    if notes:
        updates["metadata"]["resolution_notes"] = notes

    success = task_manager.update_task(bug_id, **updates)
    if success:
        console.print(
            Panel(
                f"[green]Bug {bug_id} closed[/green]\n"
                f"Resolution: {resolution}\n"
                f"Fixed in: {fixed_version or 'N/A'}",
                title="Bug Closed",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to close bug {bug_id}[/red]")
        raise typer.Exit(1)


@app.command()
def stats(
    _days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
) -> None:
    """Show bug statistics and analytics."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    bugs = task_manager.list_tasks(ticket_type="bug")

    # Calculate statistics
    total_bugs = len(bugs)
    open_bugs = len([b for b in bugs if b.get("status") == "open"])
    closed_bugs = len([b for b in bugs if b.get("status") == "closed"])
    in_progress = len([b for b in bugs if b.get("status") == "in_progress"])

    # Severity breakdown
    severity_counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    regression_count = 0
    verified_count = 0

    for bug in bugs:
        metadata = bug.get("metadata", {})
        severity = metadata.get("severity", "medium").lower()
        if severity in severity_counts:
            severity_counts[severity] += 1

        if metadata.get("is_regression"):
            regression_count += 1

        if metadata.get("verified_fixed"):
            verified_count += 1

    # Create stats table
    table = Table(title="Bug Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Bugs", str(total_bugs))
    table.add_row("Open", str(open_bugs))
    table.add_row("In Progress", str(in_progress))
    table.add_row("Closed", str(closed_bugs))
    table.add_row("", "")  # Separator
    table.add_row("Critical", str(severity_counts["critical"]))
    table.add_row("High", str(severity_counts["high"]))
    table.add_row("Medium", str(severity_counts["medium"]))
    table.add_row("Low", str(severity_counts["low"]))
    table.add_row("", "")  # Separator
    table.add_row("Regressions", str(regression_count))
    table.add_row("Verified Fixed", str(verified_count))

    console.print(table)

    # Show severity distribution
    if total_bugs > 0:
        console.print("\n[bold]Severity Distribution:[/bold]")
        for severity, count in severity_counts.items():
            percentage = (count / total_bugs) * 100
            bar_length = int(percentage / 2)
            bar = "█" * bar_length
            console.print(
                f"{severity.capitalize():8} [{count:3}] {bar} {percentage:.1f}%"
            )


if __name__ == "__main__":
    app()
