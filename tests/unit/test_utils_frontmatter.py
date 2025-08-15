"""Unit tests for frontmatter utilities."""

import tempfile
from datetime import date, datetime
from pathlib import Path

from ai_trackdown_pytools.utils.frontmatter import (
    FrontmatterError,
    FrontmatterParser,
    StatusWorkflowValidator,
    ValidationResult,
    parse_ticket_file,
    validate_ticket_data,
    write_ticket_file,
)


class TestFrontmatterParser:
    """Test FrontmatterParser functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.parser = FrontmatterParser()
        self.parser_with_validation = FrontmatterParser(validate_schema=True)

    def test_parse_valid_frontmatter_string(self):
        """Test parsing valid frontmatter from string."""
        content = """---
id: TSK-0001
title: Test Task
status: open
priority: medium
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
---

# Test Task

This is the task content.
"""

        frontmatter, markdown, result = self.parser.parse_string(content)

        assert result.valid
        assert frontmatter["id"] == "TSK-0001"
        assert frontmatter["title"] == "Test Task"
        assert frontmatter["status"] == "open"
        assert "# Test Task" in markdown
        assert "This is the task content." in markdown

    def test_parse_frontmatter_with_complex_data(self):
        """Test parsing frontmatter with complex data structures."""
        content = """---
id: TSK-0001
title: Complex Task
assignees:
  - alice
  - bob
tags:
  - bug
  - urgent
metadata:
  sprint: 1
  estimate: 8.5
dependencies:
  - TSK-0002
  - TSK-0003
---

# Complex Task

Content here.
"""

        frontmatter, markdown, result = self.parser.parse_string(content)

        assert result.valid
        assert frontmatter["assignees"] == ["alice", "bob"]
        assert frontmatter["tags"] == ["bug", "urgent"]
        assert frontmatter["metadata"]["sprint"] == 1
        assert frontmatter["metadata"]["estimate"] == 8.5
        assert frontmatter["dependencies"] == ["TSK-0002", "TSK-0003"]

    def test_parse_frontmatter_with_dates(self):
        """Test parsing frontmatter with date objects."""
        content = """---
id: TSK-0001
title: Date Task
due_date: 2025-07-18
created_at: 2025-07-11T10:00:00
target_date: 2025-07-25
---

# Date Task
"""

        frontmatter, markdown, result = self.parser.parse_string(content)

        assert result.valid
        assert isinstance(frontmatter["due_date"], date)
        assert isinstance(frontmatter["created_at"], datetime)
        assert isinstance(frontmatter["target_date"], date)

    def test_parse_invalid_yaml_frontmatter(self):
        """Test parsing invalid YAML frontmatter."""
        content = """---
