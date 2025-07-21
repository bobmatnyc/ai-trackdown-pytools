# Contributing to AI Trackdown PyTools

Thank you for your interest in contributing to AI Trackdown PyTools! This document provides guidelines and information for contributors.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Basic understanding of CLI tools and Python packaging

### Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ai-trackdown/ai-trackdown-pytools.git
   cd ai-trackdown-pytools
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e .[dev]
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

5. **Verify installation**:
   ```bash
   aitrackdown --help
   pytest
   ```

## Code Style

We use several tools to maintain code quality:

### Formatting
- **Black**: Code formatting
- **isort**: Import sorting

### Linting
- **Ruff**: Fast Python linter
- **MyPy**: Type checking

### Running Code Quality Tools

```bash
# Format code
black src tests
isort src tests

# Lint code
ruff check src tests

# Type checking
mypy src

# Run all checks
pre-commit run --all-files
```

### Style Guidelines

1. **Follow PEP 8** with Black's formatting
2. **Use type hints** for all public functions
3. **Write docstrings** for all public modules, classes, and functions
4. **Keep functions small** and focused
5. **Use descriptive variable names**

## Testing

We use pytest for testing with comprehensive coverage:

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ai_trackdown_pytools

# Run specific test file
pytest tests/unit/test_config.py

# Run tests with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

### Test Structure

```
tests/
├── unit/           # Unit tests for individual modules
├── integration/    # Integration tests for component interaction
├── e2e/           # End-to-end CLI tests
├── fixtures/      # Test data and fixtures
└── conftest.py    # Pytest configuration and fixtures
```

### Writing Tests

1. **Use descriptive test names** that explain what is being tested
2. **Follow the AAA pattern**: Arrange, Act, Assert
3. **Use fixtures** for common test data
4. **Mock external dependencies** in unit tests
5. **Test error conditions** as well as success cases

Example test:
```python
def test_create_task_with_valid_data(temp_project, sample_task_data):
    """Test creating a task with valid data."""
    # Arrange
    task_manager = TaskManager(temp_project)
    
    # Act
    task = task_manager.create_task(**sample_task_data)
    
    # Assert
    assert task.title == sample_task_data["title"]
    assert task.status == "open"
    assert task.file_path.exists()
```

## Pull Request Process

### Before Submitting

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines

3. **Add tests** for new functionality

4. **Update documentation** if needed

5. **Run the test suite**:
   ```bash
   pytest
   pre-commit run --all-files
   ```

6. **Update CHANGELOG.md** with your changes

### Submitting a Pull Request

1. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create a pull request** on GitHub with:
   - Clear title and description
   - Reference to any related issues
   - Screenshots if applicable
   - Test results

3. **Respond to feedback** and make necessary changes

### Pull Request Guidelines

- **Keep PRs focused** - one feature or fix per PR
- **Write clear commit messages**
- **Include tests** for new functionality
- **Update documentation** for user-facing changes
- **Ensure CI passes** before requesting review

## Release Process

Releases are managed by maintainers following semantic versioning:

### Version Numbering

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Steps

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v1.0.0`
4. Push tag: `git push origin v1.0.0`
5. GitHub Actions will automatically build and publish to PyPI

## Development Guidelines

### Project Structure

```
src/ai_trackdown_pytools/
├── __init__.py          # Package initialization
├── cli.py              # Main CLI entry point
├── commands/           # CLI command modules
│   ├── init.py        # Project initialization
│   ├── status.py      # Status commands
│   ├── create.py      # Creation commands
│   └── template.py    # Template management
├── core/              # Core functionality
│   ├── config.py      # Configuration management
│   ├── project.py     # Project management
│   └── task.py        # Task management
├── utils/             # Utility modules
│   ├── git.py         # Git integration
│   ├── health.py      # Health checks
│   ├── editor.py      # Editor integration
│   └── templates.py   # Template system
├── templates/         # Default templates
└── schemas/           # JSON schemas
```

### Adding New Commands

1. Create new module in `commands/`
2. Use Typer for CLI structure
3. Add command to main CLI in `cli.py`
4. Write comprehensive tests
5. Update documentation

### Adding New Features

1. **Design first** - consider the user experience
2. **Start with tests** - write failing tests first
3. **Implement incrementally** - small, focused commits
4. **Document thoroughly** - update README and docstrings
5. **Consider backward compatibility**

## Getting Help

- **Create an issue** for bugs or feature requests
- **Start a discussion** for design questions
- **Join our community** for general questions

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## License

By contributing to AI Trackdown PyTools, you agree that your contributions will be licensed under the MIT License.