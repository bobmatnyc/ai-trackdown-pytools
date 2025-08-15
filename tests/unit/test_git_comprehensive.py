"""Comprehensive unit tests for Git integration module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_trackdown_pytools.utils.git import GIT_AVAILABLE, GitError, GitUtils


class TestGitAvailability:
    """Test Git availability detection."""

    @patch("ai_trackdown_pytools.utils.git.importlib.util.find_spec")
    def test_git_available_when_gitpython_installed(self, mock_find_spec):
        """Test GIT_AVAILABLE is True when GitPython is installed."""
        mock_find_spec.return_value = Mock()  # Non-None means module found

        # Re-import to test the module-level check
        import importlib

        import ai_trackdown_pytools.utils.git

        importlib.reload(ai_trackdown_pytools.utils.git)

        from ai_trackdown_pytools.utils.git import GIT_AVAILABLE

        assert GIT_AVAILABLE is True

    @patch("ai_trackdown_pytools.utils.git.importlib.util.find_spec")
    def test_git_available_when_gitpython_not_installed(self, mock_find_spec):
        """Test GIT_AVAILABLE is False when GitPython is not installed."""
        mock_find_spec.return_value = None  # None means module not found

        # Re-import to test the module-level check
        import importlib

        import ai_trackdown_pytools.utils.git

        importlib.reload(ai_trackdown_pytools.utils.git)

        from ai_trackdown_pytools.utils.git import GIT_AVAILABLE

        assert GIT_AVAILABLE is False


@pytest.mark.skipif(not GIT_AVAILABLE, reason="GitPython not available")
class TestGitUtilsWithGitPython:
    """Test GitUtils when GitPython is available."""

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_init_with_existing_repo(self, mock_repo_class):
        """Test initialization with existing Git repository."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils(Path("/test/repo"))

        assert git_utils.repo_path == Path("/test/repo")
        assert git_utils.repo == mock_repo
        mock_repo_class.assert_called_once_with(Path("/test/repo"))

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_init_with_non_repo_directory(self, mock_repo_class):
        """Test initialization with non-repository directory."""
        mock_repo_class.side_effect = Exception("Not a git repository")

        git_utils = GitUtils(Path("/test/not-repo"))

        assert git_utils.repo_path == Path("/test/not-repo")
        assert git_utils.repo is None

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_init_with_current_directory(self, mock_repo_class):
        """Test initialization with current directory."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        with patch("pathlib.Path.cwd", return_value=Path("/current/dir")):
            git_utils = GitUtils()

            assert git_utils.repo_path == Path("/current/dir")
            mock_repo_class.assert_called_once_with(Path("/current/dir"))

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_is_git_repo_true(self, mock_repo_class):
        """Test is_git_repo returns True for valid repository."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        assert git_utils.is_git_repo() is True

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_is_git_repo_false(self, mock_repo_class):
        """Test is_git_repo returns False for non-repository."""
        mock_repo_class.side_effect = Exception("Not a git repository")

        git_utils = GitUtils()
        assert git_utils.is_git_repo() is False

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_current_branch(self, mock_repo_class):
        """Test getting current branch name."""
        mock_repo = Mock()
        mock_repo.active_branch.name = "feature/test-branch"
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        branch = git_utils.get_current_branch()

        assert branch == "feature/test-branch"

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_current_branch_detached_head(self, mock_repo_class):
        """Test getting branch name when in detached HEAD state."""
        mock_repo = Mock()
        mock_repo.active_branch.name = Mock(side_effect=TypeError("HEAD is detached"))
        mock_repo.head.commit.hexsha = "abc123def456"
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        branch = git_utils.get_current_branch()

        assert branch == "abc123def456"

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_current_branch_no_repo(self, mock_repo_class):
        """Test getting branch name when no repository."""
        mock_repo_class.side_effect = Exception("Not a git repository")

        git_utils = GitUtils()
        branch = git_utils.get_current_branch()

        assert branch is None

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_remote_url(self, mock_repo_class):
        """Test getting remote URL."""
        mock_repo = Mock()
        mock_remote = Mock()
        mock_remote.url = "https://github.com/user/repo.git"
        mock_repo.remotes = [mock_remote]
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        url = git_utils.get_remote_url()

        assert url == "https://github.com/user/repo.git"

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_remote_url_specific_remote(self, mock_repo_class):
        """Test getting specific remote URL."""
        mock_repo = Mock()
        mock_origin = Mock()
        mock_origin.name = "origin"
        mock_origin.url = "https://github.com/user/repo.git"
        mock_upstream = Mock()
        mock_upstream.name = "upstream"
        mock_upstream.url = "https://github.com/other/repo.git"
        mock_repo.remotes = [mock_origin, mock_upstream]
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()

        # Get origin URL
        url = git_utils.get_remote_url("origin")
        assert url == "https://github.com/user/repo.git"

        # Get upstream URL
        url = git_utils.get_remote_url("upstream")
        assert url == "https://github.com/other/repo.git"

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_remote_url_no_remotes(self, mock_repo_class):
        """Test getting remote URL when no remotes configured."""
        mock_repo = Mock()
        mock_repo.remotes = []
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        url = git_utils.get_remote_url()

        assert url is None

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_status(self, mock_repo_class):
        """Test getting repository status."""
        mock_repo = Mock()
        mock_repo.active_branch.name = "main"
        mock_repo.is_dirty.return_value = True
        mock_repo.untracked_files = ["new_file.txt", "another_file.py"]

        # Mock modified files
        mock_diff = Mock()
        mock_diff.a_path = "modified_file.py"
        mock_repo.index.diff.return_value = [mock_diff]

        # Mock staged files
        mock_staged = Mock()
        mock_staged.a_path = "staged_file.py"
        mock_repo.index.diff.return_value = [mock_staged]

        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        status = git_utils.get_status()

        assert status["branch"] == "main"
        assert status["is_clean"] is False
        assert status["untracked"] == ["new_file.txt", "another_file.py"]
        assert len(status["modified"]) > 0
        assert len(status["staged"]) > 0

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_status_clean_repo(self, mock_repo_class):
        """Test getting status of clean repository."""
        mock_repo = Mock()
        mock_repo.active_branch.name = "main"
        mock_repo.is_dirty.return_value = False
        mock_repo.untracked_files = []
        mock_repo.index.diff.return_value = []
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        status = git_utils.get_status()

        assert status["branch"] == "main"
        assert status["is_clean"] is True
        assert status["untracked"] == []
        assert status["modified"] == []
        assert status["staged"] == []

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_add_files(self, mock_repo_class):
        """Test adding files to staging area."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()

        # Add single file
        git_utils.add_files("file1.py")
        mock_repo.index.add.assert_called_with(["file1.py"])

        # Add multiple files
        git_utils.add_files(["file2.py", "file3.py"])
        mock_repo.index.add.assert_called_with(["file2.py", "file3.py"])

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_add_files_no_repo(self, mock_repo_class):
        """Test adding files when no repository."""
        mock_repo_class.side_effect = Exception("Not a git repository")

        git_utils = GitUtils()

        with pytest.raises(GitError) as exc_info:
            git_utils.add_files("file.py")

        assert "No git repository found" in str(exc_info.value)

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_commit(self, mock_repo_class):
        """Test creating a commit."""
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_repo.index.commit.return_value = mock_commit
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        commit_hash = git_utils.commit("Test commit message")

        assert commit_hash == "abc123def456"
        mock_repo.index.commit.assert_called_once_with("Test commit message")

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_commit_no_repo(self, mock_repo_class):
        """Test committing when no repository."""
        mock_repo_class.side_effect = Exception("Not a git repository")

        git_utils = GitUtils()

        with pytest.raises(GitError) as exc_info:
            git_utils.commit("Test message")

        assert "No git repository found" in str(exc_info.value)

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_file_history(self, mock_repo_class):
        """Test getting file commit history."""
        mock_repo = Mock()

        # Mock commits
        mock_commit1 = Mock()
        mock_commit1.hexsha = "abc123"
        mock_commit1.author.name = "John Doe"
        mock_commit1.author.email = "john@example.com"
        mock_commit1.committed_datetime = Mock()
        mock_commit1.message = "Initial commit"

        mock_commit2 = Mock()
        mock_commit2.hexsha = "def456"
        mock_commit2.author.name = "Jane Smith"
        mock_commit2.author.email = "jane@example.com"
        mock_commit2.committed_datetime = Mock()
        mock_commit2.message = "Update file"

        mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2]
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        history = git_utils.get_file_history("test.py", max_count=2)

        assert len(history) == 2
        assert history[0]["hash"] == "abc123"
        assert history[0]["author"] == "John Doe"
        assert history[0]["email"] == "john@example.com"
        assert history[0]["message"] == "Initial commit"

        mock_repo.iter_commits.assert_called_once_with(paths="test.py", max_count=2)

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_file_history_no_repo(self, mock_repo_class):
        """Test getting file history when no repository."""
        mock_repo_class.side_effect = Exception("Not a git repository")

        git_utils = GitUtils()
        history = git_utils.get_file_history("test.py")

        assert history == []

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_create_branch(self, mock_repo_class):
        """Test creating a new branch."""
        mock_repo = Mock()
        mock_branch = Mock()
        mock_repo.create_head.return_value = mock_branch
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        result = git_utils.create_branch("feature/new-feature")

        assert result is True
        mock_repo.create_head.assert_called_once_with("feature/new-feature")
        mock_branch.checkout.assert_called_once()

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_create_branch_already_exists(self, mock_repo_class):
        """Test creating branch that already exists."""
        mock_repo = Mock()
        mock_repo.create_head.side_effect = Exception("Branch already exists")
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        result = git_utils.create_branch("existing-branch")

        assert result is False

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_checkout_branch(self, mock_repo_class):
        """Test checking out a branch."""
        mock_repo = Mock()
        mock_branch = Mock()
        mock_repo.heads = {"main": mock_branch}
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        result = git_utils.checkout_branch("main")

        assert result is True
        mock_branch.checkout.assert_called_once()

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_checkout_branch_not_found(self, mock_repo_class):
        """Test checking out non-existent branch."""
        mock_repo = Mock()
        mock_repo.heads = {}
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        result = git_utils.checkout_branch("non-existent")

        assert result is False

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_list_branches(self, mock_repo_class):
        """Test listing branches."""
        mock_repo = Mock()

        mock_main = Mock()
        mock_main.name = "main"

        mock_feature = Mock()
        mock_feature.name = "feature/test"

        mock_develop = Mock()
        mock_develop.name = "develop"

        mock_repo.heads = [mock_main, mock_feature, mock_develop]
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        branches = git_utils.list_branches()

        assert branches == ["main", "feature/test", "develop"]

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_has_uncommitted_changes(self, mock_repo_class):
        """Test checking for uncommitted changes."""
        mock_repo = Mock()
        mock_repo_class.return_value = mock_repo

        # Test with dirty repo
        mock_repo.is_dirty.return_value = True
        git_utils = GitUtils()
        assert git_utils.has_uncommitted_changes() is True

        # Test with clean repo
        mock_repo.is_dirty.return_value = False
        assert git_utils.has_uncommitted_changes() is False

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_last_commit(self, mock_repo_class):
        """Test getting last commit information."""
        mock_repo = Mock()

        mock_commit = Mock()
        mock_commit.hexsha = "abc123def456"
        mock_commit.author.name = "John Doe"
        mock_commit.author.email = "john@example.com"
        mock_commit.committed_datetime = Mock()
        mock_commit.message = "Latest commit message"

        mock_repo.head.commit = mock_commit
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        last_commit = git_utils.get_last_commit()

        assert last_commit["hash"] == "abc123def456"
        assert last_commit["author"] == "John Doe"
        assert last_commit["email"] == "john@example.com"
        assert last_commit["message"] == "Latest commit message"

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_get_last_commit_no_commits(self, mock_repo_class):
        """Test getting last commit when repository has no commits."""
        mock_repo = Mock()
        mock_repo.head.commit = Mock(side_effect=ValueError("No commits"))
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()
        last_commit = git_utils.get_last_commit()

        assert last_commit is None


@pytest.mark.skipif(
    GIT_AVAILABLE, reason="Testing fallback when GitPython not available"
)
class TestGitUtilsWithoutGitPython:
    """Test GitUtils fallback behavior when GitPython is not available."""

    def test_init_without_gitpython(self):
        """Test initialization without GitPython shows warning."""
        # Temporarily set GIT_AVAILABLE to False
        with patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", False):
            git_utils = GitUtils()

            assert git_utils.repo_path == Path.cwd()
            assert git_utils.repo is None

    def test_operations_without_gitpython(self):
        """Test operations return appropriate defaults without GitPython."""
        with patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", False):
            git_utils = GitUtils()

            assert git_utils.is_git_repo() is False
            assert git_utils.get_current_branch() is None
            assert git_utils.get_remote_url() is None
            assert git_utils.get_status() == {
                "branch": None,
                "is_clean": True,
                "modified": [],
                "staged": [],
                "untracked": [],
            }
            assert git_utils.get_file_history("test.py") == []
            assert git_utils.list_branches() == []
            assert git_utils.has_uncommitted_changes() is False
            assert git_utils.get_last_commit() is None

    def test_operations_raise_errors_without_gitpython(self):
        """Test operations that should raise errors without GitPython."""
        with patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", False):
            git_utils = GitUtils()

            with pytest.raises(GitError, match="GitPython is not available"):
                git_utils.add_files("test.py")

            with pytest.raises(GitError, match="GitPython is not available"):
                git_utils.commit("Test message")

            assert git_utils.create_branch("test") is False
            assert git_utils.checkout_branch("test") is False


class TestGitError:
    """Test GitError exception."""

    def test_git_error_message(self):
        """Test GitError carries message."""
        error = GitError("Test error message")
        assert str(error) == "Test error message"

    def test_git_error_inheritance(self):
        """Test GitError inherits from Exception."""
        error = GitError("Test")
        assert isinstance(error, Exception)


class TestGitUtilsIntegration:
    """Test GitUtils integration scenarios."""

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_workflow_add_commit(self, mock_repo_class):
        """Test typical add and commit workflow."""
        mock_repo = Mock()
        mock_commit = Mock()
        mock_commit.hexsha = "abc123"
        mock_repo.index.commit.return_value = mock_commit
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()

        # Add files
        git_utils.add_files(["file1.py", "file2.py"])

        # Commit
        commit_hash = git_utils.commit("Add new files")

        assert commit_hash == "abc123"
        mock_repo.index.add.assert_called_once_with(["file1.py", "file2.py"])
        mock_repo.index.commit.assert_called_once_with("Add new files")

    @patch("ai_trackdown_pytools.utils.git.Repo")
    def test_workflow_branch_operations(self, mock_repo_class):
        """Test branch creation and checkout workflow."""
        mock_repo = Mock()
        mock_main = Mock()
        mock_main.name = "main"
        mock_feature = Mock()
        mock_feature.name = "feature/test"

        mock_repo.heads = {"main": mock_main}
        mock_repo.active_branch = mock_main
        mock_repo.create_head.return_value = mock_feature
        mock_repo_class.return_value = mock_repo

        git_utils = GitUtils()

        # Check current branch
        assert git_utils.get_current_branch() == "main"

        # Create and checkout new branch
        assert git_utils.create_branch("feature/test") is True

        # Update heads dict to simulate branch creation
        mock_repo.heads = {"main": mock_main, "feature/test": mock_feature}
        mock_repo.active_branch = mock_feature

        # Verify branch was created
        branches = git_utils.list_branches()
        assert "feature/test" in branches
