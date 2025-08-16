# AI Trackdown Python Tools - Development Documentation

This section contains technical documentation for developers working on the AI Trackdown Python Tools project.

## Quick Links

- [Contributing Guide](./CONTRIBUTING.md) - How to contribute to the project
- [Testing Guide](./CLI_TESTING_GUIDE.md) - Running and writing tests
- [PyPI Publishing](./PYPI_MANUAL_PUBLISHING_GUIDE.md) - Release procedures
- [Sync Adapter Developer Guide](./sync-adapter-developer-guide.md) - Creating new sync adapters

## Documentation Sections

### Development Setup
- [Contributing](./CONTRIBUTING.md) - Development environment setup and guidelines
- [CI/CD Automation](./CI_CD_AUTOMATION.md) - Continuous integration setup
- [GitHub Actions Setup](./GITHUB_ACTIONS_SETUP.md) - Workflow configuration

### Sync Adapter Development
- [Sync Adapter Developer Guide](./sync-adapter-developer-guide.md) - Complete guide for creating new adapters

### Testing
- [CLI Testing Guide](./CLI_TESTING_GUIDE.md) - Comprehensive testing procedures
- [Test Coverage](./COVERAGE.md) - Coverage requirements and reports
- [Coverage System Implementation](./COVERAGE_SYSTEM_IMPLEMENTATION.md) - Coverage tooling details

### Release Management
- [PyPI Manual Publishing Guide](./PYPI_MANUAL_PUBLISHING_GUIDE.md) - Step-by-step publishing
- [Semantic Versioning](./SEMANTIC_VERSIONING_IMPLEMENTATION.md) - Version management

### Quality Assurance
- [Validation](./VALIDATION.md) - Code validation procedures

### Security
- [Secure Token Usage Guide](./SECURE_TOKEN_USAGE_GUIDE.md) - API key management

### Architecture
- Project architecture is documented in the main README.md and inline code documentation

## Development Tools

Key scripts in `scripts/` directory:
- `test_runner.py` - Main test execution
- `coverage_analysis.py` - Coverage reporting
- `security_check.py` - Security scanning
- `validate_pypi_readiness.py` - Pre-release validation

## Standards

- Python 3.8+ compatibility required
- Minimum 80% test coverage
- Black formatting enforced
- Type hints required for all public functions

## Current Version

The project is currently at version 1.5.2 with comprehensive CLI functionality and sync adapters for GitHub, ClickUp, and Linear platforms.