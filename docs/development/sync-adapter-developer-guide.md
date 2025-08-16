# Sync Adapter Developer Guide

This guide explains how to create new sync adapters for AI Trackdown PyTools to integrate with additional project management platforms.

## Overview

The sync adapter system uses an abstract base class pattern to provide a consistent interface for all platform integrations. Each adapter implements platform-specific logic while inheriting common functionality from the base class.

## Architecture

### Core Components

1. **Base Adapter (`SyncAdapter`)**: Abstract base class defining the interface
2. **Platform Adapters**: Concrete implementations for each platform
3. **Registry**: Automatic registration system for adapter discovery
4. **Exceptions**: Structured error handling hierarchy
5. **Models**: Internal data models for consistent data representation

### Class Hierarchy

```
SyncAdapter (ABC)
├── GitHubAdapter
├── ClickUpAdapter
├── LinearAdapter
└── YourNewAdapter
```

## Creating a New Adapter

### Step 1: Create Adapter File

Create a new file in `src/ai_trackdown_pytools/utils/sync/`:

```python
# src/ai_trackdown_pytools/utils/sync/yourplatform_adapter.py
"""YourPlatform sync adapter implementation."""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

from ai_trackdown_pytools.core.models import (
    TaskModel,
    IssueModel,
    TicketModel,
    TaskStatus,
    Priority,
)
from .base import SyncAdapter, SyncConfig
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    ConfigurationError,
    SyncError,
)


class YourPlatformAdapter(SyncAdapter):
    """Sync adapter for YourPlatform integration."""
    
    @property
    def platform_name(self) -> str:
        """Get the platform name."""
        return "yourplatform"
    
    @property
    def supported_types(self) -> Set[str]:
        """Get supported ticket types."""
        return {"task", "issue", "bug"}  # Define what types your platform supports
```

### Step 2: Implement Required Methods

#### Authentication

```python
async def authenticate(self) -> None:
    """Authenticate with the platform.
    
    Raises:
        AuthenticationError: If authentication fails
    """
    # Validate configuration
    self.validate_config()
    
    # Get credentials from config
    api_key = self.config.auth_config.get("api_key")
    if not api_key:
        raise ConfigurationError(
            "API key not provided",
            platform=self.platform_name,
            missing_fields=["api_key"]
        )
    
    try:
        # Initialize your API client
        self._client = YourPlatformClient(api_key)
        
        # Test authentication
        await self._client.verify_credentials()
        
        self._authenticated = True
        
    except YourPlatformAuthError as e:
        raise AuthenticationError(
            f"Authentication failed: {str(e)}",
            platform=self.platform_name
        )
```

#### Connection Testing

```python
async def test_connection(self) -> bool:
    """Test the connection to the platform.
    
    Returns:
        True if connection is successful
        
    Raises:
        ConnectionError: If connection test fails
    """
    if not self._authenticated:
        await self.authenticate()
    
    try:
        # Perform a simple API call
        await self._client.ping()
        return True
        
    except Exception as e:
        raise ConnectionError(
            f"Connection test failed: {str(e)}",
            platform=self.platform_name
        )
```

#### Pull Items

```python
async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
    """Pull items from the platform.
    
    Args:
        since: Only pull items updated after this timestamp
        
    Returns:
        List of items in internal format
        
    Raises:
        SyncError: If pull operation fails
    """
    if not self._authenticated:
        await self.authenticate()
    
    try:
        # Build filter parameters
        params = {}
        if since:
            params["updated_since"] = since.isoformat()
        
        # Fetch items from platform
        platform_items = await self._client.list_items(**params)
        
        # Convert to internal models
        items = []
        for platform_item in platform_items:
            try:
                # Apply type filtering
                if not self.filter_item_type(platform_item["type"]):
                    continue
                
                # Map to internal model
                internal_item = self._map_from_platform(platform_item)
                items.append(internal_item)
                
            except Exception as e:
                # Log but don't fail entire sync
                print(f"Error mapping item {platform_item.get('id')}: {e}")
        
        return items
        
    except Exception as e:
        raise SyncError(
            f"Failed to pull items: {str(e)}",
            platform=self.platform_name
        )
```

#### Push Item

