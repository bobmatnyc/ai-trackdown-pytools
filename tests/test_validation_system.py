"""Tests for the comprehensive ticket schema validation system."""

import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from ai_trackdown_pytools.core.models import EpicModel, TaskModel
from ai_trackdown_pytools.utils.frontmatter import (
    FrontmatterParser,
    StatusWorkflowValidator,
)
from ai_trackdown_pytools.utils.validation import (
    SchemaValidator,
    validate_id_format,
    validate_relationships,
    validate_task_data,
)


class TestSchemaValidator:
    """Test the comprehensive schema validator."""

    def setup_method(self):
        """Setup test instance."""
        self.validator = SchemaValidator()

    def test_task_validation_success(self):
        """Test successful task validation."""
        task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "description": "A test task",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(task_data, "task")
        assert result.valid
        assert len(result.errors) == 0

    def test_task_validation_invalid_id(self):
        """Test task validation with invalid ID."""
        task_data = {
            "id": "INVALID-001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(task_data, "task")
        assert not result.valid
        assert any("doesn't match expected pattern" in error for error in result.errors)

    def test_task_validation_missing_required_fields(self):
        """Test task validation with missing required fields."""
        task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            # Missing required fields: status, priority, created_at, updated_at
        }

        result = self.validator.validate_ticket(task_data, "task")
        assert not result.valid
        assert len(result.errors) > 0

    def test_task_validation_circular_dependency(self):
        """Test task validation with circular dependency."""
        task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
            "dependencies": ["TSK-0001"],  # Self-dependency
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(task_data, "task")
        assert not result.valid
        assert any("cannot depend on itself" in error for error in result.errors)

    def test_epic_validation_success(self):
        """Test successful epic validation."""
        epic_data = {
            "id": "EP-0001",
            "title": "Test Epic",
            "description": "A test epic",
            "goal": "Test goal",
            "business_value": "High business value",
            "success_criteria": "All tests pass",
            "status": "planning",
            "priority": "high",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(epic_data, "epic")
        assert result.valid

    def test_epic_validation_missing_business_value(self):
        """Test epic validation with missing business value for high priority."""
        epic_data = {
            "id": "EP-0001",
            "title": "Test Epic",
            "status": "planning",
            "priority": "critical",
            "business_value": "",  # Empty business value
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(epic_data, "epic")
        # Should have warnings about missing business value
        assert any("business value" in warning for warning in result.warnings)

    def test_issue_validation_bug_report(self):
        """Test issue validation for bug report."""
        issue_data = {
            "id": "ISS-0001",
            "title": "Test Bug",
            "issue_type": "bug",
            "severity": "high",
            "status": "open",
            "priority": "high",
            "steps_to_reproduce": "1. Do this\n2. Do that",
            "expected_behavior": "Should work",
            "actual_behavior": "Doesn't work",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(issue_data, "issue")
        assert result.valid

    def test_pr_validation_breaking_changes(self):
        """Test PR validation with breaking changes."""
        pr_data = {
            "id": "PR-0001",
            "title": "Test PR",
            "pr_type": "breaking_change",
            "status": "draft",
            "priority": "low",  # Low priority for breaking change should warn
            "source_branch": "feature/test",
            "target_branch": "main",
            "breaking_changes": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(pr_data, "pr")
        # Should warn about low priority for breaking changes
        assert any("breaking changes" in warning for warning in result.warnings)

    def test_project_validation_success(self):
        """Test successful project validation."""
        project_data = {
            "id": "PROJ-0001",
            "name": "Test Project",
            "description": "A test project",
            "status": "active",
            "priority": "medium",
            "team_members": ["alice", "bob"],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = self.validator.validate_ticket(project_data, "project")
        assert result.valid


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_task_model_validation(self):
        """Test TaskModel validation."""
        now = datetime.now()
        task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
            "created_at": now,
            "updated_at": now,
        }

        task = TaskModel(**task_data)
        assert task.id == "TSK-0001"
        assert task.title == "Test Task"
        assert task.status == "open"

    def test_task_model_invalid_id(self):
        """Test TaskModel with invalid ID pattern."""
        now = datetime.now()
        with pytest.raises(Exception):  # Pydantic validation error
            TaskModel(
                id="INVALID-001",
                title="Test Task",
                status="open",
                priority="medium",
                created_at=now,
                updated_at=now,
            )

    def test_epic_model_date_validation(self):
        """Test EpicModel date validation."""
        now = datetime.now()
        past_date = date(2020, 1, 1)

        with pytest.raises(Exception):  # Should fail for past target date
            EpicModel(
                id="EP-0001",
                title="Test Epic",
                status="planning",
                priority="medium",
                target_date=past_date,
                created_at=now,
                updated_at=now,
            )


class TestFrontmatterParser:
    """Test YAML frontmatter parsing."""

    def setup_method(self):
        """Setup test instance."""
        self.parser = FrontmatterParser(validate_schema=True)

    def test_parse_valid_frontmatter(self):
        """Test parsing valid frontmatter."""
        content = """---
id: TSK-0001
title: Test Task
status: open
priority: medium
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
---

# Test Task

This is a test task.
"""

        frontmatter, markdown, result = self.parser.parse_string(content)
        assert result.valid
        assert frontmatter["id"] == "TSK-0001"
        assert "# Test Task" in markdown

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML frontmatter."""
        content = """---
invalid: yaml: content
---

# Test
"""

        frontmatter, markdown, result = self.parser.parse_string(content)
        assert not result.valid
        assert any("Invalid YAML" in error for error in result.errors)

    def test_write_and_read_roundtrip(self):
        """Test writing and reading frontmatter roundtrip."""
        frontmatter_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        markdown_content = "# Test Task\n\nThis is a test."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write file
            write_result = self.parser.write_file(
                temp_path, frontmatter_data, markdown_content
            )
            assert write_result.valid

            # Read file back
            read_frontmatter, read_content, read_result = self.parser.parse_file(
                temp_path
            )
            assert read_result.valid
            assert read_frontmatter["id"] == frontmatter_data["id"]
            assert read_frontmatter["title"] == frontmatter_data["title"]
            assert "# Test Task" in read_content
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestStatusWorkflowValidator:
    """Test status workflow validation."""

    def setup_method(self):
        """Setup test instance."""
        self.workflow_validator = StatusWorkflowValidator()

    def test_valid_task_transitions(self):
        """Test valid task status transitions."""
        # Valid transitions
        result = self.workflow_validator.validate_status_transition(
            "task", "open", "in_progress"
        )
        assert result.valid

        result = self.workflow_validator.validate_status_transition(
            "task", "in_progress", "completed"
        )
        assert result.valid

    def test_invalid_task_transitions(self):
        """Test invalid task status transitions."""
        # Invalid transition
        result = self.workflow_validator.validate_status_transition(
            "task", "completed", "open"
        )
        assert not result.valid
        assert any("Invalid status transition" in error for error in result.errors)

    def test_get_valid_transitions(self):
        """Test getting valid transitions."""
        transitions = self.workflow_validator.get_valid_transitions("task", "open")
        assert "in_progress" in transitions
        assert "cancelled" in transitions

        # Terminal status should have no transitions
        transitions = self.workflow_validator.get_valid_transitions("task", "completed")
        assert len(transitions) == 0

    def test_terminal_status_check(self):
        """Test terminal status checking."""
        assert self.workflow_validator.is_terminal_status("task", "completed")
        assert self.workflow_validator.is_terminal_status("task", "cancelled")
        assert not self.workflow_validator.is_terminal_status("task", "open")


class TestRelationshipValidation:
    """Test relationship validation between tickets."""

    def test_valid_relationships(self):
        """Test valid ticket relationships."""
        tickets = [
            {"id": "EP-0001", "title": "Epic 1", "child_issues": ["ISS-0001"]},
            {
                "id": "ISS-0001",
                "title": "Issue 1",
                "parent": "EP-0001",
                "child_tasks": ["TSK-0001"],
            },
            {"id": "TSK-0001", "title": "Task 1", "parent": "ISS-0001"},
        ]

        result = validate_relationships(tickets)
        assert result.valid

    def test_missing_parent_reference(self):
        """Test validation with missing parent reference."""
        tickets = [
            {
                "id": "TSK-0001",
                "title": "Task 1",
                "parent": "ISS-0001",  # Parent doesn't exist
            }
        ]

        result = validate_relationships(tickets)
        assert any("non-existent parent" in warning for warning in result.warnings)

    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        tickets = [
            {"id": "TSK-0001", "title": "Task 1", "dependencies": ["TSK-0002"]},
            {
                "id": "TSK-0002",
                "title": "Task 2",
                "dependencies": ["TSK-0001"],  # Circular dependency
            },
        ]

        result = validate_relationships(tickets)
        assert not result.valid
        assert any("Circular dependency" in error for error in result.errors)


class TestConvenienceFunctions:
    """Test convenience validation functions."""

    def test_validate_task_data(self):
        """Test validate_task_data convenience function."""
        task_data = {
            "id": "TSK-0001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = validate_task_data(task_data)
        assert result.valid

    def test_validate_id_format(self):
        """Test ID format validation."""
        # Valid IDs
        result = validate_id_format("TSK-0001", "task")
        assert result.valid

        result = validate_id_format("EP-0001", "epic")
        assert result.valid

        # Invalid ID
        result = validate_id_format("INVALID-001", "task")
        assert not result.valid


if __name__ == "__main__":
    pytest.main([__file__])
