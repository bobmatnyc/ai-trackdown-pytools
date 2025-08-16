#!/usr/bin/env python3
"""Example of using the Linear sync adapter.

This example demonstrates how to:
1. Configure the Linear adapter
2. Authenticate with Linear
3. Pull issues from Linear
4. Create a new issue in Linear
5. Update an existing issue
"""

import asyncio
import os
from datetime import datetime

from ai_trackdown_pytools.core.models import TaskModel, TaskStatus, Priority
from ai_trackdown_pytools.utils.sync import SyncConfig, SyncDirection
from ai_trackdown_pytools.utils.sync.linear_adapter import LinearAdapter


async def main():
    """Run Linear sync example."""
    # Configure the adapter
    config = SyncConfig(
        platform="linear",
        direction=SyncDirection.BIDIRECTIONAL,
        auth_config={
            "api_key": os.getenv("LINEAR_API_KEY"),  # Set this environment variable
            "team_id": os.getenv("LINEAR_TEAM_ID"),  # Set this environment variable
            "project_id": os.getenv("LINEAR_PROJECT_ID"),  # Optional
        },
        batch_size=50,
        sync_tags=True,
        sync_assignees=True,
    )
    
    # Create adapter instance
    adapter = LinearAdapter(config)
    
    try:
        # 1. Authenticate with Linear
        print("Authenticating with Linear...")
        await adapter.authenticate()
        print("✓ Authentication successful")
        
        # 2. Test connection
        print("\nTesting connection...")
        connected = await adapter.test_connection()
        print(f"✓ Connection test: {'successful' if connected else 'failed'}")
        
        # 3. Pull recent issues from Linear
        print("\nPulling issues from Linear...")
        items = await adapter.pull_items(since=datetime(2024, 1, 1))
        print(f"✓ Found {len(items)} issues")
        
        # Display some issues
        for item in items[:5]:  # Show first 5
            print(f"  - {item.id}: {item.title} ({item.status.value})")
        
        # 4. Create a new task
        print("\nCreating a new task in Linear...")
        new_task = TaskModel(
            id="TASK-EXAMPLE-001",
            title="Example Task from AI Trackdown",
            description="This task was created using the Linear sync adapter",
            status=TaskStatus.OPEN,
            priority=Priority.MEDIUM,
            tags=["example", "sync-test"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        result = await adapter.push_item(new_task)
        print(f"✓ Created issue: {result.get('linear_identifier')} - {result.get('remote_url')}")
        linear_id = result.get('remote_id')
        
        # 5. Update the task
        print("\nUpdating the task...")
        new_task.title = "Updated Example Task"
        new_task.status = TaskStatus.IN_PROGRESS
        new_task.priority = Priority.HIGH
        
        update_result = await adapter.update_item(new_task, linear_id)
        print(f"✓ Updated issue: {update_result.get('linear_identifier')}")
        
        # 6. Retrieve the specific issue
        print("\nRetrieving the created issue...")
        retrieved = await adapter.get_item(linear_id)
        if retrieved:
            print(f"✓ Retrieved: {retrieved.title} (Status: {retrieved.status.value})")
        
        # 7. Archive the task (Linear doesn't support hard delete)
        print("\nArchiving the task...")
        await adapter.delete_item(linear_id)
        print("✓ Task archived")
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        
    finally:
        # Clean up
        await adapter.close()
        print("\n✓ Adapter closed")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())