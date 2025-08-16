# Sync Adapter System Usage

## Overview

The AI Trackdown sync system has been refactored to use an adapter pattern, providing a flexible and extensible way to sync with multiple external platforms while maintaining backward compatibility.

## Basic Usage

### List Available Platforms

```bash
# List all available sync platforms
aitrackdown sync list-available

# Alternative method
aitrackdown sync platform list platforms
```

### Platform-Specific Sync

```bash
# New unified command structure
aitrackdown sync platform <platform> <action> [options]

# Examples:
aitrackdown sync platform github pull
aitrackdown sync platform github push --dry-run
aitrackdown sync platform github status
```

### Convenience Shortcuts

For backward compatibility and convenience, shortcut commands are available:

```bash
# Pull from a platform (defaults to GitHub)
aitrackdown sync pull [platform]

# Push to a platform (defaults to GitHub)
aitrackdown sync push [platform]

# Check sync status
aitrackdown sync status [platform]
```

### Legacy GitHub Command

The original GitHub-specific command is maintained for backward compatibility:

```bash
# Deprecated but still functional
aitrackdown sync github <action> [options]
```

## Configuration

### Configure Platform Settings

```bash
# View configuration for a platform
aitrackdown sync config <platform> --list

# Set configuration values
aitrackdown sync config github --key repository --value owner/repo
aitrackdown sync config github --key token --value your-token

# Platform-specific configuration keys
aitrackdown sync config <platform>  # Shows available keys
```

## Supported Platforms

Currently supported platforms:
- **github** - GitHub Issues and Pull Requests

Future platforms (adapter ready):
- **gitlab** - GitLab Issues and Merge Requests
- **clickup** - ClickUp Tasks
- **linear** - Linear Issues
- **jira** - JIRA Issues

## Examples

### GitHub Sync Workflow

```bash
# 1. Configure GitHub repository
aitrackdown sync config github --key repository --value myorg/myrepo

# 2. Check sync status
aitrackdown sync status github

# 3. Pull issues from GitHub
aitrackdown sync pull github

# 4. Create local tasks
aitrackdown create "New feature request" --type issue

# 5. Push new tasks to GitHub
aitrackdown sync push github --dry-run  # Preview first
aitrackdown sync push github            # Actually push
```

### Multi-Platform Workflow

```bash
# Configure multiple platforms
aitrackdown sync config github --key repository --value myorg/myrepo
aitrackdown sync config clickup --key workspace_id --value 12345

# Pull from all configured platforms
aitrackdown sync pull github
aitrackdown sync pull clickup

# Push to specific platform
aitrackdown sync push github
```

## Dry Run Mode

Always use `--dry-run` to preview sync operations:

```bash
aitrackdown sync platform github pull --dry-run
aitrackdown sync platform github push --dry-run
```

## Troubleshooting

### Platform Not Found

If you see "Platform not supported", use:
```bash
aitrackdown sync list-available
```

### Authentication Issues

For GitHub:
- Ensure `gh` CLI is installed and authenticated
- Or provide a token: `--token <your-token>`

### Configuration Issues

View current configuration:
```bash
aitrackdown sync config <platform> --list
```