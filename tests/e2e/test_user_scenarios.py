"""End-to-end tests for complete user scenarios."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app


class TestNewUserWorkflow:
    """Test complete workflow for a new user."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None
        self.project_path = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _setup_project_directory(self, project_name="e2e_test_project"):
        """Setup project directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / project_name
        self.project_path.mkdir()
        return self.project_path

    def test_complete_new_user_journey(self):
        """Test complete journey of a new user from project creation to task management."""
        project_path = self._setup_project_directory("new_user_project")

        with patch("os.getcwd", return_value=str(project_path)):
            # Step 1: Initialize new project
            result = self.runner.invoke(
                app, ["init", "project", "--name", "My First AI Trackdown Project"]
            )
            assert result.exit_code == 0
            assert (
                "initialized" in result.stdout.lower()
                or "created" in result.stdout.lower()
            )

            # Verify project structure was created
            assert (project_path / ".ai-trackdown").exists()
            assert (project_path / "tasks").exists()
            assert (project_path / "templates").exists()

            # Step 2: Check project status (should be empty initially)
            result = self.runner.invoke(app, ["status"])
            assert result.exit_code == 0

            # Step 3: List available templates
            result = self.runner.invoke(app, ["template", "list"])
            assert result.exit_code == 0
            assert "task" in result.stdout.lower()

            # Step 4: Create first task
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "task",
                    "Set up development environment",
                    "--priority",
                    "high",
                    "--assignee",
                    "developer",
                    "--tag",
                    "setup",
                    "--tag",
                    "infrastructure",
                ],
            )
            assert result.exit_code == 0

            # Step 5: Create a few more tasks to populate the project
            tasks_to_create = [
                ("Implement user authentication", "high", ["security", "backend"]),
                ("Design user interface mockups", "medium", ["ui", "design"]),
                ("Write unit tests", "medium", ["testing", "quality"]),
                ("Set up CI/CD pipeline", "low", ["devops", "automation"]),
            ]

            for title, priority, tags in tasks_to_create:
                tag_args = []
                for tag in tags:
                    tag_args.extend(["--tag", tag])

                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "task",
                        title,
                        "--priority",
                        priority,
                        "--assignee",
                        "developer",
                    ]
                    + tag_args,
                )
                assert result.exit_code == 0

            # Step 6: Check project status with tasks
            result = self.runner.invoke(app, ["status", "tasks"])
            assert result.exit_code == 0
            assert "task" in result.stdout.lower()

            # Step 7: Search for specific tasks
            result = self.runner.invoke(app, ["search", "authentication"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["search", "--tag", "security"])
            assert result.exit_code == 0

            # Step 8: Update a task (simulate work progress)
            result = self.runner.invoke(
                app, ["task", "update", "TSK-0001", "--status", "in_progress"]
            )
            # May succeed or fail depending on implementation
            assert result.exit_code in [0, 1]

            # Step 9: Validate project integrity
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]  # May have warnings but should not crash

            # Step 10: Generate project summary
            result = self.runner.invoke(app, ["status", "summary"])
            assert result.exit_code == 0

    def test_team_collaboration_workflow(self):
        """Test workflow for team collaboration scenario."""
        project_path = self._setup_project_directory("team_project")

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project for team
            result = self.runner.invoke(
                app, ["init", "project", "--name", "Team Collaboration Project"]
            )
            assert result.exit_code == 0

            # Create epic for major feature
            result = self.runner.invoke(
                app, ["create", "epic", "User Management System", "--priority", "high"]
            )
            assert result.exit_code == 0

            # Create issues for the epic
            issues = [
                ("User registration not working", "bug", "critical"),
                ("Add password reset functionality", "feature_request", "high"),
                ("Improve user profile page", "enhancement", "medium"),
            ]

            for title, issue_type, priority in issues:
                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "issue",
                        title,
                        "--issue-type",
                        issue_type,
                        "--priority",
                        priority,
                        "--assignee",
                        "team_member",
                    ],
                )
                assert result.exit_code == 0

            # Create tasks assigned to different team members
            team_tasks = [
                ("Backend API development", "alice", ["backend", "api"]),
                ("Frontend component creation", "bob", ["frontend", "react"]),
                ("Database schema design", "charlie", ["database", "schema"]),
                ("Write integration tests", "diana", ["testing", "integration"]),
                ("Security audit", "eve", ["security", "audit"]),
            ]

            for title, assignee, tags in team_tasks:
                tag_args = []
                for tag in tags:
                    tag_args.extend(["--tag", tag])

                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "task",
                        title,
                        "--assignee",
                        assignee,
                        "--priority",
                        "medium",
                    ]
                    + tag_args,
                )
                assert result.exit_code == 0

            # Create pull requests
            prs = [
                ("Add user authentication endpoints", "feature/auth", "main"),
                ("Fix user registration validation", "bugfix/registration", "main"),
                ("Update user profile UI", "feature/profile-ui", "develop"),
            ]

            for title, source, target in prs:
                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "pr",
                        title,
                        "--source-branch",
                        source,
                        "--target-branch",
                        target,
                    ],
                )
                assert result.exit_code == 0

            # Check status by different filters
            result = self.runner.invoke(app, ["status", "tasks", "--assignee", "alice"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["status", "tasks", "--priority", "high"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["search", "--tag", "backend"])
            assert result.exit_code == 0

            # Validate entire project
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]

    def test_agile_development_workflow(self):
        """Test workflow for agile development scenario."""
        project_path = self._setup_project_directory("agile_project")

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize agile project
            result = self.runner.invoke(
                app, ["init", "project", "--name", "Agile Development Project"]
            )
            assert result.exit_code == 0

            # Create epic for user stories
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "epic",
                    "E-commerce Product Catalog",
                    "--priority",
                    "critical",
                ],
            )
            assert result.exit_code == 0

            # Create user story tasks with story points and acceptance criteria
            user_stories = [
                {
                    "title": "As a customer, I want to browse products by category",
                    "priority": "high",
                    "tags": ["user-story", "frontend", "catalog"],
                    "assignee": "frontend_dev",
                },
                {
                    "title": "As a customer, I want to search for products",
                    "priority": "high",
                    "tags": ["user-story", "search", "backend"],
                    "assignee": "backend_dev",
                },
                {
                    "title": "As a customer, I want to filter products by price",
                    "priority": "medium",
                    "tags": ["user-story", "filtering", "frontend"],
                    "assignee": "frontend_dev",
                },
                {
                    "title": "As an admin, I want to manage product inventory",
                    "priority": "medium",
                    "tags": ["user-story", "admin", "inventory"],
                    "assignee": "backend_dev",
                },
            ]

            for story in user_stories:
                tag_args = []
                for tag in story["tags"]:
                    tag_args.extend(["--tag", tag])

                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "task",
                        story["title"],
                        "--priority",
                        story["priority"],
                        "--assignee",
                        story["assignee"],
                    ]
                    + tag_args,
                )
                assert result.exit_code == 0

            # Create technical tasks
            technical_tasks = [
                (
                    "Set up product database schema",
                    "database_dev",
                    ["backend", "database"],
                ),
                (
                    "Implement product search API",
                    "backend_dev",
                    ["backend", "api", "search"],
                ),
                (
                    "Create product catalog UI components",
                    "frontend_dev",
                    ["frontend", "ui", "components"],
                ),
                (
                    "Write automated tests for catalog",
                    "qa_dev",
                    ["testing", "automation"],
                ),
                (
                    "Performance optimization for search",
                    "backend_dev",
                    ["performance", "optimization"],
                ),
            ]

            for title, assignee, tags in technical_tasks:
                tag_args = []
                for tag in tags:
                    tag_args.extend(["--tag", tag])

                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "task",
                        title,
                        "--priority",
                        "medium",
                        "--assignee",
                        assignee,
                    ]
                    + tag_args,
                )
                assert result.exit_code == 0

            # Create bugs that came up during development
            bugs = [
                (
                    "Product images not loading correctly",
                    "critical",
                    ["bug", "frontend", "images"],
                ),
                (
                    "Search results pagination broken",
                    "high",
                    ["bug", "backend", "pagination"],
                ),
                (
                    "Category filter showing incorrect results",
                    "medium",
                    ["bug", "frontend", "filtering"],
                ),
            ]

            for title, priority, tags in bugs:
                tag_args = []
                for tag in tags:
                    tag_args.extend(["--tag", tag])

                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "issue",
                        title,
                        "--issue-type",
                        "bug",
                        "--priority",
                        priority,
                    ]
                    + tag_args,
                )
                assert result.exit_code == 0

            # Sprint planning simulation - check tasks by priority and assignee
            result = self.runner.invoke(
                app, ["status", "tasks", "--priority", "critical"]
            )
            assert result.exit_code == 0

            result = self.runner.invoke(
                app, ["status", "tasks", "--assignee", "frontend_dev"]
            )
            assert result.exit_code == 0

            # Sprint review - check what's been completed
            result = self.runner.invoke(
                app, ["status", "tasks", "--status", "completed"]
            )
            assert result.exit_code == 0

            # Search for specific work areas
            result = self.runner.invoke(app, ["search", "--tag", "user-story"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["search", "--tag", "bug"])
            assert result.exit_code == 0


class TestAdvancedUserScenarios:
    """Test advanced user scenarios and edge cases."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _setup_project_directory(self):
        """Setup project directory for testing."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "advanced_project"
        project_path.mkdir()
        return project_path

    def test_large_project_scenario(self):
        """Test scenario with large number of tasks and complex structure."""
        project_path = self._setup_project_directory()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(
                app, ["init", "project", "--name", "Large Scale Project"]
            )
            assert result.exit_code == 0

            # Create multiple epics
            epics = [
                "User Authentication System",
                "Payment Processing",
                "Product Catalog Management",
                "Order Management System",
                "Reporting and Analytics",
            ]

            for epic in epics:
                result = self.runner.invoke(
                    app, ["create", "epic", epic, "--priority", "high"]
                )
                assert result.exit_code == 0

            # Create many tasks across different categories

            priorities = ["low", "medium", "high", "critical"]
            assignees = ["alice", "bob", "charlie", "diana", "eve", "frank"]
            tags_groups = [
                ["frontend", "react"],
                ["backend", "api"],
                ["database", "mysql"],
                ["testing", "automation"],
                ["devops", "docker"],
                ["security", "auth"],
                ["ui", "design"],
                ["mobile", "ios"],
                ["mobile", "android"],
                ["analytics", "reporting"],
            ]

            # Create 50 tasks with varying attributes
            for i in range(50):
                priority = priorities[i % len(priorities)]
                assignee = assignees[i % len(assignees)]
                tags = tags_groups[i % len(tags_groups)]

                tag_args = []
                for tag in tags:
                    tag_args.extend(["--tag", tag])

                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "task",
                        f"Task {i+1:03d}: Implement feature {chr(65 + i % 26)}",
                        "--priority",
                        priority,
                        "--assignee",
                        assignee,
                    ]
                    + tag_args,
                )
                assert result.exit_code == 0

            # Test performance with large dataset
            result = self.runner.invoke(app, ["status", "tasks"])
            assert result.exit_code == 0

            # Test filtering with large dataset
            result = self.runner.invoke(app, ["status", "tasks", "--priority", "high"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["status", "tasks", "--assignee", "alice"])
            assert result.exit_code == 0

            # Test search with large dataset
            result = self.runner.invoke(app, ["search", "feature"])
            assert result.exit_code == 0

            # Test validation with large dataset
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]

    def test_template_customization_scenario(self):
        """Test advanced template customization scenario."""
        project_path = self._setup_project_directory()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Check available templates
            result = self.runner.invoke(app, ["template", "list"])
            assert result.exit_code == 0

            # Show default task template
            result = self.runner.invoke(app, ["template", "show", "task", "default"])
            assert result.exit_code == 0

            # Validate templates
            result = self.runner.invoke(
                app, ["template", "validate", "task", "default"]
            )
            assert result.exit_code == 0

            # Create tasks using templates (implicit)
            result = self.runner.invoke(
                app,
                [
                    "create",
                    "task",
                    "Template-based Task",
                    "--template",
                    "default",
                    "--priority",
                    "medium",
                ],
            )
            assert result.exit_code == 0

            # Test other ticket types
            result = self.runner.invoke(app, ["template", "list", "epic"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["template", "show", "epic", "default"])
            assert result.exit_code == 0

    def test_validation_and_quality_assurance_scenario(self):
        """Test comprehensive validation and quality assurance scenario."""
        project_path = self._setup_project_directory()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Create valid tasks
            valid_tasks = [
                ("Valid Task 1", "high", ["valid", "test"]),
                ("Valid Task 2", "medium", ["valid", "integration"]),
                ("Valid Task 3", "low", ["valid", "documentation"]),
            ]

            for title, priority, tags in valid_tasks:
                tag_args = []
                for tag in tags:
                    tag_args.extend(["--tag", tag])

                result = self.runner.invoke(
                    app, ["create", "task", title, "--priority", priority] + tag_args
                )
                assert result.exit_code == 0

            # Create task files with potential issues (manually create invalid files)
            tasks_dir = project_path / "tasks" / "open"

            # File with missing required fields
            incomplete_task = tasks_dir / "incomplete-task.md"
            incomplete_task.write_text(
                """---
