# ClickUp Sync Configuration Guide

This guide covers ClickUp-specific configuration and usage for the sync adapter system.

## Prerequisites

- ClickUp account with workspace access
- ClickUp API token
- List ID where tasks will be synced

## Quick Start

```bash
# Configure ClickUp
aitrackdown sync config clickup --key token --value pk_xxxxxxxxxxxxx
aitrackdown sync config clickup --key list_id --value 123456789

# Test connection
aitrackdown sync platform clickup status

# Start syncing
aitrackdown sync platform clickup pull
```

## Getting ClickUp Credentials

### 1. Generate API Token

1. Go to ClickUp Settings (bottom left corner)
2. Navigate to "Apps" or "Integrations"
3. Find "ClickUp API" section
4. Click "Generate Personal Token"
5. Copy the token (starts with `pk_`)

### 2. Find List ID

1. Navigate to the List you want to sync
2. Look at the URL: `https://app.clickup.com/12345678/v/li/987654321`
   - `12345678` is your workspace ID
   - `987654321` is your list ID

Or use the API:

```bash
# Get workspaces
curl -H "Authorization: pk_xxxxx" https://api.clickup.com/api/v2/team

# Get spaces in workspace
curl -H "Authorization: pk_xxxxx" https://api.clickup.com/api/v2/team/12345678/space

# Get lists in space
curl -H "Authorization: pk_xxxxx" https://api.clickup.com/api/v2/space/98765/list
```

## Configuration Options

### Required Configuration

| Key | Description | Example |
|-----|-------------|---------|
| `token` | ClickUp API token | `pk_12345678_ABCDEFGHIJKLMNOP` |
| `list_id` | List ID for syncing tasks | `123456789` |

### Optional Configuration

| Key | Description | Default | Example |
|-----|-------------|---------|---------|
| `workspace_id` | Workspace ID | Auto-detected | `12345678` |
| `space_id` | Space ID | Auto-detected | `90123456` |
| `batch_size` | Items per request | `50` | `100` |
| `timeout` | Request timeout (seconds) | `30` | `60` |
| `include_subtasks` | Sync subtasks | `false` | `true` |
| `include_closed` | Sync closed tasks | `false` | `true` |

### Full Configuration Example

```json
{
  "clickup": {
    "token": "pk_12345678_ABCDEFGHIJKLMNOP",
    "list_id": "123456789",
    "workspace_id": "12345678",
    "space_id": "90123456",
    "batch_size": 100,
    "timeout": 60,
    "include_subtasks": true,
    "include_closed": false,
    "status_mapping": {
      "open": "to do",
      "in_progress": "in progress",
      "completed": "complete",
      "cancelled": "closed"
    },
    "priority_mapping": {
      "critical": "urgent",
      "high": "high",
      "medium": "normal",
      "low": "low"
    }
  }
}
```

## Supported Item Types

ClickUp adapter supports:

- **Tasks** - ClickUp Tasks
- **Issues** - Tasks tagged as issues

## ClickUp-Specific Features

### Priority Levels

ClickUp uses a 1-4 priority system:

| AI Trackdown | ClickUp | ClickUp UI |
|--------------|---------|------------|
| `critical` | 1 | Urgent (red) |
| `high` | 2 | High (yellow) |
| `medium` | 3 | Normal (blue) |
| `low` | 4 | Low (gray) |

### Status Management

ClickUp statuses are customizable per list. Default mapping:

```bash
# Configure custom status mapping
aitrackdown sync config clickup --key status_mapping --value '{
  "open": "TO DO",
  "in_progress": "IN PROGRESS", 
  "in_review": "REVIEW",
  "completed": "COMPLETE",
  "cancelled": "CLOSED"
}'
```

### Custom Fields

ClickUp custom fields are preserved in metadata:

```json
{
  "metadata": {
    "clickup_custom_fields": {
      "Estimated Hours": 8,
      "Department": "Engineering",
      "Sprint": "Sprint 23"
    }
  }
}
```

## Usage Examples

### Basic Workflow

```bash
# 1. Configure ClickUp
aitrackdown sync config clickup --key token --value pk_xxxxx
aitrackdown sync config clickup --key list_id --value 123456789

# 2. Pull existing tasks
aitrackdown sync platform clickup pull

# 3. Create new tasks
aitrackdown create "Update API documentation" --type task --priority high
aitrackdown create "Fix memory leak" --type issue --priority critical

# 4. Push to ClickUp
aitrackdown sync platform clickup push --dry-run
aitrackdown sync platform clickup push
```

### Working with ClickUp Lists

