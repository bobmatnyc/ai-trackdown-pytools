"""Advanced search and filtering commands."""

import re
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager

app = typer.Typer(help="Advanced search and filtering capabilities")
console = Console()


@app.command()
def tasks(
    query: str = typer.Argument(..., help="Search query"),
    field: Optional[List[str]] = typer.Option(
        None,
        "--field",
        "-f",
        help="Fields to search (title, description, tags, assignees)",
    ),
    task_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by type (task, issue, epic, pr)"
    ),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    priority: Optional[str] = typer.Option(
        None, "--priority", "-p", help="Filter by priority"
    ),
    assignee: Optional[str] = typer.Option(
        None, "--assignee", "-a", help="Filter by assignee"
    ),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
    created_after: Optional[str] = typer.Option(
        None, "--created-after", help="Filter by creation date (YYYY-MM-DD)"
    ),
    created_before: Optional[str] = typer.Option(
        None, "--created-before", help="Filter by creation date (YYYY-MM-DD)"
    ),
    regex: bool = typer.Option(
        False, "--regex", "-r", help="Use regular expression search"
    ),
    case_sensitive: bool = typer.Option(
        False, "--case-sensitive", "-c", help="Case sensitive search"
    ),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum results to show"),
    sort_by: str = typer.Option(
        "updated", "--sort", help="Sort by (created, updated, priority, title)"
    ),
    reverse: bool = typer.Option(False, "--reverse", help="Reverse sort order"),
) -> None:
    """Search tasks with advanced filtering and sorting."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Prepare search query
    if regex:
        try:
            search_pattern = re.compile(
                query, re.IGNORECASE if not case_sensitive else 0
            )
        except re.error as e:
            console.print(f"[red]Invalid regex pattern: {e}[/red]")
            raise typer.Exit(1) from e
    else:
        query_lower = query.lower() if not case_sensitive else query

    # Define search fields
    search_fields = field or ["title", "description", "tags"]

    # Filter and search tasks
    matching_tasks = []

    for task in all_tasks:
        # Apply type filter
        if task_type:
            type_tags = {
                "task": [],
                "issue": ["issue"],
                "epic": ["epic"],
                "pr": ["pull-request"],
            }
            required_tags = type_tags.get(task_type, [])
            if required_tags and not any(tag in task.tags for tag in required_tags):
                continue
            if task_type == "task" and any(
                tag in task.tags for tag in ["issue", "epic", "pull-request"]
            ):
                continue

        # Apply status filter
        if status and task.status != status:
            continue

        # Apply priority filter
        if priority and task.priority != priority:
            continue

        # Apply assignee filter
        if assignee and assignee not in task.assignees:
            continue

        # Apply tag filter
        if tag and tag not in task.tags:
            continue

        # Apply date filters
        if created_after:
            from datetime import datetime

            try:
                after_date = datetime.strptime(created_after, "%Y-%m-%d")
                if task.created_at.date() < after_date.date():
                    continue
            except ValueError as err:
                console.print(
                    f"[red]Invalid date format: {created_after}. Use YYYY-MM-DD[/red]"
                )
                raise typer.Exit(1) from err

        if created_before:
            from datetime import datetime

            try:
                before_date = datetime.strptime(created_before, "%Y-%m-%d")
                if task.created_at.date() > before_date.date():
                    continue
            except ValueError as err:
                console.print(
                    f"[red]Invalid date format: {created_before}. Use YYYY-MM-DD[/red]"
                )
                raise typer.Exit(1) from err

        # Perform search
        match_found = False

        for search_field in search_fields:
            field_content = ""

            if search_field == "title":
                field_content = task.title
            elif search_field == "description":
                field_content = task.description
            elif search_field == "tags":
                field_content = " ".join(task.tags)
            elif search_field == "assignees":
                field_content = " ".join(task.assignees)
            elif search_field == "metadata":
                field_content = str(task.metadata)

            # Perform search on field
            if regex:
                if search_pattern.search(field_content):
                    match_found = True
                    break
            else:
                search_content = (
                    field_content.lower() if not case_sensitive else field_content
                )
                if query_lower in search_content:
                    match_found = True
                    break

        if match_found:
            matching_tasks.append(task)

    # Sort results
    sort_key_map = {
        "created": lambda t: t.created_at,
        "updated": lambda t: t.updated_at,
        "title": lambda t: t.title.lower(),
        "priority": lambda t: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(
            t.priority, 0
        ),
    }

    if sort_by in sort_key_map:
        matching_tasks.sort(key=sort_key_map[sort_by], reverse=reverse)

    # Limit results
    matching_tasks = matching_tasks[:limit]

    if not matching_tasks:
        console.print(f"[yellow]No tasks found matching '{query}'[/yellow]")
        return

    # Display results
    table = Table(title=f"Search Results: '{query}' ({len(matching_tasks)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Type", style="blue")
    table.add_column("Status", style="magenta")
    table.add_column("Priority", style="yellow")
    table.add_column("Assignee", style="green")
    table.add_column("Updated", style="dim")

    for task in matching_tasks:
        # Determine type
        if "epic" in task.tags:
            task_type_display = "Epic"
        elif "issue" in task.tags:
            task_type_display = "Issue"
        elif "pull-request" in task.tags:
            task_type_display = "PR"
        else:
            task_type_display = "Task"

        assignee_display = (
            ", ".join(task.assignees[:2]) if task.assignees else "Unassigned"
        )
        if len(task.assignees) > 2:
            assignee_display += "..."

        table.add_row(
            task.id,
            task.title[:40] + "..." if len(task.title) > 40 else task.title,
            task_type_display,
            task.status,
            task.priority,
            assignee_display,
            task.updated_at.strftime("%m/%d"),
        )

    console.print(table)

    # Show search summary
    console.print(f"\n[dim]Search: '{query}' in {', '.join(search_fields)}[/dim]")
    if any([task_type, status, priority, assignee, tag, created_after, created_before]):
        filters = []
        if task_type:
            filters.append(f"type={task_type}")
        if status:
            filters.append(f"status={status}")
        if priority:
            filters.append(f"priority={priority}")
        if assignee:
            filters.append(f"assignee={assignee}")
        if tag:
            filters.append(f"tag={tag}")
        if created_after:
            filters.append(f"after={created_after}")
        if created_before:
            filters.append(f"before={created_before}")
        console.print(f"[dim]Filters: {', '.join(filters)}[/dim]")


@app.command()
def content(
    query: str = typer.Argument(..., help="Content search query"),
    file_types: Optional[List[str]] = typer.Option(
        None, "--type", "-t", help="File types to search (.md, .py, .txt)"
    ),
    regex: bool = typer.Option(
        False, "--regex", "-r", help="Use regular expression search"
    ),
    case_sensitive: bool = typer.Option(
        False, "--case-sensitive", "-c", help="Case sensitive search"
    ),
    context_lines: int = typer.Option(
        2, "--context", help="Lines of context around matches"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum files to show"),
) -> None:
    """Search content within task files."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Default file types to search
    default_types = [".md", ".txt", ".yaml", ".yml"]
    search_types = file_types or default_types

    # Prepare search pattern
    if regex:
        try:
            search_pattern = re.compile(
                query, re.IGNORECASE if not case_sensitive else 0
            )
        except re.error as e:
            console.print(f"[red]Invalid regex pattern: {e}[/red]")
            raise typer.Exit(1) from e
    else:
        query_search = query if case_sensitive else query.lower()

    # Search in task files
    from ai_trackdown_pytools.core.config import Config

    config = Config.load(project_path=project_path)
    tasks_dir = project_path / config.get("tasks.directory", "tasks")
    if not tasks_dir.exists():
        console.print("[yellow]No tasks directory found[/yellow]")
        return

    matches_found = []
    files_searched = 0

    for task_file in tasks_dir.rglob("*"):
        if task_file.is_file() and task_file.suffix in search_types:
            files_searched += 1

            try:
                with open(task_file, encoding="utf-8") as f:
                    lines = f.readlines()

                file_matches = []

                for line_num, line in enumerate(lines, 1):
                    match_found = False

                    if regex:
                        match = search_pattern.search(line)
                        if match:
                            match_found = True
                    else:
                        search_line = line if case_sensitive else line.lower()
                        if query_search in search_line:
                            match_found = True

                    if match_found:
                        # Get context lines
                        start_line = max(0, line_num - context_lines - 1)
                        end_line = min(len(lines), line_num + context_lines)

                        context = []
                        for i in range(start_line, end_line):
                            prefix = ">>>" if i == line_num - 1 else "   "
                            context.append(f"{prefix} {i+1:3d}: {lines[i].rstrip()}")

                        file_matches.append(
                            {
                                "line_num": line_num,
                                "line": line.strip(),
                                "context": context,
                            }
                        )

                if file_matches:
                    matches_found.append({"file": task_file, "matches": file_matches})

                    if len(matches_found) >= limit:
                        break

            except UnicodeDecodeError:
                # Skip binary files
                continue
            except Exception:
                # Skip files that can't be read
                continue

    if not matches_found:
        console.print(f"[yellow]No content matches found for '{query}'[/yellow]")
        console.print(
            f"[dim]Searched {files_searched} files with types: {', '.join(search_types)}[/dim]"
        )
        return

    # Display results
    console.print(
        Panel.fit(
            f"""[bold blue]Content Search Results[/bold blue]

[dim]Query:[/dim] '{query}'
[dim]Files searched:[/dim] {files_searched}
[dim]Files with matches:[/dim] {len(matches_found)}
[dim]Total matches:[/dim] {sum(len(f['matches']) for f in matches_found)}""",
            title="Search Summary",
            border_style="blue",
        )
    )

    for file_result in matches_found:
        rel_path = file_result["file"].relative_to(project_path)

        console.print(f"\n[bold cyan]📄 {rel_path}[/bold cyan]")

        for match in file_result["matches"][:5]:  # Show max 5 matches per file
            console.print(f"\n[yellow]Line {match['line_num']}:[/yellow]")
            for context_line in match["context"]:
                if context_line.startswith(">>>"):
                    console.print(f"[bold green]{context_line}[/bold green]")
                else:
                    console.print(f"[dim]{context_line}[/dim]")

        if len(file_result["matches"]) > 5:
            console.print(
                f"[dim]... and {len(file_result['matches']) - 5} more matches[/dim]"
            )


