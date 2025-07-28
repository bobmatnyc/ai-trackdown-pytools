# Comment Status Inheritance

## Overview

The comment status inheritance feature ensures that comments on tickets automatically inherit certain behaviors based on their parent ticket's status. This is particularly important for maintaining data integrity and preserving historical records when tickets reach terminal states.

## Key Concepts

### Terminal States

Terminal states are ticket statuses that indicate no further work is expected. These include:
- `completed`
- `resolved` 
- `closed`
- `cancelled`
- `merged`
- `done`
- `archived`

### Comment Locking

When a ticket transitions to a terminal state, all existing comments on that ticket become read-only. This ensures:
- Historical accuracy is maintained
- Audit trails remain intact
- No retroactive changes can be made to closed discussions

## Implementation Details

### CommentModel

The `CommentModel` class includes status-aware functionality:

```python
class CommentModel(BaseModel):
    # Status inheritance fields
    parent_status: Optional[UnifiedStatus]
    locked_at: Optional[datetime]
    locked_reason: Optional[str]
    is_read_only: bool
    
    def can_edit(self, parent_ticket: Optional[BaseTicketModel] = None) -> tuple[bool, Optional[str]]:
        """Check if comment can be edited based on parent ticket status."""
        
    def lock_due_to_parent_status(self, parent_status: UnifiedStatus, user: Optional[str] = None):
        """Lock comment when parent reaches terminal status."""
```

### CommentManager

The enhanced `CommentManager` enforces status rules:

```python
class CommentManager:
    def add_comment(self, author: str, content: str, force: bool = False) -> bool:
        """Add comment with status validation."""
        
    def get_comments_as_models(self) -> List[CommentModel]:
        """Get comments with automatic status inheritance."""
```

## Usage Examples

### Adding Comments

```python
# Normal comment on open ticket
add_comment_to_item("task", "TSK-001", "user", "Progress update", project_path)

# Attempting to comment on closed ticket (will fail)
add_comment_to_item("task", "TSK-002", "user", "Late comment", project_path)
# Raises: ValueError: Cannot add comments to closed tickets

# Force adding system comment on closed ticket
add_comment_to_item("task", "TSK-002", "system", "Audit note", project_path, force=True)
```

### CLI Usage

```bash
# Add comment normally
ai-trackdown comment add TSK-001 "Working on implementation"

# Force add comment on closed ticket
ai-trackdown comment add TSK-002 "Post-closure note" --force
```

### Checking Comment Status

```python
# Load comments with status awareness
manager = CommentManager(ticket_file_path)
comments = manager.get_comments_as_models()

for comment in comments:
    can_edit, reason = comment.can_edit()
    if not can_edit:
        print(f"Comment {comment.id} is read-only: {reason}")
```

## Behavior Rules

1. **New Comments on Terminal Tickets**
   - By default, new comments cannot be added to tickets in terminal states
   - Use `force=True` for system comments or special cases
   - CLI provides `--force` flag for admin overrides

2. **Existing Comments**
   - Automatically become read-only when parent ticket reaches terminal state
   - Lock timestamp and reason are recorded
   - Comments remain locked even if ticket is later reopened

3. **System Comments**
   - Always read-only regardless of parent status
   - Can be added to terminal tickets with `force=True`
   - Typically used for audit trails and automated updates

4. **Comment Editing**
   - Only allowed on non-terminal parent tickets
   - System comments cannot be edited
   - Explicitly locked comments cannot be edited
   - Edit attempts on locked comments raise `ValueError`

## API Reference

### CommentModel Methods

- `can_edit(parent_ticket=None)`: Check if comment can be edited
- `lock_due_to_parent_status(status, user=None)`: Lock comment due to parent status
- `update_content(content, editor, parent_ticket=None)`: Update comment with validation

### CommentManager Methods

- `add_comment(author, content, force=False)`: Add comment with status checking
- `get_comments_as_models()`: Get comments as validated models
- `_load_parent_ticket()`: Load parent ticket for status validation

### BaseTicketModel Methods

- `get_comment_lock_status()`: Check if comments should be locked
- `transition_to(new_status, ...)`: Transition status (affects comment locking)

## Best Practices

1. **Always use the validation methods** - Don't bypass status checks unless necessary
2. **Document force usage** - When forcing comments on closed tickets, explain why
3. **Handle validation errors** - Catch and display user-friendly error messages
4. **Preserve history** - Never delete or modify locked comments directly
5. **Use system comments** - For automated updates and audit trails

## Testing

The feature includes comprehensive tests in `test_comment_status_inheritance.py`:
- Comment creation and validation
- Status inheritance behavior
- Lock/unlock scenarios
- Force comment addition
- CLI integration tests

Run tests with:
```bash
pytest tests/unit/test_comment_status_inheritance.py -v
```