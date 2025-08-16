# JIRA Sync Configuration Guide

This guide covers JIRA-specific configuration and usage for the sync adapter system.

## Prerequisites

- JIRA account with project access
- JIRA API token
- Server URL and project key

## Quick Start

```bash
# Configure JIRA
aitrackdown sync config jira --key server --value https://company.atlassian.net
aitrackdown sync config jira --key username --value your.email@company.com
aitrackdown sync config jira --key token --value ATATT3xFfGF0xxxxx
aitrackdown sync config jira --key project_key --value PROJ

# Test connection
aitrackdown sync platform jira status

# Start syncing
aitrackdown sync platform jira pull
```

## Getting JIRA Credentials

### 1. Generate API Token

1. Go to [Atlassian Account Settings](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click "Create API token"
3. Give it a label (e.g., "AI Trackdown Sync")
4. Copy the token (you won't see it again)

### 2. Find Server URL

- **JIRA Cloud**: `https://yourcompany.atlassian.net`
- **JIRA Server**: `https://jira.yourcompany.com`

### 3. Find Project Key

1. Go to your JIRA project
2. Look at the issue keys (e.g., `PROJ-123`)
3. The prefix is your project key (e.g., `PROJ`)

## Configuration Options

### Required Configuration

| Key | Description | Example |
|-----|-------------|---------|
| `server` | JIRA server URL | `https://company.atlassian.net` |
| `username` | Your email address | `user@company.com` |
| `token` | API token | `ATATT3xFfGF0xxxxx` |
| `project_key` | Project key | `PROJ` |

### Optional Configuration

| Key | Description | Default | Example |
|-----|-------------|---------|---------|
| `issue_type` | Default issue type | `Task` | `Story` |
| `board_id` | Agile board ID | None | `123` |
| `sprint_id` | Active sprint ID | None | `456` |
| `component` | Default component | None | `Backend` |
| `fix_version` | Default fix version | None | `1.0.0` |
| `custom_fields` | Custom field mappings | `{}` | See below |
| `batch_size` | Items per request | `50` | `100` |
| `timeout` | Request timeout (seconds) | `30` | `60` |

### Full Configuration Example

```json
{
  "jira": {
    "server": "https://company.atlassian.net",
    "username": "user@company.com",
    "token": "ATATT3xFfGF0xxxxx",
    "project_key": "PROJ",
    "issue_type": "Task",
    "board_id": "123",
    "component": "Backend",
    "batch_size": 50,
    "status_mapping": {
      "open": "To Do",
      "in_progress": "In Progress",
      "in_review": "In Review",
      "testing": "Testing",
      "completed": "Done",
      "cancelled": "Won't Do"
    },
    "priority_mapping": {
      "critical": "Highest",
      "high": "High",
      "medium": "Medium",
      "low": "Low"
    },
    "issue_type_mapping": {
      "task": "Task",
      "issue": "Bug",
      "feature": "Story",
      "epic": "Epic"
    },
    "custom_fields": {
      "Story Points": "customfield_10001",
      "Sprint": "customfield_10002",
      "Epic Link": "customfield_10003"
    }
  }
}
```

## Supported Item Types

JIRA adapter supports:

- **Tasks** - JIRA Tasks
- **Issues** - JIRA Bugs
- **Epics** - JIRA Epics
- **Bugs** - JIRA Bugs (specific type)

## JIRA-Specific Features

### Issue Types

Map AI Trackdown types to JIRA issue types:

```bash
# Configure issue type mapping
aitrackdown sync config jira --key issue_type_mapping --value '{
  "task": "Task",
  "issue": "Bug",
  "feature": "Story",
  "epic": "Epic"
}'
```

### Priority Levels

JIRA default priorities:

| AI Trackdown | JIRA | Icon |
|--------------|------|------|
| `critical` | Highest/Blocker | 🔴 |
| `high` | High/Critical | 🟠 |
| `medium` | Medium/Major | 🟡 |
| `low` | Low/Minor | 🟢 |
| None | Lowest/Trivial | ⚪ |

### Custom Fields

JIRA heavily uses custom fields:

```bash
# Find custom field IDs
curl -u user@company.com:token \
  https://company.atlassian.net/rest/api/3/field

# Configure custom fields
aitrackdown sync config jira --key custom_fields --value '{
  "Story Points": "customfield_10001",
  "Sprint": "customfield_10002",
  "Team": "customfield_10003",
  "T-Shirt Size": "customfield_10004"
}'
```

## Usage Examples

### Basic Workflow

```bash
# 1. Configure JIRA
aitrackdown sync config jira --key server --value https://company.atlassian.net
aitrackdown sync config jira --key username --value user@company.com
aitrackdown sync config jira --key token --value ATATT3xFfGF0xxxxx
aitrackdown sync config jira --key project_key --value PROJ

# 2. Pull existing issues
aitrackdown sync platform jira pull

# 3. Create new issues
aitrackdown create "Implement OAuth2 authentication" --type task --priority high
aitrackdown create "Database connection timeout" --type bug --priority critical

# 4. Push to JIRA
aitrackdown sync platform jira push --dry-run
aitrackdown sync platform jira push
```

### Working with Epics

```bash
# Create an epic
EPIC_ID=$(aitrackdown create "Q1 Feature Release" --type epic)

# Create issues under epic
aitrackdown create "User authentication module" \
  --type task \
  --metadata "{\"jira_epic_link\": \"$EPIC_ID\"}"

aitrackdown create "Payment processing integration" \
  --type task \
  --metadata "{\"jira_epic_link\": \"$EPIC_ID\"}"
```

### Working with Sprints

```bash
# Configure active sprint
aitrackdown sync config jira --key sprint_id --value 456

# Create issue for sprint
aitrackdown create "Fix performance regression" \
  --type bug \
  --priority high \
  --metadata '{"jira_sprint": 456}'
```

### Using Components

```bash
# Set default component
aitrackdown sync config jira --key component --value "Backend"

# Create issue with multiple components
aitrackdown create "API rate limiting" \
  --type task \
  --metadata '{"jira_components": ["Backend", "API", "Security"]}'
```

## Field Mappings

### From JIRA to AI Trackdown

| JIRA Field | AI Trackdown Field | Notes |
|------------|-------------------|-------|
| `summary` | `title` | Direct mapping |
| `description` | `description` | Preserves JIRA markdown |
| `status.name` | `status` | Via status mapping |
| `priority.name` | `priority` | Via priority mapping |
| `issuetype.name` | Type determination | Maps to model type |
| `labels` | `tags` | Direct mapping |
| `assignee` | `assignees` | Email address |
| `created` | `created_at` | Timezone aware |
| `updated` | `updated_at` | Timezone aware |
| `duedate` | `metadata.due_date` | Date only |
| `components` | `metadata.jira_components` | Component names |
| `fixVersions` | `metadata.jira_fix_versions` | Version names |
| Custom fields | `metadata.jira_custom_fields` | Configured fields |

### From AI Trackdown to JIRA

| AI Trackdown Field | JIRA Field | Notes |
|-------------------|------------|-------|
| `title` | `summary` | Required, max 255 chars |
| `description` | `description` | JIRA wiki markup |
| `status` | Workflow transition | Cannot set directly |
| `priority` | `priority` | Must be valid priority |
| Type | `issuetype` | Via type mapping |
| `tags` | `labels` | Space-separated |
| `assignees[0]` | `assignee` | Must be JIRA user |
| `metadata.due_date` | `duedate` | YYYY-MM-DD format |
| `metadata.story_points` | Custom field | If configured |

## Advanced Features

### JQL Queries

Filter issues with JQL:

```bash
# Configure JQL filter
aitrackdown sync config jira --key jql_filter --value \
  "project = PROJ AND sprint in openSprints() AND assignee = currentUser()"

# Pull filtered issues
aitrackdown sync platform jira pull
```

### Workflow Transitions

Handle JIRA workflows:

```bash
# Get available transitions
curl -u user@company.com:token \
  https://company.atlassian.net/rest/api/3/issue/PROJ-123/transitions

# Configure transition mapping
aitrackdown sync config jira --key transitions --value '{
  "in_progress": "Start Progress",
  "in_review": "Submit for Review",
  "completed": "Resolve",
  "cancelled": "Close"
}'
```

### Agile Features

Work with JIRA Agile:

```bash
# Configure board
aitrackdown sync config jira --key board_id --value 123

# Get active sprint
curl -u user@company.com:token \
  https://company.atlassian.net/rest/agile/1.0/board/123/sprint?state=active

# Sync sprint issues
aitrackdown sync platform jira pull
```

### Custom Field Examples

```bash
# Story Points
aitrackdown create "Refactor payment module" \
  --type task \
  --metadata '{"story_points": 8}'

# T-Shirt Size
aitrackdown create "New feature design" \
  --type task \
  --metadata '{"jira_custom_fields": {"T-Shirt Size": "L"}}'

# Multiple custom fields
aitrackdown create "Security audit" \
  --type task \
  --metadata '{
    "story_points": 13,
    "jira_custom_fields": {
      "Team": "Security",
      "Risk Level": "High",
      "Compliance": "SOC2"
    }
  }'
```

## Troubleshooting

### Authentication Issues

**Problem**: "401 Unauthorized" error

**Solutions**:
1. Verify credentials:
   ```bash
   curl -u user@company.com:token \
     https://company.atlassian.net/rest/api/3/myself
   ```

2. Check token format (not base64 encoded)

3. For JIRA Server, might need different auth:
   ```bash
   # Basic auth for older JIRA Server
   aitrackdown sync config jira --key auth_type --value basic
   ```

### Project Not Found

**Problem**: "Project doesn't exist" error

**Solutions**:
1. List accessible projects:
   ```bash
   curl -u user@company.com:token \
     https://company.atlassian.net/rest/api/3/project
   ```

2. Check project permissions

3. Use project ID instead of key:
   ```bash
   aitrackdown sync config jira --key project_id --value 10001
   ```

### Invalid Field Values

**Problem**: "Field 'x' cannot be set" error

**Solutions**:
1. Get valid field values:
   ```bash
   # Get priority values
   curl -u user@company.com:token \
     https://company.atlassian.net/rest/api/3/priority
   
   # Get issue types
   curl -u user@company.com:token \
     https://company.atlassian.net/rest/api/3/issuetype
   ```

2. Check field permissions

### Custom Field Issues

**Problem**: Custom field not found

**Solutions**:
1. List all fields:
   ```bash
   curl -u user@company.com:token \
     https://company.atlassian.net/rest/api/3/field | jq '.[] | select(.custom == true)'
   ```

2. Use correct field ID (customfield_xxxxx)

## Best Practices

### 1. Use Projects Effectively

Organize work by project:
```bash
# Different configurations per project
cd ~/projects/backend
aitrackdown sync config jira --key project_key --value BACK

cd ~/projects/frontend
aitrackdown sync config jira --key project_key --value FRONT
```

### 2. Leverage Issue Types

Use appropriate JIRA issue types:
```bash
# Configure comprehensive type mapping
aitrackdown sync config jira --key issue_type_mapping --value '{
  "task": "Task",
  "issue": "Bug",
  "feature": "Story",
  "epic": "Epic",
  "subtask": "Sub-task",
  "improvement": "Improvement"
}'
```

### 3. Sprint Management

Work within sprints:
```bash
# Auto-add to active sprint
aitrackdown sync config jira --key auto_sprint --value true

# Or specify sprint
aitrackdown create "Sprint task" --metadata '{"jira_sprint": "Sprint 23"}'
```

### 4. Component-Based Organization

Use components for team organization:
```bash
# Set team components
aitrackdown sync config jira --key default_components --value '["Backend", "API"]'

# Create with specific component
aitrackdown create "Database optimization" \
  --metadata '{"jira_components": ["Backend", "Database"]}'
```

### 5. Custom Field Strategy

Standardize custom field usage:
```bash
# Create template for common fields
cat > .aitrackdown/jira-template.json << EOF
{
  "story_points": 0,
  "jira_custom_fields": {
    "Team": "Engineering",
    "Phase": "Development",
    "Customer Impact": "Medium"
  }
}
EOF

# Use template
TEMPLATE=$(cat .aitrackdown/jira-template.json)
aitrackdown create "New feature" --metadata "$TEMPLATE"
```

## JIRA-Specific Metadata

The adapter preserves JIRA metadata:

```json
{
  "id": "TSK-001",
  "title": "Sample Task",
  "metadata": {
    "jira_id": "10001",
    "jira_key": "PROJ-123",
    "jira_url": "https://company.atlassian.net/browse/PROJ-123",
    "jira_project": {
      "id": "10000",
      "key": "PROJ",
      "name": "Project Name"
    },
    "jira_issue_type": {
      "id": "10002",
      "name": "Task"
    },
    "jira_components": ["Backend", "API"],
    "jira_fix_versions": ["1.0.0", "1.1.0"],
    "jira_sprint": {
      "id": 23,
      "name": "Sprint 23",
      "state": "active"
    },
    "jira_epic_link": "PROJ-100",
    "jira_custom_fields": {
      "Story Points": 8,
      "Team": "Platform"
    },
    "platform": "jira"
  }
}
```

## Integration with JIRA Features

### JIRA Automation

Synced issues work with JIRA automation rules:
- Auto-assign based on components
- Transition based on PR status
- Send notifications on priority changes

### JIRA Service Management

For service desk projects:
```bash
# Configure for JSM
aitrackdown sync config jira --key project_type --value service_desk
aitrackdown sync config jira --key customer_field --value customfield_10100
```

### Confluence Integration

Link documentation:
```bash
# Add Confluence page link
aitrackdown create "Feature documentation" \
  --metadata '{
    "jira_custom_fields": {
      "Confluence Page": "https://company.atlassian.net/wiki/spaces/PROJ/pages/123456"
    }
  }'
```

## Security Considerations

1. **API Token Security**:
   ```bash
   # Use environment variable
   export JIRA_API_TOKEN=ATATT3xFfGF0xxxxx
   export JIRA_USERNAME=user@company.com
   ```

2. **Project Permissions**: API token inherits user permissions
   - Only access permitted projects
   - Cannot perform admin actions

3. **IP Whitelisting**: For JIRA Server
   - May need to whitelist IPs
   - Check with JIRA admin

## Example Configurations

### Agile Development Team

```json
{
  "jira": {
    "server": "https://company.atlassian.net",
    "username": "dev@company.com",
    "token": "ATATT3xFfGF0xxxxx",
    "project_key": "DEV",
    "board_id": "123",
    "issue_type_mapping": {
      "task": "Task",
      "issue": "Bug",
      "feature": "Story",
      "epic": "Epic"
    },
    "custom_fields": {
      "Story Points": "customfield_10001",
      "Sprint": "customfield_10002"
    },
    "auto_sprint": true
  }
}
```

### Support Team

```json
{
  "jira": {
    "server": "https://company.atlassian.net",
    "username": "support@company.com",
    "token": "ATATT3xFfGF0xxxxx",
    "project_key": "SUP",
    "project_type": "service_desk",
    "issue_type": "Incident",
    "priority_mapping": {
      "critical": "Blocker",
      "high": "Critical",
      "medium": "Major",
      "low": "Minor"
    },
    "custom_fields": {
      "SLA": "customfield_10200",
      "Customer": "customfield_10201"
    }
  }
}
```

## Limitations

1. **Attachments**: Not synced in current version
2. **Comments**: Read-only
3. **Watchers**: Not synced
4. **Time Tracking**: Basic support only
5. **Workflow**: Cannot bypass required fields

## Future Enhancements

Planned features:

1. Attachment synchronization
2. Two-way comment sync
3. Webhook support
4. Advanced workflow handling
5. Time tracking integration
6. Sub-task creation
7. Bulk operations
8. JIRA Portfolio integration