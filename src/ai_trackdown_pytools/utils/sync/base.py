"""Base classes for sync adapter system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ai_trackdown_pytools.core.models import (
    TicketModel,
)
from ai_trackdown_pytools.utils.sync.exceptions import ConfigurationError


class SyncDirection(str, Enum):
    """Sync direction enumeration.

    WHY: Explicitly defining sync directions prevents errors and makes the code
    more self-documenting. Using string enum for JSON serialization compatibility.
    """

    PULL = "pull"  # From external platform to local
    PUSH = "push"  # From local to external platform
    BIDIRECTIONAL = "bidirectional"  # Both directions


@dataclass
class SyncConfig:
    """Configuration for sync operations.

    WHY: Dataclass provides a clean, type-safe way to pass configuration around.
    This consolidates all sync settings in one place, making it easier to extend
    and validate configurations.
    """

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
    included_types: Optional[Set[str]] = None  # None means all types
    excluded_types: Optional[Set[str]] = None
    label_mapping: Dict[str, str] = field(default_factory=dict)
    status_mapping: Dict[str, str] = field(default_factory=dict)

    # Performance
    batch_size: int = 50
    max_retries: int = 3
    timeout: int = 30  # seconds

    # Advanced options
    preserve_ids: bool = False
    conflict_resolution: str = "remote_wins"  # remote_wins, local_wins, newest_wins

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.included_types and self.excluded_types:
            overlap = self.included_types & self.excluded_types
            if overlap:
                raise ValueError(
                    f"Types cannot be both included and excluded: {overlap}"
                )


@dataclass
class SyncResult:
    """Result of a sync operation.

    WHY: Structured result object makes it easy to report sync outcomes and
    handle partial failures. This pattern allows for detailed logging and
    user feedback.
    """

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
    created_ids: List[Tuple[str, str]] = field(
        default_factory=list
    )  # (local_id, remote_id)
    updated_ids: List[Tuple[str, str]] = field(default_factory=list)
    deleted_ids: List[str] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if sync completed successfully."""
        return self.completed_at is not None and self.items_failed == 0

    @property
    def duration(self) -> Optional[float]:
        """Calculate sync duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def add_error(
        self, item_id: str, error: Exception, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an error to the result."""
        self.items_failed += 1
        self.errors.append(
            {
                "item_id": item_id,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {},
                "timestamp": datetime.now().isoformat(),
            }
        )


class SyncAdapter(ABC):
    """Abstract base class for sync adapters.

    WHY: Abstract base class enforces a consistent interface across all platform
    adapters, making it easy to add new platforms and ensuring all adapters
    implement required functionality.

    DESIGN DECISION: Using ABC instead of Protocol because we want to share
    common functionality and enforce method implementation at instantiation time.
    """

    def __init__(self, config: SyncConfig):
        """Initialize adapter with configuration.

        Args:
            config: Sync configuration
        """
        self.config = config
        self._authenticated = False
        self._connection = None

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Get the platform name for this adapter."""
        pass

    @property
    @abstractmethod
    def supported_types(self) -> Set[str]:
        """Get the set of ticket types supported by this platform."""
        pass

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the external platform.

        WHY: Async method allows for non-blocking API calls. Authentication is
        separate from initialization to allow for lazy connection and better
        error handling.

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the external platform.

        Returns:
            True if connection is successful

        Raises:
            ConnectionError: If connection test fails
        """
        pass

    @abstractmethod
    async def pull_items(self, since: Optional[datetime] = None) -> List[TicketModel]:
        """Pull items from the external platform.

        WHY: Returns our internal models to maintain consistency. The adapter
        handles all translation between external and internal formats.

        Args:
            since: Only pull items updated after this timestamp

        Returns:
            List of items in internal format

        Raises:
            SyncError: If pull operation fails
        """
        pass

    @abstractmethod
    async def push_item(self, item: TicketModel) -> Dict[str, Any]:
        """Push a single item to the external platform.

        WHY: Single item push allows for fine-grained error handling and
        progress reporting. Returns mapping info for tracking relationships.

        Args:
            item: Item to push in internal format

        Returns:
            Mapping information (e.g., {"remote_id": "123", "remote_url": "..."})

        Raises:
            SyncError: If push operation fails
        """
        pass

    @abstractmethod
    async def update_item(self, item: TicketModel, remote_id: str) -> Dict[str, Any]:
        """Update an existing item on the external platform.

        Args:
            item: Updated item in internal format
            remote_id: ID of the item on the external platform

        Returns:
            Updated mapping information

        Raises:
            SyncError: If update operation fails
        """
        pass

    @abstractmethod
    async def delete_item(self, remote_id: str) -> None:
        """Delete an item from the external platform.

        Args:
            remote_id: ID of the item to delete

        Raises:
            SyncError: If delete operation fails
        """
        pass

    @abstractmethod
    async def get_item(self, remote_id: str) -> Optional[TicketModel]:
        """Get a single item from the external platform.

        Args:
            remote_id: ID of the item to retrieve

        Returns:
            Item in internal format or None if not found

        Raises:
            SyncError: If retrieval fails
        """
        pass

    # Common functionality that can be overridden

    def validate_config(self) -> None:
        """Validate adapter configuration.

        WHY: Each adapter can have specific configuration requirements.
        This method allows adapters to validate their config early.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self.config.auth_config:
            raise ConfigurationError(
                "No authentication configuration provided", platform=self.platform_name
            )

    def map_status(self, status: str, to_external: bool = True) -> str:
        """Map status between internal and external formats.

        WHY: Status names often differ between platforms. This provides
        a common place for status translation logic.

        Args:
            status: Status to map
            to_external: If True, map from internal to external

        Returns:
            Mapped status
        """
        if to_external and self.config.status_mapping:
            return self.config.status_mapping.get(status, status)
        elif not to_external and self.config.status_mapping:
            # Reverse mapping
            reverse_map = {v: k for k, v in self.config.status_mapping.items()}
            return reverse_map.get(status, status)
        return status

    def map_labels(self, labels: List[str], to_external: bool = True) -> List[str]:
        """Map labels between internal and external formats.

        Args:
            labels: Labels to map
            to_external: If True, map from internal to external

        Returns:
            Mapped labels
        """
        if not self.config.label_mapping:
            return labels

        mapping = self.config.label_mapping
        if not to_external:
            # Reverse mapping
            mapping = {v: k for k, v in mapping.items()}

        return [mapping.get(label, label) for label in labels]

    def filter_item_type(self, item_type: str) -> bool:
        """Check if an item type should be synced.

        Args:
            item_type: Type to check

        Returns:
            True if the type should be synced
        """
        if self.config.included_types:
            return item_type in self.config.included_types
        if self.config.excluded_types:
            return item_type not in self.config.excluded_types
        return True

    async def close(self) -> None:
        """Close any open connections.

        WHY: Cleanup method ensures resources are properly released.
        Default implementation does nothing but can be overridden.
        """
        pass
