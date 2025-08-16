"""ClickUp sync adapter implementation."""

import asyncio
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import aiohttp

from ai_trackdown_pytools.core.models import (
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


class ClickUpAdapter(SyncAdapter):
    """Sync adapter for ClickUp integration.

    WHY: ClickUp is a popular project management tool that many teams use. This
    adapter allows bidirectional sync between AI Trackdown and ClickUp, enabling
    teams to leverage AI-powered tracking while maintaining their existing workflows.

    DESIGN DECISION: Using aiohttp for async HTTP requests instead of a dedicated
    ClickUp library for better control over rate limiting and error handling.
    We considered pyclickup but opted for direct API calls for more flexibility.
    """

    # ClickUp API base URL
    BASE_URL = "https://api.clickup.com/api/v2"

    # Status mapping between internal and ClickUp
    STATUS_TO_CLICKUP = {
        TaskStatus.OPEN: "open",
        TaskStatus.IN_PROGRESS: "in progress",
        TaskStatus.COMPLETED: "complete",
        TaskStatus.CANCELLED: "closed",
        TaskStatus.BLOCKED: "blocked",
    }

    STATUS_FROM_CLICKUP = {v: k for k, v in STATUS_TO_CLICKUP.items()}

    # Priority mapping (ClickUp uses 1-4, 1 being highest)
    PRIORITY_TO_CLICKUP = {
        Priority.CRITICAL: 1,  # Urgent
        Priority.HIGH: 2,  # High
        Priority.MEDIUM: 3,  # Normal
        Priority.LOW: 4,  # Low
    }

    PRIORITY_FROM_CLICKUP = {
        1: Priority.CRITICAL,
        2: Priority.HIGH,
        3: Priority.MEDIUM,
        4: Priority.LOW,
        None: Priority.MEDIUM,  # Default for no priority
    }

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "clickup"

    @property
    def supported_types(self) -> Set[str]:
        """Get supported ticket types."""
        return {"task", "issue"}  # ClickUp tasks can represent both

    def __init__(self, config: SyncConfig):
        """Initialize ClickUp adapter.

        Args:
            config: Sync configuration
        """
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._headers: Dict[str, str] = {}
        self._list_id: Optional[str] = None
        self._space_id: Optional[str] = None
        self._team_id: Optional[str] = None
        self._rate_limit_remaining = 100
        self._rate_limit_reset = 0

    def validate_config(self) -> None:
        """Validate ClickUp-specific configuration.

        Raises:
            ConfigurationError: If required config is missing
        """
        super().validate_config()

        # Check for API token
        api_token = self.config.auth_config.get("api_token") or os.getenv(
            "CLICKUP_API_TOKEN"
        )
        if not api_token:
            raise ConfigurationError(
                "ClickUp API token not provided",
                platform=self.platform_name,
                missing_fields=["api_token"],
            )

        # Check for list ID (required for task operations)
        list_id = self.config.auth_config.get("list_id")
        if not list_id:
            raise ConfigurationError(
                "ClickUp list ID not specified",
                platform=self.platform_name,
                missing_fields=["list_id"],
            )

        self._list_id = list_id
        self._space_id = self.config.auth_config.get("space_id")
        self._team_id = self.config.auth_config.get("team_id")

        # Set up headers
        self._headers = {
            "Authorization": api_token,
            "Content-Type": "application/json",
        }

    async def authenticate(self) -> None:
        """Authenticate with ClickUp.

        WHY: Tests the API token by fetching user information. This ensures
        the token is valid before attempting any sync operations.

        Raises:
            AuthenticationError: If authentication fails
        """
        self.validate_config()

        # Create session if not exists
        if not self._session:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(
                headers=self._headers, timeout=timeout
            )

        try:
            # Test authentication by getting user info
            async with self._session.get(f"{self.BASE_URL}/user") as response:
                if response.status == 401:
                    raise AuthenticationError(
                        "Invalid ClickUp API token",
                        platform=self.platform_name,
                        auth_method="api_token",
                    )
                elif response.status != 200:
                    text = await response.text()
                    raise AuthenticationError(
                        f"ClickUp authentication failed: {text}",
                        platform=self.platform_name,
                        auth_method="api_token",
                    )

                self._authenticated = True

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to connect to ClickUp: {e}",
                platform=self.platform_name,
                endpoint=self.BASE_URL,
            )

    async def test_connection(self) -> bool:
        """Test connection to ClickUp.

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If connection fails
        """
        if not self._authenticated:
            await self.authenticate()

        try:
            # Test by fetching the list info
            async with self._session.get(
                f"{self.BASE_URL}/list/{self._list_id}"
            ) as response:
                if response.status == 200:
                    return True
                else:
                    text = await response.text()
                    raise ConnectionError(
                        f"Failed to access ClickUp list: {text}",
                        platform=self.platform_name,
                        endpoint=f"{self.BASE_URL}/list/{self._list_id}",
                    )
        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"ClickUp connection test failed: {e}",
                platform=self.platform_name,
                endpoint=self.BASE_URL,
            )

    async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
        """Pull tasks from ClickUp.

        Args:
            since: Only pull items updated after this timestamp

        Returns:
            List of items in internal format
        """
        if not self._authenticated:
            await self.authenticate()

        items = []
        page = 0

        while True:
            # Build query parameters
            params = {
                "page": page,
                "order_by": "updated",
                "reverse": "true",
                "subtasks": "true",
                "include_closed": "true",
            }

            # Add date filter if provided
            if since:
                # ClickUp uses milliseconds for timestamps
                params["date_updated_gt"] = int(since.timestamp() * 1000)

            # Make request with rate limiting
            await self._check_rate_limit()

            try:
                async with self._session.get(
                    f"{self.BASE_URL}/list/{self._list_id}/task", params=params
                ) as response:
                    self._update_rate_limit(response.headers)

                    if response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", "60"))
                        raise RateLimitError(
                            "ClickUp rate limit exceeded",
                            platform=self.platform_name,
                            retry_after=retry_after,
                        )
                    elif response.status != 200:
                        text = await response.text()
                        raise SyncError(
                            f"Failed to fetch ClickUp tasks: {text}",
                            platform=self.platform_name,
                        )

                    data = await response.json()
                    tasks = data.get("tasks", [])

                    # Convert each task
                    for task_data in tasks:
                        try:
                            item = self._clickup_task_to_model(task_data)
                            if self.filter_item_type(
                                item.__class__.__name__.lower().replace("model", "")
                            ):
                                items.append(item)
                        except Exception as e:
                            # Log error but continue with other tasks
                            print(
                                f"Error converting ClickUp task {task_data.get('id')}: {e}"
                            )

                    # Check if there are more pages
                    if not tasks or len(tasks) < 100:  # ClickUp default page size
                        break

                    page += 1

            except aiohttp.ClientError as e:
                raise ConnectionError(
                    f"Failed to fetch ClickUp tasks: {e}", platform=self.platform_name
                )

        return items

    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        """Create task in ClickUp.

        Args:
            item: Item to push

        Returns:
            Mapping information
        """
        if not self._authenticated:
            await self.authenticate()

        # Convert to ClickUp format
        task_data = self._model_to_clickup_task(item)

        # Make request with rate limiting
        await self._check_rate_limit()

        try:
            async with self._session.post(
                f"{self.BASE_URL}/list/{self._list_id}/task", json=task_data
            ) as response:
                self._update_rate_limit(response.headers)

                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(
                        "ClickUp rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                elif response.status not in (200, 201):
                    text = await response.text()
                    raise SyncError(
                        f"Failed to create ClickUp task: {text}",
                        platform=self.platform_name,
                    )

                result = await response.json()

                return {
                    "remote_id": result["id"],
                    "remote_url": result.get("url", ""),
                }

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to create ClickUp task: {e}", platform=self.platform_name
            )

    async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
        """Update task in ClickUp.

        Args:
            item: Updated item
            remote_id: ClickUp task ID

        Returns:
            Updated mapping information
        """
        if not self._authenticated:
            await self.authenticate()

        # Convert to ClickUp format
        task_data = self._model_to_clickup_task(item)

        # Make request with rate limiting
        await self._check_rate_limit()

        try:
            async with self._session.put(
                f"{self.BASE_URL}/task/{remote_id}", json=task_data
            ) as response:
                self._update_rate_limit(response.headers)

                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(
                        "ClickUp rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                elif response.status != 200:
                    text = await response.text()
                    raise SyncError(
                        f"Failed to update ClickUp task: {text}",
                        platform=self.platform_name,
                    )

                result = await response.json()

                return {
                    "remote_id": result["id"],
                    "remote_url": result.get("url", ""),
                }

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to update ClickUp task: {e}", platform=self.platform_name
            )

    async def delete_item(self, remote_id: str) -> None:
        """Delete task from ClickUp.

        Args:
            remote_id: ClickUp task ID
        """
        if not self._authenticated:
            await self.authenticate()

        # Make request with rate limiting
        await self._check_rate_limit()

        try:
            async with self._session.delete(
                f"{self.BASE_URL}/task/{remote_id}"
            ) as response:
                self._update_rate_limit(response.headers)

                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(
                        "ClickUp rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                elif response.status not in (200, 204):
                    text = await response.text()
                    raise SyncError(
                        f"Failed to delete ClickUp task: {text}",
                        platform=self.platform_name,
                    )

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to delete ClickUp task: {e}", platform=self.platform_name
            )

    async def get_item(self, remote_id: str) -> Optional[TicketModel]:
        """Get single task from ClickUp.

        Args:
            remote_id: ClickUp task ID

        Returns:
            Item in internal format or None
        """
        if not self._authenticated:
            await self.authenticate()

        # Make request with rate limiting
        await self._check_rate_limit()

        try:
            async with self._session.get(
                f"{self.BASE_URL}/task/{remote_id}"
            ) as response:
                self._update_rate_limit(response.headers)

                if response.status == 404:
                    return None
                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", "60"))
                    raise RateLimitError(
                        "ClickUp rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )
                elif response.status != 200:
                    text = await response.text()
                    raise SyncError(
                        f"Failed to fetch ClickUp task: {text}",
                        platform=self.platform_name,
                    )

                task_data = await response.json()
                return self._clickup_task_to_model(task_data)

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to fetch ClickUp task: {e}", platform=self.platform_name
            )

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    # Helper methods

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting.

        WHY: ClickUp has strict rate limits that vary by plan. We track the
        remaining requests and wait if we're close to the limit to avoid 429 errors.
        """
        if self._rate_limit_remaining < 5:
            # Wait until rate limit resets
            wait_time = max(0, self._rate_limit_reset - time.time())
            if wait_time > 0:
                await asyncio.sleep(wait_time + 1)  # Add 1 second buffer

    def _update_rate_limit(self, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers."""
        if "X-RateLimit-Remaining" in headers:
            self._rate_limit_remaining = int(headers["X-RateLimit-Remaining"])
        if "X-RateLimit-Reset" in headers:
            self._rate_limit_reset = int(headers["X-RateLimit-Reset"])

    def _clickup_task_to_model(self, task_data: Dict[str, Any]) -> TicketModel:
        """Convert ClickUp task to internal model.

        WHY: We default to TaskModel but could use IssueModel based on custom
        fields or tags. This provides flexibility for different use cases.
        """
        # Extract basic fields
        # Generate numeric ID from hash of ClickUp ID for pattern compliance
        numeric_id = str(abs(hash(task_data["id"])) % 1000000)
        task_id = f"TSK-{numeric_id}"
        title = task_data.get("name", "Untitled")
        description = task_data.get("description", "")

        # Convert timestamps (ClickUp uses milliseconds)
        created_at = datetime.fromtimestamp(int(task_data["date_created"]) / 1000)
        updated_at = datetime.fromtimestamp(int(task_data["date_updated"]) / 1000)

        # Map status
        status_name = task_data.get("status", {}).get("status", "open")
        status = self.STATUS_FROM_CLICKUP.get(status_name.lower(), TaskStatus.OPEN)

        # Map priority
        priority_data = task_data.get("priority")
        if priority_data and priority_data.get("priority"):
            priority_num = int(priority_data["priority"])
            priority = self.PRIORITY_FROM_CLICKUP.get(priority_num, Priority.MEDIUM)
        else:
            priority = Priority.MEDIUM

        # Extract assignees
        assignees = []
        for assignee in task_data.get("assignees", []):
            email = assignee.get("email")
            username = assignee.get("username")
            assignees.append(email or username)

        # Extract tags
        tags = [tag["name"] for tag in task_data.get("tags", [])]
        tags = self.map_labels(tags, to_external=False)

        # Extract dates
        due_date = None
        if task_data.get("due_date"):
            due_date = datetime.fromtimestamp(int(task_data["due_date"]) / 1000).date()

        # Extract time estimates
        estimated_hours = None
        if task_data.get("time_estimate"):
            # Convert milliseconds to hours
            estimated_hours = int(task_data["time_estimate"]) / (3600 * 1000)

        actual_hours = None
        if task_data.get("time_spent"):
            # Convert milliseconds to hours
            actual_hours = int(task_data["time_spent"]) / (3600 * 1000)

        # Build metadata
        metadata = {
            "clickup_id": task_data["id"],
            "clickup_url": task_data.get("url", ""),
            "clickup_list_id": task_data.get("list", {}).get("id"),
            "platform": "clickup",
        }

        # Store custom fields in metadata
        if task_data.get("custom_fields"):
            metadata["custom_fields"] = task_data["custom_fields"]

        # Determine if this should be an Issue or Task
        # You could use custom fields or tags to determine this
        use_issue_model = "bug" in [t.lower() for t in tags] or "issue" in [
            t.lower() for t in tags
        ]

        if use_issue_model:
            return IssueModel(
                id=f"ISS-{numeric_id}",
                title=title,
                description=description,
                status=IssueStatus.OPEN
                if status == TaskStatus.OPEN
                else IssueStatus.COMPLETED,
                severity=priority,
                tags=tags,
                assignees=assignees,
                created_at=created_at,
                updated_at=updated_at,
                due_date=due_date,
                estimated_hours=estimated_hours,
                actual_hours=actual_hours,
                metadata=metadata,
            )
        else:
            return TaskModel(
                id=task_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                tags=tags,
                assignees=assignees,
                created_at=created_at,
                updated_at=updated_at,
                due_date=due_date,
                estimated_hours=estimated_hours,
                actual_hours=actual_hours,
                metadata=metadata,
            )

    def _model_to_clickup_task(self, item: TicketModel) -> Dict[str, Any]:
        """Convert internal model to ClickUp task format."""
        data = {
            "name": item.title,
            "description": item.description or "",
        }

        # Map status
        if hasattr(item, "status"):
            status = item.status
            # Handle both enum and string values (Pydantic may convert to string)
            if isinstance(status, str):
                # Try to convert string back to enum
                try:
                    status = TaskStatus(status)
                    clickup_status = self.STATUS_TO_CLICKUP.get(status)
                except ValueError:
                    # Not a valid TaskStatus, try IssueStatus
                    try:
                        status = IssueStatus(status)
                        # Map IssueStatus to ClickUp status
                        if status == IssueStatus.OPEN:
                            clickup_status = "open"
                        elif status == IssueStatus.IN_PROGRESS:
                            clickup_status = "in progress"
                        elif status == IssueStatus.COMPLETED:
                            clickup_status = "complete"
                        elif status == IssueStatus.CANCELLED:
                            clickup_status = "closed"
                        else:
                            clickup_status = "open"
                    except ValueError:
                        clickup_status = "open"
            elif isinstance(status, TaskStatus):
                clickup_status = self.STATUS_TO_CLICKUP.get(status)
            elif isinstance(status, IssueStatus):
                # Map IssueStatus to TaskStatus equivalent
                if status == IssueStatus.OPEN:
                    clickup_status = "open"
                elif status == IssueStatus.IN_PROGRESS:
                    clickup_status = "in progress"
                elif status == IssueStatus.COMPLETED:
                    clickup_status = "complete"
                elif status == IssueStatus.CANCELLED:
                    clickup_status = "closed"
                else:
                    clickup_status = "open"
            else:
                clickup_status = "open"

            if clickup_status:
                data["status"] = clickup_status

        # Map priority
        if hasattr(item, "priority"):
            priority = item.priority
            # Handle both enum and string values
            if isinstance(priority, str):
                try:
                    priority = Priority(priority)
                except ValueError:
                    priority = None

            if priority:
                priority_num = self.PRIORITY_TO_CLICKUP.get(priority)
                if priority_num:
                    data["priority"] = priority_num
        elif hasattr(item, "severity"):
            # For IssueModel, use severity as priority
            severity = item.severity
            if isinstance(severity, str):
                try:
                    severity = Priority(severity)
                except ValueError:
                    severity = None

            if severity:
                priority_num = self.PRIORITY_TO_CLICKUP.get(severity)
                if priority_num:
                    data["priority"] = priority_num

        # Map tags
        if self.config.sync_tags and item.tags:
            mapped_tags = self.map_labels(item.tags, to_external=True)
            data["tags"] = mapped_tags

        # Map assignees (would need user ID lookup in real implementation)
        # For now, we'll skip assignees as they require user IDs

        # Map dates
        if hasattr(item, "due_date") and item.due_date:
            # Convert date to datetime then to milliseconds
            from datetime import datetime, time

            dt = datetime.combine(item.due_date, time.min)
            data["due_date"] = int(dt.timestamp() * 1000)

        # Map time estimates
        if hasattr(item, "estimated_hours") and item.estimated_hours:
            # Convert hours to milliseconds
            data["time_estimate"] = int(item.estimated_hours * 3600 * 1000)

        return data


# Register the adapter
from .registry import register_adapter

register_adapter("clickup", ClickUpAdapter)
