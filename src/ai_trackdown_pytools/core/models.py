"""Pydantic models for AI Trackdown PyTools."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_serializer,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

from .constants import BugSeverity
from .workflow import (
    ResolutionType,
    UnifiedStatus,
    is_terminal_status,
    map_legacy_status,
    requires_resolution,
    workflow_state_machine,
)


# Enums for validation
class TaskStatus(str, Enum):
    """Task status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class EpicStatus(str, Enum):
    """Epic status enumeration."""

    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class IssueStatus(str, Enum):
    """Issue status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class BugStatus(str, Enum):
    """Bug status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"
    CLOSED = "closed"


class PRStatus(str, Enum):
    """Pull Request status enumeration."""

    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    IN_REVIEW = "in_review"
    CHANGES_REQUESTED = "changes_requested"
    APPROVED = "approved"
    MERGED = "merged"
    CLOSED = "closed"


class ProjectStatus(str, Enum):
    """Project status enumeration."""

    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class Priority(str, Enum):
    """Priority enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(str, Enum):
    """Issue type enumeration."""

    BUG = "bug"
    FEATURE = "feature"
    ENHANCEMENT = "enhancement"
    DOCUMENTATION = "documentation"
    QUESTION = "question"
    EPIC_TASK = "epic_task"


class PRType(str, Enum):
    """Pull Request type enumeration."""

    BUG_FIX = "bug_fix"
    FEATURE = "feature"
    BREAKING_CHANGE = "breaking_change"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    PERFORMANCE = "performance"
    OTHER = "other"


class MilestoneStatus(str, Enum):
    """Milestone status enumeration."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"


