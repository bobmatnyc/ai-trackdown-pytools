"""Sync commands for GitHub and other platforms."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.git import GitUtils
from ai_trackdown_pytools.utils.github import GitHubCLI, GitHubError
from ai_trackdown_pytools.utils.sync import (
    AdapterNotFoundError,
    SyncError,
    list_platforms,
)
from ai_trackdown_pytools.utils.sync.compat import SyncBridge

app = typer.Typer(help="Sync with external platforms (GitHub, GitLab, etc.)")
console = Console()

# Adapters are self-registered when imported via the sync module
# No need to manually register them here


@app.command(name="platform")
def sync_platform(
    platform: str = typer.Argument(
        ..., help="Platform to sync with (use 'list' to see available platforms)"
    ),
    action: str = typer.Argument(..., help="Action to perform (pull, push, status)"),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository or project identifier"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="Authentication token"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without executing"
    ),
) -> None:
    """Sync with external platforms using the adapter system.

    WHY: This is the new unified sync command that uses the adapter pattern.
    It maintains backward compatibility while supporting multiple platforms.
    """
    # Special case: list available platforms
    if platform == "list" and action == "platforms":
        platforms = list_platforms()
        console.print("[bold blue]Available Platforms:[/bold blue]")
        for p in platforms:
            console.print(f"  • {p}")
        return

    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Ensure sync directory exists
    sync_dir = project_path / ".aitrackdown"
    sync_dir.mkdir(exist_ok=True)

    # Load sync configuration
    sync_config_file = sync_dir / "sync.json"
    if sync_config_file.exists():
        with open(sync_config_file) as f:
            all_sync_config = json.load(f)
    else:
        all_sync_config = {}

    # Get platform-specific config
    platform_config = all_sync_config.get(platform, {})

    # Override with command-line options
    if repo:
        platform_config["repository"] = repo
    if token:
        platform_config["token"] = token

    # For GitHub, try to extract repo from git remote if not provided
    if platform == "github" and not platform_config.get("repository"):
        git_utils = GitUtils(project_path)
        if git_utils.is_git_repo():
            try:
                remote_url = git_utils.get_remote_url()
                if remote_url and "github.com" in remote_url:
                    # Parse GitHub URL
                    if remote_url.endswith(".git"):
                        remote_url = remote_url[:-4]
                    if "github.com/" in remote_url:
                        repo = remote_url.split("github.com/")[-1]
                        if repo.startswith("git@"):
                            repo = repo.split(":")[-1]
                        platform_config["repository"] = repo
            except Exception:
                pass

    # Validate we have required configuration
    if not platform_config.get("repository") and platform == "github":
        console.print(
            "[red]Could not determine repository. Use --repo owner/repo[/red]"
        )
        raise typer.Exit(1)

    console.print(
        f"[blue]{platform.title()} repository: {platform_config.get('repository', 'N/A')}[/blue]"
    )

    task_manager = TaskManager(project_path)
    bridge = SyncBridge(task_manager)

    try:
        if action == "status":
            # Show sync status
            last_sync = all_sync_config.get("last_sync", {}).get(platform, "Never")

            # Count platform-specific items
            all_tasks = task_manager.list_tasks()
            platform_items = [
                t
                for t in all_tasks
                if t.metadata and t.metadata.get("platform") == platform
            ]

            console.print(
                Panel.fit(
                    f"""[bold blue]{platform.title()} Sync Status[/bold blue]

[dim]Repository:[/dim] {platform_config.get('repository', 'Not configured')}
[dim]Last sync:[/dim] {last_sync}
[dim]Platform items:[/dim] {len(platform_items)}
[dim]Total local items:[/dim] {len(all_tasks)}

