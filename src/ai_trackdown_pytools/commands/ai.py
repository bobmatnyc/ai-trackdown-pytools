"""AI-specific commands for token tracking and context management."""

import json
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager

app = typer.Typer(help="AI-specific commands for tracking and context management")
console = Console()


@app.command("track-tokens")
def track_tokens(
    session_id: Optional[str] = typer.Argument(
        None, help="Session ID to track tokens for"
    ),
    input_tokens: Optional[int] = typer.Option(
        None, "--input", "-i", help="Number of input tokens"
    ),
    output_tokens: Optional[int] = typer.Option(
        None, "--output", "-o", help="Number of output tokens"
    ),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="AI model used"),
    cost: Optional[float] = typer.Option(None, "--cost", "-c", help="Cost in USD"),
    task_id: Optional[str] = typer.Option(
        None, "--task", "-t", help="Associate with task ID"
    ),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Session description"
    ),
) -> None:
    """Track AI token usage and costs."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Create .aitrackdown/ai directory if it doesn't exist
    ai_dir = project_path / ".aitrackdown" / "ai"
    ai_dir.mkdir(parents=True, exist_ok=True)

    # Load existing token data
    token_file = ai_dir / "tokens.json"
    if token_file.exists():
        with open(token_file) as f:
            token_data = json.load(f)
    else:
        token_data = {
            "sessions": [],
            "total_stats": {"input_tokens": 0, "output_tokens": 0, "total_cost": 0.0},
        }

    if not session_id:
        from datetime import datetime

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Interactive input if not provided
    if input_tokens is None:
        from rich.prompt import IntPrompt

        input_tokens = IntPrompt.ask("Input tokens", default=0)

    if output_tokens is None:
        from rich.prompt import IntPrompt

        output_tokens = IntPrompt.ask("Output tokens", default=0)

    if not model:
        from rich.prompt import Prompt

        model = Prompt.ask("AI model", default="unknown")

    if cost is None:
        from rich.prompt import FloatPrompt

        cost = FloatPrompt.ask("Cost (USD)", default=0.0)

    # Create session record
    session = {
        "session_id": session_id,
        "timestamp": token_data.get("timestamp", ""),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "model": model,
        "cost": cost,
        "task_id": task_id,
        "description": description or "",
    }

    # Add to data
    token_data["sessions"].append(session)

    # Update totals
    token_data["total_stats"]["input_tokens"] += input_tokens
    token_data["total_stats"]["output_tokens"] += output_tokens
    token_data["total_stats"]["total_cost"] += cost

    # Save data
    with open(token_file, "w") as f:
        json.dump(token_data, f, indent=2)

    console.print(
        Panel.fit(
            f"""[bold green]Token usage recorded![/bold green]

