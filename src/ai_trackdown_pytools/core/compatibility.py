"""Backward compatibility layer for status enums.

This module provides compatibility between the old individual status enums
and the new unified status system.

WHY: Existing code and data may still use the old status enums. This adapter
ensures smooth migration without breaking existing functionality.
"""

from enum import Enum
from typing import Type, Union

from .models import (
    BugStatus,
    EpicStatus,
    IssueStatus,
    ProjectStatus,
    PRStatus,
    TaskStatus,
)
from .workflow import UnifiedStatus, map_legacy_status

# Type alias for all legacy status types
LegacyStatusType = Union[
    TaskStatus,
    EpicStatus,
    IssueStatus,
    BugStatus,
    PRStatus,
    ProjectStatus,
]


def convert_to_unified_status(
    status: Union[str, LegacyStatusType, UnifiedStatus],
) -> UnifiedStatus:
    """Convert any status type to UnifiedStatus.

    WHY: Provides a single entry point for status conversion, handling all
    possible input types (strings, legacy enums, unified enums).

    Args:
        status: Status value in any format

    Returns:
        UnifiedStatus enum value
    """
    # Already unified
    if isinstance(status, UnifiedStatus):
        return status

    # String value
    if isinstance(status, str):
        return map_legacy_status(status)

    # Legacy enum
    if isinstance(status, Enum):
        return map_legacy_status(status.value)

    # Default to OPEN for unknown types
    return UnifiedStatus.OPEN


def is_compatible_status(
    status: Union[str, LegacyStatusType, UnifiedStatus], ticket_type: str
) -> bool:
    """Check if a status is valid for a given ticket type.

    WHY: Different ticket types historically had different valid statuses.
    This function ensures that status transitions respect those constraints.

    Args:
        status: Status to check
        ticket_type: Type of ticket (task, epic, issue, bug, pr, project)

    Returns:
        True if status is valid for ticket type
    """
    unified_status = convert_to_unified_status(status)

    # Define valid statuses for each ticket type
    valid_statuses = {
        "task": {
            UnifiedStatus.OPEN,
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.COMPLETED,
            UnifiedStatus.CANCELLED,
            UnifiedStatus.BLOCKED,
            UnifiedStatus.TODO,
            UnifiedStatus.DONE,
        },
        "epic": {
            UnifiedStatus.PLANNING,
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.ON_HOLD,
            UnifiedStatus.COMPLETED,
            UnifiedStatus.CANCELLED,
            UnifiedStatus.ACTIVE,
        },
        "issue": {
            UnifiedStatus.OPEN,
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.TESTING,
            UnifiedStatus.COMPLETED,
            UnifiedStatus.CANCELLED,
            UnifiedStatus.BLOCKED,
            UnifiedStatus.RESOLVED,
            UnifiedStatus.CLOSED,
        },
        "bug": {
            UnifiedStatus.OPEN,
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.TESTING,
            UnifiedStatus.COMPLETED,
            UnifiedStatus.CANCELLED,
            UnifiedStatus.BLOCKED,
            UnifiedStatus.CLOSED,
            UnifiedStatus.RESOLVED,
        },
        "pr": {
            UnifiedStatus.DRAFT,
            UnifiedStatus.READY_FOR_REVIEW,
            UnifiedStatus.IN_REVIEW,
            UnifiedStatus.CHANGES_REQUESTED,
            UnifiedStatus.APPROVED,
            UnifiedStatus.MERGED,
            UnifiedStatus.CLOSED,
            UnifiedStatus.OPEN,
        },
        "project": {
            UnifiedStatus.PLANNING,
            UnifiedStatus.ACTIVE,
            UnifiedStatus.ON_HOLD,
            UnifiedStatus.COMPLETED,
            UnifiedStatus.CANCELLED,
            UnifiedStatus.ARCHIVED,
        },
    }

    return unified_status in valid_statuses.get(ticket_type.lower(), set())


def get_legacy_status_enum(ticket_type: str) -> Type[Enum]:
    """Get the legacy status enum class for a ticket type.

    WHY: Some existing code may need to work with the legacy enum types
    directly for serialization or validation purposes.

    Args:
        ticket_type: Type of ticket

    Returns:
        Legacy status enum class
    """
    enum_map = {
        "task": TaskStatus,
        "epic": EpicStatus,
        "issue": IssueStatus,
        "bug": BugStatus,
        "pr": PRStatus,
        "project": ProjectStatus,
    }

    return enum_map.get(ticket_type.lower())


def convert_to_legacy_status(
    unified_status: UnifiedStatus, ticket_type: str
) -> Union[LegacyStatusType, None]:
    """Convert UnifiedStatus back to legacy status enum.

    WHY: For backward compatibility with systems that expect the old enum types.
    This is primarily for serialization and external API compatibility.

    Args:
        unified_status: Unified status value
        ticket_type: Type of ticket

    Returns:
        Legacy status enum value or None if not mappable
    """
    legacy_enum = get_legacy_status_enum(ticket_type)
    if not legacy_enum:
        return None

    # Try direct conversion
    try:
        return legacy_enum(unified_status.value)
    except ValueError:
        # Handle special mappings
        special_mappings = {
            "task": {
                UnifiedStatus.TODO: TaskStatus.OPEN,
                UnifiedStatus.DONE: TaskStatus.COMPLETED,
                UnifiedStatus.CLOSED: TaskStatus.COMPLETED,
                UnifiedStatus.RESOLVED: TaskStatus.COMPLETED,
            },
            "epic": {
                UnifiedStatus.ACTIVE: EpicStatus.IN_PROGRESS,
                UnifiedStatus.CLOSED: EpicStatus.COMPLETED,
                UnifiedStatus.RESOLVED: EpicStatus.COMPLETED,
            },
            "issue": {
                UnifiedStatus.RESOLVED: IssueStatus.COMPLETED,
                UnifiedStatus.DONE: IssueStatus.COMPLETED,
            },
            "pr": {
                UnifiedStatus.OPEN: PRStatus.DRAFT,
                UnifiedStatus.IN_PROGRESS: PRStatus.IN_REVIEW,
                UnifiedStatus.COMPLETED: PRStatus.MERGED,
                UnifiedStatus.CANCELLED: PRStatus.CLOSED,
            },
            "project": {
                UnifiedStatus.IN_PROGRESS: ProjectStatus.ACTIVE,
                UnifiedStatus.CLOSED: ProjectStatus.COMPLETED,
                UnifiedStatus.RESOLVED: ProjectStatus.COMPLETED,
            },
        }

        mappings = special_mappings.get(ticket_type.lower(), {})
        if unified_status in mappings:
            return mappings[unified_status]

        # Default to first valid status
        return list(legacy_enum)[0]
