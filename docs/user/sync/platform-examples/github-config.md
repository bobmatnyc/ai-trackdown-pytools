# GitHub Sync Configuration Guide

This guide covers GitHub-specific configuration and usage for the sync adapter system.

## Prerequisites

- GitHub account with repository access
- Either GitHub CLI (`gh`) installed and authenticated, OR
- GitHub Personal Access Token (PAT)

## Quick Start

### Using GitHub CLI (Recommended)

```bash
# Ensure gh CLI is authenticated
gh auth status

# Configure repository
aitrackdown sync config github --key repository --value owner/repo

# Test connection
aitrackdown sync platform github status
```

### Using Personal Access Token

```bash
# Configure with token
aitrackdown sync config github --key repository --value owner/repo
aitrackdown sync config github --key token --value ghp_xxxxxxxxxxxxx

# Test connection
aitrackdown sync platform github status
```

## Configuration Options

### Required Configuration

| Key | Description | Example |
|-----|-------------|---------|
| `repository` | GitHub repository in owner/repo format | `microsoft/vscode` |

### Optional Configuration

| Key | Description | Default | Example |
|-----|-------------|---------|---------|
| `token` | Personal Access Token | Uses `gh` CLI | `ghp_xxxxx` |
| `api_url` | GitHub API endpoint | `https://api.github.com` | `https://github.company.com/api/v3` |
| `batch_size` | Items per request | `50` | `100` |
| `timeout` | Request timeout (seconds) | `30` | `60` |

### Full Configuration Example

```json
{
  "github": {
    "repository": "myorg/myproject",
    "token": "ghp_xxxxxxxxxxxxx",
    "api_url": "https://api.github.com",
    "batch_size": 50,
    "timeout": 30,
    "status_mapping": {
      "open": "open",
      "in_progress": "in progress",
      "completed": "closed"
    },
    "label_mapping": {
      "bug": "type:bug",
      "feature": "type:feature",
      "task": "type:task"
    }
  }
}
```

## Authentication

### Option 1: GitHub CLI (Recommended)

The GitHub adapter automatically uses the GitHub CLI if available:

```bash
# Install GitHub CLI
# macOS
brew install gh

# Linux
sudo apt install gh  # Debian/Ubuntu
sudo dnf install gh  # Fedora

# Authenticate
gh auth login

# Verify authentication
gh auth status
```

### Option 2: Personal Access Token

Create a Personal Access Token:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - `repo` - Full repository access (private repos)
   - `public_repo` - Public repository access only
4. Generate and copy token

Configure token:

```bash
# Set token in configuration
aitrackdown sync config github --key token --value ghp_xxxxxxxxxxxxx

# Or use environment variable
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

### Option 3: GitHub Enterprise

For GitHub Enterprise Server:

```bash
# Configure enterprise URL
aitrackdown sync config github --key api_url --value https://github.company.com/api/v3
aitrackdown sync config github --key repository --value org/repo
aitrackdown sync config github --key token --value your-enterprise-token
```

## Supported Item Types

GitHub adapter supports:

- **Issues** - GitHub Issues
- **Tasks** - Issues labeled as tasks
- **Pull Requests** - GitHub PRs (sync as PR type)

## Usage Examples

### Basic Sync Workflow

```bash
# 1. Configure repository
aitrackdown sync config github --key repository --value myorg/myrepo

# 2. Check status
aitrackdown sync platform github status

# 3. Pull existing issues
aitrackdown sync platform github pull

# 4. Create new items locally
aitrackdown create "Fix login bug" --type issue --priority high
aitrackdown create "Add user dashboard" --type task

# 5. Push to GitHub
aitrackdown sync platform github push --dry-run  # Preview
aitrackdown sync platform github push            # Execute
```

### Working with Issues

```bash
# Pull only open issues
aitrackdown sync platform github pull

# Create issue with GitHub-specific metadata
aitrackdown create "Security vulnerability" \
  --type issue \
  --priority critical \
  --tags security bug \
  --description "Found XSS vulnerability in user input"

# Push to GitHub
aitrackdown sync platform github push
```

### Working with Pull Requests

```bash
# Pull PRs from GitHub
aitrackdown sync platform github pull

