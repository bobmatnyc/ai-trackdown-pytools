# AI Trackdown PyTools Documentation

Welcome to the documentation for AI Trackdown PyTools, a modern CLI tool for AI project tracking and task management.

## Quick Start

- **Installation**: See [Installation Guide](user/HOMEBREW_INSTALL.md)
- **First Steps**: Check out the [User Guide](user/README.md)
- **Command Reference**: Browse the [CLI Command Reference](user/CLI_IMPLEMENTATION_SUMMARY.md)

## Documentation Sections

### 📖 User Documentation
Essential guides for using AI Trackdown PyTools:

- [**User Guide**](user/README.md) - Getting started and basic usage
- [**CLI Command Reference**](user/CLI_IMPLEMENTATION_SUMMARY.md) - Complete command documentation
- [**Installation Guide**](user/HOMEBREW_INSTALL.md) - Installation instructions
- [**Platform Sync Guide**](user/sync/README.md) - Syncing with GitHub, ClickUp, and Linear
- [**Ticket Conversion**](user/ticket-conversion.md) - Converting between ticket types

### 🔧 Development Documentation
For contributors and developers:

- [**Contributing Guide**](development/CONTRIBUTING.md) - How to contribute
- [**Testing Guide**](development/CLI_TESTING_GUIDE.md) - Running and writing tests
- [**Sync Adapter Development**](development/sync-adapter-developer-guide.md) - Creating new platform adapters
- [**Release Process**](development/PYPI_MANUAL_PUBLISHING_GUIDE.md) - Publishing releases

### 🏗️ Design Documentation
Architecture and design decisions:

- [**Design Index**](design/index.md) - Design documentation overview

## Getting Help

### Common Commands
```bash
# Get help for any command
aitrackdown --help
aitrackdown create --help

# Check system health
aitrackdown doctor

# Get version information
aitrackdown --version
```

### Support Resources
- **Issues**: [GitHub Issues](https://github.com/bobmatnyc/ai-trackdown-pytools/issues)
- **Discussions**: [GitHub Discussions](https://github.com/bobmatnyc/ai-trackdown-pytools/discussions)
- **Documentation**: This documentation site

## Project Information

- **Current Version**: 1.5.2
- **License**: MIT
- **Repository**: [GitHub](https://github.com/bobmatnyc/ai-trackdown-pytools)
- **PyPI Package**: [ai-trackdown-pytools](https://pypi.org/project/ai-trackdown-pytools/)

## Key Features

- 🚀 **Modern CLI Experience** - Built with Typer and Rich
- 📋 **Hierarchical Task Management** - Tasks, epics, issues, and PRs
- 🔍 **Advanced Search** - Filter by status, assignee, tags, and more
- 🔄 **Platform Sync** - GitHub, ClickUp, and Linear integration
- 🎨 **Rich Terminal Output** - Beautiful tables and progress bars
- 🌐 **Multi-Project Support** - Manage multiple projects
- 📊 **Workflow States** - Comprehensive status management

---

*For the most up-to-date information, always refer to the main [README.md](../README.md) in the project root.*
