"""End-to-end integration tests for real-world ticket management workflows."""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app


@pytest.fixture
def integration_environment():
    """Create integration test environment with Git support."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir) / "integration_project"
    project_path.mkdir()

    runner = CliRunner()

    # Initialize Git repo
    with patch("os.getcwd", return_value=str(project_path)):
        # Initialize project
        result = runner.invoke(
            app, ["init", "project", "--name", "Integration Test Project"]
        )
        assert result.exit_code == 0

        # Mock Git initialization
        with patch("ai_trackdown_pytools.utils.git.GitUtils.init_repo") as mock_init:
            mock_init.return_value = True
            result = runner.invoke(app, ["init", "git"])

    yield {
        "runner": runner,
        "project_path": project_path,
        "temp_dir": temp_dir,
        "git_initialized": True,
    }

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestGitIntegrationWorkflows:
    """Test Git integration with ticket management."""

    def test_feature_branch_workflow(self, integration_environment):
        """Test complete feature branch workflow with tickets."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create feature epic
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "User Authentication Feature",
                    "--priority",
                    "high",
                    "--target-date",
                    "2024-12-31",
                ],
            )
            epic_id = self._extract_id(result.stdout, "EP")

            # Create feature task
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Implement OAuth2 authentication",
                    "--epic",
                    epic_id,
                    "--assignee",
                    "backend-dev",
                    "--priority",
                    "high",
                ],
            )
            task_id = self._extract_id(result.stdout, "TSK")

            # Create feature branch linked to task
            with patch(
                "ai_trackdown_pytools.utils.git.GitUtils.create_branch"
            ) as mock_branch:
                mock_branch.return_value = True
                result = runner.invoke(
                    app,
                    [
                        "git",
                        "branch",
                        "create",
                        f"feature/{task_id}-oauth2-auth",
                        "--task",
                        task_id,
                    ],
                )
                assert result.exit_code == 0

            # Start work on task
            result = runner.invoke(app, ["task", "start", task_id])
            assert result.exit_code == 0

            # Simulate commits
            commits = [
                ("Add OAuth2 dependencies", "feat: add oauth2 client libraries"),
                ("Implement token validation", "feat: add JWT token validation"),
                ("Add user session management", "feat: implement session handling"),
                ("Add tests", "test: add OAuth2 authentication tests"),
                ("Fix security issue", "fix: patch XSS vulnerability in callback"),
            ]

            with patch("ai_trackdown_pytools.utils.git.GitUtils.commit") as mock_commit:
                for subject, message in commits:
                    mock_commit.return_value = f"commit-{subject[:8]}"
                    result = runner.invoke(
                        app, ["git", "commit", "--message", message, "--task", task_id]
                    )
                    assert result.exit_code == 0

            # Create PR
            result = runner.invoke(
                app,
                [
                    "pr",
                    "create",
                    f"[{task_id}] Implement OAuth2 authentication",
                    "--source-branch",
                    f"feature/{task_id}-oauth2-auth",
                    "--target-branch",
                    "develop",
                    "--task",
                    task_id,
                    "--reviewer",
                    "tech-lead",
                    "--reviewer",
                    "security-expert",
                ],
            )
            pr_id = self._extract_id(result.stdout, "PR")

            # Complete task when PR is merged
            result = runner.invoke(
                app, ["pr", "merge", pr_id, "--complete-task", task_id]
            )
            assert result.exit_code == 0

            # Verify task is completed
            result = runner.invoke(app, ["task", "show", task_id])
            assert result.exit_code == 0
            assert "completed" in result.stdout.lower()

    def test_hotfix_workflow(self, integration_environment):
        """Test hotfix workflow for critical bugs."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Report critical bug
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "Production API returning 500 errors",
                    "--type",
                    "bug",
                    "--severity",
                    "critical",
                    "--component",
                    "api",
                    "--affects-version",
                    "2.5.0",
                    "--label",
                    "production",
                    "--label",
                    "urgent",
                ],
            )
            bug_id = self._extract_id(result.stdout, "ISS")

            # Create hotfix branch
            with patch(
                "ai_trackdown_pytools.utils.git.GitUtils.create_branch"
            ) as mock_branch:
                mock_branch.return_value = True
                result = runner.invoke(
                    app,
                    [
                        "git",
                        "branch",
                        "create",
                        f"hotfix/{bug_id}-api-500-error",
                        "--from",
                        "main",
                        "--issue",
                        bug_id,
                    ],
                )
                assert result.exit_code == 0

            # Create fix task
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Fix API 500 error in production",
                    "--issue",
                    bug_id,
                    "--priority",
                    "critical",
                    "--assignee",
                    "senior-dev",
                    "--tag",
                    "hotfix",
                ],
            )
            fix_task_id = self._extract_id(result.stdout, "TSK")

            # Fast-track the fix
            result = runner.invoke(app, ["task", "start", fix_task_id])
            assert result.exit_code == 0

            # Commit fix
            with patch("ai_trackdown_pytools.utils.git.GitUtils.commit") as mock_commit:
                mock_commit.return_value = "abc123"
                result = runner.invoke(
                    app,
                    [
                        "git",
                        "commit",
                        "--message",
                        f"fix: resolve API 500 error\n\nFixes #{bug_id}",
                        "--task",
                        fix_task_id,
                    ],
                )

            # Create PR for hotfix
            result = runner.invoke(
                app,
                [
                    "pr",
                    "create",
                    "[HOTFIX] Fix API 500 error",
                    "--source-branch",
                    f"hotfix/{bug_id}-api-500-error",
                    "--target-branch",
                    "main",
                    "--issue",
                    bug_id,
                    "--label",
                    "hotfix",
                    "--label",
                    "critical",
                    "--fast-track",
                ],
            )
            pr_id = self._extract_id(result.stdout, "PR")

            # Emergency approval and merge
            result = runner.invoke(
                app,
                [
                    "pr",
                    "emergency-merge",
                    pr_id,
                    "--approver",
                    "tech-lead",
                    "--reason",
                    "Critical production issue",
                ],
            )
            assert result.exit_code == 0

            # Close bug as resolved
            result = runner.invoke(
                app,
                [
                    "issue",
                    "resolve",
                    bug_id,
                    "--resolution",
                    "fixed",
                    "--fixed-version",
                    "2.5.1",
                ],
            )
            assert result.exit_code == 0

    def test_release_branch_workflow(self, integration_environment):
        """Test release branch workflow with version management."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create release epic
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "Release 3.0.0",
                    "--priority",
                    "critical",
                    "--target-date",
                    "2024-12-15",
                    "--tag",
                    "release",
                ],
            )
            release_epic_id = self._extract_id(result.stdout, "EP")

            # Create release branch
            with patch(
                "ai_trackdown_pytools.utils.git.GitUtils.create_branch"
            ) as mock_branch:
                mock_branch.return_value = True
                result = runner.invoke(
                    app,
                    [
                        "git",
                        "branch",
                        "create",
                        "release/3.0.0",
                        "--from",
                        "develop",
                        "--epic",
                        release_epic_id,
                    ],
                )

            # Create release tasks
            release_tasks = [
                ("Update version numbers", "devops"),
                ("Run regression tests", "qa-lead"),
                ("Update documentation", "tech-writer"),
                ("Prepare release notes", "product-manager"),
                ("Performance testing", "perf-engineer"),
            ]

            task_ids = []
            for title, assignee in release_tasks:
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        title,
                        "--epic",
                        release_epic_id,
                        "--assignee",
                        assignee,
                        "--tag",
                        "release-3.0.0",
                    ],
                )
                task_ids.append(self._extract_id(result.stdout, "TSK"))

            # Track release progress
            for i, task_id in enumerate(task_ids):
                if i < 3:  # Complete some tasks
                    result = runner.invoke(app, ["task", "complete", task_id])
                    assert result.exit_code == 0

            # Generate release report
            result = runner.invoke(
                app,
                [
                    "report",
                    "release",
                    "--epic",
                    release_epic_id,
                    "--include-completed",
                    "--include-pending",
                ],
            )
            assert result.exit_code == 0

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestCrossPlatformSyncWorkflows:
    """Test synchronization with external platforms."""

    def test_github_sync_workflow(self, integration_environment):
        """Test GitHub issue and PR synchronization."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Configure GitHub sync
            with patch(
                "ai_trackdown_pytools.utils.git.GitUtils.get_remote_url"
            ) as mock_remote:
                mock_remote.return_value = "https://github.com/user/repo.git"
                result = runner.invoke(
                    app,
                    [
                        "sync",
                        "configure",
                        "github",
                        "--token",
                        "ghp_test_token",
                        "--repo",
                        "user/repo",
                        "--enable-issues",
                        "--enable-prs",
                    ],
                )
                assert result.exit_code == 0

            # Import GitHub issues
            mock_github_issues = [
                {
                    "number": 42,
                    "title": "Add dark mode support",
                    "body": "Users are requesting dark mode",
                    "state": "open",
                    "labels": [{"name": "enhancement"}, {"name": "ui"}],
                    "assignee": {"login": "alice"},
                    "created_at": "2024-01-15T10:00:00Z",
                    "updated_at": "2024-01-16T15:30:00Z",
                },
                {
                    "number": 43,
                    "title": "Fix memory leak",
                    "body": "App crashes after extended use",
                    "state": "open",
                    "labels": [{"name": "bug"}, {"name": "critical"}],
                    "assignee": {"login": "bob"},
                    "created_at": "2024-01-16T09:00:00Z",
                    "updated_at": "2024-01-16T16:00:00Z",
                },
            ]

            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = mock_github_issues
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                result = runner.invoke(
                    app,
                    [
                        "sync",
                        "import",
                        "github",
                        "--type",
                        "issues",
                        "--since",
                        "2024-01-01",
                    ],
                )
                assert result.exit_code == 0

            # Verify imported issues
            result = runner.invoke(app, ["issue", "list", "--source", "github"])
            assert result.exit_code == 0

            # Create local task for GitHub issue
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Implement dark mode",
                    "--github-issue",
                    "42",
                    "--assignee",
                    "frontend-dev",
                ],
            )
            task_id = self._extract_id(result.stdout, "TSK")

            # Sync task updates back to GitHub
            with patch("requests.patch") as mock_patch:
                mock_patch.return_value.status_code = 200
                result = runner.invoke(
                    app,
                    [
                        "sync",
                        "push",
                        "github",
                        "--task",
                        task_id,
                        "--update-labels",
                        "--update-assignee",
                    ],
                )
                assert result.exit_code == 0

            # Import GitHub PRs
            mock_github_prs = [
                {
                    "number": 123,
                    "title": "Add dark mode toggle",
                    "body": "Implements #42",
                    "state": "open",
                    "head": {"ref": "feature/dark-mode"},
                    "base": {"ref": "main"},
                    "user": {"login": "alice"},
                    "created_at": "2024-01-17T10:00:00Z",
                    "requested_reviewers": [{"login": "bob"}, {"login": "charlie"}],
                }
            ]

            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = mock_github_prs
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                result = runner.invoke(
                    app, ["sync", "import", "github", "--type", "prs", "--link-issues"]
                )
                assert result.exit_code == 0

    def test_jira_sync_workflow(self, integration_environment):
        """Test JIRA synchronization workflow."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Configure JIRA sync
            result = runner.invoke(
                app,
                [
                    "sync",
                    "configure",
                    "jira",
                    "--url",
                    "https://company.atlassian.net",
                    "--user",
                    "user@company.com",
                    "--token",
                    "jira_token",
                    "--project",
                    "PROJ",
                ],
            )
            assert result.exit_code == 0

            # Map fields
            result = runner.invoke(
                app,
                [
                    "sync",
                    "map-fields",
                    "jira",
                    "--map",
                    "priority:priority",
                    "--map",
                    "assignee:assignee.name",
                    "--map",
                    "status:status",
                    "--map",
                    "epic:customfield_10001",
                ],
            )
            assert result.exit_code == 0

            # Import JIRA issues
            mock_jira_issues = {
                "issues": [
                    {
                        "key": "PROJ-1234",
                        "fields": {
                            "summary": "Implement user dashboard",
                            "description": "Create a new user dashboard",
                            "issuetype": {"name": "Story"},
                            "priority": {"name": "High"},
                            "status": {"name": "In Progress"},
                            "assignee": {"name": "John Doe"},
                            "customfield_10001": "PROJ-1000",  # Epic link
                        },
                    }
                ]
            }

            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = mock_jira_issues
                mock_response.status_code = 200
                mock_post.return_value = mock_response

                result = runner.invoke(
                    app,
                    [
                        "sync",
                        "import",
                        "jira",
                        "--jql",
                        "project = PROJ AND updated >= -7d",
                    ],
                )
                assert result.exit_code == 0

            # Create bi-directional sync
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Local task for JIRA",
                    "--sync-to-jira",
                    "--jira-type",
                    "Task",
                    "--jira-priority",
                    "Medium",
                ],
            )
            local_task_id = self._extract_id(result.stdout, "TSK")

            # Push to JIRA
            with patch("requests.post") as mock_post:
                mock_response = Mock()
                mock_response.json.return_value = {"key": "PROJ-1235"}
                mock_response.status_code = 201
                mock_post.return_value = mock_response

                result = runner.invoke(
                    app, ["sync", "push", "jira", "--task", local_task_id]
                )
                assert result.exit_code == 0

    def test_gitlab_sync_workflow(self, integration_environment):
        """Test GitLab synchronization workflow."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Configure GitLab sync
            result = runner.invoke(
                app,
                [
                    "sync",
                    "configure",
                    "gitlab",
                    "--url",
                    "https://gitlab.company.com",
                    "--token",
                    "gitlab_token",
                    "--project-id",
                    "123",
                ],
            )
            assert result.exit_code == 0

            # Import GitLab issues
            mock_gitlab_issues = [
                {
                    "iid": 10,
                    "title": "Upgrade dependencies",
                    "description": "Update all npm packages",
                    "state": "opened",
                    "labels": ["maintenance", "dependencies"],
                    "assignee": {"username": "developer1"},
                    "milestone": {"title": "v2.0"},
                    "created_at": "2024-01-10T10:00:00Z",
                }
            ]

            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = mock_gitlab_issues
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                result = runner.invoke(
                    app,
                    [
                        "sync",
                        "import",
                        "gitlab",
                        "--type",
                        "issues",
                        "--milestone",
                        "v2.0",
                    ],
                )
                assert result.exit_code == 0

            # Sync merge requests
            mock_gitlab_mrs = [
                {
                    "iid": 25,
                    "title": "Update package.json",
                    "description": "Updates dependencies\n\nCloses #10",
                    "state": "opened",
                    "source_branch": "update-deps",
                    "target_branch": "main",
                    "author": {"username": "developer1"},
                    "assignee": {"username": "reviewer1"},
                }
            ]

            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = mock_gitlab_mrs
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                result = runner.invoke(
                    app,
                    [
                        "sync",
                        "import",
                        "gitlab",
                        "--type",
                        "merge-requests",
                        "--state",
                        "opened",
                    ],
                )
                assert result.exit_code == 0

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestAutomationAndWebhookWorkflows:
    """Test automation and webhook integration workflows."""

    def test_webhook_automation_workflow(self, integration_environment):
        """Test webhook-driven automation workflows."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Configure webhooks
            result = runner.invoke(
                app,
                [
                    "automation",
                    "webhook",
                    "configure",
                    "--endpoint",
                    "http://localhost:8080/webhook",
                    "--secret",
                    "webhook_secret",
                    "--events",
                    "task.created,task.updated,pr.opened,pr.merged",
                ],
            )
            assert result.exit_code == 0

            # Create automation rules
            rules = [
                {
                    "name": "auto-assign-pr-reviewer",
                    "trigger": "pr.opened",
                    "condition": "pr.labels contains 'frontend'",
                    "action": "assign_reviewer:frontend-lead",
                },
                {
                    "name": "auto-label-critical-bugs",
                    "trigger": "issue.created",
                    "condition": "issue.severity == 'critical'",
                    "action": "add_label:urgent,add_label:priority-1",
                },
                {
                    "name": "notify-slack-on-completion",
                    "trigger": "task.completed",
                    "condition": "task.priority == 'high'",
                    "action": "slack_notify:#dev-updates",
                },
            ]

            for rule in rules:
                result = runner.invoke(
                    app,
                    [
                        "automation",
                        "rule",
                        "create",
                        "--name",
                        rule["name"],
                        "--trigger",
                        rule["trigger"],
                        "--condition",
                        rule["condition"],
                        "--action",
                        rule["action"],
                    ],
                )
                assert result.exit_code == 0

            # Simulate webhook events
            webhook_payloads = [
                {
                    "event": "pr.opened",
                    "data": {
                        "id": "PR-100",
                        "title": "Update frontend components",
                        "labels": ["frontend", "react"],
                        "author": "developer1",
                    },
                },
                {
                    "event": "issue.created",
                    "data": {
                        "id": "ISS-200",
                        "title": "App crashes on startup",
                        "severity": "critical",
                        "type": "bug",
                    },
                },
                {
                    "event": "task.completed",
                    "data": {
                        "id": "TSK-300",
                        "title": "Deploy to production",
                        "priority": "high",
                        "assignee": "devops",
                    },
                },
            ]

            for payload in webhook_payloads:
                with patch("requests.post") as mock_post:
                    mock_post.return_value.status_code = 200
                    result = runner.invoke(
                        app,
                        [
                            "automation",
                            "webhook",
                            "test",
                            "--payload",
                            json.dumps(payload),
                        ],
                    )
                    assert result.exit_code == 0

            # Check automation logs
            result = runner.invoke(
                app, ["automation", "logs", "--last", "10", "--filter", "success"]
            )
            assert result.exit_code == 0

    def test_scheduled_automation_workflow(self, integration_environment):
        """Test scheduled automation tasks."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create scheduled tasks
            schedules = [
                {
                    "name": "daily-standup-report",
                    "schedule": "0 9 * * *",  # 9 AM daily
                    "action": "report:standup",
                    "params": {"assignees": "all", "format": "slack"},
                },
                {
                    "name": "weekly-sprint-summary",
                    "schedule": "0 17 * * 5",  # 5 PM Friday
                    "action": "report:sprint-summary",
                    "params": {"sprint": "current", "include_metrics": True},
                },
                {
                    "name": "stale-task-reminder",
                    "schedule": "0 10 * * 1",  # 10 AM Monday
                    "action": "reminder:stale-tasks",
                    "params": {"days_inactive": 7, "notify": "assignee"},
                },
                {
                    "name": "monthly-metrics",
                    "schedule": "0 0 1 * *",  # Midnight 1st of month
                    "action": "report:monthly-metrics",
                    "params": {"export": "csv", "email": "team@company.com"},
                },
            ]

            for schedule in schedules:
                result = runner.invoke(
                    app,
                    [
                        "automation",
                        "schedule",
                        "create",
                        "--name",
                        schedule["name"],
                        "--cron",
                        schedule["schedule"],
                        "--action",
                        schedule["action"],
                        "--params",
                        json.dumps(schedule["params"]),
                    ],
                )
                assert result.exit_code == 0

            # Test scheduled task execution
            result = runner.invoke(
                app,
                [
                    "automation",
                    "schedule",
                    "run",
                    "--name",
                    "daily-standup-report",
                    "--now",  # Force immediate execution
                ],
            )
            assert result.exit_code == 0

            # List scheduled tasks
            result = runner.invoke(app, ["automation", "schedule", "list", "--active"])
            assert result.exit_code == 0
            assert "daily-standup-report" in result.stdout

    def test_workflow_automation(self, integration_environment):
        """Test complex workflow automation."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Define workflow
            workflow_def = {
                "name": "feature-development-workflow",
                "description": "Automated workflow for feature development",
                "steps": [
                    {
                        "id": "create-epic",
                        "type": "create",
                        "entity": "epic",
                        "template": "feature-epic",
                        "output": "epic_id",
                    },
                    {
                        "id": "create-tasks",
                        "type": "batch-create",
                        "entity": "task",
                        "templates": ["design", "implement", "test", "document"],
                        "parent": "{epic_id}",
                        "output": "task_ids",
                    },
                    {
                        "id": "assign-tasks",
                        "type": "assign",
                        "tasks": "{task_ids}",
                        "strategy": "round-robin",
                        "pool": ["dev1", "dev2", "dev3"],
                    },
                    {
                        "id": "create-branch",
                        "type": "git-branch",
                        "name": "feature/{epic_id}",
                        "from": "develop",
                    },
                    {
                        "id": "notify-team",
                        "type": "notify",
                        "channel": "slack:#dev-team",
                        "message": "New feature epic {epic_id} created with {task_count} tasks",
                    },
                ],
            }

            # Create workflow
            workflow_file = project_path / "workflows" / "feature-dev.yaml"
            workflow_file.parent.mkdir(exist_ok=True)
            workflow_file.write_text(yaml.dump(workflow_def))

            result = runner.invoke(
                app, ["automation", "workflow", "create", "--file", str(workflow_file)]
            )
            assert result.exit_code == 0

            # Execute workflow
            result = runner.invoke(
                app,
                [
                    "automation",
                    "workflow",
                    "run",
                    "--name",
                    "feature-development-workflow",
                    "--params",
                    json.dumps(
                        {
                            "title": "Payment Integration",
                            "priority": "high",
                            "target_date": "2024-12-31",
                        }
                    ),
                ],
            )
            assert result.exit_code == 0

            # Check workflow status
            result = runner.invoke(
                app,
                [
                    "automation",
                    "workflow",
                    "status",
                    "--name",
                    "feature-development-workflow",
                    "--last-run",
                ],
            )
            assert result.exit_code == 0