# PRs are synced as read-only by default
# View synced PRs
aitrackdown list --type pr
```

### Using Labels

GitHub labels are mapped to tags:

```bash
# Configure label mapping
aitrackdown sync config github --key label_mapping \
  --value '{"bug": "type:bug", "feature": "enhancement", "urgent": "priority:high"}'

# Create item with tags that map to GitHub labels
aitrackdown create "Memory leak issue" --tags bug urgent

# After push, GitHub issue will have labels: "type:bug", "priority:high"
```

### Status Mapping

Map AI Trackdown statuses to GitHub states:

```bash
# GitHub only has "open" and "closed" states
# Configure mapping
aitrackdown sync config github --key status_mapping \
  --value '{"open": "open", "in_progress": "open", "completed": "closed", "cancelled": "closed"}'
```

## Advanced Features

### Filtering

Control what gets synced:

```bash
# Only sync specific labels (future feature)
aitrackdown sync platform github pull --labels "bug,feature"

# Exclude certain labels (future feature)
aitrackdown sync platform github pull --exclude-labels "wontfix,duplicate"
```

### Batch Operations

For repositories with many issues:

```bash
# Configure larger batch size
aitrackdown sync config github --key batch_size --value 100

# Pull with progress indicator
aitrackdown sync platform github pull
```

### Dry Run Mode

Always preview changes:

```bash
# Preview what would be pulled
aitrackdown sync platform github pull --dry-run

# Preview what would be pushed
aitrackdown sync platform github push --dry-run
```

## Field Mappings

### From GitHub to AI Trackdown

| GitHub Field | AI Trackdown Field | Notes |
|--------------|-------------------|-------|
| `title` | `title` | Direct mapping |
| `body` | `description` | Markdown preserved |
| `state` | `status` | open → open, closed → completed |
| `labels` | `tags` | Label names become tags |
| `assignees` | `assignees` | GitHub usernames |
| `created_at` | `created_at` | Timezone preserved |
| `updated_at` | `updated_at` | Timezone preserved |
| `number` | `metadata.github_number` | Issue/PR number |
| `html_url` | `metadata.github_url` | Web URL |

### From AI Trackdown to GitHub

| AI Trackdown Field | GitHub Field | Notes |
|-------------------|--------------|-------|
| `title` | `title` | Direct mapping |
| `description` | `body` | Markdown preserved |
| `status` | `state` | completed/cancelled → closed |
| `tags` | `labels` | Creates labels if needed |
| `assignees` | `assignees` | Must be valid GitHub users |
| `priority` | `labels` | Adds priority label |

## Troubleshooting

### Authentication Issues

**Problem**: "Bad credentials" error

**Solutions**:
1. Check token permissions:
   ```bash
   gh auth status  # If using gh CLI
   ```

2. Regenerate token with correct scopes:
   - `repo` scope for private repositories
   - `public_repo` for public repositories only

3. Verify token in configuration:
   ```bash
   aitrackdown sync config github --list
   ```

### Repository Not Found

**Problem**: "Repository not found" error

**Solutions**:
1. Check repository format:
   ```bash
   # Correct format: owner/repo
   aitrackdown sync config github --key repository --value octocat/hello-world
   ```

2. Verify repository access:
   ```bash
   gh repo view owner/repo
   ```

### Rate Limiting

**Problem**: "API rate limit exceeded" error

**Solutions**:
1. Check rate limit status:
   ```bash
   gh api rate_limit
   ```

2. Use authentication (increases limit from 60 to 5000/hour):
   ```bash
   gh auth login
   ```

3. Reduce batch size:
   ```bash
   aitrackdown sync config github --key batch_size --value 25
   ```

### Missing Items

**Problem**: Some GitHub issues don't appear after sync

**Possible Causes**:
1. **Closed issues**: By default, only open issues are synced
2. **Pull requests**: Synced separately with type "pr"
3. **Permissions**: Token may lack access to private issues
4. **Filters**: Check if filters are applied

**Debug**:
```bash
# Check what would be synced
aitrackdown sync platform github pull --dry-run

