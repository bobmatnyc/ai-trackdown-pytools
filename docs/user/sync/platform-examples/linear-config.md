# Linear Sync Configuration Guide

This guide covers Linear-specific configuration and usage for the sync adapter system.

## Prerequisites

- Linear account with workspace access
- Linear API key
- Team ID for syncing issues

## Quick Start

```bash
# Configure Linear
aitrackdown sync config linear --key token --value lin_api_xxxxxxxxxxxxx
aitrackdown sync config linear --key team_id --value TEAM-XXXX

# Test connection
aitrackdown sync platform linear status

# Start syncing
aitrackdown sync platform linear pull
```

## Getting Linear Credentials

### 1. Generate API Key

1. Go to Linear Settings (⚙️ icon → Settings)
2. Navigate to "API" under "My Account"
3. Click "Create new API key"
4. Give it a descriptive name (e.g., "AI Trackdown Sync")
5. Copy the key (starts with `lin_api_`)

### 2. Find Team ID

1. Go to Linear Settings → Teams
2. Click on your team
3. Find the team identifier (e.g., `ENG`, `PROD`, etc.)

Or use the API:

```bash
# Get your teams
curl -H "Authorization: lin_api_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ teams { nodes { id name key } } }"}' \
  https://api.linear.app/graphql
```

## Configuration Options

### Required Configuration

| Key | Description | Example |
|-----|-------------|---------|
| `token` | Linear API key | `lin_api_1234567890abcdef` |
| `team_id` | Team identifier | `ENG` or `abc-123-def` |

### Optional Configuration

| Key | Description | Default | Example |
|-----|-------------|---------|---------|
| `project_id` | Default project | None | `PRJ_12345` |
| `cycle_id` | Current cycle | None | `CYC_98765` |
| `include_archived` | Sync archived issues | `false` | `true` |
| `include_cancelled` | Sync cancelled issues | `false` | `true` |
| `batch_size` | Items per request | `50` | `100` |
| `timeout` | Request timeout (seconds) | `30` | `60` |

### Full Configuration Example

```json
{
  "linear": {
    "token": "lin_api_1234567890abcdef",
    "team_id": "ENG",
    "project_id": "PRJ_12345",
    "cycle_id": "CYC_98765",
    "include_archived": false,
    "include_cancelled": false,
    "batch_size": 50,
    "status_mapping": {
      "open": "Todo",
      "in_progress": "In Progress",
      "in_review": "In Review",
      "completed": "Done",
      "cancelled": "Canceled"
    },
    "priority_mapping": {
      "critical": 1,
      "high": 2,
      "medium": 3,
      "low": 4
    },
    "label_groups": {
      "Type": ["Bug", "Feature", "Task"],
      "Area": ["Frontend", "Backend", "DevOps"]
    }
  }
}
```

## Supported Item Types

Linear adapter supports:

- **Issues** - Linear Issues
- **Tasks** - Issues labeled as tasks
- **Bugs** - Issues with bug label or priority

## Linear-Specific Features

### Priority Levels

Linear uses a 0-4 priority system:

| AI Trackdown | Linear | Linear UI | Description |
|--------------|--------|-----------|-------------|
| None | 0 | No priority | No icon |
| `critical` | 1 | Urgent | 🔴 Red |
| `high` | 2 | High | 🟠 Orange |
| `medium` | 3 | Medium | 🟡 Yellow |
| `low` | 4 | Low | ⚪ Gray |

### Workflow States

Linear has customizable workflow states:

```bash
# Get available states for your team
curl -H "Authorization: lin_api_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ workflowStates(filter: { team: { key: { eq: \"ENG\" } } }) { nodes { id name type } } }"}' \
  https://api.linear.app/graphql

# Configure mapping
aitrackdown sync config linear --key status_mapping --value '{
  "open": "Todo",
  "in_progress": "In Progress",
  "in_review": "In Review",
  "testing": "QA",
  "completed": "Done"
}'
```

### Label System

Linear uses a structured label system:

```bash
# Configure label groups
aitrackdown sync config linear --key label_groups --value '{
  "Type": ["Bug", "Feature", "Improvement"],
  "Priority": ["P0", "P1", "P2"],
  "Area": ["Frontend", "Backend", "API"]
}'
```

## Usage Examples

### Basic Workflow

```bash
# 1. Configure Linear
aitrackdown sync config linear --key token --value lin_api_xxxxx
aitrackdown sync config linear --key team_id --value ENG

# 2. Pull existing issues
aitrackdown sync platform linear pull

# 3. Create new issues
aitrackdown create "Implement user authentication" --type issue --priority high
aitrackdown create "Fix dashboard performance" --type bug --priority critical

# 4. Push to Linear
aitrackdown sync platform linear push --dry-run
aitrackdown sync platform linear push
```

### Working with Projects

