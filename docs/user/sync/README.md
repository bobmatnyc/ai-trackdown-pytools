# Platform Sync Guide

AI Trackdown PyTools supports synchronization with external project management platforms. This guide covers the available platforms and how to use the sync functionality.

## Supported Platforms

Currently supported platforms:

- **GitHub** - Issues and Pull Requests
- **ClickUp** - Tasks and Lists  
- **Linear** - Issues and Projects

## Quick Start

### 1. List Available Platforms

```bash
# List all supported sync platforms
aitrackdown sync list-available
```

### 2. Check Platform Status

```bash
# Check sync status for a platform
aitrackdown sync platform github status
aitrackdown sync platform clickup status
aitrackdown sync platform linear status
```

### 3. Configure Platform Authentication

Before syncing, you need to configure authentication for each platform:

#### GitHub
```bash
# Configure GitHub repository
aitrackdown sync config github --key repository --value owner/repo
aitrackdown sync config github --key token --value your-github-token

# Or use environment variables
export GITHUB_TOKEN=your-github-token
```

#### ClickUp
```bash
# Configure ClickUp
aitrackdown sync config clickup --key token --value your-clickup-token
aitrackdown sync config clickup --key team_id --value your-team-id
```

#### Linear
```bash
# Configure Linear
aitrackdown sync config linear --key token --value your-linear-token
aitrackdown sync config linear --key team_id --value your-team-id
```

### 4. Sync Operations

#### Pull from Platform
```bash
# Pull items from platform to local (dry-run first)
aitrackdown sync platform github pull --dry-run
aitrackdown sync platform github pull

# Pull from other platforms
aitrackdown sync platform clickup pull
aitrackdown sync platform linear pull
```

#### Push to Platform
```bash
# Push local items to platform (dry-run first)
aitrackdown sync platform github push --dry-run
aitrackdown sync platform github push

# Push to other platforms
aitrackdown sync platform clickup push
aitrackdown sync platform linear push
```

## Sync Behavior

### What Gets Synced

- **Tasks/Issues**: Title, description, status, assignees, tags/labels
- **Metadata**: Platform-specific IDs and URLs are stored in task metadata
- **Status Mapping**: AI Trackdown workflow states are mapped to platform-specific states

### Conflict Resolution

- Local items take precedence during push operations
- Platform items take precedence during pull operations
- Use `--dry-run` to preview changes before applying them

### Data Mapping

#### Status Mapping
- `OPEN` → Platform's open/new status
- `IN_PROGRESS` → Platform's in-progress status  
- `RESOLVED`/`CLOSED` → Platform's closed/done status
- `BLOCKED` → Platform's blocked status (if supported)

#### Tag/Label Mapping
- AI Trackdown tags are mapped to platform labels/tags
- Platform-specific label formats are preserved

## Configuration Management

### View Configuration
```bash
# View all platform configurations
aitrackdown sync config --list

# View specific platform configuration
aitrackdown sync config github --list
```

### Set Configuration Values
```bash
# Set configuration values
aitrackdown sync config <platform> --key <key> --value <value>

# Example: Set GitHub repository
aitrackdown sync config github --key repository --value myorg/myrepo
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify your API tokens are valid and have necessary permissions
   - Check that tokens are properly configured or set as environment variables

2. **Repository/Project Not Found**
   - Verify the repository/project identifier is correct
   - Ensure your token has access to the specified repository/project

3. **Rate Limiting**
   - The sync system includes automatic rate limiting
   - If you hit limits, wait and try again later

### Diagnostic Commands

```bash
# Check system health
aitrackdown health --verbose

# Diagnose common issues
aitrackdown doctor

# Check sync status
aitrackdown sync platform <platform> status
```

## Best Practices

1. **Always use dry-run first**: Test sync operations with `--dry-run` before applying changes
2. **Regular syncing**: Sync regularly to avoid large batches of changes
3. **Backup important data**: Keep backups of important project data
4. **Monitor sync results**: Check the output of sync operations for any errors or warnings

## Examples

### Complete GitHub Sync Workflow
```bash
# 1. Configure GitHub
export GITHUB_TOKEN=your-token
aitrackdown sync config github --key repository --value myorg/myproject

# 2. Check status
aitrackdown sync platform github status

# 3. Pull latest from GitHub (dry-run first)
aitrackdown sync platform github pull --dry-run
aitrackdown sync platform github pull

# 4. Make local changes
aitrackdown create task "New feature" --tag "enhancement"

# 5. Push to GitHub (dry-run first)
aitrackdown sync platform github push --dry-run
aitrackdown sync platform github push
```

### Multi-Platform Sync
```bash
# Sync with multiple platforms
aitrackdown sync platform github pull
aitrackdown sync platform clickup push
aitrackdown sync platform linear status
```

## Limitations

- **One-way sync per operation**: Each sync operation is either pull or push, not bidirectional
- **Platform-specific features**: Some platform-specific features may not be fully supported
- **Rate limits**: API rate limits may affect sync speed for large datasets
- **Data format differences**: Some data may be transformed to fit platform requirements

For more technical details about the sync system, see the [Development Documentation](../../development/sync-adapter-developer-guide.md).
