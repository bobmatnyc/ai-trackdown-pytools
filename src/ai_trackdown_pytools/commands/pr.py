"""Pull request management commands."""

from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.git import GitUtils
from ai_trackdown_pytools.utils.templates import TemplateManager

app = typer.Typer(help="Pull request management and tracking")
console = Console()


@app.command()
def create(
    title: Optional[str] = typer.Argument(None, help="Pull request title"),
    description: Optional[str] = typer.Option(
        None,
        "--description",
        "-d",
        help="Pull request description",
    ),
    branch: Optional[str] = typer.Option(
        None,
        "--branch",
        "-b",
        help="Source branch for pull request",
    ),
    target: Optional[str] = typer.Option(
        "main",
        "--target",
        "-t",
        help="Target branch for pull request",
    ),
    assignee: Optional[List[str]] = typer.Option(
        None,
        "--assignee",
        "-a",
        help="PR assignee (can be specified multiple times)",
    ),
    reviewer: Optional[List[str]] = typer.Option(
        None,
        "--reviewer",
        "-r",
        help="PR reviewer (can be specified multiple times)",
    ),
    label: Optional[List[str]] = typer.Option(
        None,
        "--label",
        "-l",
        help="PR label (can be specified multiple times)",
    ),
    draft: bool = typer.Option(
        False,
        "--draft",
        help="Mark as draft pull request",
    ),
    template: Optional[str] = typer.Option(
        None,
        "--template",
        help="PR template to use",
    ),
    closes: Optional[str] = typer.Option(
        None,
        "--closes",
        help="Issue ID that this PR closes",
    ),
) -> None:
    """Create a new pull request task."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    git_utils = GitUtils(project_path)

    if not git_utils.is_git_repo():
        console.print("[red]Not a git repository[/red]")
        raise typer.Exit(1)

    # Get current branch if not specified
    if not branch:
        branch = git_utils.get_current_branch()
        if not branch:
            console.print("[red]Could not determine current branch[/red]")
            raise typer.Exit(1)

    if not title:
        from rich.prompt import Prompt

        title = Prompt.ask("Pull request title")

    if not description:
        from rich.prompt import Prompt

        description = Prompt.ask("Pull request description", default="")

    # Build PR tags
    pr_tags = ["pull-request", "review"]
    if label:
        pr_tags.extend(label)
    if draft:
        pr_tags.append("draft")

    # Create PR task
    task_manager = TaskManager(project_path)

    pr_data = {
        "type": "pr",
        "title": f"PR: {title}",
        "description": description,
        "tags": pr_tags,
        "priority": "medium",
        "assignees": assignee or [],
        "metadata": {
            "type": "pull_request",
            "source_branch": branch,
            "target_branch": target,
            "status": "draft" if draft else "open",
            "reviewers": reviewer or [],
            "labels": label or [],
            "closes": closes,
            "commits": [],
            "diff_stats": {},
            "checks": {},
        },
    }

    # Apply template if specified
    if template:
        template_manager = TemplateManager()
        template_data = template_manager.load_template("pr", template)
        if template_data:
            pr_data.update(template_data)
            console.print(f"[green]Applied template: {template}[/green]")

    # Get git diff stats
    try:
        diff_stats = git_utils.get_diff_stats(f"{target}..{branch}")
        pr_data["metadata"]["diff_stats"] = diff_stats
    except Exception:
        pass  # Git diff may fail if branches don't exist

    new_pr = task_manager.create_task(**pr_data)

    console.print(
        Panel.fit(
            f"""[bold green]Pull request task created![/bold green]

[dim]ID:[/dim] {new_pr.id}
[dim]Title:[/dim] {title}
[dim]Source:[/dim] {branch}
[dim]Target:[/dim] {target}
[dim]Status:[/dim] {'Draft' if draft else 'Open'}
[dim]Reviewers:[/dim] {', '.join(reviewer) if reviewer else 'None'}
[dim]Closes:[/dim] {closes or 'None'}
[dim]File:[/dim] {new_pr.file_path}

