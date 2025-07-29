"""Test the close command in the CLI."""

import os
from datetime import datetime

import pytest
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app
from ai_trackdown_pytools.core.task import TaskManager

runner = CliRunner()


def run_in_project(project_path, func):
    """Helper to run a function in a project directory."""
    original_cwd = os.getcwd()
    try:
        os.chdir(str(project_path))
        return func()
    finally:
        os.chdir(original_cwd)


@pytest.fixture
def project_with_tickets(tmp_path):
    """Create a project with various ticket types for testing."""
    # Save original directory
    original_cwd = os.getcwd()

    try:
        # Change to temp directory for initialization
        os.chdir(str(tmp_path))

        # Initialize project
        result = runner.invoke(app, ["init", "project", "test-project"])
        assert result.exit_code == 0

        project_dir = tmp_path / "test-project"

        # Create tickets of different types
        tickets = [
            ("task", "Fix login bug", "TSK-0001"),
            ("issue", "Security vulnerability", "ISS-0001"),
            ("epic", "Refactor authentication", "EP-0001"),
            ("pr", "Add user profiles", "PR-0001"),
        ]

        task_manager = TaskManager(project_dir)

        created_tickets = {}
        for ticket_type, title, _ in tickets:
            kwargs = {
                "type": ticket_type,
                "title": title,
                "description": f"Test {ticket_type}",
            }
            if ticket_type == "pr":
                kwargs["branch"] = "feature/test"
            task = task_manager.create_task(**kwargs)
            created_tickets[ticket_type] = task.id

        return project_dir, created_tickets
    finally:
        os.chdir(original_cwd)


def test_close_task(project_with_tickets):
    """Test closing a task."""
    project_dir, created_tickets = project_with_tickets
    task_id = created_tickets["task"]

    def _test():
        result = runner.invoke(app, ["close", task_id])
        assert result.exit_code == 0
        assert f"Closed task {task_id}" in result.output

        # Verify the task was closed
        task_manager = TaskManager(project_dir)
        task = task_manager.load_task(task_id)
        assert task.status == "completed"
        assert "closed_at" in task.metadata

        # Verify timestamp format
        closed_at = datetime.fromisoformat(task.metadata["closed_at"])
        assert isinstance(closed_at, datetime)

    run_in_project(project_dir, _test)


def test_close_issue(project_with_tickets):
    """Test closing an issue."""
    project_dir, created_tickets = project_with_tickets
    issue_id = created_tickets["issue"]

    def _test():
        result = runner.invoke(app, ["close", issue_id])
        assert result.exit_code == 0
        assert f"Closed issue {issue_id}" in result.output

        # Verify the issue was closed
        task_manager = TaskManager(project_dir)
        issue = task_manager.load_task(issue_id)
        assert issue.status == "completed"
        assert "closed_at" in issue.metadata

    run_in_project(project_dir, _test)


def test_close_epic(project_with_tickets):
    """Test closing an epic."""
    project_dir, created_tickets = project_with_tickets
    epic_id = created_tickets["epic"]

    def _test():
        result = runner.invoke(app, ["close", epic_id])
        assert result.exit_code == 0
        assert f"Closed epic {epic_id}" in result.output

        # Verify the epic was closed
        task_manager = TaskManager(project_dir)
        epic = task_manager.load_task(epic_id)
        assert epic.status == "completed"
        assert "closed_at" in epic.metadata

    run_in_project(project_dir, _test)


def test_close_pr(project_with_tickets):
    """Test closing a PR."""
    project_dir, created_tickets = project_with_tickets
    pr_id = created_tickets["pr"]

    def _test():
        result = runner.invoke(app, ["close", pr_id])
        assert result.exit_code == 0
        assert f"Closed pr {pr_id}" in result.output

        # Verify the PR was closed
        task_manager = TaskManager(project_dir)
        pr = task_manager.load_task(pr_id)
        assert pr.status == "completed"
        assert "closed_at" in pr.metadata

    run_in_project(project_dir, _test)


def test_close_with_comment(project_with_tickets):
    """Test closing a ticket with a comment."""
    project_dir, created_tickets = project_with_tickets
    task_id = created_tickets["task"]

    def _test():
        result = runner.invoke(app, ["close", task_id, "--comment", "Fixed in v1.2.0"])
        assert result.exit_code == 0
        assert f"Closed task {task_id}" in result.output
        assert "Comment: Fixed in v1.2.0" in result.output

        # Verify the comment was saved
        task_manager = TaskManager(project_dir)
        task = task_manager.load_task(task_id)
        assert task.metadata["closing_comment"] == "Fixed in v1.2.0"

    run_in_project(project_dir, _test)


def test_close_case_insensitive(project_with_tickets):
    """Test closing with lowercase ticket ID."""
    project_dir, created_tickets = project_with_tickets
    task_id = created_tickets["task"]

    def _test():
        result = runner.invoke(app, ["close", task_id.lower()])
        assert result.exit_code == 0
        assert f"Closed task {task_id}" in result.output

    run_in_project(project_dir, _test)


def test_close_already_closed(project_with_tickets):
    """Test closing an already closed ticket."""
    project_dir, created_tickets = project_with_tickets
    task_id = created_tickets["task"]

    def _test():
        # First close it
        runner.invoke(app, ["close", task_id])

        # Try to close again
        result = runner.invoke(app, ["close", task_id])
        assert result.exit_code == 0
        assert "is already closed" in result.output

    run_in_project(project_dir, _test)


def test_close_invalid_ticket_id(project_with_tickets):
    """Test closing with invalid ticket ID."""
    project_dir, _ = project_with_tickets

    def _test():
        result = runner.invoke(app, ["close", "INVALID-0001"])
        assert result.exit_code == 1
        assert "Invalid ticket ID format" in result.output

    run_in_project(project_dir, _test)


def test_close_nonexistent_ticket(project_with_tickets):
    """Test closing a ticket that doesn't exist."""
    project_dir, _ = project_with_tickets

    def _test():
        result = runner.invoke(app, ["close", "TSK-0999"])
        assert result.exit_code == 1
        assert "Failed to load" in result.output

    run_in_project(project_dir, _test)


def test_close_no_project(tmp_path):
    """Test closing when not in a project."""

    def _test():
        result = runner.invoke(app, ["close", "TSK-0001"])
        assert result.exit_code == 1
        assert "No AI Trackdown project found" in result.output

    run_in_project(tmp_path, _test)


def test_close_plain_output(project_with_tickets):
    """Test close command with plain output."""
    project_dir, created_tickets = project_with_tickets
    task_id = created_tickets["task"]

    def _test():
        result = runner.invoke(app, ["--plain", "close", task_id, "--comment", "Done"])
        assert result.exit_code == 0
        assert f"Closed task {task_id}" in result.output
        assert "Comment: Done" in result.output
        # Verify no rich formatting
        assert "[" not in result.output
        assert "✅" not in result.output

    run_in_project(project_dir, _test)
