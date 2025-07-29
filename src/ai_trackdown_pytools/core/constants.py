"""Constants for AI Trackdown PyTools."""

from enum import Enum


class TicketType(str, Enum):
    """Ticket type enumeration."""

    EPIC = "epic"
    ISSUE = "issue"
    BUG = "bug"
    TASK = "task"
    PR = "pr"
    COMMENT = "comment"


class TicketPrefix(str, Enum):
    """Ticket prefix enumeration."""

    EPIC = "EP"
    ISSUE = "ISS"
    BUG = "BUG"
    TASK = "TSK"
    PR = "PR"
    COMMENT = "CMT"


class TicketSubdir(str, Enum):
    """Ticket subdirectory enumeration."""

    EPICS = "epics"
    ISSUES = "issues"
    BUGS = "bugs"
    TASKS = "tasks"
    PRS = "prs"
    COMMENTS = "comments"
    MISC = "misc"


class TicketStatus(str, Enum):
    """Ticket status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    CLOSED = "closed"
    TODO = "todo"
    DONE = "done"
    DRAFT = "draft"
    READY = "ready"
    MERGED = "merged"


class TicketPriority(str, Enum):
    """Ticket priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Priority ordering for sorting
PRIORITY_ORDER = {
    TicketPriority.CRITICAL: 4,
    TicketPriority.HIGH: 3,
    TicketPriority.MEDIUM: 2,
    TicketPriority.LOW: 1,
}


# Mapping from prefix to subdirectory
PREFIX_TO_SUBDIR = {
    TicketPrefix.EPIC: TicketSubdir.EPICS,
    TicketPrefix.ISSUE: TicketSubdir.ISSUES,
    TicketPrefix.BUG: TicketSubdir.BUGS,
    TicketPrefix.TASK: TicketSubdir.TASKS,
    TicketPrefix.PR: TicketSubdir.PRS,
    TicketPrefix.COMMENT: TicketSubdir.COMMENTS,
}


# Mapping from type to prefix
TYPE_TO_PREFIX = {
    TicketType.EPIC: TicketPrefix.EPIC,
    TicketType.ISSUE: TicketPrefix.ISSUE,
    TicketType.BUG: TicketPrefix.BUG,
    TicketType.TASK: TicketPrefix.TASK,
    TicketType.PR: TicketPrefix.PR,
    TicketType.COMMENT: TicketPrefix.COMMENT,
}


# Valid statuses for different ticket types
VALID_STATUSES = {
    TicketType.TASK: [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.COMPLETED,
        TicketStatus.CANCELLED,
        TicketStatus.BLOCKED,
    ],
    TicketType.ISSUE: [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.COMPLETED,
        TicketStatus.CANCELLED,
        TicketStatus.BLOCKED,
    ],
    TicketType.BUG: [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.COMPLETED,
        TicketStatus.CANCELLED,
        TicketStatus.BLOCKED,
        TicketStatus.CLOSED,
    ],
    TicketType.EPIC: [
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.COMPLETED,
        TicketStatus.CANCELLED,
        TicketStatus.BLOCKED,
    ],
    TicketType.PR: [
        TicketStatus.DRAFT,
        TicketStatus.OPEN,
        TicketStatus.READY,
        TicketStatus.MERGED,
        TicketStatus.CLOSED,
    ],
}


# Default values
DEFAULT_STATUS = TicketStatus.OPEN
DEFAULT_PRIORITY = TicketPriority.MEDIUM
DEFAULT_TICKET_TYPE = TicketType.TASK


class BugSeverity(str, Enum):
    """Bug severity enumeration."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
