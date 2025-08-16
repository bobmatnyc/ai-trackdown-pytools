#!/usr/bin/env python3
"""Example script demonstrating ClickUp sync adapter usage.

This script shows how to:
1. Configure the ClickUp adapter
2. Pull tasks from ClickUp
3. Create a new task in ClickUp
4. Update an existing task
"""

import asyncio
import os
from datetime import datetime, date

from ai_trackdown_pytools.utils.sync import (
    SyncConfig,
    SyncDirection,
    get_adapter,
)
from ai_trackdown_pytools.core.models import TaskModel, TaskStatus, Priority


async def main():
    """Run ClickUp sync example."""
    
    # Configuration
    # You can set these as environment variables:
    # export CLICKUP_API_TOKEN="your_token"
    # export CLICKUP_LIST_ID="your_list_id"
    
    api_token = os.getenv("CLICKUP_API_TOKEN")
    list_id = os.getenv("CLICKUP_LIST_ID")
    
    if not api_token or not list_id:
        print("Please set CLICKUP_API_TOKEN and CLICKUP_LIST_ID environment variables")
        return
    
    # Create sync configuration
    config = SyncConfig(
        platform="clickup",
        direction=SyncDirection.BIDIRECTIONAL,
        auth_config={
            "api_token": api_token,
            "list_id": list_id,
        },
        sync_tags=True,
        sync_assignees=True,
        batch_size=50,
    )
    
    # Get ClickUp adapter
    adapter = get_adapter("clickup", config)
    
    try:
        # 1. Authenticate
        print("Authenticating with ClickUp...")
        await adapter.authenticate()
        print("✓ Authentication successful")
        
        # 2. Test connection
        print("\nTesting connection...")
        if await adapter.test_connection():
            print("✓ Connection successful")
        
        # 3. Pull existing tasks
        print("\nPulling tasks from ClickUp...")
        tasks = await adapter.pull_items()
        print(f"✓ Found {len(tasks)} tasks")
        
        # Display first few tasks
        for task in tasks[:3]:
            print(f"  - {task.id}: {task.title} [{task.status.value}]")
        
        # 4. Create a new task
        print("\nCreating a new task...")
        new_task = TaskModel(
            id="TSK-DEMO-001",
            title="Demo Task from AI Trackdown",
            description="This task was created using the AI Trackdown ClickUp adapter",
            status=TaskStatus.OPEN,
            priority=Priority.MEDIUM,
            tags=["demo", "ai-trackdown"],
            assignees=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            due_date=date.today(),
            estimated_hours=3.0,
        )
        
        result = await adapter.push_item(new_task)
        remote_id = result["remote_id"]
        print(f"✓ Created task with ID: {remote_id}")
        print(f"  URL: {result.get('remote_url', 'N/A')}")
        
        # 5. Update the task
        print("\nUpdating the task...")
        new_task.status = TaskStatus.IN_PROGRESS
        new_task.priority = Priority.HIGH
        new_task.title = "Updated: " + new_task.title
        
        await adapter.update_item(new_task, remote_id)
        print("✓ Task updated successfully")
        
        # 6. Retrieve the updated task
        print("\nRetrieving updated task...")
        updated_task = await adapter.get_item(remote_id)
        if updated_task:
            print(f"✓ Retrieved: {updated_task.title}")
            print(f"  Status: {updated_task.status.value}")
            print(f"  Priority: {updated_task.priority.value}")
        
        # 7. Optional: Delete the demo task
        if input("\nDelete the demo task? (y/N): ").lower() == "y":
            await adapter.delete_item(remote_id)
            print("✓ Task deleted")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
    finally:
        # Clean up
        await adapter.close()
        print("\n✓ Connection closed")


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())