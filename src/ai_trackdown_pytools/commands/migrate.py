"""Migration and upgrade commands."""

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager

app = typer.Typer(help="Migration and upgrade utilities")
console = Console()


@app.command()
def version_check() -> None:
    """Check current version and available migrations."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    project = Project.load(project_path)

    console.print(
        Panel.fit(
            f"""[bold blue]Version Information[/bold blue]

[dim]Project Version:[/dim] {project.version}
[dim]Schema Version:[/dim] {project.metadata.get('schema_version', '1.0.0')}
[dim]Last Migration:[/dim] {project.metadata.get('last_migration', 'None')}

[dim]Available Migrations:[/dim]
• Schema v1.0.0 → v1.1.0: Add task dependencies
• Schema v1.1.0 → v1.2.0: Add epic tracking
• Schema v1.2.0 → v1.3.0: Add PR integration""",
            title="Migration Status",
            border_style="blue",
        )
    )


@app.command()
def backup(
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Backup file path"
    ),
    include_git: bool = typer.Option(
        False, "--include-git", help="Include git metadata"
    ),
) -> None:
    """Create a backup of the current project."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    import zipfile

    # Generate backup filename
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"aitrackdown_backup_{timestamp}.zip"

    backup_path = Path(output)

    console.print(f"[blue]Creating backup: {backup_path}[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating backup...", total=None)

        # Create backup archive
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add .aitrackdown directory
            aitrackdown_dir = project_path / ".aitrackdown"
            if aitrackdown_dir.exists():
                for file_path in aitrackdown_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(project_path)
                        zipf.write(file_path, arcname)

            # Add git metadata if requested
            if include_git:
                git_dir = project_path / ".git"
                if git_dir.exists():
                    for file_path in git_dir.rglob("*"):
                        if file_path.is_file():
                            try:
                                arcname = file_path.relative_to(project_path)
                                zipf.write(file_path, arcname)
                            except Exception:
                                pass  # Skip files that can't be read

        progress.update(task, completed=True, description="Backup completed")

    console.print(f"[green]Backup created successfully: {backup_path}[/green]")
    console.print(f"[dim]Backup size: {backup_path.stat().st_size / 1024:.1f} KB[/dim]")


@app.command()
def restore(
    backup_file: str = typer.Argument(..., help="Backup file to restore from"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force restore (overwrite existing)"
    ),
    target: Optional[str] = typer.Option(
        None, "--target", "-t", help="Target directory"
    ),
) -> None:
    """Restore project from a backup."""
    import zipfile

    backup_path = Path(backup_file)
    if not backup_path.exists():
        console.print(f"[red]Backup file not found: {backup_file}[/red]")
        raise typer.Exit(1)

    target_path = Path(target) if target else Path.cwd()
    aitrackdown_dir = target_path / ".aitrackdown"

    # Check if target already has a project
    if aitrackdown_dir.exists() and not force:
        console.print("[red]Target directory already has an AI Trackdown project[/red]")
        console.print("Use --force to overwrite")
        raise typer.Exit(1)

    console.print(f"[blue]Restoring from backup: {backup_path}[/blue]")
    console.print(f"[blue]Target directory: {target_path}[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Restoring backup...", total=None)

        # Extract backup
        with zipfile.ZipFile(backup_path, "r") as zipf:
            zipf.extractall(target_path)

        progress.update(task, completed=True, description="Restore completed")

    console.print(f"[green]Project restored successfully to: {target_path}[/green]")


