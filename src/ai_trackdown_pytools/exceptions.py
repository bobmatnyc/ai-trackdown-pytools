"""Comprehensive exception hierarchy for AI Trackdown PyTools.

This module provides a complete exception hierarchy with meaningful error messages,
context information, and recovery suggestions. It follows Python best practices
for exception handling and provides a consistent error experience across the codebase.

WHY: A well-designed exception hierarchy is crucial for:
- Providing clear, actionable error messages to users
- Enabling proper error recovery and retry logic
- Facilitating debugging and troubleshooting
- Maintaining consistency across the codebase
"""

from pathlib import Path
from typing import Any, Dict, List, Optional


class AiTrackdownError(Exception):
    """Base exception for all AI Trackdown errors.

    WHY: Provides a common base for all exceptions, allowing callers to catch
    all AI Trackdown errors with a single except clause. Includes context
    information and recovery suggestions to help users resolve issues.

    DESIGN DECISION: All exceptions include:
    - A clear error message
    - Optional context information
    - Optional recovery suggestions
    - Optional error code for programmatic handling
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        suggestions: Optional[List[str]] = None,
        error_code: Optional[str] = None,
    ):
        """Initialize the base exception with rich context.

        Args:
            message: The primary error message
            context: Additional context information
            suggestions: Recovery suggestions for the user
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.suggestions = suggestions or []
        self.error_code = error_code

    def __str__(self) -> str:
        """Return a formatted error message with suggestions."""
        parts = [self.message]

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")

        if self.suggestions:
            parts.append("Suggestions:")
            for suggestion in self.suggestions:
                parts.append(f"  - {suggestion}")

        return "\n".join(parts)


class ConfigurationError(AiTrackdownError):
    """Raised when configuration is invalid or missing.

    WHY: Configuration errors are common and need clear messaging to help
    users fix their setup. This exception provides specific guidance on
    configuration issues.
    """

    def __init__(
        self,
        message: str,
        config_file: Optional[Path] = None,
        missing_fields: Optional[List[str]] = None,
        invalid_values: Optional[Dict[str, Any]] = None,
    ):
        """Initialize configuration error with specific details.

        Args:
            message: The error message
            config_file: Path to the problematic config file
            missing_fields: List of missing required fields
            invalid_values: Dictionary of invalid field values
        """
        context = {}
        suggestions = []

        if config_file:
            context["config_file"] = str(config_file)
            if not config_file.exists():
                suggestions.append(
                    "Run 'aitrackdown init' to create a default configuration"
                )

        if missing_fields:
            context["missing_fields"] = ", ".join(missing_fields)
            suggestions.append(
                f"Add the missing fields to your configuration: {', '.join(missing_fields)}"
            )

        if invalid_values:
            context["invalid_values"] = invalid_values
            suggestions.append("Check the documentation for valid configuration values")

        super().__init__(message, context, suggestions, "CONFIG_ERROR")
        self.config_file = config_file
        self.missing_fields = missing_fields
        self.invalid_values = invalid_values


