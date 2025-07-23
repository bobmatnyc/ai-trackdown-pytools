# Claude PM Framework Configuration - AI Trackdown Python Tools

<!-- 
CLAUDE_MD_VERSION: 001-001
PROJECT: ai-trackdown-pytools
DEPLOYMENT_DATE: 2025-07-21
LAST_UPDATED: 2025-07-21
-->

## 🤖 AI ASSISTANT ROLE DESIGNATION

**You are operating within the AI Trackdown Python Tools project**

Your primary role is developing and maintaining the Python implementation of AI-powered project tracking tools. This project provides a Python-based CLI tool for AI-enhanced project management and issue tracking.

### Project Context
- **Project Name**: ai-trackdown-pytools
- **Primary Language**: Python
- **Package Name**: ai-trackdown-pytools
- **CLI Command**: aitrackdown
- **Purpose**: Python implementation of AI-powered project tracking and issue management
- **Distribution**: PyPI (Python Package Index)

---

## A) PROJECT STRUCTURE AND ORGANIZATION

### 🚨 MANDATORY: Directory Structure

**Root Directory Files (KEEP MINIMAL):**
- `CLAUDE.md` - This file, AI assistant instructions
- `README.md` - Project overview and user documentation
- `CHANGELOG.md` - Version history and changes
- `RELEASE_NOTES.md` - Current release information
- `VERSION` - Single source of truth for version number
- `pyproject.toml` - Python project configuration
- `setup.py` - Python package setup (if needed)
- `requirements.txt` - Direct dependencies only
- `LICENSE` - MIT License
- `.gitignore` - Git ignore rules
- `.github/` - GitHub workflows and configurations

**Documentation Organization:**
```
docs/
├── user/                   # User documentation
│   ├── index.md           # User docs index with links
│   ├── installation/      # Installation guides
│   ├── usage/             # Usage guides and tutorials
│   └── cli/               # CLI command reference
├── development/            # Development documentation
│   ├── index.md           # Dev docs index with links
│   ├── contributing/      # Contributing guidelines
│   ├── testing/           # Testing procedures
│   ├── release/           # Release procedures
│   └── api/               # API documentation
├── design/                 # Design documentation
│   ├── architecture/      # Technical architecture
│   ├── schemas/           # Schema definitions
│   └── decisions/         # Design decisions
└── misc/                   # Miscellaneous docs
    ├── archive/           # Archived documentation
    └── legacy/            # Legacy documentation
```

**Documentation Rules:**
1. User and development docs MUST have `index.md` files
2. Each `index.md` must provide comprehensive section navigation
3. Documentation should be concise but comprehensive
4. README.md must link to both user and development documentation sections

**Source Code Organization:**
```
aitrackdown/
├── __init__.py            # Package initialization
├── __version__.py         # Version information
├── cli.py                 # CLI entry point
├── core/                  # Core functionality
│   ├── __init__.py
│   ├── tracker.py         # Main tracking logic
│   ├── ai_integration.py  # AI provider integrations
│   └── models.py          # Data models
├── utils/                 # Utility functions
├── config/                # Configuration management
└── templates/             # Issue and project templates
```

**Testing Structure:**
```
tests/
├── __init__.py
├── unit/                  # Unit tests
├── integration/           # Integration tests
├── fixtures/              # Test fixtures
└── coverage/              # Coverage reports
```

### 🚨 CRITICAL: File Location Rules

1. **NO documentation in root** except CLAUDE.md, README.md, CHANGELOG.md, RELEASE_NOTES.md
2. **ALL other docs** must go in `docs/` directory
3. **ALL tests** must go in `tests/` directory
4. **NO temporary files** in version control
5. **NO IDE-specific files** (.vscode, .idea) in version control

---

## B) VERSION MANAGEMENT

### 🚨 MANDATORY: Version Control

**Single Source of Truth: VERSION file**
```bash
# VERSION file contains ONLY the version number
1.0.0
```

**Version Synchronization:**
1. `VERSION` file - Manual update
2. `aitrackdown/__version__.py` - Generated from VERSION
3. `pyproject.toml` - Updated during release
4. Git tags - Created during release

**Version Update Procedure:**
```bash
# 1. Update VERSION file
echo "1.0.1" > VERSION

# 2. Update Python version file
echo "__version__ = '$(cat VERSION)'" > aitrackdown/__version__.py

# 3. Update pyproject.toml
# Update version = "X.X.X" in pyproject.toml

# 4. Commit changes
git add VERSION aitrackdown/__version__.py pyproject.toml
git commit -m "chore: bump version to $(cat VERSION)"

# 5. Create tag
git tag -a "v$(cat VERSION)" -m "Release v$(cat VERSION)"
```

