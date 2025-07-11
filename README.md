# AI Trackdown PyTools

[![CI](https://github.com/ai-trackdown/ai-trackdown-pytools/workflows/CI/badge.svg)](https://github.com/ai-trackdown/ai-trackdown-pytools/actions)
[![Coverage](https://codecov.io/gh/ai-trackdown/ai-trackdown-pytools/branch/main/graph/badge.svg)](https://codecov.io/gh/ai-trackdown/ai-trackdown-pytools)
[![Python](https://img.shields.io/pypi/pyversions/ai-trackdown-pytools.svg)](https://pypi.org/project/ai-trackdown-pytools/)
[![Version](https://img.shields.io/pypi/v/ai-trackdown-pytools.svg)](https://pypi.org/project/ai-trackdown-pytools/)

Python CLI tools for AI project tracking and task management. A Python port of the popular ai-trackdown-tools with enhanced features and modern Python packaging.

## Features

- 🚀 **Modern CLI** - Built with Typer and Rich for beautiful terminal output
- 📋 **Task Management** - Create, track, and manage tasks with hierarchical organization
- 🏗️ **Project Structure** - Initialize and manage AI project structures
- 📝 **Templates** - Customizable templates for tasks, issues, epics, and PRs
- 🔍 **Smart Search** - Find and filter tasks with powerful search capabilities
- 🎯 **Schema Validation** - JSON schema validation for data integrity
- 🔧 **Git Integration** - Seamless integration with Git workflows
- 🎨 **Rich Output** - Beautiful terminal output with colors and formatting

## Installation

### From PyPI (Recommended)

```bash
pip install ai-trackdown-pytools
```

### From Source

```bash
git clone https://github.com/ai-trackdown/ai-trackdown-pytools.git
cd ai-trackdown-pytools
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/ai-trackdown/ai-trackdown-pytools.git
cd ai-trackdown-pytools
pip install -e .[dev]
pre-commit install
```

## Quick Start

### Initialize a Project

```bash
# Initialize AI Trackdown project in current directory
aitrackdown init project

# Initialize with custom template
aitrackdown init project --template python-project

# Initialize global configuration
aitrackdown init config --global
```

### Create Tasks

```bash
# Create a new task interactively
aitrackdown create task

# Create task with details
aitrackdown create task "Implement authentication" \
  --description "Add JWT authentication to API" \
  --assignee "john@example.com" \
  --tag "backend" \
  --priority "high"

# Create from template
aitrackdown create task --template bug-report
```

### Manage Tasks

```bash
# List all tasks
aitrackdown status tasks

# Filter by status
aitrackdown status tasks --status open

# Filter by assignee
aitrackdown status tasks --assignee "john@example.com"

# Show project overview
aitrackdown status project
```

### Templates

```bash
# List available templates
aitrackdown template list

# Show template details
aitrackdown template show default --type task

# Create custom template
aitrackdown template create my-template --type task

# Apply template
aitrackdown template apply my-template
```

## Commands Reference

### Core Commands

- `aitrackdown init` - Initialize projects and configuration
- `aitrackdown status` - Show project and task status
- `aitrackdown create` - Create tasks, issues, epics, and PRs
- `aitrackdown template` - Manage and apply templates

### Utility Commands

- `aitrackdown info` - Show system information
- `aitrackdown health` - Check system health and dependencies

### Command Aliases

- `atd` - Short alias for `aitrackdown`
- `aitrackdown-init` - Direct access to init commands
- `aitrackdown-status` - Direct access to status commands
- `aitrackdown-create` - Direct access to create commands
- `aitrackdown-template` - Direct access to template commands

## Project Structure

```
my-project/
├── .ai-trackdown/          # Configuration and templates
│   ├── config.yaml         # Project configuration
│   ├── project.yaml        # Project metadata
│   ├── templates/          # Custom templates
│   └── schemas/            # Custom schemas
├── tasks/                  # Task files organized by type
│   ├── tsk/               # Standard tasks
│   ├── epic/              # Epic tasks
│   └── bug/               # Bug reports
├── docs/                   # Documentation
└── README.md              # Project documentation
```

## Configuration

AI Trackdown PyTools uses YAML configuration files:

### Global Configuration (`~/.ai-trackdown/config.yaml`)

```yaml
version: "1.0.0"
editor:
  default: "code"  # Default editor for task editing
templates:
  directory: "templates"
git:
  auto_commit: false
  commit_prefix: "[ai-trackdown]"
```

### Project Configuration (`.ai-trackdown/config.yaml`)

```yaml
version: "1.0.0"
project:
  name: "My Project"
  description: "Project description"
  version: "1.0.0"
tasks:
  directory: "tasks"
  auto_id: true
  id_format: "TSK-{counter:04d}"
templates:
  directory: "templates"
```

## Templates

Templates are powerful tools for standardizing task creation:

### Task Template Example

```yaml
name: "Bug Report Template"
description: "Template for bug reports"
type: "task"
version: "1.0.0"

variables:
  severity:
    description: "Bug severity"
    default: "medium"
    choices: ["low", "medium", "high", "critical"]
  component:
    description: "Affected component"
    required: true

content: |
  # Bug: {{ title }}
  
  ## Description
  {{ description }}
  
  ## Severity
  {{ severity }}
  
  ## Affected Component
  {{ component }}
  
  ## Steps to Reproduce
  1. 
  2. 
  3. 
  
  ## Expected Behavior
  
  ## Actual Behavior
  
  ## Environment
  - OS: 
  - Browser: 
  - Version: 
```

## Advanced Usage

### Custom Task Types

Create custom task types with specific templates and workflows:

```bash
# Create epic
aitrackdown create epic "User Authentication System" \
  --goal "Implement complete authentication flow"

# Create issue
aitrackdown create issue "Login button not responsive" \
  --type bug \
  --severity high

# Create PR task
aitrackdown create pr "Add authentication middleware" \
  --branch feature/auth \
  --target main
```

### Integration with Git

AI Trackdown PyTools integrates seamlessly with Git:

```bash
# Initialize project with Git
aitrackdown init project --git

# Auto-commit task changes (when configured)
aitrackdown create task "New feature" # Auto-commits if enabled

# Link tasks to commits
git commit -m "Implement feature X

Closes TSK-0001"
```

### Schema Validation

All tasks are validated against JSON schemas:

```bash
# Validate template
aitrackdown template validate my-template

# Check project health (includes schema validation)
aitrackdown health
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/ai-trackdown/ai-trackdown-pytools.git
cd ai-trackdown-pytools

# Install development dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
black src tests
ruff check src tests
mypy src
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by the original [ai-trackdown-tools](https://github.com/ai-trackdown/ai-trackdown-tools)
- Built with [Typer](https://typer.tiangolo.com/) for CLI
- Uses [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- Powered by [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation

## Links

- [Documentation](https://ai-trackdown-pytools.readthedocs.io/)
- [PyPI Package](https://pypi.org/project/ai-trackdown-pytools/)
- [GitHub Repository](https://github.com/ai-trackdown/ai-trackdown-pytools)
- [Issue Tracker](https://github.com/ai-trackdown/ai-trackdown-pytools/issues)
- [Changelog](CHANGELOG.md)