# Base model with common fields
class BaseTicketModel(BaseModel):
    """Base model for all ticket types."""

    id: Annotated[
        str, Field(pattern=r"^[A-Z]+-[0-9]+$", description="Unique identifier")
    ]
    title: Annotated[str, Field(min_length=1, max_length=300, description="Title")]
    description: str = Field("", description="Description")
    priority: Priority = Field(Priority.MEDIUM, description="Priority level")
    assignees: List[str] = Field(default_factory=list, description="Assignees")
    tags: List[str] = Field(default_factory=list, description="Tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    labels: List[str] = Field(default_factory=list, description="Labels")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Resolution tracking fields
    resolution: Optional[ResolutionType] = Field(
        None, description="Resolution type for terminal states"
    )
    resolution_comment: Optional[str] = Field(
        None, description="Additional context for resolution"
    )
    resolved_at: Optional[datetime] = Field(None, description="Timestamp when resolved")
    resolved_by: Optional[str] = Field(None, description="User who resolved the ticket")

    # State tracking fields
    status_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of status changes"
    )
    reopen_count: int = Field(0, description="Number of times ticket was reopened")

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("created_at", "updated_at", "resolved_at")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None

    @field_validator("assignees", "tags", "labels")
    @classmethod
    def ensure_unique_items(cls, v):
        """Ensure list items are unique."""
        if v:
            return list(dict.fromkeys(v))  # Preserves order while removing duplicates
        return v

    @model_validator(mode="after")
    def updated_at_after_created_at(self) -> "BaseTicketModel":
        """Ensure updated_at is not before created_at."""
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be before created_at")
        return self

    @model_validator(mode="after")
    def validate_resolution_fields(self) -> "BaseTicketModel":
        """Validate resolution-related fields.

        WHY: Ensures data integrity by validating that:
        - Resolution is only set for terminal states that require it
        - Resolution timestamp is after creation time
        - Required resolution comments are provided
        """
        if self.resolution:
            # Check if resolved_at is set and valid
            if self.resolved_at and self.resolved_at < self.created_at:
                raise ValueError("resolved_at cannot be before created_at")

            # Check if resolution requires comment
            from .workflow import resolution_requires_comment

            if (
                resolution_requires_comment(self.resolution)
                and not self.resolution_comment
            ):
                raise ValueError(f"Resolution {self.resolution} requires a comment")

        return self

    def can_transition_to(
        self,
        new_status: Union[UnifiedStatus, str],
        resolution: Optional[ResolutionType] = None,
    ) -> tuple[bool, Optional[str]]:
        """Check if transition to new status is valid.

        WHY: Enforces workflow rules by validating state transitions before
        they occur. This prevents invalid state changes and maintains data integrity.

        Args:
            new_status: Target status
            resolution: Resolution type if transitioning to terminal state

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Normalize current and new status
        if hasattr(self, "status"):
            current_unified = map_legacy_status(
                self.status.value if isinstance(self.status, Enum) else str(self.status)
            )
            new_unified = map_legacy_status(
                new_status.value if isinstance(new_status, Enum) else str(new_status)
            )

            # Use the workflow state machine to validate
            return workflow_state_machine.validate_transition(
                current_unified, new_unified, resolution
            )

        return True, None

    def transition_to(
        self,
        new_status: Union[UnifiedStatus, str],
        resolution: Optional[ResolutionType] = None,
        resolution_comment: Optional[str] = None,
        user: Optional[str] = None,
    ) -> None:
        """Transition to a new status with validation.

        WHY: Provides a safe way to change status that enforces workflow rules,
        tracks history, and updates resolution fields when needed.

        Args:
            new_status: Target status
            resolution: Resolution type for terminal states
            resolution_comment: Comment explaining the resolution
            user: User making the transition

        Raises:
            ValueError: If transition is invalid
        """
        # Validate transition
        is_valid, error_msg = self.can_transition_to(new_status, resolution)
        if not is_valid:
            raise ValueError(error_msg)

        # Normalize statuses
        old_status = self.status if hasattr(self, "status") else None
        new_unified = map_legacy_status(
            new_status.value if isinstance(new_status, Enum) else str(new_status)
        )

        # Update status
        if hasattr(self, "status"):
            self.status = new_unified

        # Update resolution fields if transitioning to terminal state
        if is_terminal_status(new_unified):
            if resolution:
                self.resolution = resolution
                self.resolution_comment = resolution_comment
                self.resolved_at = datetime.now()
                self.resolved_by = user
            elif requires_resolution(new_unified) and not self.resolution:
                raise ValueError(f"Status {new_unified} requires a resolution")

        # Track status change in history
        self.status_history.append(
            {
                "from_status": (
                    old_status.value
                    if isinstance(old_status, Enum)
                    else str(old_status)
                    if old_status
                    else None
                ),
                "to_status": new_unified.value,
                "timestamp": datetime.now().isoformat(),
                "user": user,
                "resolution": resolution.value if resolution else None,
                "comment": resolution_comment,
            }
        )

        # Update timestamps
        self.updated_at = datetime.now()

        # Track reopens
        if new_unified == UnifiedStatus.REOPENED:
            self.reopen_count += 1

    def get_comment_lock_status(self) -> tuple[bool, Optional[str]]:
        """Check if comments should be locked based on ticket status.

        WHY: Provides a centralized way to determine if comments on this
        ticket should be read-only based on the ticket's current status.
        This ensures consistent behavior across the system.

        Returns:
            Tuple of (should_lock, reason)
        """
        if hasattr(self, "status"):
            status = self.status
            if isinstance(status, str):
                status = map_legacy_status(status)

            if is_terminal_status(status):
                return True, f"Ticket is in terminal state: {status.value}"

        return False, None


class TaskModel(BaseTicketModel):
    """Task data model."""

    id: Annotated[str, StringConstraints(pattern=r"^TSK-[0-9]+$")] = Field(
        ..., description="Unique task identifier"
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)] = Field(
        ..., description="Task title"
    )
    status: Union[UnifiedStatus, TaskStatus] = Field(
        UnifiedStatus.OPEN, description="Task status"
    )
    due_date: Optional[date] = Field(None, description="Task due date")
    estimated_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Estimated hours"
    )
    actual_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Actual hours"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Task dependencies"
    )
    parent: Optional[str] = Field(None, description="Parent issue or epic ID")

    @field_serializer("due_date")
    def serialize_due_date(self, value: Optional[date]) -> Optional[str]:
        """Serialize due_date to ISO format."""
        return value.isoformat() if value else None

    @model_validator(mode="after")
    def parent_not_self(self) -> "TaskModel":
        """Ensure parent is not the task itself."""
        if self.parent and self.parent == self.id:
            raise ValueError("Task cannot be its own parent")
        return self

    @model_validator(mode="after")
    def dependencies_not_self(self) -> "TaskModel":
        """Ensure task doesn't depend on itself."""
        if self.dependencies and self.id in self.dependencies:
            raise ValueError("Task cannot depend on itself")
        return self

    @model_validator(mode="after")
    def actual_hours_validation(self) -> "TaskModel":
        """Validate actual hours against estimated hours."""
        if self.actual_hours is not None and self.estimated_hours is not None:
            if (
                self.actual_hours > self.estimated_hours * 2
            ):  # Allow up to 200% of estimate
                raise ValueError("Actual hours significantly exceed estimate (>200%)")
        return self

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """Normalize status to UnifiedStatus for backward compatibility."""
        if isinstance(v, str):
            # Try to convert from TaskStatus enum value
            try:
                # If it's a valid TaskStatus, map it to UnifiedStatus
                TaskStatus(v)  # Validate it's a valid TaskStatus
                return map_legacy_status(v)
            except ValueError:
                # Try UnifiedStatus directly
                try:
                    return UnifiedStatus(v)
                except ValueError:
                    # Use legacy mapping as fallback
                    return map_legacy_status(v)
        elif isinstance(v, TaskStatus):
            return map_legacy_status(v.value)
        return v


