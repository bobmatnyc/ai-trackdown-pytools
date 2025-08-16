"""GitHub sync adapter implementation."""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from ai_trackdown_pytools.core.models import (
    IssueModel,
    IssueStatus,
    PRModel,
    PRStatus,
    TaskModel,
    TicketModel,
)
from ai_trackdown_pytools.utils.github import GitHubCLI, GitHubError

from .base import SyncAdapter, SyncConfig
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    ValidationError,
)


class GitHubAdapter(SyncAdapter):
    """Sync adapter for GitHub integration.

    WHY: This adapter provides backward compatibility with the existing GitHub
    sync implementation while following the new adapter pattern. It wraps the
    existing GitHubCLI to maintain consistency.

    DESIGN DECISION: Reusing GitHubCLI instead of reimplementing to maintain
    backward compatibility and avoid duplication. This adapter acts as a bridge
    between the old implementation and new adapter system.
    """

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "github"

    @property
    def supported_types(self) -> Set[str]:
        """Get supported ticket types."""
        return {"issue", "pr", "task"}  # GitHub issues can represent tasks too

    def __init__(self, config: SyncConfig):
        """Initialize GitHub adapter.

        Args:
            config: Sync configuration
        """
        super().__init__(config)
        self._gh_cli: Optional[GitHubCLI] = None
        self._repo: Optional[str] = None

    def validate_config(self) -> None:
        """Validate GitHub-specific configuration.

        Raises:
            ConfigurationError: If required config is missing
        """
        super().validate_config()

        # Check for repository
        repo = self.config.auth_config.get("repository")
        if not repo:
            raise ConfigurationError(
                "GitHub repository not specified",
                platform=self.platform_name,
                missing_fields=["repository"],
            )

        # Validate repository format
        if "/" not in repo or len(repo.split("/")) != 2:
            raise ConfigurationError(
                f"Invalid repository format: {repo}. Expected: owner/repo",
                platform=self.platform_name,
            )

        self._repo = repo

    async def authenticate(self) -> None:
        """Authenticate with GitHub.

        WHY: Uses the existing GitHubCLI which handles authentication via
        the GitHub CLI tool. This maintains compatibility with existing setup.

        Raises:
            AuthenticationError: If authentication fails
        """
        self.validate_config()

        try:
            self._gh_cli = GitHubCLI(self._repo)
            self._authenticated = True
        except GitHubError as e:
            raise AuthenticationError(
                str(e), platform=self.platform_name, auth_method="github_cli"
            )

    async def test_connection(self) -> bool:
        """Test connection to GitHub.

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
        """
        if not self._authenticated or not self._gh_cli:
            await self.authenticate()

        try:
            # Try to list issues with limit 1 as a connection test
            await self._run_async(self._gh_cli.list_issues, limit=1)
            return True
        except GitHubError as e:
            raise ConnectionError(
                f"Failed to connect to GitHub: {e}",
                platform=self.platform_name,
                endpoint=f"https://api.github.com/repos/{self._repo}",
            )

    async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
        """Pull items from GitHub.

        Args:
            since: Only pull items updated after this timestamp

        Returns:
            List of items in internal format
        """
        if not self._authenticated or not self._gh_cli:
            await self.authenticate()

        items = []

        # Pull issues
        if self.filter_item_type("issue"):
            github_issues = await self._run_async(
                self._gh_cli.list_issues,
                state="all",  # Get all issues, we'll filter by date
                limit=1000,  # GitHub's max
            )

            for gh_issue in github_issues:
                # Filter by update time if needed
                if since:
                    updated_at = datetime.fromisoformat(
                        gh_issue["updatedAt"].replace("Z", "+00:00")
                    )
                    if updated_at <= since:
                        continue

                # Convert to internal model
                issue = self._github_issue_to_model(gh_issue)
                items.append(issue)

        # Pull PRs
        if self.filter_item_type("pr"):
            github_prs = await self._run_async(
                self._gh_cli.list_prs, state="all", limit=1000
            )

            for gh_pr in github_prs:
                # Filter by update time if needed
                if since:
                    updated_at = datetime.fromisoformat(
                        gh_pr["updatedAt"].replace("Z", "+00:00")
                    )
                    if updated_at <= since:
                        continue

                # Convert to internal model
                pr = self._github_pr_to_model(gh_pr)
                items.append(pr)

        return items

    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        """Push item to GitHub.

        Args:
            item: Item to push

        Returns:
            Mapping information
        """
        if not self._authenticated or not self._gh_cli:
            await self.authenticate()

        if isinstance(item, IssueModel):
            # Create GitHub issue
            labels = self.map_labels(item.tags, to_external=True)

            result = await self._run_async(
                self._gh_cli.create_issue,
                title=item.title,
                body=item.description,
                labels=labels,
                assignees=item.assignees if self.config.sync_assignees else None,
            )

            return {
                "remote_id": str(result["id"]),
                "remote_number": result["number"],
                "remote_url": result["url"],
            }

        elif isinstance(item, PRModel):
            # Create GitHub PR
            labels = self.map_labels(item.tags, to_external=True)

            result = await self._run_async(
                self._gh_cli.create_pr,
                title=item.title,
                body=item.description,
                base=item.target_branch,
                head=item.source_branch,
                draft=item.status == PRStatus.DRAFT,
                labels=labels,
                assignees=item.assignees if self.config.sync_assignees else None,
            )

            return {
                "remote_id": str(result["id"]),
                "remote_number": result["number"],
                "remote_url": result["url"],
            }

        else:
            raise ValidationError(
                f"Unsupported item type for GitHub: {type(item).__name__}",
                platform=self.platform_name,
            )

    async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
        """Update item on GitHub.

        Args:
            item: Updated item
            remote_id: GitHub issue/PR number

        Returns:
            Updated mapping information
        """
        if not self._authenticated or not self._gh_cli:
            await self.authenticate()

        # GitHub uses issue/PR numbers for updates, not IDs
        # Extract number from metadata if available
        number = None
        if hasattr(item, "metadata") and item.metadata:
            number = item.metadata.get("github_number")

        if not number:
            # Try to parse from remote_id if it's actually a number
            try:
                number = int(remote_id)
            except ValueError:
                raise ValidationError(
                    f"Invalid GitHub issue/PR identifier: {remote_id}",
                    platform=self.platform_name,
                )

        if isinstance(item, (IssueModel, TaskModel)):
            # Update as GitHub issue
            labels = self.map_labels(item.tags, to_external=True)
            status = self._map_issue_status(item.status)

            result = await self._run_async(
                self._gh_cli.update_issue,
                number=number,
                title=item.title,
                body=item.description,
                state=status,
                labels=labels if self.config.sync_tags else None,
                assignees=item.assignees if self.config.sync_assignees else None,
            )

            return {
                "remote_id": str(result["id"]),
                "remote_number": result["number"],
                "remote_url": result["url"],
            }

        else:
            raise ValidationError(
                f"Cannot update item type {type(item).__name__} on GitHub",
                platform=self.platform_name,
            )

    async def delete_item(self, remote_id: str) -> None:
        """Delete item from GitHub.

        Note: GitHub doesn't support deleting issues/PRs, so we close them instead.

        Args:
            remote_id: GitHub issue/PR number
        """
        if not self._authenticated or not self._gh_cli:
            await self.authenticate()

        try:
            number = int(remote_id)
        except ValueError:
            raise ValidationError(
                f"Invalid GitHub issue/PR number: {remote_id}",
                platform=self.platform_name,
            )

        # Close the issue/PR instead of deleting
        await self._run_async(self._gh_cli.close_issue, number=number)

    async def get_item(self, remote_id: str) -> Optional[TicketModel]:
        """Get single item from GitHub.

        Args:
            remote_id: GitHub issue/PR number

        Returns:
            Item in internal format or None
        """
        if not self._authenticated or not self._gh_cli:
            await self.authenticate()

        try:
            number = int(remote_id)
        except ValueError:
            return None

        try:
            # Try to get as issue first
            gh_issue = await self._run_async(self._gh_cli.get_issue, number=number)

            # Check if it's actually a PR
            if "pull_request" in gh_issue:
                # Get full PR data
                prs = await self._run_async(self._gh_cli.list_prs, state="all", limit=1)
                for pr in prs:
                    if pr["number"] == number:
                        return self._github_pr_to_model(pr)
            else:
                return self._github_issue_to_model(gh_issue)

        except GitHubError:
            return None

    # Helper methods

    async def _run_async(self, func, *args, **kwargs):
        """Run a synchronous function in an async context.

        WHY: GitHubCLI is synchronous but our adapter interface is async.
        This bridge allows us to use the existing implementation.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    def _github_issue_to_model(self, gh_issue: Dict[str, Any]) -> IssueModel:
        """Convert GitHub issue to internal model."""
        # Map status
        status = (
            IssueStatus.COMPLETED if gh_issue["state"] == "closed" else IssueStatus.OPEN
        )

        # Extract labels
        labels = [label["name"] for label in gh_issue.get("labels", [])]
        tags = self.map_labels(labels, to_external=False)

        # Ensure "issue" tag is present
        if "issue" not in tags:
            tags.append("issue")

        # Extract assignees
        assignees = [a["login"] for a in gh_issue.get("assignees", [])]

        # Create issue model
        return IssueModel(
            id=f"ISS-{gh_issue['number']}",  # Use number as ID for consistency
            title=gh_issue["title"],
            description=gh_issue.get("body", ""),
            status=status,
            tags=tags,
            assignees=assignees,
            created_at=datetime.fromisoformat(
                gh_issue["createdAt"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                gh_issue["updatedAt"].replace("Z", "+00:00")
            ),
            metadata={
                "github_id": gh_issue["id"],
                "github_number": gh_issue["number"],
                "github_url": gh_issue["url"],
                "platform": "github",
            },
        )

    def _github_pr_to_model(self, gh_pr: Dict[str, Any]) -> PRModel:
        """Convert GitHub PR to internal model."""
        # Map status
        if gh_pr["state"] == "closed":
            status = PRStatus.CLOSED
        elif gh_pr["state"] == "merged":
            status = PRStatus.MERGED
        elif gh_pr.get("isDraft", False):
            status = PRStatus.DRAFT
        else:
            status = PRStatus.READY_FOR_REVIEW

        # Extract labels
        labels = [label["name"] for label in gh_pr.get("labels", [])]
        tags = self.map_labels(labels, to_external=False)

        # Ensure "pr" tag is present
        if "pr" not in tags:
            tags.append("pr")

        # Extract assignees
        assignees = [a["login"] for a in gh_pr.get("assignees", [])]

        # Create PR model
        return PRModel(
            id=f"PR-{gh_pr['number']}",  # Use number as ID for consistency
            title=gh_pr["title"],
            description=gh_pr.get("body", ""),
            status=status,
            source_branch=gh_pr.get("headRefName", ""),
            target_branch=gh_pr.get("baseRefName", "main"),
            tags=tags,
            assignees=assignees,
            created_at=datetime.fromisoformat(
                gh_pr["createdAt"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                gh_pr["updatedAt"].replace("Z", "+00:00")
            ),
            metadata={
                "github_id": gh_pr["id"],
                "github_number": gh_pr["number"],
                "github_url": gh_pr["url"],
                "platform": "github",
            },
        )

    def _map_issue_status(self, status: IssueStatus) -> str:
        """Map internal issue status to GitHub state."""
        if status in [IssueStatus.COMPLETED, IssueStatus.CANCELLED]:
            return "closed"
        return "open"


# Register the adapter
from .registry import register_adapter

register_adapter("github", GitHubAdapter)