---

## C) TESTING AND QUALITY ASSURANCE

### 🚨 MANDATORY: Testing Requirements

**Minimum Coverage: 80%**

**Test Execution:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=aitrackdown --cov-report=html --cov-report=term

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run with verbose output
pytest -v

# Run with parallel execution
pytest -n auto
```

**Pre-Release Testing Checklist:**
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Coverage meets 80% minimum
- [ ] No linting errors (flake8, black, mypy)
- [ ] Documentation builds successfully
- [ ] CLI commands work as expected
- [ ] Package installs correctly in clean environment

---

## D) DEPLOYMENT PROCEDURES

### 🚨 MANDATORY: PyPI Publishing

**Pre-Publishing Requirements:**
1. Version updated in VERSION file
2. CHANGELOG.md updated with new version
3. RELEASE_NOTES.md updated for current release
4. All tests passing with 80%+ coverage
5. Documentation updated
6. Git tag created

**Build Process:**
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distribution packages
python -m build

# Verify build contents
ls -la dist/
tar -tzf dist/ai-trackdown-pytools-*.tar.gz | head -20
```

**Publishing to PyPI:**
```bash
# Test on TestPyPI first
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ ai-trackdown-pytools

# Publish to PyPI
python -m twine upload dist/*
```

**Post-Publishing Verification:**
```bash
# Wait 2-3 minutes for PyPI to update
sleep 180

# Verify installation
pip install ai-trackdown-pytools
aitrackdown --version
```

---

## E) CLI USAGE AND TICKETING

### 🚨 MANDATORY: Use aitrackdown for This Project

**All ticket operations for this project use aitrackdown:**
```bash
# Initialize tracking
aitrackdown init

# Create new ticket
aitrackdown create "Add feature X"

# List tickets
aitrackdown list

# Update ticket
aitrackdown update TICKET-001 --status in-progress

# Close ticket
aitrackdown close TICKET-001
```

**DO NOT use other ticketing tools for this project**

---

## F) DEVELOPMENT WORKFLOW

### 🚨 MANDATORY: Development Environment Setup

**Initial Setup and After Code Changes:**
```bash
# Option 1: Activate virtual environment for the session (RECOMMENDED)
source venv/bin/activate
pip install -e .
# Now aitrackdown is available without prefixing for entire session

# Option 2: Install with pipx for global access (for CLI tools)
pipx install -e .
# Now aitrackdown is available system-wide

# Option 3: Use the venv Python directly (without activation)
./venv/bin/pip install -e .
# Then use: ./venv/bin/aitrackdown
```

**Development Environment Optimization:**
1. **Best Practice**: Activate venv once at session start
   ```bash
   source venv/bin/activate  # Run once per terminal session
   aitrackdown --version  # Works directly
   ```

2. **Alternative for System-Wide Access**: Use pipx
   ```bash
   brew install pipx  # or: python3 -m pip install --user pipx
   pipx install -e .
   ```

3. **Shell Alias** (add to ~/.bashrc or ~/.zshrc):
   ```bash
   alias atd-dev='source /path/to/project/venv/bin/activate'
   ```

**Why Development Mode:**
- Enables `aitrackdown` CLI commands immediately
- Reflects code changes without reinstalling
- Required for ticket creation and management
- Essential for testing CLI functionality

**Note on Wheels:**
- This project uses setuptools with pyproject.toml (PEP 517)
- Wheels are automatically built during `pip install`
- For distribution, use `python -m build` to create wheels

### 🚨 MANDATORY: Development Procedures

**Feature Development:**
1. Ensure development environment: `pip install -e .`
2. Create ticket using `aitrackdown create`
3. Create feature branch: `git checkout -b feature/TICKET-XXX-description`
4. Implement feature with tests
5. Ensure 80%+ test coverage
6. Update documentation
7. Reinstall if CLI changes made: `pip install -e .`
8. Create pull request

**Bug Fixes:**
1. Ensure development environment: `pip install -e .`
2. Create bug ticket using `aitrackdown create --type bug`
3. Create bugfix branch: `git checkout -b bugfix/TICKET-XXX-description`
4. Fix bug with regression test
5. Verify all tests pass
6. Reinstall if CLI changes made: `pip install -e .`
7. Create pull request

**Documentation Updates:**
1. Documentation goes in `docs/` directory
2. Use Markdown format
3. Include code examples
4. Update table of contents

---

## G) CODE QUALITY STANDARDS