class EpicModel(BaseTicketModel):
    """Epic data model."""

    id: Annotated[str, StringConstraints(pattern=r"^EP-[0-9]+$")] = Field(
        ..., description="Unique epic identifier"
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=300)] = Field(
        ..., description="Epic title"
    )
    status: Union[UnifiedStatus, EpicStatus] = Field(
        UnifiedStatus.PLANNING, description="Epic status"
    )
    goal: str = Field("", description="Epic goal or objective")
    business_value: str = Field("", description="Business value or impact")
    success_criteria: str = Field("", description="Success criteria")
    target_date: Optional[date] = Field(None, description="Target completion date")
    estimated_story_points: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Total story points"
    )
    child_issues: List[str] = Field(default_factory=list, description="Child issue IDs")
    dependencies: List[str] = Field(
        default_factory=list, description="Epic dependencies"
    )

    @field_serializer("target_date")
    def serialize_target_date(self, value: Optional[date]) -> Optional[str]:
        """Serialize target_date to ISO format."""
        return value.isoformat() if value else None

    @field_validator("child_issues")
    @classmethod
    def unique_child_issues(cls, v: List[str]) -> List[str]:
        """Ensure child issues are unique."""
        if v:
            return list(dict.fromkeys(v))
        return v

    @field_validator("target_date")
    @classmethod
    def target_date_in_future(cls, v: Optional[date]) -> Optional[date]:
        """Ensure target date is not in the past for new epics."""
        if v and v < date.today():
            raise ValueError("Target date should not be in the past")
        return v

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """Normalize status to UnifiedStatus for backward compatibility."""
        if isinstance(v, str):
            try:
                # If it's a valid EpicStatus, map it to UnifiedStatus
                EpicStatus(v)  # Validate it's a valid EpicStatus
                return map_legacy_status(v)
            except ValueError:
                try:
                    return UnifiedStatus(v)
                except ValueError:
                    return map_legacy_status(v)
        elif isinstance(v, EpicStatus):
            return map_legacy_status(v.value)
        return v


