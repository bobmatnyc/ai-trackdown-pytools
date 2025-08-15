"""Unit tests for workflow management system.

Tests the unified status, resolution tracking, and state transition validation.
"""

from datetime import datetime

import pytest

from ai_trackdown_pytools.core.compatibility import (
    convert_to_legacy_status,
    convert_to_unified_status,
    is_compatible_status,
)
from ai_trackdown_pytools.core.models import (
    BugModel,
    EpicStatus,
    IssueModel,
    PRStatus,
    TaskModel,
    TaskStatus,
)
from ai_trackdown_pytools.core.workflow import (
    ResolutionCategory,
    ResolutionType,
    StatusCategory,
    UnifiedStatus,
    get_resolution_category,
    get_status_category,
    is_terminal_status,
    map_legacy_status,
    requires_resolution,
    resolution_requires_comment,
    workflow_state_machine,
)


class TestUnifiedStatus:
    """Test UnifiedStatus enum and metadata."""

    def test_status_categories(self):
        """Test that all statuses have proper categories."""
        # Initial states
        assert get_status_category(UnifiedStatus.OPEN) == StatusCategory.INITIAL
        assert get_status_category(UnifiedStatus.NEW) == StatusCategory.INITIAL
        assert get_status_category(UnifiedStatus.TODO) == StatusCategory.INITIAL
        assert get_status_category(UnifiedStatus.PLANNING) == StatusCategory.INITIAL

        # Active states
        assert get_status_category(UnifiedStatus.IN_PROGRESS) == StatusCategory.ACTIVE
        assert get_status_category(UnifiedStatus.IN_REVIEW) == StatusCategory.ACTIVE
        assert get_status_category(UnifiedStatus.TESTING) == StatusCategory.ACTIVE
        assert get_status_category(UnifiedStatus.REOPENED) == StatusCategory.ACTIVE

        # Waiting states
        assert get_status_category(UnifiedStatus.PENDING) == StatusCategory.WAITING
        assert get_status_category(UnifiedStatus.ON_HOLD) == StatusCategory.WAITING
        assert get_status_category(UnifiedStatus.BLOCKED) == StatusCategory.WAITING

        # Terminal states
        assert get_status_category(UnifiedStatus.COMPLETED) == StatusCategory.TERMINAL
        assert get_status_category(UnifiedStatus.RESOLVED) == StatusCategory.TERMINAL
        assert get_status_category(UnifiedStatus.CLOSED) == StatusCategory.TERMINAL
        assert get_status_category(UnifiedStatus.CANCELLED) == StatusCategory.TERMINAL

    def test_terminal_status_detection(self):
        """Test terminal status detection."""
        # Terminal statuses
        assert is_terminal_status(UnifiedStatus.COMPLETED)
        assert is_terminal_status(UnifiedStatus.RESOLVED)
        assert is_terminal_status(UnifiedStatus.CLOSED)
        assert is_terminal_status(UnifiedStatus.CANCELLED)
        assert is_terminal_status(UnifiedStatus.MERGED)
        assert is_terminal_status(UnifiedStatus.DONE)
        assert is_terminal_status(UnifiedStatus.ARCHIVED)

        # Non-terminal statuses
        assert not is_terminal_status(UnifiedStatus.OPEN)
        assert not is_terminal_status(UnifiedStatus.IN_PROGRESS)
        assert not is_terminal_status(UnifiedStatus.BLOCKED)
        assert not is_terminal_status(UnifiedStatus.PENDING)

    def test_resolution_requirements(self):
        """Test which statuses require resolution."""
        # Statuses requiring resolution
        assert requires_resolution(UnifiedStatus.RESOLVED)
        assert requires_resolution(UnifiedStatus.CLOSED)
        assert requires_resolution(UnifiedStatus.CANCELLED)

        # Statuses not requiring resolution
        assert not requires_resolution(UnifiedStatus.COMPLETED)
        assert not requires_resolution(UnifiedStatus.MERGED)
        assert not requires_resolution(UnifiedStatus.DONE)
        assert not requires_resolution(UnifiedStatus.ARCHIVED)


