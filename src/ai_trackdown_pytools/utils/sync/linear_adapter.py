"""Linear sync adapter implementation using GraphQL."""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportError

from ai_trackdown_pytools.core.models import (
    BugModel,
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
)


class LinearAdapter(SyncAdapter):
    """Sync adapter for Linear integration using GraphQL.

    WHY: Linear uses a GraphQL API which requires different handling than REST APIs.
    This adapter provides a clean interface to Linear's issue tracking system while
    handling the complexities of GraphQL queries and mutations.

    DESIGN DECISION: Using gql library with async transport for efficient GraphQL
    operations. All queries are optimized to fetch only necessary fields to minimize
    API usage and improve performance.
    """

    # Linear GraphQL endpoint
    GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

    # Status mapping between Linear workflow states and our TaskStatus
    STATUS_TO_LINEAR = {
        TaskStatus.OPEN: ["Backlog", "Todo", "Unstarted"],
        TaskStatus.IN_PROGRESS: ["In Progress", "In Review", "Started"],
        TaskStatus.COMPLETED: ["Done", "Completed", "Shipped"],
        TaskStatus.CANCELLED: ["Canceled", "Cancelled"],
        TaskStatus.BLOCKED: ["Blocked"],
    }

    # Reverse mapping for Linear to TaskStatus
    LINEAR_TO_STATUS = {
        "backlog": TaskStatus.OPEN,
        "todo": TaskStatus.OPEN,
        "unstarted": TaskStatus.OPEN,
        "in progress": TaskStatus.IN_PROGRESS,
        "in review": TaskStatus.IN_PROGRESS,
        "started": TaskStatus.IN_PROGRESS,
        "done": TaskStatus.COMPLETED,
        "completed": TaskStatus.COMPLETED,
        "shipped": TaskStatus.COMPLETED,
        "canceled": TaskStatus.CANCELLED,
        "cancelled": TaskStatus.CANCELLED,
        "blocked": TaskStatus.BLOCKED,
    }

    # Priority mapping (Linear uses 0-4, 0 being none)
    PRIORITY_TO_LINEAR = {
        Priority.LOW: 4,
        Priority.MEDIUM: 3,
        Priority.HIGH: 2,
        Priority.CRITICAL: 1,
    }

    PRIORITY_FROM_LINEAR = {
        0: Priority.MEDIUM,  # No priority defaults to medium
        1: Priority.CRITICAL,
        2: Priority.HIGH,
        3: Priority.MEDIUM,
        4: Priority.LOW,
    }

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "linear"

    @property
    def supported_types(self) -> Set[str]:
        """Get supported ticket types."""
        return {"task", "issue", "bug"}  # Linear issues can represent various types

    def __init__(self, config: SyncConfig):
        """Initialize Linear adapter.

        Args:
            config: Sync configuration
        """
        super().__init__(config)
        self._client: Optional[Client] = None
        self._transport: Optional[AIOHTTPTransport] = None
        self._team_id: Optional[str] = None
        self._project_id: Optional[str] = None
        self._workflow_states: Dict[str, str] = {}  # state name -> state id mapping

    def validate_config(self) -> None:
        """Validate Linear-specific configuration.

        Raises:
            ConfigurationError: If required config is missing
        """
        super().validate_config()

        # Check for API key
        api_key = self.config.auth_config.get("api_key") or os.getenv("LINEAR_API_KEY")
        if not api_key:
            raise ConfigurationError(
                "Linear API key not provided",
                platform=self.platform_name,
                missing_fields=["api_key"],
            )

        # Team ID is required for creating issues
        self._team_id = self.config.auth_config.get("team_id")
        if not self._team_id:
            raise ConfigurationError(
                "Linear team ID not specified",
                platform=self.platform_name,
                missing_fields=["team_id"],
            )

        # Project ID is optional but recommended
        self._project_id = self.config.auth_config.get("project_id")

    async def authenticate(self) -> None:
        """Authenticate with Linear.

        WHY: Linear uses API key authentication passed in the Authorization header.
        We validate the key by making a simple query to fetch the authenticated user.

        Raises:
            AuthenticationError: If authentication fails
        """
        self.validate_config()

        api_key = self.config.auth_config.get("api_key") or os.getenv("LINEAR_API_KEY")

        try:
            # Create transport with API key
            self._transport = AIOHTTPTransport(
                url=self.GRAPHQL_ENDPOINT, headers={"Authorization": api_key}
            )

            # Create client
            self._client = Client(
                transport=self._transport, fetch_schema_from_transport=True
            )

            # Test authentication by fetching viewer info
            query = gql(
                """
                query TestAuth {
                    viewer {
                        id
                        email
                        name
                    }
                }
            """
            )

            async with self._client as session:
                await session.execute(query)

            self._authenticated = True

            # Fetch workflow states for the team
            await self._fetch_workflow_states()

        except TransportError as e:
            if "401" in str(e) or "Unauthorized" in str(e):
                raise AuthenticationError(
                    "Invalid Linear API key",
                    platform=self.platform_name,
                    auth_method="api_key",
                )
            else:
                raise ConnectionError(
                    f"Failed to connect to Linear: {e}",
                    platform=self.platform_name,
                    endpoint=self.GRAPHQL_ENDPOINT,
                )
        except Exception as e:
            raise AuthenticationError(
                f"Linear authentication failed: {e}", platform=self.platform_name
            )

    async def _fetch_workflow_states(self) -> None:
        """Fetch workflow states for the team.

        WHY: Linear uses workflow states that are customizable per team. We need
        to map these to our standard statuses for proper synchronization.
        """
        query = gql(
            """
            query GetWorkflowStates($teamId: String!) {
                team(id: $teamId) {
                    states {
                        nodes {
                            id
                            name
                            type
                        }
                    }
                }
            }
        """
        )

        try:
            async with self._client as session:
                result = await session.execute(
                    query, variable_values={"teamId": self._team_id}
                )

            states = result.get("team", {}).get("states", {}).get("nodes", [])
            self._workflow_states = {state["name"]: state["id"] for state in states}

        except Exception as e:
            # Non-fatal: we can still work without pre-fetched states
            print(f"Warning: Could not fetch workflow states: {e}")

    async def test_connection(self) -> bool:
        """Test the connection to Linear.

        Returns:
            True if connection is successful

        Raises:
            ConnectionError: If connection test fails
        """
        if not self._authenticated:
            raise ConnectionError(
                "Not authenticated with Linear", platform=self.platform_name
            )

        try:
            query = gql(
                """
                query TestConnection {
                    organization {
                        id
                        name
                    }
                }
            """
            )

            async with self._client as session:
                await session.execute(query)

            return True

        except Exception as e:
            raise ConnectionError(
                f"Linear connection test failed: {e}", platform=self.platform_name
            )

    async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
        """Pull issues from Linear.

        WHY: Uses GraphQL to efficiently fetch issues with all necessary fields
        in a single request. Implements cursor-based pagination for large datasets.

        Args:
            since: Only pull items updated after this timestamp

        Returns:
            List of items in internal format

        Raises:
            SyncError: If pull operation fails
        """
        if not self._authenticated:
            raise SyncError(
                "Not authenticated with Linear", platform=self.platform_name
            )

        items = []
        has_next_page = True
        end_cursor = None

        # Build filter
        filters = {}
        if self._team_id:
            filters["team"] = {"id": {"eq": self._team_id}}
        if self._project_id:
            filters["project"] = {"id": {"eq": self._project_id}}
        if since:
            filters["updatedAt"] = {"gte": since.isoformat()}

        # GraphQL query for fetching issues
        query = gql(
            """
            query GetIssues($first: Int!, $after: String, $filter: IssueFilter) {
                issues(first: $first, after: $after, filter: $filter) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        id
                        identifier
                        title
                        description
                        priority
                        priorityLabel
                        state {
                            id
                            name
                            type
                        }
                        assignee {
                            id
                            email
                            name
                        }
                        labels {
                            nodes {
                                id
                                name
                            }
                        }
                        project {
                            id
                            name
                        }
                        cycle {
                            id
                            name
                        }
                        estimate
                        dueDate
                        createdAt
                        updatedAt
                        url
                    }
                }
            }
        """
        )

        try:
            while has_next_page:
                variables = {
                    "first": min(self.config.batch_size, 100),  # Linear max is 100
                    "after": end_cursor,
                    "filter": filters if filters else None,
                }

                async with self._client as session:
                    result = await session.execute(query, variable_values=variables)

                issues_data = result.get("issues", {})
                page_info = issues_data.get("pageInfo", {})
                nodes = issues_data.get("nodes", [])

                for issue_data in nodes:
                    try:
                        item = await self._map_from_linear(issue_data)
                        if self.filter_item_type(
                            item.__class__.__name__.lower().replace("model", "")
                        ):
                            items.append(item)
                    except Exception as e:
                        print(
                            f"Error mapping Linear issue {issue_data.get('identifier', 'unknown')}: {e}"
                        )

                has_next_page = page_info.get("hasNextPage", False)
                end_cursor = page_info.get("endCursor")

        except TransportError as e:
            if "429" in str(e):
                raise RateLimitError(
                    "Linear API rate limit exceeded",
                    platform=self.platform_name,
                    retry_after=60,  # Linear doesn't provide retry-after header
                )
            else:
                raise SyncError(
                    f"Failed to pull items from Linear: {e}",
                    platform=self.platform_name,
                )

        return items

    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        """Push a single item to Linear.

        Args:
            item: Item to push in internal format

        Returns:
            Mapping information

        Raises:
            SyncError: If push operation fails
        """
        if not self._authenticated:
            raise SyncError(
                "Not authenticated with Linear", platform=self.platform_name
            )

        # Map to Linear format
        input_data = await self._map_to_linear(item)

        # GraphQL mutation for creating issue
        mutation = gql(
            """
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        url
                    }
                }
            }
        """
        )

        try:
            async with self._client as session:
                result = await session.execute(
                    mutation, variable_values={"input": input_data}
                )

            create_result = result.get("issueCreate", {})
            if not create_result.get("success"):
                raise SyncError(
                    "Failed to create issue in Linear", platform=self.platform_name
                )

            issue = create_result.get("issue", {})
            return {
                "remote_id": issue.get("id"),
                "remote_key": issue.get("identifier"),
                "remote_url": issue.get("url"),
                "linear_id": issue.get("id"),
                "linear_identifier": issue.get("identifier"),
            }

        except TransportError as e:
            if "429" in str(e):
                raise RateLimitError(
                    "Linear API rate limit exceeded",
                    platform=self.platform_name,
                    retry_after=60,
                )
            else:
                raise SyncError(
                    f"Failed to create issue in Linear: {e}",
                    platform=self.platform_name,
                )

    async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
        """Update an existing item on Linear.

        Args:
            item: Updated item in internal format
            remote_id: ID of the item on Linear

        Returns:
            Updated mapping information

        Raises:
            SyncError: If update operation fails
        """
        if not self._authenticated:
            raise SyncError(
                "Not authenticated with Linear", platform=self.platform_name
            )

        # Map to Linear format (exclude fields that can't be updated)
        input_data = await self._map_to_linear(item, is_update=True)

        # GraphQL mutation for updating issue
        mutation = gql(
            """
            mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    success
                    issue {
                        id
                        identifier
                        url
                    }
                }
            }
        """
        )

        try:
            async with self._client as session:
                result = await session.execute(
                    mutation, variable_values={"id": remote_id, "input": input_data}
                )

            update_result = result.get("issueUpdate", {})
            if not update_result.get("success"):
                raise SyncError(
                    f"Failed to update issue {remote_id} in Linear",
                    platform=self.platform_name,
                )

            issue = update_result.get("issue", {})
            return {
                "remote_id": issue.get("id"),
                "remote_key": issue.get("identifier"),
                "remote_url": issue.get("url"),
                "linear_id": issue.get("id"),
                "linear_identifier": issue.get("identifier"),
            }

        except TransportError as e:
            if "429" in str(e):
                raise RateLimitError(
                    "Linear API rate limit exceeded",
                    platform=self.platform_name,
                    retry_after=60,
                )
            else:
                raise SyncError(
                    f"Failed to update issue in Linear: {e}",
                    platform=self.platform_name,
                )

    async def delete_item(self, remote_id: str) -> None:
        """Archive an item in Linear (Linear doesn't support hard delete).

        Args:
            remote_id: ID of the item to archive

        Raises:
            SyncError: If delete operation fails
        """
        if not self._authenticated:
            raise SyncError(
                "Not authenticated with Linear", platform=self.platform_name
            )

        # GraphQL mutation for archiving issue
        mutation = gql(
            """
            mutation ArchiveIssue($id: String!) {
                issueArchive(id: $id) {
                    success
                }
            }
        """
        )

        try:
            async with self._client as session:
                result = await session.execute(
                    mutation, variable_values={"id": remote_id}
                )

            if not result.get("issueArchive", {}).get("success"):
                raise SyncError(
                    f"Failed to archive issue {remote_id} in Linear",
                    platform=self.platform_name,
                )

        except TransportError as e:
            if "429" in str(e):
                raise RateLimitError(
                    "Linear API rate limit exceeded",
                    platform=self.platform_name,
                    retry_after=60,
                )
            else:
                raise SyncError(
                    f"Failed to archive issue in Linear: {e}",
                    platform=self.platform_name,
                )

    async def get_item(self, remote_id: str) -> Optional[TicketModel]:
        """Get a single item from Linear.

        Args:
            remote_id: ID of the item to retrieve

        Returns:
            Item in internal format or None if not found

        Raises:
            SyncError: If retrieval fails
        """
        if not self._authenticated:
            raise SyncError(
                "Not authenticated with Linear", platform=self.platform_name
            )

        # GraphQL query for single issue
        query = gql(
            """
            query GetIssue($id: String!) {
                issue(id: $id) {
                    id
                    identifier
                    title
                    description
                    priority
                    priorityLabel
                    state {
                        id
                        name
                        type
                    }
                    assignee {
                        id
                        email
                        name
                    }
                    labels {
                        nodes {
                            id
                            name
                        }
                    }
                    project {
                        id
                        name
                    }
                    cycle {
                        id
                        name
                    }
                    estimate
                    dueDate
                    createdAt
                    updatedAt
                    url
                }
            }
        """
        )

        try:
            async with self._client as session:
                result = await session.execute(query, variable_values={"id": remote_id})

            issue_data = result.get("issue")
            if not issue_data:
                return None

            return await self._map_from_linear(issue_data)

        except TransportError as e:
            if "429" in str(e):
                raise RateLimitError(
                    "Linear API rate limit exceeded",
                    platform=self.platform_name,
                    retry_after=60,
                )
            else:
                raise SyncError(
                    f"Failed to get issue from Linear: {e}", platform=self.platform_name
                )

    async def _map_to_linear(
        self, item: TicketModel, is_update: bool = False
    ) -> Dict[str, Any]:
        """Map internal model to Linear format.

        WHY: Linear has specific field requirements and naming conventions.
        This method handles the translation while preserving Linear-specific
        features like cycles and projects.

        Args:
            item: Internal model to map
            is_update: Whether this is for an update (excludes some fields)

        Returns:
            Linear-formatted data
        """
        data = {
            "title": item.title,
            "description": item.description or "",
        }

        # Team ID is required for creation but not updates
        if not is_update:
            data["teamId"] = self._team_id

        # Map priority
        priority = getattr(item, "priority", Priority.MEDIUM)
        if priority in self.PRIORITY_TO_LINEAR:
            data["priority"] = self.PRIORITY_TO_LINEAR[priority]

        # Map state if we have the workflow states
        status = getattr(item, "status", TaskStatus.OPEN)
        if self._workflow_states:
            # Find matching state name
            for state_name, state_id in self._workflow_states.items():
                if state_name.lower() in [
                    s.lower() for s in self.STATUS_TO_LINEAR.get(status, [])
                ]:
                    data["stateId"] = state_id
                    break

        # Map assignee (Linear takes assignee ID, not email)
        # This would require looking up user IDs, skipping for now

        # Map labels as tag names (would need to look up label IDs)
        # Skipping for now as it requires additional API calls

        # Map due date
        if hasattr(item, "due_date") and item.due_date:
            data["dueDate"] = item.due_date.isoformat()

        # Map estimate (Linear uses points, we use hours)
        if hasattr(item, "estimated_hours") and item.estimated_hours:
            # Convert hours to points (rough approximation)
            data["estimate"] = max(1, int(item.estimated_hours / 4))

        # Add project if configured
        if self._project_id and not is_update:
            data["projectId"] = self._project_id

        # Preserve Linear-specific metadata if present
        if hasattr(item, "metadata") and item.metadata:
            if "linear_cycle_id" in item.metadata:
                data["cycleId"] = item.metadata["linear_cycle_id"]
            if "linear_label_ids" in item.metadata:
                data["labelIds"] = item.metadata["linear_label_ids"]

        return data

    async def _map_from_linear(self, linear_data: Dict[str, Any]) -> TicketModel:
        """Map Linear issue to internal model.

        WHY: Translates Linear's GraphQL response format to our internal
        models while preserving Linear-specific information in metadata.

        Args:
            linear_data: Linear issue data

        Returns:
            Internal model representation
        """
        # Determine the type based on labels or default to task
        ticket_type = "task"
        labels = linear_data.get("labels", {}).get("nodes", [])
        label_names = [label["name"].lower() for label in labels]

        if "bug" in label_names:
            ticket_type = "bug"
        elif "issue" in label_names:
            ticket_type = "issue"

        # Map status
        state = linear_data.get("state", {})
        state_name = state.get("name", "").lower()
        status = self.LINEAR_TO_STATUS.get(state_name, TaskStatus.OPEN)

        # For issue type, map to IssueStatus
        if ticket_type == "issue":
            status_map = {
                TaskStatus.OPEN: IssueStatus.OPEN,
                TaskStatus.IN_PROGRESS: IssueStatus.INVESTIGATING,
                TaskStatus.COMPLETED: IssueStatus.RESOLVED,
                TaskStatus.CANCELLED: IssueStatus.WONT_FIX,
            }
            status = status_map.get(status, IssueStatus.OPEN)

        # Map priority
        priority_num = linear_data.get("priority", 0)
        priority = self.PRIORITY_FROM_LINEAR.get(priority_num, Priority.MEDIUM)

        # Extract assignee
        assignee_data = linear_data.get("assignee", {})
        assignees = []
        if assignee_data:
            assignees = [assignee_data.get("email") or assignee_data.get("name", "")]

        # Extract tags from labels
        tags = [label["name"] for label in labels]

        # Build metadata
        metadata = {
            "linear_id": linear_data.get("id"),
            "linear_identifier": linear_data.get("identifier"),
            "linear_url": linear_data.get("url"),
            "source": "linear",
        }

        # Add Linear-specific fields
        if linear_data.get("project"):
            metadata["linear_project"] = linear_data["project"]["name"]
            metadata["linear_project_id"] = linear_data["project"]["id"]

        if linear_data.get("cycle"):
            metadata["linear_cycle"] = linear_data["cycle"]["name"]
            metadata["linear_cycle_id"] = linear_data["cycle"]["id"]

        if linear_data.get("estimate"):
            metadata["linear_estimate"] = linear_data["estimate"]

        # Store label IDs for future updates
        if labels:
            metadata["linear_label_ids"] = [label["id"] for label in labels]

        # Common fields
        common_fields = {
            "id": f"{ticket_type.upper()}-{linear_data.get('identifier', linear_data['id'])}",
            "title": linear_data.get("title", "Untitled"),
            "description": linear_data.get("description", ""),
            "created_at": datetime.fromisoformat(
                linear_data["createdAt"].replace("Z", "+00:00")
            ),
            "updated_at": datetime.fromisoformat(
                linear_data["updatedAt"].replace("Z", "+00:00")
            ),
            "assignees": assignees,
            "tags": tags,
            "metadata": metadata,
        }

        # Add type-specific fields
        if ticket_type == "task":
            task_fields = common_fields.copy()
            task_fields["status"] = status
            task_fields["priority"] = priority

            if linear_data.get("dueDate"):
                task_fields["due_date"] = datetime.fromisoformat(
                    linear_data["dueDate"]
                ).date()

            if linear_data.get("estimate"):
                # Convert points to hours (rough approximation)
                task_fields["estimated_hours"] = float(linear_data["estimate"] * 4)

            return TaskModel(**task_fields)

        elif ticket_type == "issue":
            issue_fields = common_fields.copy()
            issue_fields["status"] = status
            issue_fields["priority"] = priority
            issue_fields["severity"] = priority  # Use priority as severity proxy

            return IssueModel(**issue_fields)

        else:  # bug
            bug_fields = common_fields.copy()
            bug_fields["status"] = status
            bug_fields["priority"] = priority
            bug_fields["severity"] = priority

            return BugModel(**bug_fields)

    async def close(self) -> None:
        """Close the GraphQL client connection.

        WHY: Ensures proper cleanup of the HTTP transport and any open connections.
        """
        if self._transport:
            await self._transport.close()
        self._authenticated = False


# Register the adapter
from .registry import register_adapter

register_adapter("linear", LinearAdapter)
