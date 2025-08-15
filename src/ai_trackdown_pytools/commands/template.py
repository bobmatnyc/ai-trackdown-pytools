"""Manage and apply templates."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Manage and apply templates")
console = Console()


@app.command()
def list(
    template_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter templates by type (task, project, issue, epic, pr)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed template information",
    ),
) -> None:
    """List available templates."""
    template_manager = TemplateManager()
    templates = template_manager.list_templates(template_type)

    if not templates:
        filter_msg = f" of type '{template_type}'" if template_type else ""
        console.print(f"[yellow]No templates found{filter_msg}[/yellow]")
        return

    table = Table(
        title=f"Available Templates{' (' + template_type + ')' if template_type else ''}"
    )
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Description", style="white")

    if verbose:
        table.add_column("Path", style="dim")
        table.add_column("Modified", style="dim")

    for template in templates:
        row = [
            template["name"],
            template["type"],
            (
                template["description"][:50] + "..."
                if len(template["description"]) > 50
                else template["description"]
            ),
        ]

        if verbose:
            row.extend(
                [str(template["path"]), template["modified"].strftime("%Y-%m-%d %H:%M")]
            )

        table.add_row(*row)

    console.print(table)


@app.command()
def show(
    name: str = typer.Argument(..., help="Template name"),
    template_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Template type (task, project, issue, epic, pr)",
    ),
) -> None:
    """Show template details and content."""
    template_manager = TemplateManager()
    template_data = template_manager.load_template(template_type or "task", name)

    if not template_data:
        console.print(f"[red]Template '{name}' not found[/red]")
        if template_type:
            console.print(f"Type: {template_type}")
        raise typer.Exit(1)

    # Display template metadata
    console.print(
        Panel.fit(
            f"""[bold]{template_data.get('name', name)}[/bold]
{template_data.get('description', 'No description')}

[dim]Type:[/dim] {template_data.get('type', 'unknown')}
[dim]Version:[/dim] {template_data.get('version', '1.0.0')}
[dim]Author:[/dim] {template_data.get('author', 'Unknown')}""",
            title="Template Information",
            border_style="blue",
        )
    )

    # Display template content
    if "content" in template_data:
        console.print(
            Panel.fit(
                template_data["content"], title="Template Content", border_style="green"
            )
        )

    # Display template variables
    if "variables" in template_data:
        var_table = Table(title="Template Variables")
        var_table.add_column("Variable", style="cyan")
        var_table.add_column("Description", style="white")
        var_table.add_column("Default", style="dim")

        for var_name, var_info in template_data["variables"].items():
            var_table.add_row(
                var_name, var_info.get("description", ""), var_info.get("default", "")
            )

        console.print(var_table)


@app.command()
def create(
    name: str = typer.Argument(..., help="Template name"),
    template_type: str = typer.Option(
        "task",
        "--type",
        "-t",
        help="Template type (task, project, issue, epic, pr)",
    ),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Template description",
    ),
    author: Optional[str] = typer.Option(
        None,
        "--author",
        "-a",
        help="Template author",
    ),
    edit: bool = typer.Option(
        True,
        "--edit/--no-edit",
        help="Open template in editor after creation",
    ),
) -> None:
    """Create a new template."""
    template_manager = TemplateManager()

    # Check if template already exists
    if template_manager.template_exists(template_type, name):
        console.print(f"[red]Template '{name}' already exists[/red]")
        overwrite = typer.confirm("Overwrite existing template?")
        if not overwrite:
            raise typer.Exit(1)

    # Create template
    template_path = template_manager.create_template(
        template_type=template_type,
        name=name,
        description=description or f"{template_type.title()} template: {name}",
        author=author,
    )

    console.print(
        Panel.fit(
            f"""[bold green]Template created successfully![/bold green]

[dim]Name:[/dim] {name}
[dim]Type:[/dim] {template_type}
[dim]Path:[/dim] {template_path}

[dim]Next steps:[/dim]
1. Edit template content
2. Define template variables
3. Test template: [cyan]aitrackdown template apply {name}[/cyan]""",
            title="Template Created",
            border_style="green",
        )
    )

    # Open in editor if requested
    if edit:
        from ai_trackdown_pytools.utils.editor import EditorUtils

        EditorUtils.open_file(template_path)


@app.command()
def apply(
    name: str = typer.Argument(..., help="Template name"),
    template_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Template type (task, project, issue, epic, pr)",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path",
    ),
    variables: Optional[str] = typer.Option(
        None,
        "--variables",
        "-v",
        help="Template variables as JSON string",
    ),
) -> None:
    """Apply a template to create new content."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    template_manager = TemplateManager()

    # Parse variables if provided
    template_vars = {}
    if variables:
        import json

        try:
            template_vars = json.loads(variables)
        except json.JSONDecodeError as err:
            console.print("[red]Invalid JSON format for variables[/red]")
            raise typer.Exit(1) from err

    # Apply template
    result = template_manager.apply_template(
        template_type or "task",
        name,
        project_path,
        variables=template_vars,
        output_path=output,
    )

    if result:
        console.print(f"[green]✅ Template '{name}' applied successfully[/green]")
        if output:
            console.print(f"Output written to: {output}")
    else:
        console.print(f"[red]❌ Failed to apply template '{name}'[/red]")
        raise typer.Exit(1)


@app.command()
def validate(
    name: str = typer.Argument(..., help="Template name"),
    template_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Template type (task, project, issue, epic, pr)",
    ),
) -> None:
    """Validate a template."""
    template_manager = TemplateManager()

    validation_result = template_manager.validate_template(
        template_type or "task", name
    )

    if validation_result["valid"]:
        console.print(f"[green]✅ Template '{name}' is valid[/green]")
    else:
        console.print(f"[red]❌ Template '{name}' has validation errors:[/red]")
        for error in validation_result["errors"]:
            console.print(f"  • {error}")
        raise typer.Exit(1)

    # Show warnings if any
    if validation_result.get("warnings"):
        console.print("[yellow]⚠️  Warnings:[/yellow]")
        for warning in validation_result["warnings"]:
            console.print(f"  • {warning}")


@app.command()
def install(
    source: str = typer.Argument(..., help="Template source (URL or path)"),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Template name (if different from source)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Force installation even if template exists",
    ),
) -> None:
    """Install templates from external source."""
    template_manager = TemplateManager()

    try:
        installed_templates = template_manager.install_templates(
            source, template_name=name, force=force
        )

        console.print(
            f"[green]✅ Installed {len(installed_templates)} template(s)[/green]"
        )
        for template in installed_templates:
            console.print(f"  • {template}")

    except Exception as e:
        console.print(f"[red]❌ Failed to install templates: {e}[/red]")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
