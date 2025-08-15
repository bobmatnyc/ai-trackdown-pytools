"""Tests for comment status inheritance functionality.

WHY: These tests ensure that comments properly inherit status from their parent
tickets and enforce read-only behavior when parent tickets reach terminal states.
This is critical for maintaining data integrity and audit trails.
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from ai_trackdown_pytools.core.models import (
    BugModel,
    CommentModel,
    IssueModel,
    TaskModel,
)
from ai_trackdown_pytools.core.workflow import ResolutionType, UnifiedStatus
from ai_trackdown_pytools.utils.comments import CommentManager, add_comment_to_item


class TestCommentModel:
    """Test the CommentModel functionality."""

    def test_comment_creation(self):
        """Test basic comment creation."""
        comment = CommentModel(
            id="CMT-001",
            parent_id="TSK-001",
            parent_type="task",
            author="test_user",
            content="Test comment",
            created_at=datetime.now(),
        )

        assert comment.id == "CMT-001"
        assert comment.parent_id == "TSK-001"
        assert comment.author == "test_user"
        assert comment.content == "Test comment"
        assert not comment.is_system
        assert not comment.is_read_only

    def test_system_comment_always_readonly(self):
        """Test that system comments are always read-only."""
        comment = CommentModel(
            id="CMT-002",
            parent_id="TSK-001",
            parent_type="task",
            author="system",
            content="Status changed",
            created_at=datetime.now(),
            is_system=True,
        )

        can_edit, reason = comment.can_edit()
        assert not can_edit
        assert reason == "System comments cannot be edited"

    def test_comment_lock_on_terminal_status(self):
        """Test comment locking when parent reaches terminal status."""
        comment = CommentModel(
            id="CMT-003",
            parent_id="TSK-001",
            parent_type="task",
            author="user1",
            content="Test comment",
            created_at=datetime.now(),
        )

        # Initially editable
        can_edit, _ = comment.can_edit()
        assert can_edit

        # Lock due to parent status
        comment.lock_due_to_parent_status(UnifiedStatus.COMPLETED, "admin")

        # Now read-only
        can_edit, reason = comment.can_edit()
        assert not can_edit
        assert comment.is_read_only
        assert comment.parent_status == UnifiedStatus.COMPLETED
        assert comment.locked_reason == "Parent ticket changed to completed by admin"

    def test_comment_edit_validation_with_parent(self):
        """Test comment edit validation with parent ticket."""
        # Create a task in terminal state
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status=UnifiedStatus.COMPLETED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        comment = CommentModel(
            id="CMT-004",
            parent_id="TSK-001",
            parent_type="task",
            author="user1",
            content="Original content",
            created_at=datetime.now(),
        )

        # Cannot edit with terminal parent
        can_edit, reason = comment.can_edit(task)
        assert not can_edit
        assert "completed tickets" in reason

    def test_comment_update_content(self):
        """Test updating comment content."""
        comment = CommentModel(
            id="CMT-005",
            parent_id="TSK-001",
            parent_type="task",
            author="user1",
            content="Original content",
            created_at=datetime.now(),
        )

        # Update content
        comment.update_content("Updated content", "editor1")

        assert comment.content == "Updated content"
        assert comment.edited_by == "editor1"
        assert comment.updated_at is not None

    def test_comment_update_blocked_on_terminal_parent(self):
        """Test that comment updates are blocked on terminal parent."""
        task = TaskModel(
            id="TSK-001",
            title="Test Task",
            status=UnifiedStatus.CLOSED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        comment = CommentModel(
            id="CMT-006",
            parent_id="TSK-001",
            parent_type="task",
            author="user1",
            content="Original content",
            created_at=datetime.now(),
        )

        # Attempt to update
        with pytest.raises(ValueError, match="Cannot edit comment"):
            comment.update_content("New content", "editor1", task)


class TestCommentManager:
    """Test the CommentManager with status inheritance."""

    @pytest.fixture
    def temp_project(self):
        """Create a temporary project for testing."""
        temp_dir = tempfile.mkdtemp()

        # Initialize project structure
        config_path = Path(temp_dir) / ".ai-trackdown"
        config_path.mkdir()

        config_file = config_path / "config.yaml"
        config_file.write_text(
            """
project:
  name: Test Project
  version: 1.0.0
tasks:
  directory: tasks
"""
        )

        tasks_dir = Path(temp_dir) / "tasks"
        tasks_dir.mkdir()

        yield Path(temp_dir)

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_add_comment_to_open_ticket(self, temp_project):
        """Test adding comment to an open ticket."""
        # Create an open task
        task_file = temp_project / "tasks" / "TSK-001.md"
        task_file.write_text(
            """---
id: TSK-001
title: Test Task
status: open
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-01T00:00:00
---

# Test Task