class IssueModel(BaseTicketModel):
    """Issue data model."""

    id: Annotated[str, StringConstraints(pattern=r"^ISS-[0-9]+$")] = Field(
        ..., description="Unique issue identifier"
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=250)] = Field(
        ..., description="Issue title"
    )
    issue_type: IssueType = Field(IssueType.BUG, description="Type of issue")
    severity: Priority = Field(Priority.MEDIUM, description="Issue severity")
    status: Union[UnifiedStatus, IssueStatus] = Field(
        UnifiedStatus.OPEN, description="Issue status"
    )
    due_date: Optional[date] = Field(None, description="Issue due date")
    estimated_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Estimated hours"
    )
    actual_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Actual hours"
    )
    story_points: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Story points"
    )
    environment: str = Field("", description="Environment where issue occurs")
    steps_to_reproduce: str = Field("", description="Steps to reproduce")
    expected_behavior: str = Field("", description="Expected behavior")
    actual_behavior: str = Field("", description="Actual behavior")
    dependencies: List[str] = Field(
        default_factory=list, description="Issue dependencies"
    )
    parent: Optional[str] = Field(None, description="Parent epic ID")
    child_tasks: List[str] = Field(default_factory=list, description="Child task IDs")
    related_prs: List[str] = Field(default_factory=list, description="Related PR IDs")

    @field_serializer("due_date")
    def serialize_due_date(self, value: Optional[date]) -> Optional[str]:
        """Serialize due_date to ISO format."""
        return value.isoformat() if value else None

    @field_validator("parent")
    @classmethod
    def parent_is_epic(cls, v: Optional[str]) -> Optional[str]:
        """Ensure parent is an epic if specified."""
        if v and not v.startswith("EP-"):
            raise ValueError("Issue parent must be an epic (EP-XXXX)")
        return v

    @field_validator("child_tasks")
    @classmethod
    def child_tasks_are_tasks(cls, v: List[str]) -> List[str]:
        """Ensure child tasks are task IDs."""
        if v:
            for task_id in v:
                if not task_id.startswith("TSK-"):
                    raise ValueError(
                        f"Child task {task_id} must be a task ID (TSK-XXXX)"
                    )
        return list(dict.fromkeys(v)) if v else v

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """Normalize status to UnifiedStatus for backward compatibility."""
        if isinstance(v, str):
            try:
                # If it's a valid IssueStatus, map it to UnifiedStatus
                IssueStatus(v)  # Validate it's a valid IssueStatus
                return map_legacy_status(v)
            except ValueError:
                try:
                    return UnifiedStatus(v)
                except ValueError:
                    return map_legacy_status(v)
        elif isinstance(v, IssueStatus):
            return map_legacy_status(v.value)
        return v


class BugModel(BaseTicketModel):
    """Bug data model."""

    id: Annotated[str, StringConstraints(pattern=r"^BUG-[0-9]+$")] = Field(
        ..., description="Unique bug identifier"
    )
    type: Literal["bug"] = Field("bug", description="Ticket type (always 'bug')")
    title: Annotated[str, StringConstraints(min_length=1, max_length=250)] = Field(
        ..., description="Bug title"
    )
    severity: BugSeverity = Field(BugSeverity.MEDIUM, description="Bug severity")
    status: Union[UnifiedStatus, BugStatus] = Field(
        UnifiedStatus.OPEN, description="Bug status"
    )
    environment: str = Field("", description="Environment where bug occurs")
    steps_to_reproduce: str = Field("", description="Steps to reproduce the bug")
    expected_behavior: str = Field("", description="Expected behavior")
    actual_behavior: str = Field("", description="Actual behavior")
    affected_versions: List[str] = Field(
        default_factory=list, description="Affected versions"
    )
    fixed_in_version: Optional[str] = Field(None, description="Version with fix")
    is_regression: bool = Field(False, description="Is this a regression?")
    related_issues: List[str] = Field(
        default_factory=list, description="Related issue IDs"
    )
    related_prs: List[str] = Field(default_factory=list, description="Related PR IDs")
    parent: Optional[str] = Field(None, description="Parent epic ID")
    browser: Optional[str] = Field(None, description="Browser information")
    os: Optional[str] = Field(None, description="Operating system")
    device: Optional[str] = Field(None, description="Device information")
    error_logs: str = Field("", description="Relevant error logs")
    verified_fixed: bool = Field(False, description="Has fix been verified?")
    resolution_notes: str = Field("", description="Resolution notes")

    @field_validator("parent")
    @classmethod
    def parent_is_epic(cls, v: Optional[str]) -> Optional[str]:
        """Ensure parent is an epic if specified."""
        if v and not v.startswith("EP-"):
            raise ValueError("Bug parent must be an epic (EP-XXXX)")
        return v

    @field_validator("related_issues")
    @classmethod
    def related_issues_validation(cls, v: List[str]) -> List[str]:
        """Ensure related issues are issue IDs."""
        if v:
            for issue_id in v:
                if not (issue_id.startswith("ISS-") or issue_id.startswith("BUG-")):
                    raise ValueError(
                        f"Related issue {issue_id} must be an issue ID (ISS-XXXX) or bug ID (BUG-XXXX)"
                    )
        return list(dict.fromkeys(v)) if v else v

    @field_validator("related_prs")
    @classmethod
    def related_prs_validation(cls, v: List[str]) -> List[str]:
        """Ensure related PRs are PR IDs."""
        if v:
            for pr_id in v:
                if not pr_id.startswith("PR-"):
                    raise ValueError(f"Related PR {pr_id} must be a PR ID (PR-XXXX)")
        return list(dict.fromkeys(v)) if v else v

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """Normalize status to UnifiedStatus for backward compatibility."""
        if isinstance(v, str):
            try:
                # If it's a valid BugStatus, map it to UnifiedStatus
                BugStatus(v)  # Validate it's a valid BugStatus
                return map_legacy_status(v)
            except ValueError:
                try:
                    return UnifiedStatus(v)
                except ValueError:
                    return map_legacy_status(v)
        elif isinstance(v, BugStatus):
            return map_legacy_status(v.value)
        return v


