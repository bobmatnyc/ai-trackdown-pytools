# AI Trackdown PyTools

[![PyPI - Version](https://img.shields.io/pypi/v/ai-trackdown-pytools.svg)](https://pypi.org/project/ai-trackdown-pytools/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ai-trackdown-pytools.svg)](https://pypi.org/project/ai-trackdown-pytools/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/ai-trackdown-pytools)](https://pypi.org/project/ai-trackdown-pytools/)
[![CI Status](https://github.com/ai-trackdown/ai-trackdown-pytools/workflows/CI/badge.svg)](https://github.com/ai-trackdown/ai-trackdown-pytools/actions)
[![Coverage Status](https://codecov.io/gh/ai-trackdown/ai-trackdown-pytools/branch/main/graph/badge.svg)](https://codecov.io/gh/ai-trackdown/ai-trackdown-pytools)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Modern Python CLI tools for AI project tracking and task management**

AI Trackdown PyTools brings powerful project management capabilities to your terminal, specifically designed for AI and software development workflows. With beautiful terminal output, intuitive commands, and seamless Git integration, it's the perfect companion for managing complex projects.

## Why AI Trackdown PyTools?

- **🎯 Purpose-Built for AI Projects**: Designed specifically for managing AI and ML project workflows
- **⚡ Fast and Lightweight**: Minimal dependencies, instant startup, no bloat
- **🎨 Beautiful Terminal UI**: Rich formatting, colors, and interactive prompts that make CLI work enjoyable
- **🔧 Extensible Architecture**: Plugin-ready design with customizable templates and workflows
- **🔍 Smart Filtering**: Powerful search and filter capabilities across all your tasks and projects
- **📊 Progress Tracking**: Visual progress indicators and comprehensive status reporting

## Documentation

- 📖 **[User Documentation](docs/user/index.md)** - Installation, usage guides, and command reference
- 🔧 **[Development Documentation](docs/development/index.md)** - Contributing, testing, and release procedures

## Key Features

- 🚀 **Modern CLI Experience** - Built with Typer and Rich for an exceptional terminal experience
- 📋 **Hierarchical Task Management** - Organize tasks, epics, issues, and PRs with parent-child relationships
- 🏗️ **Smart Project Templates** - Pre-configured templates for common AI project structures
- 📝 **Flexible Template System** - Create and share custom templates for any workflow
- 🔍 **Advanced Search** - Filter by status, assignee, tags, priority, and custom fields
- 🎯 **Schema Validation** - Ensure data integrity with JSON schema validation
- 🔧 **Deep Git Integration** - Automatic commit tracking, branch management, and PR linking
- 🔄 **GitHub Sync** - Sync tasks with GitHub issues and pull requests bidirectionally
- 🎨 **Rich Terminal Output** - Tables, progress bars, syntax highlighting, and more
- 🌐 **Multi-Project Support** - Manage multiple projects from a single installation
- 📈 **Analytics and Reporting** - Built-in project analytics and customizable reports

## Installation

### Requirements

- Python 3.8 or higher
- Git (optional, for version control features)

### Install from PyPI

```bash
pip install ai-trackdown-pytools
```

### Install with pipx (Recommended for CLI tools)

```bash
pipx install ai-trackdown-pytools
```

### Install from Source

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

### Verify Installation

```bash
aitrackdown --version
aitrackdown --help
```

## Quick Start

### 1. Initialize Your First Project

```bash
# Create a new directory for your project
mkdir my-ai-project && cd my-ai-project

# Initialize AI Trackdown with interactive setup
aitrackdown init project

# Or use a pre-configured template
aitrackdown init project --template ml-research
```

### 2. Create Your First Task

```bash
# Interactive task creation
aitrackdown create task

# Or create directly with options
aitrackdown create task "Implement data preprocessing pipeline" \
  --priority high \
  --assignee "alice@team.com" \
  --tag "data-pipeline"
```

### 3. View Project Status

```bash
# See all tasks at a glance
aitrackdown status

# Get detailed project overview
aitrackdown status project --detailed
```

## Core Commands

### AI-Friendly Mode

AI Trackdown PyTools supports a plain output mode optimized for AI tools and automated scripts:

```bash
# Use --plain flag for simplified output
aitrackdown --plain version
aitrackdown --plain info
aitrackdown --plain status

# Or set environment variable
export AITRACKDOWN_PLAIN=1
aitrackdown version

# Also respects NO_COLOR standard
export NO_COLOR=1
aitrackdown status
```

The plain mode:
- Removes all color codes and rich formatting
- Simplifies output structure for easier parsing
- Ideal for piping to other tools or AI systems
- Automatically enabled in CI environments

### Task Management

```bash
# Create a new task interactively
aitrackdown create task

# Create task with full details
aitrackdown create task "Implement authentication" \
  --description "Add JWT authentication to API endpoints" \
  --assignee "john@example.com" \
  --tag "backend" --tag "security" \
  --priority "high" \
  --due "2025-08-15"

# Create from template
aitrackdown create task --template bug-report

# Create subtask under parent
aitrackdown create task "Write unit tests" --parent TSK-0001
```

### View and Filter Tasks

```bash
# List all tasks with rich formatting
aitrackdown status tasks

# Filter by multiple criteria
aitrackdown status tasks \
  --status open \
  --assignee "john@example.com" \
  --tag "backend" \
  --priority high

# Search tasks by keyword
aitrackdown search "authentication" --type task

# Show task details
aitrackdown show TSK-0001

# Update task status
aitrackdown update TSK-0001 --status in-progress
```

### Template Management

```bash
# List all available templates
aitrackdown template list

# Show template details
aitrackdown template show bug-report --type task

# Create custom template interactively
aitrackdown template create

# Create template from existing task
aitrackdown template create --from TSK-0001 --name "feature-template"

# Share template
aitrackdown template export feature-template --output feature.yaml
aitrackdown template import feature.yaml
```

### GitHub Sync

```bash
# Check sync status
aitrackdown sync github status

# Push local issues to GitHub (dry-run first)
aitrackdown sync github push --dry-run
aitrackdown sync github push

# Pull GitHub issues to local tasks
aitrackdown sync github pull --dry-run
aitrackdown sync github pull

# Specify repository explicitly
aitrackdown sync github push --repo owner/repo
```

## Complete Command Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|----------|
| `init` | Initialize project or configuration | `aitrackdown init project` |
| `create` | Create tasks, issues, epics, PRs | `aitrackdown create task "New feature"` |
| `status` | Show project and task status | `aitrackdown status tasks --open` |
| `update` | Update existing items | `aitrackdown update TSK-0001 --status done` |
| `show` | Display detailed information | `aitrackdown show TSK-0001` |
| `search` | Search across all items | `aitrackdown search "bug" --type issue` |
| `template` | Manage templates | `aitrackdown template list` |

### Advanced Commands

| Command | Description | Example |
|---------|-------------|----------|
| `epic` | Manage epic tasks | `aitrackdown epic create "Q3 Features"` |
| `pr` | Create and link pull requests | `aitrackdown pr create --branch feature/auth` |
| `migrate` | Migrate from other tools | `aitrackdown migrate --from jira` |
| `sync` | Sync with GitHub issues/PRs | `aitrackdown sync github push` |
| `report` | Generate reports | `aitrackdown report weekly --format html` |

### Utility Commands

| Command | Description | Example |
|---------|-------------|----------|
| `info` | System information | `aitrackdown info` |
| `health` | Health check | `aitrackdown health --verbose` |
| `config` | Configuration management | `aitrackdown config set editor.default "vim"` |
| `export` | Export data | `aitrackdown export --format json` |

### Quick Aliases

- `atd` → `aitrackdown`
- `atd-init` → `aitrackdown init`
- `atd-create` → `aitrackdown create`
- `atd-status` → `aitrackdown status`

## Project Structure

```
my-project/
├── .ai-trackdown/          # Configuration and templates
│   ├── config.yaml         # Project configuration
│   ├── project.yaml        # Project metadata
│   ├── templates/          # Custom templates
│   └── schemas/            # Custom schemas
├── tickets/                # Ticket files organized by type
│   ├── tasks/             # Standard tasks (TSK-XXXX)
│   ├── epics/             # Epic tasks (EP-XXXX)
│   ├── issues/            # Issues and bugs (ISS-XXXX)
│   └── prs/               # Pull requests (PR-XXXX)
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

## Real-World Examples

### Managing an ML Research Project

```bash
# Initialize ML research project
aitrackdown init project --template ml-research

# Create research epic
aitrackdown create epic "Experiment: Vision Transformer Fine-tuning" \
  --goal "Achieve 95% accuracy on custom dataset"

# Create subtasks
aitrackdown create task "Prepare dataset" --parent EPIC-0001 --assignee "data-team"
aitrackdown create task "Implement model architecture" --parent EPIC-0001
aitrackdown create task "Run baseline experiments" --parent EPIC-0001

# Track experiment results
aitrackdown update TSK-0003 --add-note "Baseline accuracy: 87.3%"
```

### Bug Tracking Workflow

```bash
# Report a bug
aitrackdown create issue "Model inference crashes on GPU" \
  --type bug \
  --severity critical \
  --component "inference-engine" \
  --affects-version "2.1.0"

# Link to PR
aitrackdown create pr "Fix GPU memory leak in inference" \
  --fixes BUG-0001 \
  --branch hotfix/gpu-memory-leak
```

### Sprint Planning

```bash
# Create sprint epic
aitrackdown create epic "Sprint 23: Authentication & API" \
  --start "2025-08-01" \
  --end "2025-08-14"

# Bulk assign tasks to sprint
aitrackdown update --tag "sprint-23" --bulk TSK-0001,TSK-0002,TSK-0003

# View sprint progress
aitrackdown status sprint --id 23
```

### Git Integration

Seamlessly integrate with your Git workflow:

```bash
# Initialize with Git integration
aitrackdown init project --git

# Auto-link commits to tasks
git commit -m "feat: Add user authentication

Implements TSK-0001
Co-authored-by: AI Trackdown <ai@trackdown.com>"

# Create PR with task linking
aitrackdown pr create \
  --title "Add authentication system" \
  --implements TSK-0001,TSK-0002 \
  --reviewers "alice,bob"

# Auto-close tasks on merge
aitrackdown config set git.auto_close_on_merge true
```

### Data Validation and Quality

```bash
# Validate all project data
aitrackdown validate

# Validate specific template
aitrackdown template validate feature-template

# Check project health
aitrackdown health --verbose

# Audit project for issues
aitrackdown audit --fix
```

## Plugin System (Coming Soon)

```python
# Example custom plugin
from ai_trackdown_pytools.plugins import Plugin

class JiraImporter(Plugin):
    """Import tasks from Jira."""
    
    def execute(self, context):
        # Implementation here
        pass

# Register and use
aitrackdown plugin install jira-importer
aitrackdown import --from jira --project "PROJ"
```

## Contributing

We love contributions! AI Trackdown PyTools is a community-driven project, and we welcome contributions of all kinds.

### Ways to Contribute

- 🐛 **Report bugs** and suggest features
- 📖 **Improve documentation** and examples  
- 🧪 **Write tests** and improve coverage
- 🎨 **Create templates** for common workflows
- 💻 **Submit pull requests** with enhancements

See our [Contributing Guide](CONTRIBUTING.md) for detailed instructions.

### Quick Development Setup

```bash
# Clone and setup
git clone https://github.com/ai-trackdown/ai-trackdown-pytools.git
cd ai-trackdown-pytools
pip install -e .[dev]
pre-commit install

# Run tests
pytest

# Format code
black src tests
ruff check src tests --fix
```

## Support

### Getting Help

- 📚 [Documentation](https://ai-trackdown-pytools.readthedocs.io/)
- 💬 [Discussions](https://github.com/ai-trackdown/ai-trackdown-pytools/discussions)
- 🐛 [Issue Tracker](https://github.com/ai-trackdown/ai-trackdown-pytools/issues)
- 📧 Email: support@ai-trackdown.com

### Community

- [Discord Server](https://discord.gg/ai-trackdown)
- [Twitter/X](https://twitter.com/aitrackdown)
- [Blog](https://blog.ai-trackdown.com)

## License

AI Trackdown PyTools is open source software licensed under the [MIT License](LICENSE).

## Acknowledgments

- Inspired by the original [ai-trackdown-tools](https://github.com/ai-trackdown/ai-trackdown-tools)
- Built with [Typer](https://typer.tiangolo.com/) for an exceptional CLI experience
- Uses [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- Powered by [Pydantic](https://pydantic-docs.helpmanual.io/) for robust data validation
- Special thanks to all [contributors](https://github.com/ai-trackdown/ai-trackdown-pytools/graphs/contributors)

## Links

- 🏠 [Homepage](https://ai-trackdown.com)
- 📦 [PyPI Package](https://pypi.org/project/ai-trackdown-pytools/)
- 🐙 [GitHub Repository](https://github.com/ai-trackdown/ai-trackdown-pytools)
- 📖 [Documentation](https://ai-trackdown-pytools.readthedocs.io/)
- 📋 [Changelog](CHANGELOG.md)
- 🗺️ [Roadmap](https://github.com/ai-trackdown/ai-trackdown-pytools/projects/1)

---

<p align="center">
  Made with ❤️ by the AI Trackdown Team
</p>