class TestResolutionType:
    """Test ResolutionType enum and metadata."""

    def test_resolution_categories(self):
        """Test that all resolutions have proper categories."""
        # Successful resolutions
        assert (
            get_resolution_category(ResolutionType.FIXED)
            == ResolutionCategory.SUCCESSFUL
        )
        assert (
            get_resolution_category(ResolutionType.COMPLETED)
            == ResolutionCategory.SUCCESSFUL
        )
        assert (
            get_resolution_category(ResolutionType.DELIVERED)
            == ResolutionCategory.SUCCESSFUL
        )
        assert (
            get_resolution_category(ResolutionType.IMPLEMENTED)
            == ResolutionCategory.SUCCESSFUL
        )

        # Unsuccessful resolutions
        assert (
            get_resolution_category(ResolutionType.WONT_FIX)
            == ResolutionCategory.UNSUCCESSFUL
        )
        assert (
            get_resolution_category(ResolutionType.INCOMPLETE)
            == ResolutionCategory.UNSUCCESSFUL
        )
        assert (
            get_resolution_category(ResolutionType.ABANDONED)
            == ResolutionCategory.UNSUCCESSFUL
        )

        # Invalid resolutions
        assert (
            get_resolution_category(ResolutionType.DUPLICATE)
            == ResolutionCategory.INVALID
        )
        assert (
            get_resolution_category(ResolutionType.CANNOT_REPRODUCE)
            == ResolutionCategory.INVALID
        )
        assert (
            get_resolution_category(ResolutionType.WORKS_AS_DESIGNED)
            == ResolutionCategory.INVALID
        )

        # Deferred resolutions
        assert (
            get_resolution_category(ResolutionType.DEFERRED)
            == ResolutionCategory.DEFERRED
        )
        assert (
            get_resolution_category(ResolutionType.MOVED) == ResolutionCategory.DEFERRED
        )
        assert (
            get_resolution_category(ResolutionType.BACKLOG)
            == ResolutionCategory.DEFERRED
        )

    def test_resolution_comment_requirements(self):
        """Test which resolutions require comments."""
        # Resolutions requiring comments
        assert resolution_requires_comment(ResolutionType.WORKAROUND)
        assert resolution_requires_comment(ResolutionType.WONT_FIX)
        assert resolution_requires_comment(ResolutionType.INCOMPLETE)
        assert resolution_requires_comment(ResolutionType.DUPLICATE)

        # Resolutions not requiring comments
        assert not resolution_requires_comment(ResolutionType.FIXED)
        assert not resolution_requires_comment(ResolutionType.COMPLETED)
        assert not resolution_requires_comment(ResolutionType.TIMEOUT)


