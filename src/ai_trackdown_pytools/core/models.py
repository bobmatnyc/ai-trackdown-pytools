"""Pydantic models for AI Trackdown PyTools."""

from datetime import datetime, date
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
    ConfigDict,
    field_serializer,
    StringConstraints,
)
from typing_extensions import Annotated


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

    model_config = ConfigDict(use_enum_values=True)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime) -> str:
        """Serialize datetime to ISO format."""
        return value.isoformat()

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


class TaskModel(BaseTicketModel):
    """Task data model."""

    id: Annotated[str, StringConstraints(pattern=r"^TSK-[0-9]+$")] = Field(
        ..., description="Unique task identifier"
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=200)] = Field(
        ..., description="Task title"
    )
    status: TaskStatus = Field(TaskStatus.OPEN, description="Task status")
    due_date: Optional[date] = Field(None, description="Task due date")
    estimated_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Estimated hours"
    )
    actual_hours: Optional[Annotated[float, Field(ge=0)]] = Field(None, description="Actual hours")
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


class EpicModel(BaseTicketModel):
    """Epic data model."""

    id: Annotated[str, StringConstraints(pattern=r"^EP-[0-9]+$")] = Field(
        ..., description="Unique epic identifier"
    )
    title: Annotated[str, StringConstraints(min_length=1, max_length=300)] = Field(
        ..., description="Epic title"
    )
    status: EpicStatus = Field(EpicStatus.PLANNING, description="Epic status")
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
    status: IssueStatus = Field(IssueStatus.OPEN, description="Issue status")
    due_date: Optional[date] = Field(None, description="Issue due date")
    estimated_hours: Optional[Annotated[float, Field(ge=0)]] = Field(
        None, description="Estimated hours"
    )
    actual_hours: Optional[Annotated[float, Field(ge=0)]] = Field(None, description="Actual hours")
    story_points: Optional[Annotated[float, Field(ge=0)]] = Field(None, description="Story points")
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
    status: PRStatus = Field(PRStatus.DRAFT, description="PR status")
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
    commits: List[Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{7,40}$")]] = (
        Field(default_factory=list, description="Commit SHAs")
    )
    files_changed: List[str] = Field(default_factory=list, description="Files changed")
    lines_added: Optional[Annotated[int, Field(ge=0)]] = Field(None, description="Lines added")
    lines_deleted: Optional[Annotated[int, Field(ge=0)]] = Field(None, description="Lines deleted")
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


class ProjectModel(BaseTicketModel):
    """Project data model."""

    id: Annotated[str, StringConstraints(pattern=r"^PROJ-[0-9]+$")] = Field(
        ..., description="Unique project identifier"
    )
    name: Annotated[str, StringConstraints(min_length=1, max_length=100)] = Field(
        ..., description="Project name"
    )
    status: ProjectStatus = Field(ProjectStatus.PLANNING, description="Project status")
    author: str = Field("", description="Project author")
    license: str = Field("MIT", description="Project license")
    tech_stack: List[str] = Field(default_factory=list, description="Technology stack")
    team_members: List[str] = Field(default_factory=list, description="Team members")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    target_completion: Optional[date] = Field(None, description="Target completion")
    budget: Optional[Annotated[float, Field(ge=0)]] = Field(None, description="Project budget")
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


# Union types for status types
StatusType = Union[TaskStatus, EpicStatus, IssueStatus, PRStatus, ProjectStatus]
PriorityType = Priority

# Union type for all ticket models
TicketModel = Union[TaskModel, EpicModel, IssueModel, PRModel, ProjectModel]


def get_model_for_type(ticket_type: str) -> type:
    """Get the appropriate model class for a ticket type."""
    model_map = {
        "task": TaskModel,
        "epic": EpicModel,
        "issue": IssueModel,
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
        "pr": r"^PR-[0-9]+$",
        "project": r"^PROJ-[0-9]+$",
    }
    return pattern_map.get(ticket_type.lower(), r"^[A-Z]+-[0-9]+$")
