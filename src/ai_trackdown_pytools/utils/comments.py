"""Comment management utilities for AI Trackdown PyTools."""

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import ValidationError

from ai_trackdown_pytools.core.models import (
    BaseTicketModel,
    CommentModel,
    get_model_for_type,
)
from ai_trackdown_pytools.core.workflow import is_terminal_status


class CommentManager:
    """Manager for handling comments on tasks, issues, and epics with status awareness.

    WHY: This enhanced manager enforces comment status inheritance rules to ensure
    comments on closed tickets remain read-only and new comments cannot be added
    to terminal state tickets. This maintains data integrity and audit trails.
    """

    def __init__(self, file_path: Path):
        """Initialize comment manager with a file path."""
        self.file_path = file_path
        self._parent_ticket = None
        self._parent_type = None
        self._parent_id = None

    def _load_parent_ticket(self) -> Optional[BaseTicketModel]:
        """Load the parent ticket from file to check its status.

        WHY: We need the parent ticket's current status to enforce
        comment rules. This loads and validates the ticket data.
        """
        try:
            with open(self.file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not fm_match:
                return None

            frontmatter = yaml.safe_load(fm_match.group(1))

            # Determine ticket type and ID
            ticket_id = frontmatter.get("id")
            if not ticket_id:
                return None

            self._parent_id = ticket_id

            # Infer type from ID prefix
            if ticket_id.startswith("TSK-"):
                self._parent_type = "task"
            elif ticket_id.startswith("ISS-"):
                self._parent_type = "issue"
            elif ticket_id.startswith("EP-"):
                self._parent_type = "epic"
            elif ticket_id.startswith("BUG-"):
                self._parent_type = "bug"
            elif ticket_id.startswith("PR-"):
                self._parent_type = "pr"
            elif ticket_id.startswith("PROJ-"):
                self._parent_type = "project"
            else:
                return None

            # Get the model class and create instance
            model_class = get_model_for_type(self._parent_type)
            if model_class:
                # Ensure required fields have defaults for loading
                if "created_at" not in frontmatter:
                    frontmatter["created_at"] = datetime.now()
                if "updated_at" not in frontmatter:
                    frontmatter["updated_at"] = frontmatter["created_at"]

                self._parent_ticket = model_class(**frontmatter)
                return self._parent_ticket

        except Exception as e:
            print(f"Error loading parent ticket: {e}")
            return None

    def add_comment(self, author: str, content: str, force: bool = False) -> bool:
        """
        Add a comment to a file with status validation.

        WHY: This method now checks parent ticket status before allowing
        new comments. This prevents comments on closed tickets unless
        explicitly forced (e.g., for system comments).

        Args:
            author: Comment author
            content: Comment content
            force: Force adding comment even on terminal status tickets

        Returns:
            True if successful, False otherwise

        Raises:
            ValueError: If attempting to comment on a terminal status ticket
        """
        # Check parent ticket status
        if not force:
            parent_ticket = self._load_parent_ticket()
            if parent_ticket and hasattr(parent_ticket, "status"):
                status = parent_ticket.status
                if isinstance(status, str):
                    from ai_trackdown_pytools.core.workflow import map_legacy_status

                    status = map_legacy_status(status)

                if is_terminal_status(status):
                    raise ValueError(
                        f"Cannot add comments to {status.value} tickets. "
                        f"Ticket {self._parent_id} is in a terminal state."
                    )

        try:
            # Read the file
            with open(self.file_path, encoding="utf-8") as f:
                file_content = f.read()

            # Find the end of the main content (before comments section)
            # Look for existing ## Comments section
            comments_match = re.search(
                r"^## Comments?\s*\n", file_content, re.MULTILINE
            )

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            comment_id = f"CMT-{uuid.uuid4().hex[:8]}"
            comment_block = f"""
### Comment by {author} - {timestamp} [ID: {comment_id}]
{content}
"""

            if comments_match:
                # Insert after existing comments header
                insert_pos = comments_match.end()
                new_content = (
                    file_content[:insert_pos]
                    + comment_block
                    + file_content[insert_pos:]
                )
            else:
                # Add new comments section at the end
                comments_section = f"""

## Comments

{comment_block.strip()}
"""
                new_content = file_content.rstrip() + comments_section

            # Write back
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return True

        except Exception as e:
            print(f"Error adding comment: {e}")
            return False

    def get_comments(self) -> List[Dict[str, Any]]:
        """
        Extract all comments from a file.

        Returns:
            List of comment dictionaries
        """
        comments = []

        try:
            with open(self.file_path, encoding="utf-8") as f:
                content = f.read()

            # Find all comment blocks with enhanced pattern to capture metadata
            comment_pattern = r"### Comment by (.*?) - ([\d\-\s:]+)(?:\s*\[ID: (.*?)\])?\n((?:(?!###).*\n)*)"
            matches = re.finditer(comment_pattern, content)

            for match in matches:
                author = match.group(1)
                timestamp_str = match.group(2)
                comment_id = match.group(3)  # May be None for old comments
                comment_content = match.group(4).strip()

                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    timestamp = None

                comments.append(
                    {
                        "id": comment_id,
                        "author": author,
                        "timestamp": timestamp,
                        "content": comment_content,
                    }
                )

        except Exception as e:
            print(f"Error reading comments: {e}")

        return comments

    def get_comments_as_models(self) -> List[CommentModel]:
        """
        Get comments as CommentModel instances with status awareness.

        WHY: This provides structured comment data with validation and
        status inheritance logic. Comments are automatically marked as
        read-only if the parent ticket is in a terminal state.

        Returns:
            List of CommentModel instances
        """
        raw_comments = self.get_comments()
        parent_ticket = self._load_parent_ticket()
        models = []

        for comment_data in raw_comments:
            try:
                # Generate ID if missing (for legacy comments)
                if not comment_data.get("id"):
                    comment_data["id"] = f"CMT-{uuid.uuid4().hex[:8]}"

                # Create model with required fields
                comment = CommentModel(
                    id=comment_data["id"],
                    parent_id=self._parent_id or "UNKNOWN",
                    parent_type=self._parent_type or "unknown",
                    author=comment_data["author"],
                    content=comment_data["content"],
                    created_at=comment_data["timestamp"] or datetime.now(),
                    is_system=comment_data["author"] == "system",
                )

                # Check if should be locked due to parent status
                if parent_ticket and hasattr(parent_ticket, "status"):
                    status = parent_ticket.status
                    if isinstance(status, str):
                        from ai_trackdown_pytools.core.workflow import map_legacy_status

                        status = map_legacy_status(status)

                    if is_terminal_status(status):
                        comment.lock_due_to_parent_status(status)

                models.append(comment)

            except ValidationError as e:
                print(f"Error creating comment model: {e}")

        return models

    def count_comments(self) -> int:
        """Get the number of comments."""
        return len(self.get_comments())

    def update_frontmatter_comment_count(self) -> bool:
        """Update the comment count in frontmatter."""
        try:
            with open(self.file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter
            fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
            if not fm_match:
                return False

            frontmatter = yaml.safe_load(fm_match.group(1))
            comment_count = self.count_comments()

            # Update comment count
            if "metadata" not in frontmatter:
                frontmatter["metadata"] = {}
            frontmatter["metadata"]["comment_count"] = comment_count

            # Reconstruct file
            new_frontmatter = yaml.dump(
                frontmatter, default_flow_style=False, allow_unicode=True
            )
            new_content = f"---\n{new_frontmatter}---\n" + content[fm_match.end() :]

            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return True

        except Exception as e:
            print(f"Error updating comment count: {e}")
            return False


def add_comment_to_item(
    item_type: str,
    item_id: str,
    author: str,
    content: str,
    project_path: Path,
    force: bool = False,
) -> bool:
    """
    Add a comment to a task, issue, or epic with status validation.

    WHY: This function now validates parent ticket status before allowing
    comments, ensuring data integrity and preventing modifications to
    closed tickets unless explicitly forced.

    Args:
        item_type: Type of item ('task', 'issue', 'epic')
        item_id: ID of the item
        author: Comment author
        content: Comment content
        project_path: Project root path
        force: Force adding comment even on terminal status tickets

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If attempting to comment on a terminal status ticket
    """
    # Find the file
    from ai_trackdown_pytools.core.config import Config

    config = Config.load(project_path=project_path)
    tasks_dir = project_path / config.get("tasks.directory", "tasks")

    # Try multiple patterns to find the file
    patterns = [
        f"**/{item_id}.md",  # Direct match anywhere
        f"*/{item_id}.md",  # In any subdirectory
        f"{item_id}.md",  # In root tasks directory
    ]

    # If we know the prefix, also try specific subdirectory patterns
    if item_id.startswith("TSK-"):
        patterns.insert(0, f"tsk/{item_id}.md")
    elif item_id.startswith("ISS-"):
        patterns.insert(0, f"iss/{item_id}.md")
    elif item_id.startswith("EP-"):
        patterns.insert(0, f"ep/{item_id}.md")

    file_path = None
    for pattern in patterns:
        matches = list(tasks_dir.glob(pattern))
        if matches:
            file_path = matches[0]
            break

    if not file_path:
        print(f"Could not find {item_type} file for ID: {item_id}")
        return False

    file_path = matches[0]
    manager = CommentManager(file_path)

    # Add comment and update count
    try:
        if manager.add_comment(author, content, force=force):
            manager.update_frontmatter_comment_count()
            return True
    except ValueError as e:
        print(f"Error: {e}")
        return False

    return False