class TestWorkflowStateMachine:
    """Test workflow state machine and transitions."""

    def test_valid_transitions_from_open(self):
        """Test valid transitions from OPEN status."""
        transitions = workflow_state_machine.get_valid_transitions(UnifiedStatus.OPEN)
        to_statuses = [t.to_status for t in transitions]

        assert UnifiedStatus.IN_PROGRESS in to_statuses
        assert UnifiedStatus.CANCELLED in to_statuses
        assert UnifiedStatus.BLOCKED in to_statuses

    def test_valid_transitions_from_in_progress(self):
        """Test valid transitions from IN_PROGRESS status."""
        transitions = workflow_state_machine.get_valid_transitions(
            UnifiedStatus.IN_PROGRESS
        )
        to_statuses = [t.to_status for t in transitions]

        assert UnifiedStatus.TESTING in to_statuses
        assert UnifiedStatus.IN_REVIEW in to_statuses
        assert UnifiedStatus.COMPLETED in to_statuses
        assert UnifiedStatus.RESOLVED in to_statuses
        assert UnifiedStatus.BLOCKED in to_statuses
        assert UnifiedStatus.ON_HOLD in to_statuses

    def test_terminal_state_transitions(self):
        """Test transitions from terminal states."""
        # Can reopen from terminal states
        for status in [
            UnifiedStatus.COMPLETED,
            UnifiedStatus.RESOLVED,
            UnifiedStatus.CLOSED,
        ]:
            transitions = workflow_state_machine.get_valid_transitions(status)
            to_statuses = [t.to_status for t in transitions]
            assert UnifiedStatus.REOPENED in to_statuses

    def test_transition_validation(self):
        """Test state transition validation."""
        # Valid transition
        is_valid, error = workflow_state_machine.validate_transition(
            UnifiedStatus.OPEN, UnifiedStatus.IN_PROGRESS
        )
        assert is_valid
        assert error is None

        # Invalid transition
        is_valid, error = workflow_state_machine.validate_transition(
            UnifiedStatus.OPEN, UnifiedStatus.MERGED
        )
        assert not is_valid
        assert "Invalid transition" in error

    def test_resolution_validation(self):
        """Test resolution validation in transitions."""
        # Transition requiring resolution
        transition = workflow_state_machine.get_transition(
            UnifiedStatus.IN_PROGRESS, UnifiedStatus.RESOLVED
        )
        assert transition.requires_resolution

        # Valid resolution
        is_valid, error = workflow_state_machine.validate_transition(
            UnifiedStatus.IN_PROGRESS, UnifiedStatus.RESOLVED, ResolutionType.FIXED
        )
        assert is_valid

        # Missing resolution
        is_valid, error = workflow_state_machine.validate_transition(
            UnifiedStatus.IN_PROGRESS, UnifiedStatus.RESOLVED
        )
        assert not is_valid
        assert "Resolution required" in error


class TestLegacyStatusMapping:
    """Test legacy status mapping and compatibility."""

    def test_map_legacy_status(self):
        """Test mapping of legacy status values."""
        # Direct mappings
        assert map_legacy_status("open") == UnifiedStatus.OPEN
        assert map_legacy_status("in_progress") == UnifiedStatus.IN_PROGRESS
        assert map_legacy_status("completed") == UnifiedStatus.COMPLETED
        assert map_legacy_status("cancelled") == UnifiedStatus.CANCELLED

        # Special mappings
        assert map_legacy_status("planning") == UnifiedStatus.PLANNING
        assert map_legacy_status("testing") == UnifiedStatus.TESTING
        assert map_legacy_status("draft") == UnifiedStatus.DRAFT
        assert map_legacy_status("merged") == UnifiedStatus.MERGED
        assert map_legacy_status("active") == UnifiedStatus.ACTIVE
        assert map_legacy_status("archived") == UnifiedStatus.ARCHIVED

    def test_convert_to_unified_status(self):
        """Test conversion from various formats to UnifiedStatus."""
        # String conversion
        assert convert_to_unified_status("open") == UnifiedStatus.OPEN
        assert convert_to_unified_status("in_progress") == UnifiedStatus.IN_PROGRESS

        # Legacy enum conversion
        assert convert_to_unified_status(TaskStatus.OPEN) == UnifiedStatus.OPEN
        assert convert_to_unified_status(EpicStatus.PLANNING) == UnifiedStatus.PLANNING
        assert convert_to_unified_status(PRStatus.DRAFT) == UnifiedStatus.DRAFT

        # Already unified
        assert convert_to_unified_status(UnifiedStatus.OPEN) == UnifiedStatus.OPEN

    def test_is_compatible_status(self):
        """Test status compatibility with ticket types."""
        # Task compatible statuses
        assert is_compatible_status(UnifiedStatus.OPEN, "task")
        assert is_compatible_status(UnifiedStatus.IN_PROGRESS, "task")
        assert is_compatible_status(UnifiedStatus.COMPLETED, "task")
        assert not is_compatible_status(UnifiedStatus.MERGED, "task")

        # PR compatible statuses
        assert is_compatible_status(UnifiedStatus.DRAFT, "pr")
        assert is_compatible_status(UnifiedStatus.MERGED, "pr")
        assert not is_compatible_status(UnifiedStatus.PLANNING, "pr")

        # Epic compatible statuses
        assert is_compatible_status(UnifiedStatus.PLANNING, "epic")
        assert is_compatible_status(UnifiedStatus.ACTIVE, "epic")
        assert not is_compatible_status(UnifiedStatus.MERGED, "epic")


