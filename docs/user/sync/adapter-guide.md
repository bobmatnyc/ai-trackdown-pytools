# Sync Adapter System User Guide

This guide covers the sync adapter system in AI Trackdown PyTools, which enables seamless synchronization with external project management platforms.

## Overview

The sync adapter system provides a unified interface for synchronizing tasks, issues, and other work items between AI Trackdown and popular project management platforms. The system supports bidirectional synchronization, allowing you to work in AI Trackdown while keeping your external platforms up to date.

## Supported Platforms

Currently supported platforms:

- **GitHub** - Issues and Pull Requests
- **ClickUp** - Tasks and Lists
- **Linear** - Issues and Projects
- **JIRA** - Issues, Tasks, Epics, and Bugs

## Quick Start

### 1. List Available Platforms

```bash
# List all supported sync platforms
aitrackdown sync list-available

# Alternative method
aitrackdown sync platform list platforms
```

### 2. Configure a Platform

Before syncing, you need to configure authentication and project settings:

```bash
# View available configuration options for a platform
aitrackdown sync config <platform>

# Set configuration values
aitrackdown sync config github --key repository --value owner/repo
aitrackdown sync config github --key token --value your-github-token

# View current configuration
aitrackdown sync config <platform> --list
```

### 3. Check Sync Status

```bash
# Check sync status for a platform
aitrackdown sync platform <platform> status

# Examples
aitrackdown sync platform github status
aitrackdown sync platform clickup status
```

### 4. Pull Items from Platform

```bash
# Pull items from external platform to local
aitrackdown sync platform <platform> pull

# Pull with dry run to preview changes
aitrackdown sync platform <platform> pull --dry-run

# Examples
aitrackdown sync platform github pull
aitrackdown sync platform linear pull --dry-run
```

### 5. Push Items to Platform

```bash
# Push local items to external platform
aitrackdown sync platform <platform> push

# Push with dry run to preview changes
aitrackdown sync platform <platform> push --dry-run

# Examples
aitrackdown sync platform jira push
aitrackdown sync platform clickup push --dry-run
```

## Platform-Specific Configuration

### GitHub

GitHub integration uses the GitHub CLI (`gh`) for authentication by default, or you can provide a personal access token.

```bash
# Configure GitHub repository
aitrackdown sync config github --key repository --value myorg/myrepo

# Optional: Set personal access token
aitrackdown sync config github --key token --value ghp_xxxxx

# Optional: Set custom API URL for GitHub Enterprise
aitrackdown sync config github --key api_url --value https://github.company.com/api/v3
```

**Required Permissions for Token:**
- `repo` scope for private repositories
- `public_repo` scope for public repositories only

### ClickUp

ClickUp requires an API token and a list ID where tasks will be synchronized.

```bash
# Configure ClickUp
aitrackdown sync config clickup --key token --value pk_xxxxx
aitrackdown sync config clickup --key list_id --value 123456789

# Optional: Set workspace ID
aitrackdown sync config clickup --key workspace_id --value 987654321
```

**Getting ClickUp Credentials:**
1. Go to ClickUp Settings → Apps
2. Generate a personal API token
3. Find your list ID in the list URL: `https://app.clickup.com/1234567/v/li/123456789`

### Linear

Linear uses API keys for authentication and requires a team ID.

```bash
# Configure Linear
aitrackdown sync config linear --key token --value lin_api_xxxxx
aitrackdown sync config linear --key team_id --value TEAM-XXXX
```

**Getting Linear Credentials:**
1. Go to Linear Settings → API
2. Create a personal API key
3. Find your team ID in Linear settings

### JIRA

JIRA requires server URL, email, API token, and project key.

```bash
# Configure JIRA
aitrackdown sync config jira --key server --value https://company.atlassian.net
aitrackdown sync config jira --key username --value your.email@company.com
aitrackdown sync config jira --key token --value ATATT3xFfGF0xxxxx
aitrackdown sync config jira --key project_key --value PROJ
```

