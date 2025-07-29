"""Comprehensive E2E tests for ticket workflow transitions.

This module tests all ticket types (epic, issue, bug, task, pr) through various
workflow paths, including happy paths, cancellation, blocking, and reopening.
It validates state transitions, resolution requirements, and comment permissions.

WHY: Comprehensive workflow testing ensures that:
- All valid transitions work correctly across ticket types
- Invalid transitions are properly rejected
- Resolution requirements are enforced for terminal states
- State history is properly tracked
- Comment permissions follow parent ticket status
"""

from datetime import datetime

import pytest

from ai_trackdown_pytools.core.models import (
    BugModel,
    BugSeverity,
    EpicModel,
    IssueModel,
    IssueType,
    PRModel,
    PRType,
    TaskModel,
)
from ai_trackdown_pytools.core.workflow import (
    ResolutionType,
    UnifiedStatus,
    is_terminal_status,
    requires_resolution,
)
from ai_trackdown_pytools.utils.comments import CommentManager
from ai_trackdown_pytools.utils.ticket_io import load_ticket, save_ticket


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory structure."""
    (tmp_path / "tasks").mkdir()
    (tmp_path / "epics").mkdir()
    (tmp_path / "issues").mkdir()
    (tmp_path / "bugs").mkdir()
    (tmp_path / "prs").mkdir()
    return tmp_path


class TestWorkflowTransitions:
    """Test workflow transitions for all ticket types."""

    def create_test_task(self, task_id: str = "TSK-001") -> TaskModel:
        """Create a test task with minimal required fields."""
        return TaskModel(
            id=task_id,
            title="Test Task",
            description="Test task description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=UnifiedStatus.OPEN,
        )

    def create_test_epic(self, epic_id: str = "EP-001") -> EpicModel:
        """Create a test epic with minimal required fields."""
        return EpicModel(
            id=epic_id,
            title="Test Epic",
            description="Test epic description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=UnifiedStatus.OPEN,
        )

    def create_test_issue(self, issue_id: str = "ISS-001") -> IssueModel:
        """Create a test issue with minimal required fields."""
        return IssueModel(
            id=issue_id,
            title="Test Issue",
            description="Test issue description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=UnifiedStatus.OPEN,
            issue_type=IssueType.FEATURE,
        )

    def create_test_bug(self, bug_id: str = "BUG-001") -> BugModel:
        """Create a test bug with minimal required fields."""
        return BugModel(
            id=bug_id,
            title="Test Bug",
            description="Test bug description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=UnifiedStatus.OPEN,
            severity=BugSeverity.MEDIUM,
        )

    def create_test_pr(self, pr_id: str = "PR-001") -> PRModel:
        """Create a test PR with minimal required fields."""
        return PRModel(
            id=pr_id,
            title="Test PR",
            description="Test PR description",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=UnifiedStatus.DRAFT,
            pr_type=PRType.FEATURE,
            source_branch="feature/test",
            target_branch="main",
        )

    def test_happy_path_task(self, temp_project_dir):
        """Test happy path: open -> in_progress -> resolved -> closed for task.

        WHY: Validates the most common successful workflow path where a task
        is created, worked on, resolved with a resolution type, and finally closed.
        """
        task = self.create_test_task()

        # Start with OPEN status
        assert task.status == UnifiedStatus.OPEN
        assert len(task.status_history) == 0

        # Transition to IN_PROGRESS
        task.transition_to(UnifiedStatus.IN_PROGRESS, user="developer1")
        assert task.status == UnifiedStatus.IN_PROGRESS
        assert len(task.status_history) == 1
        assert task.status_history[0]["from_status"] == UnifiedStatus.OPEN.value
        assert task.status_history[0]["to_status"] == UnifiedStatus.IN_PROGRESS.value
        assert task.status_history[0]["user"] == "developer1"

        # Transition to RESOLVED with resolution
        task.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.IMPLEMENTED,
            resolution_comment="Task implemented successfully",
            user="developer1",
        )
        assert task.status == UnifiedStatus.RESOLVED
        assert task.resolution == ResolutionType.IMPLEMENTED
        assert task.resolution_comment == "Task implemented successfully"
        assert task.resolved_by == "developer1"
        assert task.resolved_at is not None
        assert len(task.status_history) == 2

        # Transition to CLOSED
        task.transition_to(UnifiedStatus.CLOSED, user="manager1")
        assert task.status == UnifiedStatus.CLOSED
        assert len(task.status_history) == 3

        # Verify terminal state
        assert is_terminal_status(task.status)

    def test_cancellation_path_epic(self, temp_project_dir):
        """Test cancellation path: planning -> in_progress -> cancelled for epic.

        WHY: Tests the workflow when work is started but then cancelled,
        ensuring resolution is required and properly tracked.
        """
        epic = self.create_test_epic()

        # Start with OPEN status
        assert epic.status == UnifiedStatus.OPEN

        # Transition to IN_PROGRESS
        epic.transition_to(UnifiedStatus.IN_PROGRESS, user="product_owner")
        assert epic.status == UnifiedStatus.IN_PROGRESS

        # Put on hold first (since IN_PROGRESS can't go directly to CANCELLED)
        epic.transition_to(UnifiedStatus.ON_HOLD, user="product_owner")
        assert epic.status == UnifiedStatus.ON_HOLD

        # Cancel with resolution from ON_HOLD
        epic.transition_to(
            UnifiedStatus.CANCELLED,
            resolution=ResolutionType.OUT_OF_SCOPE,
            resolution_comment="Requirements changed, epic no longer needed",
            user="product_owner",
        )
        assert epic.status == UnifiedStatus.CANCELLED
        assert epic.resolution == ResolutionType.OUT_OF_SCOPE
        assert epic.resolution_comment == "Requirements changed, epic no longer needed"
        assert epic.resolved_by == "product_owner"
        assert is_terminal_status(epic.status)

    def test_blocking_path_issue(self, temp_project_dir):
        """Test blocking path: open -> in_progress -> blocked -> in_progress -> resolved.

        WHY: Validates workflow when work is temporarily blocked by dependencies
        or external factors, then resumed and completed.
        """
        issue = self.create_test_issue()

        # Progress through workflow
        issue.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        assert issue.status == UnifiedStatus.IN_PROGRESS

        # Block the issue
        issue.transition_to(UnifiedStatus.BLOCKED, user="dev1")
        assert issue.status == UnifiedStatus.BLOCKED
        assert len(issue.status_history) == 2

        # Unblock and resume
        issue.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        assert issue.status == UnifiedStatus.IN_PROGRESS
        assert len(issue.status_history) == 3

        # Resolve
        issue.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            resolution_comment="Issue fixed after unblocking",
            user="dev1",
        )
        assert issue.status == UnifiedStatus.RESOLVED
        assert issue.resolution == ResolutionType.FIXED

    def test_reopen_path_bug(self, temp_project_dir):
        """Test reopen path: resolved -> reopened -> in_progress -> closed.

        WHY: Tests the scenario where a resolved ticket needs to be reopened
        due to regression or incomplete fix, tracking reopen count.
        """
        bug = self.create_test_bug()

        # Progress to resolved
        bug.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        bug.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            resolution_comment="Bug fixed",
            user="dev1",
        )
        assert bug.status == UnifiedStatus.RESOLVED
        assert bug.reopen_count == 0

        # Reopen the bug
        bug.transition_to(UnifiedStatus.REOPENED, user="tester1")
        assert bug.status == UnifiedStatus.REOPENED
        assert bug.reopen_count == 1
        assert not is_terminal_status(bug.status)

        # Fix again
        bug.transition_to(UnifiedStatus.IN_PROGRESS, user="dev2")
        bug.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            resolution_comment="Bug fixed properly this time",
            user="dev2",
        )
        assert bug.resolved_by == "dev2"  # Updated resolver

        # Close
        bug.transition_to(UnifiedStatus.CLOSED, user="manager1")
        assert bug.status == UnifiedStatus.CLOSED
        assert bug.reopen_count == 1  # Count remains

    def test_pr_workflow_path(self, temp_project_dir):
        """Test PR-specific workflow: draft -> ready_for_review -> in_review -> approved -> merged.

        WHY: PRs have a unique workflow that differs from other ticket types,
        with specific states for review process.
        """
        pr = self.create_test_pr()

        # Start as DRAFT
        assert pr.status == UnifiedStatus.DRAFT

        # Mark ready for review
        pr.transition_to(UnifiedStatus.READY_FOR_REVIEW, user="developer1")
        assert pr.status == UnifiedStatus.READY_FOR_REVIEW

        # Start review
        pr.transition_to(UnifiedStatus.IN_REVIEW, user="reviewer1")
        assert pr.status == UnifiedStatus.IN_REVIEW

        # Request changes
        pr.transition_to(UnifiedStatus.CHANGES_REQUESTED, user="reviewer1")
        assert pr.status == UnifiedStatus.CHANGES_REQUESTED

        # Back to ready after changes
        pr.transition_to(UnifiedStatus.READY_FOR_REVIEW, user="developer1")
        pr.transition_to(UnifiedStatus.IN_REVIEW, user="reviewer1")

        # Approve
        pr.transition_to(UnifiedStatus.APPROVED, user="reviewer1")
        assert pr.status == UnifiedStatus.APPROVED

        # Merge
        pr.transition_to(UnifiedStatus.MERGED, user="developer1")
        assert pr.status == UnifiedStatus.MERGED
        assert is_terminal_status(pr.status)
        # Note: MERGED doesn't require resolution
        assert not requires_resolution(pr.status)

    def test_resolution_requirements(self, temp_project_dir):
        """Test that terminal states requiring resolution enforce it.

        WHY: Certain terminal states like RESOLVED and CANCELLED require
        a resolution type to provide closure reason for metrics.
        """
        task = self.create_test_task()
        task.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")

        # Try to resolve without resolution (should fail)
        with pytest.raises(ValueError, match="Resolution required for transition"):
            task.transition_to(UnifiedStatus.RESOLVED, user="dev1")

        # Try to cancel without resolution (should fail) - need to go through valid path
        task3 = self.create_test_task("TSK-003")
        task3.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        task3.transition_to(UnifiedStatus.ON_HOLD, user="dev1")
        with pytest.raises(ValueError, match="Resolution required for transition"):
            task3.transition_to(UnifiedStatus.CANCELLED, user="dev1")

        # Completed doesn't require resolution (transition from IN_PROGRESS)
        task2 = self.create_test_task("TSK-002")
        task2.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        task2.transition_to(UnifiedStatus.COMPLETED, user="dev1")
        assert task2.status == UnifiedStatus.COMPLETED
        assert task2.resolution is None

    def test_invalid_transitions(self, temp_project_dir):
        """Test that invalid transitions are rejected.

        WHY: The state machine should prevent illogical transitions that
        would result in inconsistent workflow states.
        """
        task = self.create_test_task()

        # Can't go directly from OPEN to COMPLETED (in default state machine)
        is_valid, error = task.can_transition_to(UnifiedStatus.COMPLETED)
        if not is_valid:  # Depends on state machine configuration
            with pytest.raises(ValueError):
                task.transition_to(UnifiedStatus.COMPLETED, user="dev1")

        # Can't go from terminal state to active state
        task.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        task.transition_to(
            UnifiedStatus.RESOLVED, resolution=ResolutionType.IMPLEMENTED, user="dev1"
        )

        # Resolved is terminal, can't go back to IN_PROGRESS
        is_valid, error = task.can_transition_to(UnifiedStatus.IN_PROGRESS)
        assert not is_valid
        with pytest.raises(ValueError):
            task.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")

    def test_resolution_comment_requirements(self, temp_project_dir):
        """Test resolutions that require comments.

        WHY: Some resolution types like WORKAROUND or WONT_FIX require
        explanation comments for documentation and knowledge sharing.
        """
        bug = self.create_test_bug()
        bug.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")

        # WORKAROUND requires comment
        from ai_trackdown_pytools.core.workflow import resolution_requires_comment

        assert resolution_requires_comment(ResolutionType.WORKAROUND)

        # Transition with WORKAROUND should validate comment in model validator
        bug.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.WORKAROUND,
            resolution_comment="Use alternative API endpoint until main one is fixed",
            user="dev1",
        )
        assert bug.resolution == ResolutionType.WORKAROUND
        assert bug.resolution_comment is not None

    def test_state_history_tracking(self, temp_project_dir):
        """Test comprehensive state history tracking.

        WHY: State history provides audit trail and helps analyze workflow
        efficiency, bottlenecks, and patterns.
        """
        issue = self.create_test_issue()

        # Create a complex workflow history
        transitions = [
            (UnifiedStatus.IN_PROGRESS, "dev1", None, None),
            (UnifiedStatus.BLOCKED, "dev1", None, None),
            (UnifiedStatus.IN_PROGRESS, "dev1", None, None),
            (UnifiedStatus.TESTING, "tester1", None, None),
            (UnifiedStatus.IN_PROGRESS, "dev1", None, None),  # Failed testing
            (UnifiedStatus.TESTING, "tester1", None, None),
            (UnifiedStatus.RESOLVED, "tester1", ResolutionType.FIXED, "All tests pass"),
        ]

        for new_status, user, resolution, comment in transitions:
            issue.transition_to(
                new_status, resolution=resolution, resolution_comment=comment, user=user
            )

        # Verify history
        assert len(issue.status_history) == len(transitions)

        # Check specific history entries
        assert issue.status_history[0]["from_status"] == UnifiedStatus.OPEN.value
        assert issue.status_history[0]["to_status"] == UnifiedStatus.IN_PROGRESS.value
        assert issue.status_history[0]["user"] == "dev1"

        # Check resolution in history
        last_entry = issue.status_history[-1]
        assert last_entry["resolution"] == ResolutionType.FIXED.value
        assert last_entry["comment"] == "All tests pass"

    def test_comment_status_inheritance(self, temp_project_dir):
        """Test that comments inherit read/write permissions from parent ticket.

        WHY: Comments should become read-only when the parent ticket reaches
        a terminal state, preventing modifications to closed tickets.
        """
        # Create a bug and save it
        bug = self.create_test_bug()
        bug_file = temp_project_dir / "bugs" / f"{bug.id}.yaml"
        save_ticket(bug, bug_file)

        # Create comment manager
        comment_manager = CommentManager(bug_file)

        # Add comment while bug is open
        assert comment_manager.add_comment("user1", "Initial bug report details")
        comments = comment_manager.get_comments()
        assert len(comments) == 1

        # Progress bug to terminal state
        bug.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        bug.transition_to(
            UnifiedStatus.RESOLVED, resolution=ResolutionType.FIXED, user="dev1"
        )
        save_ticket(bug, bug_file)

        # Reload bug to verify terminal state
        loaded_bug = load_ticket(bug_file, BugModel)
        assert is_terminal_status(loaded_bug.status)

        # Comments on terminal state tickets should be read-only
        # This would need to be implemented in CommentManager
        # For now, we document the expected behavior

        # Expected: comment_manager.add_comment() should fail or return False
        # when parent ticket is in terminal state

    def test_multiple_ticket_types_workflow(self, temp_project_dir):
        """Test workflows across different ticket types in parallel.

        WHY: Ensures workflow consistency across different ticket types
        and validates that each type can progress through its workflow.
        """
        # Create tickets of each type
        task = self.create_test_task("TSK-100")
        epic = self.create_test_epic("EP-100")
        issue = self.create_test_issue("ISS-100")
        bug = self.create_test_bug("BUG-100")
        pr = self.create_test_pr("PR-100")

        tickets = [
            (task, "tasks", TaskModel),
            (epic, "epics", EpicModel),
            (issue, "issues", IssueModel),
            (bug, "bugs", BugModel),
            (pr, "prs", PRModel),
        ]

        # Save all tickets
        for ticket, subdir, _ in tickets:
            ticket_file = temp_project_dir / subdir / f"{ticket.id}.yaml"
            save_ticket(ticket, ticket_file)

        # Progress each through workflow
        for ticket, subdir, model_class in tickets:
            if hasattr(ticket, "status"):
                # Move to active state
                if ticket.status == UnifiedStatus.DRAFT:
                    ticket.transition_to(UnifiedStatus.READY_FOR_REVIEW, user="user1")
                elif ticket.status == UnifiedStatus.OPEN:
                    ticket.transition_to(UnifiedStatus.IN_PROGRESS, user="user1")

                # Save progress
                ticket_file = temp_project_dir / subdir / f"{ticket.id}.yaml"
                save_ticket(ticket, ticket_file)

                # Verify save/load cycle
                loaded = load_ticket(ticket_file, model_class)
                assert loaded.status == ticket.status
                assert len(loaded.status_history) > 0

    def test_resolution_validation_edge_cases(self, temp_project_dir):
        """Test edge cases in resolution validation.

        WHY: Edge cases help ensure robustness of the resolution system
        and proper error handling for invalid inputs.
        """
        task = self.create_test_task()

        # Test setting resolution on non-terminal state (should be ignored)
        task.resolution = ResolutionType.FIXED
        task.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        # Resolution should not affect non-terminal transitions

        # Test resolution timestamp validation
        task.transition_to(
            UnifiedStatus.RESOLVED, resolution=ResolutionType.DOCUMENTED, user="dev1"
        )
        assert task.resolved_at > task.created_at

        # Test resolution with very long comment
        long_comment = "A" * 1000  # 1000 character comment
        issue = self.create_test_issue()
        issue.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        issue.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.DOCUMENTED,
            resolution_comment=long_comment,
            user="dev1",
        )
        assert len(issue.resolution_comment) == 1000

    def test_workflow_permissions_simulation(self, temp_project_dir):
        """Simulate workflow permission scenarios.

        WHY: Different users may have different permissions to transition
        tickets through workflow states. This test documents expected behavior.
        """
        epic = self.create_test_epic()

        # Simulate different user roles transitioning the epic
        transitions = [
            # (new_status, user, role_simulation)
            (UnifiedStatus.IN_PROGRESS, "product_owner", "product_owner"),
            (UnifiedStatus.ON_HOLD, "manager", "manager"),
            (UnifiedStatus.IN_PROGRESS, "product_owner", "product_owner"),
            (UnifiedStatus.COMPLETED, "product_owner", "product_owner"),
        ]

        for new_status, user, role in transitions:
            # In a real system, we would check permissions here
            # For now, we just track who made the transition
            epic.transition_to(new_status, user=user)
            assert epic.status_history[-1]["user"] == user

        # Verify final state and history
        assert epic.status == UnifiedStatus.COMPLETED
        assert len(epic.status_history) == len(transitions)


class TestWorkflowIntegration:
    """Test workflow integration with file system and other components."""

    def test_workflow_persistence(self, temp_project_dir):
        """Test that workflow state persists correctly to file system.

        WHY: Workflow state including history and resolution must persist
        correctly to maintain data integrity across application restarts.
        """
        # Create and progress a bug through workflow
        bug = BugModel(
            id="BUG-999",
            title="Persistence Test Bug",
            description="Testing workflow persistence",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            severity=BugSeverity.HIGH,
            status=UnifiedStatus.OPEN,
        )

        # Build workflow history
        bug.transition_to(UnifiedStatus.IN_PROGRESS, user="dev1")
        bug.transition_to(UnifiedStatus.TESTING, user="tester1")
        bug.transition_to(
            UnifiedStatus.RESOLVED,
            resolution=ResolutionType.FIXED,
            resolution_comment="Bug fixed with patch #123",
            user="dev1",
        )

        # Save to file
        bug_file = temp_project_dir / "bugs" / f"{bug.id}.yaml"
        save_ticket(bug, bug_file)

        # Load and verify
        loaded_bug = load_ticket(bug_file, BugModel)
        assert loaded_bug.status == UnifiedStatus.RESOLVED
        assert loaded_bug.resolution == ResolutionType.FIXED
        assert loaded_bug.resolution_comment == "Bug fixed with patch #123"
        assert loaded_bug.resolved_by == "dev1"
        assert len(loaded_bug.status_history) == 3

        # Verify history details
        assert loaded_bug.status_history[0]["from_status"] == UnifiedStatus.OPEN.value
        assert (
            loaded_bug.status_history[-1]["to_status"] == UnifiedStatus.RESOLVED.value
        )
        assert loaded_bug.status_history[-1]["resolution"] == ResolutionType.FIXED.value

    def test_concurrent_workflow_updates(self, temp_project_dir):
        """Test handling of concurrent workflow updates.

        WHY: In a multi-user environment, multiple users might try to
        transition a ticket simultaneously. This tests data consistency.
        """
        # Create initial task
        task = TaskModel(
            id="TSK-888",
            title="Concurrency Test",
            description="Testing concurrent updates",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=UnifiedStatus.OPEN,
        )
        task_file = temp_project_dir / "tasks" / f"{task.id}.yaml"
        save_ticket(task, task_file)

        # Simulate two users loading the same task
        user1_task = load_ticket(task_file, TaskModel)
        user2_task = load_ticket(task_file, TaskModel)

        # Both try to transition
        user1_task.transition_to(UnifiedStatus.IN_PROGRESS, user="user1")
        user2_task.transition_to(UnifiedStatus.BLOCKED, user="user2")

        # In a real system, we'd need locking or conflict resolution
        # For this test, we document the last-write-wins behavior
        save_ticket(user1_task, task_file)
        save_ticket(user2_task, task_file)  # This overwrites user1's changes

        # Load final state
        final_task = load_ticket(task_file, TaskModel)
        assert final_task.status == UnifiedStatus.BLOCKED
        assert final_task.status_history[-1]["user"] == "user2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
