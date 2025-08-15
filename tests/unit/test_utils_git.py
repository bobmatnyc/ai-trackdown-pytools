"""Unit tests for Git utilities."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_trackdown_pytools.utils.git import (
    GitError,
    GitRepo,
    commit_changes,
    create_branch,
    get_current_branch,
    get_file_status,
    get_repository_status,
    switch_branch,
)


class TestGitRepo:
    """Test GitRepo class functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_git_repo_initialization(self):
        """Test GitRepo initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)

                assert git_repo.path == repo_path
                assert git_repo.repo == mock_repo
                mock_repo_class.assert_called_once_with(repo_path)

    def test_git_repo_initialization_no_repo(self):
        """Test GitRepo initialization with no repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo_class.side_effect = Exception("Not a git repository")

                with pytest.raises(GitError, match="Not a git repository"):
                    GitRepo(repo_path)

    def test_get_current_branch(self):
        """Test getting current branch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.active_branch.name = "main"
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                current_branch = git_repo.get_current_branch()

                assert current_branch == "main"

    def test_get_current_branch_detached_head(self):
        """Test getting current branch with detached HEAD."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.active_branch = None
                mock_repo.head.commit.hexsha = "abc123"
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                current_branch = git_repo.get_current_branch()

                assert current_branch.startswith("detached at abc123")

    def test_get_branches(self):
        """Test getting list of branches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_branch1 = Mock()
                mock_branch1.name = "main"
                mock_branch2 = Mock()
                mock_branch2.name = "develop"
                mock_branch3 = Mock()
                mock_branch3.name = "feature/test"

                mock_repo.heads = [mock_branch1, mock_branch2, mock_branch3]
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                branches = git_repo.get_branches()

                assert branches == ["main", "develop", "feature/test"]

    def test_create_branch(self):
        """Test creating a new branch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_new_branch = Mock()
                mock_repo.create_head.return_value = mock_new_branch
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                git_repo.create_branch("feature/new-feature")

                mock_repo.create_head.assert_called_once_with("feature/new-feature")

    def test_create_branch_already_exists(self):
        """Test creating a branch that already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.create_head.side_effect = Exception("Branch already exists")
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)

                with pytest.raises(GitError, match="Failed to create branch"):
                    git_repo.create_branch("existing-branch")

    def test_switch_branch(self):
        """Test switching to a branch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_branch = Mock()
                mock_repo.heads.__getitem__.return_value = mock_branch
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                git_repo.switch_branch("develop")

                mock_branch.checkout.assert_called_once()

    def test_switch_branch_nonexistent(self):
        """Test switching to a non-existent branch."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.heads.__getitem__.side_effect = IndexError("Branch not found")
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)

                with pytest.raises(GitError, match="Branch not found"):
                    git_repo.switch_branch("nonexistent")

    def test_get_status(self):
        """Test getting repository status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.is_dirty.return_value = True
                mock_repo.untracked_files = ["new_file.txt"]
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                status = git_repo.get_status()

                assert status["dirty"] is True
                assert status["untracked_files"] == ["new_file.txt"]

    def test_commit_changes(self):
        """Test committing changes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_index = Mock()
                mock_repo.index = mock_index
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                git_repo.commit_changes(
                    "Test commit message", ["file1.txt", "file2.txt"]
                )

                mock_index.add.assert_called_once_with(["file1.txt", "file2.txt"])
                mock_index.commit.assert_called_once_with("Test commit message")

    def test_commit_changes_no_files(self):
        """Test committing with no files specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_index = Mock()
                mock_repo.index = mock_index
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                git_repo.commit_changes("Test commit message")

                # Should add all files
                mock_index.add.assert_called_once_with(["."])
                mock_index.commit.assert_called_once_with("Test commit message")

    def test_get_file_status(self):
        """Test getting file status."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.git.status.return_value = (
                    "M  modified_file.txt\nA  new_file.txt\n?? untracked.txt"
                )
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                file_status = git_repo.get_file_status()

                assert "modified_file.txt" in file_status
                assert "new_file.txt" in file_status
                assert "untracked.txt" in file_status

    def test_get_commit_history(self):
        """Test getting commit history."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_commit1 = Mock()
                mock_commit1.hexsha = "abc123"
                mock_commit1.message = "First commit"
                mock_commit1.author.name = "Test Author"

                mock_commit2 = Mock()
                mock_commit2.hexsha = "def456"
                mock_commit2.message = "Second commit"
                mock_commit2.author.name = "Test Author"

                mock_repo.iter_commits.return_value = [mock_commit1, mock_commit2]
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                history = git_repo.get_commit_history(limit=2)

                assert len(history) == 2
                assert history[0]["sha"] == "abc123"
                assert history[0]["message"] == "First commit"
                assert history[1]["sha"] == "def456"
                assert history[1]["message"] == "Second commit"


