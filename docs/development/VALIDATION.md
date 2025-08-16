# Data Validation

AI Trackdown PyTools includes comprehensive data validation to ensure data integrity and consistency.

## Overview

The validation system provides:

- **Schema Validation** - Ensures data structure matches expected format
- **Type Safety** - Validates data types and required fields
- **Workflow Validation** - Checks valid status transitions
- **Relationship Validation** - Validates task dependencies and hierarchies

## Using Validation

### Command Line Validation

```bash
# Validate entire project
aitrackdown validate

# Validate specific files
aitrackdown validate tickets/tasks/TSK-0001.md

# Validate with detailed output
aitrackdown validate --verbose
```

### Programmatic Validation

```python
from ai_trackdown_pytools.utils.validation import SchemaValidator

validator = SchemaValidator()

# Validate task data
task_data = {
    "id": "TSK-0001",
    "title": "Fix authentication bug",
    "status": "open",
    "priority": "high",
    "created_at": "2025-07-11T10:00:00",
    "updated_at": "2025-07-11T10:00:00"
}

result = validator.validate_ticket(task_data, "task")
if result.valid:
    print("Validation passed!")
else:
    for error in result.errors:
        print(f"Error: {error}")
```

## Common Validation Scenarios

### Status Transitions
Only certain status transitions are allowed:
- `open` → `in_progress`, `blocked`, `closed`
- `in_progress` → `in_review`, `blocked`, `closed`
- `in_review` → `resolved`, `in_progress`
- `resolved` → `closed`, `in_progress`

### Required Fields
All tickets must have:
- `id` - Unique identifier
- `title` - Descriptive title
- `status` - Current workflow status
- `created_at` - Creation timestamp

### ID Format Validation
- Tasks: `TSK-XXXX` (e.g., TSK-0001)
- Issues: `ISS-XXXX` (e.g., ISS-0001)
- Epics: `EP-XXXX` (e.g., EP-0001)
- PRs: `PR-XXXX` (e.g., PR-0001)

## API Reference

For detailed API documentation, see the inline documentation in:
- `ai_trackdown_pytools.utils.validation`
- `ai_trackdown_pytools.core.models`

## Troubleshooting

### Common Validation Errors

1. **Invalid ID Format**
   - Error: `ID 'TASK-001' doesn't match expected pattern`
   - Solution: Use correct format (TSK-0001, ISS-0001, etc.)

2. **Missing Required Fields**
   - Error: `Field 'created_at': field required`
   - Solution: Add all required fields to ticket frontmatter

3. **Invalid Status Transition**
   - Error: `Invalid status transition from 'completed' to 'open'`
   - Solution: Use valid status transitions according to workflow

4. **Circular Dependencies**
   - Error: `Circular dependency detected`
   - Solution: Remove circular references in task dependencies

For detailed validation schemas and advanced usage, see the inline documentation in the source code.