```python
async def push_item(self, item: TicketModel) -> Dict[str, Any]:
    """Push a single item to the platform.
    
    Args:
        item: Item to push in internal format
        
    Returns:
        Mapping information
        
    Raises:
        SyncError: If push operation fails
    """
    if not self._authenticated:
        await self.authenticate()
    
    try:
        # Convert to platform format
        platform_data = self._map_to_platform(item)
        
        # Create on platform
        created_item = await self._client.create_item(platform_data)
        
        # Return mapping info
        return {
            f"{self.platform_name}_id": created_item["id"],
            f"{self.platform_name}_url": created_item["url"],
            f"{self.platform_name}_key": created_item.get("key"),
        }
        
    except Exception as e:
        raise SyncError(
            f"Failed to push item: {str(e)}",
            platform=self.platform_name,
            item_id=item.id
        )
```

### Step 3: Implement Mapping Methods

#### Map to Platform Format

```python
def _map_to_platform(self, item: TicketModel) -> Dict[str, Any]:
    """Map internal model to platform format.
    
    Args:
        item: Internal ticket model
        
    Returns:
        Platform-specific data format
    """
    # Basic mapping
    data = {
        "title": item.title,
        "description": item.description or "",
        "type": self._get_platform_type(item),
    }
    
    # Map status
    if hasattr(item, "status"):
        data["status"] = self._map_status_to_platform(item.status)
    
    # Map priority
    if hasattr(item, "priority"):
        data["priority"] = self._map_priority_to_platform(item.priority)
    
    # Map assignees
    if item.assignees:
        data["assignees"] = self._map_assignees_to_platform(item.assignees)
    
    # Map labels/tags
    if item.tags:
        data["labels"] = self.map_labels(item.tags, to_external=True)
    
    # Map custom fields
    if item.metadata.get("custom_fields"):
        data["custom_fields"] = item.metadata["custom_fields"]
    
    return data
```

#### Map from Platform Format

```python
def _map_from_platform(self, platform_data: Dict[str, Any]) -> TicketModel:
    """Map platform data to internal model.
    
    Args:
        platform_data: Platform-specific data
        
    Returns:
        Internal ticket model
    """
    # Determine model type
    model_class = self._get_model_class(platform_data["type"])
    
    # Basic mapping
    data = {
        "id": f"{model_class.__name__[:3].upper()}-{platform_data['id']}",
        "title": platform_data["title"],
        "description": platform_data.get("description", ""),
        "created_at": self._parse_datetime(platform_data["created_at"]),
        "updated_at": self._parse_datetime(platform_data["updated_at"]),
        "metadata": {
            f"{self.platform_name}_id": platform_data["id"],
            f"{self.platform_name}_url": platform_data.get("url"),
            "platform": self.platform_name,
        }
    }
    
    # Map status
    if "status" in platform_data:
        data["status"] = self._map_status_from_platform(platform_data["status"])
    
    # Map priority
    if "priority" in platform_data:
        data["priority"] = self._map_priority_from_platform(platform_data["priority"])
    
    # Map assignees
    if "assignees" in platform_data:
        data["assignees"] = self._map_assignees_from_platform(platform_data["assignees"])
    
    # Map tags
    if "labels" in platform_data:
        data["tags"] = self.map_labels(platform_data["labels"], to_external=False)
    
    return model_class(**data)
```

### Step 4: Add Status and Priority Mapping

```python
# Status mapping
STATUS_TO_PLATFORM = {
    TaskStatus.OPEN: "todo",
    TaskStatus.IN_PROGRESS: "in_progress",
    TaskStatus.COMPLETED: "done",
    TaskStatus.CANCELLED: "cancelled",
    TaskStatus.BLOCKED: "blocked",
}

STATUS_FROM_PLATFORM = {v: k for k, v in STATUS_TO_PLATFORM.items()}

def _map_status_to_platform(self, status: TaskStatus) -> str:
    """Map internal status to platform status."""
    return self.STATUS_TO_PLATFORM.get(status, "todo")

def _map_status_from_platform(self, platform_status: str) -> TaskStatus:
    """Map platform status to internal status."""
    return self.STATUS_FROM_PLATFORM.get(
        platform_status.lower(), 
        TaskStatus.OPEN
    )

# Priority mapping
PRIORITY_TO_PLATFORM = {
    Priority.CRITICAL: "highest",
    Priority.HIGH: "high",
    Priority.MEDIUM: "medium",
    Priority.LOW: "low",
}

PRIORITY_FROM_PLATFORM = {v: k for k, v in PRIORITY_TO_PLATFORM.items()}

def _map_priority_to_platform(self, priority: Priority) -> str:
    """Map internal priority to platform priority."""
    return self.PRIORITY_TO_PLATFORM.get(priority, "medium")

def _map_priority_from_platform(self, platform_priority: str) -> Priority:
    """Map platform priority to internal priority."""
    return self.PRIORITY_FROM_PLATFORM.get(
        platform_priority.lower(),
        Priority.MEDIUM
    )
```

