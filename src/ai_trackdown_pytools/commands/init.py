"""Initialize AI Trackdown project structure."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.utils.git import GitUtils
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Initialize AI Trackdown project structure")
console = Console()


@app.command()
def project(
    path: Optional[Path] = typer.Argument(
        None,
        help="Project directory path (defaults to current directory)",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Project template to use",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force initialization even if project already exists",
    ),
    git_init: bool = typer.Option(
        True,
        "--git/--no-git",
        help="Initialize git repository",
    ),
) -> None:
    """Initialize a new AI Trackdown project."""
    project_path = path or Path.cwd()

    if not force and Project.exists(project_path):
        console.print(f"[red]Project already exists at {project_path}[/red]")
        console.print("Use --force to reinitialize")
        raise typer.Exit(1)

    console.print(f"[blue]Initializing AI Trackdown project at {project_path}[/blue]")

    # Create project structure
    Project.create(project_path)

    # Initialize git repository if requested
    if git_init and not GitUtils.is_git_repo_static(project_path):
        GitUtils.init_repo(project_path)
        console.print("[green]✅ Git repository initialized[/green]")

    # Apply template if specified
    if template:
        template_manager = TemplateManager()
        if template_manager.apply_template("project", template, project_path):
            console.print(f"[green]✅ Applied template: {template}[/green]")
        else:
            console.print(f"[yellow]⚠️  Template not found: {template}[/yellow]")

    console.print(
        Panel.fit(
            """[bold green]Project initialized successfully![/bold green]

[dim]Created structure:[/dim]
• Configuration: .ai-trackdown/config.yaml
• Tickets directory: tickets/
• Templates: .ai-trackdown/templates/
• Documentation: docs/

[dim]Next steps:[/dim]
1. Review configuration: [cyan]aitrackdown status[/cyan]
2. Create your first task: [cyan]aitrackdown create task[/cyan]
3. Check available templates: [cyan]aitrackdown template list[/cyan]""",
            title="Initialization Complete",
            border_style="green",
        )
    )


@app.command()
def config(
    global_config: bool = typer.Option(
        False,
        "--global",
        "-g",
        help="Initialize global configuration",
    ),
    editor: Optional[str] = typer.Option(
        None,
        "--editor",
        "-e",
        help="Default editor for task editing",
    ),
) -> None:
    """Initialize or update configuration."""
    from ai_trackdown_pytools.core.config import Config

    if global_config:
        config_path = Config.get_global_config_path()
        console.print(
            f"[blue]Initializing global configuration at {config_path}[/blue]"
        )
    else:
        config_path = Path.cwd() / ".ai-trackdown" / "config.yaml"
        console.print(
            f"[blue]Initializing project configuration at {config_path}[/blue]"
        )

    config = Config.create_default(config_path)

    if editor:
        config.set("editor.default", editor)
        config.save()

    console.print(f"[green]✅ Configuration initialized at {config_path}[/green]")


@app.command()
def templates(
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Source URL or path for templates",
    ),
) -> None:
    """Initialize template system."""
    template_manager = TemplateManager()

    if source:
        template_manager.install_templates(source)
        console.print(f"[green]✅ Templates installed from {source}[/green]")
    else:
        template_manager.init_templates()
        console.print("[green]✅ Default templates initialized[/green]")


if __name__ == "__main__":
    app()
