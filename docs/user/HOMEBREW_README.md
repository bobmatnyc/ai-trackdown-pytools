# Homebrew Formula Package for AI Trackdown PyTools

This directory contains the complete Homebrew formula and documentation for AI Trackdown PyTools, a Python CLI tool for AI project tracking and task management.

## 📋 Contents

### Formula Files
- `ai-trackdown-pytools.rb` - Complete Homebrew formula with all dependencies
- `scripts/calculate_sha256.py` - Script to calculate SHA256 for package releases
- `scripts/validate_homebrew_formula.py` - Formula validation tool

### Documentation
- `HOMEBREW_FORMULA.md` - Comprehensive formula setup and tap creation guide
- `HOMEBREW_INSTALL.md` - User installation guide
- `HOMEBREW_README.md` - This overview document

## 🚀 Quick Setup for Homebrew Tap

### 1. Calculate Package SHA256

```bash
# Calculate SHA256 for the current version
python3 scripts/calculate_sha256.py
```

### 2. Update Formula

Replace `PLACEHOLDER_SHA256` in `ai-trackdown-pytools.rb` with the calculated hash.

### 3. Validate Formula

```bash
# Validate the formula structure
python3 scripts/validate_homebrew_formula.py ai-trackdown-pytools.rb
```

### 4. Create Homebrew Tap Repository

```bash
# Create repository: https://github.com/ai-trackdown/homebrew-tap
# Structure:
# homebrew-tap/
# ├── Formula/
# │   └── ai-trackdown-pytools.rb
# ├── README.md
# └── LICENSE
```

### 5. Test Installation

```bash
# Add tap and install
brew tap ai-trackdown/tap
brew install ai-trackdown-pytools

# Test commands
aitrackdown --version
atd --help
```

## 📦 Package Features

The Homebrew package provides:

### CLI Commands
- `aitrackdown` - Main CLI interface
- `atd` - Short alias
- `aitrackdown-init` - Direct init access
- `aitrackdown-status` - Direct status access  
- `aitrackdown-create` - Direct create access
- `aitrackdown-template` - Direct template access

### Dependencies Managed
- Python 3.11+ (via Homebrew)
- Complete virtualenv with all Python dependencies
- Shell completions for Zsh and Fish

### Testing Coverage
- Version checks for all commands
- Help output validation
- Basic functionality testing (project init)
- File creation verification

## 🛠️ Development Workflow

### For New Releases

1. **Update Version**: Update version in `pyproject.toml`
2. **Build Package**: Build and publish to PyPI
3. **Calculate SHA256**: Run `python3 scripts/calculate_sha256.py`
4. **Update Formula**: Replace SHA256 and version in formula
5. **Validate**: Run `python3 scripts/validate_homebrew_formula.py`
6. **Test**: Install and test locally
7. **Push to Tap**: Update the homebrew-tap repository

### For Formula Development

```bash
# Test local formula
brew install --build-from-source ./ai-trackdown-pytools.rb

# Debug installation
brew install --verbose --debug ./ai-trackdown-pytools.rb

# Audit formula
brew audit --strict ./ai-trackdown-pytools.rb

# Test installed package
brew test ai-trackdown-pytools
```

## 📚 Documentation Structure

1. **HOMEBREW_INSTALL.md** - End-user installation guide
   - Quick installation steps
   - Troubleshooting common issues
   - Comparison with PyPI installation

2. **HOMEBREW_FORMULA.md** - Technical implementation guide
   - Complete tap setup instructions
   - Formula validation and testing
   - Dependency management details

3. **This README** - Development overview
   - Workflow for maintainers
   - File organization
   - Quick reference commands

## 🔧 Tools and Scripts

### calculate_sha256.py
- Downloads package from PyPI
- Calculates SHA256 hash for formula
- Automatically cleans up downloaded files
- Outputs formatted hash for copy-paste

### validate_homebrew_formula.py
- Validates Ruby syntax and structure
- Checks required Homebrew formula fields
- Validates URL patterns and dependencies
- Ensures proper test block implementation
- Reports errors and warnings with line numbers

## ✅ Quality Checks

The formula passes all validation checks:

- ✅ Correct class name and inheritance
- ✅ All required fields present (desc, homepage, url, license)
- ✅ Proper Python dependency declaration
- ✅ Complete resource list for all dependencies
- ✅ Virtualenv installation method
- ✅ Shell completion generation
- ✅ Comprehensive test suite
- ✅ Balanced Ruby syntax (class/def/do/end blocks)

## 🌟 Ready for Production

This Homebrew formula is production-ready and includes:

- **Complete dependency management** with pinned versions
- **Robust testing** covering basic functionality  
- **Shell integration** with auto-completions
- **Multiple CLI entry points** for user convenience
- **Professional documentation** for users and maintainers

To publish, simply:
1. Update the SHA256 placeholder
2. Create the homebrew-tap repository
3. Copy the formula to `Formula/ai-trackdown-pytools.rb`
4. Test and announce to users

The formula follows all Homebrew best practices and conventions for Python packages.