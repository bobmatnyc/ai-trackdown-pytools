"""Comprehensive unit tests for validation module."""

import json
from pathlib import Path
from unittest.mock import mock_open, patch

import yaml

from ai_trackdown_pytools.utils.validation import (
    SchemaValidator,
    ValidationResult,
    get_id_pattern_for_type,
    validate_epic_data,
    validate_id_format,
    validate_issue_data,
    validate_pr_data,
    validate_project_data,
    validate_project_structure,
    validate_relationships,
    validate_task_data,
    validate_task_file,
    validate_ticket_file,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating ValidationResult."""
        result = ValidationResult(
            valid=True, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )

        assert result.valid is True
        assert result.errors == ["Error 1", "Error 2"]
        assert result.warnings == ["Warning 1"]

    def test_validation_result_defaults(self):
        """Test ValidationResult with defaults."""
        result = ValidationResult()

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_add_error(self):
        """Test adding error to ValidationResult."""
        result = ValidationResult()
        assert result.valid is True

        result.add_error("Test error")

        assert result.valid is False
        assert "Test error" in result.errors

    def test_validation_result_add_warning(self):
        """Test adding warning to ValidationResult."""
        result = ValidationResult()

        result.add_warning("Test warning")

        assert result.valid is True  # Warnings don't affect validity
        assert "Test warning" in result.warnings

    def test_validation_result_merge(self):
        """Test merging ValidationResults."""
        result1 = ValidationResult(valid=True)
        result1.add_warning("Warning 1")

        result2 = ValidationResult(valid=False)
        result2.add_error("Error 2")
        result2.add_warning("Warning 2")

        result1.merge(result2)

        assert result1.valid is False  # Merged invalid result
        assert "Error 2" in result1.errors
        assert "Warning 1" in result1.warnings
        assert "Warning 2" in result1.warnings

    def test_validation_result_to_dict(self):
        """Test converting ValidationResult to dict."""
        result = ValidationResult(valid=False)
        result.add_error("Error")
        result.add_warning("Warning")

        result_dict = result.to_dict()

        assert result_dict["valid"] is False
        assert result_dict["errors"] == ["Error"]
        assert result_dict["warnings"] == ["Warning"]


class TestSchemaValidator:
    """Test SchemaValidator class."""

    @patch("pathlib.Path.glob")
    @patch("builtins.open")
    def test_schema_validator_init(self, mock_open_func, mock_glob):
        """Test SchemaValidator initialization."""
        # Mock schema files
        mock_glob.return_value = [
            Path("/schemas/task.json"),
            Path("/schemas/epic.json"),
        ]

        # Mock schema content
        task_schema = {"type": "object", "properties": {"id": {"type": "string"}}}
        epic_schema = {"type": "object", "properties": {"id": {"type": "string"}}}

        mock_open_func.side_effect = [
            mock_open(read_data=json.dumps(task_schema))(),
            mock_open(read_data=json.dumps(epic_schema))(),
        ]

        validator = SchemaValidator()

        assert validator.schema_dir.name == "schemas"
        assert len(validator._schemas) == 2
        assert "task" in validator._schemas
        assert "epic" in validator._schemas

    def test_validate_ticket_with_schema(self):
        """Test validating ticket with schema."""
        validator = SchemaValidator()

        # Mock schema
        task_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "id": {"type": "string", "pattern": "^TSK-\\d+$"},
                "title": {"type": "string"},
            },
            "required": ["id", "title"],
        }
        validator._schemas["task"] = task_schema

        # Valid task
        valid_task = {"id": "TSK-001", "title": "Test Task"}
        result = validator.validate_ticket(valid_task, "task")
        assert result.valid is True

        # Invalid task - wrong ID format
        invalid_task = {"id": "WRONG-001", "title": "Test Task"}
        result = validator.validate_ticket(invalid_task, "task")
        assert result.valid is False

    def test_validate_ticket_specific_rules(self):
        """Test ticket-specific validation rules."""
        validator = SchemaValidator()
        validator._schemas["task"] = {"type": "object"}

        # Task with invalid parent
        task_data = {
            "id": "TSK-001",
            "parent": "TSK-002",  # Tasks can't have task parents
        }
        result = validator.validate_ticket(task_data, "task")
        assert result.valid is False
        assert any("parent must be an issue" in err for err in result.errors)

        # Task with self-dependency
        task_data = {"id": "TSK-001", "dependencies": ["TSK-001"]}
        result = validator.validate_ticket(task_data, "task")
        assert result.valid is False
        assert any("cannot depend on itself" in err for err in result.errors)

    def test_validate_config(self):
        """Test configuration validation."""
        validator = SchemaValidator()

        # Valid config
        valid_config = {
            "version": "1.0.0",
            "editor": {"default": "vim"},
            "tasks": {"id_format": "TSK-{counter:04d}"},
        }
        result = validator.validate_config(valid_config)
        assert result["valid"] is True

        # Invalid editor config
        invalid_config = {"editor": "not a dict"}
        result = validator.validate_config(invalid_config)
        assert result["valid"] is False
        assert any("must be a dictionary" in err for err in result["errors"])

    def test_validate_template(self):
        """Test template validation."""
        validator = SchemaValidator()

        # Valid template
        valid_template = {
            "name": "Bug Report",
            "type": "issue",
            "content": "Bug report template content",
        }
        result = validator.validate_template(valid_template)
        assert result["valid"] is True

        # Missing required fields
        invalid_template = {"name": "Test Template"}
        result = validator.validate_template(invalid_template)
        assert result["valid"] is False
        assert any("Missing required field: type" in err for err in result["errors"])
        assert any("Missing required field: content" in err for err in result["errors"])


class TestProjectStructureValidation:
    """Test project structure validation functions."""

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_dir")
    def test_validate_project_structure_valid(self, mock_is_dir, mock_exists):
        """Test validating valid project structure."""

        # Mock file system
        def exists_side_effect(path):
            path_str = str(path)
            return any(
                part in path_str
                for part in [
                    ".aitrackdown",
                    "config.yaml",
                    "tasks",
                    "issues",
                    "epics",
                    "prs",
                ]
            )

        mock_exists.side_effect = exists_side_effect
        mock_is_dir.return_value = True

        result = validate_project_structure(Path("/project"))

        assert result["valid"] is True
        assert result["errors"] == []

    @patch("pathlib.Path.exists")
    def test_validate_project_structure_missing_dirs(self, mock_exists):
        """Test validating project with missing directories."""
        # Only .aitrackdown exists
        mock_exists.side_effect = lambda p: ".aitrackdown" in str(
            p
        ) and "config" not in str(p)

        result = validate_project_structure(Path("/project"))

        assert result["valid"] is False
        assert len(result["errors"]) > 0


class TestTaskFileValidation:
    """Test task file validation functions."""

    def test_validate_task_file_valid(self):
        """Test validating valid task file."""
        valid_content = """---
id: TSK-0001
title: Test Task
status: open
priority: medium
created_at: 2023-01-01T00:00:00
updated_at: 2023-01-01T00:00:00
---

# Test Task

## Description
This is a test task."""

        with patch("builtins.open", mock_open(read_data=valid_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = validate_task_file(Path("/tasks/TSK-0001.md"))

                assert result["valid"] is True
                assert result["errors"] == []

    def test_validate_task_file_not_found(self):
        """Test validating non-existent task file."""
        with patch("pathlib.Path.exists", return_value=False):
            result = validate_task_file(Path("/tasks/TSK-9999.md"))

            assert result["valid"] is False
            assert any("not found" in err for err in result["errors"])


class TestTicketFileValidation:
    """Test ticket file validation."""

    def test_validate_ticket_file_auto_detect_type(self):
        """Test ticket file validation with auto-detected type."""
        task_content = """---
id: TSK-001
title: Test Task
type: task
---

# Test Task"""

        with patch("builtins.open", mock_open(read_data=task_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = validate_ticket_file(Path("/tasks/TSK-001.md"))

                assert result.valid is True

    def test_validate_ticket_file_explicit_type(self):
        """Test ticket file validation with explicit type."""
        epic_content = """---
id: EP-001
title: Test Epic
---

# Test Epic"""

        with patch("builtins.open", mock_open(read_data=epic_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = validate_ticket_file(
                    Path("/epics/EP-001.md"), ticket_type="epic"
                )

                assert result.valid is True


class TestIdValidation:
    """Test ID format validation."""

    def test_get_id_pattern_for_type(self):
        """Test getting ID pattern for ticket types."""
        assert get_id_pattern_for_type("task") == r"^TSK-[0-9]+$"
        assert get_id_pattern_for_type("epic") == r"^EP-[0-9]+$"
        assert get_id_pattern_for_type("issue") == r"^ISS-[0-9]+$"
        assert get_id_pattern_for_type("pr") == r"^PR-[0-9]+$"
        assert get_id_pattern_for_type("project") == r"^PROJ-[0-9]+$"
        assert get_id_pattern_for_type("unknown") == r"^[A-Z]+-[0-9]+$"

    def test_validate_id_format(self):
        """Test ID format validation."""
        # Valid IDs
        result = validate_id_format("TSK-001", "task")
        assert result.valid is True

        result = validate_id_format("EP-123", "epic")
        assert result.valid is True

        # Invalid IDs
        result = validate_id_format("WRONG-001", "task")
        assert result.valid is False

        result = validate_id_format("TSK001", "task")  # Missing hyphen
        assert result.valid is False

        result = validate_id_format("tsk-001", "task")  # Lowercase
        assert result.valid is False


class TestRelationshipValidation:
    """Test relationship validation."""

    def test_validate_relationships_valid(self):
        """Test validating valid relationships."""
        tickets = [
            {"id": "TSK-001", "dependencies": [], "parent": None},
            {"id": "TSK-002", "dependencies": ["TSK-001"], "parent": "EP-001"},
            {"id": "EP-001", "dependencies": [], "parent": None},
        ]

        result = validate_relationships(tickets)
        assert result.valid is True

    def test_validate_relationships_circular_dependency(self):
        """Test detecting circular dependencies."""
        tickets = [
            {"id": "TSK-001", "dependencies": ["TSK-002"]},
            {"id": "TSK-002", "dependencies": ["TSK-003"]},
            {"id": "TSK-003", "dependencies": ["TSK-001"]},  # Circular
        ]

        result = validate_relationships(tickets)
        assert result.valid is False
        assert any("Circular dependency" in err for err in result.errors)

    def test_validate_relationships_invalid_reference(self):
        """Test detecting invalid references."""
        tickets = [{"id": "TSK-001", "dependencies": ["TSK-999"]}]  # Non-existent

        result = validate_relationships(tickets)
        assert result.valid is False
        assert any("Invalid dependency" in err for err in result.errors)


class TestTicketDataValidation:
    """Test ticket data validation functions."""

    def test_validate_task_data(self):
        """Test task data validation."""
        # Valid task
        valid_task = {
            "id": "TSK-001",
            "title": "Test Task",
            "status": "open",
            "priority": "medium",
        }
        result = validate_task_data(valid_task)
        assert result.valid is True

        # Task with invalid parent
        invalid_task = {
            "id": "TSK-001",
            "title": "Test Task",
            "parent": "TSK-002",  # Tasks can't have task parents
        }
        result = validate_task_data(invalid_task)
        assert result.valid is False

    def test_validate_epic_data(self):
        """Test epic data validation."""
        # High priority epic without business value
        epic = {
            "id": "EP-001",
            "title": "Test Epic",
            "priority": "high",
            "business_value": "",
        }
        result = validate_epic_data(epic)
        assert result.valid is True  # Just a warning
        assert len(result.warnings) > 0
        assert any("business value" in warn for warn in result.warnings)

    def test_validate_issue_data(self):
        """Test issue data validation."""
        # Bug without reproduction steps
        bug = {
            "id": "ISS-001",
            "title": "Test Bug",
            "issue_type": "bug",
            "steps_to_reproduce": "",
            "expected_behavior": "Should work",
            "actual_behavior": "",
        }
        result = validate_issue_data(bug)
        assert result.valid is True  # Just warnings
        assert len(result.warnings) > 0

    def test_validate_pr_data(self):
        """Test PR data validation."""
        # Merged PR without merge timestamp
        pr = {"id": "PR-001", "title": "Test PR", "status": "merged", "merged_at": None}
        result = validate_pr_data(pr)
        assert result.valid is False
        assert any("merged_at timestamp" in err for err in result.errors)

        # Large PR without reviewers
        large_pr = {
            "id": "PR-002",
            "title": "Large PR",
            "lines_added": 300,
            "lines_deleted": 250,
            "reviewers": [],
        }
        result = validate_pr_data(large_pr)
        assert result.valid is True  # Just a warning
        assert len(result.warnings) > 0

    def test_validate_project_data(self):
        """Test project data validation."""
        # Active project without team
        project = {
            "id": "PROJ-001",
            "name": "Test Project",
            "status": "active",
            "team_members": [],
        }
        result = validate_project_data(project)
        assert result.valid is True  # Just a warning
        assert len(result.warnings) > 0
        assert any("team members" in warn for warn in result.warnings)


class TestValidationIntegration:
    """Test validation integration scenarios."""

    @patch("builtins.open")
    @patch("pathlib.Path.exists")
    def test_full_ticket_validation_flow(self, mock_exists, mock_open_func):
        """Test complete ticket validation flow."""
        ticket_content = """---
id: TSK-001
title: Integration Test Task
status: open
priority: high
dependencies: ["TSK-002", "EP-001"]
parent: EP-001
created_at: 2023-01-01T00:00:00
updated_at: 2023-01-01T00:00:00
---

# Integration Test Task

Testing the full validation flow."""

        mock_exists.return_value = True
        mock_open_func.return_value = mock_open(read_data=ticket_content)()

        # Validate file
        result = validate_ticket_file(Path("/tasks/TSK-001.md"))

        # Should validate structure and content
        assert isinstance(result, ValidationResult)

        # Validate just the data
        task_data = yaml.safe_load(ticket_content.split("---")[1])
        data_result = validate_task_data(task_data)

        assert isinstance(data_result, ValidationResult)

    def test_validation_result_aggregation(self):
        """Test aggregating multiple validation results."""
        results = []

        # Validate multiple tasks
        tasks = [
            {"id": "TSK-001", "title": "Task 1"},
            {"id": "INVALID", "title": "Task 2"},  # Invalid ID
            {"id": "TSK-003", "title": "Task 3", "parent": "TSK-004"},  # Invalid parent
        ]

        for task in tasks:
            result = validate_task_data(task)
            results.append(result)

        # Aggregate results
        total_valid = sum(1 for r in results if r.valid)
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)

        assert total_valid < len(tasks)  # Some invalid
        assert total_errors > 0  # Has errors

    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.exists")
    @patch("builtins.open")
    def test_batch_file_validation(self, mock_open_func, mock_exists, mock_glob):
        """Test validating multiple files in batch."""
        # Mock file system
        mock_exists.return_value = True
        mock_glob.return_value = [
            Path("/tasks/TSK-001.md"),
            Path("/tasks/TSK-002.md"),
            Path("/epics/EP-001.md"),
        ]

        # Mock file contents
        file_contents = {
            "/tasks/TSK-001.md": """---
id: TSK-001
title: Task 1
---
# Task 1""",
            "/tasks/TSK-002.md": """---
id: TSK-002
title: Task 2
parent: TSK-001
---
# Task 2""",
            "/epics/EP-001.md": """---
id: EP-001
title: Epic 1
priority: high
---
# Epic 1""",
        }

        mock_open_func.side_effect = lambda path, *args: mock_open(
            read_data=file_contents.get(str(path), "")
        )()

        # Validate all files
        results = {}
        for file_path in mock_glob.return_value:
            result = validate_ticket_file(file_path)
            results[file_path.name] = result

        assert len(results) == 3
        assert all(isinstance(r, ValidationResult) for r in results.values())
