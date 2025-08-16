# Sync Adapter API Reference

This document provides a comprehensive API reference for the sync adapter system in AI Trackdown PyTools.

## Core Classes

### SyncAdapter

Abstract base class for all sync adapters.

```python
class SyncAdapter(ABC):
    """Abstract base class for sync adapters."""
    
    def __init__(self, config: SyncConfig):
        """Initialize adapter with configuration."""
```

#### Properties

##### platform_name

```python
@property
@abstractmethod
def platform_name(self) -> str:
    """Get the platform name for this adapter.
    
    Returns:
        str: Platform identifier (e.g., "github", "jira")
    """
```

##### supported_types

```python
@property
@abstractmethod
def supported_types(self) -> Set[str]:
    """Get the set of ticket types supported by this platform.
    
    Returns:
        Set[str]: Set of supported types (e.g., {"task", "issue", "bug"})
    """
```

#### Abstract Methods

##### authenticate

```python
@abstractmethod
async def authenticate(self) -> None:
    """Authenticate with the external platform.
    
    Raises:
        AuthenticationError: If authentication fails
        ConfigurationError: If configuration is invalid
    """
```

##### test_connection

```python
@abstractmethod
async def test_connection(self) -> bool:
    """Test the connection to the external platform.
    
    Returns:
        bool: True if connection is successful
        
    Raises:
        ConnectionError: If connection test fails
    """
```

##### pull_items

```python
@abstractmethod
async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
    """Pull items from the external platform.
    
    Args:
        since: Only pull items updated after this timestamp
        
    Returns:
        List[TicketModel]: List of items in internal format
        
    Raises:
        SyncError: If pull operation fails
        RateLimitError: If rate limit is exceeded
    """
```

##### push_item

```python
@abstractmethod
async def push_item(self, item: TicketModel) -> Dict[str, Any]:
    """Push a single item to the external platform.
    
    Args:
        item: Item to push in internal format
        
    Returns:
        Dict[str, Any]: Mapping information including:
            - {platform}_id: The item's ID on the platform
            - {platform}_url: URL to view the item
            - {platform}_key: Human-readable key (if applicable)
            
    Raises:
        SyncError: If push operation fails
        ValidationError: If item data is invalid
        RateLimitError: If rate limit is exceeded
    """
```

##### update_item

```python
@abstractmethod
async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
    """Update an existing item on the external platform.
    
    Args:
        item: Updated item in internal format
        remote_id: ID of the item on the external platform
        
    Returns:
        Dict[str, Any]: Updated mapping information
        
    Raises:
        SyncError: If update operation fails
        ValidationError: If item data is invalid
        NotFoundError: If item doesn't exist on platform
    """
```

##### delete_item

```python
@abstractmethod
async def delete_item(self, remote_id: str) -> None:
    """Delete an item from the external platform.
    
    Args:
        remote_id: ID of the item to delete
        
    Raises:
        SyncError: If delete operation fails
        NotFoundError: If item doesn't exist
    """
```

##### get_item

```python
@abstractmethod
async def get_item(self, remote_id: str) -> Optional[TicketModel]:
    """Get a single item from the external platform.
    
    Args:
        remote_id: ID of the item to retrieve
        
    Returns:
        Optional[TicketModel]: Item in internal format or None if not found
        
    Raises:
        SyncError: If retrieval fails
    """
```

#### Inherited Methods

##### validate_config

```python
def validate_config(self) -> None:
    """Validate adapter configuration.
    
    Default implementation checks for auth_config presence.
    Override to add platform-specific validation.
    
    Raises:
        ConfigurationError: If configuration is invalid
    """
```

##### map_status

```python
def map_status(self, status: str, to_external: bool = True) -> str:
    """Map status between internal and external formats.
    
    Args:
        status: Status to map
        to_external: If True, map from internal to external
        
    Returns:
        str: Mapped status
    """
```

##### map_labels

```python
def map_labels(self, labels: List[str], to_external: bool = True) -> List[str]:
    """Map labels between internal and external formats.
    
    Args:
        labels: Labels to map
        to_external: If True, map from internal to external
        
    Returns:
        List[str]: Mapped labels
    """
```

##### filter_item_type

```python
def filter_item_type(self, item_type: str) -> bool:
    """Check if an item type should be synced.
    
    Args:
        item_type: Type to check
        
    Returns:
        bool: True if the type should be synced
    """
```

##### close

```python
async def close(self) -> None:
    """Close any open connections.
    
    Default implementation does nothing.
    Override to clean up resources.
    """
```

### SyncConfig

Configuration dataclass for sync operations.