class TestTemplateSystemIntegration:
    """Test template system integration with ticket management."""

    def test_custom_template_workflow(self, integration_environment):
        """Test custom template creation and usage."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create custom task template
            custom_template = {
                "name": "security-review",
                "description": "Template for security review tasks",
                "fields": {
                    "title": {
                        "type": "string",
                        "required": True,
                        "prompt": "Security review title",
                    },
                    "component": {
                        "type": "choice",
                        "choices": ["frontend", "backend", "api", "database"],
                        "required": True,
                    },
                    "severity": {
                        "type": "choice",
                        "choices": ["low", "medium", "high", "critical"],
                        "default": "medium",
                    },
                    "checklist": {
                        "type": "list",
                        "default": [
                            "Review authentication mechanisms",
                            "Check for SQL injection vulnerabilities",
                            "Validate input sanitization",
                            "Review access controls",
                            "Check for XSS vulnerabilities",
                        ],
                    },
                },
                "content": """---
title: {{ title }}
type: task
priority: {{ severity }}
tags: [security, review, {{ component }}]
assignee: security-team
metadata:
  component: {{ component }}
  severity: {{ severity }}
  review_type: security
---

# {{ title }}

## Security Review Checklist

{% for item in checklist %}
- [ ] {{ item }}
{% endfor %}