```bash
# Sync issues from specific project
aitrackdown sync config linear --key project_id --value PRJ_12345
aitrackdown sync platform linear pull

# Create issue for project
aitrackdown create "Design new API endpoints" \
  --type task \
  --metadata '{"linear_project_id": "PRJ_12345"}'
```

### Working with Cycles

```bash
# Sync current cycle
aitrackdown sync config linear --key cycle_id --value CYC_98765
aitrackdown sync platform linear pull

# Create issue for cycle
aitrackdown create "Sprint 23 planning" \
  --metadata '{"linear_cycle_id": "CYC_98765"}'
```

### Using Labels

Linear's structured labels map to tags:

```bash
# Create issue with Linear labels
aitrackdown create "Memory leak in worker process" \
  --tags "Bug" "Backend" "P0" \
  --priority critical

# Labels are organized by groups in Linear
```

## Field Mappings

### From Linear to AI Trackdown

| Linear Field | AI Trackdown Field | Notes |
|--------------|-------------------|-------|
| `title` | `title` | Direct mapping |
| `description` | `description` | Markdown preserved |
| `state.name` | `status` | Via status mapping |
| `priority` | `priority` | 0-4 scale mapped |
| `labels` | `tags` | Label names |
| `assignee` | `assignees` | Single assignee |
| `createdAt` | `created_at` | ISO format |
| `updatedAt` | `updated_at` | ISO format |
| `dueDate` | `metadata.due_date` | Stored as metadata |
| `estimate` | `metadata.estimate` | Story points |
| `project` | `metadata.linear_project` | Project details |
| `cycle` | `metadata.linear_cycle` | Cycle details |
| `parent` | `metadata.linear_parent_id` | For sub-issues |

### From AI Trackdown to Linear

| AI Trackdown Field | Linear Field | Notes |
|-------------------|---------------|-------|
| `title` | `title` | Required |
| `description` | `description` | Markdown supported |
| `status` | `stateId` | Must map to valid state |
| `priority` | `priority` | Mapped to 0-4 |
| `tags` | `labelIds` | Matched by name |
| `assignees[0]` | `assigneeId` | First assignee only |
| `metadata.due_date` | `dueDate` | ISO date format |
| `metadata.estimate` | `estimate` | Number (points) |

## Advanced Features

### Sub-Issues

Handle Linear's sub-issue hierarchy:

```bash
# Create parent issue
PARENT_ID=$(aitrackdown create "Epic: New Feature" --type issue)

# Create sub-issue
aitrackdown create "Implement backend API" \
  --type task \
  --metadata "{\"linear_parent_id\": \"$PARENT_ID\"}"
```

### SLA and Triage

Configure SLA workflows:

```bash
# Set up SLA configuration
aitrackdown sync config linear --key sla_config --value '{
  "response_time": {
    "critical": "1h",
    "high": "4h",
    "medium": "1d",
    "low": "3d"
  },
  "auto_triage": true
}'
```

### Integrations

Linear integrates with many tools:

```bash
# Add integration metadata
aitrackdown create "Fix Sentry error #1234" \
  --type bug \
  --metadata '{
    "linear_integrations": {
      "sentry": {"issue_id": "1234"},
      "github": {"pr_number": "456"}
    }
  }'
```

## GraphQL Queries

Linear uses GraphQL. Here are useful queries:

### Get Issues

```bash
# Get recent issues
curl -H "Authorization: lin_api_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ issues(filter: { team: { key: { eq: \"ENG\" } } }, first: 10) { nodes { id title description state { name } priority assignee { email } } } }"
  }' \
  https://api.linear.app/graphql
```

### Create Issue

```bash
# Create new issue
curl -H "Authorization: lin_api_xxxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { issueCreate(input: { teamId: \"TEAM_ID\", title: \"New Issue\", description: \"Description\" }) { issue { id } success } }"
  }' \
  https://api.linear.app/graphql
```

## Troubleshooting

### Authentication Issues

**Problem**: "Invalid authentication" error

**Solutions**:
1. Verify API key:
   ```bash
   curl -H "Authorization: lin_api_xxxxx" \
     -H "Content-Type: application/json" \
     -d '{"query": "{ viewer { id email } }"}' \
     https://api.linear.app/graphql
   ```

2. Regenerate API key in Linear settings

3. Check configuration:
   ```bash
   aitrackdown sync config linear --list
   ```

### Team Not Found

**Problem**: "Team not found" error

**Solutions**:
1. List available teams:
   ```bash
   curl -H "Authorization: lin_api_xxxxx" \
     -H "Content-Type: application/json" \
     -d '{"query": "{ teams { nodes { id key name } } }"}' \
     https://api.linear.app/graphql
   ```

2. Use the correct team key or ID

### Invalid State

**Problem**: "Invalid workflow state" error

