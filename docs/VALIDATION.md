# Validation System Documentation

The AI Trackdown PyTools validation system provides comprehensive schema validation, type safety, and data integrity checking for all ticket types. This document explains how to use the validation system effectively.

## Overview

The validation system consists of several layers:

1. **JSON Schema Validation** - Structural validation against JSON Schema definitions
2. **Pydantic Model Validation** - Type-safe validation with Python type hints
3. **YAML Frontmatter Parsing** - Parse and validate markdown files with YAML frontmatter
4. **Status Workflow Validation** - Validate status transitions according to business rules
5. **Relationship Validation** - Validate dependencies and parent-child relationships
6. **Custom Business Rules** - Domain-specific validation rules

## Quick Start

### Basic Validation

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

### File Validation

```python
from ai_trackdown_pytools.utils.validation import validate_ticket_file
from pathlib import Path

result = validate_ticket_file(Path("task-001.md"))
if not result.valid:
    for error in result.errors:
        print(f"Error: {error}")
    for warning in result.warnings:
        print(f"Warning: {warning}")
```

### CLI Validation

```bash
# Validate a single file
aitrackdown validate file task-001.md

# Validate all files in a directory
aitrackdown validate directory ./tasks/

# Validate ID format
aitrackdown validate id-format TSK-0001 task

# Validate status transition
aitrackdown validate transition open in_progress task

# Validate relationships
aitrackdown validate relationships ./tasks/
```

## Ticket Types and Schemas

### Task (TSK-XXXX)

```yaml
id: TSK-0001
title: "Task title"
description: "Task description"
status: open  # open, in_progress, completed, cancelled, blocked
priority: medium  # low, medium, high, critical
assignees: ["user1", "user2"]
tags: ["tag1", "tag2"]
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
due_date: 2025-07-15
estimated_hours: 8.0
actual_hours: 6.0
dependencies: ["TSK-0002"]
parent: "ISS-0001"  # Parent issue or epic
labels: ["enhancement"]
metadata:
  complexity: "medium"
```

### Epic (EP-XXXX)

```yaml
id: EP-0001
title: "Epic title"
description: "Epic description"
goal: "Epic objective"
business_value: "Business impact"
success_criteria: "Definition of done"
status: planning  # planning, in_progress, on_hold, completed, cancelled
priority: high
target_date: 2025-12-31
estimated_story_points: 50
child_issues: ["ISS-0001", "ISS-0002"]
dependencies: ["EP-0002"]
```

### Issue (ISS-XXXX)

```yaml
id: ISS-0001
title: "Issue title"
description: "Issue description"
issue_type: bug  # bug, feature, enhancement, documentation, question, epic_task
severity: high  # low, medium, high, critical
status: open  # open, in_progress, testing, completed, cancelled, blocked
environment: "production"
steps_to_reproduce: "1. Do this\n2. Do that"
expected_behavior: "Should work"
actual_behavior: "Doesn't work"
parent: "EP-0001"  # Parent epic
child_tasks: ["TSK-0001", "TSK-0002"]
related_prs: ["PR-0001"]
```

### Pull Request (PR-XXXX)

```yaml
id: PR-0001
title: "PR title"
description: "PR description"
pr_type: feature  # bug_fix, feature, breaking_change, documentation, refactoring, performance, other
status: draft  # draft, ready_for_review, in_review, changes_requested, approved, merged, closed
source_branch: "feature/auth"
target_branch: "main"
breaking_changes: false
reviewers: ["reviewer1", "reviewer2"]
related_issues: ["ISS-0001"]
closes_issues: ["ISS-0002"]
lines_added: 150
lines_deleted: 25
test_coverage: 95.0
```

### Project (PROJ-XXXX)

```yaml
id: PROJ-0001
name: "Project name"
description: "Project description"
status: active  # planning, active, on_hold, completed, cancelled, archived
author: "project-owner"
team_members: ["member1", "member2"]
start_date: 2025-01-01
end_date: 2025-12-31
estimated_hours: 1000.0
epics: ["EP-0001", "EP-0002"]
repository_url: "https://github.com/org/repo"
milestones:
  - name: "Alpha Release"
    target_date: 2025-06-01
    status: planned
```

## Status Workflows

### Task Workflow
- `open` → `in_progress`, `cancelled`
- `in_progress` → `completed`, `blocked`, `cancelled`
- `blocked` → `in_progress`, `cancelled`
- `completed` → (terminal)
- `cancelled` → (terminal)

### Epic Workflow
- `planning` → `in_progress`, `cancelled`
- `in_progress` → `on_hold`, `completed`, `cancelled`
- `on_hold` → `in_progress`, `cancelled`
- `completed` → (terminal)
- `cancelled` → (terminal)

### Issue Workflow
- `open` → `in_progress`, `cancelled`
- `in_progress` → `testing`, `blocked`, `cancelled`
- `testing` → `completed`, `in_progress`
- `blocked` → `in_progress`, `cancelled`
- `completed` → (terminal)
- `cancelled` → (terminal)

