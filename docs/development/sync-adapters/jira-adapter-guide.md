# JIRA Sync Adapter Guide

**Component**: JIRA Sync Adapter  
**Module**: `ai_trackdown_pytools.utils.sync.jira_adapter`  
**Purpose**: Enable bidirectional synchronization between AI Trackdown and JIRA

## Overview

The JIRA sync adapter provides seamless integration with Atlassian JIRA, allowing teams to:
- Pull issues from JIRA into AI Trackdown
- Push AI Trackdown tickets to JIRA
- Keep both systems synchronized
- Map fields, statuses, and priorities between systems
- Support custom fields and JQL queries

## Installation

The JIRA adapter requires the official `jira` Python library:

```bash
pip install ai-trackdown-pytools[jira]
# or
pip install jira>=3.5.0
```

## Configuration

### Basic Configuration

```python
from ai_trackdown_pytools.utils.sync import SyncConfig, get_adapter

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
```

### Authentication

The JIRA adapter supports API token authentication (recommended for JIRA Cloud):

1. **Generate API Token**:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Copy the generated token

2. **Environment Variables** (optional):
   ```bash
   export JIRA_SERVER="https://your-domain.atlassian.net"
   export JIRA_EMAIL="your-email@example.com"
   export JIRA_API_TOKEN="your-api-token"
   ```

3. **Configuration Options**:
   - `server`: JIRA instance URL (required)
   - `email`: Your JIRA account email (required)
   - `api_token`: API token for authentication (required)
   - `project_key`: Default project for creating issues (required)

### Advanced Configuration

```python
config = SyncConfig(
    platform="jira",
    auth_config={
        "server": "https://your-domain.atlassian.net",
        "email": "your-email@example.com",
        "api_token": "your-api-token",
        "project_key": "PROJ",
        
        # Optional: JQL filter for pulling issues
        "jql_filter": 'labels in ("ai-trackdown") AND resolution = Unresolved',
        
        # Optional: Custom issue type mapping
        "type_mapping": {
            "task": "Story",      # TaskModel -> Story issue type
            "bug": "Bug",         # BugModel -> Bug issue type
            "epic": "Epic",       # EpicModel -> Epic issue type
            "issue": "Task",      # IssueModel -> Task issue type
        }
    },
    
    # Sync options
    sync_tags=True,           # Sync labels
    sync_assignees=True,      # Sync assignees
    sync_comments=False,      # Sync comments (requires extra API calls)
    sync_attachments=False,   # Sync attachments
    
    # Field mappings
    label_mapping={
        "frontend": "ui",     # Map AI Trackdown tags to JIRA labels
        "backend": "api",
        "urgent": "high-priority",
    },
    
    status_mapping={
        "open": "To Do",      # Map AI Trackdown status to JIRA status
        "in_progress": "In Development",
        "completed": "Done",
    },
    
    # Type filtering
    included_types={"task", "bug"},  # Only sync these types
    
    # Performance
    batch_size=50,            # Items per request
    timeout=60,               # Request timeout in seconds
)
```

## Usage Examples

### Pull Issues from JIRA

```python
import asyncio
from datetime import datetime, timedelta

async def pull_jira_issues():
    adapter = get_adapter("jira", config)
    await adapter.authenticate()
    
    # Pull all issues
    all_items = await adapter.pull_items()
    
    # Pull issues updated in last 7 days
    since = datetime.now() - timedelta(days=7)
    recent_items = await adapter.pull_items(since=since)
    
    for item in recent_items:
        print(f"{item.id}: {item.title} ({item.status})")
        print(f"  Type: {type(item).__name__}")
        print(f"  Tags: {', '.join(item.tags)}")
        print(f"  JIRA Key: {item.metadata['jira_key']}")

asyncio.run(pull_jira_issues())
```

### Create Issues in JIRA

