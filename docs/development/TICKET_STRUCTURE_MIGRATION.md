# Ticket Structure Migration

## Overview

The ai-trackdown-pytools ticket structure has been migrated to match the official ai-trackdown schema, with proper directory organization and ID prefixes for different ticket types.

## Changes Implemented

### 1. Directory Structure

The ticket directory structure now follows the ai-trackdown schema:

```
tasks/
├── epics/     # EP-XXXX files (Strategic initiatives)
├── issues/    # ISS-XXXX files (Implementation features)  
├── tasks/     # TSK-XXXX files (Development work)
└── prs/       # PR-XXXX files (Code changes)
```

### 2. ID Generation

Updated the ID generation system to use correct prefixes based on ticket type:

- **Epics**: `EP-XXXX` (e.g., EP-0001)
- **Issues**: `ISS-XXXX` (e.g., ISS-0001)
- **Tasks**: `TSK-XXXX` (e.g., TSK-0001)
- **Pull Requests**: `PR-XXXX` (e.g., PR-0001)

### 3. Configuration Updates

The configuration system now maintains separate counters for each ticket type:

```yaml
epics:
  counter: 4
issues:
  counter: 6
tasks:
  counter: 19
prs:
  counter: 5
```

### 4. Code Changes

#### Task Manager (`src/ai_trackdown_pytools/core/task.py`)

- Modified `_generate_task_id()` to accept a `task_type` parameter
- Updated `_get_task_file_path()` to route tickets to correct directories
- Modified `create_task()` to accept a `type` parameter

#### CLI Commands

- Updated `create epic` command to use `type="epic"`
- Updated `create issue` command to use `type="issue"`
- Updated `pr create` command to use `type="pr"`

### 5. Migration Script

Created `scripts/migrate_ticket_structure.py` to:

- Analyze existing tickets and determine their type
- Move tickets to appropriate directories
- Update IDs where necessary
- Update configuration counters

## Migration Results

Successfully migrated 11 existing tickets:

- 2 Epics (EP-0001, EP-0002)
- 4 Issues (ISS-0001 to ISS-0004)
- 2 Tasks (TSK-0011, TSK-0016)
- 3 Pull Requests (PR-0001 to PR-0003)

## Usage

### Creating Tickets

```bash
# Create an epic
aitrackdown create epic "Strategic Initiative"

# Create an issue
aitrackdown create issue "New Feature"

# Create a task
aitrackdown create task "Implement function"

# Create a pull request
aitrackdown pr create "Fix bug #123"
```

### Running Migration

For projects with existing tickets in the old structure:

```bash
# Dry run to see what would be migrated
python scripts/migrate_ticket_structure.py --dry-run

# Execute migration
python scripts/migrate_ticket_structure.py
```

## Benefits

1. **Clear Organization**: Each ticket type has its own directory
2. **Proper Identification**: ID prefixes immediately identify ticket type
3. **Schema Compliance**: Matches official ai-trackdown schema
4. **Scalability**: Separate counters prevent ID conflicts
5. **Migration Path**: Existing projects can be migrated easily

## Future Considerations

- Consider adding support for Comments (CMT-XXX)
- Add validation to ensure ticket types match their ID prefixes
- Implement cross-type relationships (e.g., issues linking to epics)