## Component
{{ component }}

## Severity
{{ severity }}

## Notes
_Add security review notes here_
""",
            }

            # Save template
            template_file = project_path / "templates" / "task" / "security-review.yaml"
            template_file.parent.mkdir(parents=True, exist_ok=True)
            template_file.write_text(yaml.dump(custom_template))

            # Use template to create task
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "--template",
                    "security-review",
                    "--title",
                    "API Endpoint Security Review",
                    "--component",
                    "api",
                    "--severity",
                    "high",
                ],
            )
            assert result.exit_code == 0
            task_id = self._extract_id(result.stdout, "TSK")

            # Verify task was created with template
            result = runner.invoke(app, ["task", "show", task_id])
            assert result.exit_code == 0
            assert "security" in result.stdout
            assert "Review authentication mechanisms" in result.stdout

    def test_template_inheritance_workflow(self, integration_environment):
        """Test template inheritance and composition."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create base template
            base_template = {
                "name": "base-task",
                "fields": {
                    "priority": {
                        "type": "choice",
                        "choices": ["low", "medium", "high", "critical"],
                        "default": "medium",
                    },
                    "estimate": {
                        "type": "string",
                        "pattern": r"^\d+[hdw]$",
                        "prompt": "Time estimate (e.g., 2h, 1d, 1w)",
                    },
                },
            }

            # Create specialized template inheriting from base
            bug_template = {
                "name": "bug-report",
                "extends": "base-task",
                "fields": {
                    "severity": {
                        "type": "choice",
                        "choices": ["minor", "major", "critical", "blocker"],
                        "required": True,
                    },
                    "steps_to_reproduce": {"type": "text", "required": True},
                    "expected_behavior": {"type": "text", "required": True},
                    "actual_behavior": {"type": "text", "required": True},
                },
                "content": """---
title: {{ title }}
type: issue
priority: {{ priority }}
severity: {{ severity }}
tags: [bug, {{ severity }}]
estimate: {{ estimate }}
---

# {{ title }}

## Steps to Reproduce
{{ steps_to_reproduce }}

## Expected Behavior
{{ expected_behavior }}

## Actual Behavior
{{ actual_behavior }}

## Environment
- OS: 
- Browser: 
- Version: 
""",
            }

            # Save templates
            base_file = project_path / "templates" / "task" / "base-task.yaml"
            base_file.write_text(yaml.dump(base_template))

            bug_file = project_path / "templates" / "issue" / "bug-report.yaml"
            bug_file.parent.mkdir(parents=True, exist_ok=True)
            bug_file.write_text(yaml.dump(bug_template))

            # Use inherited template
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "--template",
                    "bug-report",
                    "--title",
                    "Login button not working",
                    "--severity",
                    "critical",
                    "--priority",
                    "high",
                    "--estimate",
                    "4h",
                ],
                input="1. Go to login page\n2. Click login button\nButton should submit form\nNothing happens\n",
            )
            assert result.exit_code == 0

    def test_template_validation_workflow(self, integration_environment):
        """Test template validation and error handling."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create template with validation rules
            validated_template = {
                "name": "feature-request",
                "description": "Template for feature requests with validation",
                "fields": {
                    "title": {
                        "type": "string",
                        "required": True,
                        "min_length": 10,
                        "max_length": 100,
                    },
                    "business_value": {
                        "type": "text",
                        "required": True,
                        "min_length": 50,
                    },
                    "target_users": {
                        "type": "choice",
                        "choices": ["all", "premium", "enterprise", "specific"],
                        "multiple": True,
                        "required": True,
                    },
                    "priority_score": {
                        "type": "number",
                        "min": 1,
                        "max": 10,
                        "required": True,
                    },
                },
                "validation": {
                    "rules": [
                        {
                            "field": "priority_score",
                            "condition": "value >= 8",
                            "then_require": ["justification", "sponsor"],
                        }
                    ]
                },
            }

            # Save template
            template_file = (
                project_path / "templates" / "issue" / "feature-request.yaml"
            )
            template_file.write_text(yaml.dump(validated_template))

            # Test validation - should fail with short title
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "--template",
                    "feature-request",
                    "--title",
                    "Short",  # Too short
                    "--business_value",
                    "This will increase user engagement significantly",
                    "--target_users",
                    "premium",
                    "--priority_score",
                    "5",
                ],
            )
            assert result.exit_code == 1
            assert "min_length" in result.stdout or "too short" in result.stdout.lower()

            # Test conditional validation
            result = runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    "--template",
                    "feature-request",
                    "--title",
                    "Add advanced analytics dashboard",
                    "--business_value",
                    "This feature will provide detailed insights to users",
                    "--target_users",
                    "enterprise",
                    "--priority_score",
                    "9",  # High priority requires additional fields
                ],
            )
            assert result.exit_code == 1
            assert "justification" in result.stdout or "sponsor" in result.stdout

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestAdvancedQueryAndReporting:
    """Test advanced query and reporting capabilities."""

    def test_complex_query_workflow(self, integration_environment):
        """Test complex query construction and execution."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create diverse dataset
            self._create_query_test_data(runner)

            # Test complex AND/OR queries
            result = runner.invoke(
                app,
                [
                    "query",
                    "build",
                    "--where",
                    "status IN ('open', 'in_progress')",
                    "--and",
                    "priority IN ('high', 'critical')",
                    "--and",
                    "(assignee = 'alice' OR assignee = 'bob')",
                    "--and",
                    "created_at >= '2024-01-01'",
                    "--order-by",
                    "priority DESC, created_at ASC",
                    "--limit",
                    "20",
                ],
            )
            assert result.exit_code == 0

            # Test aggregation queries
            result = runner.invoke(
                app,
                [
                    "query",
                    "aggregate",
                    "--group-by",
                    "assignee,status",
                    "--count",
                    "*",
                    "--avg",
                    "estimate_hours",
                    "--sum",
                    "story_points",
                    "--having",
                    "COUNT(*) > 5",
                ],
            )
            assert result.exit_code == 0

            # Test JOIN-like queries across ticket types
            result = runner.invoke(
                app,
                [
                    "query",
                    "related",
                    "--from",
                    "task",
                    "--join",
                    "issue ON task.issue_id = issue.id",
                    "--join",
                    "epic ON task.epic_id = epic.id",
                    "--select",
                    "task.id, task.title, issue.severity, epic.business_value",
                    "--where",
                    "issue.severity = 'critical'",
                ],
            )
            assert result.exit_code == 0

            # Test full-text search with ranking
            result = runner.invoke(
                app,
                [
                    "query",
                    "search",
                    "--text",
                    "authentication security login",
                    "--in",
                    "title,description,comments",
                    "--rank-by",
                    "relevance",
                    "--boost",
                    "title:2.0",
                    "--min-score",
                    "0.5",
                ],
            )
            assert result.exit_code == 0

    def test_custom_report_generation(self, integration_environment):
        """Test custom report generation with various formats."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create report data
            self._create_query_test_data(runner)

            # Sprint velocity report
            result = runner.invoke(
                app,
                [
                    "report",
                    "generate",
                    "--type",
                    "sprint-velocity",
                    "--sprints",
                    "last-4",
                    "--metrics",
                    "completed-points,committed-points,carry-over",
                    "--group-by",
                    "team",
                    "--format",
                    "json",
                    "--output",
                    "velocity-report.json",
                ],
            )
            assert result.exit_code == 0

            # Burndown chart data
            result = runner.invoke(
                app,
                [
                    "report",
                    "burndown",
                    "--sprint",
                    "current",
                    "--resolution",
                    "daily",
                    "--include-scope-changes",
                    "--format",
                    "csv",
                    "--output",
                    "burndown.csv",
                ],
            )
            assert result.exit_code == 0

            # Team performance metrics
            result = runner.invoke(
                app,
                [
                    "report",
                    "team-metrics",
                    "--period",
                    "last-quarter",
                    "--metrics",
                    [
                        "avg-cycle-time",
                        "throughput",
                        "defect-rate",
                        "on-time-delivery",
                        "code-review-time",
                    ],
                    "--by-member",
                    "--format",
                    "html",
                    "--output",
                    "team-performance.html",
                ],
            )
            assert result.exit_code == 0

            # Custom SQL-like report
            result = runner.invoke(
                app,
                [
                    "report",
                    "custom",
                    "--query",
                    """
                SELECT 
                    assignee,
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    AVG(CASE WHEN estimate_hours IS NOT NULL THEN estimate_hours END) as avg_estimate,
                    SUM(CASE WHEN priority = 'critical' THEN 1 ELSE 0 END) as critical_tasks
                FROM tasks
                WHERE created_at >= '2024-01-01'
                GROUP BY assignee
                HAVING total_tasks > 0
                ORDER BY completed DESC
                """,
                    "--format",
                    "table",
                    "--output",
                    "-",  # stdout
                ],
            )
            assert result.exit_code == 0

    def test_dashboard_generation(self, integration_environment):
        """Test dashboard generation with multiple widgets."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Define dashboard configuration
            dashboard_config = {
                "name": "project-dashboard",
                "title": "Project Status Dashboard",
                "refresh": 300,  # 5 minutes
                "widgets": [
                    {
                        "type": "stat",
                        "title": "Open Tasks",
                        "query": "SELECT COUNT(*) FROM tasks WHERE status = 'open'",
                        "format": "number",
                        "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                    },
                    {
                        "type": "chart",
                        "title": "Task Status Distribution",
                        "query": "SELECT status, COUNT(*) FROM tasks GROUP BY status",
                        "chart_type": "pie",
                        "position": {"x": 3, "y": 0, "w": 6, "h": 4},
                    },
                    {
                        "type": "list",
                        "title": "Critical Issues",
                        "query": "SELECT id, title, assignee FROM issues WHERE severity = 'critical' AND status = 'open' LIMIT 10",
                        "position": {"x": 0, "y": 2, "w": 6, "h": 4},
                    },
                    {
                        "type": "timeline",
                        "title": "Epic Progress",
                        "query": "SELECT id, title, start_date, target_date, progress FROM epics WHERE status = 'active'",
                        "position": {"x": 6, "y": 4, "w": 6, "h": 4},
                    },
                ],
            }

            # Create dashboard
            dashboard_file = project_path / "dashboards" / "project-dashboard.yaml"
            dashboard_file.parent.mkdir(exist_ok=True)
            dashboard_file.write_text(yaml.dump(dashboard_config))

            result = runner.invoke(
                app, ["dashboard", "create", "--config", str(dashboard_file)]
            )
            assert result.exit_code == 0

            # Generate dashboard
            result = runner.invoke(
                app,
                [
                    "dashboard",
                    "generate",
                    "--name",
                    "project-dashboard",
                    "--format",
                    "html",
                    "--output",
                    "dashboard.html",
                    "--embed-data",
                ],
            )
            assert result.exit_code == 0

    def _create_query_test_data(self, runner):
        """Create diverse test data for queries."""
        # Create epics
        epics = [
            ("Q1 Features", "high", "2024-01-01", "2024-03-31"),
            ("Infrastructure Upgrade", "critical", "2024-02-01", "2024-04-30"),
            ("Mobile App", "medium", "2024-03-01", "2024-06-30"),
        ]

        epic_ids = []
        for title, priority, start, end in epics:
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    title,
                    "--priority",
                    priority,
                    "--start-date",
                    start,
                    "--target-date",
                    end,
                ],
            )
            epic_ids.append(self._extract_id(result.stdout, "EP"))

        # Create tasks with various attributes
        assignees = ["alice", "bob", "charlie", "diana", "eve"]
        for i in range(30):
            epic_id = epic_ids[i % len(epic_ids)]
            assignee = assignees[i % len(assignees)]
            priority = ["low", "medium", "high", "critical"][i % 4]
            status = ["open", "in_progress", "completed", "blocked"][i % 4]

            runner.invoke(
                app,
                [
                    "task",
                    "create",
                    f"Task {i+1}: Feature implementation",
                    "--epic",
                    epic_id,
                    "--assignee",
                    assignee,
                    "--priority",
                    priority,
                    "--status",
                    status,
                    "--estimate",
                    f"{(i % 8 + 1)}h",
                    "--story-points",
                    str(i % 5 + 1),
                ],
            )

        # Create issues
        for i in range(10):
            severity = ["low", "medium", "high", "critical"][i % 4]
            issue_type = ["bug", "feature", "enhancement"][i % 3]

            runner.invoke(
                app,
                [
                    "issue",
                    "create",
                    f"Issue {i+1}",
                    "--type",
                    issue_type,
                    "--severity",
                    severity,
                    "--component",
                    ["frontend", "backend", "api", "database"][i % 4],
                ],
            )

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestSecurityAndAccessControl:
    """Test security and access control features."""

    def test_role_based_access_control(self, integration_environment):
        """Test RBAC implementation for ticket management."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Configure roles
            roles = [
                {
                    "name": "admin",
                    "permissions": ["*"],
                    "description": "Full access to all operations",
                },
                {
                    "name": "developer",
                    "permissions": [
                        "task:create",
                        "task:update:assigned",
                        "task:read",
                        "issue:create",
                        "issue:comment",
                        "pr:create",
                    ],
                    "description": "Developer access",
                },
                {
                    "name": "viewer",
                    "permissions": ["*:read"],
                    "description": "Read-only access",
                },
            ]

            for role in roles:
                result = runner.invoke(
                    app,
                    [
                        "auth",
                        "role",
                        "create",
                        "--name",
                        role["name"],
                        "--permissions",
                        ",".join(role["permissions"]),
                        "--description",
                        role["description"],
                    ],
                )
                assert result.exit_code == 0

            # Create users with roles
            users = [
                ("alice", "admin", "alice@company.com"),
                ("bob", "developer", "bob@company.com"),
                ("charlie", "developer", "charlie@company.com"),
                ("diana", "viewer", "diana@company.com"),
            ]

            for username, role, email in users:
                result = runner.invoke(
                    app,
                    [
                        "auth",
                        "user",
                        "create",
                        "--username",
                        username,
                        "--role",
                        role,
                        "--email",
                        email,
                    ],
                )
                assert result.exit_code == 0

            # Test permission enforcement
            # Admin can do everything
            with patch.dict(os.environ, {"AITRACKDOWN_USER": "alice"}):
                result = runner.invoke(app, ["task", "create", "Admin task"])
                assert result.exit_code == 0

                result = runner.invoke(app, ["auth", "user", "list"])
                assert result.exit_code == 0

            # Developer has limited permissions
            with patch.dict(os.environ, {"AITRACKDOWN_USER": "bob"}):
                result = runner.invoke(app, ["task", "create", "Developer task"])
                assert result.exit_code == 0

                # Cannot manage users
                result = runner.invoke(
                    app, ["auth", "user", "create", "--username", "test"]
                )
                assert result.exit_code == 1
                assert "permission" in result.stdout.lower()

            # Viewer can only read
            with patch.dict(os.environ, {"AITRACKDOWN_USER": "diana"}):
                result = runner.invoke(app, ["task", "list"])
                assert result.exit_code == 0

                # Cannot create tasks
                result = runner.invoke(app, ["task", "create", "Viewer task"])
                assert result.exit_code == 1
                assert "permission" in result.stdout.lower()

    def test_audit_logging(self, integration_environment):
        """Test audit logging for all operations."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Enable audit logging
            result = runner.invoke(
                app, ["config", "set", "security.audit_logging", "true", "--global"]
            )
            assert result.exit_code == 0

            # Perform various operations
            operations = [
                ("task", "create", ["Test audit task", "--assignee", "alice"]),
                ("task", "update", ["TSK-001", "--status", "in_progress"]),
                ("issue", "create", ["Security issue", "--type", "bug"]),
                ("auth", "user", ["create", "--username", "newuser"]),
            ]

            for cmd_group, cmd, args in operations:
                runner.invoke(app, [cmd_group, cmd] + args)

            # Query audit log
            result = runner.invoke(
                app, ["audit", "log", "--last", "10", "--format", "json"]
            )
            assert result.exit_code == 0

            # Filter audit log
            result = runner.invoke(
                app,
                [
                    "audit",
                    "log",
                    "--user",
                    "alice",
                    "--action",
                    "create",
                    "--entity-type",
                    "task",
                ],
            )
            assert result.exit_code == 0

            # Export audit log
            result = runner.invoke(
                app,
                [
                    "audit",
                    "export",
                    "--start-date",
                    "2024-01-01",
                    "--end-date",
                    "2024-12-31",
                    "--format",
                    "csv",
                    "--output",
                    "audit-log.csv",
                ],
            )
            assert result.exit_code == 0

    def test_data_encryption(self, integration_environment):
        """Test data encryption for sensitive fields."""
        runner = integration_environment["runner"]
        project_path = integration_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Configure encryption
            result = runner.invoke(
                app,
                [
                    "security",
                    "encryption",
                    "enable",
                    "--fields",
                    "api_keys,tokens,passwords",
                    "--algorithm",
                    "AES-256-GCM",
                ],
            )
            assert result.exit_code == 0

            # Create task with sensitive data
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Deploy API with credentials",
                    "--metadata",
                    "api_key:sk-1234567890abcdef",
                    "--metadata",
                    "db_password:super_secret_pass",
                    "--tag",
                    "deployment",
                ],
            )
            assert result.exit_code == 0
            task_id = self._extract_id(result.stdout, "TSK")

            # Verify data is encrypted at rest
            task_file = project_path / "tasks" / "open" / f"{task_id}.md"
            content = task_file.read_text()
            assert "sk-1234567890abcdef" not in content
            assert "super_secret_pass" not in content

            # Read task (should decrypt for authorized user)
            result = runner.invoke(app, ["task", "show", task_id, "--show-metadata"])
            assert result.exit_code == 0
            # With proper auth, should see decrypted values

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
