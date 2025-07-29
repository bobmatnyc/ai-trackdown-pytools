"""Exceptions for AI Trackdown PyTools."""


class TaskError(Exception):
    """Exception raised for task-related errors."""

    pass


class ProjectError(Exception):
    """Exception raised for project-related errors."""

    pass


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""

    pass


class ValidationError(Exception):
    """Exception raised for validation errors."""

    pass


class TemplateError(Exception):
    """Exception raised for template-related errors."""

    pass
