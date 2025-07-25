# Release Notes - v1.3.0

## AI Trackdown PyTools v1.3.0 - Comprehensive Enum System and Improved Type Safety

**Release Date**: 2025-07-25  
**Status**: Production/Stable

We are excited to announce version 1.3.0 of AI Trackdown PyTools! This release introduces a major refactoring to use enums throughout the codebase for better type safety and consistency. The default parent directory for tickets has been changed from "tasks/" to "tickets/" for better clarity.

## 🎉 Highlights

### Major New Features

1. **Comprehensive Enum System**
   - Introduced `TicketType` enum for ticket types (epic, issue, task, pr, comment)
   - Added `TicketPrefix` enum for ticket prefixes (EP, ISS, TSK, PR, CMT)
   - Created `TicketSubdir` enum for ticket subdirectories
   - Implemented `TicketStatus` enum for all possible ticket statuses
   - Added `TicketPriority` enum for priority levels (low, medium, high, critical)

2. **Default Directory Change**
   - Changed default parent directory from "tasks/" to "tickets/"
   - Directory structure is now: `tickets/tasks/`, `tickets/epics/`, `tickets/issues/`, `tickets/prs/`
   - Fully configurable via `tasks.directory` in config.yaml

## 🚀 Improvements

### Code Quality
- Replaced all hardcoded strings with proper enums throughout the codebase
- Improved type safety and IDE support with autocomplete for enums
- Centralized all magic strings in `core/constants.py`
- Better validation against allowed values

### Configuration
- Default configuration now uses "tickets" as the parent directory
- All directory references are now configuration-driven
- Removed hardcoded paths throughout the codebase

## 🐛 Bug Fixes
- Fixed import issues with TaskError exception
- Resolved nested directory structure problems
- Fixed test compatibility with new enum system
- Corrected exception module organization

## ⚠️ Breaking Changes
- New projects will default to "tickets/" directory instead of "tasks/"
- Existing projects are unaffected (configuration is preserved)

## 📝 Migration Notes

For existing projects, no action is required. Your current directory structure will continue to work as configured in your `.ai-trackdown/config.yaml`.

For new projects, the default structure will be:
```
project/
├── tickets/
│   ├── tasks/      # TSK-XXXX files
│   ├── epics/      # EP-XXXX files
│   ├── issues/     # ISS-XXXX files
│   └── prs/        # PR-XXXX files
├── docs/
└── .ai-trackdown/
```

## 🔧 Technical Details

### New Constants Module
The new `core/constants.py` module provides:
- Type-safe enums for all ticket-related strings
- Mapping dictionaries for conversions
- Default values for status, priority, and ticket type
- Priority ordering for sorting

### Updated Modules
Key modules updated to use enums:
- `core/task.py` - Uses enums for defaults and ID generation
- `commands/create.py` - Validates against enum values
- `commands/status.py` - Uses enums for status display
- `commands/portfolio.py` - Uses enums for priority sorting

## 📦 Installation

```bash
pip install --upgrade ai-trackdown-pytools
```

## 🙏 Acknowledgments

Thank you to all contributors and users who provided feedback for this release!

---

For questions or issues, please visit our [GitHub repository](https://github.com/ai-trackdown/ai-trackdown-pytools).