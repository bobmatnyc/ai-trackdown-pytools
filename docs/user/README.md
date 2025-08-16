# AI Trackdown PyTools - User Guide

Welcome to the user documentation for AI Trackdown PyTools, a modern CLI tool for project tracking and task management.

## Quick Start

1. **Install**: `pip install ai-trackdown-pytools` or `pipx install ai-trackdown-pytools`
2. **Initialize**: `aitrackdown init project`
3. **Create tasks**: `aitrackdown create task "My first task"`
4. **View status**: `aitrackdown status`

## 📚 User Documentation

### Installation
- [Homebrew Installation](./HOMEBREW_INSTALL.md) - Install via Homebrew (macOS/Linux)
- [Homebrew Formula](./HOMEBREW_FORMULA.md) - Technical details about the Homebrew formula
- [Homebrew README](./HOMEBREW_README.md) - Additional Homebrew information

### Usage Guides
- [CLI Command Reference](./CLI_IMPLEMENTATION_SUMMARY.md) - Complete command documentation
- [Ticket Type Conversion](./ticket-conversion.md) - Converting between task, issue, and epic types

### Platform Integration
- [Sync Guide](./sync/README.md) - Sync with GitHub, ClickUp, and Linear platforms

## Key Features

- **Modern CLI Experience**: Built with Typer and Rich for beautiful terminal output
- **Hierarchical Task Management**: Organize tasks, epics, issues, and PRs
- **Workflow States**: Comprehensive state management (OPEN, IN_PROGRESS, BLOCKED, etc.)
- **Platform Sync**: Sync with GitHub, ClickUp, and Linear
- **Template System**: Create and share custom templates
- **Search & Filtering**: Advanced search across all your tasks
- **Git Integration**: Automatic commit tracking and branch management

## Common Commands

```bash
# Project management
aitrackdown init project
aitrackdown status
aitrackdown health

# Task management
aitrackdown create task "New feature"
aitrackdown transition TSK-001 IN_PROGRESS
aitrackdown show TSK-001

# Platform sync
aitrackdown sync list-available
aitrackdown sync platform github status
aitrackdown sync platform github pull

# Search and filtering
aitrackdown search "authentication"
aitrackdown status tasks --status IN_PROGRESS
```

## Getting Help

- Use `aitrackdown --help` for command overview
- Use `aitrackdown <command> --help` for specific command help
- Use `aitrackdown doctor` to diagnose issues
- Check the [CLI Command Reference](./CLI_IMPLEMENTATION_SUMMARY.md) for detailed documentation

## Version Information

Current version: 1.5.2
For release history, see [CHANGELOG.md](../../CHANGELOG.md)