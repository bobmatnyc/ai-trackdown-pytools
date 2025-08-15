"""YAML frontmatter parsing utilities for AI Trackdown PyTools."""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from yaml.dumper import SafeDumper
from yaml.loader import SafeLoader

from ai_trackdown_pytools.utils.validation import SchemaValidator, ValidationResult


class FrontmatterError(Exception):
    """Frontmatter parsing error."""

    pass


class FrontmatterParser:
    """YAML frontmatter parser with validation."""

    def __init__(self, validate_schema: bool = True):
        """Initialize frontmatter parser.

        Args:
            validate_schema: Whether to validate against schema after parsing
        """
        self.validate_schema = validate_schema
        self.validator = SchemaValidator() if validate_schema else None

    def parse_file(
        self, file_path: Path
    ) -> Tuple[Dict[str, Any], str, ValidationResult]:
        """Parse frontmatter from a markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Tuple of (frontmatter_data, content, validation_result)

        Raises:
            FrontmatterError: If file cannot be read or parsed
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            raise FrontmatterError(f"Cannot read file {file_path}: {e}") from e

        return self.parse_string(content)

    def parse_string(
        self, content: str
    ) -> Tuple[Dict[str, Any], str, ValidationResult]:
        """Parse frontmatter from a string.

        Args:
            content: Markdown content with YAML frontmatter

        Returns:
            Tuple of (frontmatter_data, markdown_content, validation_result)

        Raises:
            FrontmatterError: If frontmatter cannot be parsed
        """
        validation_result = ValidationResult()

        # Extract frontmatter using regex
        frontmatter_data, markdown_content = self._extract_frontmatter(content)

        if not frontmatter_data:
            validation_result.add_error("No YAML frontmatter found")
            return {}, content, validation_result

        # Parse YAML
        try:
            parsed_data = yaml.load(frontmatter_data, Loader=SafeLoader)
            if not isinstance(parsed_data, dict):
                validation_result.add_error(
                    "Frontmatter must be a YAML object/dictionary"
                )
                return {}, markdown_content, validation_result
        except yaml.YAMLError as e:
            validation_result.add_error(f"Invalid YAML in frontmatter: {e}")
            return {}, markdown_content, validation_result

        # Validate against schema if enabled
        if self.validate_schema and self.validator:
            ticket_type = self._detect_ticket_type(parsed_data)
            if ticket_type:
                schema_validation = self.validator.validate_ticket(
                    parsed_data, ticket_type
                )
                validation_result.merge(schema_validation)
            else:
                validation_result.add_warning(
                    "Could not detect ticket type for schema validation"
                )

        return parsed_data, markdown_content, validation_result

    def write_file(
        self,
        file_path: Path,
        frontmatter_data: Dict[str, Any],
        content: str,
        validate: bool = True,
    ) -> ValidationResult:
        """Write frontmatter and content to a markdown file.

        Args:
            file_path: Path to write the file
            frontmatter_data: Frontmatter data dictionary
            content: Markdown content
            validate: Whether to validate before writing

        Returns:
            ValidationResult indicating success/failure

        Raises:
            FrontmatterError: If file cannot be written
        """
        validation_result = ValidationResult()

        # Validate before writing if requested
        if validate and self.validate_schema and self.validator:
            ticket_type = self._detect_ticket_type(frontmatter_data)
            if ticket_type:
                schema_validation = self.validator.validate_ticket(
                    frontmatter_data, ticket_type
                )
                validation_result.merge(schema_validation)
                if not schema_validation.valid:
                    validation_result.add_error("Validation failed, file not written")
                    return validation_result

        # Generate full content
        full_content = self._generate_content(frontmatter_data, content)

        # Write file
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)
        except Exception as e:
            validation_result.add_error(f"Cannot write file {file_path}: {e}")

        return validation_result

    def update_frontmatter(
        self, file_path: Path, updates: Dict[str, Any], validate: bool = True
    ) -> ValidationResult:
        """Update frontmatter in an existing file.

        Args:
            file_path: Path to the file
            updates: Dictionary of field updates
            validate: Whether to validate after updating

        Returns:
            ValidationResult indicating success/failure
        """
        # Parse existing file
        try:
            frontmatter_data, content, parse_result = self.parse_file(file_path)
            if not parse_result.valid:
                return parse_result
        except FrontmatterError as e:
            result = ValidationResult()
            result.add_error(str(e))
            return result

        # Apply updates
        frontmatter_data.update(updates)

        # Write back
        return self.write_file(file_path, frontmatter_data, content, validate)

    def _extract_frontmatter(self, content: str) -> Tuple[Optional[str], str]:
        """Extract YAML frontmatter from markdown content.

        Args:
            content: Full markdown content

        Returns:
            Tuple of (frontmatter_yaml, remaining_content)
        """
        # Match YAML frontmatter pattern
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return None, content

        frontmatter_yaml = match.group(1)
        remaining_content = match.group(2)

        return frontmatter_yaml, remaining_content

    def _generate_content(self, frontmatter_data: Dict[str, Any], content: str) -> str:
        """Generate full markdown content with frontmatter.

        Args:
            frontmatter_data: Frontmatter data dictionary
            content: Markdown content

        Returns:
            Full markdown content with YAML frontmatter
        """
        # Convert to YAML with custom formatting
        yaml_content = yaml.dump(
            frontmatter_data,
            Dumper=SafeDumper,
            default_flow_style=False,
            sort_keys=True,
            allow_unicode=True,
            width=120,
        )

        # Ensure content doesn't start with newlines
        content = content.lstrip("\n")

        return f"---\n{yaml_content}---\n\n{content}"

    def _detect_ticket_type(self, frontmatter_data: Dict[str, Any]) -> Optional[str]:
        """Detect ticket type from frontmatter data.

        Args:
            frontmatter_data: Parsed frontmatter data

        Returns:
            Detected ticket type or None
        """
        # Check explicit type field
        if "type" in frontmatter_data:
            return frontmatter_data["type"].lower()

        # Detect from ID pattern
        if "id" in frontmatter_data:
            ticket_id = frontmatter_data["id"]
            if ticket_id.startswith("TSK-"):
                return "task"
            elif ticket_id.startswith("EP-"):
                return "epic"
            elif ticket_id.startswith("ISS-"):
                return "issue"
            elif ticket_id.startswith("PR-"):
                return "pr"
            elif ticket_id.startswith("PROJ-"):
                return "project"

        # Detect from fields present
        if "issue_type" in frontmatter_data:
            return "issue"
        elif "pr_type" in frontmatter_data:
            return "pr"
        elif "goal" in frontmatter_data or "business_value" in frontmatter_data:
            return "epic"
        elif "team_members" in frontmatter_data or "budget" in frontmatter_data:
            return "project"

        # Default to task
        return "task"

    def validate_frontmatter(
        self, frontmatter_data: Dict[str, Any], ticket_type: Optional[str] = None
    ) -> ValidationResult:
        """Validate frontmatter data against schema.

        Args:
            frontmatter_data: Frontmatter data to validate
            ticket_type: Optional explicit ticket type

        Returns:
            ValidationResult
        """
        if not self.validator:
            result = ValidationResult()
            result.add_warning("Schema validation disabled")
            return result

        if not ticket_type:
            ticket_type = self._detect_ticket_type(frontmatter_data)

        if not ticket_type:
            result = ValidationResult()
            result.add_error("Cannot determine ticket type for validation")
            return result

        return self.validator.validate_ticket(frontmatter_data, ticket_type)


class StatusWorkflowValidator:
    """Validates status transitions and workflow rules."""

    # Define valid status transitions for each ticket type
    STATUS_WORKFLOWS = {
        "task": {
            "open": ["in_progress", "cancelled"],
            "in_progress": ["completed", "blocked", "cancelled"],
            "blocked": ["in_progress", "cancelled"],
            "completed": [],  # Terminal state
            "cancelled": [],  # Terminal state
        },
        "epic": {
            "planning": ["in_progress", "cancelled"],
            "in_progress": ["on_hold", "completed", "cancelled"],
            "on_hold": ["in_progress", "cancelled"],
            "completed": [],
            "cancelled": [],
        },
        "issue": {
            "open": ["in_progress", "cancelled"],
            "in_progress": ["testing", "blocked", "cancelled"],
            "testing": ["completed", "in_progress"],
            "blocked": ["in_progress", "cancelled"],
            "completed": [],
            "cancelled": [],
        },
        "pr": {
            "draft": ["ready_for_review", "closed"],
            "ready_for_review": ["in_review", "draft", "closed"],
            "in_review": ["changes_requested", "approved", "closed"],
            "changes_requested": ["ready_for_review", "closed"],
            "approved": ["merged", "closed"],
            "merged": [],
            "closed": [],
        },
        "project": {
            "planning": ["active", "cancelled"],
            "active": ["on_hold", "completed", "cancelled"],
            "on_hold": ["active", "cancelled"],
            "completed": ["archived"],
            "cancelled": ["archived"],
            "archived": [],
        },
    }

    def validate_status_transition(
        self, ticket_type: str, from_status: str, to_status: str
    ) -> ValidationResult:
        """Validate a status transition.

        Args:
            ticket_type: Type of ticket
            from_status: Current status
            to_status: Target status

        Returns:
            ValidationResult
        """
        result = ValidationResult()

        if ticket_type not in self.STATUS_WORKFLOWS:
            result.add_error(f"Unknown ticket type: {ticket_type}")
            return result

        workflow = self.STATUS_WORKFLOWS[ticket_type]

        if from_status not in workflow:
            result.add_error(
                f"Invalid current status '{from_status}' for {ticket_type}"
            )
            return result

        if to_status not in workflow:
            result.add_error(f"Invalid target status '{to_status}' for {ticket_type}")
            return result

        valid_transitions = workflow[from_status]
        if to_status not in valid_transitions:
            result.add_error(
                f"Invalid status transition from '{from_status}' to '{to_status}' for {ticket_type}. "
                f"Valid transitions: {', '.join(valid_transitions) if valid_transitions else 'none (terminal state)'}"
            )

        return result

    def get_valid_transitions(self, ticket_type: str, current_status: str) -> List[str]:
        """Get valid status transitions from current status.

        Args:
            ticket_type: Type of ticket
            current_status: Current status

        Returns:
            List of valid target statuses
        """
        if ticket_type not in self.STATUS_WORKFLOWS:
            return []

        workflow = self.STATUS_WORKFLOWS[ticket_type]
        return workflow.get(current_status, [])

    def is_terminal_status(self, ticket_type: str, status: str) -> bool:
        """Check if a status is terminal (no further transitions).

        Args:
            ticket_type: Type of ticket
            status: Status to check

        Returns:
            True if status is terminal
        """
        valid_transitions = self.get_valid_transitions(ticket_type, status)
        return len(valid_transitions) == 0


def parse_ticket_file(
    file_path: Path, validate: bool = True
) -> Tuple[Dict[str, Any], str, ValidationResult]:
    """Convenience function to parse a ticket file.

    Args:
        file_path: Path to the ticket file
        validate: Whether to validate against schema

    Returns:
        Tuple of (frontmatter_data, content, validation_result)
    """
    parser = FrontmatterParser(validate_schema=validate)
    return parser.parse_file(file_path)


def validate_ticket_data(
    data: Dict[str, Any], ticket_type: Optional[str] = None
) -> ValidationResult:
    """Convenience function to validate ticket data.

    Args:
        data: Ticket data to validate
        ticket_type: Optional explicit ticket type

    Returns:
        ValidationResult
    """
    validator = SchemaValidator()

    if not ticket_type:
        parser = FrontmatterParser(validate_schema=False)
        ticket_type = parser._detect_ticket_type(data)

    if not ticket_type:
        result = ValidationResult()
        result.add_error("Cannot determine ticket type for validation")
        return result

    return validator.validate_ticket(data, ticket_type)


def write_ticket_file(
    file_path: Path,
    frontmatter_data: Dict[str, Any],
    content: str = "",
    validate: bool = True,
) -> ValidationResult:
    """Convenience function to write a ticket file.

    Args:
        file_path: Path to write the file
        frontmatter_data: Frontmatter data dictionary
        content: Markdown content (optional)
        validate: Whether to validate before writing

    Returns:
        ValidationResult indicating success/failure
    """
    parser = FrontmatterParser(validate_schema=validate)
    return parser.write_file(file_path, frontmatter_data, content, validate)