class TestModelIntegration:
    """Test integration with Pydantic models."""

    def test_task_model_status_normalization(self):
        """Test TaskModel status normalization."""
        # Create task with legacy status
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status="open",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert isinstance(task.status, UnifiedStatus)
        assert task.status == UnifiedStatus.OPEN

        # Create task with TaskStatus enum
        task2 = TaskModel(
            id="TSK-002",
            title="Test Task 2",
            status=TaskStatus.IN_PROGRESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert isinstance(task2.status, UnifiedStatus)
        assert task2.status == UnifiedStatus.IN_PROGRESS

    def test_issue_model_resolution_validation(self):
        """Test IssueModel resolution validation."""
        # Valid resolution without comment
        issue = IssueModel(
            id="ISS-001",
            title="Test Issue",
            status=UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert issue.resolution == ResolutionType.FIXED

        # Resolution requiring comment
        with pytest.raises(ValueError, match="requires a comment"):
            issue2 = IssueModel(
                id="ISS-002",
                title="Test Issue 2",
                status=UnifiedStatus.CLOSED,
                resolution=ResolutionType.WONT_FIX,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

    def test_model_state_transition(self):
        """Test state transition methods on models."""
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status=UnifiedStatus.OPEN,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Valid transition
        can_transition, error = task.can_transition_to(UnifiedStatus.IN_PROGRESS)
        assert can_transition
        assert error is None

        # Invalid transition
        can_transition, error = task.can_transition_to(UnifiedStatus.MERGED)
        assert not can_transition
        assert error is not None

        # Perform transition
        task.transition_to(UnifiedStatus.IN_PROGRESS, user="test_user")
        assert task.status == UnifiedStatus.IN_PROGRESS
        assert len(task.status_history) == 1
        assert task.status_history[0]["from_status"] == "open"
        assert task.status_history[0]["to_status"] == "in_progress"
        assert task.status_history[0]["user"] == "test_user"

    def test_resolution_tracking(self):
        """Test resolution tracking in models."""
        bug = BugModel(
            id="BUG-001",
            title="Test Bug",
            status=UnifiedStatus.IN_PROGRESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Transition to resolved with resolution
        bug.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            resolution_comment="Bug fixed in commit abc123",
            user="developer",
        )

        assert bug.status == UnifiedStatus.RESOLVED
        assert bug.resolution == ResolutionType.FIXED
        assert bug.resolution_comment == "Bug fixed in commit abc123"
        assert bug.resolved_by == "developer"
        assert bug.resolved_at is not None

        # Reopen increases counter
        bug.transition_to(UnifiedStatus.REOPENED, user="tester")
        assert bug.reopen_count == 1


class TestBackwardCompatibility:
    """Test backward compatibility features."""

    def test_convert_to_legacy_status(self):
        """Test conversion from UnifiedStatus to legacy enums."""
        # Task status conversions
        assert convert_to_legacy_status(UnifiedStatus.OPEN, "task") == TaskStatus.OPEN
        assert (
            convert_to_legacy_status(UnifiedStatus.IN_PROGRESS, "task")
            == TaskStatus.IN_PROGRESS
        )
        assert convert_to_legacy_status(UnifiedStatus.TODO, "task") == TaskStatus.OPEN
        assert (
            convert_to_legacy_status(UnifiedStatus.DONE, "task") == TaskStatus.COMPLETED
        )

        # PR status conversions
        assert convert_to_legacy_status(UnifiedStatus.DRAFT, "pr") == PRStatus.DRAFT
        assert convert_to_legacy_status(UnifiedStatus.MERGED, "pr") == PRStatus.MERGED
        assert convert_to_legacy_status(UnifiedStatus.OPEN, "pr") == PRStatus.DRAFT

        # Epic status conversions
        assert (
            convert_to_legacy_status(UnifiedStatus.PLANNING, "epic")
            == EpicStatus.PLANNING
        )
        assert (
            convert_to_legacy_status(UnifiedStatus.ACTIVE, "epic")
            == EpicStatus.IN_PROGRESS
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
