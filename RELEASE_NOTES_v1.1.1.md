# Release Notes - v1.1.1

**Release Date**: 2025-07-23

## Overview

AI Trackdown PyTools v1.1.1 is a patch release that adds GitHub synchronization capabilities and fixes several important bugs identified in v1.1.0. This release enhances the tool's integration with external platforms while improving overall stability.

## Key Features

### GitHub Synchronization
- **New sync commands**: Bidirectional sync with GitHub issues and pull requests
  - `aitrackdown sync github pull` - Pull issues from GitHub
  - `aitrackdown sync github push` - Push local tasks to GitHub
  - `aitrackdown sync github status` - Check sync status
- **GitHub CLI integration**: Leverages `gh` CLI for robust GitHub API access
- **Sync configuration**: Persistent sync settings in `.aitrackdown/sync.json`
- **Rich metadata support**: Syncs labels, assignees, milestones, and more

### Bug Fixes
- **Task updates**: Fixed critical error when updating tasks with epic/parent relationships
- **Comment system**: Resolved file lookup issues that prevented adding comments
- **Project status**: Fixed NoneType error with empty project.yaml files
- **Error handling**: Improved error messages throughout the CLI

### Documentation Improvements
- Reorganized documentation into clear user/development/design sections
- Added index files for better navigation
- Consolidated redundant files from root directory
- Enhanced PyPI publishing guides

## Installation

```bash
# Upgrade from previous version
pip install --upgrade ai-trackdown-pytools

# Fresh installation
pip install ai-trackdown-pytools
```

## GitHub Sync Quick Start

```bash
# Configure GitHub repository
aitrackdown sync github --repo owner/repo

# Pull issues from GitHub
aitrackdown sync github pull

# Push local tasks to GitHub
aitrackdown sync github push --dry-run  # Preview first
aitrackdown sync github push

# Check sync status
aitrackdown sync github status
```

## Bug Fixes Detail

1. **Task Update Error**: Added missing `save_task` method that was causing "slice indices must be integers" errors
2. **Comment Lookup**: Improved file pattern matching to find tasks in various directory structures
3. **Project Status**: Added proper validation for empty or malformed project.yaml files

## Breaking Changes

None - This is a backward-compatible patch release.

## Migration Notes

No migration required. Simply upgrade to the latest version.

## Known Issues

- GitHub sync requires `gh` CLI to be installed and authenticated
- Large repositories may experience slower sync times on first pull

## Coming Next

- GitLab synchronization support
- Jira integration
- Enhanced filtering and search capabilities
- Performance improvements for large projects

## Contributors

Thanks to all contributors who reported issues and provided feedback for this release.

## Support

- Documentation: https://github.com/yourusername/ai-trackdown-pytools
- Issues: https://github.com/yourusername/ai-trackdown-pytools/issues
- PyPI: https://pypi.org/project/ai-trackdown-pytools/