[dim]Configuration:[/dim]
• Repository: {platform_config.get('repository', 'Not set')}
• Auth: {'Configured' if platform_config.get('token') or platform == 'github' else 'Not configured'}""",
                    title=f"{platform.title()} Sync Status",
                    border_style="blue",
                )
            )

        elif action == "pull":
            # Pull items from platform
            console.print(
                f"[blue]Pulling from {platform} repository: {platform_config.get('repository')}[/blue]"
            )

            if dry_run:
                console.print(
                    f"[yellow]DRY RUN: Would fetch items from {platform}[/yellow]"
                )

            # Use the sync bridge for backward compatibility
            created, updated = bridge.pull_from_platform(
                platform, platform_config, dry_run
            )

            if not dry_run:
                # Update sync metadata
                all_sync_config.setdefault("last_sync", {})
                all_sync_config["last_sync"][platform] = datetime.now().isoformat()
                with open(sync_config_file, "w") as f:
                    json.dump(all_sync_config, f, indent=2)

            console.print(f"[green]Successfully synced from {platform}:[/green]")
            console.print(f"• Items created: {created}")
            console.print(f"• Items updated: {updated}")

        elif action == "push":
            # Push items to platform
            console.print(
                f"[blue]Pushing to {platform} repository: {platform_config.get('repository')}[/blue]"
            )

            if dry_run:
                console.print(
                    f"[yellow]DRY RUN: Would push items to {platform}[/yellow]"
                )

            # Use the sync bridge
            created, updated, errors = bridge.push_to_platform(
                platform, platform_config, dry_run
            )

            if not dry_run:
                # Update sync metadata
                all_sync_config.setdefault("last_sync", {})
                all_sync_config["last_sync"][platform] = datetime.now().isoformat()
                with open(sync_config_file, "w") as f:
                    json.dump(all_sync_config, f, indent=2)

            console.print(f"[green]Successfully pushed to {platform}:[/green]")
            console.print(f"• Items created: {created}")
            console.print(f"• Items updated: {updated}")

            if errors:
                console.print(
                    f"\n[yellow]Warnings ({len(errors)} items failed):[/yellow]"
                )
                for error in errors[:5]:  # Show first 5 errors
                    console.print(f"  • {error}")
                if len(errors) > 5:
                    console.print(f"  • ... and {len(errors) - 5} more errors")

        else:
            console.print(f"[red]Unknown action: {action}[/red]")
            console.print("Valid actions: status, pull, push")
            raise typer.Exit(1)

    except AdapterNotFoundError:
        console.print(f"[red]Platform not supported: {platform}[/red]")
        console.print(
            "Use 'aitrackdown sync list platforms' to see available platforms"
        )
        raise typer.Exit(1)
    except SyncError as e:
        console.print(f"[red]Sync error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def github(
    action: str = typer.Argument(..., help="Action to perform (pull, push, status)"),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="GitHub repository (owner/repo)"
    ),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="GitHub token"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done without executing"
    ),
) -> None:
    """Sync with GitHub issues and pull requests."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    git_utils = GitUtils(project_path)
    if not git_utils.is_git_repo():
        console.print("[red]Not a git repository[/red]")
        raise typer.Exit(1)

    # Load sync configuration
    sync_config_file = project_path / ".aitrackdown" / "sync.json"
    if sync_config_file.exists():
        with open(sync_config_file) as f:
            sync_config = json.load(f)
    else:
        sync_config = {"github": {}, "last_sync": {}}

    # Get repository info
    if not repo:
        # Try to extract from git remote
        try:
            remote_url = git_utils.get_remote_url()
            if remote_url and "github.com" in remote_url:
                # Parse GitHub URL
                if remote_url.endswith(".git"):
                    remote_url = remote_url[:-4]
                if "github.com/" in remote_url:
                    repo = remote_url.split("github.com/")[-1]
                    if repo.startswith("git@"):
                        repo = repo.split(":")[-1]
        except Exception:
            pass

    if not repo:
        console.print(
            "[red]Could not determine repository. Use --repo owner/repo[/red]"
        )
        raise typer.Exit(1)

    console.print(f"[blue]GitHub repository: {repo}[/blue]")

    # DEPRECATED: This command is maintained for backward compatibility
    # Use 'aitrackdown sync platform github <action>' instead
    console.print(
        "[yellow]Note: This command is deprecated. "
        "Use 'aitrackdown sync platform github <action>' instead[/yellow]"
    )

    task_manager = TaskManager(project_path)

    if action == "status":
        # Show sync status
        # Check if gh CLI is authenticated
        try:
            GitHubCLI(repo)  # Test if gh CLI is authenticated
            gh_auth_status = "Yes (via gh CLI)"
        except GitHubError:
            gh_auth_status = (
                "Yes" if token or sync_config.get("github", {}).get("token") else "No"
            )

        console.print(
            Panel.fit(
                f"""[bold blue]GitHub Sync Status[/bold blue]

[dim]Repository:[/dim] {repo}
[dim]Last sync:[/dim] {sync_config.get('last_sync', {}).get('github', 'Never')}
[dim]Token configured:[/dim] {gh_auth_status}

[dim]Local counts:[/dim]
• Issues: {len([t for t in task_manager.list_tasks() if 'issue' in t.tags])}
• PRs: {len([t for t in task_manager.list_tasks() if 'pull-request' in t.tags])}""",
                title="Sync Status",
                border_style="blue",
            )
        )

    elif action == "pull":
        # Pull issues and PRs from GitHub
        console.print(f"[blue]Pulling from GitHub repository: {repo}[/blue]")

        try:
            gh = GitHubCLI(repo)

            if dry_run:
                console.print(
                    "[yellow]DRY RUN: Would fetch issues and PRs from GitHub[/yellow]"
                )
                console.print("• Fetch open issues")
                console.print("• Fetch open pull requests")
                console.print("• Create local tasks for new items")
                console.print("• Update existing tasks with changes")

                # Show what would be pulled
                issues = gh.list_issues(state="open", limit=10)
                prs = gh.list_prs(state="open", limit=10)

                console.print(f"\nWould pull {len(issues)} issues and {len(prs)} PRs")
            else:
                # Pull issues
                created_issues, updated_issues = gh.pull_issues_from_github(
                    task_manager, dry_run=False
                )

                # TODO: Pull PRs (similar to issues but with PR-specific logic)
                created_prs = 0
                updated_prs = 0

                # Update sync metadata
                sync_config["last_sync"]["github"] = datetime.now().isoformat()
                with open(sync_config_file, "w") as f:
                    json.dump(sync_config, f, indent=2)

                console.print("[green]Successfully synced from GitHub:[/green]")
                console.print(
                    f"• Issues: {created_issues} created, {updated_issues} updated"
                )
                console.print(f"• PRs: {created_prs} created, {updated_prs} updated")

        except GitHubError as e:
            console.print(f"[red]GitHub sync error: {e}[/red]")
            raise typer.Exit(1) from e

    elif action == "push":
        # Push local changes to GitHub
        console.print(f"[blue]Pushing to GitHub repository: {repo}[/blue]")

        try:
            gh = GitHubCLI(repo)

            # Find unsynced items
            all_tasks = task_manager.list_tasks()
            issues = [t for t in all_tasks if "issue" in t.tags]
            prs = [t for t in all_tasks if "pull-request" in t.tags]

            unsynced_issues = [i for i in issues if not i.metadata.get("github_id")]
            unsynced_prs = [p for p in prs if not p.metadata.get("github_id")]

            if dry_run:
                console.print(
                    f"[yellow]DRY RUN: Would sync {len(unsynced_issues)} issues and {len(unsynced_prs)} PRs[/yellow]"
                )

                if unsynced_issues:
                    console.print("\nIssues to create:")
                    for issue in unsynced_issues:
                        console.print(f"  • {issue.id}: {issue.title}")

                if unsynced_prs:
                    console.print("\nPRs to create:")
                    for pr in unsynced_prs:
                        console.print(f"  • {pr.id}: {pr.title}")
            else:
                created_issues = 0
                created_prs = 0
                errors = []

                # Push issues
                if unsynced_issues:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            "Creating GitHub issues...", total=len(unsynced_issues)
                        )

                        for issue in unsynced_issues:
                            try:
                                github_issue = gh.sync_issue_to_github(issue)

                                # Update local task with GitHub metadata
                                task_manager.update_task(
                                    issue.id,
                                    metadata={
                                        **issue.metadata,
                                        "github_id": github_issue["id"],
                                        "github_number": github_issue["number"],
                                        "github_url": github_issue["url"],
                                        "github_created": github_issue["createdAt"],
                                    },
                                )

                                created_issues += 1
                                progress.update(task, advance=1)

                            except Exception as e:
                                errors.append(f"Failed to create issue {issue.id}: {e}")
                                progress.update(task, advance=1)

                # Push PRs
                if unsynced_prs:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        console=console,
                    ) as progress:
                        task = progress.add_task(
                            "Creating GitHub PRs...", total=len(unsynced_prs)
                        )

                        for pr in unsynced_prs:
                            try:
                                # Note: PR creation requires head branch to exist
                                # This is a simplified version - you'd want more logic here
                                github_pr = gh.sync_pr_to_github(pr)

                                # Update local task with GitHub metadata
                                task_manager.update_task(
                                    pr.id,
                                    metadata={
                                        **pr.metadata,
                                        "github_id": github_pr["id"],
                                        "github_number": github_pr["number"],
                                        "github_url": github_pr["url"],
                                        "github_created": github_pr["createdAt"],
                                    },
                                )

                                created_prs += 1
                                progress.update(task, advance=1)

                            except Exception as e:
                                errors.append(f"Failed to create PR {pr.id}: {e}")
                                progress.update(task, advance=1)

                # Update sync metadata
                sync_config["last_sync"]["github"] = datetime.now().isoformat()
                with open(sync_config_file, "w") as f:
                    json.dump(sync_config, f, indent=2)

                # Show results
                console.print("\n[green]Successfully pushed to GitHub:[/green]")
                console.print(f"• Issues created: {created_issues}")
                console.print(f"• PRs created: {created_prs}")

                if errors:
                    console.print(
                        f"\n[yellow]Warnings ({len(errors)} items failed):[/yellow]"
                    )
                    for error in errors[:5]:  # Show first 5 errors
                        console.print(f"  • {error}")
                    if len(errors) > 5:
                        console.print(f"  • ... and {len(errors) - 5} more errors")

        except GitHubError as e:
            console.print(f"[red]GitHub sync error: {e}[/red]")
            raise typer.Exit(1) from e

    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Valid actions: status, pull, push")
        raise typer.Exit(1)


