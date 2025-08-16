#!/usr/bin/env python3
"""Example usage of JIRA sync adapter.

This example demonstrates how to use the JIRA sync adapter to:
1. Connect to a JIRA instance
2. Pull issues from JIRA
3. Create new issues in JIRA
4. Update existing issues
5. Handle custom fields and JQL queries
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List

from ai_trackdown_pytools.core.models import (
    TaskModel,
    IssueModel,
    BugModel,
    TaskStatus,
    Priority,
)
from ai_trackdown_pytools.utils.sync import (
    SyncConfig,
    SyncDirection,
    get_adapter,
)


async def basic_jira_sync():
    """Basic JIRA synchronization example.
    
    This example shows the minimal configuration needed to sync with JIRA.
    """
    # Configure JIRA connection
    config = SyncConfig(
        platform="jira",
        direction=SyncDirection.BIDIRECTIONAL,
        auth_config={
            "server": "https://your-domain.atlassian.net",
            "email": "your-email@example.com",
            "api_token": "your-api-token",  # Generate from Atlassian account settings
            "project_key": "PROJ",
        }
    )
    
    # Get JIRA adapter
    adapter = get_adapter("jira", config)
    
    # Authenticate
    await adapter.authenticate()
    print("Connected to JIRA successfully!")
    
    # Test connection
    if await adapter.test_connection():
        print(f"Successfully accessed project: {config.auth_config['project_key']}")
    
    # Pull recent issues (last 7 days)
    since = datetime.now() - timedelta(days=7)
    items = await adapter.pull_items(since=since)
    
    print(f"\nFound {len(items)} items updated in the last 7 days:")
    for item in items[:5]:  # Show first 5
        print(f"  - {item.id}: {item.title} ({item.status})")
    
    # Create a new task
    new_task = TaskModel(
        id="LOCAL-001",
        title="Implement new feature",
        description="This task was created via AI Trackdown sync",
        status=TaskStatus.OPEN,
        priority=Priority.HIGH,
        tags=["feature", "api", "backend"],
        assignees=["developer@example.com"],
        estimated_hours=8.0,
    )
    
    result = await adapter.push_item(new_task)
    print(f"\nCreated JIRA issue: {result['remote_key']}")
    print(f"URL: {result['remote_url']}")
    
    # Close connection
    await adapter.close()


async def advanced_jira_sync():
    """Advanced JIRA synchronization with custom configuration.
    
    This example demonstrates:
    - Custom JQL filtering
    - Status and label mapping
    - Custom field handling
    - Different issue types
    """
    # Advanced configuration
    config = SyncConfig(
        platform="jira",
        direction=SyncDirection.BIDIRECTIONAL,
        auth_config={
            "server": os.getenv("JIRA_SERVER", "https://your-domain.atlassian.net"),
            "email": os.getenv("JIRA_EMAIL"),
            "api_token": os.getenv("JIRA_API_TOKEN"),
            "project_key": "PROJ",
            # Custom JQL filter to limit which issues are synced
            "jql_filter": 'labels in ("ai-trackdown") AND resolution = Unresolved',
            # Custom issue type mapping
            "type_mapping": {
                "task": "Story",
                "bug": "Bug",
                "epic": "Epic",
                "issue": "Task",
            }
        },
        # Configure what to sync
        sync_tags=True,
        sync_assignees=True,
        sync_comments=False,  # Comments require additional API calls
        sync_attachments=False,
        
        # Map labels between systems
        label_mapping={
            "frontend": "ui",
            "backend": "api",
            "urgent": "high-priority",
        },
        
        # Map statuses
        status_mapping={
            "open": "To Do",
            "in_progress": "In Development",
            "completed": "Done",
            "blocked": "On Hold",
        },
        
        # Only sync specific types
        included_types={"task", "bug"},
        
        # Performance settings
        batch_size=100,
        timeout=60,
    )
    
    adapter = get_adapter("jira", config)
    await adapter.authenticate()
    
    # Pull items with custom filtering
    items = await adapter.pull_items()
    
    # Group by type
    tasks = [i for i in items if isinstance(i, TaskModel)]
    bugs = [i for i in items if isinstance(i, BugModel)]
    
    print(f"Found {len(tasks)} tasks and {len(bugs)} bugs")
    
    # Create a bug with custom fields
    bug = BugModel(
        id="BUG-001",
        title="Critical API error in production",
        description="The API returns 500 errors when processing large payloads",
        severity="critical",
        status=TaskStatus.OPEN,
        tags=["api", "production", "urgent"],
        assignees=["senior-dev@example.com"],
        reproduction_steps="""
        1. Send POST request to /api/process with >10MB payload
        2. Observe 500 error response
        3. Check server logs for memory errors
        """,
        metadata={
            # Custom JIRA fields
            "jira_custom_fields": {
                "Customer Impact": "High",
                "Environment": "Production",
                "Affected Version": "2.1.0",
            }
        }
    )
    
    result = await adapter.push_item(bug)
    print(f"\nCreated bug: {result['remote_key']}")
    
    # Update the bug status
    bug.status = TaskStatus.IN_PROGRESS
    await adapter.update_item(bug, result['remote_key'])
    print(f"Updated bug status to: {bug.status}")
    
    await adapter.close()


async def sync_with_error_handling():
    """Example showing proper error handling for JIRA sync.
    
    Demonstrates handling of common errors:
    - Authentication failures
    - Network issues
    - Rate limiting
    - Validation errors
    """
    from ai_trackdown_pytools.utils.sync.exceptions import (
        AuthenticationError,
        ConnectionError,
        RateLimitError,
        ValidationError,
    )
    
    config = SyncConfig(
        platform="jira",
        auth_config={
            "server": "https://your-domain.atlassian.net",
            "email": "your-email@example.com",
            "api_token": "your-api-token",
            "project_key": "PROJ",
        }
    )
    
    adapter = get_adapter("jira", config)
    
    try:
        # Authenticate
        await adapter.authenticate()
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        print("Please check your email and API token")
        return
        
    except ConnectionError as e:
        print(f"Connection failed: {e}")
        print("Please check your server URL and network connection")
        return
    
    # Pull items with error handling
    try:
        items = await adapter.pull_items()
        print(f"Successfully pulled {len(items)} items")
        
    except RateLimitError as e:
        print(f"Rate limit exceeded. Retry after {e.retry_after} seconds")
        # Could implement exponential backoff here
        await asyncio.sleep(e.retry_after)
        items = await adapter.pull_items()  # Retry
        
    except Exception as e:
        print(f"Unexpected error during pull: {e}")
        return
    
    # Create item with validation error handling
    task = TaskModel(
        id="TASK-001",
        title="A" * 300,  # Too long for JIRA
        description="Test task",
        status=TaskStatus.OPEN,
    )
    
    try:
        result = await adapter.push_item(task)
        
    except ValidationError as e:
        print(f"Validation error: {e}")
        if e.field_errors:
            print("Field errors:", e.field_errors)
        
        # Fix the issue and retry
        task.title = task.title[:255]  # JIRA limit
        result = await adapter.push_item(task)
        print(f"Created after fixing: {result['remote_key']}")
    
    await adapter.close()


async def bulk_sync_example():
    """Example of bulk synchronization between AI Trackdown and JIRA.
    
    This shows how to sync many items efficiently.
    """
    from ai_trackdown_pytools.utils.sync.base import SyncResult
    
    config = SyncConfig(
        platform="jira",
        auth_config={
            "server": "https://your-domain.atlassian.net",
            "email": "your-email@example.com",
            "api_token": "your-api-token",
            "project_key": "PROJ",
        },
        dry_run=False,  # Set to True to test without making changes
        batch_size=50,  # Process in batches
    )
    
    adapter = get_adapter("jira", config)
    await adapter.authenticate()
    
    # Initialize sync result tracking
    sync_result = SyncResult(
        platform="jira",
        direction=SyncDirection.PUSH,
        started_at=datetime.now(),
    )
    
    # Get local items to sync (mock data for example)
    local_items = [
        TaskModel(
            id=f"TASK-{i:03d}",
            title=f"Task {i}: Implement feature {i}",
            description=f"Description for task {i}",
            status=TaskStatus.OPEN if i % 3 == 0 else TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH if i % 5 == 0 else Priority.MEDIUM,
            tags=["bulk-sync", "example"],
        )
        for i in range(1, 11)  # Create 10 tasks
    ]
    
    # Process items in batches
    for i in range(0, len(local_items), config.batch_size):
        batch = local_items[i:i + config.batch_size]
        
        for item in batch:
            try:
                result = await adapter.push_item(item)
                sync_result.items_created += 1
                sync_result.created_ids.append((item.id, result['remote_key']))
                print(f"Created: {item.id} -> {result['remote_key']}")
                
            except Exception as e:
                sync_result.add_error(item.id, e)
                print(f"Failed: {item.id} - {e}")
        
        # Small delay to avoid rate limits
        await asyncio.sleep(1)
    
    # Mark sync as complete
    sync_result.completed_at = datetime.now()
    sync_result.items_processed = len(local_items)
    
    # Print summary
    print(f"\nSync completed in {sync_result.duration:.2f} seconds")
    print(f"Created: {sync_result.items_created}")
    print(f"Failed: {sync_result.items_failed}")
    
    if sync_result.errors:
        print("\nErrors:")
        for error in sync_result.errors:
            print(f"  - {error['item_id']}: {error['error_message']}")
    
    await adapter.close()


if __name__ == "__main__":
    # Run the examples
    print("=== Basic JIRA Sync Example ===")
    # asyncio.run(basic_jira_sync())
    
    print("\n=== Advanced JIRA Sync Example ===")
    # asyncio.run(advanced_jira_sync())
    
    print("\n=== Error Handling Example ===")
    # asyncio.run(sync_with_error_handling())
    
    print("\n=== Bulk Sync Example ===")
    # asyncio.run(bulk_sync_example())
    
    print("\nUncomment the examples you want to run!")