class MilestoneModel(BaseModel):
    """Milestone model for projects."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=100)] = Field(
        ..., description="Milestone name"
    )
    description: str = Field("", description="Milestone description")
    target_date: date = Field(..., description="Target completion date")
    status: MilestoneStatus = Field(
        MilestoneStatus.PLANNED, description="Milestone status"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("target_date")
    def serialize_target_date(self, value: date) -> str:
        """Serialize target_date to ISO format."""
        return value.isoformat()


class PRModel(BaseTicketModel):
    """Pull Request data model."""

    id: Annotated[str, StringConstraints(pattern=r"^PR-[0-9]+$")] = Field(
        ..., description="Unique PR identifier"
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)] = Field(
        ..., description="PR title"
    )
    pr_type: PRType = Field(PRType.FEATURE, description="Type of pull request")
    status: Union[UnifiedStatus, PRStatus] = Field(
        UnifiedStatus.DRAFT, description="PR status"
    )
    source_branch: Annotated[str, StringConstraints(min_length=1)] = Field(
        ..., description="Source branch"
    )
    target_branch: Annotated[str, StringConstraints(min_length=1)] = Field(
        "main", description="Target branch"
    )
    breaking_changes: bool = Field(False, description="Contains breaking changes")
    reviewers: List[str] = Field(default_factory=list, description="PR reviewers")
    merged_at: Optional[datetime] = Field(None, description="Merge timestamp")
    related_issues: List[str] = Field(
        default_factory=list, description="Related issue IDs"
    )
    closes_issues: List[str] = Field(
        default_factory=list, description="Issues closed by this PR"
    )
    commits: List[
        Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{7,40}$")]
    ] = Field(default_factory=list, description="Commit SHAs")
    files_changed: List[str] = Field(default_factory=list, description="Files changed")
    lines_added: Optional[Annotated[int, Field(ge=0)]] = Field(
        None, description="Lines added"
    )
    lines_deleted: Optional[Annotated[int, Field(ge=0)]] = Field(
        None, description="Lines deleted"
    )
    test_coverage: Optional[Annotated[float, Field(ge=0, le=100)]] = Field(
        None, description="Test coverage %"
    )

    @field_serializer("merged_at")
    def serialize_merged_at(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize merged_at to ISO format."""
        return value.isoformat() if value else None

    @model_validator(mode="after")
    def merged_at_validation(self) -> "PRModel":
        """Validate merge timestamp."""
        if self.merged_at:
            if self.status not in [PRStatus.MERGED, PRStatus.CLOSED]:
                raise ValueError("merged_at can only be set for merged or closed PRs")
            if self.merged_at < self.created_at:
                raise ValueError("merged_at cannot be before created_at")
        return self

    @field_validator("closes_issues")
    @classmethod
    def closes_issues_are_issues(cls, v: List[str]) -> List[str]:
        """Ensure closed items are issue IDs."""
        if v:
            for issue_id in v:
                if not issue_id.startswith("ISS-"):
                    raise ValueError(
                        f"Closed issue {issue_id} must be an issue ID (ISS-XXXX)"
                    )
        return list(dict.fromkeys(v)) if v else v

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """Normalize status to UnifiedStatus for backward compatibility."""
        if isinstance(v, str):
            try:
                # If it's a valid PRStatus, map it to UnifiedStatus
                PRStatus(v)  # Validate it's a valid PRStatus
                return map_legacy_status(v)
            except ValueError:
                try:
                    return UnifiedStatus(v)
                except ValueError:
                    return map_legacy_status(v)
        elif isinstance(v, PRStatus):
            return map_legacy_status(v.value)
        return v


