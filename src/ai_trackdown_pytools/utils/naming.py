"""File naming utilities for AI Trackdown PyTools."""

import re
from typing import Optional


def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    Sanitize a string for use as a filename.

    Args:
        name: The string to sanitize
        max_length: Maximum length of the filename

    Returns:
        A sanitized filename string
    """
    # Remove or replace invalid characters
    # Keep alphanumeric, spaces, hyphens, underscores, and dots
    sanitized = re.sub(r"[^\w\s\-_\.]", "", name)

    # Replace multiple spaces with single hyphen
    sanitized = re.sub(r"\s+", "-", sanitized)

    # Replace multiple hyphens with single hyphen
    sanitized = re.sub(r"-+", "-", sanitized)

    # Remove leading/trailing hyphens and spaces
    sanitized = sanitized.strip(" -_.")

    # Ensure filename is not empty
    if not sanitized:
        sanitized = "untitled"

    # Truncate to max length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip(" -_.")

    return sanitized


def create_safe_task_filename(task_id: str, title: Optional[str] = None) -> str:
    """
    Create a safe filename for a task.

    Args:
        task_id: The task ID (e.g., TSK-0001)
        title: The task title (optional)

    Returns:
        A safe filename like 'TSK-0001.md' or 'TSK-0001-task-title.md'
    """
    if title:
        safe_title = sanitize_filename(title)
        # Ensure no double dashes
        filename = f"{task_id}-{safe_title}.md"
        # Replace any double dashes with single dash
        filename = re.sub(r"-+", "-", filename)
        return filename
    else:
        return f"{task_id}.md"


def create_safe_epic_filename(epic_id: str, title: Optional[str] = None) -> str:
    """
    Create a safe filename for an epic.

    Args:
        epic_id: The epic ID (e.g., EP-0001)
        title: The epic title (optional)

    Returns:
        A safe filename like 'EP-0001.md' or 'EP-0001-epic-title.md'
    """
    if title:
        safe_title = sanitize_filename(title)
        filename = f"{epic_id}-{safe_title}.md"
        # Replace any double dashes with single dash
        filename = re.sub(r"-+", "-", filename)
        return filename
    else:
        return f"{epic_id}.md"


def create_safe_issue_filename(issue_id: str, title: Optional[str] = None) -> str:
    """
    Create a safe filename for an issue.

    Args:
        issue_id: The issue ID (e.g., ISS-0001)
        title: The issue title (optional)

    Returns:
        A safe filename like 'ISS-0001.md' or 'ISS-0001-issue-title.md'
    """
    if title:
        safe_title = sanitize_filename(title)
        filename = f"{issue_id}-{safe_title}.md"
        # Replace any double dashes with single dash
        filename = re.sub(r"-+", "-", filename)
        return filename
    else:
        return f"{issue_id}.md"


def extract_id_from_filename(filename: str) -> Optional[str]:
    """
    Extract the ID from a filename.

    Args:
        filename: The filename to extract from

    Returns:
        The ID if found, None otherwise
    """
    # Match patterns like TSK-0001, EP-0001, ISS-0001, PR-0001
    match = re.match(r"^([A-Z]+-\d+)", filename)
    return match.group(1) if match else None
