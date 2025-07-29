"""GitHub integration utilities using GitHub CLI (gh)."""

import json
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class GitHubError(Exception):
    """Exception raised for GitHub-related errors."""

    pass


class GitHubCLI:
    """GitHub CLI wrapper for issue and PR management."""

    def __init__(self, repo: str):
        """Initialize GitHub CLI wrapper.

        Args:
            repo: Repository in format "owner/repo"
        """
        self.repo = repo

        # Verify gh is available
        if not self._check_gh_available():
            raise GitHubError("GitHub CLI (gh) is not installed or not in PATH")

        # Verify authentication
        if not self._check_gh_auth():
            raise GitHubError("GitHub CLI is not authenticated. Run 'gh auth login'")

    def _check_gh_available(self) -> bool:
        """Check if gh command is available."""
        try:
            subprocess.run(["gh", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_gh_auth(self) -> bool:
        """Check if gh is authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True
            )
            return result.returncode == 0
        except subprocess.CalledProcessError:
            return False

    def _run_gh_command(self, args: List[str]) -> str:
        """Run a gh command and return output."""
        try:
            result = subprocess.run(
                ["gh"] + args, capture_output=True, text=True, check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise GitHubError(f"GitHub CLI error: {e.stderr}") from e

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a GitHub issue.

        Args:
            title: Issue title
            body: Issue body/description
            labels: List of labels to apply
            assignees: List of assignees (GitHub usernames)

        Returns:
            Dict containing issue details (number, url, etc.)
        """
        args = [
            "issue",
            "create",
            "--repo",
            self.repo,
            "--title",
            title,
            "--body",
            body,
        ]

        if labels:
            args.extend(["--label", ",".join(labels)])

        if assignees:
            args.extend(["--assignee", ",".join(assignees)])

        # Add JSON output
        args.append("--json")
        args.append("number,title,url,state,createdAt,id")

        output = self._run_gh_command(args)
        return json.loads(output)

    def list_issues(
        self, state: str = "open", labels: Optional[List[str]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List GitHub issues.

        Args:
            state: Issue state (open, closed, all)
            labels: Filter by labels
            limit: Maximum number of issues to return

        Returns:
            List of issue dictionaries
        """
        args = [
            "issue",
            "list",
            "--repo",
            self.repo,
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            "number,title,body,state,labels,assignees,createdAt,updatedAt,id,url",
        ]

        if labels:
            args.extend(["--label", ",".join(labels)])

        output = self._run_gh_command(args)
        return json.loads(output)

    def get_issue(self, number: int) -> Dict[str, Any]:
        """Get a specific issue by number.

        Args:
            number: Issue number

        Returns:
            Issue dictionary
        """
        args = [
            "issue",
            "view",
            str(number),
            "--repo",
            self.repo,
            "--json",
            "number,title,body,state,labels,assignees,createdAt,updatedAt,id,url",
        ]

        output = self._run_gh_command(args)
        return json.loads(output)

    def update_issue(
        self,
        number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Update a GitHub issue.

        Args:
            number: Issue number
            title: New title (optional)
            body: New body (optional)
            state: New state (open/closed) (optional)
            labels: New labels (optional)
            assignees: New assignees (optional)

        Returns:
            Updated issue dictionary
        """
        args = ["issue", "edit", str(number), "--repo", self.repo]

        if title:
            args.extend(["--title", title])

        if body:
            args.extend(["--body", body])

        if state:
            args.extend(["--state", state])

        if labels is not None:
            args.extend(["--add-label", ",".join(labels)])

        if assignees is not None:
            args.extend(["--add-assignee", ",".join(assignees)])

        self._run_gh_command(args)

        # Get updated issue
        return self.get_issue(number)

    def close_issue(self, number: int) -> Dict[str, Any]:
        """Close a GitHub issue.

        Args:
            number: Issue number

        Returns:
            Updated issue dictionary
        """
        return self.update_issue(number, state="closed")

    def create_pr(
        self,
        title: str,
        body: str,
        base: str = "main",
        head: Optional[str] = None,
        draft: bool = False,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a GitHub pull request.

        Args:
            title: PR title
            body: PR body/description
            base: Base branch (default: main)
            head: Head branch (default: current branch)
            draft: Create as draft PR
            labels: List of labels to apply
            assignees: List of assignees

        Returns:
            Dict containing PR details
        """
        args = [
            "pr",
            "create",
            "--repo",
            self.repo,
            "--title",
            title,
            "--body",
            body,
            "--base",
            base,
        ]

        if head:
            args.extend(["--head", head])

        if draft:
            args.append("--draft")

        if labels:
            args.extend(["--label", ",".join(labels)])

        if assignees:
            args.extend(["--assignee", ",".join(assignees)])

        # Add JSON output
        args.append("--json")
        args.append("number,title,url,state,createdAt,id")

        output = self._run_gh_command(args)
        return json.loads(output)

    def list_prs(
        self, state: str = "open", labels: Optional[List[str]] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List GitHub pull requests.

        Args:
            state: PR state (open, closed, merged, all)
            labels: Filter by labels
            limit: Maximum number of PRs to return

        Returns:
            List of PR dictionaries
        """
        args = [
            "pr",
            "list",
            "--repo",
            self.repo,
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            "number,title,body,state,labels,assignees,createdAt,updatedAt,id,url,headRefName,baseRefName",
        ]

        if labels:
            args.extend(["--label", ",".join(labels)])

        output = self._run_gh_command(args)
        return json.loads(output)

    def sync_issue_to_github(
        self, task: Any, dry_run: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Sync a local task to GitHub as an issue.

        Args:
            task: Task object with id, title, description, etc.
            dry_run: If True, don't actually create the issue

        Returns:
            Created issue dictionary or None if dry run
        """
        if dry_run:
            console.print(f"[yellow]DRY RUN:[/yellow] Would create issue: {task.title}")
            return None

        # Prepare labels - filter out 'issue' tag
        labels = [tag for tag in task.tags if tag != "issue"]

        # Create issue
        issue = self.create_issue(
            title=task.title,
            body=task.description or "No description provided.",
            labels=labels,
            assignees=task.assignees if task.assignees else None,
        )

        return issue

    def sync_pr_to_github(
        self, task: Any, dry_run: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Sync a local task to GitHub as a pull request.

        Args:
            task: Task object with id, title, description, etc.
            dry_run: If True, don't actually create the PR

        Returns:
            Created PR dictionary or None if dry run
        """
        if dry_run:
            console.print(f"[yellow]DRY RUN:[/yellow] Would create PR: {task.title}")
            return None

        # For PRs, we need to determine branches
        # This is a simplified version - in reality you'd want more logic here
        base = task.metadata.get("base_branch", "main")
        head = task.metadata.get("head_branch")

        if not head:
            raise GitHubError(
                f"Task {task.id} is marked as PR but has no head_branch in metadata"
            )

        # Prepare labels - filter out 'pull-request' tag
        labels = [tag for tag in task.tags if tag != "pull-request"]

        # Create PR
        pr = self.create_pr(
            title=task.title,
            body=task.description or "No description provided.",
            base=base,
            head=head,
            labels=labels,
            assignees=task.assignees if task.assignees else None,
        )

        return pr

    def pull_issues_from_github(
        self, task_manager: Any, dry_run: bool = False
    ) -> Tuple[int, int]:
        """Pull issues from GitHub and create/update local tasks.

        Args:
            task_manager: TaskManager instance
            dry_run: If True, don't actually create/update tasks

        Returns:
            Tuple of (created_count, updated_count)
        """
        created = 0
        updated = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching issues from GitHub...", total=None)

            # Get all open issues
            issues = self.list_issues(state="open")

            progress.update(task, description=f"Processing {len(issues)} issues...")

            for issue in issues:
                # Check if we already have this issue locally
                existing_tasks = task_manager.list_tasks()
                existing_task = None

                for task_obj in existing_tasks:
                    if task_obj.metadata.get("github_id") == issue["id"]:
                        existing_task = task_obj
                        break

                if existing_task:
                    # Update existing task
                    if not dry_run:
                        task_manager.update_task(
                            existing_task.id,
                            title=issue["title"],
                            description=issue.get("body", ""),
                            status="open" if issue["state"] == "open" else "closed",
                            tags=["issue"]
                            + [label["name"] for label in issue.get("labels", [])],
                            assignees=[a["login"] for a in issue.get("assignees", [])],
                            metadata={
                                **existing_task.metadata,
                                "github_number": issue["number"],
                                "github_url": issue["url"],
                                "github_updated": issue["updatedAt"],
                            },
                        )
                    updated += 1
                else:
                    # Create new task
                    if not dry_run:
                        task_manager.create_task(
                            title=issue["title"],
                            description=issue.get("body", ""),
                            status="open" if issue["state"] == "open" else "closed",
                            tags=["issue"]
                            + [label["name"] for label in issue.get("labels", [])],
                            assignees=[a["login"] for a in issue.get("assignees", [])],
                            metadata={
                                "github_id": issue["id"],
                                "github_number": issue["number"],
                                "github_url": issue["url"],
                                "github_created": issue["createdAt"],
                                "github_updated": issue["updatedAt"],
                                "imported_from": "github",
                            },
                        )
                    created += 1

        return created, updated