```bash
# Sync from specific list
aitrackdown sync config clickup --key list_id --value 123456789
aitrackdown sync platform clickup pull

# Switch to different list
aitrackdown sync config clickup --key list_id --value 987654321
aitrackdown sync platform clickup pull
```

### Using Tags

ClickUp tags sync with AI Trackdown tags:

```bash
# Create task with tags
aitrackdown create "Implement caching" \
  --tags backend performance \
  --priority high

# After sync, task will have these tags in ClickUp
```

### Time Tracking

```bash
# Create task with time estimate
aitrackdown create "Database optimization" \
  --type task \
  --metadata '{"estimated_hours": 16}'

# This maps to ClickUp's time estimate field
```

## Field Mappings

### From ClickUp to AI Trackdown

| ClickUp Field | AI Trackdown Field | Notes |
|---------------|-------------------|-------|
| `name` | `title` | Task name |
| `description` | `description` | Supports markdown |
| `status` | `status` | Mapped via configuration |
| `priority` | `priority` | 1-4 scale mapped |
| `tags` | `tags` | Direct mapping |
| `assignees` | `assignees` | Email addresses |
| `date_created` | `created_at` | Converted to datetime |
| `date_updated` | `updated_at` | Converted to datetime |
| `due_date` | `metadata.due_date` | Stored as metadata |
| `time_estimate` | `metadata.estimated_hours` | Milliseconds to hours |
| `custom_fields` | `metadata.clickup_custom_fields` | All custom fields preserved |

### From AI Trackdown to ClickUp

| AI Trackdown Field | ClickUp Field | Notes |
|-------------------|---------------|-------|
| `title` | `name` | Direct mapping |
| `description` | `description` | Markdown supported |
| `status` | `status` | Must match list statuses |
| `priority` | `priority` | Mapped to 1-4 |
| `tags` | `tags` | Creates if needed |
| `assignees` | `assignees` | Requires user access |

## Advanced Features

### Subtask Handling

```bash
# Enable subtask syncing
aitrackdown sync config clickup --key include_subtasks --value true

# Subtasks appear as linked items
aitrackdown list --format tree
```

### Multiple Lists

Manage tasks across multiple ClickUp lists:

```bash
# Create configuration profiles
cat > .aitrackdown/clickup-lists.json << EOF
{
  "development": "123456789",
  "bugs": "987654321",
  "features": "456789123"
}
EOF

# Sync specific list
LIST_ID=$(jq -r '.bugs' .aitrackdown/clickup-lists.json)
aitrackdown sync config clickup --key list_id --value $LIST_ID
aitrackdown sync platform clickup pull
```

### Workspace Templates

Create consistent task templates:

```bash
# Create template task
aitrackdown create "Bug Report Template" \
  --type issue \
  --description "## Description\n\n## Steps to Reproduce\n\n## Expected Behavior\n\n## Actual Behavior" \
  --tags template bug \
  --metadata '{"clickup_template": true}'
```

## Troubleshooting

### Authentication Issues

**Problem**: "Invalid token" error

**Solutions**:
1. Verify token is correct:
   ```bash
   curl -H "Authorization: pk_xxxxx" https://api.clickup.com/api/v2/user
   ```

2. Regenerate token in ClickUp settings

3. Check token in configuration:
   ```bash
   aitrackdown sync config clickup --list
   ```

### List Not Found

**Problem**: "List not found" error

**Solutions**:
1. Verify list ID:
   ```bash
   # Get all accessible lists
   curl -H "Authorization: pk_xxxxx" \
     https://api.clickup.com/api/v2/team/WORKSPACE_ID/list
   ```

2. Check permissions for the list

3. Ensure list exists and is not archived

### Rate Limiting

**Problem**: "Rate limit exceeded" error

**Solutions**:
1. ClickUp allows 100 requests per minute
2. Reduce batch size:
   ```bash
   aitrackdown sync config clickup --key batch_size --value 25
   ```
3. Add delays between operations

### Status Mismatch

**Problem**: "Invalid status" error

**Solutions**:
1. Check available statuses for your list:
   ```bash
   curl -H "Authorization: pk_xxxxx" \
     https://api.clickup.com/api/v2/list/LIST_ID
   ```

2. Update status mapping:
   ```bash
   aitrackdown sync config clickup --key status_mapping --value '{
     "open": "YOUR_OPEN_STATUS",
     "in_progress": "YOUR_PROGRESS_STATUS"
   }'
   ```

## Best Practices

### 1. Organize with Spaces and Lists

Structure your ClickUp workspace:
```
Workspace
├── Development Space
│   ├── Sprint Tasks (list)
│   ├── Backlog (list)
│   └── Bugs (list)
└── Operations Space
    ├── Infrastructure (list)
    └── Incidents (list)
```