@app.command()
def list_available() -> None:
    """List available sync platforms.

    WHY: Provides a convenient way to discover which platforms are supported
    without having to know the special 'list platforms' syntax.
    """
    platforms = list_platforms()

    console.print(
        Panel.fit(
            "[bold blue]Available Sync Platforms[/bold blue]\n\n"
            + "\n".join([f"• {p}" for p in platforms])
            + "\n\n[dim]Use 'aitrackdown sync platform <name> status' to check platform status[/dim]",
            title="Sync Platforms",
            border_style="blue",
        )
    )


@app.command()
def config(
    platform: str = typer.Argument(..., help="Platform to configure"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Configuration key"),
    value: Optional[str] = typer.Option(
        None, "--value", "-v", help="Configuration value"
    ),
    list_config: bool = typer.Option(
        False, "--list", "-l", help="List current configuration"
    ),
) -> None:
    """Configure sync settings for external platforms."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    # Ensure sync directory exists
    sync_dir = project_path / ".aitrackdown"
    sync_dir.mkdir(exist_ok=True)

    sync_config_file = sync_dir / "sync.json"

    # Load existing config
    if sync_config_file.exists():
        with open(sync_config_file) as f:
            sync_config = json.load(f)
    else:
        sync_config = {}

    if platform not in sync_config:
        sync_config[platform] = {}

    if list_config:
        # Show current configuration
        platform_config = sync_config.get(platform, {})

        if not platform_config:
            console.print(f"[yellow]No configuration found for {platform}[/yellow]")
            # Show available platforms
            platforms = list_platforms()
            if platform not in platforms:
                console.print(
                    f"\n[dim]Available platforms: {', '.join(platforms)}[/dim]"
                )
            return

        console.print(
            Panel.fit(
                f"""[bold blue]{platform.title()} Configuration[/bold blue]

"""
                + "\n".join(
                    [f"[dim]{k}:[/dim] {v}" for k, v in platform_config.items()]
                ),
                title="Sync Configuration",
                border_style="blue",
            )
        )
        return

    if not key:
        console.print(f"[yellow]Available {platform} configuration keys:[/yellow]")

        # Platform-specific configuration help
        config_help = {
            "github": [
                ("repository", "GitHub repository (owner/repo)"),
                ("token", "GitHub personal access token (optional if using gh CLI)"),
                ("api_url", "GitHub API URL (default: https://api.github.com)"),
            ],
            "gitlab": [
                ("repository", "GitLab project path or ID"),
                ("token", "GitLab access token"),
                ("api_url", "GitLab API URL"),
            ],
            "clickup": [
                ("workspace_id", "ClickUp workspace ID"),
                ("token", "ClickUp API token"),
                ("list_id", "Default list ID for tasks"),
            ],
            "linear": [
                ("team_id", "Linear team ID"),
                ("token", "Linear API key"),
            ],
            "jira": [
                ("server", "JIRA server URL"),
                ("project_key", "JIRA project key"),
                ("username", "JIRA username"),
                ("token", "JIRA API token"),
            ],
        }

        if platform in config_help:
            for key_name, description in config_help[platform]:
                console.print(f"• {key_name} - {description}")
        else:
            # Generic configuration for unknown platforms
            console.print("• repository - Repository or project identifier")
            console.print("• token - Authentication token")
            console.print("• api_url - API endpoint URL")

        console.print(
            f"\nUse: aitrackdown sync config {platform} --key <key> --value <value>"
        )
        return

    if value is None:
        # Get configuration value
        current_value = sync_config[platform].get(key)
        if current_value:
            if key == "token":
                console.print(
                    f"{key}: {'*' * len(current_value[:4]) + current_value[-4:]}"
                )
            else:
                console.print(f"{key}: {current_value}")
        else:
            console.print(
                f"[yellow]Configuration key '{key}' not found for {platform}[/yellow]"
            )
        return

    # Set configuration value
    sync_config[platform][key] = value

    # Save configuration
    with open(sync_config_file, "w") as f:
        json.dump(sync_config, f, indent=2)

    console.print(
        f"[green]Set {platform}.{key} = {value if key != 'token' else '***'}[/green]"
    )


@app.command()
def import_data(
    source: str = typer.Argument(..., help="Data source (github-json, csv, trello)"),
    file_path: str = typer.Argument(..., help="Path to import file"),
    task_type: str = typer.Option(
        "task", "--type", "-t", help="Default task type (task, issue, epic)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be imported"
    ),
) -> None:
    """Import tasks from external data sources."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    import_file = Path(file_path)
    if not import_file.exists():
        console.print(f"[red]Import file not found: {file_path}[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    imported_count = 0

    if source == "github-json":
        # Import from GitHub issues/PRs JSON export
        with open(import_file) as f:
            github_data = json.load(f)

        if not isinstance(github_data, list):
            github_data = [github_data]

        for item in github_data:
            title = item.get("title", "Untitled")
            description = item.get("body", "")
            labels = [label.get("name", "") for label in item.get("labels", [])]

            # Determine type
            if "pull_request" in item:
                item_type = "pull-request"
                tags = ["pull-request"] + labels
            else:
                item_type = "issue"
                tags = ["issue"] + labels

            task_data = {
                "title": title,
                "description": description,
                "tags": tags,
                "metadata": {
                    "github_id": item.get("id"),
                    "github_number": item.get("number"),
                    "github_url": item.get("html_url"),
                    "imported_from": "github",
                },
            }

            if dry_run:
                console.print(f"Would import: {title} ({item_type})")
            else:
                task_manager.create_task(**task_data)
                imported_count += 1

    elif source == "csv":
        # Import from CSV file
        import csv

        with open(import_file) as f:
            reader = csv.DictReader(f)

            for row in reader:
                title = row.get("title", row.get("Title", "Untitled"))
                description = row.get("description", row.get("Description", ""))
                status = row.get("status", row.get("Status", "open"))
                priority = row.get("priority", row.get("Priority", "medium"))

                task_data = {
                    "title": title,
                    "description": description,
                    "status": status,
                    "priority": priority,
                    "tags": [task_type],
                    "metadata": {"imported_from": "csv", "original_data": row},
                }

                if dry_run:
                    console.print(f"Would import: {title} ({task_type})")
                else:
                    task_manager.create_task(**task_data)
                    imported_count += 1

    else:
        console.print(f"[red]Unsupported import source: {source}[/red]")
        console.print("Supported sources: github-json, csv")
        raise typer.Exit(1)

    if dry_run:
        if source == "github-json":
            item_count = len(github_data)
        else:
            with open(import_file) as f:
                item_count = len(list(csv.DictReader(f)))
        console.print(f"[yellow]DRY RUN: Would import {item_count} items[/yellow]")
    else:
        console.print(f"[green]Successfully imported {imported_count} items[/green]")


@app.command()
def export(
    format: str = typer.Argument(..., help="Export format (json, csv, github-json)"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file path"
    ),
    task_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by task type"
    ),
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
) -> None:
    """Export tasks to external formats."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Apply filters
    filtered_tasks = all_tasks

    if task_type:
        filtered_tasks = [t for t in filtered_tasks if task_type in t.tags]

    if status_filter:
        filtered_tasks = [t for t in filtered_tasks if t.status == status_filter]

    # Generate output filename if not provided
    if not output:
        timestamp = (
            filtered_tasks[0].updated_at.strftime("%Y%m%d_%H%M%S")
            if filtered_tasks
            else "empty"
        )
        output = f"export_{timestamp}.{format.split('-')[0]}"

    output_path = project_path / output

    if format == "json":
        # Export as JSON
        export_data = []
        for task in filtered_tasks:
            export_data.append(
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "tags": task.tags,
                    "assignees": task.assignees,
                    "created_at": task.created_at.isoformat(),
                    "updated_at": task.updated_at.isoformat(),
                    "metadata": task.metadata,
                }
            )

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

    elif format == "csv":
        # Export as CSV
        import csv

        with open(output_path, "w", newline="") as f:
            fieldnames = [
                "id",
                "title",
                "description",
                "status",
                "priority",
                "tags",
                "assignees",
                "created_at",
                "updated_at",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for task in filtered_tasks:
                writer.writerow(
                    {
                        "id": task.id,
                        "title": task.title,
                        "description": task.description,
                        "status": task.status,
                        "priority": task.priority,
                        "tags": ", ".join(task.tags),
                        "assignees": ", ".join(task.assignees),
                        "created_at": task.created_at.isoformat(),
                        "updated_at": task.updated_at.isoformat(),
                    }
                )

    elif format == "github-json":
        # Export in GitHub issues format
        export_data = []
        for task in filtered_tasks:
            if "issue" in task.tags:
                github_issue = {
                    "title": task.title,
                    "body": task.description,
                    "state": (
                        "open" if task.status in ["open", "in_progress"] else "closed"
                    ),
                    "labels": [{"name": tag} for tag in task.tags if tag != "issue"],
                }
                export_data.append(github_issue)

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

    else:
        console.print(f"[red]Unsupported export format: {format}[/red]")
        console.print("Supported formats: json, csv, github-json")
        raise typer.Exit(1)

    console.print(
        f"[green]Exported {len(filtered_tasks)} tasks to {output_path}[/green]"
    )


# Add convenience commands for backward compatibility
@app.command(name="pull")
def pull_shortcut(
    platform: str = typer.Argument("github", help="Platform to pull from"),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository identifier"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="Authentication token"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done"
    ),
) -> None:
    """Shortcut for 'sync platform <platform> pull'."""
    sync_platform(platform, "pull", repo, token, dry_run)


@app.command(name="push")
def push_shortcut(
    platform: str = typer.Argument("github", help="Platform to push to"),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository identifier"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", "-t", help="Authentication token"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be done"
    ),
) -> None:
    """Shortcut for 'sync platform <platform> push'."""
    sync_platform(platform, "push", repo, token, dry_run)


@app.command(name="status")
def status_shortcut(
    platform: str = typer.Argument("github", help="Platform to check status"),
    repo: Optional[str] = typer.Option(
        None, "--repo", "-r", help="Repository identifier"
    ),
) -> None:
    """Shortcut for 'sync platform <platform> status'."""
    sync_platform(platform, "status", repo, None, False)


if __name__ == "__main__":
    app()