class ValidationError(AiTrackdownError):
    """Raised when data validation fails.

    WHY: Data validation errors need detailed information about what failed
    to help users fix their input. This exception provides field-level
    error details.
    """

    def __init__(
        self,
        message: str,
        field_errors: Optional[Dict[str, str]] = None,
        schema_name: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """Initialize validation error with field details.

        Args:
            message: The error message
            field_errors: Dictionary of field-specific errors
            schema_name: Name of the schema that failed validation
            data: The data that failed validation
        """
        context = {}
        suggestions = []

        if field_errors:
            context["field_errors"] = field_errors
            for field, error in field_errors.items():
                suggestions.append(f"Fix {field}: {error}")

        if schema_name:
            context["schema"] = schema_name
            suggestions.append(f"Check the {schema_name} schema documentation")

        super().__init__(message, context, suggestions, "VALIDATION_ERROR")
        self.field_errors = field_errors
        self.schema_name = schema_name
        self.data = data


class FileOperationError(AiTrackdownError):
    """Raised when file operations fail.

    WHY: File I/O errors are common and can have various causes (permissions,
    disk space, locks). This exception helps diagnose and recover from
    file operation failures.
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize file operation error with details.

        Args:
            message: The error message
            file_path: Path to the file that caused the error
            operation: The operation that failed (read, write, delete, etc.)
            original_error: The original exception if any
        """
        context = {}
        suggestions = []

        if file_path:
            context["file"] = str(file_path)

            if operation == "read" and not file_path.exists():
                suggestions.append(f"Ensure the file exists: {file_path}")
            elif operation == "write":
                parent = file_path.parent
                if not parent.exists():
                    suggestions.append(f"Create the parent directory: {parent}")
                else:
                    suggestions.append(f"Check write permissions for: {parent}")
                    suggestions.append("Check available disk space")
            elif operation == "delete":
                suggestions.append(f"Check delete permissions for: {file_path}")

        if operation:
            context["operation"] = operation

        if original_error:
            context["original_error"] = str(original_error)
            if "Permission" in str(original_error):
                suggestions.append("Check file/directory permissions")
            elif "No space" in str(original_error):
                suggestions.append("Free up disk space")
            elif "locked" in str(original_error).lower():
                suggestions.append("Ensure the file is not open in another program")

        super().__init__(message, context, suggestions, "FILE_ERROR")
        self.file_path = file_path
        self.operation = operation
        self.original_error = original_error


class GitOperationError(AiTrackdownError):
    """Raised when Git operations fail.

    WHY: Git operations can fail for many reasons (uncommitted changes,
    conflicts, missing remotes). This exception provides Git-specific
    context and recovery steps.
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        repository: Optional[Path] = None,
        branch: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize Git operation error with details.

        Args:
            message: The error message
            operation: The Git operation that failed
            repository: Path to the repository
            branch: The branch involved in the operation
            original_error: The original Git exception
        """
        context = {}
        suggestions = []

        if operation:
            context["operation"] = operation

        if repository:
            context["repository"] = str(repository)
            if not (repository / ".git").exists():
                suggestions.append("Initialize a Git repository: git init")

        if branch:
            context["branch"] = branch

        if original_error:
            error_str = str(original_error)
            context["git_error"] = error_str

            if "uncommitted" in error_str.lower():
                suggestions.append("Commit or stash your changes first")
            elif "conflict" in error_str.lower():
                suggestions.append("Resolve merge conflicts before continuing")
            elif "remote" in error_str.lower():
                suggestions.append("Check your remote configuration: git remote -v")
            elif "permission" in error_str.lower():
                suggestions.append("Check repository permissions or SSH keys")

        super().__init__(message, context, suggestions, "GIT_ERROR")
        self.operation = operation
        self.repository = repository
        self.branch = branch
        self.original_error = original_error


class NetworkError(AiTrackdownError):
    """Raised when network operations fail.

    WHY: Network errors are often transient and may benefit from retry logic.
    This exception provides network-specific context and retry guidance.
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        retry_after: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize network error with details.

        Args:
            message: The error message
            url: The URL that failed
            status_code: HTTP status code if applicable
            retry_after: Seconds to wait before retrying
            original_error: The original network exception
        """
        context = {}
        suggestions = []

        if url:
            context["url"] = url

        if status_code:
            context["status_code"] = status_code
            if status_code == 401:
                suggestions.append("Check your authentication credentials")
            elif status_code == 403:
                suggestions.append("Check your permissions or API token")
            elif status_code == 404:
                suggestions.append("Verify the URL is correct")
            elif status_code == 429:
                suggestions.append("You've hit a rate limit, wait before retrying")
            elif status_code >= 500:
                suggestions.append("The server is having issues, try again later")

        if retry_after:
            context["retry_after"] = f"{retry_after} seconds"
            suggestions.append(f"Wait {retry_after} seconds before retrying")

        if original_error:
            error_str = str(original_error)
            if "timeout" in error_str.lower():
                suggestions.append("Check your network connection")
                suggestions.append("Try increasing the timeout value")
            elif "connection" in error_str.lower():
                suggestions.append("Check your internet connection")
                suggestions.append("Check if the service is available")

        super().__init__(message, context, suggestions, "NETWORK_ERROR")
        self.url = url
        self.status_code = status_code
        self.retry_after = retry_after
        self.original_error = original_error


class TicketNotFoundError(AiTrackdownError):
    """Raised when a ticket cannot be found.

    WHY: Ticket lookup failures are common and need specific guidance on
    valid ticket formats and searching for existing tickets.
    """

    def __init__(
        self,
        ticket_id: str,
        ticket_type: Optional[str] = None,
        search_path: Optional[Path] = None,
    ):
        """Initialize ticket not found error.

        Args:
            ticket_id: The ticket ID that wasn't found
            ticket_type: The type of ticket being searched for
            search_path: The path where the search was performed
        """
        message = f"Ticket not found: {ticket_id}"
        context = {"ticket_id": ticket_id}
        suggestions = [
            "Check the ticket ID is correct",
            "Use 'aitrackdown list' to see available tickets",
            "Use 'aitrackdown search' to find tickets by content",
        ]

        if ticket_type:
            context["ticket_type"] = ticket_type
            suggestions.append(f"Ensure the ticket is a {ticket_type}")

        if search_path:
            context["search_path"] = str(search_path)
            suggestions.append(f"Check tickets exist in: {search_path}")

        super().__init__(message, context, suggestions, "TICKET_NOT_FOUND")
        self.ticket_id = ticket_id
        self.ticket_type = ticket_type
        self.search_path = search_path


class DependencyError(AiTrackdownError):
    """Raised when required dependencies are missing or incompatible.

    WHY: Dependency issues need clear instructions on how to install or
    update the required packages.
    """

    def __init__(
        self,
        message: str,
        missing_packages: Optional[List[str]] = None,
        incompatible_versions: Optional[Dict[str, str]] = None,
        optional_feature: Optional[str] = None,
    ):
        """Initialize dependency error with details.

        Args:
            message: The error message
            missing_packages: List of missing packages
            incompatible_versions: Dict of package -> required version
            optional_feature: The optional feature that requires the dependency
        """
        context = {}
        suggestions = []

        if missing_packages:
            context["missing"] = ", ".join(missing_packages)
            pip_cmd = f"pip install {' '.join(missing_packages)}"
            suggestions.append(f"Install missing packages: {pip_cmd}")

        if incompatible_versions:
            context["incompatible"] = incompatible_versions
            for pkg, version in incompatible_versions.items():
                suggestions.append(f"Update {pkg} to version {version}")

        if optional_feature:
            context["feature"] = optional_feature
            suggestions.append(f"This is optional for the {optional_feature} feature")
            suggestions.append(
                f"Install extras: pip install ai-trackdown-pytools[{optional_feature}]"
            )

        super().__init__(message, context, suggestions, "DEPENDENCY_ERROR")
        self.missing_packages = missing_packages
        self.incompatible_versions = incompatible_versions
        self.optional_feature = optional_feature


class PermissionError(AiTrackdownError):
    """Raised when permission is denied for an operation.

    WHY: Permission errors need platform-specific guidance on how to
    fix file permissions or elevate privileges.
    """

    def __init__(
        self,
        message: str,
        path: Optional[Path] = None,
        operation: Optional[str] = None,
        required_permission: Optional[str] = None,
    ):
        """Initialize permission error with details.

        Args:
            message: The error message
            path: The path where permission was denied
            operation: The operation that was denied
            required_permission: The permission that's required
        """
        context = {}
        suggestions = []

        if path:
            context["path"] = str(path)
            suggestions.append(f"Check permissions: ls -la {path}")

            if path.is_dir():
                suggestions.append(f"Fix directory permissions: chmod 755 {path}")
            else:
                suggestions.append(f"Fix file permissions: chmod 644 {path}")

        if operation:
            context["operation"] = operation
            if operation == "write":
                suggestions.append("Ensure you have write access to the directory")
            elif operation == "execute":
                suggestions.append("Add execute permission: chmod +x <file>")

        if required_permission:
            context["required"] = required_permission
            if required_permission == "admin":
                suggestions.append("Run the command with administrator privileges")
                suggestions.append("On Unix: use 'sudo'")
                suggestions.append("On Windows: run as Administrator")

        super().__init__(message, context, suggestions, "PERMISSION_ERROR")
        self.path = path
        self.operation = operation
        self.required_permission = required_permission


class TaskError(AiTrackdownError):
    """Raised for task-related errors.

    WHY: Task operations have specific failure modes that need targeted
    error messages and recovery suggestions.
    """

    def __init__(
        self,
        message: str,
        task_id: Optional[str] = None,
        task_file: Optional[Path] = None,
        operation: Optional[str] = None,
    ):
        """Initialize task error with details.

        Args:
            message: The error message
            task_id: The task ID involved
            task_file: Path to the task file
            operation: The operation that failed
        """
        context = {}
        suggestions = []

        if task_id:
            context["task_id"] = task_id

        if task_file:
            context["file"] = str(task_file)
            if not task_file.exists():
                suggestions.append(f"Task file not found: {task_file}")
                suggestions.append("Use 'aitrackdown create' to create a new task")

        if operation:
            context["operation"] = operation
            if operation == "parse":
                suggestions.append("Check the task file format (YAML frontmatter)")
                suggestions.append("Validate YAML syntax at yamllint.com")
            elif operation == "transition":
                suggestions.append("Check valid status transitions")
                suggestions.append(
                    "Use 'aitrackdown status <task>' to see current state"
                )

        super().__init__(message, context, suggestions, "TASK_ERROR")
        self.task_id = task_id
        self.task_file = task_file
        self.operation = operation


class ProjectError(AiTrackdownError):
    """Raised for project-related errors.

    WHY: Project initialization and management have specific requirements
    that need clear error messages when not met.
    """

    def __init__(
        self,
        message: str,
        project_path: Optional[Path] = None,
        missing_components: Optional[List[str]] = None,
    ):
        """Initialize project error with details.

        Args:
            message: The error message
            project_path: Path to the project
            missing_components: List of missing project components
        """
        context = {}
        suggestions = []

        if project_path:
            context["project"] = str(project_path)
            if not (project_path / ".ai-trackdown").exists():
                suggestions.append("Initialize a project: aitrackdown init")

        if missing_components:
            context["missing"] = ", ".join(missing_components)
            suggestions.append("Run 'aitrackdown init' to create missing components")
            for component in missing_components:
                if component == "config":
                    suggestions.append("Create config: aitrackdown init --config-only")
                elif component == "tickets":
                    suggestions.append("Create tickets directory manually or run init")

        super().__init__(message, context, suggestions, "PROJECT_ERROR")
        self.project_path = project_path
        self.missing_components = missing_components


class TemplateError(AiTrackdownError):
    """Raised for template-related errors.

    WHY: Template processing errors need specific guidance on template
    syntax and available variables.
    """

    def __init__(
        self,
        message: str,
        template_name: Optional[str] = None,
        template_path: Optional[Path] = None,
        missing_variables: Optional[List[str]] = None,
    ):
        """Initialize template error with details.

        Args:
            message: The error message
            template_name: Name of the template
            template_path: Path to the template file
            missing_variables: List of missing template variables
        """
        context = {}
        suggestions = []

        if template_name:
            context["template"] = template_name

        if template_path:
            context["path"] = str(template_path)
            if not template_path.exists():
                suggestions.append(f"Template not found: {template_path}")
                suggestions.append(
                    "Use 'aitrackdown template list' to see available templates"
                )

        if missing_variables:
            context["missing_vars"] = ", ".join(missing_variables)
            suggestions.append(
                f"Provide missing variables: {', '.join(missing_variables)}"
            )
            suggestions.append("Check template documentation for required variables")

        super().__init__(message, context, suggestions, "TEMPLATE_ERROR")
        self.template_name = template_name
        self.template_path = template_path
        self.missing_variables = missing_variables


# Maintain backward compatibility by importing old exception names
from .core.exceptions import ConfigError
from .core.exceptions import ProjectError as LegacyProjectError
from .core.exceptions import TaskError as LegacyTaskError
from .core.exceptions import TemplateError as LegacyTemplateError
from .core.exceptions import ValidationError as LegacyValidationError

__all__ = [
    # New comprehensive exceptions
    "AiTrackdownError",
    "ConfigurationError",
    "ValidationError",
    "FileOperationError",
    "GitOperationError",
    "NetworkError",
    "TicketNotFoundError",
    "DependencyError",
    "PermissionError",
    "TaskError",
    "ProjectError",
    "TemplateError",
    # Legacy exceptions for backward compatibility
    "ConfigError",
    "LegacyTaskError",
    "LegacyProjectError",
    "LegacyValidationError",
    "LegacyTemplateError",
]
