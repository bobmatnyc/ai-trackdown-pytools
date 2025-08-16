"""JIRA sync adapter implementation."""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from jira import JIRA, JIRAError

from ai_trackdown_pytools.core.models import (
    BugModel,
    EpicModel,
    IssueModel,
    IssueStatus,
    Priority,
    TaskModel,
    TaskStatus,
    TicketModel,
)

from .base import SyncAdapter, SyncConfig
from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConnectionError,
    RateLimitError,
    SyncError,
    ValidationError,
)


class JiraAdapter(SyncAdapter):
    """Sync adapter for JIRA integration.

    WHY: JIRA is one of the most widely used issue tracking systems in enterprise
    environments. This adapter enables teams to use AI Trackdown while maintaining
    their existing JIRA workflows and integrations.

    DESIGN DECISION: Using the official jira-python library provides robust API
    coverage and handles many edge cases. We wrap synchronous calls in async
    methods to match our adapter interface.
    """

    # Status mapping between internal and JIRA
    STATUS_TO_JIRA = {
        TaskStatus.OPEN: "To Do",
        TaskStatus.IN_PROGRESS: "In Progress",
        TaskStatus.COMPLETED: "Done",
        TaskStatus.CANCELLED: "Won't Do",
        TaskStatus.BLOCKED: "Blocked",
    }

    STATUS_FROM_JIRA = {
        "to do": TaskStatus.OPEN,
        "todo": TaskStatus.OPEN,
        "backlog": TaskStatus.OPEN,
        "open": TaskStatus.OPEN,
        "in progress": TaskStatus.IN_PROGRESS,
        "in development": TaskStatus.IN_PROGRESS,
        "in review": TaskStatus.IN_PROGRESS,
        "done": TaskStatus.COMPLETED,
        "closed": TaskStatus.COMPLETED,
        "resolved": TaskStatus.COMPLETED,
        "won't do": TaskStatus.CANCELLED,
        "won't fix": TaskStatus.CANCELLED,
        "cancelled": TaskStatus.CANCELLED,
        "blocked": TaskStatus.BLOCKED,
        "on hold": TaskStatus.BLOCKED,
    }

    # Priority mapping (JIRA uses names)
    PRIORITY_TO_JIRA = {
        Priority.CRITICAL: "Highest",
        Priority.HIGH: "High",
        Priority.MEDIUM: "Medium",
        Priority.LOW: "Low",
    }

    PRIORITY_FROM_JIRA = {
        "highest": Priority.CRITICAL,
        "critical": Priority.CRITICAL,
        "blocker": Priority.CRITICAL,
        "high": Priority.HIGH,
        "major": Priority.HIGH,
        "medium": Priority.MEDIUM,
        "normal": Priority.MEDIUM,
        "low": Priority.LOW,
        "minor": Priority.LOW,
        "lowest": Priority.LOW,
        "trivial": Priority.LOW,
    }

    # Issue type mapping
    ISSUE_TYPE_MAP = {
        "task": TaskModel,
        "story": TaskModel,
        "issue": IssueModel,
        "bug": BugModel,
        "epic": EpicModel,
    }

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "jira"

    @property
    def supported_types(self) -> Set[str]:
        """Get supported ticket types."""
        return {"task", "issue", "bug", "epic"}

    def __init__(self, config: SyncConfig):
        """Initialize JIRA adapter.

        Args:
            config: Sync configuration
        """
        super().__init__(config)
        self._jira_client: Optional[JIRA] = None
        self._server: Optional[str] = None
        self._project_key: Optional[str] = None
        self._custom_fields: Dict[str, str] = {}
        self._field_map: Dict[str, str] = {}

    def validate_config(self) -> None:
        """Validate JIRA-specific configuration.

        Raises:
            ConfigurationError: If required config is missing
        """
        super().validate_config()

        # Check for server URL
        server = self.config.auth_config.get("server") or os.getenv("JIRA_SERVER")
        if not server:
            raise ConfigurationError(
                "JIRA server URL not provided",
                platform=self.platform_name,
                missing_fields=["server"],
            )

        # Validate server URL format
        if not server.startswith(("http://", "https://")):
            raise ConfigurationError(
                f"Invalid server URL format: {server}. Must start with http:// or https://",
                platform=self.platform_name,
            )

        # Check for authentication
        email = self.config.auth_config.get("email") or os.getenv("JIRA_EMAIL")
        api_token = self.config.auth_config.get("api_token") or os.getenv(
            "JIRA_API_TOKEN"
        )

        if not email or not api_token:
            raise ConfigurationError(
                "JIRA email and API token required for authentication",
                platform=self.platform_name,
                missing_fields=["email", "api_token"],
            )

        # Check for project key
        project_key = self.config.auth_config.get("project_key")
        if not project_key:
            raise ConfigurationError(
                "JIRA project key not specified",
                platform=self.platform_name,
                missing_fields=["project_key"],
            )

        self._server = server
        self._project_key = project_key

    async def authenticate(self) -> None:
        """Authenticate with JIRA.

        WHY: Uses basic authentication with email + API token, which is the
        recommended approach for JIRA Cloud. The jira-python library handles
        session management and cookie handling automatically.

        Raises:
            AuthenticationError: If authentication fails
        """
        self.validate_config()

        email = self.config.auth_config.get("email") or os.getenv("JIRA_EMAIL")
        api_token = self.config.auth_config.get("api_token") or os.getenv(
            "JIRA_API_TOKEN"
        )

        try:
            # Create JIRA client with basic auth
            self._jira_client = JIRA(
                server=self._server,
                basic_auth=(email, api_token),
                options={
                    "verify": True,  # Verify SSL certificates
                    "agile_rest_path": "agile",  # For Agile APIs
                    "headers": {
                        "Accept": "application/json",
                    },
                },
            )

            # Test authentication by getting current user
            await self._run_async(self._jira_client.current_user)
            self._authenticated = True

            # Discover custom fields
            await self._discover_custom_fields()

        except JIRAError as e:
            if e.status_code == 401:
                raise AuthenticationError(
                    "Invalid JIRA credentials",
                    platform=self.platform_name,
                    auth_method="basic_auth",
                )
            else:
                raise AuthenticationError(
                    f"JIRA authentication failed: {e.text}",
                    platform=self.platform_name,
                    auth_method="basic_auth",
                )
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to JIRA: {e}",
                platform=self.platform_name,
                endpoint=self._server,
            )

    async def test_connection(self) -> bool:
        """Test connection to JIRA.

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
        """
        if not self._authenticated or not self._jira_client:
            await self.authenticate()

        try:
            # Test by getting project info
            project = await self._run_async(
                self._jira_client.project, self._project_key
            )
            return project is not None
        except JIRAError as e:
            raise ConnectionError(
                f"Failed to access JIRA project {self._project_key}: {e.text}",
                platform=self.platform_name,
                endpoint=f"{self._server}/rest/api/3/project/{self._project_key}",
            )

    async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
        """Pull items from JIRA.

        WHY: Uses JQL (JIRA Query Language) for flexible filtering. We pull all
        issue types and convert them to appropriate internal models based on
        their JIRA issue type.

        Args:
            since: Only pull items updated after this timestamp

        Returns:
            List of items in internal format
        """
        if not self._authenticated or not self._jira_client:
            await self.authenticate()

        items = []

        # Build JQL query
        jql_parts = [f'project = "{self._project_key}"']

        # Add date filter if provided
        if since:
            # JIRA uses a specific date format
            date_str = since.strftime("%Y-%m-%d %H:%M")
            jql_parts.append(f'updated >= "{date_str}"')

        # Add custom JQL from config if provided
        custom_jql = self.config.auth_config.get("jql_filter")
        if custom_jql:
            jql_parts.append(f"({custom_jql})")

        jql = " AND ".join(jql_parts)

        # Search for issues with pagination
        start_at = 0
        max_results = 50  # JIRA's recommended batch size

        while True:
            try:
                # Search issues
                issues = await self._run_async(
                    self._jira_client.search_issues,
                    jql,
                    startAt=start_at,
                    maxResults=max_results,
                    expand="changelog,renderedFields",
                )

                if not issues:
                    break

                # Convert each issue to internal model
                for jira_issue in issues:
                    try:
                        model = self._jira_issue_to_model(jira_issue)
                        if model and self.filter_item_type(model.type):
                            items.append(model)
                    except Exception as e:
                        # Log error but continue processing
                        print(f"Error converting JIRA issue {jira_issue.key}: {e}")

                # Check if we've retrieved all issues
                if len(issues) < max_results:
                    break

                start_at += max_results

            except JIRAError as e:
                if e.status_code == 429:  # Rate limit
                    retry_after = int(e.response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        "JIRA rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                else:
                    raise SyncError(
                        f"Failed to search JIRA issues: {e.text}",
                        platform=self.platform_name,
                    )

        return items

    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        """Push item to JIRA.

        Args:
            item: Item to push

        Returns:
            Mapping information
        """
        if not self._authenticated or not self._jira_client:
            await self.authenticate()

        # Determine issue type
        issue_type = self._get_issue_type_for_model(item)

        # Build issue fields
        fields = {
            "project": {"key": self._project_key},
            "summary": item.title,
            "description": item.description or "",
            "issuetype": {"name": issue_type},
        }

        # Add priority if mapped
        if hasattr(item, "priority") and item.priority:
            jira_priority = self.PRIORITY_TO_JIRA.get(item.priority)
            if jira_priority:
                fields["priority"] = {"name": jira_priority}

        # Add labels
        if self.config.sync_tags and item.tags:
            fields["labels"] = self.map_labels(item.tags, to_external=True)

        # Add assignee if enabled and available
        if self.config.sync_assignees and item.assignees:
            # JIRA only supports single assignee
            assignee = item.assignees[0] if item.assignees else None
            if assignee:
                try:
                    # Try to find user by email or username
                    users = await self._run_async(
                        self._jira_client.search_users, assignee
                    )
                    if users:
                        fields["assignee"] = {"accountId": users[0].accountId}
                except JIRAError:
                    # User not found, skip assignee
                    pass

        # Add due date if available
        if hasattr(item, "due_date") and item.due_date:
            fields["duedate"] = item.due_date.strftime("%Y-%m-%d")

        # Add time estimate if available
        if hasattr(item, "estimated_hours") and item.estimated_hours:
            # Convert hours to seconds for JIRA
            fields["timeoriginalestimate"] = int(item.estimated_hours * 3600)

        # Add custom fields from metadata
        if item.metadata and "jira_custom_fields" in item.metadata:
            for field_name, value in item.metadata["jira_custom_fields"].items():
                if field_name in self._custom_fields:
                    fields[self._custom_fields[field_name]] = value

        try:
            # Create the issue
            jira_issue = await self._run_async(
                self._jira_client.create_issue, fields=fields
            )

            # Update status if needed
            await self._update_issue_status(jira_issue, item)

            return {
                "remote_id": jira_issue.id,
                "remote_key": jira_issue.key,
                "remote_url": f"{self._server}/browse/{jira_issue.key}",
            }

        except JIRAError as e:
            raise ValidationError(
                f"Failed to create JIRA issue: {e.text}",
                platform=self.platform_name,
                field_errors={"fields": e.response.json() if e.response else {}},
            )

    async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
        """Update item on JIRA.

        Args:
            item: Updated item
            remote_id: JIRA issue key or ID

        Returns:
            Updated mapping information
        """
        if not self._authenticated or not self._jira_client:
            await self.authenticate()

        try:
            # Get the issue
            jira_issue = await self._run_async(self._jira_client.issue, remote_id)

            # Build update fields
            fields = {
                "summary": item.title,
                "description": item.description or "",
            }

            # Update priority
            if hasattr(item, "priority") and item.priority:
                jira_priority = self.PRIORITY_TO_JIRA.get(item.priority)
                if jira_priority:
                    fields["priority"] = {"name": jira_priority}

            # Update labels
            if self.config.sync_tags:
                fields["labels"] = self.map_labels(item.tags, to_external=True)

            # Update assignee
            if self.config.sync_assignees:
                if item.assignees:
                    assignee = item.assignees[0]
                    try:
                        users = await self._run_async(
                            self._jira_client.search_users, assignee
                        )
                        if users:
                            fields["assignee"] = {"accountId": users[0].accountId}
                    except JIRAError:
                        pass
                else:
                    # Unassign
                    fields["assignee"] = None

            # Update due date
            if hasattr(item, "due_date"):
                fields["duedate"] = (
                    item.due_date.strftime("%Y-%m-%d") if item.due_date else None
                )

            # Update time estimate
            if hasattr(item, "estimated_hours") and item.estimated_hours is not None:
                fields["timeoriginalestimate"] = int(item.estimated_hours * 3600)

            # Update the issue
            await self._run_async(jira_issue.update, fields=fields)

            # Update status if needed
            await self._update_issue_status(jira_issue, item)

            return {
                "remote_id": jira_issue.id,
                "remote_key": jira_issue.key,
                "remote_url": f"{self._server}/browse/{jira_issue.key}",
            }

        except JIRAError as e:
            if e.status_code == 404:
                raise ValidationError(
                    f"JIRA issue not found: {remote_id}", platform=self.platform_name
                )
            else:
                raise ValidationError(
                    f"Failed to update JIRA issue: {e.text}",
                    platform=self.platform_name,
                    field_errors={"fields": e.response.json() if e.response else {}},
                )

    async def delete_item(self, remote_id: str) -> None:
        """Delete item from JIRA.

        Note: JIRA doesn't always allow deletion. We may need to transition
        to a closed/cancelled state instead.

        Args:
            remote_id: JIRA issue key or ID
        """
        if not self._authenticated or not self._jira_client:
            await self.authenticate()

        try:
            # Try to delete the issue
            await self._run_async(self._jira_client.issue(remote_id).delete)
        except JIRAError as e:
            if e.status_code == 403:
                # No permission to delete, try to close/cancel instead
                try:
                    jira_issue = await self._run_async(
                        self._jira_client.issue, remote_id
                    )
                    # Transition to cancelled/closed state
                    transitions = await self._run_async(
                        self._jira_client.transitions, jira_issue
                    )

                    # Look for cancel/close transition
                    for trans in transitions:
                        if trans["name"].lower() in [
                            "cancel",
                            "close",
                            "won't do",
                            "won't fix",
                        ]:
                            await self._run_async(
                                self._jira_client.transition_issue,
                                jira_issue,
                                trans["id"],
                            )
                            return

                except JIRAError:
                    pass

                raise ValidationError(
                    f"Cannot delete JIRA issue {remote_id}. No permission or suitable transition found.",
                    platform=self.platform_name,
                )
            elif e.status_code == 404:
                # Already deleted or doesn't exist
                return
            else:
                raise SyncError(
                    f"Failed to delete JIRA issue: {e.text}",
                    platform=self.platform_name,
                )

    async def get_item(self, remote_id: str) -> Optional[TicketModel]:
        """Get single item from JIRA.

        Args:
            remote_id: JIRA issue key or ID

        Returns:
            Item in internal format or None
        """
        if not self._authenticated or not self._jira_client:
            await self.authenticate()

        try:
            jira_issue = await self._run_async(
                self._jira_client.issue, remote_id, expand="changelog,renderedFields"
            )
            return self._jira_issue_to_model(jira_issue)
        except JIRAError as e:
            if e.status_code == 404:
                return None
            else:
                raise SyncError(
                    f"Failed to get JIRA issue: {e.text}", platform=self.platform_name
                )

    # Helper methods

    async def _run_async(self, func, *args, **kwargs):
        """Run a synchronous function in an async context.

        WHY: jira-python is synchronous but our adapter interface is async.
        This bridge allows us to use the official library while maintaining
        async compatibility.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, func, *args, **kwargs)

    async def _discover_custom_fields(self) -> None:
        """Discover custom field IDs for the project.

        WHY: JIRA custom fields have dynamic IDs (like customfield_10001).
        We need to map field names to IDs for proper field handling.
        """
        try:
            fields = await self._run_async(self._jira_client.fields)

            for field in fields:
                if field["custom"]:
                    # Store mapping of name to ID
                    self._custom_fields[field["name"]] = field["id"]
                    self._field_map[field["id"]] = field["name"]

        except JIRAError:
            # Non-critical error, continue without custom fields
            pass

    def _jira_issue_to_model(self, jira_issue: Any) -> Optional[TicketModel]:
        """Convert JIRA issue to internal model.

        WHY: Maps JIRA's complex field structure to our simplified model.
        Handles different issue types and maps them to appropriate model classes.
        """
        fields = jira_issue.fields

        # Determine model type based on issue type
        issue_type_name = fields.issuetype.name.lower()
        model_class = self.ISSUE_TYPE_MAP.get(issue_type_name, TaskModel)

        # Map status
        status_name = fields.status.name.lower()
        if model_class == TaskModel:
            status = self.STATUS_FROM_JIRA.get(status_name, TaskStatus.OPEN)
        elif model_class == IssueModel:
            status = (
                IssueStatus.OPEN
                if status_name not in ["done", "closed", "resolved"]
                else IssueStatus.COMPLETED
            )
        else:
            status = self.STATUS_FROM_JIRA.get(status_name, TaskStatus.OPEN)

        # Map priority
        priority = Priority.MEDIUM
        if fields.priority:
            priority_name = fields.priority.name.lower()
            priority = self.PRIORITY_FROM_JIRA.get(priority_name, Priority.MEDIUM)

        # Extract labels/tags
        labels = list(fields.labels) if fields.labels else []
        tags = self.map_labels(labels, to_external=False)

        # Ensure type tag is present
        type_tag = issue_type_name
        if type_tag not in tags:
            tags.append(type_tag)

        # Extract assignees
        assignees = []
        if fields.assignee:
            # Try email first, fall back to displayName
            assignee = (
                getattr(fields.assignee, "emailAddress", None)
                or fields.assignee.displayName
            )
            assignees.append(assignee)

        # Convert timestamps
        created_at = datetime.fromisoformat(fields.created.replace("Z", "+00:00"))
        updated_at = datetime.fromisoformat(fields.updated.replace("Z", "+00:00"))

        # Extract due date
        due_date = None
        if hasattr(fields, "duedate") and fields.duedate:
            due_date = datetime.strptime(fields.duedate, "%Y-%m-%d").date()

        # Extract time estimate (convert seconds to hours)
        estimated_hours = None
        if hasattr(fields, "timeoriginalestimate") and fields.timeoriginalestimate:
            estimated_hours = fields.timeoriginalestimate / 3600.0

        # Build metadata
        metadata = {
            "jira_id": jira_issue.id,
            "jira_key": jira_issue.key,
            "jira_url": f"{self._server}/browse/{jira_issue.key}",
            "platform": "jira",
            "issue_type": fields.issuetype.name,
            "project_key": fields.project.key,
            "project_name": fields.project.name,
        }

        # Add custom fields to metadata
        custom_fields = {}
        for field_id, field_name in self._field_map.items():
            if hasattr(fields, field_id):
                value = getattr(fields, field_id)
                if value is not None:
                    custom_fields[field_name] = value

        if custom_fields:
            metadata["jira_custom_fields"] = custom_fields

        # Create appropriate model
        common_kwargs = {
            "id": f"{model_class.__name__[:-5].upper()}-{jira_issue.key}",
            "title": fields.summary,
            "description": fields.description or "",
            "status": status,
            "tags": tags,
            "assignees": assignees,
            "created_at": created_at,
            "updated_at": updated_at,
            "metadata": metadata,
        }

        # Add model-specific fields
        if model_class in [TaskModel, IssueModel, EpicModel]:
            if hasattr(fields, "priority"):
                common_kwargs["priority"] = priority

        if model_class == TaskModel:
            common_kwargs["due_date"] = due_date
            common_kwargs["estimated_hours"] = estimated_hours

        if model_class == BugModel:
            # Extract severity from priority or custom field
            common_kwargs["severity"] = priority.value.lower()

            # Try to extract reproduction steps from description
            if fields.description:
                lines = fields.description.split("\n")
                for i, line in enumerate(lines):
                    if "steps" in line.lower() and "reproduce" in line.lower():
                        # Found reproduction steps section
                        steps = []
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip() and not lines[j].startswith("#"):
                                steps.append(lines[j].strip())
                            else:
                                break
                        if steps:
                            common_kwargs["reproduction_steps"] = "\n".join(steps)
                        break

        if model_class == EpicModel:
            # Look for child issues
            if hasattr(fields, "subtasks"):
                common_kwargs["child_items"] = [
                    subtask.key for subtask in fields.subtasks
                ]

        return model_class(**common_kwargs)

    def _get_issue_type_for_model(self, item: TicketModel) -> str:
        """Get JIRA issue type name for internal model type.

        WHY: Different JIRA instances may have different issue type names.
        This provides a default mapping that can be overridden via config.
        """
        # Check for custom mapping in config
        type_mapping = self.config.auth_config.get("type_mapping", {})

        if isinstance(item, BugModel):
            return type_mapping.get("bug", "Bug")
        elif isinstance(item, EpicModel):
            return type_mapping.get("epic", "Epic")
        elif isinstance(item, IssueModel):
            return type_mapping.get("issue", "Task")
        else:  # TaskModel
            return type_mapping.get("task", "Task")

    async def _update_issue_status(self, jira_issue: Any, item: TicketModel) -> None:
        """Update JIRA issue status if needed.

        WHY: JIRA uses transitions to change status, not direct field updates.
        We need to find the appropriate transition and execute it.
        """
        # Get target status name
        target_status = None
        if hasattr(item, "status"):
            if isinstance(item.status, TaskStatus):
                target_status = self.STATUS_TO_JIRA.get(item.status)
            elif isinstance(item.status, IssueStatus):
                if item.status == IssueStatus.COMPLETED:
                    target_status = "Done"
                elif item.status == IssueStatus.CANCELLED:
                    target_status = "Won't Do"

        if not target_status:
            return

        # Check if already in target status
        current_status = jira_issue.fields.status.name
        if current_status.lower() == target_status.lower():
            return

        try:
            # Get available transitions
            transitions = await self._run_async(
                self._jira_client.transitions, jira_issue
            )

            # Find matching transition
            for trans in transitions:
                if trans["to"]["name"].lower() == target_status.lower():
                    # Execute transition
                    await self._run_async(
                        self._jira_client.transition_issue, jira_issue, trans["id"]
                    )
                    break

        except JIRAError:
            # Non-critical error, status update failed but issue was created/updated
            pass


# Register the adapter
from .registry import register_adapter

register_adapter("jira", JiraAdapter)