```python
@dataclass
class SyncConfig:
    """Configuration for sync operations."""
    
    platform: str
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    dry_run: bool = False
    
    # Authentication
    auth_config: Dict[str, Any] = field(default_factory=dict)
    
    # Sync options
    sync_tags: bool = True
    sync_assignees: bool = True
    sync_comments: bool = True
    sync_attachments: bool = False
    
    # Filtering
    included_types: Optional[Set[str]] = None
    excluded_types: Optional[Set[str]] = None
    label_mapping: Dict[str, str] = field(default_factory=dict)
    status_mapping: Dict[str, str] = field(default_factory=dict)
    
    # Performance
    batch_size: int = 50
    max_retries: int = 3
    timeout: int = 30  # seconds
    
    # Advanced options
    preserve_ids: bool = False
    conflict_resolution: str = "remote_wins"
```

#### Fields

- **platform** (str): Platform identifier
- **direction** (SyncDirection): Sync direction (PULL, PUSH, BIDIRECTIONAL)
- **dry_run** (bool): If True, simulate operations without making changes
- **auth_config** (Dict[str, Any]): Platform-specific authentication configuration
- **sync_tags** (bool): Whether to sync tags/labels
- **sync_assignees** (bool): Whether to sync assignees
- **sync_comments** (bool): Whether to sync comments
- **sync_attachments** (bool): Whether to sync attachments
- **included_types** (Optional[Set[str]]): Types to include (None means all)
- **excluded_types** (Optional[Set[str]]): Types to exclude
- **label_mapping** (Dict[str, str]): Label translation map
- **status_mapping** (Dict[str, str]): Status translation map
- **batch_size** (int): Number of items to process in batch
- **max_retries** (int): Maximum retry attempts for failed operations
- **timeout** (int): Operation timeout in seconds
- **preserve_ids** (bool): Whether to preserve original IDs
- **conflict_resolution** (str): Conflict resolution strategy

### SyncResult

Result dataclass for sync operations.

```python
@dataclass
class SyncResult:
    """Result of a sync operation."""
    
    platform: str
    direction: SyncDirection
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    # Counts
    items_processed: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_deleted: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    
    # Details
    created_ids: List[Tuple[str, str]] = field(default_factory=list)
    updated_ids: List[Tuple[str, str]] = field(default_factory=list)
    deleted_ids: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
```

#### Properties

##### success

```python
@property
def success(self) -> bool:
    """Check if sync completed successfully.
    
    Returns:
        bool: True if completed without failures
    """
```

##### duration

```python
@property
def duration(self) -> Optional[float]:
    """Calculate sync duration in seconds.
    
    Returns:
        Optional[float]: Duration in seconds or None if not completed
    """
```

#### Methods

##### add_error

```python
def add_error(self, item_id: str, error: Exception, context: Dict[str, Any] = None):
    """Add an error to the result.
    
    Args:
        item_id: ID of the item that failed
        error: The exception that occurred
        context: Additional context information
    """
```

### SyncDirection

Enumeration for sync directions.

```python
class SyncDirection(str, Enum):
    """Sync direction enumeration."""
    
    PULL = "pull"  # From external platform to local
    PUSH = "push"  # From local to external platform
    BIDIRECTIONAL = "bidirectional"  # Both directions
```

## Exceptions

### Exception Hierarchy

```
SyncError (base)
├── ConfigurationError
├── AuthenticationError
├── ConnectionError
├── ValidationError
├── RateLimitError
└── NotFoundError
```

### SyncError

Base exception for all sync-related errors.

```python
class SyncError(Exception):
    """Base exception for sync operations."""
    
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        item_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize sync error."""
```

### ConfigurationError

Raised when configuration is invalid or missing.

```python
class ConfigurationError(SyncError):
    """Raised when configuration is invalid."""
    
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        missing_fields: Optional[List[str]] = None,
        help_text: Optional[str] = None
    ):
        """Initialize configuration error."""
```

### AuthenticationError

Raised when authentication fails.

```python
class AuthenticationError(SyncError):
    """Raised when authentication fails."""
```

### ConnectionError

Raised when connection to platform fails.

```python
class ConnectionError(SyncError):
    """Raised when connection fails."""
```

### ValidationError

Raised when data validation fails.

```python
class ValidationError(SyncError):
    """Raised when validation fails."""
    
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None
    ):
        """Initialize validation error."""
```

### RateLimitError

Raised when rate limit is exceeded.

```python
class RateLimitError(SyncError):
    """Raised when rate limit is exceeded."""
    
    def __init__(
        self,
        message: str,
        platform: Optional[str] = None,
        retry_after: Optional[int] = None
    ):
        """Initialize rate limit error."""
```

### NotFoundError

Raised when requested resource is not found.

```python
class NotFoundError(SyncError):
    """Raised when resource is not found."""
```