# View sync details
aitrackdown sync platform github status
```

## Best Practices

### 1. Use Descriptive Titles

GitHub issues are searchable by title:
```bash
# Good
aitrackdown create "Fix: Login fails with special characters in password"

# Less descriptive
aitrackdown create "Login bug"
```

### 2. Leverage GitHub Labels

Map your workflow to GitHub labels:
```bash
# Set up label mapping for your workflow
aitrackdown sync config github --key label_mapping --value '{
  "bug": "type:bug",
  "feature": "type:feature", 
  "task": "type:task",
  "critical": "priority:critical",
  "high": "priority:high",
  "medium": "priority:medium",
  "low": "priority:low"
}'
```

### 3. Use Milestones for Grouping

Associate issues with GitHub milestones:
```bash
# Add milestone in metadata (future feature)
aitrackdown create "Implement user auth" \
  --metadata '{"github_milestone": "v2.0"}'
```

### 4. Regular Sync Schedule

Establish a sync routine:
```bash
#!/bin/bash
# Daily sync script
echo "Starting GitHub sync: $(date)"

# Pull latest changes
aitrackdown sync platform github pull

# Show status
aitrackdown list --format table

# Push any local changes
aitrackdown sync platform github push --dry-run
```

### 5. Handle PR References

When referencing PRs in issues:
```bash
# Create issue that references a PR
aitrackdown create "Review needed for PR #123" \
  --type issue \
  --description "Please review https://github.com/owner/repo/pull/123"
```

## GitHub-Specific Metadata

The adapter preserves GitHub-specific metadata:

```json
{
  "id": "ISS-001",
  "title": "Sample Issue",
  "metadata": {
    "github_id": "1234567890",
    "github_number": 42,
    "github_url": "https://github.com/owner/repo/issues/42",
    "github_created_by": "octocat",
    "github_labels": ["bug", "help wanted"],
    "github_milestone": "v1.0",
    "github_state": "open",
    "platform": "github"
  }
}
```

## Integration with GitHub Features

### GitHub Projects

Items synced from AI Trackdown appear in GitHub Projects automatically.

### GitHub Actions

Trigger workflows on issue/PR events:
```yaml
on:
  issues:
    types: [opened, closed, labeled]
```

### GitHub Discussions

Discussions are not currently synced but can be referenced in issues.

## Security Considerations

1. **Token Storage**: Tokens are stored in `.aitrackdown/sync.json`
   - Add to `.gitignore`
   - Use environment variables for CI/CD

2. **Token Permissions**: Use minimal required scopes
   - `public_repo` for public repositories
   - `repo` only when private access needed

3. **API URL**: Always use HTTPS
   - Verify SSL certificates for enterprise

## Example Configurations

### Open Source Project

```json
{
  "github": {
    "repository": "myorg/opensource-project",
    "batch_size": 100,
    "label_mapping": {
      "bug": "bug",
      "feature": "enhancement",
      "docs": "documentation",
      "help": "help wanted"
    }
  }
}
```

### Private Enterprise Project

```json
{
  "github": {
    "repository": "enterprise/internal-tool",
    "token": "ghp_xxxxxxxxxxxxx",
    "api_url": "https://github.company.com/api/v3",
    "timeout": 60,
    "status_mapping": {
      "open": "open",
      "in_progress": "open",
      "in_review": "open",
      "completed": "closed"
    }
  }
}
```

### Multi-Repository Setup

For managing multiple repositories, create separate configurations:

```bash
# Repository 1
cd ~/projects/frontend
aitrackdown init
aitrackdown sync config github --key repository --value myorg/frontend

# Repository 2
cd ~/projects/backend
aitrackdown init
aitrackdown sync config github --key repository --value myorg/backend
```

## Limitations

1. **Binary Attachments**: Not synced (GitHub uses Git LFS)
2. **Issue Comments**: Read-only in current version
3. **PR Creation**: Requires existing branch
4. **GitHub Emojis**: Preserved but not interpreted
5. **Issue Templates**: Not automatically applied

## Future Enhancements

Planned features for GitHub adapter:

1. Comment synchronization
2. PR creation support
3. Milestone management
4. Project board integration
5. Webhook support for real-time sync
6. GitHub App authentication
7. Issue template support
8. Reaction sync