### 🚨 MANDATORY: Quality Requirements

**Python Standards:**
- Python 3.8+ compatibility
- Type hints for all functions
- Docstrings for all public functions
- Black formatting
- Flake8 compliance
- MyPy type checking

**Code Formatting:**
```bash
# Format with black
black aitrackdown tests

# Check with flake8
flake8 aitrackdown tests

# Type check with mypy
mypy aitrackdown
```

**Import Organization:**
1. Standard library imports
2. Third-party imports
3. Local imports
4. One blank line between groups

---

## H) DOCUMENTATION STANDARDS

### 🚨 MANDATORY: Documentation Requirements

**API Documentation:**
- All public functions must have docstrings
- Include parameter types and descriptions
- Include return type and description
- Include usage examples
- Document exceptions raised

**User Documentation:**
- Clear installation instructions
- Getting started guide
- Command reference
- Configuration options
- Troubleshooting section

**Developer Documentation:**
- Architecture overview
- Contributing guidelines
- Development setup
- Testing procedures
- Release process

---

## I) RELEASE PROCEDURES

### 🚨 MANDATORY: Release Checklist

**Pre-Release:**
- [ ] All tickets for release milestone completed
- [ ] Version bumped in VERSION file
- [ ] CHANGELOG.md updated
- [ ] RELEASE_NOTES.md created/updated
- [ ] All tests passing
- [ ] Coverage >= 80%
- [ ] Documentation updated
- [ ] Package builds successfully

**Release:**
- [ ] Create git tag
- [ ] Push tag to GitHub
- [ ] Build distribution packages
- [ ] Upload to PyPI
- [ ] Create GitHub release
- [ ] Announce release

**Post-Release:**
- [ ] Verify PyPI installation works
- [ ] Update project boards
- [ ] Plan next release
- [ ] Archive RELEASE_NOTES.md to docs/releases/

---

## J) TROUBLESHOOTING

### Common Issues

**Installation Problems:**
```bash
# Clear pip cache
pip cache purge

# Install with verbose output
pip install -v ai-trackdown-pytools

# Install from source
git clone https://github.com/yourusername/ai-trackdown-pytools.git
cd ai-trackdown-pytools
pip install -e .
```

**Import Errors:**
```python
# Verify installation
python -c "import aitrackdown; print(aitrackdown.__version__)"

# Check Python path
python -c "import sys; print(sys.path)"
```

**CLI Not Found:**
```bash
# Check if script is in PATH
which aitrackdown

# Find installed location
pip show -f ai-trackdown-pytools | grep bin/

# Add to PATH if needed
export PATH="$PATH:$(python -m site --user-base)/bin"
```

---

## K) DEPENDENCIES AND REQUIREMENTS

### 🚨 MANDATORY: Dependency Management

**Direct Dependencies Only in requirements.txt:**
- List only direct dependencies
- Pin major versions, not exact versions
- Use >= for minimum versions
- Document why each dependency is needed

**Example requirements.txt:**
```
click>=8.0  # CLI framework
requests>=2.25  # HTTP client for AI APIs
pydantic>=2.0  # Data validation
rich>=10.0  # Terminal formatting
```

**Development Dependencies:**
```
# requirements-dev.txt
pytest>=7.0
pytest-cov>=4.0
black>=22.0
flake8>=5.0
mypy>=1.0
build>=0.10
twine>=4.0
```

---

## L) SECURITY CONSIDERATIONS

### 🚨 MANDATORY: Security Practices

**API Key Management:**
- Never commit API keys
- Use environment variables
- Document required environment variables
- Provide example .env file

**Sensitive Data:**
- No passwords in code
- No tokens in version control
- Sanitize error messages
- Validate all user input

---

## M) PROJECT-SPECIFIC RULES

### 🚨 CRITICAL: AI Trackdown Python Tools Specific

1. **This is the Python implementation** - maintain Python best practices
2. **CLI is primary interface** - ensure excellent CLI UX
3. **AI integration is core** - support multiple AI providers
4. **Cross-platform support** - test on Linux, macOS, Windows
5. **Async where appropriate** - use async for AI API calls
6. **Extensible architecture** - allow custom providers and templates

---

## CRITICAL REMINDERS

- **Version in VERSION file** - always update before release
- **Tests must pass** - no exceptions
- **80% coverage minimum** - maintain quality
- **Use aitrackdown** - for all project tickets
- **Docs in docs/** - keep root clean
- **PyPI publishing** - test on TestPyPI first

**Framework Version**: 001-001
**Project**: ai-trackdown-pytools
**Last Updated**: 2025-07-21