@app.command()
def filters(
    list_values: bool = typer.Option(
        False, "--list", "-l", help="List all filter values"
    ),
    field: Optional[str] = typer.Option(
        None, "--field", "-f", help="Field to list values for"
    ),
) -> None:
    """Show available filter values for search commands."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    if not all_tasks:
        console.print("[yellow]No tasks found[/yellow]")
        return

    if list_values:
        # Collect all unique values
        statuses = {task.status for task in all_tasks}
        priorities = {task.priority for task in all_tasks}
        assignees = {assignee for task in all_tasks for assignee in task.assignees}
        tags = {tag for task in all_tasks for tag in task.tags}

        if field:
            if field == "status":
                values = sorted(statuses)
            elif field == "priority":
                values = sorted(
                    priorities,
                    key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(
                        x, 0
                    ),
                    reverse=True,
                )
            elif field == "assignee":
                values = sorted(assignees)
            elif field == "tag":
                values = sorted(tags)
            else:
                console.print(f"[red]Unknown field: {field}[/red]")
                console.print("Available fields: status, priority, assignee, tag")
                raise typer.Exit(1)

            console.print(f"[bold blue]{field.title()} Values:[/bold blue]")
            for value in values:
                console.print(f"• {value}")
        else:
            # Show all filter values
            console.print(
                Panel.fit(
                    f"""[bold blue]Available Filter Values[/bold blue]

