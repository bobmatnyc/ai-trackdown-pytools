# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.2] - 2025-07-25

### Changed
- Updated default directory from "tasks" to "tickets" to align with ai-trackdown schema v4.5.1
- Fixed TaskManager to properly use configured directory without appending subdirectories

### Fixed  
- Issue detection now works correctly when tickets are organized in subdirectories (epics/, issues/, tasks/)
- Configuration handling now properly respects the tasks.directory setting

## [1.3.1] - 2025-07-25

### Fixed
- Removed unused import of non-existent id_generator module

## [1.3.0] - 2025-07-25

### Added
- Comprehensive enum system for type safety:
  - `TicketType` enum for ticket types (epic, issue, task, pr, comment)
  - `TicketPrefix` enum for ticket prefixes (EP, ISS, TSK, PR, CMT)
  - `TicketSubdir` enum for ticket subdirectories
  - `TicketStatus` enum for all possible ticket statuses
  - `TicketPriority` enum for priority levels (low, medium, high, critical)
- New `core/constants.py` module centralizing all magic strings
- Mapping dictionaries for enum conversions
- Default values for status, priority, and ticket type
- Priority ordering for consistent sorting

### Changed
- Default parent directory changed from "tasks/" to "tickets/" for new projects
- All hardcoded strings replaced with proper enums throughout codebase
- Improved type safety and IDE support with autocomplete
- Better validation against allowed enum values
- All directory references now configuration-driven

### Fixed
- Import issues with TaskError exception
- Nested directory structure problems
- Test compatibility with new enum system
- Exception module organization

### Technical Details
- Created centralized exceptions module at `core/exceptions.py`
- Updated key modules to use enums: task.py, create.py, status.py, portfolio.py
- Maintained backward compatibility for existing projects
- Configuration preserved for existing installations

## [1.2.0] - 2025-07-24

### Added
- Unified ticket management commands (`show`, `close`, `transition`, `archive`, `delete`) with automatic ticket type inference
- Epic-Issue-Task relationship management commands:
  - `aitrackdown epic link-issue` - Link issues to epics
  - `aitrackdown issue link-task` - Link tasks to issues
  - `aitrackdown issue unlink-task` - Unlink tasks from issues
- Config reload functionality with cache management:
  - `reload()` - Reload configuration from disk
  - `clear_cache()` - Clear configuration cache
  - `is_stale()` - Check if configuration needs reloading
- Archive functionality for all ticket types with `tasks/*/archive/` directories
- New utility module `tickets.py` for unified ticket operations
- Enhanced create command with:
  - `--issue` flag to link task to an issue during creation
  - Automatic parent/child relationship handling
  - Better field validation and error messages

### Fixed
- Tasks directory configuration now properly respects `config.yaml` settings
- Fixed ticket type inference to handle archived tickets correctly
- Improved error handling for missing or invalid ticket IDs
- Fixed validation issues with epic and issue linking
- Corrected file path resolution for comments and other operations
- Enhanced error messages for better user experience

### Changed
- Reorganized CLI commands for better usability and consistency
- Improved ticket search to include archive directories
- Enhanced status display to show epic/issue/task relationships
- Unified ticket operations to reduce code duplication
- Better handling of ticket state transitions

### Technical Details
- Added comprehensive test coverage for new unified commands
- Implemented ticket type inference logic for seamless operations
- Created centralized ticket utility functions for consistency
- Enhanced configuration reload mechanism for dynamic updates
- Improved file path handling across all operations

## [1.1.2] - 2025-07-23

### Fixed
- Critical bug in PR and Epic update functionality that prevented closing/updating these items
- Task update functionality was broken due to missing `save_task` method in TaskManager class
- Improved error handling and display in task update operations

### Technical Details
- Added missing `save_task` method to TaskManager class (ISS-0012)
- Fixed task relationship updates for epic and parent task management
- Enhanced error messaging for better user experience during task operations

## [1.1.1] - 2025-07-23

### Added
- GitHub sync functionality for bidirectional synchronization with GitHub issues and PRs
- GitHub CLI (gh) integration for issue and PR management
- Sync commands: `aitrackdown sync github pull/push/status`
- Sync configuration management in `.aitrackdown/sync.json`
- Support for syncing issue labels, assignees, and milestones
- Documentation reorganization with clear user/development separation
- Index files for documentation sections to improve navigation

### Fixed
- Task update slice indices error - added missing `save_task` method in TaskManager
- Comment functionality lookup issues - improved file path finding patterns
- Status project NoneType error - added validation for empty project.yaml files
- Proper error handling for task updates with epic/parent relationships
- YAML parsing and double-escaping issues in various commands

### Changed
- Documentation structure moved to organized subdirectories (user/, development/, design/, misc/)
- Removed redundant documentation files from root directory
- Consolidated PyPI publishing guides into development documentation
- Improved error messages and user feedback throughout CLI

### Development
- Enhanced test coverage for new sync functionality
- Added GitHub API mocking for offline testing
- Improved CI/CD pipeline with security checks
- Updated dependencies for GitHub integration

## [1.1.0] - 2025-07-21

