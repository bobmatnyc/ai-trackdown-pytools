# Sync Adapter System

The sync adapter system provides a flexible, extensible framework for syncing AI Trackdown tasks with external platforms like GitHub, ClickUp, Linear, and JIRA.

## Available Adapters

- **GitHub**: Full bidirectional sync with GitHub Issues and Pull Requests
- **ClickUp**: Full CRUD operations with ClickUp tasks, including rate limiting and custom fields

## Architecture

The system follows the adapter pattern with these key components:

- **SyncAdapter**: Abstract base class defining the interface all adapters must implement
- **AdapterRegistry**: Registry for dynamic adapter loading and management
- **SyncConfig**: Configuration dataclass for sync operations
- **SyncResult**: Result dataclass for tracking sync outcomes

## Creating a New Adapter

To add support for a new platform:

1. Create a new adapter class inheriting from `SyncAdapter`
2. Implement all required methods
3. Register the adapter with the registry

Example:

```python
from ai_trackdown_pytools.utils.sync import SyncAdapter, register_adapter

class MyPlatformAdapter(SyncAdapter):
    @property
    def platform_name(self) -> str:
        return "myplatform"
    
    @property
    def supported_types(self) -> Set[str]:
        return {"task", "issue", "bug"}
    
    async def authenticate(self) -> None:
        # Implement authentication
        pass
    
    # Implement other required methods...

# Register the adapter
register_adapter("myplatform", MyPlatformAdapter)
```

## Using an Adapter

```python
from ai_trackdown_pytools.utils.sync import SyncConfig, get_adapter

# Configure sync
config = SyncConfig(
    platform="github",
    auth_config={"repository": "owner/repo"},
    direction=SyncDirection.BIDIRECTIONAL,
    sync_tags=True,
    sync_assignees=True
)

# Get adapter instance
adapter = get_adapter("github", config)

# Authenticate
await adapter.authenticate()

# Pull items from platform
items = await adapter.pull_items()

# Push item to platform
mapping = await adapter.push_item(my_task)
```

## Configuration Options

- **platform**: Platform identifier
- **direction**: PULL, PUSH, or BIDIRECTIONAL
- **dry_run**: Test mode without making changes
- **auth_config**: Platform-specific authentication
- **sync_tags**: Sync tags/labels
- **sync_assignees**: Sync assignee information
- **label_mapping**: Map between internal and external labels
- **status_mapping**: Map between internal and external statuses
- **batch_size**: Number of items to process at once
- **included_types**: Only sync these types
- **excluded_types**: Don't sync these types

## Error Handling

The system provides specific exception types:

- **SyncError**: Base exception for all sync errors
- **AdapterNotFoundError**: No adapter for platform
- **AuthenticationError**: Authentication failed
- **ConfigurationError**: Invalid configuration
- **ConnectionError**: Network/connection issues
- **RateLimitError**: API rate limit exceeded
- **ValidationError**: Data validation failed

## Backward Compatibility

The `compat.py` module provides a bridge to the existing sync command, allowing gradual migration to the new adapter system.