### Step 5: Handle Platform-Specific Features

```python
def validate_config(self) -> None:
    """Validate platform-specific configuration."""
    super().validate_config()
    
    # Check required fields
    required_fields = ["api_key", "workspace_id"]
    missing_fields = []
    
    for field in required_fields:
        if not self.config.auth_config.get(field):
            missing_fields.append(field)
    
    if missing_fields:
        raise ConfigurationError(
            "Missing required configuration",
            platform=self.platform_name,
            missing_fields=missing_fields
        )
    
    # Validate field values
    workspace_id = self.config.auth_config.get("workspace_id")
    if workspace_id and not workspace_id.isdigit():
        raise ConfigurationError(
            "Invalid workspace_id format",
            platform=self.platform_name,
            details="workspace_id must be numeric"
        )

async def get_custom_fields(self) -> Dict[str, Any]:
    """Get available custom fields from platform."""
    if not self._authenticated:
        await self.authenticate()
    
    try:
        fields = await self._client.get_custom_fields()
        return {
            field["name"]: field["id"]
            for field in fields
        }
    except Exception as e:
        raise SyncError(
            f"Failed to fetch custom fields: {str(e)}",
            platform=self.platform_name
        )
```

### Step 6: Register the Adapter

Add to `src/ai_trackdown_pytools/utils/sync/__init__.py`:

```python
# Import your adapter
from .yourplatform_adapter import YourPlatformAdapter

# The adapter will auto-register when imported
```

### Step 7: Add Configuration Help

Update the sync command configuration help in `src/ai_trackdown_pytools/commands/sync.py`:

```python
config_help = {
    # ... existing platforms ...
    "yourplatform": [
        ("api_key", "YourPlatform API key"),
        ("workspace_id", "YourPlatform workspace ID"),
        ("project_id", "Default project ID (optional)"),
    ],
}
```

## Best Practices

### 1. Error Handling

Always use the structured exception hierarchy:

```python
try:
    # Platform operation
    result = await platform_api.call()
except PlatformAuthError:
    raise AuthenticationError("Invalid credentials", platform=self.platform_name)
except PlatformRateLimit as e:
    raise RateLimitError(
        "Rate limit exceeded",
        platform=self.platform_name,
        retry_after=e.retry_after
    )
except PlatformNotFound:
    raise ValidationError("Resource not found", platform=self.platform_name)
except Exception as e:
    raise SyncError(f"Unexpected error: {str(e)}", platform=self.platform_name)
```

### 2. Async Operations

Use async/await for all I/O operations:

```python
async def _fetch_with_pagination(self, endpoint: str) -> List[Dict]:
    """Fetch all pages of results."""
    all_items = []
    page = 1
    
    while True:
        response = await self._session.get(
            f"{endpoint}?page={page}&limit=100"
        )
        data = await response.json()
        
        all_items.extend(data["items"])
        
        if not data.get("has_next"):
            break
            
        page += 1
        
        # Respect rate limits
        await self._check_rate_limit(response)
    
    return all_items
```

### 3. Rate Limiting

Implement rate limit handling:

```python
async def _check_rate_limit(self, response) -> None:
    """Check and handle rate limits."""
    remaining = int(response.headers.get("X-RateLimit-Remaining", 100))
    reset = int(response.headers.get("X-RateLimit-Reset", 0))
    
    if remaining < 10:
        # Getting close to limit, slow down
        await asyncio.sleep(1)
    
    if remaining == 0:
        # Hit rate limit, wait until reset
        wait_time = max(0, reset - int(time.time()))
        raise RateLimitError(
            "Rate limit exceeded",
            platform=self.platform_name,
            retry_after=wait_time
        )
```

### 4. Session Management

Properly manage HTTP sessions:

```python
async def _ensure_session(self) -> None:
    """Ensure HTTP session is created."""
    if not self._session:
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self._session = aiohttp.ClientSession(
            headers=self._headers,
            timeout=timeout
        )

async def close(self) -> None:
    """Close any open connections."""
    if self._session:
        await self._session.close()
        self._session = None
```

### 5. Type Safety

Use type hints throughout:

