# ClickUp Sync Adapter

The ClickUp sync adapter enables bidirectional synchronization between AI Trackdown PyTools and ClickUp, a popular project management platform.

## Features

- **Bidirectional Sync**: Pull tasks from ClickUp and push local tasks to ClickUp
- **Status Mapping**: Automatic mapping between AI Trackdown and ClickUp statuses
- **Priority Mapping**: Convert between AI Trackdown priorities and ClickUp priority levels
- **Rate Limiting**: Built-in rate limit handling with automatic retry
- **Custom Fields**: Preserves ClickUp custom fields in metadata
- **Flexible Task Types**: Supports both TaskModel and IssueModel

## Configuration

### Required Configuration

```json
{
  "platform": "clickup",
  "auth_config": {
    "api_token": "YOUR_CLICKUP_API_TOKEN",
    "list_id": "YOUR_LIST_ID"
  }
}
```

### Optional Configuration

```json
{
  "platform": "clickup",
  "direction": "bidirectional",
  "auth_config": {
    "api_token": "YOUR_CLICKUP_API_TOKEN",
    "list_id": "YOUR_LIST_ID",
    "space_id": "YOUR_SPACE_ID",
    "team_id": "YOUR_TEAM_ID"
  },
  "sync_tags": true,
  "sync_assignees": true,
  "sync_comments": false,
  "batch_size": 100,
  "timeout": 30
}
```

### Environment Variables

You can also provide the API token via environment variable:

```bash
export CLICKUP_API_TOKEN="pk_12345678_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
```

## Authentication

1. **Get API Token**:
   - Go to ClickUp Settings → Apps → API Token
   - Generate a personal API token
   - Copy and save the token securely

2. **Find List ID**:
   - Navigate to your ClickUp list
   - The URL will contain the list ID: `https://app.clickup.com/1234567/v/li/123456789`
   - In this example, `123456789` is the list ID

## Usage

### Command Line

```bash
# Pull tasks from ClickUp
aitrackdown sync platform clickup pull --config clickup-config.json

# Push tasks to ClickUp
aitrackdown sync platform clickup push --config clickup-config.json

# Check sync status
aitrackdown sync platform clickup status
```

### Programmatic Usage

```python
from ai_trackdown_pytools.utils.sync import SyncConfig, get_adapter
import asyncio

# Configure adapter
config = SyncConfig(
    platform="clickup",
    auth_config={
        "api_token": "your_token",
        "list_id": "your_list_id"
    }
)

# Get adapter instance
adapter = get_adapter("clickup", config)

# Pull tasks
async def pull_tasks():
    await adapter.authenticate()
    tasks = await adapter.pull_items()
    return tasks

# Run async function
tasks = asyncio.run(pull_tasks())
```

## Field Mappings

### Status Mapping

| AI Trackdown Status | ClickUp Status |
|-------------------|----------------|
| `OPEN` | `open` |
| `IN_PROGRESS` | `in progress` |
| `COMPLETED` | `complete` |
| `CANCELLED` | `closed` |
| `BLOCKED` | `blocked` |

### Priority Mapping

| AI Trackdown Priority | ClickUp Priority |
|---------------------|------------------|
| `CRITICAL` | 1 (Urgent) |
| `HIGH` | 2 (High) |
| `MEDIUM` | 3 (Normal) |
| `LOW` | 4 (Low) |

### Date Fields

- **Due Date**: Mapped between `due_date` and ClickUp's `due_date`
- **Created/Updated**: Automatically synced timestamps
- **Time Estimates**: `estimated_hours` ↔ `time_estimate` (converted between hours and milliseconds)
- **Time Tracking**: `actual_hours` ↔ `time_spent`

## Rate Limiting

ClickUp enforces the following rate limits:

- **Basic/Unlimited/Business**: 100 requests/minute/token
- **Business Plus**: 1,000 requests/minute/token
- **Enterprise**: 10,000 requests/minute/token

The adapter automatically:
- Tracks remaining requests from response headers
- Waits when approaching rate limits
- Handles 429 (Rate Limit) responses with exponential backoff
- Respects the `Retry-After` header

## Custom Fields

ClickUp custom fields are preserved in the task metadata:

```python
task.metadata["custom_fields"] = [
    {
        "id": "field_id",
        "name": "Sprint",
        "value": "Sprint 23"
    }
]
```

## Model Selection

The adapter automatically determines whether to use `TaskModel` or `IssueModel` based on tags:

- Tasks with "bug" or "issue" tags → `IssueModel`
- All other tasks → `TaskModel`

## Error Handling

The adapter provides specific exceptions for different error scenarios:

- `ConfigurationError`: Missing or invalid configuration
- `AuthenticationError`: Invalid API token
- `RateLimitError`: Rate limit exceeded (includes retry_after)
- `ConnectionError`: Network or API connectivity issues
- `ValidationError`: Data validation failures

## Limitations

1. **Assignee Sync**: Currently limited as ClickUp requires user IDs, not emails
2. **Comments**: Comment sync not yet implemented
3. **Attachments**: File attachments not yet supported
4. **Subtasks**: Subtask hierarchy not yet mapped
5. **Custom Status**: Only default statuses are mapped

## Troubleshooting

### Common Issues

1. **401 Unauthorized**:
   - Verify your API token is correct
   - Check if the token has been revoked
   - Ensure you're using the correct token format

2. **404 Not Found**:
   - Verify the list_id is correct
   - Check if you have access to the specified list
   - Ensure the list hasn't been deleted

3. **Rate Limit Errors**:
   - Reduce batch_size in configuration
   - Add delays between sync operations
   - Consider upgrading your ClickUp plan

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.getLogger("ai_trackdown_pytools.utils.sync.clickup_adapter").setLevel(logging.DEBUG)
```

## Future Enhancements

- Full assignee sync with user ID lookup
- Comment synchronization
- File attachment support
- Subtask hierarchy mapping
- Custom field mapping configuration
- Webhook support for real-time sync
- Bulk operations for better performance