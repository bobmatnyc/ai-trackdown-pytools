# Homebrew Installation Guide

## Quick Start

### Install via Homebrew (Recommended)

```bash
# Add the AI Trackdown tap
brew tap ai-trackdown/tap

# Install AI Trackdown PyTools
brew install ai-trackdown-pytools
```

### Verify Installation

```bash
# Check version
aitrackdown --version

# View available commands
aitrackdown --help

# Test with short alias
atd --help
```

### First Use

```bash
# Initialize a new project
mkdir my-project && cd my-project
aitrackdown init project

# Create your first task
aitrackdown create task "Set up development environment"

# Check project status
aitrackdown status project
```

## Alternative Installation Methods

### Direct Formula Installation

If you prefer not to add the tap:

```bash
# Install directly from formula file
brew install https://raw.githubusercontent.com/ai-trackdown/homebrew-tap/main/Formula/ai-trackdown-pytools.rb
```

### Install from Source

```bash
# Download and install from local formula
curl -O https://raw.githubusercontent.com/ai-trackdown/homebrew-tap/main/Formula/ai-trackdown-pytools.rb
brew install ./ai-trackdown-pytools.rb
```

## What Gets Installed

The Homebrew package includes:

- **Main CLI**: `aitrackdown` - Primary command-line interface
- **Short Alias**: `atd` - Quick access alias  
- **Specialized Commands**:
  - `aitrackdown-init` - Direct access to initialization commands
  - `aitrackdown-status` - Direct access to status commands
  - `aitrackdown-create` - Direct access to creation commands
  - `aitrackdown-template` - Direct access to template commands
- **Shell Completions**: Auto-completion for Zsh and Fish shells
- **Python Environment**: Isolated virtualenv with all dependencies

## Shell Completions

Homebrew automatically installs shell completions:

### Zsh
Completions are automatically available if you have Homebrew's completion system enabled.

### Fish
Completions are automatically installed to the Fish completions directory.

### Manual Setup
If completions don't work automatically:

```bash
# For Zsh (add to ~/.zshrc)
eval "$(_AITRACKDOWN_COMPLETE=zsh_source aitrackdown)"

# For Fish (add to ~/.config/fish/config.fish)
eval (env _AITRACKDOWN_COMPLETE=fish_source aitrackdown)
```

## Updating

```bash
# Update Homebrew and all packages
brew update && brew upgrade

# Update only AI Trackdown PyTools
brew upgrade ai-trackdown-pytools

# Check for updates
brew outdated | grep ai-trackdown-pytools
```

## Uninstalling

```bash
# Remove the package
brew uninstall ai-trackdown-pytools

# Optional: Remove the tap
brew untap ai-trackdown/tap
```

## Troubleshooting

### Installation Issues

1. **Python Dependency Error**:
   ```bash
   brew install python@3.11
   brew link python@3.11
   ```

2. **Build Failed**:
   ```bash
   # Install Xcode Command Line Tools
   xcode-select --install
   ```

3. **Permission Issues**:
   ```bash
   # Fix Homebrew permissions
   sudo chown -R $(whoami) $(brew --prefix)/*
   ```

### Runtime Issues

1. **Command Not Found**:
   ```bash
   # Check if Homebrew is in PATH
   echo $PATH | grep -q $(brew --prefix)/bin || echo "Add Homebrew to PATH"
   
   # Add to shell profile if needed
   echo 'export PATH="$(brew --prefix)/bin:$PATH"' >> ~/.zshrc
   ```

2. **Python Environment Issues**:
   ```bash
   # Reinstall to fix Python environment
   brew uninstall ai-trackdown-pytools
   brew install ai-trackdown-pytools
   ```

3. **Completions Not Working**:
   ```bash
   # Manually source completions
   source $(brew --prefix)/share/zsh/site-functions/_aitrackdown
   ```

## Getting Help

- **Command Help**: `aitrackdown --help` or `aitrackdown COMMAND --help`
- **Project Issues**: [GitHub Issues](https://github.com/ai-trackdown/ai-trackdown-pytools/issues)
- **Homebrew Issues**: [Homebrew Troubleshooting](https://docs.brew.sh/Troubleshooting)
- **Documentation**: [Full Documentation](https://ai-trackdown-pytools.readthedocs.io/)

## Next Steps

After installation, check out:

1. **[Quick Start Guide](README.md#quick-start)** - Learn basic usage
2. **[Configuration Guide](README.md#configuration)** - Customize your setup
3. **[Templates Guide](README.md#templates)** - Create custom templates
4. **[Advanced Usage](README.md#advanced-usage)** - Power user features

## Comparison with PyPI Installation

| Method | Pros | Cons |
|--------|------|------|
| **Homebrew** | ✅ System-wide installation<br>✅ Dependency management<br>✅ Easy updates<br>✅ Shell completions | ❌ macOS/Linux only<br>❌ Less control over Python version |
| **PyPI (pip)** | ✅ Works everywhere<br>✅ Virtual environment control<br>✅ Development installs | ❌ Manual dependency management<br>❌ No shell completions<br>❌ Manual updates |

Choose Homebrew for:
- **macOS/Linux systems** with Homebrew
- **System-wide availability** across users
- **Simplified management** and updates
- **Integrated shell completions**

Choose PyPI for:
- **Windows systems** or non-Homebrew environments
- **Development work** with virtual environments
- **Custom Python versions** or constraints
- **CI/CD environments** with specific requirements