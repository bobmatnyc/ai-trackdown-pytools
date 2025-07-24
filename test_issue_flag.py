#!/usr/bin/env python3
"""Test script for the --issue flag functionality."""

import tempfile
import shutil
from pathlib import Path
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager

def test_issue_flag():
    """Test creating a task with --issue flag."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        
        # Initialize project
        project = Project(project_path)
        project.initialize()
        print(f"✅ Project initialized at {project_path}")
        
        # Create task manager
        task_manager = TaskManager(project_path)
        
        # Create an issue first
        issue = task_manager.create_task(
            type="issue",
            title="Test Issue",
            description="A test issue for verification",
            tags=["issue", "bug"],
            metadata={"type": "issue", "issue_type": "bug", "severity": "medium"}
        )
        print(f"✅ Created issue: {issue.id}")
        
        # Create a task associated with the issue
        task = task_manager.create_task(
            title="Fix the bug",
            description="Task to fix the bug in the issue",
            parent=issue.id,
            tags=["bugfix"]
        )
        print(f"✅ Created task: {task.id} with parent: {task.parent}")
        
        # Update the issue's subtasks
        issue_metadata = issue.metadata.copy()
        subtasks = issue_metadata.get("subtasks", [])
        subtasks.append(task.id)
        issue_metadata["subtasks"] = subtasks
        
        # Update the issue
        success = task_manager.update_task(issue.id, metadata=issue_metadata)
        print(f"✅ Updated issue with subtask: {success}")
        
        # Reload the issue to verify
        updated_issue = task_manager.load_task(issue.id)
        print(f"✅ Issue subtasks: {updated_issue.metadata.get('subtasks', [])}")
        
        # Verify the task has the correct parent
        assert task.parent == issue.id, f"Task parent should be {issue.id}, but got {task.parent}"
        assert task.id in updated_issue.metadata.get("subtasks", []), f"Task {task.id} should be in issue's subtasks"
        
        print("\n✨ All tests passed! The --issue flag implementation works correctly.")

if __name__ == "__main__":
    test_issue_flag()