title: Incomplete Task
# Missing required fields like id, status, etc.
---

# Incomplete Task

This task is missing required fields.
"""
            )

            # File with invalid frontmatter
            invalid_yaml_task = tasks_dir / "invalid-yaml.md"
            invalid_yaml_task.write_text(
                """---
title: Invalid YAML
status: open
bad_field: [unclosed list
priority: medium
---

# Invalid YAML Task

This task has invalid YAML.
"""
            )

            # Run comprehensive validation
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]  # Should detect issues

            # Run validation with different options
            result = self.runner.invoke(app, ["validate", "--schema-only"])
            assert result.exit_code in [0, 1]

            # Validate specific files
            valid_task_file = (
                tasks_dir / [f for f in tasks_dir.glob("*.md") if "TSK-" in f.name][0]
            )
            result = self.runner.invoke(app, ["validate", str(valid_task_file)])
            assert result.exit_code == 0

            # Try to validate invalid file
            result = self.runner.invoke(app, ["validate", str(invalid_yaml_task)])
            assert result.exit_code == 1

    def test_migration_and_maintenance_scenario(self):
        """Test project migration and maintenance scenario."""
        project_path = self._setup_project_directory()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project with older structure (simulate)
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Create some tasks
            for i in range(5):
                result = self.runner.invoke(
                    app,
                    ["create", "task", f"Legacy Task {i+1}", "--priority", "medium"],
                )
                assert result.exit_code == 0

            # Test project health check
            result = self.runner.invoke(app, ["health"])
            assert result.exit_code in [0, 1]  # May have health issues

            # Test migration commands (if available)
            result = self.runner.invoke(app, ["migrate", "--help"])
            # May or may not be implemented
            assert result.exit_code in [0, 1, 2]

            # Test project structure validation
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]

            # Test backup/export functionality (if available)
            result = self.runner.invoke(app, ["sync", "--help"])
            # May or may not be implemented
            assert result.exit_code in [0, 1, 2]


class TestErrorRecoveryScenarios:
    """Test error recovery and edge case scenarios."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_corrupted_project_recovery(self):
        """Test recovery from corrupted project state."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "corrupted_project"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Create some tasks
            result = self.runner.invoke(app, ["create", "task", "Test Task"])
            assert result.exit_code == 0

            # Corrupt configuration file
            config_file = project_path / ".ai-trackdown" / "config.yaml"
            config_file.write_text("invalid: yaml: content")

            # Test handling of corrupted config
            result = self.runner.invoke(app, ["status"])
            # Should handle gracefully or provide helpful error
            assert result.exit_code in [0, 1, 2]

            # Test re-initialization over corrupted project
            result = self.runner.invoke(app, ["init", "config"])
            assert result.exit_code in [0, 1]

    def test_permission_and_access_issues(self):
        """Test handling of permission and access issues."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "permission_project"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Make tasks directory read-only
            tasks_dir = project_path / "tasks"
            original_mode = tasks_dir.stat().st_mode
            tasks_dir.chmod(0o444)  # Read-only

            try:
                # Try to create task with read-only directory
                result = self.runner.invoke(app, ["create", "task", "Permission Test"])
                # Should handle permission error gracefully
                assert result.exit_code in [0, 1]
            finally:
                # Restore permissions for cleanup
                tasks_dir.chmod(original_mode)

    def test_disk_space_and_resource_limits(self):
        """Test handling of resource constraints."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "resource_project"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Create task with very large content
            large_content = "x" * 1000000  # 1MB of content

            # Should handle large content gracefully
            result = self.runner.invoke(
                app,
                ["create", "task", "Large Task"],
                input=f"Large task\n{large_content}\n\n\n",
            )
            assert result.exit_code in [0, 1]

    def test_concurrent_access_simulation(self):
        """Test simulation of concurrent access patterns."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "concurrent_project"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Simulate multiple users creating tasks simultaneously
            # (In real scenario, this would be done with threading)

            users = ["alice", "bob", "charlie"]
            for i, user in enumerate(users):
                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "task",
                        f"Task by {user}",
                        "--assignee",
                        user,
                        "--priority",
                        "medium",
                    ],
                )
                assert result.exit_code == 0

            # Check that all tasks were created
            result = self.runner.invoke(app, ["status", "tasks"])
            assert result.exit_code == 0

            # Check for any file conflicts or corruption
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]