## Registry Functions

### get_adapter

```python
def get_adapter(platform: str, config: SyncConfig) -> SyncAdapter:
    """Get a sync adapter instance for the specified platform.
    
    Args:
        platform: Platform name
        config: Sync configuration
        
    Returns:
        SyncAdapter: Configured adapter instance
        
    Raises:
        AdapterNotFoundError: If platform is not supported
    """
```

### list_platforms

```python
def list_platforms() -> List[str]:
    """Get list of available sync platforms.
    
    Returns:
        List[str]: List of platform names
    """
```

### register_adapter

```python
def register_adapter(platform: str, adapter_class: Type[SyncAdapter]) -> None:
    """Register a sync adapter.
    
    Args:
        platform: Platform name
        adapter_class: Adapter class
        
    Raises:
        ValueError: If platform already registered
    """
```

## Compatibility Bridge

### SyncBridge

Provides backward compatibility with the old sync system.

```python
class SyncBridge:
    """Bridge between old sync interface and new adapter system."""
    
    def __init__(self, task_manager: TaskManager):
        """Initialize sync bridge."""
    
    def pull_from_platform(
        self,
        platform: str,
        config: Dict[str, Any],
        dry_run: bool = False
    ) -> Tuple[int, int]:
        """Pull items from platform using adapter.
        
        Returns:
            Tuple[int, int]: (created_count, updated_count)
        """
    
    def push_to_platform(
        self,
        platform: str,
        config: Dict[str, Any],
        dry_run: bool = False
    ) -> Tuple[int, int, List[str]]:
        """Push items to platform using adapter.
        
        Returns:
            Tuple[int, int, List[str]]: (created, updated, errors)
        """
```

## Model Classes

### TicketModel

Base class for all ticket types.

```python
class TicketModel(BaseModel):
    """Base model for all ticket types."""
    
    id: str
    title: str
    description: Optional[str] = ""
    status: str = "open"
    priority: str = "medium"
    tags: List[str] = Field(default_factory=list)
    assignees: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### TaskModel

Model for tasks.

```python
class TaskModel(TicketModel):
    """Model for tasks."""
    
    status: TaskStatus = TaskStatus.OPEN
    priority: Priority = Priority.MEDIUM
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
```

### IssueModel

Model for issues.

```python
class IssueModel(TicketModel):
    """Model for issues."""
    
    status: IssueStatus = IssueStatus.OPEN
    priority: Priority = Priority.MEDIUM
    issue_type: str = "bug"
    severity: Optional[str] = None
    affected_version: Optional[str] = None
    fix_version: Optional[str] = None
```

### PRModel

Model for pull requests.

```python
class PRModel(TicketModel):
    """Model for pull requests."""
    
    status: PRStatus = PRStatus.OPEN
    source_branch: Optional[str] = None
    target_branch: Optional[str] = None
    reviewers: List[str] = Field(default_factory=list)
    approved_by: List[str] = Field(default_factory=list)
    merged_at: Optional[datetime] = None
    merged_by: Optional[str] = None
```

### EpicModel

Model for epics.

```python
class EpicModel(TicketModel):
    """Model for epics."""
    
    status: EpicStatus = EpicStatus.OPEN
    child_issues: List[str] = Field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: float = 0.0
```

### BugModel

Model for bugs.

```python
class BugModel(IssueModel):
    """Model for bugs."""
    
    issue_type: str = "bug"
    severity: str = "medium"
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    environment: Optional[str] = None
```

## Enumerations

### TaskStatus

```python
class TaskStatus(str, Enum):
    """Task status enumeration."""
    
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
```

### IssueStatus

```python
class IssueStatus(str, Enum):
    """Issue status enumeration."""
    
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
```

### PRStatus

```python
class PRStatus(str, Enum):
    """Pull request status enumeration."""
    
    OPEN = "open"
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"
```

### EpicStatus

```python
class EpicStatus(str, Enum):
    """Epic status enumeration."""
    
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

### Priority

```python
class Priority(str, Enum):
    """Priority enumeration."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

## Usage Examples

### Basic Adapter Usage

```python
from ai_trackdown_pytools.utils.sync import get_adapter, SyncConfig
from ai_trackdown_pytools.utils.sync.base import SyncDirection

# Create configuration
config = SyncConfig(
    platform="github",
    direction=SyncDirection.PULL,
    auth_config={
        "repository": "owner/repo",
        "token": "ghp_xxxxx"
    }
)

# Get adapter instance
adapter = get_adapter("github", config)

# Authenticate
await adapter.authenticate()

# Pull items
items = await adapter.pull_items(since=datetime(2024, 1, 1))

# Process items
for item in items:
    print(f"{item.id}: {item.title}")
