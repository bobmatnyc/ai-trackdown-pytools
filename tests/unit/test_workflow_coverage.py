"""Unit tests for workflow module to increase coverage."""


from ai_trackdown_pytools.core.workflow import (
    ResolutionCategory,
    ResolutionType,
    StateTransition,
    StatusCategory,
    UnifiedStatus,
    WorkflowStateMachine,
    get_resolution_category,
    get_status_category,
    is_terminal_status,
    map_legacy_status,
    requires_resolution,
    resolution_requires_comment,
)


class TestWorkflowCoverage:
    """Test cases to increase workflow coverage."""

    def test_workflow_state_machine_creation(self):
        """Test WorkflowStateMachine creation."""
        machine = WorkflowStateMachine()

        assert machine is not None
        assert hasattr(machine, "transitions")
        assert hasattr(machine, "resolution_requirements")

    def test_unified_status_enum(self):
        """Test UnifiedStatus enum."""
        # Test basic statuses
        assert UnifiedStatus.OPEN.value == "open"
        assert UnifiedStatus.IN_PROGRESS.value == "in_progress"
        assert UnifiedStatus.CLOSED.value == "closed"

        # Test ticket-specific statuses
        assert UnifiedStatus.DRAFT.value == "draft"
        assert UnifiedStatus.PLANNED.value == "planned"
        assert UnifiedStatus.ACTIVE.value == "active"

    def test_get_status_category(self):
        """Test status categorization."""
        assert get_status_category(UnifiedStatus.OPEN) == StatusCategory.TODO
        assert (
            get_status_category(UnifiedStatus.IN_PROGRESS) == StatusCategory.IN_PROGRESS
        )
        assert get_status_category(UnifiedStatus.CLOSED) == StatusCategory.DONE

    def test_is_terminal_status(self):
        """Test terminal status check."""
        assert is_terminal_status(UnifiedStatus.CLOSED) is True
        assert is_terminal_status(UnifiedStatus.DONE) is True
        assert is_terminal_status(UnifiedStatus.CANCELLED) is True
        assert is_terminal_status(UnifiedStatus.OPEN) is False
        assert is_terminal_status(UnifiedStatus.IN_PROGRESS) is False

    def test_requires_resolution(self):
        """Test resolution requirement check."""
        assert requires_resolution(UnifiedStatus.RESOLVED) is True
        assert requires_resolution(UnifiedStatus.CLOSED) is True
        assert requires_resolution(UnifiedStatus.OPEN) is False
        assert requires_resolution(UnifiedStatus.IN_PROGRESS) is False

    def test_resolution_requires_comment(self):
        """Test resolution comment requirement."""
        assert resolution_requires_comment(ResolutionType.WONT_FIX) is True
        assert resolution_requires_comment(ResolutionType.INVALID) is True
        assert resolution_requires_comment(ResolutionType.FIXED) is False
        assert resolution_requires_comment(ResolutionType.DONE) is False

    def test_state_transition(self):
        """Test StateTransition model."""
        transition = StateTransition(
            from_status=UnifiedStatus.OPEN,
            to_status=UnifiedStatus.IN_PROGRESS,
            allowed_ticket_types=["task", "issue"],
        )

        assert transition.from_status == UnifiedStatus.OPEN
        assert transition.to_status == UnifiedStatus.IN_PROGRESS
        assert "task" in transition.allowed_ticket_types

    def test_map_legacy_status(self):
        """Test legacy status mapping."""
        # Test common legacy statuses
        assert map_legacy_status("todo") == UnifiedStatus.OPEN
        assert map_legacy_status("doing") == UnifiedStatus.IN_PROGRESS
        assert map_legacy_status("done") == UnifiedStatus.CLOSED

        # Test exact matches
        assert map_legacy_status("open") == UnifiedStatus.OPEN
        assert map_legacy_status("closed") == UnifiedStatus.CLOSED

    def test_resolution_type_enum(self):
        """Test ResolutionType enum."""
        # Test issue resolutions
        assert ResolutionType.FIXED.value == "fixed"
        assert ResolutionType.WONT_FIX.value == "wont_fix"
        assert ResolutionType.DUPLICATE.value == "duplicate"
        assert ResolutionType.INVALID.value == "invalid"

        # Test epic resolutions
        assert ResolutionType.DELIVERED.value == "delivered"
        assert ResolutionType.PARTIALLY_DELIVERED.value == "partially_delivered"

    def test_get_resolution_category(self):
        """Test resolution categorization."""
        assert (
            get_resolution_category(ResolutionType.FIXED)
            == ResolutionCategory.COMPLETED
        )
        assert (
            get_resolution_category(ResolutionType.WONT_FIX)
            == ResolutionCategory.REJECTED
        )
        assert (
            get_resolution_category(ResolutionType.DUPLICATE)
            == ResolutionCategory.REJECTED
        )

    def test_workflow_state_machine_validate_transition(self):
        """Test WorkflowStateMachine transition validation."""
        machine = WorkflowStateMachine()

        # Valid transition
        result = machine.validate_transition(
            "task", UnifiedStatus.OPEN, UnifiedStatus.IN_PROGRESS
        )
        assert result.valid is True

    def test_workflow_state_machine_validate_resolution(self):
        """Test WorkflowStateMachine resolution validation."""
        machine = WorkflowStateMachine()

        # Valid resolution
        result = machine.validate_resolution(
            "issue", UnifiedStatus.RESOLVED, ResolutionType.FIXED
        )
        assert result.valid is True

    def test_status_category_enum(self):
        """Test StatusCategory enum."""
        assert StatusCategory.TODO.value == "todo"
        assert StatusCategory.IN_PROGRESS.value == "in_progress"
        assert StatusCategory.DONE.value == "done"

    def test_resolution_category_enum(self):
        """Test ResolutionCategory enum."""
        assert ResolutionCategory.COMPLETED.value == "completed"
        assert ResolutionCategory.REJECTED.value == "rejected"
        assert ResolutionCategory.DEFERRED.value == "deferred"

    def test_workflow_state_machine_get_allowed_transitions(self):
        """Test getting allowed transitions."""
        machine = WorkflowStateMachine()

        # Get transitions from open
        transitions = machine.get_allowed_transitions("task", UnifiedStatus.OPEN)
        assert UnifiedStatus.IN_PROGRESS in transitions
        assert UnifiedStatus.CLOSED in transitions

        # Terminal states have no transitions
        transitions = machine.get_allowed_transitions("task", UnifiedStatus.CLOSED)
        assert len(transitions) == 0