Description here.
"""
        )

        # Add comment
        success = add_comment_to_item(
            "task", "TSK-001", "test_user", "Test comment", temp_project
        )

        assert success

        # Verify comment was added
        content = task_file.read_text()
        assert "## Comments" in content
        assert "Test comment" in content
        assert "test_user" in content

    def test_add_comment_blocked_on_closed_ticket(self, temp_project):
        """Test that adding comments is blocked on closed tickets."""
        # Create a closed task
        task_file = temp_project / "tasks" / "TSK-002.md"
        task_file.write_text(
            """---
id: TSK-002
title: Closed Task
status: closed
resolution: completed
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-01T00:00:00
---

# Closed Task

This task is closed.
"""
        )

        # Attempt to add comment
        success = add_comment_to_item(
            "task", "TSK-002", "test_user", "Should fail", temp_project
        )

        assert not success

        # Verify no comment was added
        content = task_file.read_text()
        assert "Should fail" not in content

    def test_force_add_comment_on_closed_ticket(self, temp_project):
        """Test force adding comment on closed ticket."""
        # Create a closed task
        task_file = temp_project / "tasks" / "TSK-003.md"
        task_file.write_text(
            """---
id: TSK-003
title: Closed Task
status: completed
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-01T00:00:00
---

# Closed Task

This task is completed.
"""
        )

        # Force add comment
        success = add_comment_to_item(
            "task", "TSK-003", "system", "Status update", temp_project, force=True
        )

        assert success

        # Verify comment was added
        content = task_file.read_text()
        assert "Status update" in content

    def test_get_comments_as_models_with_terminal_parent(self, temp_project):
        """Test getting comments as models with terminal parent."""
        # Create a completed task with existing comments
        task_file = temp_project / "tasks" / "TSK-004.md"
        task_file.write_text(
            """---
id: TSK-004
title: Completed Task
status: completed
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-01T00:00:00
---

# Completed Task

## Comments

### Comment by user1 - 2024-01-01 10:00:00 [ID: CMT-001]
First comment

### Comment by user2 - 2024-01-01 11:00:00 [ID: CMT-002]
Second comment
"""
        )

        manager = CommentManager(task_file)
        comments = manager.get_comments_as_models()

        assert len(comments) == 2

        # All comments should be locked due to terminal parent
        for comment in comments:
            assert comment.is_read_only
            assert comment.parent_status == UnifiedStatus.COMPLETED
            can_edit, _ = comment.can_edit()
            assert not can_edit

    def test_comment_id_generation(self, temp_project):
        """Test that comment IDs are generated for new comments."""
        task_file = temp_project / "tasks" / "TSK-005.md"
        task_file.write_text(
            """---
id: TSK-005
title: Test Task
status: open
created_at: 2024-01-01T00:00:00
updated_at: 2024-01-01T00:00:00
---

# Test Task
"""
        )

        manager = CommentManager(task_file)
        manager.add_comment("test_user", "Test comment")

        # Read back and verify ID was generated
        content = task_file.read_text()
        assert "[ID: CMT-" in content


class TestStatusTransitionCommentBehavior:
    """Test comment behavior during status transitions."""

    def test_comments_locked_on_ticket_closure(self):
        """Test that all comments are locked when ticket is closed."""
        # Create issue with comments
        issue = IssueModel(
            id="ISS-001",
            title="Test Issue",
            status=UnifiedStatus.IN_PROGRESS,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create comments
        comments = [
            CommentModel(
                id=f"CMT-{i:03d}",
                parent_id="ISS-001",
                parent_type="issue",
                author=f"user{i}",
                content=f"Comment {i}",
                created_at=datetime.now(),
            )
            for i in range(1, 4)
        ]

        # All comments should be editable initially
        for comment in comments:
            can_edit, _ = comment.can_edit(issue)
            assert can_edit

        # Transition issue to resolved (which is a terminal state)
        issue.transition_to(
            UnifiedStatus.RESOLVED, resolution=ResolutionType.FIXED, user="admin"
        )

        # Lock all comments
        for comment in comments:
            comment.lock_due_to_parent_status(issue.status, "admin")
            can_edit, _ = comment.can_edit(issue)
            assert not can_edit
            assert comment.is_read_only

    def test_reopened_ticket_comments_remain_locked(self):
        """Test that comments remain locked even after ticket is reopened."""
        bug = BugModel(
            id="BUG-001",
            title="Test Bug",
            status=UnifiedStatus.CLOSED,
            resolution=ResolutionType.FIXED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Create a locked comment
        comment = CommentModel(
            id="CMT-001",
            parent_id="BUG-001",
            parent_type="bug",
            author="user1",
            content="Original comment",
            created_at=datetime.now(),
            is_read_only=True,
            parent_status=UnifiedStatus.CLOSED,
            locked_at=datetime.now(),
            locked_reason="Parent ticket changed to closed",
        )

        # Reopen the bug
        bug.transition_to(UnifiedStatus.REOPENED)

        # Comment should remain locked
        can_edit, reason = comment.can_edit(bug)
        assert not can_edit
        assert comment.is_read_only
        # The stored parent status should still show why it was locked
        assert comment.parent_status == UnifiedStatus.CLOSED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
