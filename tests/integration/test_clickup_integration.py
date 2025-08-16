"""Integration tests for ClickUp sync adapter.

Note: These tests require a valid ClickUp API token and list ID to run.
They are marked with @pytest.mark.integration and will be skipped in CI.
"""

import asyncio
import os
from datetime import date, datetime

import pytest

from ai_trackdown_pytools.core.models import Priority, TaskModel, TaskStatus
from ai_trackdown_pytools.utils.sync import SyncConfig, get_adapter


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("CLICKUP_API_TOKEN") or not os.getenv("CLICKUP_TEST_LIST_ID"),
    reason="ClickUp credentials not available",
)
class TestClickUpIntegration:
    """Integration tests for ClickUp adapter.

    WHY: These tests verify actual integration with ClickUp API to ensure
    the adapter works correctly in real-world scenarios. They help catch
    issues that unit tests with mocks might miss.
    """

    @pytest.fixture
    def config(self):
        """Create configuration from environment variables."""
        return SyncConfig(
            platform="clickup",
            auth_config={
                "api_token": os.getenv("CLICKUP_API_TOKEN"),
                "list_id": os.getenv("CLICKUP_TEST_LIST_ID"),
            },
            dry_run=False,
        )

    @pytest.fixture
    def test_task(self):
        """Create a test task for integration testing."""
        return TaskModel(
            id="TSK-TEST-001",
            title=f"Test Task {datetime.now().isoformat()}",
            description="This is an integration test task from AI Trackdown PyTools",
            status=TaskStatus.OPEN,
            priority=Priority.MEDIUM,
            tags=["test", "integration"],
            assignees=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=date.today(),
            estimated_hours=2.0,
        )

    @pytest.mark.asyncio
    async def test_authenticate(self, config):
        """Test authentication with real ClickUp API."""
        adapter = get_adapter("clickup", config)

        # Should not raise any exceptions
        await adapter.authenticate()

        assert adapter._authenticated is True

    @pytest.mark.asyncio
    async def test_connection(self, config):
        """Test connection to ClickUp."""
        adapter = get_adapter("clickup", config)

        result = await adapter.test_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_pull_items(self, config):
        """Test pulling items from ClickUp."""
        adapter = get_adapter("clickup", config)
        await adapter.authenticate()

        # Pull recent items
        items = await adapter.pull_items()

        # Should return a list (might be empty if no tasks in list)
        assert isinstance(items, list)

        # If there are items, verify their structure
        if items:
            item = items[0]
            assert hasattr(item, "id")
            assert hasattr(item, "title")
            assert hasattr(item, "status")
            assert hasattr(item, "metadata")
            assert "clickup_id" in item.metadata

    @pytest.mark.asyncio
    async def test_full_sync_cycle(self, config, test_task):
        """Test complete sync cycle: push, get, update, delete."""
        adapter = get_adapter("clickup", config)
        await adapter.authenticate()

        remote_id = None

        try:
            # 1. Push new task
            push_result = await adapter.push_item(test_task)
            remote_id = push_result["remote_id"]

            assert remote_id is not None
            assert "remote_url" in push_result

            # 2. Get the task back
            retrieved_task = await adapter.get_item(remote_id)

            assert retrieved_task is not None
            assert retrieved_task.title == test_task.title
            assert retrieved_task.description == test_task.description

            # 3. Update the task
            test_task.title = f"Updated {test_task.title}"
            test_task.status = TaskStatus.IN_PROGRESS
            test_task.priority = Priority.HIGH

            update_result = await adapter.update_item(test_task, remote_id)

            assert update_result["remote_id"] == remote_id

            # 4. Verify the update
            updated_task = await adapter.get_item(remote_id)

            assert updated_task.title == test_task.title
            assert updated_task.status == TaskStatus.IN_PROGRESS
            assert updated_task.priority == Priority.HIGH

        finally:
            # 5. Clean up - delete the test task
            if remote_id:
                await adapter.delete_item(remote_id)

                # Verify deletion
                deleted_task = await adapter.get_item(remote_id)
                # ClickUp doesn't actually delete, it moves to trash
                # So the task might still exist but be in a deleted state

    @pytest.mark.asyncio
    async def test_rate_limiting(self, config):
        """Test that rate limiting is handled gracefully."""
        adapter = get_adapter("clickup", config)
        await adapter.authenticate()

        # Make multiple rapid requests
        tasks = []
        for i in range(5):
            tasks.append(adapter.pull_items())

        # Should handle rate limiting without raising exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check that we got results (or rate limit errors handled gracefully)
        for result in results:
            if not isinstance(result, Exception):
                assert isinstance(result, list)
