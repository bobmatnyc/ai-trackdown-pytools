"""Validation command for AI Trackdown PyTools."""

import json
from pathlib import Path
from typing import List, Optional

import click
import yaml
from rich.console import Console
from rich.table import Table

from ai_trackdown_pytools.utils.frontmatter import (
    FrontmatterParser,
    StatusWorkflowValidator,
)
from ai_trackdown_pytools.utils.validation import (
    SchemaValidator,
    ValidationResult,
    validate_id_format,
    validate_relationships,
    validate_ticket_file,
)

console = Console()


@click.group()
def validate():
    """Validate tickets, schemas, and relationships."""
    pass


@validate.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--ticket-type",
    type=click.Choice(["task", "epic", "issue", "pr", "project"]),
    help="Explicit ticket type (auto-detected if not provided)",
)
@click.option(
    "--output-format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed validation information"
)
def file(
    file_path: Path, ticket_type: Optional[str], output_format: str, verbose: bool
):
    """Validate a ticket file."""
    try:
        result = validate_ticket_file(file_path, ticket_type)

        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        elif output_format == "yaml":
            click.echo(yaml.dump(result.to_dict(), default_flow_style=False))
        else:
            _display_validation_result(result, file_path, verbose)

        # Exit with non-zero code if validation failed
        if not result.valid:
            raise click.ClickException("Validation failed")

    except Exception as e:
        console.print(f"[red]Error validating file: {e}[/red]")
        raise click.ClickException(str(e)) from e


