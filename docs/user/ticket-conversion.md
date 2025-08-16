# Ticket Type Conversion

The AI Trackdown PyTools provides a powerful ticket conversion feature that allows you to change the type of existing tickets while preserving all metadata and relationships.

## Overview

The `aitrackdown convert` command enables you to transform tickets between different types, which is useful when:
- A task grows in scope and should become an issue
- An issue needs to be elevated to an epic
- An epic needs to be broken down into smaller issues
- You initially created the wrong ticket type

## Supported Conversions

The following conversions are supported:

```
TSK (Task) <--> ISS (Issue) <--> EP (Epic)
```

Valid conversion paths:
- **Task ↔ Issue** (bidirectional)
- **Issue ↔ Epic** (bidirectional)

Invalid conversions (not allowed):
- Task → Epic (must go through Issue)
- Epic → Task (must go through Issue)
- Any type → Bug, PR, or Comment

## Command Usage

### Basic Syntax

```bash
aitrackdown convert <ticket-id> --to <type> [options]
```

### Parameters

- `<ticket-id>`: The ID of the ticket to convert (e.g., TSK-001, ISS-002, EP-003)
- `--to <type>`: The target ticket type (`task`, `issue`, or `epic`)
- `--archive/--no-archive`: Whether to archive the original ticket (default: archive)

### Examples

Convert a task to an issue:
```bash
aitrackdown convert TSK-001 --to issue
```

Convert an issue to an epic:
```bash
aitrackdown convert ISS-002 --to epic
```

Convert an epic back to an issue:
```bash
aitrackdown convert EP-003 --to issue
```

Convert without archiving (deletes original):
```bash
aitrackdown convert ISS-004 --to task --no-archive
```

## What Gets Preserved

During conversion, ALL ticket metadata is preserved:

- **Title**: Unchanged
- **Description**: Unchanged
- **Status**: Maintained
- **Priority**: Maintained
- **Assignees**: All preserved
- **Tags**: All preserved
- **Due Date**: If set
- **Estimated/Actual Hours**: If tracked
- **Dependencies**: All preserved with IDs updated
- **Parent/Child Relationships**: Automatically updated
- **Labels**: All preserved
- **Custom Metadata**: All preserved

## Conversion Metadata

The converted ticket includes additional metadata to track the conversion:

```yaml
metadata:
  converted_from: TSK-001        # Original ticket ID
  converted_from_type: task      # Original ticket type
  converted_at: 2025-01-14T...   # Conversion timestamp
  conversion: task -> issue       # Conversion path
  original_created_at: 2025-01-01T...  # Original creation date
```

## File Organization

### Before Conversion
```
tickets/
├── tasks/
│   └── TSK-001.md    # Original task
├── issues/
└── epics/
```

### After Conversion (with archiving)
```
tickets/
├── tasks/
│   └── archive/
│       └── TSK-001.md    # Archived original
├── issues/
│   └── ISS-001.md        # New converted issue
└── epics/
```

### After Conversion (without archiving)
```
tickets/
├── tasks/
│   # TSK-001.md deleted
├── issues/
│   └── ISS-001.md        # New converted issue
└── epics/
```

## Relationship Updates

When a ticket is converted, all references to it in other tickets are automatically updated:

1. **Parent References**: If other tickets reference the converted ticket as their parent, those references are updated to the new ticket ID

2. **Dependencies**: If other tickets list the converted ticket as a dependency, those dependency lists are updated with the new ticket ID

3. **Bidirectional Updates**: The system ensures consistency across all ticket relationships

## Use Cases

### Escalating a Task to an Issue

When a simple task becomes more complex:
```bash
# Original: TSK-042 "Fix login button"
# Becomes: ISS-015 "Fix login button" (now tracked as an issue)
aitrackdown convert TSK-042 --to issue
```

### Promoting an Issue to an Epic

When an issue requires multiple sub-tasks:
```bash
# Original: ISS-008 "Implement payment system"
# Becomes: EP-003 "Implement payment system" (now an epic)
aitrackdown convert ISS-008 --to epic
```

### Demoting an Epic to an Issue

When an epic scope is reduced:
```bash
# Original: EP-002 "Q1 Roadmap"
# Becomes: ISS-020 "Q1 Roadmap" (simplified to issue)
aitrackdown convert EP-002 --to issue
```

## Best Practices

1. **Archive by Default**: Keep the `--archive` option (default) to maintain history

2. **Review Before Converting**: Use `aitrackdown show <ticket-id>` to review the ticket before conversion

3. **Update Documentation**: After conversion, update any external documentation that references the old ticket ID

4. **Communicate Changes**: Inform team members when converting shared tickets

5. **Use Appropriate Types**:
   - **Tasks**: For specific, actionable work items
   - **Issues**: For problems, features, or improvements
   - **Epics**: For large initiatives containing multiple issues/tasks

## Error Handling

The conversion command will fail with an error message if:

- The source ticket doesn't exist
- The target type is invalid
- The conversion path is not supported (e.g., task → epic)
- The ticket is already the target type
- File system permissions prevent the operation

## Tips

- You can chain conversions: Task → Issue → Epic
- Conversion is immediate and atomic
- Use `aitrackdown show <new-id>` to verify the conversion
- Check `tickets/*/archive/` directories to find archived originals
- The new ticket gets a fresh ID from the target type's sequence