class ProjectModel(BaseTicketModel):
    """Project data model."""

    id: Annotated[str, StringConstraints(pattern=r"^PROJ-[0-9]+$")] = Field(
        ..., description="Unique project identifier"
    )
    name: Annotated[str, StringConstraints(min_length=1, max_length=100)] = Field(
        ..., description="Project name"
    )
    status: Union[UnifiedStatus, ProjectStatus] = Field(
        UnifiedStatus.PLANNING, description="Project status"
    )
    author: str = Field("", description="Project author")
    license: str = Field("MIT", description="Project license")
    tech_stack: List[str] = Field(default_factory=list, description="Technology stack")
    team_members: List[str] = Field(default_factory=list, description="Team members")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    target_completion: Optional[date] = Field(None, description="Target completion")
    budget: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Project budget"
    )
    estimated_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Total estimated hours"
    )
    actual_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Total actual hours"
    )
    progress_percentage: Optional[Annotated[float, Field(ge=0, le=100)]] = Field(
        None, description="Completion %"
    )
    epics: List[str] = Field(default_factory=list, description="Project epic IDs")
    repository_url: Optional[str] = Field(None, description="Repository URL")
    documentation_url: Optional[str] = Field(None, description="Documentation URL")
    milestones: List[MilestoneModel] = Field(
        default_factory=list, description="Project milestones"
    )

    @field_serializer("start_date", "end_date", "target_completion")
    def serialize_dates(self, value: Optional[date]) -> Optional[str]:
        """Serialize date fields to ISO format."""
        return value.isoformat() if value else None

    @model_validator(mode="after")
    def end_date_after_start_date(self) -> "ProjectModel":
        """Ensure end date is after start date."""
        if self.end_date and self.start_date and self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self

    @model_validator(mode="after")
    def target_completion_validation(self) -> "ProjectModel":
        """Validate target completion date."""
        if self.target_completion:
            if self.start_date and self.target_completion <= self.start_date:
                raise ValueError("target_completion must be after start_date")
            if self.end_date and self.target_completion > self.end_date:
                raise ValueError("target_completion should not be after end_date")
        return self

    @field_validator("epics")
    @classmethod
    def epics_are_epic_ids(cls, v: List[str]) -> List[str]:
        """Ensure epics are epic IDs."""
        if v:
            for epic_id in v:
                if not epic_id.startswith("EP-"):
                    raise ValueError(f"Epic {epic_id} must be an epic ID (EP-XXXX)")
        return list(dict.fromkeys(v)) if v else v

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v):
        """Normalize status to UnifiedStatus for backward compatibility."""
        if isinstance(v, str):
            try:
                # If it's a valid ProjectStatus, map it to UnifiedStatus
                ProjectStatus(v)  # Validate it's a valid ProjectStatus
                return map_legacy_status(v)
            except ValueError:
                try:
                    return UnifiedStatus(v)
                except ValueError:
                    return map_legacy_status(v)
        elif isinstance(v, ProjectStatus):
            return map_legacy_status(v.value)
        return v


# Union types for status types
StatusType = Union[
    UnifiedStatus,
    TaskStatus,
    EpicStatus,
    IssueStatus,
    BugStatus,
    PRStatus,
    ProjectStatus,
]
PriorityType = Priority


