"""Utility functions for ticket type inference and management."""

from typing import Optional

# Mapping of prefixes to ticket types
PREFIX_TO_TYPE = {
    "EP": "epic",
    "ISS": "issue",
    "BUG": "bug",
    "TSK": "task",
    "PR": "pr",
    "COM": "comment",
}

# Mapping of ticket types to prefixes
TYPE_TO_PREFIX = {
    "epic": "EP",
    "issue": "ISS",
    "bug": "BUG",
    "task": "TSK",
    "pr": "PR",
    "comment": "COM",
}


def infer_ticket_type(ticket_id: str) -> Optional[str]:
    """
    Infer ticket type from ticket ID based on prefix.

    Args:
        ticket_id: Ticket ID like "EP-001", "ISS-002", "BUG-003", "TSK-004", "PR-005", "COM-006"

    Returns:
        Ticket type ("epic", "issue", "bug", "task", "pr", "comment") or None if invalid

    Examples:
        >>> infer_ticket_type("EP-001")
        'epic'
        >>> infer_ticket_type("iss-002")  # Case insensitive
        'issue'
        >>> infer_ticket_type("BUG-003")
        'bug'
        >>> infer_ticket_type("TSK-004")
        'task'
        >>> infer_ticket_type("PR-005")
        'pr'
        >>> infer_ticket_type("COM-006")
        'comment'
        >>> infer_ticket_type("INVALID-007")
        None
        >>> infer_ticket_type("EP001")  # Missing hyphen
        None
    """
    if not ticket_id or not isinstance(ticket_id, str):
        return None

    # Split by hyphen
    parts = ticket_id.split("-", 1)
    if len(parts) != 2:
        return None

    prefix = parts[0].upper()
    number_part = parts[1]

    # Validate number part contains digits
    if not number_part or not any(c.isdigit() for c in number_part):
        return None

    # Look up the type
    return PREFIX_TO_TYPE.get(prefix)


def get_ticket_prefix(ticket_type: str) -> str:
    """
    Get the ticket prefix for a given ticket type.

    Args:
        ticket_type: Ticket type ("epic", "issue", "bug", "task", "pr", "comment")

    Returns:
        Ticket prefix (e.g., "EP", "ISS", "BUG", "TSK", "PR", "COM")

    Raises:
        ValueError: If ticket_type is not recognized

    Examples:
        >>> get_ticket_prefix("epic")
        'EP'
        >>> get_ticket_prefix("issue")
        'ISS'
        >>> get_ticket_prefix("bug")
        'BUG'
        >>> get_ticket_prefix("task")
        'TSK'
        >>> get_ticket_prefix("pr")
        'PR'
        >>> get_ticket_prefix("comment")
        'COM'
        >>> get_ticket_prefix("invalid")
        Traceback (most recent call last):
        ...
        ValueError: Unknown ticket type: invalid
    """
    if not ticket_type or not isinstance(ticket_type, str):
        raise ValueError(f"Invalid ticket type: {ticket_type}")

    ticket_type_lower = ticket_type.lower()

    if ticket_type_lower not in TYPE_TO_PREFIX:
        raise ValueError(f"Unknown ticket type: {ticket_type}")

    return TYPE_TO_PREFIX[ticket_type_lower]


def is_valid_ticket_id(ticket_id: str) -> bool:
    """
    Check if a ticket ID is valid (has a recognized prefix).

    Args:
        ticket_id: Ticket ID to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> is_valid_ticket_id("EP-001")
        True
        >>> is_valid_ticket_id("INVALID-001")
        False
    """
    return infer_ticket_type(ticket_id) is not None


def normalize_ticket_id(ticket_id: str) -> Optional[str]:
    """
    Normalize a ticket ID to uppercase prefix format.

    Args:
        ticket_id: Ticket ID to normalize

    Returns:
        Normalized ticket ID or None if invalid

    Examples:
        >>> normalize_ticket_id("ep-001")
        'EP-001'
        >>> normalize_ticket_id("ISS-002")
        'ISS-002'
        >>> normalize_ticket_id("invalid-003")
        None
    """
    if not ticket_id or not isinstance(ticket_id, str):
        return None

    # Split by hyphen
    parts = ticket_id.split("-", 1)
    if len(parts) != 2:
        return None

    prefix = parts[0].upper()
    number_part = parts[1]

    # Check if it's a valid prefix
    if prefix not in PREFIX_TO_TYPE:
        return None

    return f"{prefix}-{number_part}"