invalid: yaml: content: here
bad_syntax: [unclosed list
---

# Invalid Task
"""

        frontmatter, markdown, result = self.parser.parse_string(content)

        assert not result.valid
        assert "Invalid YAML" in str(result.errors)
        assert frontmatter == {}

    def test_parse_missing_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = """# Task Without Frontmatter

This task has no frontmatter.
"""

        frontmatter, markdown, result = self.parser.parse_string(content)

        assert not result.valid
        assert "No frontmatter found" in str(result.errors)
        assert frontmatter == {}
        assert markdown == content

    def test_parse_empty_frontmatter(self):
        """Test parsing empty frontmatter."""
        content = """---
---

# Empty Frontmatter Task
"""

        frontmatter, markdown, result = self.parser.parse_string(content)

        assert result.valid  # Empty frontmatter is valid
        assert frontmatter == {}
        assert "# Empty Frontmatter Task" in markdown

    def test_parse_frontmatter_only(self):
        """Test parsing frontmatter without markdown content."""
        content = """---
id: TSK-0001
title: Frontmatter Only
status: open
---
"""

        frontmatter, markdown, result = self.parser.parse_string(content)

        assert result.valid
        assert frontmatter["id"] == "TSK-0001"
        assert markdown.strip() == ""

    def test_parse_file_success(self):
        """Test parsing frontmatter from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
id: TSK-0001
title: File Test
status: open
---

# File Test Task
"""
            )
            temp_path = Path(f.name)

        try:
            frontmatter, markdown, result = self.parser.parse_file(temp_path)

            assert result.valid
            assert frontmatter["id"] == "TSK-0001"
            assert "# File Test Task" in markdown
        finally:
            temp_path.unlink()

    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file."""
        nonexistent_path = Path("/nonexistent/file.md")

        frontmatter, markdown, result = self.parser.parse_file(nonexistent_path)

        assert not result.valid
        assert "File not found" in str(result.errors)

    def test_write_file_success(self):
        """Test writing frontmatter to file."""
        frontmatter_data = {
            "id": "TSK-0001",
            "title": "Write Test",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now(),
            "assignees": ["alice", "bob"],
            "tags": ["test"],
        }
        markdown_content = "# Write Test\n\nThis is test content."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = Path(f.name)

        try:
            result = self.parser.write_file(
                temp_path, frontmatter_data, markdown_content
            )

            assert result.valid
            assert temp_path.exists()

            # Read back and verify
            content = temp_path.read_text()
            assert "id: TSK-0001" in content
            assert "title: Write Test" in content
            assert "assignees:" in content
            assert "- alice" in content
            assert "# Write Test" in content
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_write_file_with_none_values(self):
        """Test writing frontmatter with None values (should be omitted)."""
        frontmatter_data = {
            "id": "TSK-0001",
            "title": "Write Test",
            "description": None,  # Should be omitted
            "assignees": [],  # Should be included as empty list
            "parent": None,  # Should be omitted
        }
        markdown_content = "# Test content"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = Path(f.name)

        try:
            result = self.parser.write_file(
                temp_path, frontmatter_data, markdown_content
            )

            assert result.valid
            content = temp_path.read_text()
            assert "description:" not in content
            assert "parent:" not in content
            assert "assignees: []" in content
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_roundtrip_parse_write(self):
        """Test roundtrip parsing and writing."""
        original_frontmatter = {
            "id": "TSK-0001",
            "title": "Roundtrip Test",
            "status": "open",
            "priority": "medium",
            "assignees": ["alice"],
            "tags": ["test", "roundtrip"],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        original_markdown = "# Roundtrip Test\n\nOriginal content."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = Path(f.name)

        try:
            # Write original data
            write_result = self.parser.write_file(
                temp_path, original_frontmatter, original_markdown
            )
            assert write_result.valid

            # Parse it back
            parsed_frontmatter, parsed_markdown, parse_result = self.parser.parse_file(
                temp_path
            )
            assert parse_result.valid

            # Verify data integrity
            assert parsed_frontmatter["id"] == original_frontmatter["id"]
            assert parsed_frontmatter["title"] == original_frontmatter["title"]
            assert parsed_frontmatter["assignees"] == original_frontmatter["assignees"]
            assert parsed_frontmatter["tags"] == original_frontmatter["tags"]
            assert "# Roundtrip Test" in parsed_markdown
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_parser_with_schema_validation_enabled(self):
        """Test parser with schema validation enabled."""
        valid_content = """---
id: TSK-0001
title: Valid Task
status: open
priority: medium
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
---

# Valid Task
"""

        frontmatter, markdown, result = self.parser_with_validation.parse_string(
            valid_content
        )

        assert result.valid
        assert len(result.errors) == 0

    def test_parser_with_schema_validation_invalid(self):
        """Test parser with schema validation for invalid data."""
        invalid_content = """---
id: INVALID-001  # Invalid ID format
title: Invalid Task
status: invalid_status  # Invalid status
priority: medium
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
---

# Invalid Task
"""

        frontmatter, markdown, result = self.parser_with_validation.parse_string(
            invalid_content
        )

        assert not result.valid
        assert len(result.errors) > 0


class TestStatusWorkflowValidator:
    """Test StatusWorkflowValidator functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.validator = StatusWorkflowValidator()

    def test_valid_task_status_transitions(self):
        """Test valid task status transitions."""
        # Valid transitions
        result = self.validator.validate_status_transition(
            "task", "open", "in_progress"
        )
        assert result.valid

        result = self.validator.validate_status_transition(
            "task", "in_progress", "completed"
        )
        assert result.valid

        result = self.validator.validate_status_transition("task", "open", "cancelled")
        assert result.valid

        result = self.validator.validate_status_transition(
            "task", "blocked", "in_progress"
        )
        assert result.valid

    def test_invalid_task_status_transitions(self):
        """Test invalid task status transitions."""
        # Invalid transitions
        result = self.validator.validate_status_transition("task", "completed", "open")
        assert not result.valid
        assert "Invalid status transition" in str(result.errors)

        result = self.validator.validate_status_transition(
            "task", "cancelled", "in_progress"
        )
        assert not result.valid

        result = self.validator.validate_status_transition(
            "task", "completed", "cancelled"
        )
        assert not result.valid

    def test_valid_epic_status_transitions(self):
        """Test valid epic status transitions."""
        result = self.validator.validate_status_transition(
            "epic", "planning", "in_progress"
        )
        assert result.valid

        result = self.validator.validate_status_transition(
            "epic", "in_progress", "completed"
        )
        assert result.valid

        result = self.validator.validate_status_transition(
            "epic", "planning", "on_hold"
        )
        assert result.valid

    def test_valid_issue_status_transitions(self):
        """Test valid issue status transitions."""
        result = self.validator.validate_status_transition(
            "issue", "open", "in_progress"
        )
        assert result.valid

        result = self.validator.validate_status_transition(
            "issue", "in_progress", "resolved"
        )
        assert result.valid

        result = self.validator.validate_status_transition(
            "issue", "resolved", "verified"
        )
        assert result.valid

        result = self.validator.validate_status_transition(
            "issue", "verified", "closed"
        )
        assert result.valid

    def test_valid_pr_status_transitions(self):
        """Test valid PR status transitions."""
        result = self.validator.validate_status_transition("pr", "draft", "open")
        assert result.valid

        result = self.validator.validate_status_transition("pr", "open", "approved")
        assert result.valid

        result = self.validator.validate_status_transition("pr", "approved", "merged")
        assert result.valid

        result = self.validator.validate_status_transition("pr", "open", "closed")
        assert result.valid

    def test_get_valid_transitions(self):
        """Test getting valid transitions for a status."""
        # Task transitions
        open_transitions = self.validator.get_valid_transitions("task", "open")
        assert "in_progress" in open_transitions
        assert "cancelled" in open_transitions
        assert "blocked" in open_transitions

        # Terminal status should have no transitions
        completed_transitions = self.validator.get_valid_transitions(
            "task", "completed"
        )
        assert len(completed_transitions) == 0

        # Epic transitions
        planning_transitions = self.validator.get_valid_transitions("epic", "planning")
        assert "in_progress" in planning_transitions
        assert "on_hold" in planning_transitions
        assert "cancelled" in planning_transitions

    def test_is_terminal_status(self):
        """Test checking if status is terminal."""
        # Task terminal statuses
        assert self.validator.is_terminal_status("task", "completed")
        assert self.validator.is_terminal_status("task", "cancelled")
        assert not self.validator.is_terminal_status("task", "open")
        assert not self.validator.is_terminal_status("task", "in_progress")

        # Epic terminal statuses
        assert self.validator.is_terminal_status("epic", "completed")
        assert self.validator.is_terminal_status("epic", "cancelled")
        assert not self.validator.is_terminal_status("epic", "planning")

        # Issue terminal statuses
        assert self.validator.is_terminal_status("issue", "closed")
        assert self.validator.is_terminal_status("issue", "wont_fix")
        assert not self.validator.is_terminal_status("issue", "open")

        # PR terminal statuses
        assert self.validator.is_terminal_status("pr", "merged")
        assert self.validator.is_terminal_status("pr", "closed")
        assert not self.validator.is_terminal_status("pr", "open")

    def test_unknown_ticket_type(self):
        """Test validation with unknown ticket type."""
        result = self.validator.validate_status_transition("unknown", "open", "closed")
        assert not result.valid
        assert "Unknown ticket type" in str(result.errors)

    def test_invalid_current_status(self):
        """Test validation with invalid current status."""
        result = self.validator.validate_status_transition(
            "task", "invalid_status", "open"
        )
        assert not result.valid
        assert "Invalid current status" in str(result.errors)

    def test_invalid_new_status(self):
        """Test validation with invalid new status."""
        result = self.validator.validate_status_transition(
            "task", "open", "invalid_status"
        )
        assert not result.valid
        assert "Invalid new status" in str(result.errors)


class TestConvenienceFunctions:
    """Test convenience functions for frontmatter parsing."""

    def test_parse_ticket_file(self):
        """Test parse_ticket_file convenience function."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(
                """---
id: TSK-0001
title: Convenience Test
status: open
priority: medium
---

# Convenience Test
"""
            )
            temp_path = Path(f.name)

        try:
            frontmatter, markdown, result = parse_ticket_file(temp_path)

            assert result.valid
            assert frontmatter["id"] == "TSK-0001"
            assert "# Convenience Test" in markdown
        finally:
            temp_path.unlink()

    def test_validate_ticket_data(self):
        """Test validate_ticket_data convenience function."""
        valid_data = {
            "id": "TSK-0001",
            "title": "Valid Task",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = validate_ticket_data(valid_data, "task")
        assert result.valid

        # Invalid data
        invalid_data = {
            "id": "INVALID-001",
            "title": "Invalid Task",
            "status": "invalid_status",
        }

        result = validate_ticket_data(invalid_data, "task")
        assert not result.valid

    def test_write_ticket_file(self):
        """Test write_ticket_file convenience function."""
        frontmatter_data = {
            "id": "TSK-0001",
            "title": "Write Convenience Test",
            "status": "open",
            "priority": "medium",
            "created_at": datetime.now(),
        }
        markdown_content = "# Write Convenience Test\n\nTest content."

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            temp_path = Path(f.name)

        try:
            result = write_ticket_file(temp_path, frontmatter_data, markdown_content)

            assert result.valid
            assert temp_path.exists()

            # Verify content
            content = temp_path.read_text()
            assert "id: TSK-0001" in content
            assert "# Write Convenience Test" in content
        finally:
            if temp_path.exists():
                temp_path.unlink()


class TestValidationResult:
    """Test ValidationResult class."""

    def test_valid_result(self):
        """Test creating valid result."""
        result = ValidationResult(valid=True)

        assert result.valid
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self):
        """Test creating invalid result with errors."""
        errors = ["Error 1", "Error 2"]
        result = ValidationResult(valid=False, errors=errors)

        assert not result.valid
        assert result.errors == errors
        assert result.warnings == []

    def test_result_with_warnings(self):
        """Test creating result with warnings."""
        warnings = ["Warning 1", "Warning 2"]
        result = ValidationResult(valid=True, warnings=warnings)

        assert result.valid
        assert result.errors == []
        assert result.warnings == warnings

    def test_add_error(self):
        """Test adding error to result."""
        result = ValidationResult(valid=True)
        result.add_error("New error")

        assert not result.valid  # Should become invalid
        assert "New error" in result.errors

    def test_add_warning(self):
        """Test adding warning to result."""
        result = ValidationResult(valid=True)
        result.add_warning("New warning")

        assert result.valid  # Should remain valid
        assert "New warning" in result.warnings

    def test_result_string_representation(self):
        """Test string representation of result."""
        result = ValidationResult(
            valid=False, errors=["Error 1"], warnings=["Warning 1"]
        )

        result_str = str(result)
        assert "ValidationResult" in result_str
        assert "valid=False" in result_str


class TestFrontmatterError:
    """Test FrontmatterError exception."""

    def test_frontmatter_error_creation(self):
        """Test creating FrontmatterError."""
        error = FrontmatterError("Test error message")
        assert str(error) == "Test error message"

    def test_frontmatter_error_inheritance(self):
        """Test FrontmatterError inheritance."""
        error = FrontmatterError("Test error")
        assert isinstance(error, Exception)
