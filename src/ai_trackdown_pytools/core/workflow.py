"""Workflow management for ticket status and resolution tracking.

This module implements a unified state and resolution system that provides:
- Consistent status and resolution enums across all ticket types
- State transition validation logic
- Workflow state machine enforcement
- Resolution tracking for terminal states

WHY: The previous implementation had separate status enums for each ticket type,
leading to inconsistency and complexity. This unified approach:
- Provides a single source of truth for status states
- Enables resolution tracking for better metrics
- Enforces valid state transitions through a state machine
- Maintains backward compatibility with existing code
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class UnifiedStatus(str, Enum):
    """Unified status enumeration for all ticket types.

    WHY: Having a single status enum ensures consistency across ticket types
    and simplifies state transition logic. Categories help group related states.
    """

    # Initial states - tickets that haven't been started
    OPEN = "open"  # Default for new tickets
    NEW = "new"  # Alternative to open
    TODO = "todo"  # Planning/backlog state

    # Active states - work is in progress
    IN_PROGRESS = "in_progress"  # Actively being worked on
    IN_REVIEW = "in_review"  # Under review (PRs, code)
    TESTING = "testing"  # In testing phase
    REOPENED = "reopened"  # Previously closed, now active again
    ESCALATED = "escalated"  # Requires urgent attention

    # Waiting states - blocked or paused
    PENDING = "pending"  # Waiting for external input
    ON_HOLD = "on_hold"  # Temporarily suspended
    BLOCKED = "blocked"  # Cannot proceed due to dependencies
    WAITING = "waiting"  # General waiting state

    # Terminal states - no more work expected
    COMPLETED = "completed"  # Successfully finished
    RESOLVED = "resolved"  # Issue addressed (requires resolution)
    CLOSED = "closed"  # Finalized (requires resolution)
    CANCELLED = "cancelled"  # Abandoned (requires resolution)
    MERGED = "merged"  # PR specific terminal state
    DONE = "done"  # Alternative to completed

    # Special states for specific workflows
    DRAFT = "draft"  # PR specific initial state
    READY_FOR_REVIEW = "ready_for_review"  # PR ready state
    CHANGES_REQUESTED = "changes_requested"  # PR feedback state
    APPROVED = "approved"  # PR approved state
    PLANNING = "planning"  # Epic/Project planning phase
    ACTIVE = "active"  # Epic/Project active phase
    ARCHIVED = "archived"  # Long-term storage state


class ResolutionType(str, Enum):
    """Resolution types for terminal states.

    WHY: Tracking resolution provides valuable metrics on why tickets close.
    Categories help analyze success rates and identify patterns.
    """

    # Successful resolutions - goals achieved
    FIXED = "fixed"  # Bug was fixed, issue resolved
    COMPLETED = "completed"  # Work finished successfully
    DELIVERED = "delivered"  # Feature/functionality delivered
    IMPLEMENTED = "implemented"  # Implementation complete
    DOCUMENTED = "documented"  # Resolved via documentation
    CONFIGURED = "configured"  # Resolved via configuration
    WORKAROUND = "workaround"  # Alternative solution provided

    # Unsuccessful resolutions - goals not achieved
    WONT_FIX = "wont_fix"  # Deliberate decision not to fix
    INCOMPLETE = "incomplete"  # Cannot complete due to missing info
    ABANDONED = "abandoned"  # Work stopped without completion
    TIMEOUT = "timeout"  # Exceeded time limits
    NO_RESPONSE = "no_response"  # No response from reporter

    # Invalid resolutions - not actual issues
    DUPLICATE = "duplicate"  # Duplicate of another ticket
    INVALID = "invalid"  # Not a valid issue/request
    CANNOT_REPRODUCE = "cannot_reproduce"  # Issue not reproducible
    WORKS_AS_DESIGNED = "works_as_designed"  # Not a bug
    USER_ERROR = "user_error"  # User mistake, not system issue
    OUT_OF_SCOPE = "out_of_scope"  # Outside project scope

    # Deferred resolutions - postponed
    DEFERRED = "deferred"  # Postponed to future
    MOVED = "moved"  # Moved to different project/system
    BACKLOG = "backlog"  # Moved to backlog


class StatusCategory(str, Enum):
    """Categories for grouping status states."""

    INITIAL = "initial"  # Starting states
    ACTIVE = "active"  # Work in progress
    WAITING = "waiting"  # Blocked or paused
    TERMINAL = "terminal"  # End states


class ResolutionCategory(str, Enum):
    """Categories for grouping resolution types."""

    SUCCESSFUL = "successful"  # Goals achieved
    UNSUCCESSFUL = "unsuccessful"  # Goals not achieved
    INVALID = "invalid"  # Not actual issues
    DEFERRED = "deferred"  # Postponed


# Status metadata mapping
STATUS_METADATA = {
    UnifiedStatus.OPEN: {
        "category": StatusCategory.INITIAL,
        "description": "Ticket created but not started",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.NEW: {
        "category": StatusCategory.INITIAL,
        "description": "Newly created ticket",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.TODO: {
        "category": StatusCategory.INITIAL,
        "description": "In planning/backlog",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.IN_PROGRESS: {
        "category": StatusCategory.ACTIVE,
        "description": "Actively being worked on",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.IN_REVIEW: {
        "category": StatusCategory.ACTIVE,
        "description": "Under review",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.TESTING: {
        "category": StatusCategory.ACTIVE,
        "description": "In testing phase",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.REOPENED: {
        "category": StatusCategory.ACTIVE,
        "description": "Previously closed, now active",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.ESCALATED: {
        "category": StatusCategory.ACTIVE,
        "description": "Requires urgent attention",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.PENDING: {
        "category": StatusCategory.WAITING,
        "description": "Waiting for external input",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.ON_HOLD: {
        "category": StatusCategory.WAITING,
        "description": "Temporarily suspended",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.BLOCKED: {
        "category": StatusCategory.WAITING,
        "description": "Cannot proceed due to blockers",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.WAITING: {
        "category": StatusCategory.WAITING,
        "description": "General waiting state",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.COMPLETED: {
        "category": StatusCategory.TERMINAL,
        "description": "Successfully finished",
        "is_terminal": True,
        "requires_resolution": False,  # Resolution optional
    },
    UnifiedStatus.RESOLVED: {
        "category": StatusCategory.TERMINAL,
        "description": "Issue addressed",
        "is_terminal": True,
        "requires_resolution": True,
    },
    UnifiedStatus.CLOSED: {
        "category": StatusCategory.TERMINAL,
        "description": "Finalized",
        "is_terminal": True,
        "requires_resolution": True,
    },
    UnifiedStatus.CANCELLED: {
        "category": StatusCategory.TERMINAL,
        "description": "Abandoned",
        "is_terminal": True,
        "requires_resolution": True,
    },
    UnifiedStatus.MERGED: {
        "category": StatusCategory.TERMINAL,
        "description": "PR merged",
        "is_terminal": True,
        "requires_resolution": False,
    },
    UnifiedStatus.DONE: {
        "category": StatusCategory.TERMINAL,
        "description": "Work done",
        "is_terminal": True,
        "requires_resolution": False,
    },
    UnifiedStatus.DRAFT: {
        "category": StatusCategory.INITIAL,
        "description": "PR in draft state",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.READY_FOR_REVIEW: {
        "category": StatusCategory.ACTIVE,
        "description": "PR ready for review",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.CHANGES_REQUESTED: {
        "category": StatusCategory.WAITING,
        "description": "PR needs changes",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.APPROVED: {
        "category": StatusCategory.ACTIVE,
        "description": "PR approved",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.PLANNING: {
        "category": StatusCategory.INITIAL,
        "description": "In planning phase",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.ACTIVE: {
        "category": StatusCategory.ACTIVE,
        "description": "Actively running",
        "is_terminal": False,
        "requires_resolution": False,
    },
    UnifiedStatus.ARCHIVED: {
        "category": StatusCategory.TERMINAL,
        "description": "Archived for reference",
        "is_terminal": True,
        "requires_resolution": False,
    },
}


# Resolution metadata mapping
RESOLUTION_METADATA = {
    ResolutionType.FIXED: {
        "category": ResolutionCategory.SUCCESSFUL,
        "description": "Issue was fixed",
        "requires_comment": False,
    },
    ResolutionType.COMPLETED: {
        "category": ResolutionCategory.SUCCESSFUL,
        "description": "Work completed successfully",
        "requires_comment": False,
    },
    ResolutionType.DELIVERED: {
        "category": ResolutionCategory.SUCCESSFUL,
        "description": "Feature/functionality delivered",
        "requires_comment": False,
    },
    ResolutionType.IMPLEMENTED: {
        "category": ResolutionCategory.SUCCESSFUL,
        "description": "Implementation complete",
        "requires_comment": False,
    },
    ResolutionType.DOCUMENTED: {
        "category": ResolutionCategory.SUCCESSFUL,
        "description": "Resolved via documentation",
        "requires_comment": False,
    },
    ResolutionType.CONFIGURED: {
        "category": ResolutionCategory.SUCCESSFUL,
        "description": "Resolved via configuration",
        "requires_comment": False,
    },
    ResolutionType.WORKAROUND: {
        "category": ResolutionCategory.SUCCESSFUL,
        "description": "Alternative solution provided",
        "requires_comment": True,
    },
    ResolutionType.WONT_FIX: {
        "category": ResolutionCategory.UNSUCCESSFUL,
        "description": "Will not be fixed",
        "requires_comment": True,
    },
    ResolutionType.INCOMPLETE: {
        "category": ResolutionCategory.UNSUCCESSFUL,
        "description": "Cannot complete",
        "requires_comment": True,
    },
    ResolutionType.ABANDONED: {
        "category": ResolutionCategory.UNSUCCESSFUL,
        "description": "Work abandoned",
        "requires_comment": True,
    },
    ResolutionType.TIMEOUT: {
        "category": ResolutionCategory.UNSUCCESSFUL,
        "description": "Exceeded time limits",
        "requires_comment": False,
    },
    ResolutionType.NO_RESPONSE: {
        "category": ResolutionCategory.UNSUCCESSFUL,
        "description": "No response received",
        "requires_comment": False,
    },
    ResolutionType.DUPLICATE: {
        "category": ResolutionCategory.INVALID,
        "description": "Duplicate of another ticket",
        "requires_comment": True,
    },
    ResolutionType.INVALID: {
        "category": ResolutionCategory.INVALID,
        "description": "Not a valid issue",
        "requires_comment": True,
    },
    ResolutionType.CANNOT_REPRODUCE: {
        "category": ResolutionCategory.INVALID,
        "description": "Cannot reproduce issue",
        "requires_comment": True,
    },
    ResolutionType.WORKS_AS_DESIGNED: {
        "category": ResolutionCategory.INVALID,
        "description": "Working as intended",
        "requires_comment": False,
    },
    ResolutionType.USER_ERROR: {
        "category": ResolutionCategory.INVALID,
        "description": "User mistake",
        "requires_comment": True,
    },
    ResolutionType.OUT_OF_SCOPE: {
        "category": ResolutionCategory.INVALID,
        "description": "Outside project scope",
        "requires_comment": True,
    },
    ResolutionType.DEFERRED: {
        "category": ResolutionCategory.DEFERRED,
        "description": "Postponed to future",
        "requires_comment": True,
    },
    ResolutionType.MOVED: {
        "category": ResolutionCategory.DEFERRED,
        "description": "Moved elsewhere",
        "requires_comment": True,
    },
    ResolutionType.BACKLOG: {
        "category": ResolutionCategory.DEFERRED,
        "description": "Added to backlog",
        "requires_comment": False,
    },
}


class StateTransition(BaseModel):
    """Represents a valid state transition."""

    from_status: UnifiedStatus
    to_status: UnifiedStatus
    name: str
    description: Optional[str] = None
    required_fields: List[str] = Field(default_factory=list)
    requires_resolution: bool = False
    allowed_resolutions: List[ResolutionType] = Field(default_factory=list)


class WorkflowStateMachine:
    """State machine for enforcing workflow transitions.

    WHY: A state machine ensures only valid transitions occur and provides
    a centralized place to define workflow rules. This prevents invalid
    state changes and maintains data integrity.
    """

    def __init__(self):
        """Initialize the state machine with default transitions."""
        self.transitions: Dict[UnifiedStatus, List[StateTransition]] = {}
        self._initialize_default_transitions()

    def _initialize_default_transitions(self):
        """Set up default state transitions.

        WHY: These transitions represent common workflow patterns that work
        across different ticket types. Specific workflows can override these.
        """
        # From OPEN
        self.add_transition(
            UnifiedStatus.OPEN,
            UnifiedStatus.IN_PROGRESS,
            "Start Work",
            "Begin working on ticket",
        )
        self.add_transition(
            UnifiedStatus.OPEN,
            UnifiedStatus.CANCELLED,
            "Cancel",
            "Cancel without starting",
            requires_resolution=True,
            allowed_resolutions=[
                ResolutionType.DUPLICATE,
                ResolutionType.INVALID,
                ResolutionType.WONT_FIX,
                ResolutionType.OUT_OF_SCOPE,
            ],
        )
        self.add_transition(
            UnifiedStatus.OPEN, UnifiedStatus.BLOCKED, "Block", "Mark as blocked"
        )

        # From IN_PROGRESS
        self.add_transition(
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.TESTING,
            "Send to Testing",
            "Move to testing phase",
        )
        self.add_transition(
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.IN_REVIEW,
            "Request Review",
            "Submit for review",
        )
        self.add_transition(
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.COMPLETED,
            "Complete",
            "Mark as complete",
        )
        self.add_transition(
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.RESOLVED,
            "Resolve",
            "Resolve with reason",
            requires_resolution=True,
            allowed_resolutions=[
                ResolutionType.FIXED,
                ResolutionType.IMPLEMENTED,
                ResolutionType.DOCUMENTED,
                ResolutionType.CONFIGURED,
                ResolutionType.WORKAROUND,
            ],
        )
        self.add_transition(
            UnifiedStatus.IN_PROGRESS, UnifiedStatus.BLOCKED, "Block", "Mark as blocked"
        )
        self.add_transition(
            UnifiedStatus.IN_PROGRESS,
            UnifiedStatus.ON_HOLD,
            "Put on Hold",
            "Temporarily suspend",
        )

        # From TESTING
        self.add_transition(
            UnifiedStatus.TESTING,
            UnifiedStatus.IN_PROGRESS,
            "Return to Development",
            "Failed testing",
        )
        self.add_transition(
            UnifiedStatus.TESTING,
            UnifiedStatus.COMPLETED,
            "Pass Testing",
            "Testing successful",
        )
        self.add_transition(
            UnifiedStatus.TESTING,
            UnifiedStatus.RESOLVED,
            "Resolve",
            "Resolve after testing",
            requires_resolution=True,
        )

        # From BLOCKED/ON_HOLD
        for waiting_status in [UnifiedStatus.BLOCKED, UnifiedStatus.ON_HOLD]:
            self.add_transition(
                waiting_status, UnifiedStatus.IN_PROGRESS, "Resume", "Resume work"
            )
            self.add_transition(
                waiting_status,
                UnifiedStatus.CANCELLED,
                "Cancel",
                "Cancel blocked work",
                requires_resolution=True,
            )

        # From terminal states
        for terminal in [
            UnifiedStatus.COMPLETED,
            UnifiedStatus.RESOLVED,
            UnifiedStatus.CLOSED,
        ]:
            self.add_transition(terminal, UnifiedStatus.CLOSED, "Close", "Close ticket")
            self.add_transition(
                terminal, UnifiedStatus.REOPENED, "Reopen", "Reopen for more work"
            )

        # From REOPENED
        self.add_transition(
            UnifiedStatus.REOPENED,
            UnifiedStatus.IN_PROGRESS,
            "Start Rework",
            "Begin rework",
        )

        # PR-specific transitions
        self.add_transition(
            UnifiedStatus.DRAFT,
            UnifiedStatus.READY_FOR_REVIEW,
            "Mark Ready",
            "Ready for review",
        )
        self.add_transition(
            UnifiedStatus.READY_FOR_REVIEW,
            UnifiedStatus.IN_REVIEW,
            "Start Review",
            "Begin review",
        )
        self.add_transition(
            UnifiedStatus.IN_REVIEW,
            UnifiedStatus.CHANGES_REQUESTED,
            "Request Changes",
            "Changes needed",
        )
        self.add_transition(
            UnifiedStatus.IN_REVIEW, UnifiedStatus.APPROVED, "Approve", "Approve PR"
        )
        self.add_transition(
            UnifiedStatus.APPROVED, UnifiedStatus.MERGED, "Merge", "Merge PR"
        )
        self.add_transition(
            UnifiedStatus.CHANGES_REQUESTED,
            UnifiedStatus.READY_FOR_REVIEW,
            "Resubmit",
            "Ready for re-review",
        )

    def add_transition(
        self,
        from_status: UnifiedStatus,
        to_status: UnifiedStatus,
        name: str,
        description: str = "",
        required_fields: List[str] = None,
        requires_resolution: bool = False,
        allowed_resolutions: List[ResolutionType] = None,
    ):
        """Add a valid state transition."""
        if from_status not in self.transitions:
            self.transitions[from_status] = []

        transition = StateTransition(
            from_status=from_status,
            to_status=to_status,
            name=name,
            description=description,
            required_fields=required_fields or [],
            requires_resolution=requires_resolution,
            allowed_resolutions=allowed_resolutions or [],
        )

        self.transitions[from_status].append(transition)

    def get_valid_transitions(
        self, current_status: UnifiedStatus
    ) -> List[StateTransition]:
        """Get all valid transitions from current status."""
        return self.transitions.get(current_status, [])

    def is_valid_transition(
        self, from_status: UnifiedStatus, to_status: UnifiedStatus
    ) -> bool:
        """Check if a transition is valid."""
        transitions = self.get_valid_transitions(from_status)
        return any(t.to_status == to_status for t in transitions)

    def get_transition(
        self, from_status: UnifiedStatus, to_status: UnifiedStatus
    ) -> Optional[StateTransition]:
        """Get specific transition details."""
        transitions = self.get_valid_transitions(from_status)
        for transition in transitions:
            if transition.to_status == to_status:
                return transition
        return None

    def validate_transition(
        self,
        from_status: UnifiedStatus,
        to_status: UnifiedStatus,
        resolution: Optional[ResolutionType] = None,
        fields: Optional[Dict[str, any]] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Validate a state transition with all requirements.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if transition exists
        transition = self.get_transition(from_status, to_status)
        if not transition:
            return False, f"Invalid transition from {from_status} to {to_status}"

        # Check resolution requirements
        if transition.requires_resolution and not resolution:
            return False, f"Resolution required for transition to {to_status}"

        if resolution and transition.allowed_resolutions:
            if resolution not in transition.allowed_resolutions:
                allowed = ", ".join(r.value for r in transition.allowed_resolutions)
                return False, f"Invalid resolution. Allowed: {allowed}"

        # Check required fields
        if transition.required_fields and fields:
            missing = [f for f in transition.required_fields if not fields.get(f)]
            if missing:
                return False, f"Missing required fields: {', '.join(missing)}"

        return True, None


# Create global state machine instance
workflow_state_machine = WorkflowStateMachine()


def get_status_category(status: UnifiedStatus) -> StatusCategory:
    """Get the category for a status."""
    return STATUS_METADATA[status]["category"]


def get_resolution_category(resolution: ResolutionType) -> ResolutionCategory:
    """Get the category for a resolution."""
    return RESOLUTION_METADATA[resolution]["category"]


def is_terminal_status(status: UnifiedStatus) -> bool:
    """Check if a status is terminal."""
    return STATUS_METADATA[status]["is_terminal"]


def requires_resolution(status: UnifiedStatus) -> bool:
    """Check if a status requires resolution."""
    return STATUS_METADATA[status]["requires_resolution"]


def resolution_requires_comment(resolution: ResolutionType) -> bool:
    """Check if a resolution requires a comment."""
    return RESOLUTION_METADATA[resolution]["requires_comment"]


# Backward compatibility mappings
# Maps old status values to new unified status
LEGACY_STATUS_MAPPING = {
    # TaskStatus
    "open": UnifiedStatus.OPEN,
    "in_progress": UnifiedStatus.IN_PROGRESS,
    "completed": UnifiedStatus.COMPLETED,
    "cancelled": UnifiedStatus.CANCELLED,
    "blocked": UnifiedStatus.BLOCKED,
    # EpicStatus
    "planning": UnifiedStatus.PLANNING,
    "on_hold": UnifiedStatus.ON_HOLD,
    # IssueStatus/BugStatus
    "testing": UnifiedStatus.TESTING,
    "closed": UnifiedStatus.CLOSED,
    # PRStatus
    "draft": UnifiedStatus.DRAFT,
    "ready_for_review": UnifiedStatus.READY_FOR_REVIEW,
    "in_review": UnifiedStatus.IN_REVIEW,
    "changes_requested": UnifiedStatus.CHANGES_REQUESTED,
    "approved": UnifiedStatus.APPROVED,
    "merged": UnifiedStatus.MERGED,
    # ProjectStatus
    "active": UnifiedStatus.ACTIVE,
    "archived": UnifiedStatus.ARCHIVED,
}


def map_legacy_status(old_status: str) -> UnifiedStatus:
    """Map old status values to unified status.

    WHY: This ensures backward compatibility when migrating existing data
    to the new unified status system.
    """
    # Try direct enum conversion first
    try:
        return UnifiedStatus(old_status)
    except ValueError:
        pass

    # Try legacy mapping
    if old_status in LEGACY_STATUS_MAPPING:
        return LEGACY_STATUS_MAPPING[old_status]

    # Default to OPEN for unknown statuses
    return UnifiedStatus.OPEN
