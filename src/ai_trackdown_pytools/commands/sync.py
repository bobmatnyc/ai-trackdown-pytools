"""Sync commands for GitHub and other platforms."""

from pathlib import Path
from typing import List, Optional
import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.git import GitUtils

app = typer.Typer(help="Sync with external platforms (GitHub, GitLab, etc.)")
console = Console()


@app.command()
def github(
    action: str = typer.Argument(..., help="Action to perform (pull, push, status)"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r", help="GitHub repository (owner/repo)"),
    token: Optional[str] = typer.Option(None, "--token", "-t", help="GitHub token"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without executing"),
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
        with open(sync_config_file, 'r') as f:
            sync_config = json.load(f)
    else:
        sync_config = {"github": {}, "last_sync": {}}
    
    # Get repository info
    if not repo:
        # Try to extract from git remote
        try:
            remote_url = git_utils.get_remote_url()
            if "github.com" in remote_url:
                # Parse GitHub URL
                if remote_url.endswith('.git'):
                    remote_url = remote_url[:-4]
                if 'github.com/' in remote_url:
                    repo = remote_url.split('github.com/')[-1]
                    if repo.startswith('git@'):
                        repo = repo.split(':')[-1]
        except Exception:
            pass
    
    if not repo:
        console.print("[red]Could not determine repository. Use --repo owner/repo[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]GitHub repository: {repo}[/blue]")
    
    task_manager = TaskManager(project_path)
    
    if action == "status":
        # Show sync status
        console.print(Panel.fit(
            f"""[bold blue]GitHub Sync Status[/bold blue]

[dim]Repository:[/dim] {repo}
[dim]Last sync:[/dim] {sync_config.get('last_sync', {}).get('github', 'Never')}
[dim]Token configured:[/dim] {'Yes' if token or sync_config.get('github', {}).get('token') else 'No'}

[dim]Local counts:[/dim]
• Issues: {len([t for t in task_manager.list_tasks() if 'issue' in t.tags])}
• PRs: {len([t for t in task_manager.list_tasks() if 'pull-request' in t.tags])}""",
            title="Sync Status",
            border_style="blue"
        ))
    
    elif action == "pull":
        # Pull issues and PRs from GitHub
        console.print(f"[blue]Pulling from GitHub repository: {repo}[/blue]")
        
        if dry_run:
            console.print("[yellow]DRY RUN: Would fetch issues and PRs from GitHub[/yellow]")
            console.print("• Fetch open issues")
            console.print("• Fetch open pull requests") 
            console.print("• Create local tasks for new items")
            console.print("• Update existing tasks with changes")
        else:
            console.print("[yellow]GitHub API integration not implemented yet[/yellow]")
            console.print("This would:")
            console.print("1. Fetch issues from GitHub API")
            console.print("2. Fetch pull requests from GitHub API")
            console.print("3. Create/update local tasks")
            console.print("4. Store sync metadata")
    
    elif action == "push":
        # Push local changes to GitHub
        console.print(f"[blue]Pushing to GitHub repository: {repo}[/blue]")
        
        # Find unsynced items
        issues = [t for t in task_manager.list_tasks() if 'issue' in t.tags]
        prs = [t for t in task_manager.list_tasks() if 'pull-request' in t.tags]
        
        unsynced_issues = [i for i in issues if not i.metadata.get('github_id')]
        unsynced_prs = [p for p in prs if not p.metadata.get('github_id')]
        
        if dry_run:
            console.print(f"[yellow]DRY RUN: Would sync {len(unsynced_issues)} issues and {len(unsynced_prs)} PRs[/yellow]")
            
            if unsynced_issues:
                console.print("\nIssues to create:")
                for issue in unsynced_issues:
                    console.print(f"  • {issue.id}: {issue.title}")
            
            if unsynced_prs:
                console.print("\nPRs to create:")
                for pr in unsynced_prs:
                    console.print(f"  • {pr.id}: {pr.title}")
        else:
            console.print("[yellow]GitHub API integration not implemented yet[/yellow]")
            console.print("This would:")
            console.print("1. Create GitHub issues for unsynced local issues")
            console.print("2. Create GitHub PRs for unsynced local PRs")
            console.print("3. Update local tasks with GitHub IDs")
            console.print("4. Store sync metadata")
    
    else:
        console.print(f"[red]Unknown action: {action}[/red]")
        console.print("Valid actions: status, pull, push")
        raise typer.Exit(1)


@app.command()
def config(
    platform: str = typer.Argument(..., help="Platform to configure (github, gitlab)"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Configuration key"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Configuration value"),
    list_config: bool = typer.Option(False, "--list", "-l", help="List current configuration"),
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
        with open(sync_config_file, 'r') as f:
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
            return
        
        console.print(Panel.fit(
            f"""[bold blue]{platform.title()} Configuration[/bold blue]

""" + "\n".join([f"[dim]{k}:[/dim] {v}" for k, v in platform_config.items()]),
            title="Sync Configuration",
            border_style="blue"
        ))
        return
    
    if not key:
        console.print(f"[yellow]Available {platform} configuration keys:[/yellow]")
        if platform == "github":
            console.print("• token - GitHub personal access token")
            console.print("• repo - Default repository (owner/repo)")
            console.print("• api_url - GitHub API URL (default: https://api.github.com)")
        elif platform == "gitlab":
            console.print("• token - GitLab access token")
            console.print("• project_id - GitLab project ID")
            console.print("• api_url - GitLab API URL")
        
        console.print(f"\nUse: aitrackdown sync config {platform} --key <key> --value <value>")
        return
    
    if value is None:
        # Get configuration value
        current_value = sync_config[platform].get(key)
        if current_value:
            if key == "token":
                console.print(f"{key}: {'*' * len(current_value[:4]) + current_value[-4:]}")
            else:
                console.print(f"{key}: {current_value}")
        else:
            console.print(f"[yellow]Configuration key '{key}' not found for {platform}[/yellow]")
        return
    
    # Set configuration value
    sync_config[platform][key] = value
    
    # Save configuration
    with open(sync_config_file, 'w') as f:
        json.dump(sync_config, f, indent=2)
    
    console.print(f"[green]Set {platform}.{key} = {value if key != 'token' else '***'}[/green]")


@app.command()
def import_data(
    source: str = typer.Argument(..., help="Data source (github-json, csv, trello)"),
    file_path: str = typer.Argument(..., help="Path to import file"),
    task_type: str = typer.Option("task", "--type", "-t", help="Default task type (task, issue, epic)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be imported"),
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
        with open(import_file, 'r') as f:
            github_data = json.load(f)
        
        if not isinstance(github_data, list):
            github_data = [github_data]
        
        for item in github_data:
            title = item.get('title', 'Untitled')
            description = item.get('body', '')
            labels = [label.get('name', '') for label in item.get('labels', [])]
            
            # Determine type
            if 'pull_request' in item:
                item_type = 'pull-request'
                tags = ['pull-request'] + labels
            else:
                item_type = 'issue'
                tags = ['issue'] + labels
            
            task_data = {
                'title': title,
                'description': description,
                'tags': tags,
                'metadata': {
                    'github_id': item.get('id'),
                    'github_number': item.get('number'),
                    'github_url': item.get('html_url'),
                    'imported_from': 'github'
                }
            }
            
            if dry_run:
                console.print(f"Would import: {title} ({item_type})")
            else:
                task_manager.create_task(**task_data)
                imported_count += 1
    
    elif source == "csv":
        # Import from CSV file
        import csv
        
        with open(import_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                title = row.get('title', row.get('Title', 'Untitled'))
                description = row.get('description', row.get('Description', ''))
                status = row.get('status', row.get('Status', 'open'))
                priority = row.get('priority', row.get('Priority', 'medium'))
                
                task_data = {
                    'title': title,
                    'description': description,
                    'status': status,
                    'priority': priority,
                    'tags': [task_type],
                    'metadata': {
                        'imported_from': 'csv',
                        'original_data': row
                    }
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
        console.print(f"[yellow]DRY RUN: Would import {len(github_data if source == 'github-json' else list(csv.DictReader(open(import_file))))} items[/yellow]")
    else:
        console.print(f"[green]Successfully imported {imported_count} items[/green]")


@app.command()
def export(
    format: str = typer.Argument(..., help="Export format (json, csv, github-json)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by task type"),
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
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
        timestamp = filtered_tasks[0].updated_at.strftime("%Y%m%d_%H%M%S") if filtered_tasks else "empty"
        output = f"export_{timestamp}.{format.split('-')[0]}"
    
    output_path = project_path / output
    
    if format == "json":
        # Export as JSON
        export_data = []
        for task in filtered_tasks:
            export_data.append({
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'tags': task.tags,
                'assignees': task.assignees,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat(),
                'metadata': task.metadata
            })
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    elif format == "csv":
        # Export as CSV
        import csv
        
        with open(output_path, 'w', newline='') as f:
            fieldnames = ['id', 'title', 'description', 'status', 'priority', 'tags', 'assignees', 'created_at', 'updated_at']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            for task in filtered_tasks:
                writer.writerow({
                    'id': task.id,
                    'title': task.title,
                    'description': task.description,
                    'status': task.status,
                    'priority': task.priority,
                    'tags': ', '.join(task.tags),
                    'assignees': ', '.join(task.assignees),
                    'created_at': task.created_at.isoformat(),
                    'updated_at': task.updated_at.isoformat()
                })
    
    elif format == "github-json":
        # Export in GitHub issues format
        export_data = []
        for task in filtered_tasks:
            if 'issue' in task.tags:
                github_issue = {
                    'title': task.title,
                    'body': task.description,
                    'state': 'open' if task.status in ['open', 'in_progress'] else 'closed',
                    'labels': [{'name': tag} for tag in task.tags if tag != 'issue']
                }
                export_data.append(github_issue)
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
    
    else:
        console.print(f"[red]Unsupported export format: {format}[/red]")
        console.print("Supported formats: json, csv, github-json")
        raise typer.Exit(1)
    
    console.print(f"[green]Exported {len(filtered_tasks)} tasks to {output_path}[/green]")


if __name__ == "__main__":
    app()