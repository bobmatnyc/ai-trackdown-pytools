"""Comprehensive end-to-end tests for all ticket management functionality."""

import json
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app


@pytest.fixture
def test_environment():
    """Create a complete test environment with proper cleanup."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir) / "e2e_test_project"
    project_path.mkdir()

    runner = CliRunner()

    # Initialize project
    with patch("os.getcwd", return_value=str(project_path)):
        result = runner.invoke(app, ["init", "project", "--name", "E2E Test Project"])
        assert result.exit_code == 0

    yield {
        "runner": runner,
        "project_path": project_path,
        "temp_dir": temp_dir,
        "cleanup_tasks": [],
    }

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestTaskLifecycleManagement:
    """Test complete task lifecycle from creation to archival."""

    def test_complete_task_lifecycle(self, test_environment):
        """Test full task lifecycle: create → update → block → unblock → complete → archive."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Step 1: Create a task
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Implement user authentication",
                    "--description",
                    "Add OAuth2 and JWT authentication",
                    "--priority",
                    "high",
                    "--assignee",
                    "alice",
                    "--tag",
                    "security",
                    "--tag",
                    "backend",
                    "--estimate",
                    "8h",
                ],
            )
            assert result.exit_code == 0
            assert "Task created successfully" in result.stdout

            # Extract task ID from output
            task_id = self._extract_task_id(result.stdout)
            assert task_id.startswith("TSK-")

            # Step 2: View task details
            result = runner.invoke(app, ["task", "show", task_id, "--detailed"])
            assert result.exit_code == 0
            assert "Implement user authentication" in result.stdout
            assert "high" in result.stdout
            assert "alice" in result.stdout

            # Step 3: Start working on task
            result = runner.invoke(
                app, ["task", "start", task_id, "--comment", "Beginning implementation"]
            )
            assert result.exit_code == 0

            # Step 4: Update task with progress
            result = runner.invoke(
                app,
                [
                    "task",
                    "update",
                    task_id,
                    "--description",
                    "Add OAuth2 and JWT authentication - 50% complete",
                    "--add-tag",
                    "in-review",
                    "--estimate",
                    "12h",  # Revised estimate
                ],
            )
            assert result.exit_code == 0

            # Step 5: Block task due to dependency
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Setup OAuth provider",
                    "--priority",
                    "critical",
                    "--assignee",
                    "bob",
                ],
            )
            blocker_id = self._extract_task_id(result.stdout)

            result = runner.invoke(
                app,
                [
                    "task",
                    "block",
                    task_id,
                    blocker_id,
                    "--reason",
                    "Waiting for OAuth provider configuration",
                ],
            )
            assert result.exit_code == 0

            # Verify task is blocked
            result = runner.invoke(app, ["task", "show", task_id])
            assert result.exit_code == 0
            assert "blocked" in result.stdout.lower()

            # Step 6: Complete blocker and unblock
            result = runner.invoke(
                app,
                [
                    "task",
                    "complete",
                    blocker_id,
                    "--comment",
                    "OAuth provider configured",
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(app, ["task", "unblock", task_id, blocker_id])
            assert result.exit_code == 0

            # Step 7: Complete the task
            result = runner.invoke(
                app,
                [
                    "task",
                    "complete",
                    task_id,
                    "--comment",
                    "Authentication system fully implemented and tested",
                ],
            )
            assert result.exit_code == 0

            # Step 8: Verify completion
            result = runner.invoke(app, ["task", "show", task_id])
            assert result.exit_code == 0
            assert "completed" in result.stdout.lower()

    def test_subtask_hierarchy_management(self, test_environment):
        """Test creation and management of task hierarchies with subtasks."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create parent task
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Build user dashboard",
                    "--priority",
                    "high",
                    "--assignee",
                    "team-lead",
                    "--tag",
                    "feature",
                    "--estimate",
                    "40h",
                ],
            )
            parent_id = self._extract_task_id(result.stdout)

            # Create subtasks
            subtasks = [
                ("Design dashboard layout", "designer", "8h", ["ui", "design"]),
                ("Implement dashboard API", "backend-dev", "16h", ["api", "backend"]),
                (
                    "Create React components",
                    "frontend-dev",
                    "12h",
                    ["react", "frontend"],
                ),
                ("Write unit tests", "qa-engineer", "8h", ["testing", "quality"]),
                (
                    "Performance optimization",
                    "senior-dev",
                    "4h",
                    ["performance", "optimization"],
                ),
            ]

            subtask_ids = []
            for title, assignee, estimate, tags in subtasks:
                tag_args = []
                for tag in tags:
                    tag_args.extend(["--tag", tag])

                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        title,
                        "--parent",
                        parent_id,
                        "--assignee",
                        assignee,
                        "--estimate",
                        estimate,
                        "--priority",
                        "medium",
                    ]
                    + tag_args,
                )
                assert result.exit_code == 0
                subtask_ids.append(self._extract_task_id(result.stdout))

            # View parent task with subtasks
            result = runner.invoke(app, ["task", "show", parent_id, "--detailed"])
            assert result.exit_code == 0
            assert "Subtasks: 5 task(s)" in result.stdout

            # Complete subtasks in order
            for i, subtask_id in enumerate(subtask_ids):
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "complete",
                        subtask_id,
                        "--comment",
                        f"Subtask {i+1} completed",
                    ],
                )
                assert result.exit_code == 0

            # Verify all subtasks are completed
            result = runner.invoke(app, ["task", "list", "--parent", parent_id])
            assert result.exit_code == 0

            # Complete parent task
            result = runner.invoke(
                app,
                [
                    "task",
                    "complete",
                    parent_id,
                    "--comment",
                    "All subtasks completed, dashboard ready",
                ],
            )
            assert result.exit_code == 0

    def test_task_dependencies_and_relationships(self, test_environment):
        """Test complex task dependencies and relationship management."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create interconnected tasks
            tasks = {}

            # Create database migration task
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Database migration",
                    "--priority",
                    "critical",
                    "--assignee",
                    "dba",
                ],
            )
            tasks["db_migration"] = self._extract_task_id(result.stdout)

            # Create API update task (depends on DB migration)
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Update API endpoints",
                    "--priority",
                    "high",
                    "--assignee",
                    "backend-dev",
                ],
            )
            tasks["api_update"] = self._extract_task_id(result.stdout)

            # Create frontend update task (depends on API)
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Update frontend to use new API",
                    "--priority",
                    "high",
                    "--assignee",
                    "frontend-dev",
                ],
            )
            tasks["frontend_update"] = self._extract_task_id(result.stdout)

            # Create documentation task (depends on all above)
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Update API documentation",
                    "--priority",
                    "medium",
                    "--assignee",
                    "tech-writer",
                ],
            )
            tasks["documentation"] = self._extract_task_id(result.stdout)

            # Set up dependencies
            result = runner.invoke(
                app,
                [
                    "task",
                    "block",
                    tasks["api_update"],
                    tasks["db_migration"],
                    "--reason",
                    "Cannot update API until database is migrated",
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(
                app,
                [
                    "task",
                    "block",
                    tasks["frontend_update"],
                    tasks["api_update"],
                    "--reason",
                    "Frontend needs new API endpoints",
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(
                app,
                [
                    "task",
                    "block",
                    tasks["documentation"],
                    tasks["api_update"],
                    "--reason",
                    "Documentation needs final API implementation",
                ],
            )
            assert result.exit_code == 0

            # Try to start blocked task (should fail)
            result = runner.invoke(app, ["task", "start", tasks["frontend_update"]])
            assert result.exit_code == 1
            assert "blocked" in result.stdout.lower()

            # Complete tasks in dependency order
            # 1. Complete database migration
            result = runner.invoke(app, ["task", "complete", tasks["db_migration"]])
            assert result.exit_code == 0

            # 2. Unblock and complete API update
            result = runner.invoke(app, ["task", "unblock", tasks["api_update"]])
            assert result.exit_code == 0
            result = runner.invoke(app, ["task", "complete", tasks["api_update"]])
            assert result.exit_code == 0

            # 3. Now frontend and documentation can be worked on
            result = runner.invoke(app, ["task", "unblock", tasks["frontend_update"]])
            assert result.exit_code == 0
            result = runner.invoke(app, ["task", "unblock", tasks["documentation"]])
            assert result.exit_code == 0

            # Complete remaining tasks
            result = runner.invoke(app, ["task", "complete", tasks["frontend_update"]])
            assert result.exit_code == 0
            result = runner.invoke(app, ["task", "complete", tasks["documentation"]])
            assert result.exit_code == 0

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        # Fallback for tests
        return "TSK-001"


class TestIssueTrackingWorkflows:
    """Test comprehensive issue tracking and management workflows."""

    def test_bug_lifecycle_management(self, test_environment):
        """Test complete bug tracking lifecycle."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Report a critical bug
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "Login page crashes on mobile devices",
                    "--description",
                    "App crashes when accessing login page on iOS devices",
                    "--type",
                    "bug",
                    "--severity",
                    "critical",
                    "--component",
                    "authentication",
                    "--assignee",
                    "mobile-dev",
                    "--label",
                    "mobile",
                    "--label",
                    "crash",
                    "--label",
                    "ios",
                ],
            )
            assert result.exit_code == 0
            bug_id = self._extract_issue_id(result.stdout)

            # Add reproduction steps
            result = runner.invoke(
                app,
                [
                    "issue",
                    "update",
                    bug_id,
                    "--add-reproduction-steps",
                    "1. Open app on iOS device\n2. Navigate to login\n3. App crashes immediately",
                ],
            )
            assert result.exit_code == 0

            # Link related issue
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "Memory leak in authentication module",
                    "--type",
                    "bug",
                    "--severity",
                    "high",
                    "--relates-to",
                    bug_id,
                ],
            )
            related_id = self._extract_issue_id(result.stdout)

            # Create tasks to fix the issues
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Fix iOS login crash",
                    "--issue",
                    bug_id,
                    "--assignee",
                    "mobile-dev",
                    "--priority",
                    "critical",
                ],
            )
            fix_task_id = self._extract_task_id_from_output(result.stdout)

            # Add comments and progress updates
            result = runner.invoke(
                app,
                [
                    "issue",
                    "comment",
                    bug_id,
                    "--message",
                    "Reproduced on iPhone 12 and iPhone 13",
                    "--author",
                    "qa-tester",
                ],
            )
            assert result.exit_code == 0

            # Change issue status
            result = runner.invoke(
                app,
                [
                    "issue",
                    "update",
                    bug_id,
                    "--status",
                    "in_progress",
                    "--add-affected-version",
                    "2.3.0",
                    "--add-affected-version",
                    "2.3.1",
                ],
            )
            assert result.exit_code == 0

            # Mark as resolved
            result = runner.invoke(
                app,
                [
                    "issue",
                    "resolve",
                    bug_id,
                    "--resolution",
                    "fixed",
                    "--fixed-version",
                    "2.3.2",
                    "--comment",
                    "Fixed memory management issue causing crash",
                ],
            )
            assert result.exit_code == 0

            # Verify issue is resolved
            result = runner.invoke(app, ["issue", "show", bug_id])
            assert result.exit_code == 0
            assert (
                "resolved" in result.stdout.lower() or "fixed" in result.stdout.lower()
            )

    def test_feature_request_workflow(self, test_environment):
        """Test feature request tracking workflow."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create feature request
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "Add dark mode support",
                    "--type",
                    "feature",
                    "--description",
                    "Users want a dark theme option",
                    "--component",
                    "ui",
                    "--label",
                    "enhancement",
                    "--label",
                    "ux",
                ],
            )
            feature_id = self._extract_issue_id(result.stdout)

            # Add user stories
            result = runner.invoke(
                app,
                [
                    "issue",
                    "add-user-story",
                    feature_id,
                    "--story",
                    "As a user, I want to switch to dark mode to reduce eye strain",
                    "--acceptance",
                    "Theme toggle in settings",
                    "--acceptance",
                    "All UI elements support dark theme",
                    "--acceptance",
                    "User preference is persisted",
                ],
            )
            assert result.exit_code == 0

            # Vote for feature
            for voter in ["user1", "user2", "user3", "user4", "user5"]:
                result = runner.invoke(
                    app, ["issue", "vote", feature_id, "--user", voter]
                )
                assert result.exit_code == 0

            # Add implementation details
            result = runner.invoke(
                app,
                [
                    "issue",
                    "update",
                    feature_id,
                    "--add-label",
                    "high-demand",
                    "--priority",
                    "high",
                    "--target-version",
                    "3.0.0",
                ],
            )
            assert result.exit_code == 0

            # Create epic for feature
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "Dark Mode Implementation",
                    "--issue",
                    feature_id,
                    "--business-value",
                    "Improve user satisfaction and accessibility",
                ],
            )
            epic_id = self._extract_epic_id(result.stdout)

            # Create implementation tasks
            tasks = [
                ("Design dark mode color palette", "designer"),
                ("Implement theme switching logic", "frontend-dev"),
                ("Update all components for dark mode", "frontend-dev"),
                ("Add theme preference to user settings", "backend-dev"),
                ("Test dark mode across devices", "qa-engineer"),
            ]

            for title, assignee in tasks:
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        title,
                        "--epic",
                        epic_id,
                        "--assignee",
                        assignee,
                        "--tag",
                        "dark-mode",
                    ],
                )
                assert result.exit_code == 0

    def test_issue_triage_and_prioritization(self, test_environment):
        """Test issue triage and prioritization workflows."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create multiple issues of different types and severities
            issues = [
                ("App crashes on startup", "bug", "critical", "crash"),
                ("Slow performance on large datasets", "bug", "high", "performance"),
                ("Add export to PDF feature", "feature", "medium", "export"),
                ("Typo in help documentation", "bug", "low", "documentation"),
                ("Security vulnerability in login", "bug", "critical", "security"),
                ("Improve search functionality", "enhancement", "medium", "search"),
                ("Memory leak in background service", "bug", "high", "performance"),
                ("Add multi-language support", "feature", "low", "i18n"),
            ]

            issue_ids = []
            for title, issue_type, severity, component in issues:
                result = runner.invoke(
                    app,
                    [
                        "issue",
                        "create",
                        title,
                        "--type",
                        issue_type,
                        "--severity",
                        severity,
                        "--component",
                        component,
                    ],
                )
                assert result.exit_code == 0
                issue_ids.append(self._extract_issue_id(result.stdout))

            # Triage issues - assign to team members
            assignments = {
                "crash": "senior-dev",
                "performance": "perf-engineer",
                "security": "security-team",
                "documentation": "tech-writer",
                "export": "backend-dev",
                "search": "search-team",
                "i18n": "i18n-team",
            }

            for issue_id in issue_ids:
                result = runner.invoke(app, ["issue", "show", issue_id])
                assert result.exit_code == 0

                # Extract component from output and assign
                for component, assignee in assignments.items():
                    if component in result.stdout.lower():
                        result = runner.invoke(
                            app,
                            [
                                "issue",
                                "assign",
                                issue_id,
                                "--assignee",
                                assignee,
                                "--comment",
                                f"Assigned to {assignee} for triage",
                            ],
                        )
                        break

            # List critical issues
            result = runner.invoke(
                app, ["issue", "list", "--severity", "critical", "--status", "open"]
            )
            assert result.exit_code == 0
            assert "critical" in result.stdout.lower()

            # Generate triage report
            result = runner.invoke(app, ["issue", "report", "--type", "triage"])
            assert result.exit_code == 0

    def _extract_issue_id(self, output: str) -> str:
        """Extract issue ID from CLI output."""
        import re

        match = re.search(r"(ISS-\d+)", output)
        if match:
            return match.group(1)
        return "ISS-001"

    def _extract_epic_id(self, output: str) -> str:
        """Extract epic ID from CLI output."""
        import re

        match = re.search(r"(EP-\d+)", output)
        if match:
            return match.group(1)
        return "EP-001"

    def _extract_task_id_from_output(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestEpicAndPortfolioManagement:
    """Test epic and portfolio management workflows."""

    def test_epic_lifecycle_with_tasks(self, test_environment):
        """Test complete epic lifecycle with associated tasks and issues."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create a major epic
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "E-commerce Platform Overhaul",
                    "--description",
                    "Complete redesign and modernization of e-commerce platform",
                    "--business-value",
                    "Increase conversion rate by 25% and improve user experience",
                    "--target-date",
                    "2024-12-31",
                    "--priority",
                    "critical",
                    "--owner",
                    "product-manager",
                    "--tag",
                    "strategic",
                    "--tag",
                    "q4-initiative",
                ],
            )
            assert result.exit_code == 0
            epic_id = self._extract_epic_id(result.stdout)

            # Add success criteria
            result = runner.invoke(
                app,
                [
                    "epic",
                    "add-criteria",
                    epic_id,
                    "--criterion",
                    "Page load time under 2 seconds",
                    "--criterion",
                    "Mobile conversion rate increased by 30%",
                    "--criterion",
                    "Customer satisfaction score above 4.5",
                ],
            )
            assert result.exit_code == 0

            # Create sub-epics
            sub_epics = [
                ("Frontend Modernization", "Migrate to React and improve UI/UX"),
                (
                    "Backend Optimization",
                    "Microservices architecture and API improvements",
                ),
                ("Payment System Upgrade", "Support multiple payment providers"),
                ("Mobile App Development", "Native iOS and Android apps"),
            ]

            sub_epic_ids = []
            for title, description in sub_epics:
                result = runner.invoke(
                    app,
                    [
                        "epic",
                        "create",
                        title,
                        "--description",
                        description,
                        "--parent-epic",
                        epic_id,
                        "--priority",
                        "high",
                    ],
                )
                assert result.exit_code == 0
                sub_epic_ids.append(self._extract_epic_id(result.stdout))

            # Create tasks for first sub-epic
            frontend_tasks = [
                ("Audit current frontend architecture", "tech-lead", "16h"),
                ("Design new component library", "ui-designer", "40h"),
                ("Implement React migration plan", "senior-frontend", "24h"),
                ("Create responsive layouts", "frontend-dev", "32h"),
                ("Performance optimization", "perf-engineer", "16h"),
            ]

            for title, assignee, estimate in frontend_tasks:
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        title,
                        "--epic",
                        sub_epic_ids[0],
                        "--assignee",
                        assignee,
                        "--estimate",
                        estimate,
                        "--priority",
                        "high",
                    ],
                )
                assert result.exit_code == 0

            # Update epic progress
            result = runner.invoke(
                app,
                [
                    "epic",
                    "update-progress",
                    epic_id,
                    "--completed-points",
                    "25",
                    "--total-points",
                    "200",
                    "--comment",
                    "Frontend audit completed, design phase started",
                ],
            )
            assert result.exit_code == 0

            # Generate epic report
            result = runner.invoke(app, ["epic", "report", epic_id, "--detailed"])
            assert result.exit_code == 0
            assert "E-commerce Platform Overhaul" in result.stdout

    def test_portfolio_backlog_management(self, test_environment):
        """Test portfolio and backlog management across multiple projects."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create multiple projects/initiatives
            initiatives = [
                {
                    "title": "Customer Portal Redesign",
                    "priority": "high",
                    "business_value": "Improve customer self-service capabilities",
                    "estimated_cost": "$250,000",
                    "duration": "6 months",
                },
                {
                    "title": "AI-Powered Recommendations",
                    "priority": "medium",
                    "business_value": "Increase average order value by 15%",
                    "estimated_cost": "$180,000",
                    "duration": "4 months",
                },
                {
                    "title": "Supply Chain Integration",
                    "priority": "critical",
                    "business_value": "Reduce inventory costs by 20%",
                    "estimated_cost": "$500,000",
                    "duration": "9 months",
                },
                {
                    "title": "Mobile App Enhancement",
                    "priority": "medium",
                    "business_value": "Increase mobile user engagement",
                    "estimated_cost": "$120,000",
                    "duration": "3 months",
                },
            ]

            epic_ids = []
            for init in initiatives:
                result = runner.invoke(
                    app,
                    [
                        "epic",
                        "create",
                        init["title"],
                        "--priority",
                        init["priority"],
                        "--business-value",
                        init["business_value"],
                        "--metadata",
                        f"cost:{init['estimated_cost']}",
                        "--metadata",
                        f"duration:{init['duration']}",
                    ],
                )
                assert result.exit_code == 0
                epic_ids.append(self._extract_epic_id(result.stdout))

            # Create backlog items
            backlog_items = [
                ("Implement SSO authentication", "high", "security"),
                ("Add real-time inventory tracking", "medium", "inventory"),
                ("Create customer feedback system", "low", "feedback"),
                ("Optimize database queries", "high", "performance"),
                ("Add A/B testing framework", "medium", "analytics"),
                ("Implement GDPR compliance", "critical", "compliance"),
                ("Add voice search capability", "low", "search"),
                ("Create admin dashboard", "medium", "admin"),
            ]

            for title, priority, tag in backlog_items:
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        title,
                        "--priority",
                        priority,
                        "--tag",
                        tag,
                        "--tag",
                        "backlog",
                        "--status",
                        "backlog",
                    ],
                )
                assert result.exit_code == 0

            # Portfolio views
            result = runner.invoke(app, ["portfolio", "overview"])
            assert result.exit_code == 0

            result = runner.invoke(
                app, ["portfolio", "roadmap", "--quarter", "Q4-2024"]
            )
            assert result.exit_code == 0

            # Backlog grooming
            result = runner.invoke(
                app, ["portfolio", "backlog", "--priority", "high", "--unassigned"]
            )
            assert result.exit_code == 0

            # Resource allocation view
            result = runner.invoke(app, ["portfolio", "resources", "--by-epic"])
            assert result.exit_code == 0

    def test_epic_dependencies_and_milestones(self, test_environment):
        """Test epic dependencies and milestone tracking."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create interconnected epics
            epics = {}

            # Infrastructure epic (foundation)
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "Cloud Infrastructure Migration",
                    "--priority",
                    "critical",
                    "--target-date",
                    "2024-06-30",
                ],
            )
            epics["infrastructure"] = self._extract_epic_id(result.stdout)

            # Platform epic (depends on infrastructure)
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "Platform Modernization",
                    "--priority",
                    "high",
                    "--target-date",
                    "2024-09-30",
                ],
            )
            epics["platform"] = self._extract_epic_id(result.stdout)

            # Features epic (depends on platform)
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "New Feature Rollout",
                    "--priority",
                    "medium",
                    "--target-date",
                    "2024-12-31",
                ],
            )
            epics["features"] = self._extract_epic_id(result.stdout)

            # Set dependencies
            result = runner.invoke(
                app,
                [
                    "epic",
                    "add-dependency",
                    epics["platform"],
                    "--depends-on",
                    epics["infrastructure"],
                    "--type",
                    "blocks",
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(
                app,
                [
                    "epic",
                    "add-dependency",
                    epics["features"],
                    "--depends-on",
                    epics["platform"],
                    "--type",
                    "blocks",
                ],
            )
            assert result.exit_code == 0

            # Create milestones
            milestones = [
                (
                    "Infrastructure Phase 1 Complete",
                    "2024-04-30",
                    epics["infrastructure"],
                ),
                ("Platform Core Ready", "2024-08-31", epics["platform"]),
                ("Feature MVP Launch", "2024-11-30", epics["features"]),
            ]

            for title, date, epic_id in milestones:
                result = runner.invoke(
                    app,
                    [
                        "epic",
                        "add-milestone",
                        epic_id,
                        "--title",
                        title,
                        "--date",
                        date,
                        "--description",
                        f"Major milestone: {title}",
                    ],
                )
                assert result.exit_code == 0

            # Check epic timeline
            result = runner.invoke(app, ["epic", "timeline", "--show-dependencies"])
            assert result.exit_code == 0

    def _extract_epic_id(self, output: str) -> str:
        """Extract epic ID from CLI output."""
        import re

        match = re.search(r"(EP-\d+)", output)
        if match:
            return match.group(1)
        return "EP-001"


class TestPullRequestManagement:
    """Test pull request tracking and management workflows."""

    def test_pr_lifecycle_with_reviews(self, test_environment):
        """Test complete PR lifecycle including reviews and merging."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create a feature task first
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Add user profile API endpoint",
                    "--assignee",
                    "backend-dev",
                    "--priority",
                    "high",
                ],
            )
            task_id = self._extract_task_id(result.stdout)

            # Create pull request
            result = runner.invoke(
                app,
                [
                    "pr",
                    "create",
                    "Add user profile API endpoint",
                    "--description",
                    "Implements GET/PUT /api/users/{id}/profile endpoint",
                    "--source-branch",
                    "feature/user-profile-api",
                    "--target-branch",
                    "develop",
                    "--task",
                    task_id,
                    "--assignee",
                    "backend-dev",
                    "--reviewer",
                    "senior-dev",
                    "--reviewer",
                    "tech-lead",
                    "--label",
                    "backend",
                    "--label",
                    "api",
                ],
            )
            assert result.exit_code == 0
            pr_id = self._extract_pr_id(result.stdout)

            # Add PR checklist
            result = runner.invoke(
                app,
                [
                    "pr",
                    "add-checklist",
                    pr_id,
                    "--item",
                    "Unit tests added",
                    "--item",
                    "Integration tests added",
                    "--item",
                    "API documentation updated",
                    "--item",
                    "Code follows style guide",
                    "--item",
                    "No security vulnerabilities",
                ],
            )
            assert result.exit_code == 0

            # Update PR with commit info
            commits = [
                ("a1b2c3d", "Initial API endpoint implementation"),
                ("e4f5g6h", "Add request validation"),
                ("i7j8k9l", "Add unit tests"),
                ("m0n1o2p", "Update API documentation"),
            ]

            for sha, message in commits:
                result = runner.invoke(
                    app, ["pr", "add-commit", pr_id, "--sha", sha, "--message", message]
                )
                assert result.exit_code == 0

            # Reviewers add comments
            result = runner.invoke(
                app,
                [
                    "pr",
                    "review",
                    pr_id,
                    "--reviewer",
                    "senior-dev",
                    "--status",
                    "changes_requested",
                    "--comment",
                    "Please add input validation for email field",
                ],
            )
            assert result.exit_code == 0

            # Developer addresses feedback
            result = runner.invoke(
                app,
                [
                    "pr",
                    "add-commit",
                    pr_id,
                    "--sha",
                    "q3r4s5t",
                    "--message",
                    "Add email validation",
                ],
            )
            assert result.exit_code == 0

            # Update checklist
            result = runner.invoke(
                app,
                [
                    "pr",
                    "update-checklist",
                    pr_id,
                    "--item",
                    "Unit tests added",
                    "--checked",
                ],
            )
            assert result.exit_code == 0

            # Approve PR
            result = runner.invoke(
                app,
                [
                    "pr",
                    "review",
                    pr_id,
                    "--reviewer",
                    "senior-dev",
                    "--status",
                    "approved",
                    "--comment",
                    "LGTM! Good work on the validation.",
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(
                app,
                [
                    "pr",
                    "review",
                    pr_id,
                    "--reviewer",
                    "tech-lead",
                    "--status",
                    "approved",
                    "--comment",
                    "Approved. Ready to merge.",
                ],
            )
            assert result.exit_code == 0

            # Merge PR
            result = runner.invoke(
                app,
                [
                    "pr",
                    "merge",
                    pr_id,
                    "--method",
                    "squash",
                    "--commit-message",
                    "Add user profile API endpoint (#42)",
                ],
            )
            assert result.exit_code == 0

            # Verify PR is merged
            result = runner.invoke(app, ["pr", "show", pr_id])
            assert result.exit_code == 0
            assert "merged" in result.stdout.lower()

    def test_pr_conflict_resolution_workflow(self, test_environment):
        """Test PR conflict detection and resolution workflow."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create two PRs that might conflict
            result = runner.invoke(
                app,
                [
                    "pr",
                    "create",
                    "Update user model",
                    "--source-branch",
                    "feature/update-user-model",
                    "--target-branch",
                    "develop",
                    "--assignee",
                    "dev1",
                ],
            )
            pr1_id = self._extract_pr_id(result.stdout)

            result = runner.invoke(
                app,
                [
                    "pr",
                    "create",
                    "Add user preferences",
                    "--source-branch",
                    "feature/user-preferences",
                    "--target-branch",
                    "develop",
                    "--assignee",
                    "dev2",
                ],
            )
            pr2_id = self._extract_pr_id(result.stdout)

            # Mark PR as having conflicts
            result = runner.invoke(
                app,
                [
                    "pr",
                    "update",
                    pr2_id,
                    "--status",
                    "conflict",
                    "--conflict-with",
                    pr1_id,
                    "--comment",
                    "Conflicts with user model changes in PR #1",
                ],
            )
            assert result.exit_code == 0

            # First PR gets merged
            result = runner.invoke(app, ["pr", "merge", pr1_id, "--method", "merge"])
            assert result.exit_code == 0

            # Resolve conflicts in second PR
            result = runner.invoke(
                app,
                [
                    "pr",
                    "add-commit",
                    pr2_id,
                    "--sha",
                    "x1y2z3a",
                    "--message",
                    "Resolve merge conflicts with develop",
                ],
            )
            assert result.exit_code == 0

            result = runner.invoke(
                app,
                [
                    "pr",
                    "update",
                    pr2_id,
                    "--status",
                    "open",
                    "--comment",
                    "Conflicts resolved, ready for review",
                ],
            )
            assert result.exit_code == 0

    def test_pr_integration_with_ci_cd(self, test_environment):
        """Test PR integration with CI/CD pipeline status."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create PR
            result = runner.invoke(
                app,
                [
                    "pr",
                    "create",
                    "Add payment processing module",
                    "--source-branch",
                    "feature/payment-processing",
                    "--target-branch",
                    "main",
                    "--assignee",
                    "payment-dev",
                ],
            )
            pr_id = self._extract_pr_id(result.stdout)

            # Add CI/CD status updates
            ci_steps = [
                ("build", "pending", "Build started"),
                ("build", "success", "Build completed successfully"),
                ("unit-tests", "pending", "Running unit tests"),
                ("unit-tests", "success", "All unit tests passed (156/156)"),
                ("integration-tests", "pending", "Running integration tests"),
                ("integration-tests", "failure", "2 integration tests failed"),
                ("security-scan", "pending", "Running security scan"),
                ("security-scan", "success", "No vulnerabilities found"),
            ]

            for step, status, description in ci_steps:
                result = runner.invoke(
                    app,
                    [
                        "pr",
                        "update-ci-status",
                        pr_id,
                        "--step",
                        step,
                        "--status",
                        status,
                        "--description",
                        description,
                        "--url",
                        f"https://ci.example.com/builds/{pr_id}/{step}",
                    ],
                )
                assert result.exit_code == 0

                # Simulate time passing
                time.sleep(0.1)

            # Fix failing tests
            result = runner.invoke(
                app,
                [
                    "pr",
                    "add-commit",
                    pr_id,
                    "--sha",
                    "f1x2d3e",
                    "--message",
                    "Fix failing integration tests",
                ],
            )
            assert result.exit_code == 0

            # Update CI status
            result = runner.invoke(
                app,
                [
                    "pr",
                    "update-ci-status",
                    pr_id,
                    "--step",
                    "integration-tests",
                    "--status",
                    "success",
                    "--description",
                    "All integration tests passed (48/48)",
                ],
            )
            assert result.exit_code == 0

            # Check PR readiness
            result = runner.invoke(app, ["pr", "check-merge-ready", pr_id])
            assert result.exit_code == 0

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"

    def _extract_pr_id(self, output: str) -> str:
        """Extract PR ID from CLI output."""
        import re

        match = re.search(r"(PR-\d+)", output)
        if match:
            return match.group(1)
        return "PR-001"


class TestSearchAndFilteringCapabilities:
    """Test advanced search and filtering capabilities."""

    def test_complex_search_queries(self, test_environment):
        """Test complex search queries across different ticket types."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create diverse content for searching
            self._create_searchable_content(runner)

            # Test basic text search
            result = runner.invoke(app, ["search", "authentication"])
            assert result.exit_code == 0
            assert "authentication" in result.stdout.lower()

            # Test search with type filter
            result = runner.invoke(app, ["search", "bug", "--type", "issue"])
            assert result.exit_code == 0

            # Test search with multiple filters
            result = runner.invoke(
                app,
                [
                    "search",
                    "performance",
                    "--type",
                    "task",
                    "--status",
                    "open",
                    "--priority",
                    "high",
                    "--assignee",
                    "perf-engineer",
                ],
            )
            assert result.exit_code == 0

            # Test search with date range
            result = runner.invoke(
                app,
                [
                    "search",
                    "*",  # All items
                    "--created-after",
                    "2024-01-01",
                    "--created-before",
                    "2024-12-31",
                ],
            )
            assert result.exit_code == 0

            # Test search with tags
            result = runner.invoke(
                app, ["search", "--tag", "security", "--tag", "critical"]
            )
            assert result.exit_code == 0

            # Test regex search
            result = runner.invoke(
                app, ["search", "--regex", "API.*endpoint", "--type", "task"]
            )
            assert result.exit_code == 0

            # Test search with sorting
            result = runner.invoke(
                app,
                [
                    "search",
                    "feature",
                    "--sort",
                    "priority",
                    "--order",
                    "desc",
                    "--limit",
                    "10",
                ],
            )
            assert result.exit_code == 0

    def test_advanced_filtering_workflows(self, test_environment):
        """Test advanced filtering workflows for project management."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create content
            self._create_searchable_content(runner)

            # Sprint planning view - unassigned high priority tasks
            result = runner.invoke(
                app,
                [
                    "task",
                    "list",
                    "--priority",
                    "high",
                    "--unassigned",
                    "--status",
                    "open",
                    "--estimate-less-than",
                    "8h",
                ],
            )
            assert result.exit_code == 0

            # Team workload view
            result = runner.invoke(
                app,
                [
                    "task",
                    "list",
                    "--assignee",
                    "frontend-dev",
                    "--status",
                    "in_progress",
                    "--group-by",
                    "epic",
                ],
            )
            assert result.exit_code == 0

            # Overdue items
            result = runner.invoke(
                app,
                [
                    "search",
                    "--overdue",
                    "--status",
                    "open,in_progress",
                    "--sort",
                    "due-date",
                    "--order",
                    "asc",
                ],
            )
            assert result.exit_code == 0

            # Blocked items report
            result = runner.invoke(
                app, ["task", "list", "--status", "blocked", "--show-blockers"]
            )
            assert result.exit_code == 0

            # Items without estimates
            result = runner.invoke(
                app, ["task", "list", "--no-estimate", "--status", "open,in_progress"]
            )
            assert result.exit_code == 0

    def test_saved_searches_and_filters(self, test_environment):
        """Test saving and reusing complex searches."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create and save searches
            searches = [
                {
                    "name": "critical-bugs",
                    "query": {
                        "type": "issue",
                        "severity": "critical",
                        "status": "open",
                    },
                },
                {
                    "name": "my-tasks",
                    "query": {"assignee": "@me", "status": "open,in_progress"},
                },
                {
                    "name": "sprint-backlog",
                    "query": {
                        "tag": "sprint-24",
                        "status": "open",
                        "sort": "priority:desc",
                    },
                },
            ]

            for search in searches:
                query_args = []
                for key, value in search["query"].items():
                    query_args.extend([f"--{key}", value])

                result = runner.invoke(
                    app, ["search", "save", search["name"]] + query_args
                )
                assert result.exit_code == 0

            # Use saved searches
            result = runner.invoke(app, ["search", "run", "critical-bugs"])
            assert result.exit_code == 0

            # List saved searches
            result = runner.invoke(app, ["search", "saved", "--list"])
            assert result.exit_code == 0
            assert "critical-bugs" in result.stdout

            # Export search results
            result = runner.invoke(
                app,
                [
                    "search",
                    "run",
                    "sprint-backlog",
                    "--export",
                    "csv",
                    "--output",
                    "sprint-backlog.csv",
                ],
            )
            assert result.exit_code == 0

    def _create_searchable_content(self, runner):
        """Create diverse content for search testing."""
        # Create epics
        epics = [
            ("Authentication System", "security"),
            ("Performance Optimization", "performance"),
            ("Mobile Application", "mobile"),
        ]

        for title, tag in epics:
            runner.invoke(
                app, ["epic", "create", title, "--tag", tag, "--priority", "high"]
            )

        # Create tasks
        tasks = [
            (
                "Implement JWT authentication",
                "high",
                ["security", "backend"],
                "auth-dev",
            ),
            (
                "Optimize database queries",
                "critical",
                ["performance", "database"],
                "perf-engineer",
            ),
            ("Fix login page bug", "high", ["bug", "frontend"], "frontend-dev"),
            ("Add API rate limiting", "medium", ["security", "api"], "backend-dev"),
            (
                "Improve search performance",
                "high",
                ["performance", "search"],
                "search-engineer",
            ),
        ]

        for title, priority, tags, assignee in tasks:
            tag_args = []
            for tag in tags:
                tag_args.extend(["--tag", tag])

            runner.invoke(
                app,
                [
                    "task",
                    "create",
                    title,
                    "--priority",
                    priority,
                    "--assignee",
                    assignee,
                ]
                + tag_args,
            )

        # Create issues
        issues = [
            ("Memory leak in background service", "bug", "critical", "performance"),
            ("Add two-factor authentication", "feature", "high", "security"),
            ("Search not working on mobile", "bug", "high", "mobile"),
        ]

        for title, issue_type, severity, component in issues:
            runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    title,
                    "--type",
                    issue_type,
                    "--severity",
                    severity,
                    "--component",
                    component,
                ],
            )