@validate.command()
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option("--pattern", default="**/*.md", help="File pattern to match")
@click.option(
    "--ticket-type",
    type=click.Choice(["task", "epic", "issue", "pr", "project"]),
    help="Filter by ticket type",
)
@click.option(
    "--output-format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
@click.option("--summary-only", is_flag=True, help="Show only summary statistics")
def directory(
    directory: Path,
    pattern: str,
    ticket_type: Optional[str],
    output_format: str,
    summary_only: bool,
):
    """Validate all ticket files in a directory."""
    files = list(directory.glob(pattern))
    if not files:
        console.print(
            f"[yellow]No files found matching pattern '{pattern}' in {directory}[/yellow]"
        )
        return

    results = []
    for file_path in files:
        try:
            result = validate_ticket_file(file_path, ticket_type)
            results.append((file_path, result))
        except Exception as e:
            error_result = ValidationResult()
            error_result.add_error(f"Error processing file: {e}")
            results.append((file_path, error_result))

    if output_format == "json":
        output_data = {
            "files": [
                {"file": str(file_path), "validation": result.to_dict()}
                for file_path, result in results
            ]
        }
        click.echo(json.dumps(output_data, indent=2))
    elif output_format == "yaml":
        output_data = {
            "files": [
                {"file": str(file_path), "validation": result.to_dict()}
                for file_path, result in results
            ]
        }
        click.echo(yaml.dump(output_data, default_flow_style=False))
    else:
        _display_directory_results(results, summary_only)


@validate.command()
@click.argument("data", type=str)
@click.argument(
    "ticket_type", type=click.Choice(["task", "epic", "issue", "pr", "project"])
)
@click.option(
    "--input-format",
    type=click.Choice(["json", "yaml"]),
    default="json",
    help="Input data format",
)
@click.option(
    "--output-format",
    type=click.Choice(["text", "json", "yaml"]),
    default="text",
    help="Output format",
)
def data(data: str, ticket_type: str, input_format: str, output_format: str):
    """Validate ticket data from command line."""
    try:
        # Parse input data
        if input_format == "yaml":
            ticket_data = yaml.safe_load(data)
        else:
            ticket_data = json.loads(data)

        # Validate
        validator = SchemaValidator()
        result = validator.validate_ticket(ticket_data, ticket_type)

        if output_format == "json":
            click.echo(json.dumps(result.to_dict(), indent=2))
        elif output_format == "yaml":
            click.echo(yaml.dump(result.to_dict(), default_flow_style=False))
        else:
            _display_validation_result(result, f"{ticket_type} data", True)

        if not result.valid:
            raise click.ClickException("Validation failed")

    except (json.JSONDecodeError, yaml.YAMLError) as e:
        console.print(f"[red]Error parsing input data: {e}[/red]")
        raise click.ClickException("Invalid input data format") from e
    except Exception as e:
        console.print(f"[red]Error validating data: {e}[/red]")
        raise click.ClickException(str(e)) from e


@validate.command()
@click.argument("ticket_id", type=str)
@click.argument(
    "ticket_type", type=click.Choice(["task", "epic", "issue", "pr", "project"])
)
def id_format(ticket_id: str, ticket_type: str):
    """Validate ticket ID format."""
    result = validate_id_format(ticket_id, ticket_type)

    if result.valid:
        console.print(f"[green]✓[/green] ID '{ticket_id}' is valid for {ticket_type}")
    else:
        console.print(f"[red]✗[/red] ID '{ticket_id}' is invalid for {ticket_type}")
        for error in result.errors:
            console.print(f"  [red]Error:[/red] {error}")

        if not result.valid:
            raise click.ClickException("ID validation failed")


@validate.command()
@click.argument("from_status", type=str)
@click.argument("to_status", type=str)
@click.argument(
    "ticket_type", type=click.Choice(["task", "epic", "issue", "pr", "project"])
)
def transition(from_status: str, to_status: str, ticket_type: str):
    """Validate status transition."""
    workflow_validator = StatusWorkflowValidator()
    result = workflow_validator.validate_status_transition(
        ticket_type, from_status, to_status
    )

    if result.valid:
        console.print(
            f"[green]✓[/green] Transition '{from_status}' → '{to_status}' is valid for {ticket_type}"
        )
    else:
        console.print(
            f"[red]✗[/red] Transition '{from_status}' → '{to_status}' is invalid for {ticket_type}"
        )
        for error in result.errors:
            console.print(f"  [red]Error:[/red] {error}")

        # Show valid transitions
        valid_transitions = workflow_validator.get_valid_transitions(
            ticket_type, from_status
        )
        if valid_transitions:
            console.print(f"\n[blue]Valid transitions from '{from_status}':[/blue]")
            for transition in valid_transitions:
                console.print(f"  • {from_status} → {transition}")
        else:
            console.print(
                f"\n[yellow]'{from_status}' is a terminal status (no valid transitions)[/yellow]"
            )

        if not result.valid:
            raise click.ClickException("Transition validation failed")


@validate.command()
@click.argument(
    "directory", type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option("--pattern", default="**/*.md", help="File pattern to match")
def relationships(directory: Path, pattern: str):
    """Validate relationships between tickets in a directory."""
    files = list(directory.glob(pattern))
    if not files:
        console.print(
            f"[yellow]No files found matching pattern '{pattern}' in {directory}[/yellow]"
        )
        return

    # Parse all tickets
    tickets = []
    parser = FrontmatterParser(validate_schema=False)

    for file_path in files:
        try:
            frontmatter, _, parse_result = parser.parse_file(file_path)
            if parse_result.valid and frontmatter:
                tickets.append(frontmatter)
        except Exception as e:
            console.print(f"[red]Error parsing {file_path}: {e}[/red]")

    if not tickets:
        console.print(
            "[yellow]No valid tickets found to validate relationships[/yellow]"
        )
        return

    # Validate relationships
    result = validate_relationships(tickets)

    console.print("\n[blue]Relationship Validation Results[/blue]")
    console.print(f"Tickets analyzed: {len(tickets)}")

    if result.valid:
        console.print("[green]✓ All relationships are valid[/green]")
    else:
        console.print("[red]✗ Relationship validation failed[/red]")

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  • {error}")

    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")

    if not result.valid:
        raise click.ClickException("Relationship validation failed")


@validate.command()
def schemas():
    """List available validation schemas."""
    validator = SchemaValidator()
    schemas = validator.list_schemas()

    if not schemas:
        console.print("[yellow]No schemas found[/yellow]")
        return

    table = Table(title="Available Validation Schemas")
    table.add_column("Schema Name", style="cyan")
    table.add_column("Description", style="white")

    schema_descriptions = {
        "task": "Individual work items and tasks",
        "epic": "Large features and initiatives",
        "issue": "Bug reports and feature requests",
        "pr": "Pull requests and code reviews",
        "project": "Project-level tracking and management",
    }

    for schema_name in sorted(schemas):
        description = schema_descriptions.get(schema_name, "No description available")
        table.add_row(schema_name, description)

    console.print(table)


def _display_validation_result(
    result: ValidationResult, source: str, verbose: bool = False
):
    """Display validation result in rich format."""
    if result.valid:
        console.print(f"[green]✓ Validation passed[/green] for {source}")
    else:
        console.print(f"[red]✗ Validation failed[/red] for {source}")

    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  • {error}")

    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")

    if verbose and not result.errors and not result.warnings:
        console.print("[dim]No validation issues found[/dim]")


def _display_directory_results(results: List[tuple], summary_only: bool = False):
    """Display validation results for multiple files."""
    total_files = len(results)
    valid_files = sum(1 for _, result in results if result.valid)
    invalid_files = total_files - valid_files

    # Summary statistics
    console.print("\n[blue]Validation Summary[/blue]")
    console.print(f"Total files: {total_files}")
    console.print(f"[green]Valid: {valid_files}[/green]")
    console.print(f"[red]Invalid: {invalid_files}[/red]")

    if summary_only:
        return

    # Detailed results
    if invalid_files > 0:
        console.print("\n[red]Files with validation errors:[/red]")
        for file_path, result in results:
            if not result.valid:
                console.print(f"\n[red]✗ {file_path}[/red]")
                for error in result.errors:
                    console.print(f"    • {error}")
                if result.warnings:
                    for warning in result.warnings:
                        console.print(f"    [yellow]⚠ {warning}[/yellow]")

    # Show warnings even for valid files
    files_with_warnings = [(fp, r) for fp, r in results if r.valid and r.warnings]
    if files_with_warnings:
        console.print("\n[yellow]Files with warnings:[/yellow]")
        for file_path, result in files_with_warnings:
            console.print(f"\n[yellow]⚠ {file_path}[/yellow]")
            for warning in result.warnings:
                console.print(f"    • {warning}")


if __name__ == "__main__":
    validate()
