# Homebrew Tap for AI Trackdown Tools

This is a Homebrew tap that provides easy installation of AI Trackdown PyTools and related utilities.

## Installation

```bash
# Add the tap
brew tap bobmatnyc/tools

# Install AI Trackdown PyTools
brew install ai-trackdown-pytools
```

## Available Packages

### AI Trackdown PyTools

Python CLI tools for AI project tracking and task management.

**Commands provided:**
- `aitrackdown` - Main CLI interface
- `atd` - Short alias for aitrackdown

**Features:**
- Complete project tracking and task management
- AI-powered ticket creation and management
- Git integration for project context
- Template-based workflow automation
- Rich CLI interface with syntax highlighting
- Shell completions for Zsh and Fish

## Quick Start

After installation, initialize a new project:

```bash
# Initialize a new AI Trackdown project
aitrackdown init project --name "My Project"

# Create a new task
aitrackdown create task --title "Implement feature X"

# Check project status
aitrackdown status

# Get help
aitrackdown --help
```

## Requirements

- macOS 10.15+ or Linux
- Python 3.11+ (automatically managed by Homebrew)
- Git (for project context features)

## Support

- **GitHub Repository**: [ai-trackdown-pytools](https://github.com/bobmatnyc/ai-trackdown-pytools)
- **Issues**: Report issues on the main repository
- **Documentation**: See the main repository for comprehensive documentation

## Development

This tap is maintained alongside the main AI Trackdown PyTools project. Formula updates are automatically managed through the release process.

### Local Development

```bash
# Test the formula locally
brew install --build-from-source ./Formula/ai-trackdown-pytools.rb

# Debug installation issues
brew install --verbose --debug ./Formula/ai-trackdown-pytools.rb

# Audit the formula
brew audit --strict ./Formula/ai-trackdown-pytools.rb
```

## License

MIT License - see the individual package repositories for details.