**Getting JIRA Credentials:**
1. Go to [Atlassian API tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Create an API token
3. Use your email as username
4. Find project key in JIRA project settings

## Sync Workflows

### Basic Sync Workflow

1. **Initial Setup**
   ```bash
   # Configure platform
   aitrackdown sync config github --key repository --value myorg/myrepo
   
   # Check configuration
   aitrackdown sync config github --list
   ```

2. **First Sync - Pull Existing Items**
   ```bash
   # Preview what will be pulled
   aitrackdown sync platform github pull --dry-run
   
   # Pull items
   aitrackdown sync platform github pull
   ```

3. **Work Locally**
   ```bash
   # Create new items locally
   aitrackdown create "New feature" --type issue
   aitrackdown create "Bug fix" --type task
   ```

4. **Push Changes**
   ```bash
   # Preview what will be pushed
   aitrackdown sync platform github push --dry-run
   
   # Push new items
   aitrackdown sync platform github push
   ```

### Multi-Platform Workflow

You can sync with multiple platforms simultaneously:

```bash
# Configure multiple platforms
aitrackdown sync config github --key repository --value myorg/myrepo
aitrackdown sync config linear --key team_id --value TEAM-ABC

# Pull from all platforms
aitrackdown sync platform github pull
aitrackdown sync platform linear pull

# Work locally
aitrackdown create "Cross-platform task" --type task

# Push to specific platform
aitrackdown sync platform github push
```

### Selective Sync

Control what gets synced using tags and metadata:

```bash
# Create items with platform-specific tags
aitrackdown create "GitHub-only issue" --tags github issue
aitrackdown create "Linear-specific task" --tags linear task

# Items will sync to appropriate platforms based on configuration
```

## Sync Direction and Conflict Resolution

### Sync Directions

- **Pull**: Brings items from external platform to local
- **Push**: Sends local items to external platform
- **Bidirectional**: Future feature for automatic two-way sync

### Conflict Resolution

When the same item exists both locally and remotely with different changes:

1. **During Pull**: Remote changes take precedence by default
2. **During Push**: Local changes are pushed, updating the remote
3. **Dry Run**: Always use `--dry-run` to preview changes before syncing

### Preventing Duplicates

The sync system tracks items using platform-specific IDs in metadata:
- GitHub: `github_id`, `github_number`
- ClickUp: `clickup_id`
- Linear: `linear_id`
- JIRA: `jira_id`, `jira_key`

Items with these IDs are updated rather than duplicated during sync.

## Advanced Features

### Custom Field Mapping

Map fields between AI Trackdown and external platforms:

```bash
# Map status values
aitrackdown sync config github --key status_mapping --value '{"open": "todo", "in_progress": "in progress"}'

# Map labels
aitrackdown sync config github --key label_mapping --value '{"bug": "type:bug", "feature": "type:feature"}'
```

### Filtering

Control which items are synced:

```bash
# Only sync specific types
aitrackdown sync platform github pull --types issue,bug

# Exclude certain types
aitrackdown sync platform jira push --exclude-types epic
```

### Batch Operations

For better performance with large datasets:

```bash
# Set batch size for sync operations
aitrackdown sync config clickup --key batch_size --value 100

# Sync with custom timeout
aitrackdown sync platform linear pull --timeout 60
```

## Troubleshooting

### Common Issues

#### Authentication Failures

**Problem**: "Authentication failed" error

**Solutions**:
1. Verify your credentials are correct
2. Check token permissions/scopes
3. Ensure API access is enabled for your account
4. For GitHub, ensure `gh` CLI is authenticated: `gh auth status`

#### Rate Limiting

**Problem**: "Rate limit exceeded" error

**Solutions**:
1. Wait for rate limit to reset (shown in error message)
2. Reduce batch size in configuration
3. Use `--dry-run` for testing without consuming API quota

#### Missing Items

**Problem**: Some items don't appear after sync

**Possible Causes**:
1. Items filtered by type restrictions
2. Items in closed/archived state
3. Permissions issue on external platform
4. Items in different project/list than configured

#### Configuration Not Found

**Problem**: "No configuration found for platform"

**Solution**:
```bash
# Initialize configuration
aitrackdown sync config <platform> --key <required_key> --value <value>

# Verify configuration exists
aitrackdown sync config <platform> --list
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Set log level to debug
export AITRACKDOWN_LOG_LEVEL=DEBUG

# Run sync with debug output
aitrackdown sync platform github pull
```

### Checking Sync State

View detailed sync information:

```bash
# Check sync metadata
cat .aitrackdown/sync.json

# View sync state
cat .aitrackdown/sync_state.json
```

## Best Practices

### 1. Always Use Dry Run First

Before any sync operation, preview changes:
```bash
aitrackdown sync platform <platform> pull --dry-run
aitrackdown sync platform <platform> push --dry-run
```

### 2. Regular Sync Schedule

Establish a regular sync routine:
- Pull at the start of your work session
- Push completed work at the end
- Use `status` command to track last sync times

### 3. Backup Before Major Syncs

Before initial sync or major operations:
```bash
# Export current data
aitrackdown sync export json --output backup.json

# Proceed with sync
aitrackdown sync platform github pull
```

### 4. Use Consistent Naming

Maintain consistent naming conventions across platforms:
- Use clear, descriptive titles
- Apply consistent labeling schemes
- Document naming conventions in your project

### 5. Monitor Sync Health

Regularly check sync status:
```bash
# Check all configured platforms
for platform in github clickup linear jira; do
  echo "=== $platform ==="
  aitrackdown sync platform $platform status
done
```

## Security Considerations

### Token Storage

- Tokens are stored in `.aitrackdown/sync.json`
- This file should be added to `.gitignore`
- Never commit tokens to version control

### Environment Variables

For added security, use environment variables:
```bash
# GitHub
export GITHUB_TOKEN=ghp_xxxxx

# ClickUp
export CLICKUP_API_TOKEN=pk_xxxxx

# Linear
export LINEAR_API_KEY=lin_api_xxxxx

# JIRA
export JIRA_API_TOKEN=ATATT3xFfGF0xxxxx
```

### Access Permissions

- Use minimal required permissions for API tokens
- Regularly rotate API tokens
- Revoke unused tokens immediately

## Migration from Legacy Sync

If you're using the old GitHub-only sync commands:

### Old Command Structure
```bash
# Legacy commands (deprecated but still functional)
aitrackdown sync github pull
aitrackdown sync github push
aitrackdown sync github status
```

### New Command Structure
```bash
# New unified commands
aitrackdown sync platform github pull
aitrackdown sync platform github push
aitrackdown sync platform github status
```

### Migration Steps

1. Your existing configuration is automatically compatible
2. Update any scripts to use new command structure
3. Take advantage of new features like dry-run and filtering

## Getting Help

### Documentation

- User Guide: This document
- [Developer Guide](../development/sync-adapter-developer-guide.md)
- [API Reference](../development/sync-adapter-api-reference.md)
- [Platform Examples](./platform-examples/)

### Support

- GitHub Issues: Report bugs or request features
- Discussions: Ask questions and share tips
- Documentation: Check for updates and examples

### Command Help

Get help for any command:
```bash
# General sync help
aitrackdown sync --help

# Platform command help
aitrackdown sync platform --help

# Configuration help
aitrackdown sync config --help
```