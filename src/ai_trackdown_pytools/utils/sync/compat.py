"""Compatibility layer for existing sync functionality.

WHY: This module provides backward compatibility with the existing sync
command while using the new adapter system underneath. It allows for a
gradual migration to the new system.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Tuple

from ai_trackdown_pytools.core.models import TicketModel
from ai_trackdown_pytools.core.task import TaskManager

from .base import SyncConfig, SyncDirection, SyncResult
from .exceptions import SyncError
from .registry import get_adapter


class SyncBridge:
    """Bridge between old sync interface and new adapter system.

    WHY: Provides a synchronous interface that matches the existing sync
    command expectations while using the async adapter system internally.
    This allows us to migrate gradually without breaking existing code.
    """

    def __init__(self, task_manager: TaskManager):
        """Initialize the sync bridge.

        Args:
            task_manager: TaskManager instance for local operations
        """
        self.task_manager = task_manager
        self._loop = None

    def _get_loop(self):
        """Get or create event loop.

        WHY: The existing sync command is synchronous, but our adapters
        are async. This ensures we have a consistent event loop.
        """
        if self._loop is None:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    def _run_async(self, coro):
        """Run an async coroutine in a sync context."""
        loop = self._get_loop()
        return loop.run_until_complete(coro)

    def pull_from_platform(
        self, platform: str, config: Dict[str, Any], dry_run: bool = False
    ) -> Tuple[int, int]:
        """Pull items from a platform.

        WHY: Matches the interface of the existing pull_issues_from_github
        method for backward compatibility.

        Args:
            platform: Platform name (e.g., "github")
            config: Platform configuration
            dry_run: If True, don't actually create/update items

        Returns:
            Tuple of (created_count, updated_count)
        """
        # Create sync config
        sync_config = SyncConfig(
            platform=platform,
            direction=SyncDirection.PULL,
            dry_run=dry_run,
            auth_config=config,
        )

        # Get adapter
        adapter = get_adapter(platform, sync_config)

        # Run sync
        result = self._run_async(self._pull_items(adapter, dry_run))

        return result.items_created, result.items_updated

    def push_to_platform(
        self, platform: str, config: Dict[str, Any], dry_run: bool = False
    ) -> Tuple[int, int, List[str]]:
        """Push items to a platform.

        Args:
            platform: Platform name
            config: Platform configuration
            dry_run: If True, don't actually push items

        Returns:
            Tuple of (created_count, updated_count, errors)
        """
        # Create sync config
        sync_config = SyncConfig(
            platform=platform,
            direction=SyncDirection.PUSH,
            dry_run=dry_run,
            auth_config=config,
        )

        # Get adapter
        adapter = get_adapter(platform, sync_config)

        # Run sync
        result = self._run_async(self._push_items(adapter, dry_run))

        # Format errors for backward compatibility
        errors = [
            f"Failed to sync {e['item_id']}: {e['error_message']}"
            for e in result.errors
        ]

        return result.items_created, result.items_updated, errors

    async def _pull_items(self, adapter, dry_run: bool) -> SyncResult:
        """Pull items using the adapter."""
        result = SyncResult(
            platform=adapter.platform_name,
            direction=SyncDirection.PULL,
            started_at=datetime.now(),
        )

        try:
            # Authenticate
            await adapter.authenticate()

            # Get existing items to check for updates
            existing_tasks = self.task_manager.list_tasks()
            existing_by_remote_id = {}

            for task in existing_tasks:
                if (
                    task.metadata
                    and task.metadata.get("platform") == adapter.platform_name
                ):
                    remote_id = task.metadata.get(f"{adapter.platform_name}_id")
                    if remote_id:
                        existing_by_remote_id[remote_id] = task

            # Pull items from platform
            remote_items = await adapter.pull_items()

            for item in remote_items:
                result.items_processed += 1

                # Check if we already have this item
                remote_id = item.metadata.get(f"{adapter.platform_name}_id")
                existing = existing_by_remote_id.get(remote_id) if remote_id else None

                try:
                    if existing:
                        # Update existing item
                        if not dry_run:
                            self.task_manager.update_task(
                                existing.id,
                                title=item.title,
                                description=item.description,
                                status=item.status.value,
                                tags=item.tags,
                                assignees=item.assignees,
                                metadata={**existing.metadata, **item.metadata},
                            )
                        result.items_updated += 1
                        result.updated_ids.append((existing.id, remote_id))
                    else:
                        # Create new item
                        if not dry_run:
                            created = self.task_manager.create_task(
                                title=item.title,
                                description=item.description,
                                status=item.status.value,
                                tags=item.tags,
                                assignees=item.assignees,
                                metadata=item.metadata,
                            )
                            result.created_ids.append((created.id, remote_id))
                        else:
                            result.created_ids.append(("DRY-RUN", remote_id))
                        result.items_created += 1

                except Exception as e:
                    result.add_error(
                        item.id, e, {"title": item.title, "remote_id": remote_id}
                    )

        except SyncError as e:
            result.add_error("_sync", e)
        finally:
            await adapter.close()
            result.completed_at = datetime.now()

        return result

    async def _push_items(self, adapter, dry_run: bool) -> SyncResult:
        """Push items using the adapter."""
        result = SyncResult(
            platform=adapter.platform_name,
            direction=SyncDirection.PUSH,
            started_at=datetime.now(),
        )

        try:
            # Authenticate
            await adapter.authenticate()

            # Get items to push
            all_tasks = self.task_manager.list_tasks()

            # Filter items that need to be pushed
            for task in all_tasks:
                # Skip if already synced to this platform
                if task.metadata and task.metadata.get(f"{adapter.platform_name}_id"):
                    continue

                # Skip if type not supported
                task_type = self._determine_task_type(task)
                if not adapter.filter_item_type(task_type):
                    continue

                result.items_processed += 1

                try:
                    if not dry_run:
                        # Convert to appropriate model type
                        item = self._task_to_model(task, task_type)

                        # Push to platform
                        mapping = await adapter.push_item(item)

                        # Update local task with mapping
                        self.task_manager.update_task(
                            task.id,
                            metadata={
                                **task.metadata,
                                f"{adapter.platform_name}_id": mapping["remote_id"],
                                f"{adapter.platform_name}_url": mapping.get(
                                    "remote_url"
                                ),
                                "platform": adapter.platform_name,
                            },
                        )

                        result.created_ids.append((task.id, mapping["remote_id"]))
                    else:
                        result.created_ids.append((task.id, "DRY-RUN"))

                    result.items_created += 1

                except Exception as e:
                    result.add_error(task.id, e, {"title": task.title})

        except SyncError as e:
            result.add_error("_sync", e)
        finally:
            await adapter.close()
            result.completed_at = datetime.now()

        return result

    def _determine_task_type(self, task) -> str:
        """Determine the type of a task based on tags."""
        if "pull-request" in task.tags or "pr" in task.tags:
            return "pr"
        elif "issue" in task.tags:
            return "issue"
        elif "bug" in task.tags:
            return "bug"
        elif "epic" in task.tags:
            return "epic"
        else:
            return "task"

    def _task_to_model(self, task, task_type: str) -> TicketModel:
        """Convert a task to the appropriate model type.

        WHY: The task manager stores everything as generic tasks, but
        adapters expect specific model types for proper field mapping.
        """
        # Import here to avoid circular imports
        from ai_trackdown_pytools.core.models import (
            BugModel,
            BugStatus,
            EpicModel,
            EpicStatus,
            IssueModel,
            IssueStatus,
            PRModel,
            PRStatus,
            TaskModel,
            TaskStatus,
        )

        # Common fields
        common_fields = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "tags": task.tags,
            "assignees": task.assignees,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "metadata": task.metadata,
        }

        # Create appropriate model
        if task_type == "pr":
            return PRModel(
                **common_fields,
                status=PRStatus.DRAFT,  # Default status
                source_branch=task.metadata.get("source_branch", "feature"),
                target_branch=task.metadata.get("target_branch", "main"),
            )
        elif task_type == "issue":
            return IssueModel(
                **common_fields,
                status=IssueStatus.OPEN,
            )
        elif task_type == "bug":
            return BugModel(
                **common_fields,
                status=BugStatus.OPEN,
            )
        elif task_type == "epic":
            return EpicModel(
                **common_fields,
                status=EpicStatus.PLANNING,
            )
        else:
            return TaskModel(
                **common_fields,
                status=TaskStatus.OPEN,
            )
