"""Example adapter implementation for reference.

This module demonstrates how to implement a sync adapter for a new platform.
It's not functional but shows the structure and patterns to follow.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import aiohttp

from ai_trackdown_pytools.core.models import (
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
    ValidationError,
)


class ExamplePlatformAdapter(SyncAdapter):
    """Example sync adapter for a fictional platform.

    WHY: This serves as a template for implementing new platform adapters.
    It demonstrates best practices and common patterns used in sync adapters.

    To implement a real adapter:
    1. Replace 'ExamplePlatform' with your platform name
    2. Implement authentication logic for your platform's API
    3. Map between platform's data model and our internal models
    4. Handle platform-specific error cases
    5. Add platform-specific configuration validation
    """

    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "example"

    @property
    def supported_types(self) -> Set[str]:
        """Get supported ticket types for this platform."""
        return {"task", "issue"}  # Example platform only supports tasks and issues

    def __init__(self, config: SyncConfig):
        """Initialize the adapter."""
        super().__init__(config)
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = "https://api.example.com/v1"

    def validate_config(self) -> None:
        """Validate platform-specific configuration."""
        super().validate_config()

        # Check for required authentication fields
        api_key = self.config.auth_config.get("api_key")
        workspace = self.config.auth_config.get("workspace")

        missing = []
        if not api_key:
            missing.append("api_key")
        if not workspace:
            missing.append("workspace")

        if missing:
            raise ConfigurationError(
                f"Missing required configuration for {self.platform_name}",
                platform=self.platform_name,
                missing_fields=missing,
            )

    async def authenticate(self) -> None:
        """Authenticate with the platform.

        WHY: Most platforms require authentication before any operations.
        This method sets up the authenticated session for future requests.
        """
        self.validate_config()

        # Create aiohttp session with auth headers
        headers = {
            "Authorization": f"Bearer {self.config.auth_config['api_key']}",
            "Content-Type": "application/json",
        }

        self._session = aiohttp.ClientSession(
            headers=headers, timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )

        # Test authentication by making a simple API call
        try:
            async with self._session.get(f"{self._base_url}/user") as response:
                if response.status == 401:
                    raise AuthenticationError(
                        "Invalid API key",
                        platform=self.platform_name,
                        auth_method="api_key",
                    )
                elif response.status != 200:
                    raise AuthenticationError(
                        f"Authentication failed with status {response.status}",
                        platform=self.platform_name,
                    )

                self._authenticated = True

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to connect to {self.platform_name}: {e}",
                platform=self.platform_name,
                endpoint=self._base_url,
            )

    async def test_connection(self) -> bool:
        """Test the connection to the platform."""
        if not self._authenticated:
            await self.authenticate()

        try:
            async with self._session.get(f"{self._base_url}/ping") as response:
                return response.status == 200
        except Exception:
            return False

    async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
        """Pull items from the platform."""
        if not self._authenticated:
            await self.authenticate()

        items = []
        workspace = self.config.auth_config["workspace"]

        # Example: Fetch tasks
        if self.filter_item_type("task"):
            endpoint = f"{self._base_url}/workspaces/{workspace}/tasks"
            params = {}

            if since:
                params["updated_since"] = since.isoformat()

            async with self._session.get(endpoint, params=params) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    raise RateLimitError(
                        "Rate limit exceeded",
                        platform=self.platform_name,
                        retry_after=retry_after,
                    )

                response.raise_for_status()
                data = await response.json()

                for task_data in data["tasks"]:
                    task = self._platform_task_to_model(task_data)
                    items.append(task)

        return items

    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        """Push an item to the platform."""
        if not self._authenticated:
            await self.authenticate()

        workspace = self.config.auth_config["workspace"]

        if isinstance(item, TaskModel):
            endpoint = f"{self._base_url}/workspaces/{workspace}/tasks"
            data = self._model_to_platform_task(item)

            async with self._session.post(endpoint, json=data) as response:
                response.raise_for_status()
                result = await response.json()

                return {
                    "remote_id": result["id"],
                    "remote_url": result["url"],
                }

        else:
            raise ValidationError(
                f"Unsupported item type: {type(item).__name__}",
                platform=self.platform_name,
            )

    async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
        """Update an item on the platform."""
        if not self._authenticated:
            await self.authenticate()

        workspace = self.config.auth_config["workspace"]

        if isinstance(item, TaskModel):
            endpoint = f"{self._base_url}/workspaces/{workspace}/tasks/{remote_id}"
            data = self._model_to_platform_task(item)

            async with self._session.put(endpoint, json=data) as response:
                response.raise_for_status()
                result = await response.json()

                return {
                    "remote_id": result["id"],
                    "remote_url": result["url"],
                }

        else:
            raise ValidationError(
                f"Cannot update item type: {type(item).__name__}",
                platform=self.platform_name,
            )

    async def delete_item(self, remote_id: str) -> None:
        """Delete an item from the platform."""
        if not self._authenticated:
            await self.authenticate()

        workspace = self.config.auth_config["workspace"]
        endpoint = f"{self._base_url}/workspaces/{workspace}/items/{remote_id}"

        async with self._session.delete(endpoint) as response:
            if response.status == 404:
                # Item already deleted, not an error
                return
            response.raise_for_status()

    async def get_item(self, remote_id: str) -> Optional[TicketModel]:
        """Get a single item from the platform."""
        if not self._authenticated:
            await self.authenticate()

        workspace = self.config.auth_config["workspace"]
        endpoint = f"{self._base_url}/workspaces/{workspace}/items/{remote_id}"

        try:
            async with self._session.get(endpoint) as response:
                if response.status == 404:
                    return None

                response.raise_for_status()
                data = await response.json()

                # Determine type and convert
                if data["type"] == "task":
                    return self._platform_task_to_model(data)
                else:
                    return None

        except aiohttp.ClientError:
            return None

    async def close(self) -> None:
        """Close the session."""
        if self._session:
            await self._session.close()

    # Helper methods for data conversion

    def _platform_task_to_model(self, data: Dict[str, Any]) -> TaskModel:
        """Convert platform task data to internal model."""
        # Map status
        status_map = {
            "todo": TaskStatus.OPEN,
            "in_progress": TaskStatus.IN_PROGRESS,
            "done": TaskStatus.COMPLETED,
            "cancelled": TaskStatus.CANCELLED,
        }
        status = status_map.get(data["status"], TaskStatus.OPEN)

        # Map tags
        tags = self.map_labels(data.get("labels", []), to_external=False)
        tags.append("task")

        return TaskModel(
            id=f"TSK-{data['id'][-6:]}",  # Use last 6 chars of platform ID
            title=data["title"],
            description=data.get("description", ""),
            status=status,
            tags=tags,
            assignees=data.get("assignees", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata={
                "platform": self.platform_name,
                "remote_id": data["id"],
                "remote_url": data.get("url"),
            },
        )

    def _model_to_platform_task(self, task: TaskModel) -> Dict[str, Any]:
        """Convert internal task model to platform format."""
        # Map status
        status_map = {
            TaskStatus.OPEN: "todo",
            TaskStatus.IN_PROGRESS: "in_progress",
            TaskStatus.COMPLETED: "done",
            TaskStatus.CANCELLED: "cancelled",
            TaskStatus.BLOCKED: "blocked",
        }

        # Map labels
        labels = self.map_labels(
            [tag for tag in task.tags if tag != "task"], to_external=True
        )

        return {
            "title": task.title,
            "description": task.description,
            "status": status_map.get(task.status, "todo"),
            "labels": labels,
            "assignees": task.assignees if self.config.sync_assignees else [],
        }
