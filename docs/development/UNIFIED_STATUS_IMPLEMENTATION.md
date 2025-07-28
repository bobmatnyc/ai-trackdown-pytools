# Unified Status and Resolution Implementation

## Overview

This document describes the implementation of the unified status and resolution system in ai-trackdown-pytools. This system provides:

- A single, consistent status enum (`UnifiedStatus`) used across all ticket types
- Resolution tracking for terminal states
- State transition validation through a workflow state machine
- Full backward compatibility with existing status enums

## Key Components

### 1. Unified Status System (`core/workflow.py`)

The `UnifiedStatus` enum consolidates all status values from different ticket types:

```python
class UnifiedStatus(str, Enum):
    # Initial states
    OPEN = "open"
    NEW = "new"
    TODO = "todo"
    
    # Active states
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    TESTING = "testing"
    REOPENED = "reopened"
    ESCALATED = "escalated"
    
    # Waiting states
    PENDING = "pending"
    ON_HOLD = "on_hold"
    BLOCKED = "blocked"
    WAITING = "waiting"
    
    # Terminal states
    COMPLETED = "completed"
    RESOLVED = "resolved"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    MERGED = "merged"
    DONE = "done"
    
    # Special states for specific workflows
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    PLANNING = "planning"
    ACTIVE = "active"
    ARCHIVED = "archived"
```

### 2. Resolution Tracking

Resolution types track the outcome reasoning for terminal states:

```python
class ResolutionType(str, Enum):
    # Successful resolutions
    FIXED = "fixed"
    COMPLETED = "completed"
    DELIVERED = "delivered"
    IMPLEMENTED = "implemented"
    DOCUMENTED = "documented"
    CONFIGURED = "configured"
    WORKAROUND = "workaround"
    
    # Unsuccessful resolutions
    WONT_FIX = "wont_fix"
    INCOMPLETE = "incomplete"
    ABANDONED = "abandoned"
    TIMEOUT = "timeout"
    NO_RESPONSE = "no_response"
    
    # Invalid resolutions
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    CANNOT_REPRODUCE = "cannot_reproduce"
    WORKS_AS_DESIGNED = "works_as_designed"
    USER_ERROR = "user_error"
    OUT_OF_SCOPE = "out_of_scope"
    
    # Deferred resolutions
    DEFERRED = "deferred"
    MOVED = "moved"
    BACKLOG = "backlog"
```

### 3. Workflow State Machine

The `WorkflowStateMachine` enforces valid state transitions:

```python
workflow_state_machine = WorkflowStateMachine()

# Example: Check if transition is valid
is_valid, error = workflow_state_machine.validate_transition(
    UnifiedStatus.OPEN, 
    UnifiedStatus.IN_PROGRESS
)

# Example: Get valid transitions from current state
transitions = workflow_state_machine.get_valid_transitions(UnifiedStatus.OPEN)
```

### 4. Model Updates

All ticket models now include resolution tracking fields:

```python
class BaseTicketModel(BaseModel):
    # ... existing fields ...
    
    # Resolution tracking fields
    resolution: Optional[ResolutionType] = None
    resolution_comment: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    # State tracking fields
    status_history: List[Dict[str, Any]] = []
    reopen_count: int = 0
    
    # Methods for state transitions
    def can_transition_to(self, new_status, resolution=None) -> tuple[bool, Optional[str]]
    def transition_to(self, new_status, resolution=None, resolution_comment=None, user=None)
```

## Backward Compatibility

### Status Field Updates

Each model's status field now accepts both unified and legacy status values:

```python
class TaskModel(BaseTicketModel):
    status: Union[UnifiedStatus, TaskStatus] = Field(
        UnifiedStatus.OPEN, description="Task status"
    )
```

### Automatic Status Normalization

Models include validators that automatically convert legacy status values:

```python
@field_validator("status", mode="before")
@classmethod
def normalize_status(cls, v):
    """Normalize status to UnifiedStatus for backward compatibility."""
    if isinstance(v, str):
        # Convert string to UnifiedStatus
        return map_legacy_status(v)
    elif isinstance(v, TaskStatus):
        # Convert legacy enum to UnifiedStatus
        return map_legacy_status(v.value)
    return v
```

### Compatibility Module

The `core/compatibility.py` module provides utilities for working with both systems:

```python
# Convert any status format to UnifiedStatus
unified_status = convert_to_unified_status(old_status)

# Check if status is valid for ticket type
is_valid = is_compatible_status(status, "task")

# Convert back to legacy enum if needed
legacy_status = convert_to_legacy_status(unified_status, "task")
```

## Usage Examples

### 1. Creating a Ticket with Status

```python
# Works with unified status
task = TaskModel(
    id="TSK-001",
    title="Implement feature",
    status=UnifiedStatus.OPEN,
    created_at=datetime.now(),
    updated_at=datetime.now()
)

# Also works with legacy status (automatically converted)
task2 = TaskModel(
    id="TSK-002",
    title="Fix bug",
    status="open",  # String converted to UnifiedStatus
    created_at=datetime.now(),
    updated_at=datetime.now()
)
```

### 2. Transitioning States

```python
# Check if transition is valid
can_transition, error = task.can_transition_to(UnifiedStatus.IN_PROGRESS)
if can_transition:
    # Perform transition
    task.transition_to(
        UnifiedStatus.IN_PROGRESS,
        user="developer@example.com"
    )

# Transition to terminal state with resolution
task.transition_to(
    UnifiedStatus.RESOLVED,
    resolution=ResolutionType.FIXED,
    resolution_comment="Fixed in PR #123",
    user="developer@example.com"
)
```

### 3. Querying Resolution Data

```python
# Check if ticket is resolved
if task.resolution:
    print(f"Resolved as: {task.resolution}")
    print(f"Resolution comment: {task.resolution_comment}")
    print(f"Resolved by: {task.resolved_by}")
    print(f"Resolved at: {task.resolved_at}")

# Get resolution category for metrics
category = get_resolution_category(task.resolution)
if category == ResolutionCategory.SUCCESSFUL:
    print("Successfully resolved!")
```

## Migration Guide

### For Existing Code

1. **Status Comparisons**: Update direct status comparisons to use UnifiedStatus:
   ```python
   # Old
   if task.status == TaskStatus.OPEN:
   
   # New (both work due to backward compatibility)
   if task.status == UnifiedStatus.OPEN:
   if task.status == "open":
   ```

2. **Status Assignment**: Can continue using strings or legacy enums:
   ```python
   # All of these work
   task.status = UnifiedStatus.IN_PROGRESS
   task.status = "in_progress"
   task.status = TaskStatus.IN_PROGRESS  # Automatically converted
   ```

3. **State Transitions**: Use the new transition methods for validation:
   ```python
   # Old (direct assignment)
   task.status = "completed"
   
   # New (with validation and tracking)
   task.transition_to(UnifiedStatus.COMPLETED)
   ```

### For New Code

1. Always use `UnifiedStatus` for status values
2. Use `transition_to()` method for state changes
3. Track resolutions for terminal states
4. Check transition validity before attempting changes

## Benefits

1. **Consistency**: Single status system across all ticket types
2. **Metrics**: Resolution tracking enables better reporting
3. **Validation**: State machine prevents invalid transitions
4. **History**: Full audit trail of status changes
5. **Flexibility**: Easy to add new statuses or modify workflows
6. **Compatibility**: Existing code continues to work without changes

## Future Enhancements

1. **Custom Workflows**: Load workflow definitions from JSON/YAML
2. **Workflow Hooks**: Execute actions on state transitions
3. **SLA Tracking**: Track time in each status
4. **Bulk Operations**: Transition multiple tickets with validation
5. **Workflow Visualization**: Generate state diagrams from definitions