[dim]Next steps:[/dim]
1. Review changes: [cyan]git diff {target}..{branch}[/cyan]
2. Update PR description: [cyan]aitrackdown pr update {new_pr.id} --description "..."[/cyan]
3. Request review: [cyan]aitrackdown pr review {new_pr.id} --reviewer name[/cyan]""",
            title="PR Task Created",
            border_style="purple",
        )
    )


@app.command()
def list(
    status_filter: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status"
    ),
    author_filter: Optional[str] = typer.Option(
        None, "--author", "-a", help="Filter by author"
    ),
    reviewer_filter: Optional[str] = typer.Option(
        None, "--reviewer", "-r", help="Filter by reviewer"
    ),
    target_filter: Optional[str] = typer.Option(
        None, "--target", "-t", help="Filter by target branch"
    ),
    show_closed: bool = typer.Option(
        False, "--closed", "-c", help="Include closed PRs"
    ),
    show_draft: bool = typer.Option(True, "--draft", "-d", help="Include draft PRs"),
    limit: int = typer.Option(
        20, "--limit", "-l", help="Maximum number of PRs to show"
    ),
) -> None:
    """List pull requests."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    all_tasks = task_manager.list_tasks()

    # Filter PRs
    prs = [task for task in all_tasks if "pull-request" in task.tags]

    # Apply filters
    if status_filter:
        prs = [pr for pr in prs if pr.metadata.get("status") == status_filter]

    if author_filter:
        prs = [pr for pr in prs if author_filter in pr.assignees]

    if reviewer_filter:
        prs = [pr for pr in prs if reviewer_filter in pr.metadata.get("reviewers", [])]

    if target_filter:
        prs = [pr for pr in prs if pr.metadata.get("target_branch") == target_filter]

    if not show_closed:
        prs = [pr for pr in prs if pr.status not in ["completed", "cancelled"]]

    if not show_draft:
        prs = [pr for pr in prs if pr.metadata.get("status") != "draft"]

    # Limit results
    prs = prs[:limit]

    if not prs:
        console.print("[yellow]No pull requests found[/yellow]")
        return

    table = Table(title=f"Pull Requests ({len(prs)} found)")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Source → Target", style="blue")
    table.add_column("Status", style="magenta")
    table.add_column("Author", style="yellow")
    table.add_column("Reviewers", style="green")

    for pr in prs:
        title = pr.title.replace("PR: ", "")
        source = pr.metadata.get("source_branch", "")
        target = pr.metadata.get("target_branch", "")
        author = ", ".join(pr.assignees) if pr.assignees else "Unknown"
        reviewers = ", ".join(pr.metadata.get("reviewers", [])) or "None"
        pr_status = pr.metadata.get("status", pr.status)

        table.add_row(
            pr.id,
            title[:30] + "..." if len(title) > 30 else title,
            f"{source} → {target}",
            pr_status,
            author[:15] + "..." if len(author) > 15 else author,
            reviewers[:15] + "..." if len(reviewers) > 15 else reviewers,
        )

    console.print(table)


@app.command()
def show(
    pr_id: str = typer.Argument(..., help="PR ID to display"),
    detailed: bool = typer.Option(
        False, "--detailed", "-d", help="Show detailed information"
    ),
    show_commits: bool = typer.Option(
        False, "--commits", "-c", help="Show commit history"
    ),
) -> None:
    """Show detailed pull request information."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    pr = task_manager.load_task(pr_id)

    if not pr or "pull-request" not in pr.tags:
        console.print(f"[red]Pull request '{pr_id}' not found[/red]")
        raise typer.Exit(1)

    title = pr.title.replace("PR: ", "")
    author = ", ".join(pr.assignees) if pr.assignees else "Unknown"
    reviewers = ", ".join(pr.metadata.get("reviewers", [])) or "None"
    labels = ", ".join(pr.metadata.get("labels", [])) or "None"

    info_text = f"""[bold purple]Pull Request Details[/bold purple]

