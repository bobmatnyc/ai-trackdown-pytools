# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.11] - 2025-08-24

### Fixed
- Added "done" as a valid workflow state for ticket transitions
- Added "--priority" as an alias for "--severity" in issue and bug create commands for compatibility

## [1.5.8] - 2025-08-20

### Fixed
- Fixed GitHub CLI --json flag error in create commands (properly applied)
- Resolved GitHub CLI compatibility issues with create operations
- Fixed run_in_executor() keyword argument error in sync adapters using functools.partial

## [1.5.7] - 2025-08-20

### Fixed
- Fixed GitHub CLI --json flag error in create commands
- Resolved GitHub CLI compatibility issues with create operations


## [1.5.6] - 2025-08-20

### Fixed
- Fixed run_in_executor() keyword argument error in GitHub sync adapter
- Fixed run_in_executor() keyword argument error in Jira sync adapter
- Resolved executor argument compatibility issues in sync adapters

## [1.5.5] - 2025-08-20

### Fixed
- Fixed GitHub sync for TaskModel and EpicModel items
- Improved TaskModel and EpicModel synchronization with GitHub issues
- Enhanced status mapping for unified ticket types in GitHub adapter

## [Unreleased]