```python
from ai_trackdown_pytools.core.models import TaskModel, BugModel, Priority

async def create_jira_issues():
    adapter = get_adapter("jira", config)
    await adapter.authenticate()
    
    # Create a task
    task = TaskModel(
        id="TASK-001",
        title="Implement user authentication",
        description="Add OAuth2 authentication to the API",
        status=TaskStatus.OPEN,
        priority=Priority.HIGH,
        tags=["security", "api", "backend"],
        assignees=["developer@example.com"],
        due_date=date.today() + timedelta(days=14),
        estimated_hours=16.0,
    )
    
    result = await adapter.push_item(task)
    print(f"Created JIRA issue: {result['remote_key']}")
    print(f"URL: {result['remote_url']}")
    
    # Create a bug with custom fields
    bug = BugModel(
        id="BUG-001",
        title="Memory leak in data processing",
        description="Application consumes excessive memory when processing large datasets",
        severity="critical",
        status=TaskStatus.OPEN,
        reproduction_steps="1. Upload 1GB CSV file\n2. Start processing\n3. Monitor memory usage",
        metadata={
            "jira_custom_fields": {
                "Customer Impact": "High",
                "Environment": "Production",
                "Affected Version": "2.1.0",
            }
        }
    )
    
    bug_result = await adapter.push_item(bug)
    print(f"Created bug: {bug_result['remote_key']}")

asyncio.run(create_jira_issues())
```

### Update Existing Issues

```python
async def update_jira_issue():
    adapter = get_adapter("jira", config)
    await adapter.authenticate()
    
    # Get existing issue
    item = await adapter.get_item("PROJ-123")
    
    if item:
        # Update fields
        item.title = "Updated: " + item.title
        item.status = TaskStatus.IN_PROGRESS
        item.priority = Priority.CRITICAL
        item.tags.append("updated")
        
        # Push update
        result = await adapter.update_item(item, "PROJ-123")
        print(f"Updated issue: {result['remote_key']}")

asyncio.run(update_jira_issue())
```

### Bulk Synchronization

```python
async def bulk_sync():
    from ai_trackdown_pytools.utils.sync.base import SyncResult
    
    adapter = get_adapter("jira", config)
    await adapter.authenticate()
    
    # Track sync results
    sync_result = SyncResult(
        platform="jira",
        direction=SyncDirection.PUSH,
        started_at=datetime.now(),
    )
    
    # Get local items to sync
    local_items = get_local_items_to_sync()  # Your implementation
    
    for item in local_items:
        try:
            # Check if item exists in JIRA
            jira_key = item.metadata.get("jira_key")
            
            if jira_key:
                # Update existing
                result = await adapter.update_item(item, jira_key)
                sync_result.items_updated += 1
                sync_result.updated_ids.append((item.id, jira_key))
            else:
                # Create new
                result = await adapter.push_item(item)
                sync_result.items_created += 1
                sync_result.created_ids.append((item.id, result['remote_key']))
                
                # Store JIRA key for future syncs
                item.metadata["jira_key"] = result['remote_key']
                save_item(item)  # Your implementation
                
        except Exception as e:
            sync_result.add_error(item.id, e)
    
    sync_result.completed_at = datetime.now()
    print(f"Sync completed: {sync_result.items_created} created, {sync_result.items_updated} updated")

asyncio.run(bulk_sync())
```

## Field Mappings

### Status Mapping

| AI Trackdown Status | JIRA Status (Default) |
|--------------------|-----------------------|
| `TaskStatus.OPEN` | "To Do" |
| `TaskStatus.IN_PROGRESS` | "In Progress" |
| `TaskStatus.COMPLETED` | "Done" |
| `TaskStatus.CANCELLED` | "Won't Do" |
| `TaskStatus.BLOCKED` | "Blocked" |

### Priority Mapping

| AI Trackdown Priority | JIRA Priority |
|----------------------|---------------|
| `Priority.CRITICAL` | "Highest" |
| `Priority.HIGH` | "High" |
| `Priority.MEDIUM` | "Medium" |
| `Priority.LOW` | "Low" |

### Issue Type Mapping

| AI Trackdown Model | JIRA Issue Type (Default) |
|-------------------|---------------------------|
| `TaskModel` | "Task" |
| `IssueModel` | "Task" |
| `BugModel` | "Bug" |
| `EpicModel` | "Epic" |

## Custom Fields

The JIRA adapter automatically discovers custom fields in your JIRA instance. To use custom fields:

```python
# When creating/updating items
item = TaskModel(
    title="Task with custom fields",
    metadata={
        "jira_custom_fields": {
            "Sprint": "Sprint 23",
            "Story Points": 5,
            "Customer": "ACME Corp",
            "Custom Dropdown": "Option A",
        }
    }
)

# Custom fields are preserved when pulling from JIRA
pulled_item = await adapter.get_item("PROJ-123")
custom_fields = pulled_item.metadata.get("jira_custom_fields", {})
print(f"Sprint: {custom_fields.get('Sprint')}")
```

## JQL Filtering

Use JQL (JIRA Query Language) to filter which issues are synchronized:

```python
config = SyncConfig(
    platform="jira",
    auth_config={
        # ... other config ...
        "jql_filter": """
            project = PROJ 
            AND type in (Task, Bug) 
            AND (
                labels in ("ai-trackdown") 
                OR component = "AI Features"
            )
            AND resolution = Unresolved
            ORDER BY priority DESC, created DESC
        """
    }
)
```

Common JQL examples:
- `assignee = currentUser()` - Issues assigned to the authenticated user
- `updated >= -7d` - Issues updated in the last 7 days
- `priority in (Highest, High) AND status != Done` - High priority incomplete issues
- `"Epic Link" = PROJ-100` - Issues in a specific epic

## Error Handling

```python
from ai_trackdown_pytools.utils.sync.exceptions import (
    AuthenticationError,
    ConnectionError,
    RateLimitError,
    ValidationError,
)

async def sync_with_error_handling():
    try:
        adapter = get_adapter("jira", config)
        await adapter.authenticate()
        items = await adapter.pull_items()
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        # Check API token and email
        
    except ConnectionError as e:
        print(f"Connection error: {e}")
        # Check server URL and network
        
    except RateLimitError as e:
        print(f"Rate limit hit. Retry after {e.retry_after} seconds")
        await asyncio.sleep(e.retry_after)
        # Retry operation
        
    except ValidationError as e:
        print(f"Validation error: {e}")
        if e.field_errors:
            for field, error in e.field_errors.items():
                print(f"  {field}: {error}")
```

## Performance Considerations

1. **Batch Operations**: Use `batch_size` in config to control pagination
2. **JQL Optimization**: Use specific JQL queries to reduce data transfer
3. **Field Selection**: JIRA adapter uses `expand` parameter efficiently
4. **Rate Limiting**: JIRA typically allows 50-100 requests per minute
5. **Async Operations**: All operations are async-compatible for better performance

## Limitations

1. **Single Assignee**: JIRA supports only one assignee per issue (uses first from list)
2. **Status Transitions**: Status changes must follow JIRA workflow rules
3. **Field Validation**: JIRA has strict field validation (e.g., summary max 255 chars)
4. **Permissions**: Operations require appropriate JIRA permissions
5. **Attachments**: Attachment sync requires additional configuration

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Verify email and API token are correct
   - Ensure API token hasn't expired
   - Check JIRA instance allows API token auth

2. **404 Project Not Found**
   - Verify project key is correct
   - Ensure user has access to the project
   - Check for typos in project key

3. **400 Field Validation Error**
   - Check field values meet JIRA requirements
   - Verify custom field names are correct
   - Ensure required fields are provided

4. **429 Rate Limit Exceeded**
   - Implement exponential backoff
   - Reduce batch size
   - Add delays between requests

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ai_trackdown_pytools.utils.sync.jira_adapter")
```

## Best Practices

1. **Use Environment Variables**: Store credentials securely
2. **Filter with JQL**: Reduce data transfer with specific queries
3. **Map Fields Appropriately**: Configure field mappings for your workflow
4. **Handle Errors Gracefully**: Implement proper error handling
5. **Test with Dry Run**: Use `dry_run=True` to test without making changes
6. **Monitor Rate Limits**: Implement backoff strategies
7. **Cache Custom Fields**: The adapter caches field discovery per session
8. **Use Batch Operations**: Process multiple items efficiently
9. **Validate Before Push**: Check field requirements before creating issues
10. **Store JIRA Keys**: Save JIRA keys in metadata for future updates