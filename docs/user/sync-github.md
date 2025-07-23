# GitHub Sync Guide

The AI Trackdown PyTools includes powerful GitHub integration features that allow you to sync your local tasks with GitHub issues and pull requests.

## Prerequisites

1. **GitHub CLI (gh)**: The sync functionality uses the GitHub CLI, which must be installed and authenticated:
   ```bash
   # Install GitHub CLI
   brew install gh  # macOS
   # or see: https://cli.github.com/manual/installation

   # Authenticate
   gh auth login
   ```

2. **Git Repository**: Your project must be a git repository with a GitHub remote.

## Basic Usage

### Check Sync Status

```bash
aitrackdown sync github status
# or specify repository explicitly
aitrackdown sync github status --repo owner/repo
```

This shows:
- Current repository
- Last sync timestamp
- Authentication status
- Local task counts (issues and PRs)

### Push Local Tasks to GitHub

Push your local tasks to GitHub as issues or pull requests:

```bash
# Dry run - see what would be created
aitrackdown sync github push --dry-run

# Actually create GitHub issues/PRs
aitrackdown sync github push

# Specify repository explicitly
aitrackdown sync github push --repo owner/repo
```

**Note**: 
- Only tasks tagged with `issue` will be created as GitHub issues
- Only tasks tagged with `pull-request` will be created as GitHub PRs
- Tasks that already have a `github_id` in their metadata will be skipped
- Created issues/PRs will be updated with GitHub metadata for future syncing

### Pull GitHub Issues to Local

Import GitHub issues as local tasks:

```bash
# Dry run - see what would be imported
aitrackdown sync github pull --dry-run

# Actually import GitHub issues
aitrackdown sync github pull

# Specify repository
aitrackdown sync github pull --repo owner/repo
```

**Note**:
- Imports all open issues from GitHub
- Updates existing tasks if they have matching `github_id`
- Creates new tasks for issues not yet tracked locally
- Preserves GitHub metadata (issue number, URL, etc.)

## Advanced Usage

### Configure Sync Settings

Store repository configuration for easier use:

```bash
# List current configuration
aitrackdown sync config github --list

# Set default repository
aitrackdown sync config github --key repo --value owner/repo

# Set custom API URL (for GitHub Enterprise)
aitrackdown sync config github --key api_url --value https://github.company.com/api/v3
```

### Import/Export Data

Import issues from other sources:

```bash
# Import from GitHub JSON export
aitrackdown sync import-data github-json issues_export.json

# Import from CSV
aitrackdown sync import csv tasks.csv --type issue

# Export to various formats
aitrackdown sync export json --output tasks.json
aitrackdown sync export csv --output tasks.csv --type issue
aitrackdown sync export github-json --output github_issues.json
```

## Task Metadata

When syncing with GitHub, the following metadata is stored:

- `github_id`: Unique GitHub ID for the issue/PR
- `github_number`: Issue/PR number (e.g., #123)
- `github_url`: Direct link to the issue/PR
- `github_created`: When the issue/PR was created on GitHub
- `github_updated`: Last update time on GitHub
- `imported_from`: Set to "github" for imported issues

## Best Practices

1. **Use Dry Run First**: Always test with `--dry-run` before actual syncing
2. **Regular Syncing**: Set up a regular sync schedule to keep tasks in sync
3. **Tag Appropriately**: Ensure tasks are properly tagged as `issue` or `pull-request`
4. **Commit Before Sync**: Commit your local changes before syncing
5. **Review After Import**: Review imported issues and adjust as needed

## Troubleshooting

### Authentication Issues

If you see "GitHub CLI is not authenticated":
```bash
gh auth status  # Check current auth
gh auth login   # Re-authenticate
```

### Repository Detection

If the repository isn't detected automatically:
1. Ensure you're in a git repository
2. Check that you have a GitHub remote: `git remote -v`
3. Explicitly specify with `--repo owner/repo`

### Sync Conflicts

If a task exists both locally and on GitHub:
- Pull will update the local task with GitHub data
- Push will skip tasks that already have a `github_id`
- To force update, remove the `github_id` from metadata

## Examples

### Complete Workflow Example

```bash
# 1. Initialize project
aitrackdown init

# 2. Create some issues
aitrackdown create "Implement user authentication" --type issue
aitrackdown create "Add API documentation" --type issue

# 3. Check what would be synced
aitrackdown sync github push --dry-run

# 4. Push to GitHub
aitrackdown sync github push

# 5. Later, pull any new issues from GitHub
aitrackdown sync github pull

# 6. Check sync status
aitrackdown sync github status
```

### PR Workflow Example

```bash
# 1. Create a PR task with branch info
aitrackdown create "Add login feature" --type pr

# 2. Edit the task to add metadata
# Add to metadata:
#   head_branch: feature/login
#   base_branch: main

# 3. Push to create GitHub PR
aitrackdown sync github push
```

Note: PR creation requires that the head branch exists on GitHub.