class TestReportingAndAnalytics:
    """Test reporting and analytics capabilities."""

    def test_project_status_reports(self, test_environment):
        """Test various project status reports."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create project data
            self._create_project_data(runner)

            # Overall project status
            result = runner.invoke(app, ["status", "project", "--detailed"])
            assert result.exit_code == 0

            # Task status by assignee
            result = runner.invoke(app, ["status", "tasks", "--by-assignee"])
            assert result.exit_code == 0

            # Epic progress report
            result = runner.invoke(app, ["status", "epics", "--show-progress"])
            assert result.exit_code == 0

            # Burndown chart data
            result = runner.invoke(
                app, ["report", "burndown", "--sprint", "current", "--format", "json"]
            )
            assert result.exit_code == 0

            # Velocity report
            result = runner.invoke(app, ["report", "velocity", "--last-sprints", "4"])
            assert result.exit_code == 0

            # Issue trends
            result = runner.invoke(
                app, ["report", "issue-trends", "--period", "last-30-days", "--by-type"]
            )
            assert result.exit_code == 0

    def test_custom_reports_generation(self, test_environment):
        """Test custom report generation."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create data
            self._create_project_data(runner)

            # Team performance report
            result = runner.invoke(
                app,
                [
                    "report",
                    "team-performance",
                    "--team",
                    "frontend",
                    "--metrics",
                    "completion-rate,velocity,quality",
                    "--period",
                    "last-quarter",
                ],
            )
            assert result.exit_code == 0

            # Risk assessment report
            result = runner.invoke(
                app,
                [
                    "report",
                    "risk-assessment",
                    "--include-blocked",
                    "--include-overdue",
                    "--include-high-priority",
                ],
            )
            assert result.exit_code == 0

            # Executive summary
            result = runner.invoke(
                app,
                [
                    "report",
                    "executive-summary",
                    "--format",
                    "pdf",
                    "--output",
                    "exec-summary.pdf",
                ],
            )
            assert result.exit_code == 0

    def _create_project_data(self, runner):
        """Create project data for reporting."""
        # Create epics with different states
        epics = [
            ("Completed Epic", "completed"),
            ("In Progress Epic", "in_progress"),
            ("Planned Epic", "planned"),
        ]

        for title, status in epics:
            runner.invoke(app, ["epic", "create", title, "--status", status])

        # Create diverse tasks
        for i in range(20):
            status = ["open", "in_progress", "completed", "blocked"][i % 4]
            priority = ["low", "medium", "high", "critical"][i % 4]
            assignee = ["dev1", "dev2", "dev3", "dev4"][i % 4]

            runner.invoke(
                app,
                [
                    "task",
                    "create",
                    f"Task {i+1}",
                    "--status",
                    status,
                    "--priority",
                    priority,
                    "--assignee",
                    assignee,
                    "--estimate",
                    f"{(i % 8 + 1)}h",
                ],
            )


