"""Index management utilities for AI Trackdown PyTools."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class IndexManager:
    """Manager for maintaining file indexes for efficient searching and tracking."""

    def __init__(self, project_path: Path):
        """Initialize index manager."""
        self.project_path = project_path
        self.index_path = project_path / ".ai-trackdown" / "cache" / "index.json"
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._index = self._load_index()

    def _load_index(self) -> Dict[str, Any]:
        """Load existing index or create new one."""
        if self.index_path.exists():
            try:
                with open(self.index_path, encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
            except Exception:
                pass

        return {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "files": {},
            "statistics": {
                "total_tasks": 0,
                "total_issues": 0,
                "total_epics": 0,
                "total_prs": 0,
                "by_status": {},
                "by_priority": {},
                "by_assignee": {},
            },
        }

    def _save_index(self) -> None:
        """Save index to file."""
        self._index["updated_at"] = datetime.now().isoformat()

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self._index, f, indent=2)

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content."""
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _extract_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract metadata from a task/issue/epic file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    return frontmatter
        except Exception:
            pass

        return None

    def update_file(self, file_path: Path) -> bool:
        """Update index entry for a single file."""
        try:
            # Calculate relative path
            relative_path = file_path.relative_to(self.project_path)
            path_str = str(relative_path)

            # Get file stats
            stat = file_path.stat()
            current_mtime = stat.st_mtime
            current_hash = self._calculate_file_hash(file_path)

            # Check if file needs updating
            if path_str in self._index["files"]:
                entry = self._index["files"][path_str]
                if (
                    entry.get("hash") == current_hash
                    and entry.get("mtime") == current_mtime
                ):
                    return False  # No update needed

            # Extract metadata
            metadata = self._extract_metadata(file_path)
            if not metadata:
                return False

            # Update index entry
            self._index["files"][path_str] = {
                "path": path_str,
                "hash": current_hash,
                "mtime": current_mtime,
                "indexed_at": datetime.now().isoformat(),
                "id": metadata.get("id"),
                "title": metadata.get("title"),
                "status": metadata.get("status"),
                "priority": metadata.get("priority"),
                "assignees": metadata.get("assignees", []),
                "tags": metadata.get("tags", []),
                "created_at": metadata.get("created_at"),
                "updated_at": metadata.get("updated_at"),
                "type": self._determine_type(metadata.get("id", "")),
            }

            return True

        except Exception as e:
            print(f"Error indexing file {file_path}: {e}")
            return False

    def _determine_type(self, item_id: str) -> str:
        """Determine item type from ID."""
        if item_id.startswith("TSK-"):
            return "task"
        elif item_id.startswith("ISS-"):
            return "issue"
        elif item_id.startswith("EP-"):
            return "epic"
        elif item_id.startswith("PR-"):
            return "pr"
        else:
            return "unknown"

    def rebuild_index(self) -> Dict[str, int]:
        """Rebuild the entire index."""
        self._index["files"] = {}
        stats = {"indexed": 0, "errors": 0}

        # Index all markdown files in tasks directory
        from ai_trackdown_pytools.core.config import Config

        config = Config.load(project_path=self.project_path)
        tasks_dir = self.project_path / config.get("tasks.directory", "tasks")
        if tasks_dir.exists():
            for md_file in tasks_dir.rglob("*.md"):
                if self.update_file(md_file):
                    stats["indexed"] += 1
                else:
                    stats["errors"] += 1

        # Update statistics
        self._update_statistics()

        # Save index
        self._save_index()

        return stats

    def _update_statistics(self) -> None:
        """Update index statistics."""
        stats = {
            "total_tasks": 0,
            "total_issues": 0,
            "total_epics": 0,
            "total_prs": 0,
            "by_status": {},
            "by_priority": {},
            "by_assignee": {},
        }

        for entry in self._index["files"].values():
            # Count by type
            item_type = entry.get("type", "unknown")
            if item_type == "task":
                stats["total_tasks"] += 1
            elif item_type == "issue":
                stats["total_issues"] += 1
            elif item_type == "epic":
                stats["total_epics"] += 1
            elif item_type == "pr":
                stats["total_prs"] += 1

            # Count by status
            status = entry.get("status", "unknown")
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # Count by priority
            priority = entry.get("priority", "unknown")
            stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

            # Count by assignee
            for assignee in entry.get("assignees", []):
                stats["by_assignee"][assignee] = (
                    stats["by_assignee"].get(assignee, 0) + 1
                )

        self._index["statistics"] = stats

    def update_changed_files(self) -> Dict[str, int]:
        """Update only files that have changed."""
        stats = {"updated": 0, "removed": 0, "added": 0}

        # Check existing files
        existing_files = set()
        from ai_trackdown_pytools.core.config import Config

        config = Config.load(project_path=self.project_path)
        tasks_dir = self.project_path / config.get("tasks.directory", "tasks")

        if tasks_dir.exists():
            for md_file in tasks_dir.rglob("*.md"):
                relative_path = str(md_file.relative_to(self.project_path))
                existing_files.add(relative_path)

                if relative_path not in self._index["files"]:
                    # New file
                    if self.update_file(md_file):
                        stats["added"] += 1
                else:
                    # Check if file changed
                    entry = self._index["files"][relative_path]
                    stat = md_file.stat()

                    if entry.get("mtime") != stat.st_mtime:
                        if self.update_file(md_file):
                            stats["updated"] += 1

        # Remove deleted files
        for path in list(self._index["files"].keys()):
            if path not in existing_files:
                del self._index["files"][path]
                stats["removed"] += 1

        # Update statistics if changes were made
        if any(stats.values()):
            self._update_statistics()
            self._save_index()

        return stats

    def search(
        self, query: str, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search the index with optional filters."""
        results = []
        query_lower = query.lower()

        for entry in self._index["files"].values():
            # Text search
            if query_lower in entry.get("title", "").lower():
                match_score = 2.0
            elif query_lower in entry.get("id", "").lower():
                match_score = 1.5
            elif any(query_lower in tag.lower() for tag in entry.get("tags", [])):
                match_score = 1.0
            else:
                continue

            # Apply filters
            if filters:
                if "type" in filters and entry.get("type") != filters["type"]:
                    continue
                if "status" in filters and entry.get("status") != filters["status"]:
                    continue
                if (
                    "priority" in filters
                    and entry.get("priority") != filters["priority"]
                ):
                    continue
                if "assignee" in filters and filters["assignee"] not in entry.get(
                    "assignees", []
                ):
                    continue

            # Add to results
            result = entry.copy()
            result["match_score"] = match_score
            results.append(result)

        # Sort by match score and updated date
        results.sort(
            key=lambda x: (-x["match_score"], x.get("updated_at", "")), reverse=True
        )

        return results

    def get_statistics(self) -> Dict[str, Any]:
        """Get current index statistics."""
        return self._index.get("statistics", {})

    def needs_update(self) -> bool:
        """Check if index needs updating."""
        # Check if index is older than 5 minutes
        if "updated_at" in self._index:
            try:
                last_update = datetime.fromisoformat(self._index["updated_at"])
                age = datetime.now() - last_update
                return age.total_seconds() > 300  # 5 minutes
            except Exception:
                pass

        return True


def update_index_on_file_change(project_path: Path, file_path: Path) -> bool:
    """Update index when a file changes (hook for file operations)."""
    try:
        manager = IndexManager(project_path)
        return manager.update_file(file_path)
    except Exception:
        return False
