"""Git utilities for AI Trackdown PyTools.

This module provides Git integration utilities with proper error handling
and fallback behavior when GitPython is not available.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_trackdown_pytools.exceptions import GitOperationError

try:
    from git import GitCommandError, InvalidGitRepositoryError, Repo

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    Repo = None
    InvalidGitRepositoryError = None
    GitCommandError = None


# Keep GitError for backward compatibility but inherit from GitOperationError
class GitError(GitOperationError):
    """Exception raised for git-related errors.

    WHY: Maintained for backward compatibility. New code should use GitOperationError.
    """

    def __init__(self, message: str):
        super().__init__(message)


class GitRepo:
    """Git repository wrapper class."""

    def __init__(self, path: Path):
        """Initialize GitRepo."""
        self.path = Path(path)

        if not GIT_AVAILABLE:
            raise GitError("GitPython not available")

        try:
            self.repo = Repo(path)
        except Exception as e:
            raise GitError(f"Not a git repository: {e}") from e

    def get_current_branch(self) -> str:
        """Get current branch name."""
        try:
            return self.repo.active_branch.name
        except Exception as e:
            raise GitError(f"Failed to get current branch: {e}") from e

    def get_status(self) -> Dict[str, Any]:
        """Get repository status."""
        try:
            return {
                "branch": self.get_current_branch(),
                "commit": str(self.repo.head.commit.hexsha),
                "modified": [item.a_path for item in self.repo.index.diff(None)],
                "untracked": self.repo.untracked_files,
                "staged": [item.a_path for item in self.repo.index.diff("HEAD")],
            }
        except Exception as e:
            raise GitError(f"Failed to get repository status: {e}") from e

    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> None:
        """Commit changes with proper error handling.

        WHY: Commits can fail due to conflicts, hooks, or permissions.
        This provides specific guidance for each failure mode.
        """
        try:
            if files:
                self.repo.index.add(files)
            else:
                # Check if there are changes to commit
                if not self.repo.is_dirty() and not self.repo.untracked_files:
                    return  # Nothing to commit
                self.repo.git.add(A=True)

            self.repo.index.commit(message)
        except GitCommandError as e:
            if "nothing to commit" in str(e):
                return  # Not an error, just no changes
            raise GitOperationError(
                "Git command failed during commit",
                operation="commit",
                repository=self.path,
                original_error=e,
            )
        except Exception as e:
            raise GitOperationError(
                "Failed to commit changes",
                operation="commit",
                repository=self.path,
                original_error=e,
            )

    def create_branch(self, branch_name: str) -> None:
        """Create new branch."""
        try:
            self.repo.create_head(branch_name)
        except Exception as e:
            raise GitError(f"Failed to create branch {branch_name}: {e}") from e

    def switch_branch(self, branch_name: str) -> None:
        """Switch to branch."""
        try:
            self.repo.heads[branch_name].checkout()
        except Exception as e:
            raise GitError(f"Failed to switch to branch {branch_name}: {e}") from e

    def get_file_status(self) -> Dict[str, Any]:
        """Get file status information."""
        try:
            return {
                "modified": [item.a_path for item in self.repo.index.diff(None)],
                "untracked": self.repo.untracked_files,
                "staged": [item.a_path for item in self.repo.index.diff("HEAD")],
            }
        except Exception as e:
            raise GitError(f"Failed to get file status: {e}") from e


class GitUtils:
    """Git utilities for AI Trackdown projects."""

    def __init__(self, path: Optional[Path] = None):
        """Initialize Git utilities."""
        self.path = Path(path) if path else Path.cwd()
        self._repo = None

        if GIT_AVAILABLE:
            try:
                self._repo = Repo(self.path, search_parent_directories=True)
            except InvalidGitRepositoryError:
                self._repo = None

    def is_git_repo(self, path: Optional[Path] = None) -> bool:
        """Check if path is a git repository."""
        if not GIT_AVAILABLE:
            return False

        check_path = Path(path) if path else self.path

        try:
            Repo(check_path, search_parent_directories=True)
            return True
        except InvalidGitRepositoryError:
            return False

    @staticmethod
    def is_git_repo_static(path: Path) -> bool:
        """Check if path is a git repository (static method)."""
        if not GIT_AVAILABLE:
            return False

        try:
            Repo(path, search_parent_directories=True)
            return True
        except InvalidGitRepositoryError:
            return False

    @staticmethod
    def init_repo(path: Path) -> bool:
        """Initialize git repository."""
        if not GIT_AVAILABLE:
            return False

        try:
            Repo.init(path)
            return True
        except Exception:
            return False

    def get_current_branch(self) -> Optional[str]:
        """Get current git branch."""
        if not self._repo:
            return None

        try:
            return self._repo.active_branch.name
        except Exception:
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get git repository status."""
        if not self._repo:
            return {}

        try:
            return {
                "branch": self.get_current_branch(),
                "commit": str(self._repo.head.commit.hexsha),
                "modified": [item.a_path for item in self._repo.index.diff(None)],
                "untracked": self._repo.untracked_files,
                "staged": [item.a_path for item in self._repo.index.diff("HEAD")],
            }
        except Exception:
            return {}

    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> bool:
        """Commit changes to git."""
        if not self._repo:
            return False

        try:
            if files:
                self._repo.index.add(files)
            else:
                self._repo.git.add(A=True)

            self._repo.index.commit(message)
            return True
        except Exception:
            return False

    def create_branch(self, branch_name: str) -> bool:
        """Create new git branch."""
        if not self._repo:
            return False

        try:
            self._repo.create_head(branch_name)
            return True
        except Exception:
            return False

    def switch_branch(self, branch_name: str) -> bool:
        """Switch to git branch."""
        if not self._repo:
            return False

        try:
            self._repo.heads[branch_name].checkout()
            return True
        except Exception:
            return False

    def get_remote_url(self) -> Optional[str]:
        """Get remote URL for the repository."""
        if not self._repo:
            return None

        try:
            remote = self._repo.remote("origin")
            return remote.url
        except Exception:
            return None

    def get_diff_stats(self, comparison: str) -> Dict[str, Any]:
        """Get diff statistics between commits/branches."""
        if not self._repo:
            return {}

        try:
            # Parse comparison (e.g., "main..feature-branch")
            diff = self._repo.git.diff(comparison, numstat=True)

            if not diff:
                return {"files_changed": 0, "insertions": 0, "deletions": 0}

            lines = diff.strip().split("\n")
            files_changed = len(lines)
            insertions = 0
            deletions = 0

            for line in lines:
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        insertions += int(parts[0]) if parts[0] != "-" else 0
                        deletions += int(parts[1]) if parts[1] != "-" else 0
                    except ValueError:
                        continue

            return {
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions,
            }
        except Exception:
            return {"files_changed": 0, "insertions": 0, "deletions": 0}

    def get_commit_history(self, branch: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get commit history for a branch."""
        if not self._repo:
            return []

        try:
            commits = []
            for commit in self._repo.iter_commits(branch, max_count=limit):
                commits.append(
                    {
                        "sha": str(commit.hexsha),
                        "message": commit.message.strip(),
                        "author": str(commit.author),
                        "date": commit.committed_datetime.isoformat(),
                    }
                )
            return commits
        except Exception:
            return []


# Utility functions that work with GitRepo
def get_current_branch(path: Path) -> str:
    """Get current branch for repository at path."""
    git_repo = GitRepo(path)
    return git_repo.get_current_branch()


def get_repository_status(path: Path) -> Dict[str, Any]:
    """Get repository status for repository at path."""
    git_repo = GitRepo(path)
    return git_repo.get_status()


def create_branch(path: Path, branch_name: str) -> None:
    """Create branch in repository at path."""
    git_repo = GitRepo(path)
    git_repo.create_branch(branch_name)


def switch_branch(path: Path, branch_name: str) -> None:
    """Switch branch in repository at path."""
    git_repo = GitRepo(path)
    git_repo.switch_branch(branch_name)


def commit_changes(path: Path, message: str, files: Optional[List[str]] = None) -> None:
    """Commit changes in repository at path."""
    git_repo = GitRepo(path)
    git_repo.commit_changes(message, files)


def get_file_status(path: Path) -> Dict[str, Any]:
    """Get file status for repository at path."""
    git_repo = GitRepo(path)
    return git_repo.get_file_status()