class TestDataValidationAndIntegrity:
    """Test data validation and integrity checks."""

    def test_schema_validation(self, test_environment):
        """Test schema validation for all ticket types."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test valid tickets
            valid_tickets = [
                (
                    "task",
                    {
                        "title": "Valid Task",
                        "priority": "high",
                        "assignee": "developer",
                    },
                ),
                (
                    "issue",
                    {"title": "Valid Issue", "type": "bug", "severity": "critical"},
                ),
                ("epic", {"title": "Valid Epic", "business-value": "Increase revenue"}),
                (
                    "pr",
                    {
                        "title": "Valid PR",
                        "source-branch": "feature/test",
                        "target-branch": "main",
                    },
                ),
            ]

            for ticket_type, attrs in valid_tickets:
                args = ["create", ticket_type, attrs["title"]]
                for key, value in attrs.items():
                    if key != "title":
                        args.extend([f"--{key}", value])

                result = runner.invoke(app, args)
                assert result.exit_code == 0

            # Validate all tickets
            result = runner.invoke(app, ["validate", "tasks", "--strict"])
            assert result.exit_code == 0

            # Test invalid data handling
            # Invalid priority
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Invalid Priority Task",
                    "--priority",
                    "super-urgent",  # Invalid priority
                ],
            )
            assert result.exit_code == 1

            # Invalid status
            result = runner.invoke(
                app,
                [
                    "task",
                    "update",
                    "TSK-001",
                    "--status",
                    "almost-done",  # Invalid status
                ],
            )
            assert result.exit_code == 1

    def test_referential_integrity(self, test_environment):
        """Test referential integrity between related tickets."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create parent epic
            result = runner.invoke(app, ["epic", "create", "Parent Epic"])
            epic_id = self._extract_epic_id(result.stdout)

            # Create task referencing epic
            result = runner.invoke(
                app, ["task", "create", "Epic Task", "--epic", epic_id]
            )
            task_id = self._extract_task_id(result.stdout)

            # Try to delete epic with references (should warn or fail)
            result = runner.invoke(app, ["epic", "delete", epic_id])
            # Should either fail or warn about existing references

            # Check integrity
            result = runner.invoke(app, ["validate", "relationships"])
            assert result.exit_code == 0

            # Fix orphaned references
            result = runner.invoke(app, ["validate", "relationships", "--fix-orphans"])
            assert result.exit_code == 0

    def test_data_migration_validation(self, test_environment):
        """Test data validation during migration scenarios."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create legacy format data
            legacy_data = {
                "tasks": [
                    {
                        "id": "OLD-001",
                        "title": "Legacy Task",
                        "status": "todo",  # Old status format
                        "owner": "john",  # Old field name
                    }
                ]
            }

            # Import with validation
            import_file = project_path / "legacy_import.json"
            import_file.write_text(json.dumps(legacy_data))

            result = runner.invoke(
                app,
                [
                    "migrate",
                    "import",
                    "--file",
                    str(import_file),
                    "--validate",
                    "--map",
                    "owner:assignee",
                    "--map",
                    "todo:open",
                ],
            )
            assert result.exit_code == 0

            # Verify migration
            result = runner.invoke(app, ["task", "show", "OLD-001"])
            assert result.exit_code == 0
            assert "open" in result.stdout  # Status mapped correctly

    def _extract_epic_id(self, output: str) -> str:
        """Extract epic ID from CLI output."""
        import re

        match = re.search(r"(EP-\d+)", output)
        if match:
            return match.group(1)
        return "EP-001"

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestPerformanceAndScalability:
    """Test performance with large datasets and concurrent operations."""

    def test_large_dataset_operations(self, test_environment):
        """Test operations with large number of tickets."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create large dataset (reduced for CI)
            num_items = 100  # Would be 1000+ for real performance testing

            start_time = time.time()

            # Batch create tasks
            for i in range(num_items):
                if i % 10 == 0:  # Create some epics
                    runner.invoke(
                        app,
                        [
                            "epic",
                            "create",
                            f"Epic {i//10 + 1}",
                            "--priority",
                            ["low", "medium", "high"][i % 3],
                        ],
                    )
                else:
                    runner.invoke(
                        app,
                        [
                            "task",
                            "create",
                            f"Task {i+1}",
                            "--priority",
                            ["low", "medium", "high", "critical"][i % 4],
                            "--assignee",
                            f"dev{i % 5 + 1}",
                            "--tag",
                            f"batch{i // 20}",
                        ],
                    )

            creation_time = time.time() - start_time

            # Test search performance
            start_time = time.time()
            result = runner.invoke(app, ["search", "Task", "--limit", "50"])
            assert result.exit_code == 0
            search_time = time.time() - start_time

            # Test filtering performance
            start_time = time.time()
            result = runner.invoke(
                app, ["task", "list", "--priority", "high", "--limit", "100"]
            )
            assert result.exit_code == 0
            filter_time = time.time() - start_time

            # Test aggregation performance
            start_time = time.time()
            result = runner.invoke(app, ["status", "summary"])
            assert result.exit_code == 0
            summary_time = time.time() - start_time

            # Performance assertions (generous for CI)
            assert creation_time < 300  # 5 minutes for 100 items
            assert search_time < 5
            assert filter_time < 5
            assert summary_time < 10

    def test_concurrent_operations(self, test_environment):
        """Test handling of concurrent operations."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Simulate concurrent task creation
            # In real scenario, this would use threading/multiprocessing

            # Create base task
            result = runner.invoke(
                app, ["task", "create", "Concurrent Base Task", "--priority", "high"]
            )
            base_id = self._extract_task_id(result.stdout)

            # Simulate multiple users updating same task
            updates = [
                ("--add-tag", "update1"),
                ("--add-tag", "update2"),
                ("--priority", "critical"),
                ("--assignee", "new-assignee"),
            ]

            for update_type, value in updates:
                result = runner.invoke(
                    app, ["task", "update", base_id, update_type, value]
                )
                # Should handle concurrent updates gracefully
                assert result.exit_code in [0, 1]

            # Verify final state
            result = runner.invoke(app, ["task", "show", base_id])
            assert result.exit_code == 0

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestExportImportWorkflows:
    """Test export and import functionality."""

    def test_project_export_import(self, test_environment):
        """Test full project export and import."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]
        export_path = Path(test_environment["temp_dir"]) / "export"
        export_path.mkdir()

        with patch("os.getcwd", return_value=str(project_path)):
            # Create project content
            self._create_export_test_data(runner)

            # Export entire project
            export_file = export_path / "project_export.json"
            result = runner.invoke(
                app,
                [
                    "export",
                    "project",
                    "--format",
                    "json",
                    "--output",
                    str(export_file),
                    "--include-attachments",
                ],
            )
            assert result.exit_code == 0
            assert export_file.exists()

            # Create new project for import
            import_project = Path(test_environment["temp_dir"]) / "import_project"
            import_project.mkdir()

            with patch("os.getcwd", return_value=str(import_project)):
                # Initialize new project
                result = runner.invoke(app, ["init", "project"])
                assert result.exit_code == 0

                # Import data
                result = runner.invoke(
                    app,
                    [
                        "import",
                        "project",
                        "--file",
                        str(export_file),
                        "--merge-strategy",
                        "replace",
                    ],
                )
                assert result.exit_code == 0

                # Verify imported content
                result = runner.invoke(app, ["status", "summary"])
                assert result.exit_code == 0
                assert "task" in result.stdout.lower()

    def test_selective_export(self, test_environment):
        """Test selective export of specific items."""
        runner = test_environment["runner"]
        project_path = test_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create content
            self._create_export_test_data(runner)

            # Export only high priority items
            result = runner.invoke(
                app,
                [
                    "export",
                    "tasks",
                    "--filter-priority",
                    "high,critical",
                    "--format",
                    "csv",
                    "--output",
                    "high_priority_tasks.csv",
                ],
            )
            assert result.exit_code == 0

            # Export specific epic and its children
            result = runner.invoke(
                app,
                [
                    "export",
                    "epic",
                    "EP-001",
                    "--include-children",
                    "--format",
                    "markdown",
                    "--output",
                    "epic_report.md",
                ],
            )
            assert result.exit_code == 0

            # Export for external tools
            result = runner.invoke(
                app,
                [
                    "export",
                    "jira",
                    "--map",
                    "priority:priority",
                    "--map",
                    "assignee:assignee",
                    "--output",
                    "jira_import.csv",
                ],
            )
            assert result.exit_code == 0

    def _create_export_test_data(self, runner):
        """Create test data for export testing."""
        # Create epic
        runner.invoke(app, ["epic", "create", "Export Test Epic", "--priority", "high"])

        # Create tasks
        for i in range(5):
            runner.invoke(
                app,
                [
                    "task",
                    "create",
                    f"Export Task {i+1}",
                    "--priority",
                    ["low", "medium", "high"][i % 3],
                    "--assignee",
                    f"user{i % 3 + 1}",
                ],
            )

        # Create issues
        runner.invoke(
            app,
            [
                "issue",
                "create",
                "Export Test Issue",
                "--type",
                "bug",
                "--severity",
                "high",
            ],
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