# Comment model for tracking comments with status awareness
class CommentModel(BaseModel):
    """Comment data model with status inheritance support.

    WHY: Comments need to respect parent ticket status to prevent modifications
    to closed tickets and maintain data integrity. This model provides:
    - Structured comment data with validation
    - Read-only enforcement for terminal state tickets
    - Parent ticket status awareness
    - Comment modification tracking
    """

    id: str = Field(..., description="Unique comment identifier")
    parent_id: Annotated[
        str, Field(pattern=r"^[A-Z]+-[0-9]+$", description="Parent ticket ID")
    ]
    parent_type: str = Field(..., description="Type of parent ticket")
    author: str = Field(..., description="Comment author")
    content: str = Field(..., description="Comment content")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    edited_by: Optional[str] = Field(None, description="User who last edited")
    is_system: bool = Field(False, description="System-generated comment")
    is_read_only: bool = Field(False, description="Comment cannot be edited")

    # Status inheritance fields
    parent_status: Optional[UnifiedStatus] = Field(
        None, description="Current status of parent ticket"
    )
    locked_at: Optional[datetime] = Field(
        None, description="When comment was locked due to parent status"
    )
    locked_reason: Optional[str] = Field(
        None, description="Reason for locking (e.g., 'Parent ticket closed')"
    )

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("created_at", "updated_at", "locked_at")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format."""
        return value.isoformat() if value else None

    @model_validator(mode="after")
    def validate_timestamps(self) -> "CommentModel":
        """Ensure timestamp consistency."""
        if self.updated_at and self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be before created_at")
        if self.locked_at and self.locked_at < self.created_at:
            raise ValueError("locked_at cannot be before created_at")
        return self

    def can_edit(
        self, parent_ticket: Optional[BaseTicketModel] = None
    ) -> tuple[bool, Optional[str]]:
        """Check if comment can be edited based on parent ticket status.

        WHY: Comments should become read-only when their parent ticket reaches
        a terminal state. This prevents modifications to historical records
        and maintains audit trail integrity.

        Args:
            parent_ticket: Parent ticket model instance

        Returns:
            Tuple of (can_edit, reason_if_not)
        """
        # System comments are always read-only
        if self.is_system:
            return False, "System comments cannot be edited"

        # Explicitly locked comments
        if self.is_read_only:
            return False, self.locked_reason or "Comment is read-only"

        # Check parent ticket status
        if parent_ticket and hasattr(parent_ticket, "status"):
            parent_status = parent_ticket.status
            if isinstance(parent_status, str):
                parent_status = map_legacy_status(parent_status)

            if is_terminal_status(parent_status):
                return False, f"Cannot edit comments on {parent_status.value} tickets"

        # Check if parent status is terminal (from stored value)
        if self.parent_status and is_terminal_status(self.parent_status):
            return False, f"Cannot edit comments on {self.parent_status.value} tickets"

        return True, None

    def lock_due_to_parent_status(
        self, parent_status: UnifiedStatus, user: Optional[str] = None
    ) -> None:
        """Lock comment when parent reaches terminal status.

        WHY: When a ticket is closed/resolved, its comments should be preserved
        as-is for historical accuracy. This method enforces that preservation.

        Args:
            parent_status: The parent ticket's new status
            user: User who triggered the status change
        """
        if is_terminal_status(parent_status):
            self.is_read_only = True
            self.parent_status = parent_status
            self.locked_at = datetime.now()
            self.locked_reason = f"Parent ticket changed to {parent_status.value}"
            if user:
                self.locked_reason += f" by {user}"

    def update_content(
        self,
        new_content: str,
        editor: str,
        parent_ticket: Optional[BaseTicketModel] = None,
    ) -> None:
        """Update comment content with validation.

        WHY: Centralizes comment editing logic with proper validation and
        audit trail tracking. Ensures comments can only be edited when allowed.

        Args:
            new_content: New comment content
            editor: User making the edit
            parent_ticket: Parent ticket for status checking

        Raises:
            ValueError: If comment cannot be edited
        """
        can_edit, reason = self.can_edit(parent_ticket)
        if not can_edit:
            raise ValueError(f"Cannot edit comment: {reason}")

        self.content = new_content
        self.updated_at = datetime.now()
        self.edited_by = editor


# Union type for all ticket models
TicketModel = Union[TaskModel, EpicModel, IssueModel, BugModel, PRModel, ProjectModel]


def get_model_for_type(ticket_type: str) -> type:
    """Get the appropriate model class for a ticket type."""
    model_map = {
        "task": TaskModel,
        "epic": EpicModel,
        "issue": IssueModel,
        "bug": BugModel,
        "pr": PRModel,
        "project": ProjectModel,
    }
    return model_map.get(ticket_type.lower())


def get_id_pattern_for_type(ticket_type: str) -> str:
    """Get the ID pattern for a ticket type."""
    pattern_map = {
        "task": r"^TSK-[0-9]+$",
        "epic": r"^EP-[0-9]+$",
        "issue": r"^ISS-[0-9]+$",
        "bug": r"^BUG-[0-9]+$",
        "pr": r"^PR-[0-9]+$",
        "project": r"^PROJ-[0-9]+$",
    }
    return pattern_map.get(ticket_type.lower(), r"^[A-Z]+-[0-9]+$")