**Solutions**:
1. Get valid states:
   ```bash
   # Query available states
   curl -H "Authorization: lin_api_xxxxx" \
     -H "Content-Type: application/json" \
     -d '{"query": "{ workflowStates(filter: { team: { key: { eq: \"YOUR_TEAM\" } } }) { nodes { id name type } } }"}' \
     https://api.linear.app/graphql
   ```

2. Update status mapping configuration

### Rate Limiting

**Problem**: Rate limit errors

**Solutions**:
1. Linear has generous rate limits (1500 points/hour)
2. Reduce batch size if needed:
   ```bash
   aitrackdown sync config linear --key batch_size --value 25
   ```

## Best Practices

### 1. Use Projects for Organization

Structure your work:
```bash
# Configure default project
aitrackdown sync config linear --key project_id --value PRJ_FRONTEND

# Create issues in project
aitrackdown create "Redesign navigation" --type task
```

### 2. Leverage Cycles

Work in sprints:
```bash
# Sync current cycle only
aitrackdown sync config linear --key cycle_id --value CURRENT
aitrackdown sync platform linear pull
```

### 3. Consistent Labeling

Use Linear's label groups effectively:
```bash
# Set up label mapping
aitrackdown sync config linear --key label_mapping --value '{
  "bug": "Type/Bug",
  "feature": "Type/Feature",
  "frontend": "Area/Frontend",
  "backend": "Area/Backend",
  "urgent": "Priority/P0"
}'
```

### 4. Automate with Linear

Set up Linear automations:
- Auto-assign based on labels
- Move to "In Progress" when assigned
- Close when PR is merged

### 5. Use Estimates

Track velocity:
```bash
# Create issue with estimate
aitrackdown create "Refactor authentication" \
  --metadata '{"estimate": 5}' \
  --priority high
```

## Linear-Specific Metadata

The adapter preserves Linear metadata:

```json
{
  "id": "ISS-001",
  "title": "Sample Issue",
  "metadata": {
    "linear_id": "ENG-123",
    "linear_url": "https://linear.app/team/issue/ENG-123",
    "linear_number": 123,
    "linear_identifier": "ENG-123",
    "linear_project": {
      "id": "PRJ_12345",
      "name": "Q1 Features"
    },
    "linear_cycle": {
      "id": "CYC_98765",
      "name": "Sprint 23",
      "number": 23
    },
    "linear_state": {
      "id": "STATE_ID",
      "name": "In Progress",
      "type": "started"
    },
    "linear_labels": [
      {"id": "LABEL_1", "name": "Bug"},
      {"id": "LABEL_2", "name": "Backend"}
    ],
    "platform": "linear"
  }
}
```

## Integration Features

### GitHub Integration

Linear's GitHub integration works with synced issues:
```bash
# Reference Linear issue in commit
git commit -m "Fix authentication bug [ENG-123]"

# Linear automatically links commit to issue
```

### Slack Integration

Issues synced from AI Trackdown appear in Slack notifications.

### Figma Integration

Link designs to synced issues using Linear's Figma plugin.

## Security Considerations

1. **API Key Security**:
   ```bash
   # Use environment variable
   export LINEAR_API_KEY=lin_api_xxxxx
   ```

2. **Permissions**: API key has full user permissions
   - Be careful with key distribution
   - Rotate keys regularly

3. **Data Privacy**:
   - Linear API keys are personal
   - Team data access based on user permissions

## Example Configurations

### Engineering Team

```json
{
  "linear": {
    "token": "lin_api_xxxxx",
    "team_id": "ENG",
    "status_mapping": {
      "open": "Backlog",
      "in_progress": "In Progress",
      "in_review": "In Review",
      "testing": "Testing",
      "completed": "Done",
      "cancelled": "Canceled"
    },
    "label_groups": {
      "Type": ["Bug", "Feature", "Task", "Epic"],
      "Priority": ["P0", "P1", "P2", "P3"],
      "Component": ["API", "Frontend", "Database", "Infrastructure"]
    },
    "include_archived": false
  }
}
```

### Product Team

```json
{
  "linear": {
    "token": "lin_api_xxxxx",
    "team_id": "PROD",
    "project_id": "PRJ_Q1_ROADMAP",
    "status_mapping": {
      "open": "Ideation",
      "in_progress": "Design",
      "in_review": "User Testing",
      "completed": "Shipped"
    },
    "priority_mapping": {
      "critical": 1,
      "high": 2,
      "medium": 3,
      "low": 4
    }
  }
}
```

## Limitations

1. **Single Assignee**: Linear supports one assignee per issue
2. **Comments**: Read-only in current version
3. **Attachments**: Not synced
4. **Custom Fields**: Limited support
5. **Webhooks**: Not yet implemented

## Future Enhancements

Planned features:

1. Two-way comment sync
2. Attachment support
3. Webhook integration for real-time sync
4. Multi-assignee workaround
5. Custom field support
6. Roadmap integration
7. Initiative tracking
8. SLA automation