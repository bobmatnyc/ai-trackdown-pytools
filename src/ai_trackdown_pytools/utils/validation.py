"""Validation utilities for AI Trackdown PyTools."""

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import jsonschema
import yaml
from jsonschema import ValidationError
from pydantic import ValidationError as PydanticValidationError

# from ai_trackdown_pytools.core.models import (
#     TaskModel, EpicModel, IssueModel, PRModel, ProjectModel,
#     TicketModel, get_model_for_type, get_id_pattern_for_type
# )


def get_id_pattern_for_type(ticket_type: str) -> str:
    """Get the ID pattern for a ticket type."""
    pattern_map = {
        "task": r"^TSK-[0-9]+$",
        "epic": r"^EP-[0-9]+$",
        "issue": r"^ISS-[0-9]+$",
        "pr": r"^PR-[0-9]+$",
        "project": r"^PROJ-[0-9]+$",
    }
    return pattern_map.get(ticket_type.lower(), r"^[A-Z]+-[0-9]+$")


class ValidationResult:
    """Validation result container."""

    def __init__(
        self, valid: bool = True, errors: List[str] = None, warnings: List[str] = None
    ):
        """Initialize validation result."""
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)
        self.valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning."""
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.valid:
            self.valid = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {"valid": self.valid, "errors": self.errors, "warnings": self.warnings}


class SchemaValidator:
    """Schema validation utilities."""

    def __init__(self):
        """Initialize schema validator."""
        self.schema_dir = Path(__file__).parent.parent / "schemas"
        self._schemas = {}
        self._model_validators = {}
        self._load_schemas()
        self._setup_model_validators()

    def _load_schemas(self) -> None:
        """Load all available schemas."""
        for schema_file in self.schema_dir.glob("*.json"):
            schema_name = schema_file.stem
            try:
                with open(schema_file, encoding="utf-8") as f:
                    self._schemas[schema_name] = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                continue

    def _setup_model_validators(self) -> None:
        """Setup Pydantic model validators."""
        # Temporarily disabled until models are fixed
        self._model_validators = {}

    def validate_ticket(
        self, ticket_data: Dict[str, Any], ticket_type: str
    ) -> ValidationResult:
        """Validate ticket data against both JSON schema and Pydantic model."""
        result = ValidationResult()

        # First validate against JSON schema
        schema_result = self._validate_against_json_schema(ticket_data, ticket_type)
        result.merge(schema_result)

        # Then validate against Pydantic model (temporarily disabled)
        # model_result = self._validate_against_pydantic_model(ticket_data, ticket_type)
        # result.merge(model_result)

        # Additional custom validations
        custom_result = self._validate_custom_rules(ticket_data, ticket_type)
        result.merge(custom_result)

        return result

    def validate_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task data against schema (legacy method)."""
        result = self.validate_ticket(task_data, "task")
        return result.to_dict()

    def validate_epic(self, epic_data: Dict[str, Any]) -> ValidationResult:
        """Validate epic data."""
        return self.validate_ticket(epic_data, "epic")

    def validate_issue(self, issue_data: Dict[str, Any]) -> ValidationResult:
        """Validate issue data."""
        return self.validate_ticket(issue_data, "issue")

    def validate_pr(self, pr_data: Dict[str, Any]) -> ValidationResult:
        """Validate pull request data."""
        return self.validate_ticket(pr_data, "pr")

    def validate_project(self, project_data: Dict[str, Any]) -> ValidationResult:
        """Validate project data."""
        return self.validate_ticket(project_data, "project")

    def _validate_against_json_schema(
        self, data: Dict[str, Any], schema_name: str
    ) -> ValidationResult:
        """Validate data against JSON schema."""
        result = ValidationResult()

        if schema_name not in self._schemas:
            result.add_error(f"Schema '{schema_name}' not found")
            return result

        schema = self._schemas[schema_name]

        try:
            jsonschema.validate(data, schema)
        except ValidationError as e:
            result.add_error(f"JSON Schema validation failed: {e.message}")

            # Add more specific error information
            if e.path:
                field_path = ".".join(str(p) for p in e.path)
                result.add_error(f"Error in field: {field_path}")

            # Add validation context
            if e.validator and e.validator_value:
                result.add_error(
                    f"Validation rule '{e.validator}' failed with value: {e.validator_value}"
                )

        except jsonschema.SchemaError as e:
            result.add_error(f"Schema error: {e.message}")

        return result

    def _validate_against_pydantic_model(
        self, data: Dict[str, Any], ticket_type: str
    ) -> ValidationResult:
        """Validate data against Pydantic model."""
        result = ValidationResult()

        if ticket_type not in self._model_validators:
            result.add_error(f"No Pydantic model found for type '{ticket_type}'")
            return result

        model_class = self._model_validators[ticket_type]

        try:
            # Preprocess datetime strings
            processed_data = self._preprocess_datetime_fields(data.copy())

            # Validate with Pydantic
            model_instance = model_class(**processed_data)

            # Additional type-specific validations
            self._validate_model_instance(model_instance, result)

        except PydanticValidationError as e:
            for error in e.errors():
                field = ".".join(str(loc) for loc in error["loc"])
                message = error["msg"]
                error_type = error["type"]
                result.add_error(f"Field '{field}': {message} (type: {error_type})")
        except Exception as e:
            result.add_error(f"Unexpected validation error: {str(e)}")

        return result

    def _validate_custom_rules(
        self, data: Dict[str, Any], ticket_type: str
    ) -> ValidationResult:
        """Apply custom validation rules."""
        result = ValidationResult()

        # ID pattern validation
        if "id" in data:
            expected_pattern = get_id_pattern_for_type(ticket_type)
            if not re.match(expected_pattern, data["id"]):
                result.add_error(
                    f"ID '{data['id']}' doesn't match expected pattern for {ticket_type}"
                )

        # Cross-field validations
        if ticket_type == "task":
            self._validate_task_specific_rules(data, result)
        elif ticket_type == "epic":
            self._validate_epic_specific_rules(data, result)
        elif ticket_type == "issue":
            self._validate_issue_specific_rules(data, result)
        elif ticket_type == "pr":
            self._validate_pr_specific_rules(data, result)
        elif ticket_type == "project":
            self._validate_project_specific_rules(data, result)

        # Common relationship validations
        self._validate_relationships(data, result)

        return result

    def _validate_task_specific_rules(
        self, data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate task-specific rules."""
        # Parent validation
        if "parent" in data and data["parent"]:
            parent_id = data["parent"]
            if not (parent_id.startswith("ISS-") or parent_id.startswith("EP-")):
                result.add_error("Task parent must be an issue (ISS-) or epic (EP-)")

        # Dependency cycles
        if "dependencies" in data and "id" in data:
            if data["id"] in data["dependencies"]:
                result.add_error("Task cannot depend on itself")

    def _validate_epic_specific_rules(
        self, data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate epic-specific rules."""
        # Business value should be provided for high priority epics
        if (
            data.get("priority") in ["high", "critical"]
            and not data.get("business_value", "").strip()
        ):
            result.add_warning("High priority epics should have business value defined")

        # Success criteria should be defined
        if not data.get("success_criteria", "").strip():
            result.add_warning("Epics should have success criteria defined")

    def _validate_issue_specific_rules(
        self, data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate issue-specific rules."""
        # Bug reports should have reproduction steps
        if data.get("issue_type") == "bug":
            required_fields = [
                "steps_to_reproduce",
                "expected_behavior",
                "actual_behavior",
            ]
            for field in required_fields:
                if not data.get(field, "").strip():
                    result.add_warning(f"Bug reports should have '{field}' defined")

        # Feature requests should have clear description
        if (
            data.get("issue_type") == "feature"
            and not data.get("description", "").strip()
        ):
            result.add_warning("Feature requests should have detailed description")

    def _validate_pr_specific_rules(
        self, data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate pull request-specific rules."""
        # Breaking changes should be clearly marked
        if data.get("breaking_changes", False) and data.get("priority") not in [
            "high",
            "critical",
        ]:
            result.add_warning(
                "PRs with breaking changes should typically have high or critical priority"
            )

        # Merged PRs should have merge timestamp
        if data.get("status") == "merged" and not data.get("merged_at"):
            result.add_error("Merged PRs must have merged_at timestamp")

        # Large PRs should have reviewers
        lines_added = data.get("lines_added", 0)
        lines_deleted = data.get("lines_deleted", 0)
        total_changes = lines_added + lines_deleted
        if total_changes > 500 and not data.get("reviewers"):
            result.add_warning(
                "Large PRs (>500 lines changed) should have reviewers assigned"
            )

    def _validate_project_specific_rules(
        self, data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate project-specific rules."""
        # Active projects should have team members
        if data.get("status") == "active" and not data.get("team_members"):
            result.add_warning("Active projects should have team members assigned")

        # Projects with budget should have estimated hours
        if data.get("budget") and not data.get("estimated_hours"):
            result.add_warning("Projects with budget should have estimated hours")

    def _validate_relationships(
        self, data: Dict[str, Any], result: ValidationResult
    ) -> None:
        """Validate relationship constraints."""
        # Check for circular dependencies
        if "dependencies" in data and "id" in data:
            self._check_circular_dependencies(data["id"], data["dependencies"], result)

        # Validate reference formats
        reference_fields = [
            "dependencies",
            "child_issues",
            "child_tasks",
            "related_issues",
            "closes_issues",
            "epics",
        ]
        for field in reference_fields:
            if field in data and data[field]:
                self._validate_reference_ids(data[field], result, field)

    def _check_circular_dependencies(
        self, ticket_id: str, dependencies: List[str], result: ValidationResult
    ) -> None:
        """Check for circular dependencies (basic check)."""
        if ticket_id in dependencies:
            result.add_error(
                f"Circular dependency detected: {ticket_id} cannot depend on itself"
            )

    def _validate_reference_ids(
        self, ids: List[str], result: ValidationResult, field_name: str
    ) -> None:
        """Validate reference ID formats."""
        valid_patterns = [
            r"^TSK-[0-9]+$",  # Task
            r"^EP-[0-9]+$",  # Epic
            r"^ISS-[0-9]+$",  # Issue
            r"^PR-[0-9]+$",  # Pull Request
            r"^PROJ-[0-9]+$",  # Project
        ]

        for ref_id in ids:
            if not any(re.match(pattern, ref_id) for pattern in valid_patterns):
                result.add_error(
                    f"Invalid reference ID format in {field_name}: {ref_id}"
                )

    def _validate_model_instance(self, instance, result: ValidationResult) -> None:
        """Additional validation on model instance."""
        # Check for logical consistency
        if hasattr(instance, "actual_hours") and hasattr(instance, "estimated_hours"):
            if (
                instance.actual_hours
                and instance.estimated_hours
                and instance.actual_hours > instance.estimated_hours * 3
            ):
                result.add_warning("Actual hours significantly exceed estimate (>300%)")

        # Check date consistency
        if hasattr(instance, "due_date") and instance.due_date:
            if instance.due_date < date.today():
                result.add_warning("Due date is in the past")

    def _preprocess_datetime_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess datetime string fields."""
        datetime_fields = ["created_at", "updated_at", "merged_at"]
        date_fields = [
            "due_date",
            "target_date",
            "start_date",
            "end_date",
            "target_completion",
        ]

        for field in datetime_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = datetime.fromisoformat(
                        data[field].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass  # Let Pydantic handle the error

        for field in date_fields:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = date.fromisoformat(data[field])
                except ValueError:
                    pass  # Let Pydantic handle the error

        return data

    def validate_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration data."""
        # For now, basic validation - could add config schema later
        errors = []
        warnings = []

        # Check required fields
        if "version" not in config_data:
            warnings.append("Missing version field")

        # Check editor configuration
        if "editor" in config_data:
            editor_config = config_data["editor"]
            if not isinstance(editor_config, dict):
                errors.append("Editor configuration must be a dictionary")
            elif "default" not in editor_config:
                warnings.append("No default editor specified")

        # Check tasks configuration
        if "tasks" in config_data:
            tasks_config = config_data["tasks"]
            if not isinstance(tasks_config, dict):
                errors.append("Tasks configuration must be a dictionary")
            else:
                if "id_format" in tasks_config:
                    id_format = tasks_config["id_format"]
                    if not isinstance(id_format, str) or "{counter" not in id_format:
                        errors.append("Invalid task ID format")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def validate_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate template data."""
        errors = []
        warnings = []

        # Check required fields
        required_fields = ["name", "type", "content"]
        for field in required_fields:
            if field not in template_data:
                errors.append(f"Missing required field: {field}")

        # Check template type
        if "type" in template_data:
            valid_types = ["task", "issue", "epic", "pr", "project"]
            if template_data["type"] not in valid_types:
                warnings.append(f"Unknown template type: {template_data['type']}")

        # Check variables
        if "variables" in template_data:
            variables = template_data["variables"]
            if not isinstance(variables, dict):
                errors.append("Variables must be a dictionary")
            else:
                for var_name, var_config in variables.items():
                    if not isinstance(var_config, dict):
                        errors.append(
                            f"Variable '{var_name}' configuration must be a dictionary"
                        )
                    elif "description" not in var_config:
                        warnings.append(f"Variable '{var_name}' missing description")

        # Check content
        if "content" in template_data:
            content = template_data["content"]
            if not isinstance(content, str):
                errors.append("Template content must be a string")
            elif not content.strip():
                warnings.append("Template content is empty")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _validate_data(self, data: Dict[str, Any], schema_name: str) -> Dict[str, Any]:
        """Validate data against a specific schema."""
        if schema_name not in self._schemas:
            return {
                "valid": False,
                "errors": [f"Schema '{schema_name}' not found"],
                "warnings": [],
            }

        schema = self._schemas[schema_name]
        errors = []
        warnings = []

        try:
            jsonschema.validate(data, schema)
        except ValidationError as e:
            errors.append(str(e.message))

            # Add more specific error information
            if e.path:
                field_path = ".".join(str(p) for p in e.path)
                errors.append(f"Error in field: {field_path}")
        except jsonschema.SchemaError as e:
            errors.append(f"Schema error: {e.message}")

        # Additional custom validations
        if schema_name == "task":
            # Check task-specific rules
            if "dependencies" in data:
                deps = data["dependencies"]
                if deps and any(dep == data.get("id") for dep in deps):
                    errors.append("Task cannot depend on itself")

            if "parent" in data and data.get("parent") == data.get("id"):
                errors.append("Task cannot be its own parent")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def list_schemas(self) -> List[str]:
        """List available schemas."""
        return list(self._schemas.keys())

    def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get schema by name."""
        return self._schemas.get(schema_name)


def validate_project_structure(project_path: Path) -> Dict[str, Any]:
    """Validate project directory structure."""
    errors = []
    warnings = []

    # Check required directories
    from ai_trackdown_pytools.core.config import Config

    config = Config.load(project_path=project_path)
    tasks_directory = config.get("tasks.directory", "tasks")
    required_dirs = [".ai-trackdown", tasks_directory]

    for dir_name in required_dirs:
        dir_path = project_path / dir_name
        if not dir_path.exists():
            errors.append(f"Missing required directory: {dir_name}")
        elif not dir_path.is_dir():
            errors.append(f"'{dir_name}' exists but is not a directory")

    # Check required files
    required_files = [".ai-trackdown/config.yaml", ".ai-trackdown/project.yaml"]

    for file_name in required_files:
        file_path = project_path / file_name
        if not file_path.exists():
            errors.append(f"Missing required file: {file_name}")
        elif not file_path.is_file():
            errors.append(f"'{file_name}' exists but is not a file")

    # Check optional but recommended files
    recommended_files = ["README.md", ".gitignore"]

    for file_name in recommended_files:
        file_path = project_path / file_name
        if not file_path.exists():
            warnings.append(f"Recommended file missing: {file_name}")

    # Check templates directory
    templates_dir = project_path / ".ai-trackdown" / "templates"
    if templates_dir.exists():
        template_types = ["task", "issue", "epic", "pr"]
        for template_type in template_types:
            type_dir = templates_dir / template_type
            if not type_dir.exists():
                warnings.append(f"No {template_type} templates found")
            else:
                template_files = list(type_dir.glob("*.yaml"))
                if not template_files:
                    warnings.append(f"No {template_type} templates found")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_task_file(file_path: Path) -> Dict[str, Any]:
    """Validate a task file."""
    errors = []
    warnings = []

    if not file_path.exists():
        return {"valid": False, "errors": ["File does not exist"], "warnings": []}

    if not file_path.suffix == ".md":
        warnings.append("Task file should have .md extension")

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return {"valid": False, "errors": [f"Cannot read file: {e}"], "warnings": []}

    # Check for frontmatter
    if not content.startswith("---"):
        errors.append("Task file missing YAML frontmatter")
        return {"valid": False, "errors": errors, "warnings": warnings}

    # Extract and validate frontmatter
    try:
        import re

        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            errors.append("Invalid YAML frontmatter format")
            return {"valid": False, "errors": errors, "warnings": warnings}

        frontmatter_data = yaml.safe_load(match.group(1))

        # Validate frontmatter against schema
        validator = SchemaValidator()
        validation_result = validator.validate_task(frontmatter_data)

        errors.extend(validation_result.get("errors", []))
        warnings.extend(validation_result.get("warnings", []))

    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML in frontmatter: {e}")
    except Exception as e:
        errors.append(f"Error parsing frontmatter: {e}")

    return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


def validate_ticket_file(
    file_path: Path, _ticket_type: Optional[str] = None
) -> ValidationResult:
    """Validate a ticket file with comprehensive schema validation.

    Args:
        file_path: Path to the ticket file
        ticket_type: Optional explicit ticket type

    Returns:
        ValidationResult with detailed validation information
    """
    from ai_trackdown_pytools.utils.frontmatter import parse_ticket_file

    result = ValidationResult()

    if not file_path.exists():
        result.add_error("File does not exist")
        return result

    if file_path.suffix != ".md":
        result.add_warning("Ticket file should have .md extension")

    try:
        frontmatter_data, content, parse_result = parse_ticket_file(
            file_path, validate=True
        )
        result.merge(parse_result)

        # Additional file-specific validations
        if not content.strip():
            result.add_warning("Ticket file has no content after frontmatter")

        # Check file naming convention
        if frontmatter_data.get("id"):
            expected_filename = frontmatter_data["id"].lower() + ".md"
            if file_path.name.lower() != expected_filename:
                result.add_warning(
                    f"File name '{file_path.name}' doesn't match ticket ID '{frontmatter_data['id']}'"
                )

    except Exception as e:
        result.add_error(f"Error validating file: {e}")

    return result


def validate_id_format(ticket_id: str, ticket_type: str) -> ValidationResult:
    """Validate ticket ID format.

    Args:
        ticket_id: Ticket ID to validate
        ticket_type: Type of ticket

    Returns:
        ValidationResult
    """
    result = ValidationResult()

    expected_pattern = get_id_pattern_for_type(ticket_type)
    if not re.match(expected_pattern, ticket_id):
        result.add_error(
            f"ID '{ticket_id}' doesn't match expected pattern {expected_pattern} for {ticket_type}"
        )

    return result


def validate_relationships(tickets: List[Dict[str, Any]]) -> ValidationResult:
    """Validate relationships between multiple tickets.

    Args:
        tickets: List of ticket data dictionaries

    Returns:
        ValidationResult
    """
    result = ValidationResult()

    # Create ID lookup
    ticket_ids = {ticket.get("id") for ticket in tickets if ticket.get("id")}

    for ticket in tickets:
        ticket_id = ticket.get("id")
        if not ticket_id:
            continue

        # Check dependencies exist
        dependencies = ticket.get("dependencies", [])
        for dep_id in dependencies:
            if dep_id not in ticket_ids:
                result.add_warning(
                    f"Ticket {ticket_id} depends on non-existent ticket {dep_id}"
                )

        # Check parent exists
        parent_id = ticket.get("parent")
        if parent_id and parent_id not in ticket_ids:
            result.add_warning(
                f"Ticket {ticket_id} has non-existent parent {parent_id}"
            )

        # Check child relationships
        child_fields = ["child_issues", "child_tasks"]
        for field in child_fields:
            children = ticket.get(field, [])
            for child_id in children:
                if child_id not in ticket_ids:
                    result.add_warning(
                        f"Ticket {ticket_id} references non-existent child {child_id}"
                    )

    # Check for circular dependencies (simple implementation)
    _check_circular_dependencies_deep(tickets, result)

    return result


def _check_circular_dependencies_deep(
    tickets: List[Dict[str, Any]], result: ValidationResult
) -> None:
    """Check for circular dependencies in ticket relationships."""
    # Build dependency graph
    dependencies = {}
    for ticket in tickets:
        ticket_id = ticket.get("id")
        if ticket_id:
            dependencies[ticket_id] = ticket.get("dependencies", [])

    # Check for cycles using DFS
    visited = set()
    rec_stack = set()

    def has_cycle(node: str) -> bool:
        if node in rec_stack:
            return True
        if node in visited:
            return False

        visited.add(node)
        rec_stack.add(node)

        for neighbor in dependencies.get(node, []):
            if neighbor in dependencies and has_cycle(neighbor):
                return True

        rec_stack.remove(node)
        return False

    for ticket_id in dependencies:
        if ticket_id not in visited:
            if has_cycle(ticket_id):
                result.add_error(
                    f"Circular dependency detected involving ticket {ticket_id}"
                )


# Convenience functions for validation
def validate_task_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate task data."""
    validator = SchemaValidator()
    return validator.validate_ticket(data, "task")


def validate_epic_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate epic data."""
    validator = SchemaValidator()
    return validator.validate_ticket(data, "epic")


def validate_issue_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate issue data."""
    validator = SchemaValidator()
    return validator.validate_ticket(data, "issue")


def validate_pr_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate pull request data."""
    validator = SchemaValidator()
    return validator.validate_ticket(data, "pr")


def validate_project_data(data: Dict[str, Any]) -> ValidationResult:
    """Validate project data."""
    validator = SchemaValidator()
    return validator.validate_ticket(data, "project")
