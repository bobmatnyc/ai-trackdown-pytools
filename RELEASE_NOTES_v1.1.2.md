# Release Notes - v1.1.2

**Release Date:** 2025-07-23  
**Release Type:** Patch Release (Bug Fixes)

## Overview

Version 1.1.2 is a critical patch release that fixes a significant bug affecting PR (Pull Request) and Epic update functionality. This bug prevented users from properly closing or updating PRs and Epics, which are core features of the AI Trackdown system.

## Critical Bug Fixes

### 1. PR and Epic Update Functionality (ISS-0012)

**Problem:** Users were unable to close or update Pull Requests and Epics due to a missing method in the TaskManager class. This resulted in errors when attempting to update task relationships or change PR/Epic status.

**Solution:** Added the missing `save_task` method to the TaskManager class, which properly handles task persistence and index updates.

**Impact:** This fix restores full functionality to PR and Epic management, allowing users to:
- Close Pull Requests with proper status updates
- Update Epic metadata and relationships
- Manage task relationships without errors
- Properly save all task modifications

### 2. Enhanced Error Handling

**Improvement:** Updated error handling and display in task update operations to provide clearer feedback when issues occur.

## Technical Details

The fix involved adding the following method to the TaskManager class:

```python
def save_task(self, task: Task) -> None:
    """Save task to file."""
    self._save_task_file(task.data, task.file_path)
    
    # Update index
    update_index_on_file_change(self.project_path, task.file_path)
```

This ensures that all task modifications are properly persisted to disk and the search index is updated accordingly.

## Upgrade Recommendation

**Highly Recommended:** All users should upgrade to v1.1.2 immediately if they use PR or Epic functionality. This patch release contains no breaking changes and is fully backward compatible with v1.1.1.

## Installation

Update to the latest version:

```bash
pip install --upgrade ai-trackdown-pytools
```

Or install specific version:

```bash
pip install ai-trackdown-pytools==1.1.2
```

## Verification

After upgrading, verify the fix by testing PR and Epic operations:

```bash
# Test PR update
aitrackdown pr update PR-001 --status merged

# Test Epic update  
aitrackdown epic update EP-001 --add-subtask TSK-002

# Verify version
aitrackdown --version
```

## Acknowledgments

Thank you to the users who reported this issue and helped identify the root cause. Your feedback is invaluable in maintaining the quality and reliability of AI Trackdown.

## Next Steps

The development team is working on comprehensive test coverage for all update operations to prevent similar issues in future releases. Version 1.2.0 will include enhanced validation and error recovery mechanisms.

---

For more information, see the [CHANGELOG](CHANGELOG.md) or visit our [GitHub repository](https://github.com/MasaFoundation/ai-trackdown-pytools).