### PR Workflow
- `draft` → `ready_for_review`, `closed`
- `ready_for_review` → `in_review`, `draft`, `closed`
- `in_review` → `changes_requested`, `approved`, `closed`
- `changes_requested` → `ready_for_review`, `closed`
- `approved` → `merged`, `closed`
- `merged` → (terminal)
- `closed` → (terminal)

### Project Workflow
- `planning` → `active`, `cancelled`
- `active` → `on_hold`, `completed`, `cancelled`
- `on_hold` → `active`, `cancelled`
- `completed` → `archived`
- `cancelled` → `archived`
- `archived` → (terminal)

## Validation Rules

### ID Format Rules
- Tasks: `TSK-XXXX` (e.g., TSK-0001)
- Epics: `EP-XXXX` (e.g., EP-0001)
- Issues: `ISS-XXXX` (e.g., ISS-0001)
- Pull Requests: `PR-XXXX` (e.g., PR-0001)
- Projects: `PROJ-XXXX` (e.g., PROJ-0001)

### Relationship Rules
- Tasks can have issue or epic parents
- Issues can have epic parents
- Epics can have child issues
- Issues can have child tasks
- No circular dependencies allowed
- Referenced tickets must exist

### Business Rules
- High priority epics should have business value defined
- Bug reports should have reproduction steps
- Large PRs (>500 lines) should have reviewers
- Breaking changes should have high/critical priority
- Active projects should have team members

### Date Rules
- `updated_at` must be >= `created_at`
- `due_date` should not be in the past (warning)
- `target_date` should not be in the past for new items
- `end_date` must be after `start_date`

## Error Handling

### ValidationResult Object

```python
class ValidationResult:
    valid: bool          # Overall validation status
    errors: List[str]    # Critical errors that prevent processing
    warnings: List[str]  # Issues that should be addressed but don't prevent processing
    
    def add_error(self, error: str) -> None
    def add_warning(self, warning: str) -> None
    def merge(self, other: 'ValidationResult') -> None
    def to_dict(self) -> Dict[str, Any]
```

### Error Categories

1. **Schema Errors** - Data doesn't match JSON schema
2. **Type Errors** - Invalid data types or formats
3. **Business Rule Errors** - Violates domain-specific rules
4. **Relationship Errors** - Invalid references or circular dependencies
5. **Workflow Errors** - Invalid status transitions

## Advanced Usage

### Custom Validation Rules

```python
from ai_trackdown_pytools.utils.validation import SchemaValidator, ValidationResult

class CustomValidator(SchemaValidator):
    def _validate_custom_rules(self, data, ticket_type):
        result = super()._validate_custom_rules(data, ticket_type)
        
        # Add custom validation logic
        if ticket_type == "task" and data.get("priority") == "critical":
            if not data.get("assignees"):
                result.add_error("Critical tasks must have assignees")
        
        return result
```

### Bulk Validation

```python
from ai_trackdown_pytools.utils.validation import validate_relationships
from pathlib import Path

# Load all tickets from directory
tickets = []
for file_path in Path("./tasks").glob("**/*.md"):
    frontmatter, _, result = parse_ticket_file(file_path)
    if result.valid:
        tickets.append(frontmatter)

# Validate relationships between all tickets
relationship_result = validate_relationships(tickets)
```

### Integration with CI/CD

```bash
#!/bin/bash
# validate-tickets.sh

echo "Validating ticket files..."
aitrackdown validate directory ./tickets/ --output-format json > validation_results.json

if [ $? -ne 0 ]; then
    echo "Ticket validation failed!"
    cat validation_results.json | jq '.files[] | select(.validation.valid == false)'
    exit 1
fi

echo "All tickets valid!"
```

## Performance Considerations

- Schema validation is cached for better performance
- Pydantic models are compiled for fast validation
- Large directories can be validated in parallel
- Relationship validation uses efficient graph algorithms

## Troubleshooting

### Common Issues

1. **Invalid ID Format**
   ```
   Error: ID 'TASK-001' doesn't match expected pattern ^TSK-[0-9]+$ for task
   ```
   Solution: Use correct ID format (TSK-0001)

2. **Missing Required Fields**
   ```
   Error: Field 'created_at': field required
   ```
   Solution: Add all required fields to frontmatter

3. **Invalid Status Transition**
   ```
   Error: Invalid status transition from 'completed' to 'open' for task
   ```
   Solution: Use valid status transitions according to workflow

4. **Circular Dependencies**
   ```
   Error: Circular dependency detected involving ticket TSK-0001
   ```
   Solution: Remove circular references in dependencies

### Debug Mode

```python
# Enable verbose validation for debugging
result = validator.validate_ticket(data, "task")
if not result.valid:
    print("Validation failed:")
    for i, error in enumerate(result.errors):
        print(f"{i+1}. {error}")
    for i, warning in enumerate(result.warnings):
        print(f"Warning {i+1}: {warning}")
```

## API Reference

See the inline documentation in the source code for complete API details:

- `ai_trackdown_pytools.utils.validation`
- `ai_trackdown_pytools.utils.frontmatter`
- `ai_trackdown_pytools.core.models`

## Examples

See `examples/validation_demo.py` for a comprehensive demonstration of all validation features.
