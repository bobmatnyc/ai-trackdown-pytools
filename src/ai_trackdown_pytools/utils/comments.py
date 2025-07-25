"""Comment management utilities for AI Trackdown PyTools."""

import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import yaml


class CommentManager:
    """Manager for handling comments on tasks, issues, and epics."""

    def __init__(self, file_path: Path):
        """Initialize comment manager with a file path."""
        self.file_path = file_path

    def add_comment(self, author: str, content: str) -> bool:
        """
        Add a comment to a file.

        Args:
            author: Comment author
            content: Comment content

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read the file
            with open(self.file_path, "r", encoding="utf-8") as f:
                file_content = f.read()

            # Find the end of the main content (before comments section)
            # Look for existing ## Comments section
            comments_match = re.search(
                r"^## Comments?\s*\n", file_content, re.MULTILINE
            )

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            comment_block = f"""
### Comment by {author} - {timestamp}
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
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find all comment blocks
            comment_pattern = r"### Comment by (.*?) - ([\d\-\s:]+)\n((?:(?!###).*\n)*)"
            matches = re.finditer(comment_pattern, content)

            for match in matches:
                author = match.group(1)
                timestamp_str = match.group(2)
                comment_content = match.group(3).strip()

                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    timestamp = None

                comments.append(
                    {
                        "author": author,
                        "timestamp": timestamp,
                        "content": comment_content,
                    }
                )

        except Exception as e:
            print(f"Error reading comments: {e}")

        return comments

    def count_comments(self) -> int:
        """Get the number of comments."""
        return len(self.get_comments())

    def update_frontmatter_comment_count(self) -> bool:
        """Update the comment count in frontmatter."""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
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
    item_type: str, item_id: str, author: str, content: str, project_path: Path
) -> bool:
    """
    Add a comment to a task, issue, or epic.

    Args:
        item_type: Type of item ('task', 'issue', 'epic')
        item_id: ID of the item
        author: Comment author
        content: Comment content
        project_path: Project root path

    Returns:
        True if successful, False otherwise
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
    if manager.add_comment(author, content):
        manager.update_frontmatter_comment_count()
        return True

    return False