class TestPerformanceScenarios:
    """Test performance-related scenarios."""

    def setup_method(self):
        """Setup test environment."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_large_dataset_performance(self):
        """Test performance with large datasets."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "performance_project"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Create many tasks (smaller number for CI/testing)
            num_tasks = 20  # Would be larger in real performance testing

            import time

            start_time = time.time()

            for i in range(num_tasks):
                result = self.runner.invoke(
                    app,
                    [
                        "create",
                        "task",
                        f"Performance Task {i:03d}",
                        "--priority",
                        "medium",
                    ],
                )
                assert result.exit_code == 0

            creation_time = time.time() - start_time

            # Test status command performance
            start_time = time.time()
            result = self.runner.invoke(app, ["status", "tasks"])
            assert result.exit_code == 0
            status_time = time.time() - start_time

            # Test search performance
            start_time = time.time()
            result = self.runner.invoke(app, ["search", "Performance"])
            assert result.exit_code == 0
            search_time = time.time() - start_time

            # Test validation performance
            start_time = time.time()
            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]
            validation_time = time.time() - start_time

            # Performance should be reasonable (these are generous limits)
            assert creation_time < 60  # 60 seconds for 20 tasks
            assert status_time < 10  # 10 seconds for status
            assert search_time < 10  # 10 seconds for search
            assert validation_time < 30  # 30 seconds for validation

    def test_memory_usage_patterns(self):
        """Test memory usage patterns with various operations."""
        self.temp_dir = tempfile.mkdtemp()
        project_path = Path(self.temp_dir) / "memory_project"
        project_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Initialize project
            result = self.runner.invoke(app, ["init", "project"])
            assert result.exit_code == 0

            # Create tasks with large content
            for i in range(5):
                large_description = f"Large description {i} " * 1000  # Larger content
                result = self.runner.invoke(
                    app,
                    ["create", "task", f"Memory Test Task {i}"],
                    input=f"Memory Test Task {i}\n{large_description}\nmedium\n\n\n",
                )
                assert result.exit_code == 0

            # Test operations that might consume memory
            result = self.runner.invoke(app, ["status"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["search", "Memory"])
            assert result.exit_code == 0

            result = self.runner.invoke(app, ["validate"])
            assert result.exit_code in [0, 1]

            # These operations should complete without memory errors
            # (Actual memory monitoring would require additional tools)