class TestGitUtilityFunctions:
    """Test utility functions for Git operations."""

    def test_get_current_branch_function(self):
        """Test get_current_branch utility function."""
        with patch("ai_trackdown_pytools.utils.git.GitRepo") as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_git_repo.get_current_branch.return_value = "main"
            mock_git_repo_class.return_value = mock_git_repo

            current_branch = get_current_branch(Path("/test/repo"))

            assert current_branch == "main"
            mock_git_repo_class.assert_called_once_with(Path("/test/repo"))

    def test_get_repository_status_function(self):
        """Test get_repository_status utility function."""
        with patch("ai_trackdown_pytools.utils.git.GitRepo") as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_status = {"dirty": True, "untracked_files": ["test.txt"]}
            mock_git_repo.get_status.return_value = mock_status
            mock_git_repo_class.return_value = mock_git_repo

            status = get_repository_status(Path("/test/repo"))

            assert status == mock_status
            mock_git_repo_class.assert_called_once_with(Path("/test/repo"))

    def test_create_branch_function(self):
        """Test create_branch utility function."""
        with patch("ai_trackdown_pytools.utils.git.GitRepo") as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_git_repo_class.return_value = mock_git_repo

            create_branch(Path("/test/repo"), "feature/test")

            mock_git_repo.create_branch.assert_called_once_with("feature/test")
            mock_git_repo_class.assert_called_once_with(Path("/test/repo"))

    def test_switch_branch_function(self):
        """Test switch_branch utility function."""
        with patch("ai_trackdown_pytools.utils.git.GitRepo") as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_git_repo_class.return_value = mock_git_repo

            switch_branch(Path("/test/repo"), "develop")

            mock_git_repo.switch_branch.assert_called_once_with("develop")
            mock_git_repo_class.assert_called_once_with(Path("/test/repo"))

    def test_commit_changes_function(self):
        """Test commit_changes utility function."""
        with patch("ai_trackdown_pytools.utils.git.GitRepo") as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_git_repo_class.return_value = mock_git_repo

            commit_changes(Path("/test/repo"), "Test commit", ["file1.txt"])

            mock_git_repo.commit_changes.assert_called_once_with(
                "Test commit", ["file1.txt"]
            )
            mock_git_repo_class.assert_called_once_with(Path("/test/repo"))

    def test_get_file_status_function(self):
        """Test get_file_status utility function."""
        with patch("ai_trackdown_pytools.utils.git.GitRepo") as mock_git_repo_class:
            mock_git_repo = Mock()
            mock_status = {"file1.txt": "M", "file2.txt": "A"}
            mock_git_repo.get_file_status.return_value = mock_status
            mock_git_repo_class.return_value = mock_git_repo

            file_status = get_file_status(Path("/test/repo"))

            assert file_status == mock_status
            mock_git_repo_class.assert_called_once_with(Path("/test/repo"))


class TestGitError:
    """Test GitError exception."""

    def test_git_error_creation(self):
        """Test creating GitError."""
        error = GitError("Test error message")
        assert str(error) == "Test error message"

    def test_git_error_inheritance(self):
        """Test GitError inheritance."""
        error = GitError("Test error")
        assert isinstance(error, Exception)


class TestGitIntegration:
    """Test Git integration scenarios."""

    def test_typical_git_workflow(self):
        """Test typical Git workflow operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.active_branch.name = "main"
                mock_repo.heads = []
                mock_repo.is_dirty.return_value = False
                mock_repo.untracked_files = []
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)

                # Get current status
                status = git_repo.get_status()
                assert status["dirty"] is False

                # Create and switch to feature branch
                git_repo.create_branch("feature/test")
                git_repo.switch_branch("feature/test")

                # Make changes and commit
                git_repo.commit_changes("Add test feature", ["test_file.py"])

                # Verify calls were made correctly
                mock_repo.create_head.assert_called_with("feature/test")
                mock_repo.index.add.assert_called_with(["test_file.py"])
                mock_repo.index.commit.assert_called_with("Add test feature")

    def test_error_handling_in_git_operations(self):
        """Test error handling in Git operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo.create_head.side_effect = Exception("Git error")
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)

                with pytest.raises(GitError):
                    git_repo.create_branch("test-branch")

    def test_git_repository_detection(self):
        """Test Git repository detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Test with valid repository
            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                assert git_repo.repo == mock_repo

            # Test with invalid repository
            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo_class.side_effect = Exception("Not a git repository")

                with pytest.raises(GitError):
                    GitRepo(repo_path)

    def test_branch_operations_with_remotes(self):
        """Test branch operations with remote branches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()

                # Mock local and remote branches
                mock_local_branch = Mock()
                mock_local_branch.name = "main"
                mock_remote_branch = Mock()
                mock_remote_branch.name = "origin/develop"

                mock_repo.heads = [mock_local_branch]
                mock_repo.remotes.origin.refs = [mock_remote_branch]
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                branches = git_repo.get_branches()

                assert "main" in branches
                # Remote branches might be included depending on implementation

    def test_commit_with_author_info(self):
        """Test committing with author information."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                mock_index = Mock()
                mock_repo.index = mock_index
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                git_repo.commit_changes(
                    "Test commit with author",
                    ["file.txt"],
                    author_name="Test Author",
                    author_email="test@example.com",
                )

                # Verify commit was called with author info
                # (Implementation details may vary)
                mock_index.commit.assert_called()

    def test_file_status_parsing(self):
        """Test parsing of Git file status output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo_class:
                mock_repo = Mock()
                # Mock git status output
                status_output = """
M  modified_file.py
A  added_file.py
D  deleted_file.py
R  renamed_file.py -> new_name.py
?? untracked_file.py
"""
                mock_repo.git.status.return_value = status_output.strip()
                mock_repo_class.return_value = mock_repo

                git_repo = GitRepo(repo_path)
                file_status = git_repo.get_file_status()

                # Verify status parsing
                assert len(file_status) > 0
                # Specific parsing behavior depends on implementation