### 2. Use Custom Fields

Leverage ClickUp's custom fields:
```bash
# Sync with custom field data
aitrackdown create "Performance optimization" \
  --metadata '{
    "clickup_custom_fields": {
      "Sprint": "Sprint 24",
      "Story Points": 8,
      "Component": "Backend"
    }
  }'
```

### 3. Status Workflow

Align statuses with your workflow:
```bash
# Map to your custom statuses
aitrackdown sync config clickup --key status_mapping --value '{
  "open": "📋 Backlog",
  "in_progress": "🚧 In Development",
  "in_review": "👀 Code Review",
  "testing": "🧪 Testing",
  "completed": "✅ Done"
}'
```

### 4. Time Management

Track time effectively:
```bash
# Create task with time tracking
aitrackdown create "Refactor authentication module" \
  --metadata '{
    "estimated_hours": 20,
    "clickup_time_tracking": true
  }'
```

### 5. Automation Rules

Set up ClickUp automations that work with synced tasks:
- Auto-assign based on tags
- Move tasks between lists based on status
- Add watchers for specific priorities

## ClickUp-Specific Metadata

The adapter preserves ClickUp metadata:

```json
{
  "id": "TSK-001",
  "title": "Sample Task",
  "metadata": {
    "clickup_id": "abc123def",
    "clickup_url": "https://app.clickup.com/t/abc123def",
    "clickup_list_id": "123456789",
    "clickup_space_id": "90123456",
    "clickup_folder_id": "78901234",
    "clickup_status": {
      "status": "in progress",
      "color": "#4287f5",
      "type": "custom"
    },
    "clickup_creator": "user@example.com",
    "clickup_custom_fields": {
      "Sprint": "Sprint 24",
      "Department": "Engineering"
    },
    "platform": "clickup"
  }
}
```

## Integration Tips

### Webhooks (Future Feature)

ClickUp supports webhooks for real-time updates:
```bash
# Future: Configure webhook endpoint
aitrackdown sync config clickup --key webhook_url --value https://your-app.com/webhooks/clickup
```

### Multiple Workspaces

For managing multiple workspaces:
```bash
# Workspace 1
export CLICKUP_TOKEN=pk_workspace1_xxxxx
aitrackdown sync config clickup --key token --value $CLICKUP_TOKEN
aitrackdown sync config clickup --key list_id --value 123456789

# Workspace 2 (different project)
cd ../other-project
export CLICKUP_TOKEN=pk_workspace2_yyyyy
aitrackdown sync config clickup --key token --value $CLICKUP_TOKEN
aitrackdown sync config clickup --key list_id --value 987654321
```

### ClickUp Views

Synced tasks appear in all ClickUp views:
- List View
- Board View (Kanban)
- Calendar View
- Gantt View
- Timeline View

## Security Considerations

1. **Token Storage**: Store tokens securely
   ```bash
   # Use environment variable
   export CLICKUP_TOKEN=pk_xxxxx
   aitrackdown sync config clickup --key token --value $CLICKUP_TOKEN
   ```

2. **Permissions**: Token has full access to workspace
   - Be cautious with token distribution
   - Regularly rotate tokens

3. **Data Privacy**: 
   - Custom fields may contain sensitive data
   - Use workspace permissions appropriately

## Example Configurations

### Development Team

```json
{
  "clickup": {
    "token": "pk_xxxxx",
    "list_id": "123456789",
    "status_mapping": {
      "open": "Backlog",
      "in_progress": "In Development",
      "in_review": "Code Review",
      "testing": "QA Testing",
      "completed": "Done",
      "cancelled": "Won't Do"
    },
    "priority_mapping": {
      "critical": "urgent",
      "high": "high",
      "medium": "normal",
      "low": "low"
    },
    "include_subtasks": true
  }
}
```

### Bug Tracking

```json
{
  "clickup": {
    "token": "pk_xxxxx",
    "list_id": "987654321",
    "status_mapping": {
      "open": "New",
      "in_progress": "Investigating",
      "testing": "Validating Fix",
      "completed": "Resolved",
      "cancelled": "Not a Bug"
    },
    "include_closed": true,
    "batch_size": 100
  }
}
```

## Limitations

1. **Comments**: Read-only in current version
2. **Attachments**: Not synced
3. **Recurring Tasks**: Not fully supported
4. **Dependencies**: Basic support only
5. **Guest Users**: Limited permissions

## Future Enhancements

Planned features:

1. Two-way comment sync
2. Attachment support
3. Webhook integration
4. Custom field type detection
5. Dependency management
6. Time tracking integration
7. Multiple assignee support
8. ClickUp Dashboard integration