@app.command()
def schema_upgrade(
    target_version: Optional[str] = typer.Option(
        None, "--to", help="Target schema version"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be upgraded"
    ),
) -> None:
    """Upgrade project schema to newer version."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    project = Project.load(project_path)
    current_version = project.metadata.get("schema_version", "1.0.0")
    target_version = target_version or "1.3.0"

    console.print(f"[blue]Schema upgrade: {current_version} → {target_version}[/blue]")

    if current_version == target_version:
        console.print("[green]Schema is already up to date[/green]")
        return

    # Define migration steps
    migrations = {
        ("1.0.0", "1.1.0"): _migrate_1_0_to_1_1,
        ("1.1.0", "1.2.0"): _migrate_1_1_to_1_2,
        ("1.2.0", "1.3.0"): _migrate_1_2_to_1_3,
    }

    # Plan migration path
    migration_path = []
    current = current_version

    while current != target_version:
        next_migration = None
        for (from_ver, to_ver), migration_func in migrations.items():
            if from_ver == current:
                next_migration = (from_ver, to_ver, migration_func)
                break

        if not next_migration:
            console.print(
                f"[red]No migration path found from {current} to {target_version}[/red]"
            )
            raise typer.Exit(1)

        migration_path.append(next_migration)
        current = next_migration[1]

    if dry_run:
        console.print(
            "[yellow]DRY RUN: Migration steps that would be executed:[/yellow]"
        )
        for from_ver, to_ver, _ in migration_path:
            console.print(f"  • {from_ver} → {to_ver}")
        return

    # Execute migrations
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        for from_ver, to_ver, migration_func in migration_path:
            task = progress.add_task(f"Migrating {from_ver} → {to_ver}...", total=None)

            try:
                migration_func(project_path)
                progress.update(
                    task, completed=True, description=f"Completed {from_ver} → {to_ver}"
                )
            except Exception as e:
                console.print(f"[red]Migration failed: {e}[/red]")
                raise typer.Exit(1) from e

    # Update project schema version
    project.metadata["schema_version"] = target_version
    project.metadata["last_migration"] = target_version
    project.save()

    console.print(f"[green]Schema upgraded successfully to {target_version}[/green]")


def _migrate_1_0_to_1_1(project_path: Path) -> None:
    """Migrate from schema 1.0.0 to 1.1.0 - Add task dependencies."""
    task_manager = TaskManager(project_path)
    tasks = task_manager.list_tasks()

    for task in tasks:
        # Add dependency tracking metadata
        if "dependencies" not in task.metadata:
            task.metadata["dependencies"] = []
        if "blocked_by" not in task.metadata:
            task.metadata["blocked_by"] = []
        if "blocks" not in task.metadata:
            task.metadata["blocks"] = []

        task_manager.save_task(task)


def _migrate_1_1_to_1_2(project_path: Path) -> None:
    """Migrate from schema 1.1.0 to 1.2.0 - Add epic tracking."""
    task_manager = TaskManager(project_path)
    tasks = task_manager.list_tasks()

    for task in tasks:
        # Add epic tracking metadata
        if "epic" not in task.metadata:
            task.metadata["epic"] = None
        if "subtasks" not in task.metadata:
            task.metadata["subtasks"] = []

        # Convert old 'epic' tag to proper epic metadata
        if "epic" in task.tags and task.metadata["epic"] is None:
            task.metadata["type"] = "epic"

        task_manager.save_task(task)


def _migrate_1_2_to_1_3(project_path: Path) -> None:
    """Migrate from schema 1.2.0 to 1.3.0 - Add PR integration."""
    task_manager = TaskManager(project_path)
    tasks = task_manager.list_tasks()

    for task in tasks:
        # Add PR integration metadata
        if "pull_request" not in task.metadata:
            task.metadata["pull_request"] = None
        if "github_id" not in task.metadata:
            task.metadata["github_id"] = None

        # Convert old 'pull-request' tag to proper PR metadata
        if "pull-request" in task.tags:
            task.metadata["type"] = "pull_request"

        task_manager.save_task(task)


@app.command()
def repair(
    fix_issues: bool = typer.Option(
        False, "--fix", "-f", help="Attempt to fix found issues"
    ),
    check_only: bool = typer.Option(
        False, "--check-only", "-c", help="Check for issues without fixing"
    ),
) -> None:
    """Repair project data integrity issues."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    tasks = task_manager.list_tasks()

    issues_found = []

    console.print("[blue]Checking project data integrity...[/blue]")

    # Check all task files for various issues
    from ai_trackdown_pytools.core.config import Config

    config = Config.load(project_path=project_path)
    tasks_dir = project_path / config.get("tasks.directory", "tasks")
    if tasks_dir.exists():
        for task_file in tasks_dir.rglob("*.md"):
            try:
                with open(task_file, encoding="utf-8") as f:
                    content = f.read()

                # Extract frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])

                        # Check for required fields based on ID
                        file_id = frontmatter.get("id", "")

                        # Common required fields
                        required_fields = ["id", "title", "created_at", "updated_at"]

                        # Type-specific required fields
                        if file_id.startswith("EP-"):
                            required_fields.extend(["goal", "status"])
                        elif file_id.startswith("ISS-"):
                            required_fields.extend(["issue_type", "severity", "status"])
                        elif file_id.startswith("TSK-"):
                            required_fields.extend(["status", "priority"])

                        # Check for missing fields
                        missing_fields = []
                        for field in required_fields:
                            if field not in frontmatter or frontmatter[field] is None:
                                missing_fields.append(field)

                        if missing_fields:
                            issues_found.append(
                                {
                                    "type": "missing_fields",
                                    "file": str(task_file.relative_to(project_path)),
                                    "fields": missing_fields,
                                    "id": file_id,
                                    "description": f"{file_id}: Missing required fields: {', '.join(missing_fields)}",
                                }
                            )

                        # Check for legacy field names
                        if "epic_id" in frontmatter:
                            issues_found.append(
                                {
                                    "type": "legacy_field",
                                    "file": str(task_file.relative_to(project_path)),
                                    "field": "epic_id",
                                    "replacement": "parent",
                                    "id": file_id,
                                    "value": frontmatter["epic_id"],
                                    "description": f"{file_id}: Uses legacy field 'epic_id' (should be 'parent')",
                                }
                            )

                        if "issue_id" in frontmatter:
                            issues_found.append(
                                {
                                    "type": "legacy_field",
                                    "file": str(task_file.relative_to(project_path)),
                                    "field": "issue_id",
                                    "replacement": "parent",
                                    "id": file_id,
                                    "value": frontmatter["issue_id"],
                                    "description": f"{file_id}: Uses legacy field 'issue_id' (should be 'parent')",
                                }
                            )

            except Exception as e:
                issues_found.append(
                    {
                        "type": "parse_error",
                        "file": str(task_file.relative_to(project_path)),
                        "error": str(e),
                        "description": f"Error parsing {task_file.name}: {str(e)}",
                    }
                )

    # Check for orphaned task references
    task_ids = {task.id for task in tasks}

    for task in tasks:
        # Check epic references
        epic_id = task.metadata.get("epic")
        if epic_id and epic_id not in task_ids:
            issues_found.append(
                {
                    "type": "orphaned_epic_reference",
                    "task_id": task.id,
                    "epic_id": epic_id,
                    "description": f"Task {task.id} references non-existent epic {epic_id}",
                }
            )

        # Check subtask references
        subtasks = task.metadata.get("subtasks", [])
        for subtask_id in subtasks:
            if subtask_id not in task_ids:
                issues_found.append(
                    {
                        "type": "orphaned_subtask_reference",
                        "task_id": task.id,
                        "subtask_id": subtask_id,
                        "description": f"Task {task.id} references non-existent subtask {subtask_id}",
                    }
                )

        # Check blocking relationships
        blocked_by = task.metadata.get("blocked_by", [])
        for blocked_id in blocked_by:
            if blocked_id not in task_ids:
                issues_found.append(
                    {
                        "type": "orphaned_block_reference",
                        "task_id": task.id,
                        "blocked_id": blocked_id,
                        "description": f"Task {task.id} references non-existent blocking task {blocked_id}",
                    }
                )

    # Report issues
    if not issues_found:
        console.print("[green]✅ No data integrity issues found[/green]")
        return

    console.print(f"[yellow]Found {len(issues_found)} data integrity issues:[/yellow]")

    for i, issue in enumerate(issues_found, 1):
        console.print(f"  {i}. {issue['description']}")

    if check_only:
        return

    if fix_issues:
        console.print("\n[blue]Fixing issues...[/blue]")

        fixed_count = 0
        for issue in issues_found:
            try:
                if issue["type"] == "missing_fields":
                    # Read file
                    file_path = project_path / issue["file"]
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])

                        # Add default values for missing fields
                        for field in issue["fields"]:
                            if field == "created_at" or field == "updated_at":
                                frontmatter[field] = datetime.now().isoformat()
                            elif field == "status":
                                frontmatter[field] = "open"
                            elif field == "priority":
                                frontmatter[field] = "medium"
                            elif field == "goal":
                                frontmatter[field] = "No goal specified"
                            elif field == "issue_type":
                                frontmatter[field] = "bug"
                            elif field == "severity":
                                frontmatter[field] = "medium"

                        # Write back
                        new_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)}---\n{parts[2]}"
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)

                        console.print(f"  ✅ Added missing fields to {issue['id']}")
                        fixed_count += 1

                elif issue["type"] == "legacy_field":
                    # Read file
                    file_path = project_path / issue["file"]
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = yaml.safe_load(parts[1])

                        # Rename legacy field
                        if issue["field"] in frontmatter:
                            frontmatter[issue["replacement"]] = frontmatter[
                                issue["field"]
                            ]
                            del frontmatter[issue["field"]]

                        # Write back
                        new_content = f"---\n{yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True)}---\n{parts[2]}"
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write(new_content)

                        console.print(
                            f"  ✅ Renamed {issue['field']} to {issue['replacement']} in {issue['id']}"
                        )
                        fixed_count += 1

                elif issue.get("task_id"):
                    # Handle orphaned references
                    task = task_manager.load_task(issue["task_id"])
                    if not task:
                        continue

                    if issue["type"] == "orphaned_epic_reference":
                        task.metadata["epic"] = None
                        console.print(
                            f"  ✅ Removed orphaned epic reference from {task.id}"
                        )

                    elif issue["type"] == "orphaned_subtask_reference":
                        subtasks = task.metadata.get("subtasks", [])
                        if issue["subtask_id"] in subtasks:
                            subtasks.remove(issue["subtask_id"])
                            task.metadata["subtasks"] = subtasks
                        console.print(
                            f"  ✅ Removed orphaned subtask reference from {task.id}"
                        )

                    elif issue["type"] == "orphaned_block_reference":
                        blocked_by = task.metadata.get("blocked_by", [])
                        if issue["blocked_id"] in blocked_by:
                            blocked_by.remove(issue["blocked_id"])
                            task.metadata["blocked_by"] = blocked_by
                        console.print(
                            f"  ✅ Removed orphaned block reference from {task.id}"
                        )

                    task_manager.save_task(task)
                    fixed_count += 1

            except Exception as e:
                console.print(
                    f"  ❌ Failed to fix {issue.get('id', issue.get('file', 'unknown'))}: {e}"
                )

        console.print(
            f"[green]Fixed {fixed_count} of {len(issues_found)} data integrity issues[/green]"
        )
    else:
        console.print("\n[dim]Use --fix to attempt automatic repair[/dim]")


if __name__ == "__main__":
    app()
