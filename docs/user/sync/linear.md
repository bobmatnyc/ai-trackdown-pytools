# Linear Sync Adapter

The Linear sync adapter allows you to synchronize tasks between AI Trackdown and Linear using their GraphQL API.

## Features

- **Full CRUD Operations**: Create, read, update, and archive Linear issues
- **GraphQL Integration**: Efficient data fetching with optimized queries
- **Bidirectional Sync**: Pull from and push to Linear
- **Type Support**: Handles tasks, issues, and bugs
- **Field Mapping**: 
  - Status (workflow states)
  - Priority levels
  - Assignees
  - Labels/tags
  - Due dates
  - Estimates
  - Projects and cycles
- **Rate Limiting**: Automatic handling of API rate limits
- **Pagination**: Handles large datasets with cursor-based pagination

## Prerequisites

1. **Linear Account**: You need a Linear account with access to the workspace
2. **API Key**: Generate a personal API key from Linear settings
3. **Team ID**: The ID of your Linear team (found in team settings)
4. **Project ID** (optional): Specific project to sync with

## Configuration

### 1. Generate Linear API Key

1. Go to Linear Settings → API → Personal API keys
2. Click "Create key"
3. Give it a descriptive name (e.g., "AI Trackdown Sync")
4. Copy the generated key

### 2. Find Your Team ID

1. Go to Linear Settings → Teams
2. Click on your team
3. The team ID is in the URL: `linear.app/YOUR-WORKSPACE/team/TEAM-ID/...`

### 3. Configure AI Trackdown

Create a sync configuration file `.aitrackdown/sync.json`:

```json
{
  "linear": {
    "api_key": "lin_api_YOUR_API_KEY",
    "team_id": "YOUR-TEAM-ID",
    "project_id": "YOUR-PROJECT-ID"  // optional
  }
}
```

Or use environment variables:

```bash
export LINEAR_API_KEY="lin_api_YOUR_API_KEY"
```

## Usage

### Pull Tasks from Linear

Pull all tasks from Linear:

```bash
aitrackdown sync platform linear pull
```

Pull tasks updated since a specific date:

```bash
aitrackdown sync platform linear pull --since "2024-01-01"
```

### Push Tasks to Linear

Push local tasks to Linear:

```bash
aitrackdown sync platform linear push
```

Push specific task types:

```bash
aitrackdown sync platform linear push --types task,bug
```

### Check Sync Status

View the current sync status:

```bash
aitrackdown sync platform linear status
```

## Field Mapping

### Status Mapping

| AI Trackdown Status | Linear States |
|-------------------|---------------|
| OPEN | Backlog, Todo, Unstarted |
| IN_PROGRESS | In Progress, In Review, Started |
| COMPLETED | Done, Completed, Shipped |
| CANCELLED | Canceled, Cancelled |
| BLOCKED | Blocked |

### Priority Mapping

| AI Trackdown Priority | Linear Priority |
|---------------------|-----------------|
| CRITICAL | Urgent (1) |
| HIGH | High (2) |
| MEDIUM | Medium (3) |
| LOW | Low (4) |

### Special Fields

- **Linear Identifier**: Stored as `linear_identifier` in metadata (e.g., "ENG-123")
- **Linear URL**: Direct link to the issue stored in metadata
- **Projects**: Linear project information preserved in metadata
- **Cycles**: Sprint/cycle information preserved in metadata
- **Estimates**: Linear points converted to/from hours (1 point ≈ 4 hours)

## Advanced Configuration

### Custom Status Mapping

Override default status mappings in your sync config:

```json
{
  "linear": {
    "api_key": "...",
    "team_id": "...",
    "status_mapping": {
      "open": "Backlog",
      "in_progress": "In Progress",
      "completed": "Done",
      "cancelled": "Canceled"
    }
  }
}
```

### Filtering

Filter which items to sync:

```json
{
  "linear": {
    "api_key": "...",
    "team_id": "...",
    "included_types": ["task", "bug"],
    "excluded_types": ["epic"],
    "sync_tags": true,
    "sync_assignees": true,
    "sync_comments": false
  }
}
```

### Performance Tuning

Adjust batch size and timeouts:

```json
{
  "linear": {
    "api_key": "...",
    "team_id": "...",
    "batch_size": 50,
    "timeout": 30,
    "max_retries": 3
  }
}
```

## Troubleshooting

### Authentication Errors

**Error**: "Invalid Linear API key"
- Verify your API key is correct
- Ensure the key hasn't expired
- Check if the key has necessary permissions

**Error**: "Linear team ID not specified"
- Add `team_id` to your configuration
- Verify the team ID is correct

### Rate Limiting

The adapter automatically handles rate limiting, but if you encounter issues:
- Reduce `batch_size` in configuration
- Add delays between sync operations
- Use Linear's higher-tier plans for increased limits

### Connection Issues

**Error**: "Failed to connect to Linear"
- Check your internet connection
- Verify Linear's API status at status.linear.app
- Try again with increased timeout

### Data Mapping Issues

If certain fields aren't syncing correctly:
- Check the field mapping section above
- Ensure custom fields are properly configured
- Review Linear's workflow states match expected values

## Example Workflows

### Daily Sync

Set up a daily sync to keep Linear and AI Trackdown in sync:

```bash
# Pull updates from Linear
aitrackdown sync platform linear pull --since "1 day ago"

# Push local changes to Linear
aitrackdown sync platform linear push --dry-run  # Preview first
aitrackdown sync platform linear push
```

### Project Migration

Migrate a project from Linear to AI Trackdown:

```bash
# Configure for specific project
echo '{
  "linear": {
    "api_key": "YOUR_KEY",
    "team_id": "YOUR_TEAM",
    "project_id": "PROJECT_ID"
  }
}' > .aitrackdown/linear-sync.json

# Pull all project tasks
aitrackdown sync platform linear pull --config .aitrackdown/linear-sync.json

# Verify import
aitrackdown list --format table
```

### Selective Sync

Sync only high-priority bugs:

```bash
# Configure filters
aitrackdown sync platform linear pull \
  --types bug \
  --priority high,critical \
  --status open,in_progress
```

## Best Practices

1. **Test with Dry Run**: Always use `--dry-run` first to preview changes
2. **Regular Syncs**: Set up automated daily or weekly syncs
3. **Backup First**: Export your data before major sync operations
4. **Monitor Rate Limits**: Keep an eye on API usage
5. **Use Projects**: Organize work by syncing specific Linear projects
6. **Consistent Workflow**: Align your Linear workflow states with AI Trackdown statuses

## Limitations

- **No Hard Delete**: Linear only supports archiving, not deletion
- **Limited User Mapping**: Assignees mapped by email only
- **Label Creation**: New labels must be created in Linear first
- **Custom Fields**: Not all Linear custom fields are supported
- **Comments**: Comment sync requires additional API calls (disabled by default)

## Security Considerations

- **API Key Storage**: Never commit API keys to version control
- **Use Environment Variables**: Preferred for CI/CD environments
- **Limit Scope**: Use project-specific configurations when possible
- **Rotate Keys**: Regularly rotate API keys for security
- **Audit Access**: Review API key permissions periodically