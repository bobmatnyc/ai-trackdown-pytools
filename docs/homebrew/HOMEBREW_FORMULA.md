# Homebrew Formula for AI Trackdown PyTools

This document provides comprehensive instructions for installing AI Trackdown PyTools via Homebrew and setting up a Homebrew tap repository.

## Quick Installation

Once the Homebrew tap is set up, you can install AI Trackdown PyTools with:

```bash
# Install from official tap (when available)
brew install ai-trackdown/tap/ai-trackdown-pytools

# Or install directly from formula file
brew install ./ai-trackdown-pytools.rb
```

## Formula Features

The Homebrew formula provides:

- **Complete Python Environment**: Isolated virtualenv with all dependencies
- **Multiple CLI Commands**: `aitrackdown`, `atd`, and specialized sub-commands
- **Shell Completions**: Auto-generated completions for Zsh and Fish
- **Comprehensive Testing**: Validates installation and basic functionality
- **Dependency Management**: Handles all Python dependencies automatically

## Available Commands After Installation

```bash
# Main commands
aitrackdown                    # Primary CLI interface
atd                           # Short alias for aitrackdown

# Specialized commands (direct access)
aitrackdown-init              # Direct access to init commands
aitrackdown-status            # Direct access to status commands
aitrackdown-create            # Direct access to create commands
aitrackdown-template          # Direct access to template commands
```

## Setting Up a Homebrew Tap Repository

### 1. Create Tap Repository

Create a new GitHub repository named `homebrew-tap` under your organization:

```bash
# Repository name should follow Homebrew convention
https://github.com/ai-trackdown/homebrew-tap
```

### 2. Repository Structure

Your tap repository should have this structure:

```
homebrew-tap/
├── Formula/
│   └── ai-trackdown-pytools.rb    # The formula file
├── README.md                      # Tap documentation
└── LICENSE                        # License file
```

### 3. Prepare the Formula

Before publishing, you need to update the SHA256 checksum in the formula:

```bash
# Download the source package and calculate SHA256
curl -L -o ai-trackdown-pytools-0.9.0.tar.gz \
  "https://files.pythonhosted.org/packages/source/a/ai-trackdown-pytools/ai-trackdown-pytools-0.9.0.tar.gz"

# Calculate SHA256
sha256sum ai-trackdown-pytools-0.9.0.tar.gz
# or on macOS:
shasum -a 256 ai-trackdown-pytools-0.9.0.tar.gz
```

Update the `sha256` field in the formula with the actual checksum.

### 4. Add Formula to Tap

```bash
# Clone your tap repository
git clone https://github.com/ai-trackdown/homebrew-tap.git
cd homebrew-tap

# Create Formula directory
mkdir -p Formula

# Copy the formula file
cp /path/to/ai-trackdown-pytools.rb Formula/

# Commit and push
git add Formula/ai-trackdown-pytools.rb
git commit -m "Add ai-trackdown-pytools formula v0.9.0"
git push origin main
```

### 5. Test the Tap

```bash
# Add the tap locally
brew tap ai-trackdown/tap

# Install from tap
brew install ai-trackdown-pytools

# Test installation
aitrackdown --version
atd --help
```

## Manual Formula Installation

If you don't want to set up a tap, you can install directly from the formula file:

```bash
# Install directly from local formula
brew install --build-from-source ./ai-trackdown-pytools.rb

# Or from a URL
brew install https://raw.githubusercontent.com/ai-trackdown/homebrew-tap/main/Formula/ai-trackdown-pytools.rb
```

## Updating the Formula

When releasing a new version:

1. **Update Version**: Change the version number in the `url` field
2. **Update SHA256**: Calculate new checksum for the updated package
3. **Test Formula**: Validate the formula works with the new version
4. **Commit Changes**: Push updated formula to tap repository

```bash
# Example for version 1.0.0
# In the formula file, update:
url "https://files.pythonhosted.org/packages/source/a/ai-trackdown-pytools/ai-trackdown-pytools-1.0.0.tar.gz"
sha256 "NEW_SHA256_CHECKSUM"
```

## Formula Validation

### Local Testing

```bash
# Audit the formula
brew audit --strict ai-trackdown-pytools.rb

# Test installation
brew install --build-from-source ai-trackdown-pytools.rb

# Test the installed package
brew test ai-trackdown-pytools
```

### Automated Testing

The formula includes comprehensive tests that verify:

- **Version Check**: `aitrackdown --version` and `atd --version`
- **Help Output**: `aitrackdown --help`
- **Basic Functionality**: Project initialization and configuration creation
- **File Creation**: Validates that required files are created during init

## Dependencies

The formula handles these Python dependencies automatically:

### Core Dependencies
- **click** >= 8.0.0 - CLI framework
- **pydantic** >= 2.0.0 - Data validation
- **pyyaml** >= 6.0 - YAML parsing
- **gitpython** >= 3.1.30 - Git integration
- **rich** >= 13.0.0 - Rich terminal output
- **typer** >= 0.9.0 - Modern CLI framework
- **jinja2** >= 3.1.0 - Template engine
- **jsonschema** >= 4.17.0 - JSON schema validation
- **toml** >= 0.10.2 - TOML parsing
- **pathspec** >= 0.11.0 - Path specification utilities

### Dependency Chain
The formula also includes all transitive dependencies to ensure complete isolation.

## Platform Support

The formula supports:

- **macOS**: All supported Homebrew versions
- **Linux**: Homebrew on Linux (Linuxbrew)
- **Python**: Requires Python 3.11 (managed by Homebrew)

## Troubleshooting

### Common Issues

1. **Missing Python**: Ensure `python@3.11` is available
   ```bash
   brew install python@3.11
   ```

2. **Build Failures**: Check that Xcode Command Line Tools are installed
   ```bash
   xcode-select --install
   ```

3. **Permission Issues**: Ensure Homebrew has proper permissions
   ```bash
   sudo chown -R $(whoami) $(brew --prefix)/*
   ```

### Formula Development

For formula development and testing:

```bash
# Install in development mode
brew install --HEAD --build-from-source ai-trackdown-pytools.rb

# Debug installation
brew install --verbose --debug ai-trackdown-pytools.rb

# Clean up for testing
brew uninstall ai-trackdown-pytools
brew cleanup
```

## Contributing to the Formula

1. **Fork the Tap Repository**: Create your own fork of the homebrew-tap repo
2. **Create Feature Branch**: Work on formula improvements in a feature branch
3. **Test Thoroughly**: Ensure all tests pass and the formula works correctly
4. **Submit Pull Request**: Submit your changes for review

## Resources

- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Python Formula Guidelines](https://docs.brew.sh/Python-for-Formula-Authors)
- [Homebrew Tap Documentation](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)
- [AI Trackdown PyTools Repository](https://github.com/ai-trackdown/ai-trackdown-pytools)

## License

This formula is distributed under the MIT License, consistent with the AI Trackdown PyTools project.