```python
from typing import TypeVar, Generic, Union

T = TypeVar("T", bound=TicketModel)

async def push_item_typed(self, item: T) -> Tuple[T, Dict[str, Any]]:
    """Type-safe push with model preservation."""
    mapping = await self.push_item(item)
    
    # Update item with platform metadata
    item.metadata.update(mapping)
    
    return item, mapping
```

### 6. Configuration Validation

Validate configuration early and clearly:

```python
def validate_config(self) -> None:
    """Validate configuration with helpful error messages."""
    super().validate_config()
    
    # Check for required fields
    if not self.config.auth_config.get("api_key"):
        raise ConfigurationError(
            "API key is required for YourPlatform",
            platform=self.platform_name,
            missing_fields=["api_key"],
            help_text="Get your API key from: https://yourplatform.com/settings/api"
        )
    
    # Validate URL format if provided
    api_url = self.config.auth_config.get("api_url")
    if api_url and not api_url.startswith(("http://", "https://")):
        raise ConfigurationError(
            "Invalid API URL format",
            platform=self.platform_name,
            details="URL must start with http:// or https://"
        )
```

## Testing Your Adapter

### Unit Tests

Create `tests/unit/sync/test_yourplatform_adapter.py`:

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from ai_trackdown_pytools.utils.sync import YourPlatformAdapter
from ai_trackdown_pytools.utils.sync.base import SyncConfig
from ai_trackdown_pytools.core.models import TaskModel, TaskStatus, Priority