[dim]Statuses:[/dim] {', '.join(sorted(statuses))}

[dim]Priorities:[/dim] {', '.join(sorted(priorities, key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(x, 0), reverse=True))}

[dim]Assignees:[/dim] {', '.join(sorted(assignees)[:10])}{('...' if len(assignees) > 10 else '')}

[dim]Tags:[/dim] {', '.join(sorted(tags)[:15])}{('...' if len(tags) > 15 else '')}""",
                    title="Filter Values",
                    border_style="blue",
                )
            )
    else:
        # Show search command examples
        console.print(
            Panel.fit(
                """[bold blue]Search Command Examples[/bold blue]

[dim]Basic search:[/dim]
aitrackdown search tasks "bug fix"

[dim]Search with filters:[/dim]
aitrackdown search tasks "performance" --type issue --status open

[dim]Search specific fields:[/dim]
aitrackdown search tasks "database" --field title --field description

[dim]Regex search:[/dim]
aitrackdown search tasks "feat|fix" --regex

[dim]Date range search:[/dim]
aitrackdown search tasks "urgent" --created-after 2024-01-01

[dim]Content search:[/dim]
aitrackdown search content "TODO" --type .py --type .md

[dim]Search with sorting:[/dim]
aitrackdown search tasks "api" --sort priority --reverse""",
                title="Search Examples",
                border_style="green",
            )
        )


if __name__ == "__main__":
    app()