[dim]Session ID:[/dim] {session_id}
[dim]Model:[/dim] {model}
[dim]Input tokens:[/dim] {input_tokens:,}
[dim]Output tokens:[/dim] {output_tokens:,}
[dim]Total tokens:[/dim] {input_tokens + output_tokens:,}
[dim]Cost:[/dim] ${cost:.4f}
[dim]Task:[/dim] {task_id or 'None'}""",
            title="Token Usage Tracked",
            border_style="green",
        )
    )


@app.command("token-stats")
def token_stats(
    task_id: Optional[str] = typer.Option(
        None, "--task", "-t", help="Show stats for specific task"
    ),
    model_filter: Optional[str] = typer.Option(
        None, "--model", "-m", help="Filter by model"
    ),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed session breakdown"
    ),
    export: Optional[str] = typer.Option(
        None, "--export", "-e", help="Export to CSV file"
    ),
) -> None:
    """Show AI token usage statistics."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    token_file = project_path / ".aitrackdown" / "ai" / "tokens.json"
    if not token_file.exists():
        console.print("[yellow]No token usage data found[/yellow]")
        return

    with open(token_file) as f:
        token_data = json.load(f)

    sessions = token_data.get("sessions", [])

    # Apply filters
    if task_id:
        sessions = [s for s in sessions if s.get("task_id") == task_id]

    if model_filter:
        sessions = [s for s in sessions if s.get("model") == model_filter]

    if not sessions:
        console.print("[yellow]No sessions found matching criteria[/yellow]")
        return

    # Calculate stats
    total_input = sum(s.get("input_tokens", 0) for s in sessions)
    total_output = sum(s.get("output_tokens", 0) for s in sessions)
    total_cost = sum(s.get("cost", 0) for s in sessions)
    session_count = len(sessions)

    # Show summary
    console.print(
        Panel.fit(
            f"""[bold blue]Token Usage Statistics[/bold blue]

[dim]Sessions:[/dim] {session_count}
[dim]Total Input Tokens:[/dim] {total_input:,}
[dim]Total Output Tokens:[/dim] {total_output:,}
[dim]Total Tokens:[/dim] {total_input + total_output:,}
[dim]Total Cost:[/dim] ${total_cost:.4f}
[dim]Average Cost per Session:[/dim] ${total_cost/session_count:.4f}""",
            title="Token Statistics",
            border_style="blue",
        )
    )

    # Show detailed breakdown
    if detailed:
        console.print("\n[bold]Session Details:[/bold]")

        table = Table()
        table.add_column("Session ID", style="cyan")
        table.add_column("Model", style="blue")
        table.add_column("Input", style="green")
        table.add_column("Output", style="yellow")
        table.add_column("Cost", style="magenta")
        table.add_column("Task", style="dim")

        for session in sessions[-20:]:  # Show last 20 sessions
            table.add_row(
                session.get("session_id", "")[:12],
                session.get("model", ""),
                f"{session.get('input_tokens', 0):,}",
                f"{session.get('output_tokens', 0):,}",
                f"${session.get('cost', 0):.4f}",
                session.get("task_id", ""),
            )

        console.print(table)

    # Export to CSV
    if export:
        import csv

        export_path = Path(export)

        with open(export_path, "w", newline="") as csvfile:
            fieldnames = [
                "session_id",
                "timestamp",
                "model",
                "input_tokens",
                "output_tokens",
                "total_tokens",
                "cost",
                "task_id",
                "description",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for session in sessions:
                writer.writerow(session)

        console.print(f"[green]Token data exported to {export_path}[/green]")


@app.command("generate-llms-txt")
def generate_llms_txt(
    output: Optional[str] = typer.Option(
        "llms.txt", "--output", "-o", help="Output filename"
    ),
    include_code: bool = typer.Option(
        True, "--include-code", help="Include code files"
    ),
    include_docs: bool = typer.Option(
        True, "--include-docs", help="Include documentation"
    ),
    include_tests: bool = typer.Option(
        False, "--include-tests", help="Include test files"
    ),
    max_file_size: int = typer.Option(
        50000, "--max-size", help="Maximum file size in bytes"
    ),
    exclude_patterns: Optional[List[str]] = typer.Option(
        None, "--exclude", help="Patterns to exclude"
    ),
) -> None:
    """Generate llms.txt file for AI context sharing."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Default exclude patterns
    default_excludes = [
        "node_modules",
        ".git",
        "__pycache__",
        ".pytest_cache",
        "venv",
        ".venv",
        "env",
        ".env",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        "*.log",
        "*.tmp",
        "*.cache",
    ]

    if exclude_patterns:
        default_excludes.extend(exclude_patterns)

    # File extensions to include
    code_extensions = {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".rs",
        ".go",
        ".rb",
        ".php",
    }
    doc_extensions = {
        ".md",
        ".rst",
        ".txt",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".ini",
        ".cfg",
    }
    include_extensions = set()
    if include_code:
        include_extensions.update(code_extensions)
    if include_docs:
        include_extensions.update(doc_extensions)
    if include_tests:
        include_extensions.update({".py", ".js", ".ts"})

    # Collect files
    files_to_include = []

    def should_exclude(path: Path) -> bool:
        path_str = str(path)
        for pattern in default_excludes:
            if pattern in path_str or path.name.startswith("."):
                return True
        return False

    def is_test_file(path: Path) -> bool:
        return "test" in path.name.lower() or "spec" in path.name.lower()

    for file_path in project_path.rglob("*"):
        if file_path.is_file():
            # Check exclusions
            if should_exclude(file_path):
                continue

            # Check file size
            if file_path.stat().st_size > max_file_size:
                continue

            # Check extension
            if file_path.suffix.lower() not in include_extensions:
                continue

            # Check if test file
            if is_test_file(file_path) and not include_tests:
                continue

            files_to_include.append(file_path)

    # Generate llms.txt content
    output_path = project_path / output

    with open(output_path, "w", encoding="utf-8") as f:
        # Header
        f.write(f"# AI Context for {project_path.name}\n\n")
        f.write("Generated by AI Trackdown PyTools\n")
        f.write(f"Project: {project_path.name}\n")
        f.write(f"Files included: {len(files_to_include)}\n\n")

        # Project structure
        f.write("## Project Structure\n\n")
        f.write("```\n")

        # Simple directory tree
        def write_tree(
            path: Path, prefix: str = "", max_depth: int = 3, current_depth: int = 0
        ):
            if current_depth >= max_depth:
                return

            items = sorted([p for p in path.iterdir() if not should_exclude(p)])
            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                f.write(f"{prefix}{current_prefix}{item.name}\n")

                if item.is_dir() and current_depth < max_depth - 1:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    write_tree(item, next_prefix, max_depth, current_depth + 1)

        write_tree(project_path)
        f.write("```\n\n")

        # File contents
        f.write("## File Contents\n\n")

        for file_path in sorted(files_to_include):
            rel_path = file_path.relative_to(project_path)
            f.write(f"### {rel_path}\n\n")

            try:
                content = file_path.read_text(encoding="utf-8")
                f.write(f"```{file_path.suffix[1:] if file_path.suffix else 'text'}\n")
                f.write(content)
                if not content.endswith("\n"):
                    f.write("\n")
                f.write("```\n\n")
            except UnicodeDecodeError:
                f.write("*Binary file - content not included*\n\n")
            except Exception as e:
                f.write(f"*Error reading file: {e}*\n\n")

    console.print(
        Panel.fit(
            f"""[bold green]llms.txt generated successfully![/bold green]

[dim]Output file:[/dim] {output_path}
[dim]Files included:[/dim] {len(files_to_include)}
[dim]Include code:[/dim] {include_code}
[dim]Include docs:[/dim] {include_docs}
[dim]Include tests:[/dim] {include_tests}
[dim]Max file size:[/dim] {max_file_size:,} bytes""",
            title="Context File Generated",
            border_style="green",
        )
    )


@app.command("context")
def context(
    task_id: Optional[str] = typer.Argument(
        None, help="Task ID to generate context for"
    ),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    include_related: bool = typer.Option(
        True, "--include-related", help="Include related tasks"
    ),
    _include_files: bool = typer.Option(
        True, "--include-files", help="Include relevant files"
    ),
    format: str = typer.Option(
        "markdown", "--format", "-f", help="Output format (markdown, json, txt)"
    ),
) -> None:
    """Generate AI context for a specific task or project."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)

    if task_id:
        task = task_manager.load_task(task_id)
        if not task:
            console.print(f"[red]Task '{task_id}' not found[/red]")
            raise typer.Exit(1)

        context_data = {
            "task": {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "tags": task.tags,
                "metadata": task.metadata,
            }
        }

        # Include related tasks
        if include_related:
            related_tasks = []

            # Epic tasks
            if task.metadata.get("epic"):
                epic = task_manager.load_task(task.metadata.get("epic"))
                if epic:
                    related_tasks.append({"type": "epic", "task": epic})

            # Subtasks
            for subtask_id in task.metadata.get("subtasks", []):
                subtask = task_manager.load_task(subtask_id)
                if subtask:
                    related_tasks.append({"type": "subtask", "task": subtask})

            # Blocked by
            for blocked_id in task.metadata.get("blocked_by", []):
                blocked_task = task_manager.load_task(blocked_id)
                if blocked_task:
                    related_tasks.append({"type": "blocks", "task": blocked_task})

            context_data["related_tasks"] = related_tasks

        output_file = output or f"context_{task_id}.{format}"
    else:
        # Project-wide context
        all_tasks = task_manager.list_tasks()
        context_data = {
            "project": {
                "name": project_path.name,
                "path": str(project_path),
                "total_tasks": len(all_tasks),
            },
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                    "tags": task.tags,
                }
                for task in all_tasks
            ],
        }

        output_file = output or f"project_context.{format}"

    # Generate output
    output_path = project_path / output_file

    if format == "json":
        with open(output_path, "w") as f:
            json.dump(context_data, f, indent=2, default=str)

    elif format == "markdown":
        with open(output_path, "w") as f:
            if task_id:
                task_data = context_data["task"]
                f.write(f"# Context for Task: {task_data['title']}\n\n")
                f.write(f"**ID:** {task_data['id']}\n")
                f.write(f"**Status:** {task_data['status']}\n")
                f.write(f"**Priority:** {task_data['priority']}\n")
                f.write(f"**Tags:** {', '.join(task_data['tags'])}\n\n")
                f.write(f"## Description\n\n{task_data['description']}\n\n")

                if "related_tasks" in context_data:
                    f.write("## Related Tasks\n\n")
                    for related in context_data["related_tasks"]:
                        rel_task = related["task"]
                        f.write(
                            f"- **{related['type'].title()}:** {rel_task.id} - {rel_task.title}\n"
                        )
            else:
                proj_data = context_data["project"]
                f.write(f"# Project Context: {proj_data['name']}\n\n")
                f.write(f"**Total Tasks:** {proj_data['total_tasks']}\n\n")
                f.write("## Tasks\n\n")
                for task in context_data["tasks"]:
                    f.write(f"- **{task['id']}:** {task['title']} ({task['status']})\n")

    else:  # txt format
        with open(output_path, "w") as f:
            if task_id:
                task_data = context_data["task"]
                f.write(f"Task Context: {task_data['title']}\n")
                f.write(f"ID: {task_data['id']}\n")
                f.write(f"Status: {task_data['status']}\n")
                f.write(f"Priority: {task_data['priority']}\n")
                f.write(f"Description: {task_data['description']}\n")
            else:
                proj_data = context_data["project"]
                f.write(f"Project: {proj_data['name']}\n")
                f.write(f"Total Tasks: {proj_data['total_tasks']}\n")

    console.print(f"[green]Context generated: {output_path}[/green]")


if __name__ == "__main__":
    app()