```

### Error Handling

```python
from ai_trackdown_pytools.utils.sync.exceptions import (
    AuthenticationError,
    RateLimitError,
    SyncError
)

try:
    await adapter.push_item(task)
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
    # Re-authenticate and retry
except RateLimitError as e:
    print(f"Rate limit hit, retry after {e.retry_after} seconds")
    await asyncio.sleep(e.retry_after)
    # Retry
except SyncError as e:
    print(f"Sync failed: {e}")
    # Log and continue
```

### Custom Configuration

```python
# Advanced configuration
config = SyncConfig(
    platform="jira",
    auth_config={
        "server": "https://company.atlassian.net",
        "email": "user@company.com",
        "api_token": "xxxxx",
        "project_key": "PROJ"
    },
    # Filtering
    included_types={"issue", "bug"},
    excluded_types={"epic"},
    
    # Mappings
    status_mapping={
        "open": "To Do",
        "in_progress": "In Progress",
        "completed": "Done"
    },
    label_mapping={
        "frontend": "ui",
        "backend": "api"
    },
    
    # Performance
    batch_size=100,
    timeout=60,
    
    # Options
    sync_comments=True,
    dry_run=True
)
```

### Batch Operations

```python
# Pull all items and process in batches
all_items = []
since = datetime.now() - timedelta(days=30)

items = await adapter.pull_items(since=since)
all_items.extend(items)

# Process in batches
for i in range(0, len(all_items), config.batch_size):
    batch = all_items[i:i + config.batch_size]
    await process_batch(batch)
```

### Using the Sync Bridge

```python
from ai_trackdown_pytools.utils.sync.compat import SyncBridge
from ai_trackdown_pytools.core.task import TaskManager

# Initialize
task_manager = TaskManager(project_path)
bridge = SyncBridge(task_manager)

# Pull from platform
created, updated = bridge.pull_from_platform(
    "github",
    {"repository": "owner/repo"},
    dry_run=False
)

print(f"Created: {created}, Updated: {updated}")
```

## Type Annotations

All methods and functions in the sync adapter system are fully type-annotated. This enables:

- IDE autocomplete and type checking
- Static analysis with mypy
- Better documentation
- Fewer runtime errors

Example type annotations:

```python
from typing import Dict, Any, List, Optional, Set, Tuple, Union
from datetime import datetime

async def sync_items(
    items: List[Union[TaskModel, IssueModel]],
    config: SyncConfig,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> Tuple[List[str], List[str], Dict[str, Exception]]:
    """Sync multiple items with progress tracking.
    
    Args:
        items: Items to sync
        config: Sync configuration
        progress_callback: Optional callback for progress updates
        
    Returns:
        Tuple of:
            - List of successfully synced item IDs
            - List of skipped item IDs
            - Dict mapping failed item IDs to exceptions
    """
```

## Thread Safety

The sync adapter system is designed to be thread-safe:

- Adapters maintain their own state
- HTTP sessions are managed per-adapter instance
- No global mutable state

For concurrent operations, create separate adapter instances:

```python
import asyncio

async def sync_platform(platform: str, config: SyncConfig):
    adapter = get_adapter(platform, config)
    await adapter.authenticate()
    return await adapter.pull_items()

# Sync multiple platforms concurrently
configs = [
    SyncConfig(platform="github", ...),
    SyncConfig(platform="jira", ...),
    SyncConfig(platform="linear", ...)
]

results = await asyncio.gather(*[
    sync_platform(c.platform, c) for c in configs
])
```

## Performance Considerations

1. **Connection Pooling**: Adapters should reuse HTTP sessions
2. **Batch Operations**: Use batch_size configuration for large datasets
3. **Rate Limiting**: Respect platform rate limits automatically
4. **Caching**: Adapters may cache frequently accessed data
5. **Async Operations**: All I/O operations are asynchronous

## Extending the API

To extend the sync adapter API:

1. **Add Optional Methods**: Add new methods to SyncAdapter with default implementations
2. **Extend Models**: Create new model types inheriting from TicketModel
3. **Add Configuration Options**: Extend SyncConfig with new fields
4. **Create Mixins**: Add optional functionality via mixin classes

Example mixin:

```python
class CommentSyncMixin:
    """Mixin for adapters that support comment syncing."""
    
    async def pull_comments(self, item_id: str) -> List[Comment]:
        """Pull comments for an item."""
        raise NotImplementedError
    
    async def push_comment(self, item_id: str, comment: Comment) -> str:
        """Push a comment to an item."""
        raise NotImplementedError

class GitHubAdapter(SyncAdapter, CommentSyncMixin):
    """GitHub adapter with comment support."""
    pass
```