class TestYourPlatformAdapter:
    """Test YourPlatform adapter implementation."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SyncConfig(
            platform="yourplatform",
            auth_config={
                "api_key": "test-key",
                "workspace_id": "12345"
            }
        )
    
    @pytest.fixture
    def adapter(self, config):
        """Create adapter instance."""
        return YourPlatformAdapter(config)
    
    def test_platform_name(self, adapter):
        """Test platform name property."""
        assert adapter.platform_name == "yourplatform"
    
    def test_supported_types(self, adapter):
        """Test supported types property."""
        assert adapter.supported_types == {"task", "issue", "bug"}
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self, adapter):
        """Test successful authentication."""
        with patch.object(adapter, "_client") as mock_client:
            mock_client.verify_credentials = AsyncMock()
            
            await adapter.authenticate()
            
            assert adapter._authenticated is True
            mock_client.verify_credentials.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_map_to_platform(self, adapter):
        """Test mapping to platform format."""
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            description="Test Description",
            status=TaskStatus.IN_PROGRESS,
            priority=Priority.HIGH,
            tags=["feature", "backend"],
            assignees=["user@example.com"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        platform_data = adapter._map_to_platform(task)
        
        assert platform_data["title"] == "Test Task"
        assert platform_data["description"] == "Test Description"
        assert platform_data["status"] == "in_progress"
        assert platform_data["priority"] == "high"
        assert platform_data["labels"] == ["feature", "backend"]
```

### Integration Tests

Create `tests/integration/sync/test_yourplatform_integration.py`:

```python
import pytest
from datetime import datetime

from ai_trackdown_pytools.utils.sync import YourPlatformAdapter
from ai_trackdown_pytools.utils.sync.base import SyncConfig
from ai_trackdown_pytools.core.models import TaskModel


@pytest.mark.integration
class TestYourPlatformIntegration:
    """Integration tests for YourPlatform adapter."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration with real credentials."""
        return SyncConfig(
            platform="yourplatform",
            auth_config={
                "api_key": os.getenv("YOURPLATFORM_TEST_API_KEY"),
                "workspace_id": os.getenv("YOURPLATFORM_TEST_WORKSPACE_ID")
            }
        )
    
    @pytest.mark.skipif(
        not os.getenv("YOURPLATFORM_TEST_API_KEY"),
        reason="YourPlatform test credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_full_sync_cycle(self, config):
        """Test complete sync cycle."""
        adapter = YourPlatformAdapter(config)
        
        # Authenticate
        await adapter.authenticate()
        assert await adapter.test_connection()
        
        # Create test task
        test_task = TaskModel(
            id="TSK-TEST-001",
            title=f"Test Task {datetime.now().isoformat()}",
            description="Integration test task",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Push task
        mapping = await adapter.push_item(test_task)
        assert f"{adapter.platform_name}_id" in mapping
        
        # Pull and verify
        items = await adapter.pull_items()
        matching_items = [
            item for item in items
            if item.title == test_task.title
        ]
        assert len(matching_items) == 1
        
        # Clean up
        await adapter.delete_item(mapping[f"{adapter.platform_name}_id"])
```

### Manual Testing

Test your adapter using the CLI:

```bash
# Configure your adapter
aitrackdown sync config yourplatform --key api_key --value test-key
aitrackdown sync config yourplatform --key workspace_id --value 12345

# Test connection
aitrackdown sync platform yourplatform status

# Test pull
aitrackdown sync platform yourplatform pull --dry-run

# Test push
aitrackdown create "Test task for YourPlatform" --type task
aitrackdown sync platform yourplatform push --dry-run
```

## Performance Optimization

### 1. Batch Operations

Implement batch operations for better performance:

```python
async def push_items_batch(self, items: List[TicketModel]) -> List[Dict[str, Any]]:
    """Push multiple items in batch."""
    if not items:
        return []
    
    # Prepare batch data
    batch_data = [
        self._map_to_platform(item)
        for item in items[:self.config.batch_size]
    ]
    
    # Send batch request
    try:
        results = await self._client.create_batch(batch_data)
        
        # Map results back to items
        mappings = []
        for i, result in enumerate(results):
            mappings.append({
                f"{self.platform_name}_id": result["id"],
                f"{self.platform_name}_url": result["url"],
                "local_id": items[i].id
            })
        
        return mappings
        
    except Exception as e:
        # Fall back to individual pushes
        return await self._push_items_individually(items)
```

### 2. Caching

Implement caching for frequently accessed data:

```python
from functools import lru_cache
from typing import Dict

class YourPlatformAdapter(SyncAdapter):
    def __init__(self, config: SyncConfig):
        super().__init__(config)
        self._field_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
    
    @lru_cache(maxsize=128)
    async def _get_user_id(self, email: str) -> Optional[str]:
        """Get user ID from email with caching."""
        try:
            user = await self._client.get_user_by_email(email)
            return user["id"] if user else None
        except Exception:
            return None
    
    async def _map_assignees_to_platform(self, assignees: List[str]) -> List[str]:
        """Map assignee emails to platform user IDs."""
        user_ids = []
        
        for email in assignees:
            user_id = await self._get_user_id(email)
            if user_id:
                user_ids.append(user_id)
        
        return user_ids
```

### 3. Connection Pooling

Use connection pooling for better performance:

```python
async def _ensure_session(self) -> None:
    """Ensure HTTP session with connection pooling."""
    if not self._session:
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool size
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache timeout
        )
        
        timeout = aiohttp.ClientTimeout(
            total=self.config.timeout,
            connect=5,
            sock_read=30
        )
        
        self._session = aiohttp.ClientSession(
            connector=connector,
            headers=self._headers,
            timeout=timeout
        )
```

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging

logger = logging.getLogger(__name__)

class YourPlatformAdapter(SyncAdapter):
    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        """Push item with debug logging."""
        logger.debug(f"Pushing item {item.id} to {self.platform_name}")
        logger.debug(f"Item data: {item.dict()}")
        
        try:
            platform_data = self._map_to_platform(item)
            logger.debug(f"Mapped data: {platform_data}")
            
            result = await self._client.create_item(platform_data)
            logger.debug(f"Platform response: {result}")
            
            return self._extract_mapping(result)
            
        except Exception as e:
            logger.error(f"Failed to push item {item.id}: {str(e)}", exc_info=True)
            raise
```

### 2. Request/Response Inspection

```python
async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
    """Make HTTP request with inspection."""
    url = f"{self.base_url}{endpoint}"
    
    if self.config.debug:
        print(f"\n[DEBUG] {method} {url}")
        print(f"[DEBUG] Headers: {self._headers}")
        if "json" in kwargs:
            print(f"[DEBUG] Body: {kwargs['json']}")
    
    async with self._session.request(method, url, **kwargs) as response:
        text = await response.text()
        
        if self.config.debug:
            print(f"[DEBUG] Status: {response.status}")
            print(f"[DEBUG] Response: {text[:500]}...")
        
        response.raise_for_status()
        return await response.json()
```

### 3. Dry Run Implementation

```python
async def push_item(self, item: TicketModel) -> Dict[str, Any]:
    """Push item with dry run support."""
    if self.config.dry_run:
        # Simulate push without making API call
        logger.info(f"[DRY RUN] Would push item: {item.id}")
        logger.info(f"[DRY RUN] Title: {item.title}")
        logger.info(f"[DRY RUN] Type: {type(item).__name__}")
        
        # Return simulated mapping
        return {
            f"{self.platform_name}_id": f"dry-run-{item.id}",
            f"{self.platform_name}_url": f"https://{self.platform_name}.com/dry-run",
            "dry_run": True
        }
    
    # Actual push logic
    return await self._do_push(item)
```

## Common Pitfalls and Solutions

### 1. Timezone Handling

Always handle timezones consistently:

```python
from datetime import timezone

def _parse_datetime(self, dt_string: str) -> datetime:
    """Parse datetime string to aware datetime."""
    # Parse ISO format
    dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    
    # Ensure timezone aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt

def _format_datetime(self, dt: datetime) -> str:
    """Format datetime for platform API."""
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    return dt.isoformat().replace("+00:00", "Z")
```

### 2. ID Collision Prevention

Prevent ID collisions between platforms:

```python
def _generate_local_id(self, platform_id: str, item_type: str) -> str:
    """Generate unique local ID from platform ID."""
    # Include platform prefix to prevent collisions
    type_prefix = {
        "task": "TSK",
        "issue": "ISS",
        "bug": "BUG",
        "epic": "EPC",
    }.get(item_type, "ITM")
    
    # Format: TYPE-PLATFORM-ID
    return f"{type_prefix}-{self.platform_name.upper()[:3]}-{platform_id}"
```

### 3. Partial Sync Failures

Handle partial failures gracefully:

```python
async def push_items_batch(self, items: List[TicketModel]) -> SyncResult:
    """Push items with partial failure handling."""
    result = SyncResult(
        platform=self.platform_name,
        direction=SyncDirection.PUSH,
        started_at=datetime.now()
    )
    
    for item in items:
        try:
            mapping = await self.push_item(item)
            result.created_ids.append((item.id, mapping[f"{self.platform_name}_id"]))
            result.items_created += 1
            
        except RateLimitError as e:
            # Stop on rate limit
            result.add_error(item.id, e)
            raise
            
        except ValidationError as e:
            # Skip invalid items
            result.add_error(item.id, e)
            result.items_skipped += 1
            continue
            
        except Exception as e:
            # Log unexpected errors
            result.add_error(item.id, e)
            result.items_failed += 1
            
            # Continue with remaining items
            if not self.config.fail_fast:
                continue
            else:
                raise
    
    result.completed_at = datetime.now()
    return result
```

## Publishing Your Adapter

### 1. Documentation

Create comprehensive documentation:

```markdown
# YourPlatform Sync Adapter

## Installation

```bash
pip install aitrackdown-yourplatform-adapter
```

## Configuration

1. Get your API key from [YourPlatform Settings](https://yourplatform.com/settings/api)
2. Find your workspace ID in the URL: `https://yourplatform.com/w/12345`
3. Configure the adapter:

```bash
aitrackdown sync config yourplatform --key api_key --value your-key
aitrackdown sync config yourplatform --key workspace_id --value 12345
```

## Usage

[Include examples and common workflows]

## Troubleshooting

[Common issues and solutions]
```

### 2. Package Structure

If distributing separately:

```
aitrackdown-yourplatform-adapter/
├── src/
│   └── aitrackdown_yourplatform/
│       ├── __init__.py
│       ├── adapter.py
│       └── client.py
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
├── pyproject.toml
├── README.md
└── LICENSE
```

### 3. Entry Point

Register via entry points in `pyproject.toml`:

```toml
[project.entry-points."aitrackdown.sync_adapters"]
yourplatform = "aitrackdown_yourplatform:YourPlatformAdapter"
```

## Support and Community

- Review existing adapters for examples
- Ask questions in discussions
- Submit PRs for improvements
- Share your adapter with the community

## Checklist for New Adapters

- [ ] Implement all required abstract methods
- [ ] Add comprehensive error handling
- [ ] Include status and priority mapping
- [ ] Support dry run mode
- [ ] Handle rate limiting
- [ ] Implement proper session management
- [ ] Add configuration validation
- [ ] Write unit tests (80% coverage minimum)
- [ ] Write integration tests
- [ ] Document configuration requirements
- [ ] Add platform to configuration help
- [ ] Test with real platform data
- [ ] Handle edge cases (empty data, special characters)
- [ ] Implement efficient batch operations
- [ ] Add debug logging
- [ ] Document platform-specific features
- [ ] Create user documentation
- [ ] Add examples

Your adapter is ready when all items are checked!