### Added
- The `aitrackdown` CLI command is the primary command for this project
- Standardized command naming for better user experience
- Full schema compliance with proper ID prefixes (EP-, ISS-, TSK-, PR-)
- Correct directory structure (tasks/epics/, tasks/issues/, tasks/tasks/, tasks/prs/)
- Epic/issue linking commands with `--epic` option for updates
- Plain output mode (`--plain`) for AI-friendly command output
- Environment variable support (AITRACKDOWN_PLAIN, NO_COLOR, CI)
- Auto-detection of piped output for simplified formatting
- Bidirectional relationship management for epic/issue/task linking
- Comment system for issues (with future support for epics/tasks)
- Index management system for efficient searching
- Field validation for required schema fields

### Fixed
- Cross-project file creation issue - proper project isolation
- Task update display warning about "limit must be an integer"
- YAML parsing warnings and double-escaping issues
- File naming consistency (no more double dashes)
- Missing required fields in legacy file formats

### Changed
- Migrated from single TSK- prefix to proper schema prefixes
- Reorganized file structure to match ai-trackdown schema
- Improved help command descriptions for better AI usability
- Enhanced error messages and user feedback

## [1.0.0] - 2025-07-21

### Added
- Enhanced unit test coverage for all core functions
- Comprehensive test suite with 90%+ coverage targets
- Extended validation testing with edge cases
- PyPI-optimized documentation with badges and examples
- setup.py for compatibility with older pip versions
- py.typed marker for PEP 561 compliance
- Comprehensive project metadata and classifiers
- Extended keywords for better PyPI discoverability
- Production-ready stability and performance
- Security validation with multiple scanning tools
- Full CI/CD automation with GitHub Actions
- Comprehensive error handling and recovery
- Performance benchmarks and stress testing
- PyPI publication readiness with all requirements

### Changed
- Improved test fixtures and parametrized testing
- Enhanced error handling test scenarios
- Updated README with professional PyPI presentation
- Expanded project metadata in pyproject.toml
- Enhanced MANIFEST.in for complete package distribution
- Upgraded from Beta to Production/Stable status
- Version bumped from 0.9.0 to 1.0.0

### Documentation
- Added real-world usage examples in README
- Created comprehensive command reference table
- Added plugin system preview documentation
- Enhanced installation instructions with multiple methods
- Added community and support information
- Created PyPI upload and distribution guides
- Added Homebrew formula for macOS installation

### Security
- Passed Bandit security scanning
- Passed Safety vulnerability scanning
- Passed pip-audit dependency checks
- Implemented secure configuration handling
- Added input validation across all commands

### Testing
- Achieved comprehensive test coverage
- Added stress testing for large datasets
- Implemented performance benchmarking
- Created end-to-end test scenarios
- Added cross-platform compatibility tests

### Distribution
- Prepared for PyPI publication
- Created source and wheel distributions
- Validated package metadata and classifiers
- Tested installation on multiple platforms
- Added Homebrew formula for easy macOS installation

## [0.9.0] - 2025-07-11

### Added
- Semantic versioning implementation starting at 0.9.0
- Comprehensive CHANGELOG backfilled with current features
- Initial project structure and packaging
- CLI framework with Typer and Rich for enhanced user experience
- Core modules for configuration, projects, and task management
- Template system with YAML-based templates for standardized workflows
- JSON schema validation for all ticket types (tasks, epics, issues, PRs)
- Git integration utilities for version control workflows
- Project initialization and configuration management
- Task creation, management, and tracking capabilities
- Rich terminal output with colors and formatting
- Frontmatter parsing for YAML metadata in markdown files
- Health check system for project validation
- Editor integration for external editing capabilities
- Comprehensive testing infrastructure with pytest
- Test fixtures for all major components
- Unit, integration, and end-to-end test suites
- Performance testing framework
- Modern Python packaging with pyproject.toml
- Development tooling integration (black, ruff, mypy)
- Pre-commit hooks for code quality enforcement
- Coverage reporting with HTML and XML output
- Tox integration for multi-environment testing
- GitHub Actions CI/CD pipeline
- Comprehensive documentation and examples

### Technical Implementation
- Pydantic models for data validation and serialization
- Singleton pattern for configuration management
- Template rendering with Jinja2
- Path-based project discovery and management
- YAML configuration with dot notation access
- Git repository integration with GitPython
- CLI command structure with proper error handling
- Modular architecture with clear separation of concerns

### Development Infrastructure
- pytest configuration with markers and fixtures
- Coverage configuration with exclusions
- Black code formatting with 88-character line length
- Ruff linting with comprehensive rule set
- MyPy type checking with strict settings
- Pre-commit hooks for automated quality checks
- GitHub Actions workflows for CI/CD
- Multi-Python version support (3.8-3.12)

### Quality Assurance
- Comprehensive test fixtures for all scenarios
- Mock integration for external dependencies
- Parametrized testing for multiple input scenarios
- Performance testing for large datasets
- Error simulation and edge case testing
- Integration testing for complete workflows
- End-to-end testing for user scenarios
- CLI testing with Typer test runner

### Note
This version represents the initial beta release of AI Trackdown PyTools. The project
follows semantic versioning principles and is approaching feature completeness for v1.0.0.