[dim]ID:[/dim] {pr.id}
[dim]Title:[/dim] {title}
[dim]Source Branch:[/dim] {pr.metadata.get('source_branch', 'Unknown')}
[dim]Target Branch:[/dim] {pr.metadata.get('target_branch', 'Unknown')}
[dim]Status:[/dim] {pr.metadata.get('status', pr.status)}
[dim]Author:[/dim] {author}
[dim]Reviewers:[/dim] {reviewers}
[dim]Labels:[/dim] {labels}
[dim]Created:[/dim] {pr.created_at.strftime('%Y-%m-%d %H:%M')}
[dim]Updated:[/dim] {pr.updated_at.strftime('%Y-%m-%d %H:%M')}"""

    if pr.metadata.get("closes"):
        info_text += f"\n[dim]Closes:[/dim] {pr.metadata.get('closes')}"

    # Show diff stats if available
    diff_stats = pr.metadata.get("diff_stats", {})
    if diff_stats:
        info_text += f"\n[dim]Changes:[/dim] +{diff_stats.get('insertions', 0)} -{diff_stats.get('deletions', 0)} lines"
        info_text += f", {diff_stats.get('files_changed', 0)} files"

    # Show check status
    checks = pr.metadata.get("checks", {})
    if checks:
        passing = sum(1 for status in checks.values() if status == "passed")
        total = len(checks)
        info_text += f"\n[dim]Checks:[/dim] {passing}/{total} passing"

    if detailed:
        info_text += f"\n\n[dim]Description:[/dim]\n{pr.description}"

    console.print(
        Panel.fit(info_text, title="Pull Request Information", border_style="purple")
    )

    # Show commits if requested
    if show_commits and pr.metadata.get("commits"):
        console.print("\n[bold]Commits:[/bold]")

        table = Table()
        table.add_column("SHA", style="cyan")
        table.add_column("Message", style="white")
        table.add_column("Author", style="yellow")

        for commit in pr.metadata.get("commits", []):
            table.add_row(
                commit.get("sha", "")[:8],
                (
                    commit.get("message", "")[:60] + "..."
                    if len(commit.get("message", "")) > 60
                    else commit.get("message", "")
                ),
                commit.get("author", ""),
            )

        console.print(table)


@app.command()
def update(
    pr_id: str = typer.Argument(..., help="PR ID to update"),
    title: Optional[str] = typer.Option(None, "--title", help="Update PR title"),
    description: Optional[str] = typer.Option(
        None, "--description", "-d", help="Update PR description"
    ),
    status: Optional[str] = typer.Option(
        None,
        "--status",
        "-s",
        help="Update PR status (draft, open, ready, merged, closed)",
    ),
    add_reviewer: Optional[List[str]] = typer.Option(
        None, "--add-reviewer", help="Add reviewers"
    ),
    remove_reviewer: Optional[List[str]] = typer.Option(
        None, "--remove-reviewer", help="Remove reviewers"
    ),
    add_label: Optional[List[str]] = typer.Option(
        None, "--add-label", help="Add labels"
    ),
    remove_label: Optional[List[str]] = typer.Option(
        None, "--remove-label", help="Remove labels"
    ),
) -> None:
    """Update an existing pull request."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    pr = task_manager.load_task(pr_id)

    if not pr or "pull-request" not in pr.tags:
        console.print(f"[red]Pull request '{pr_id}' not found[/red]")
        raise typer.Exit(1)

    # Prepare update data
    updates = {}
    metadata_updates = {}

    if title:
        updates["title"] = f"PR: {title}"
    if description:
        updates["description"] = description
    if status:
        valid_statuses = ["draft", "open", "ready", "merged", "closed"]
        if status not in valid_statuses:
            console.print(f"[red]Invalid status: {status}[/red]")
            console.print(f"Valid statuses: {', '.join(valid_statuses)}")
            raise typer.Exit(1)
        metadata_updates["status"] = status
        # Map to task status
        if status in ["merged", "closed"]:
            updates["status"] = "completed"
        elif status == "ready":
            updates["status"] = "in_progress"
        else:
            updates["status"] = "open"

    # Handle reviewer updates
    if add_reviewer or remove_reviewer:
        current_reviewers = set(pr.metadata.get("reviewers", []))
        if add_reviewer:
            current_reviewers.update(add_reviewer)
        if remove_reviewer:
            current_reviewers.difference_update(remove_reviewer)
        metadata_updates["reviewers"] = [*current_reviewers]

    # Handle label updates
    if add_label or remove_label:
        current_labels = set(pr.metadata.get("labels", []))
        if add_label:
            current_labels.update(add_label)
        if remove_label:
            current_labels.difference_update(remove_label)
        metadata_updates["labels"] = [*current_labels]

    if not updates and not metadata_updates:
        console.print("[yellow]No updates specified[/yellow]")
        return

    # Apply metadata updates
    if metadata_updates:
        pr.metadata.update(metadata_updates)
        updates["metadata"] = pr.metadata

    # Apply updates
    success = task_manager.update_task(pr_id, **updates)

    if success:
        # Build list of what was updated
        updated_fields = [k for k in updates]
        if metadata_updates:
            # Add metadata fields to the list, but avoid duplicating 'metadata'
            if "metadata" in updated_fields:
                updated_fields.remove("metadata")
            updated_fields.extend(k for k in metadata_updates)

        console.print(
            Panel.fit(
                f"""[bold green]Pull request updated successfully![/bold green]

[dim]ID:[/dim] {pr_id}
[dim]Updates applied:[/dim] {', '.join(updated_fields)}""",
                title="PR Updated",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to update pull request {pr_id}[/red]")
        raise typer.Exit(1)


@app.command()
def review(
    pr_id: str = typer.Argument(..., help="PR ID to review"),
    action: str = typer.Option(
        ..., "--action", "-a", help="Review action (approve, request_changes, comment)"
    ),
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="Review message"
    ),
    reviewer: Optional[str] = typer.Option(
        None, "--reviewer", "-r", help="Reviewer name"
    ),
) -> None:
    """Add a review to a pull request."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    pr = task_manager.load_task(pr_id)

    if not pr or "pull-request" not in pr.tags:
        console.print(f"[red]Pull request '{pr_id}' not found[/red]")
        raise typer.Exit(1)

    valid_actions = ["approve", "request_changes", "comment"]
    if action not in valid_actions:
        console.print(f"[red]Invalid action: {action}[/red]")
        console.print(f"Valid actions: {', '.join(valid_actions)}")
        raise typer.Exit(1)

    if not reviewer:
        from rich.prompt import Prompt

        reviewer = Prompt.ask("Reviewer name")

    if not message:
        from rich.prompt import Prompt

        message = Prompt.ask("Review message", default="")

    # Add review to PR metadata
    reviews = pr.metadata.get("reviews", [])
    reviews.append(
        {
            "reviewer": reviewer,
            "action": action,
            "message": message,
            "timestamp": pr.updated_at.isoformat(),
        }
    )
    pr.metadata["reviews"] = reviews

    # Update PR status based on review
    if action == "approve":
        pr.metadata["status"] = "approved"
        console.print(f"[green]PR {pr_id} approved by {reviewer}[/green]")
    elif action == "request_changes":
        pr.metadata["status"] = "changes_requested"
        console.print(
            f"[yellow]Changes requested for PR {pr_id} by {reviewer}[/yellow]"
        )
    else:
        console.print(f"[blue]Comment added to PR {pr_id} by {reviewer}[/blue]")

    # Save changes
    task_manager.update_task(pr_id, metadata=pr.metadata)

    if message:
        console.print(f"[dim]Message: {message}[/dim]")


@app.command()
def merge(
    pr_id: str = typer.Argument(..., help="PR ID to merge"),
    merge_type: str = typer.Option(
        "merge", "--type", "-t", help="Merge type (merge, squash, rebase)"
    ),
    delete_branch: bool = typer.Option(
        False, "--delete-branch", "-d", help="Delete source branch after merge"
    ),
) -> None:
    """Mark a pull request as merged."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    pr = task_manager.load_task(pr_id)

    if not pr or "pull-request" not in pr.tags:
        console.print(f"[red]Pull request '{pr_id}' not found[/red]")
        raise typer.Exit(1)

    valid_merge_types = ["merge", "squash", "rebase"]
    if merge_type not in valid_merge_types:
        console.print(f"[red]Invalid merge type: {merge_type}[/red]")
        console.print(f"Valid types: {', '.join(valid_merge_types)}")
        raise typer.Exit(1)

    # Update PR metadata
    pr.metadata.update(
        {
            "status": "merged",
            "merge_type": merge_type,
            "merged_at": pr.updated_at.isoformat(),
            "branch_deleted": delete_branch,
        }
    )

    # Close any related issues
    if pr.metadata.get("closes"):
        related_issue = task_manager.load_task(pr.metadata.get("closes"))
        if related_issue:
            task_manager.update_task(related_issue.id, status="completed")
            console.print(f"[green]Closed related issue: {related_issue.id}[/green]")

    # Update PR task
    success = task_manager.update_task(pr_id, status="completed", metadata=pr.metadata)

    if success:
        console.print(
            Panel.fit(
                f"""[bold green]Pull request merged successfully![/bold green]

[dim]ID:[/dim] {pr_id}
[dim]Merge type:[/dim] {merge_type}
[dim]Source branch:[/dim] {pr.metadata.get('source_branch')}
[dim]Target branch:[/dim] {pr.metadata.get('target_branch')}
[dim]Branch deleted:[/dim] {'Yes' if delete_branch else 'No'}""",
                title="PR Merged",
                border_style="green",
            )
        )
    else:
        console.print(f"[red]Failed to merge pull request {pr_id}[/red]")
        raise typer.Exit(1)


@app.command()
def close(
    pr_id: str = typer.Argument(..., help="PR ID to close"),
    reason: Optional[str] = typer.Option(
        None, "--reason", "-r", help="Reason for closing"
    ),
) -> None:
    """Close a pull request without merging."""
    project_path = Path.cwd()

    if not Project.exists(project_path):
        console.print("[red]No AI Trackdown project found[/red]")
        raise typer.Exit(1)

    task_manager = TaskManager(project_path)
    pr = task_manager.load_task(pr_id)

    if not pr or "pull-request" not in pr.tags:
        console.print(f"[red]Pull request '{pr_id}' not found[/red]")
        raise typer.Exit(1)

    # Update PR metadata
    pr.metadata.update(
        {
            "status": "closed",
            "closed_at": pr.updated_at.isoformat(),
            "close_reason": reason,
        }
    )

    success = task_manager.update_task(pr_id, status="cancelled", metadata=pr.metadata)

    if success:
        console.print(f"[yellow]Pull request {pr_id} closed[/yellow]")
        if reason:
            console.print(f"[dim]Reason: {reason}[/dim]")
    else:
        console.print(f"[red]Failed to close pull request {pr_id}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
