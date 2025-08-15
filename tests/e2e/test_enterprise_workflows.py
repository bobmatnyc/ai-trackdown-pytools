"""End-to-end tests for enterprise and business workflows."""

import json
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app


@pytest.fixture
def enterprise_environment():
    """Create enterprise test environment with multiple projects."""
    temp_dir = tempfile.mkdtemp()
    org_path = Path(temp_dir) / "enterprise_org"
    org_path.mkdir()

    runner = CliRunner()

    # Create multiple project structure
    projects = {
        "platform": org_path / "platform-team",
        "mobile": org_path / "mobile-team",
        "web": org_path / "web-team",
        "data": org_path / "data-team",
    }

    for project_name, project_path in projects.items():
        project_path.mkdir(parents=True)
        with patch("os.getcwd", return_value=str(project_path)):
            result = runner.invoke(
                app,
                ["init", "project", "--name", f"{project_name.title()} Team Project"],
            )
            assert result.exit_code == 0

    yield {
        "runner": runner,
        "org_path": org_path,
        "projects": projects,
        "temp_dir": temp_dir,
    }

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestAgileScrumWorkflows:
    """Test Agile/Scrum methodology workflows."""

    def test_complete_sprint_workflow(self, enterprise_environment):
        """Test complete sprint planning, execution, and retrospective."""
        runner = enterprise_environment["runner"]
        platform_project = enterprise_environment["projects"]["platform"]

        with patch("os.getcwd", return_value=str(platform_project)):
            # Sprint planning
            sprint_number = 24
            sprint_start = date.today()
            sprint_end = sprint_start + timedelta(days=14)

            # Create sprint epic
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    f"Sprint {sprint_number}",
                    "--description",
                    "Q4 Sprint focused on API performance",
                    "--start-date",
                    sprint_start.isoformat(),
                    "--target-date",
                    sprint_end.isoformat(),
                    "--tag",
                    "sprint",
                    "--tag",
                    f"sprint-{sprint_number}",
                ],
            )
            assert result.exit_code == 0
            sprint_epic_id = self._extract_id(result.stdout, "EP")

            # User stories for sprint
            user_stories = [
                {
                    "title": "As a user, I want faster API response times",
                    "points": 8,
                    "priority": "high",
                    "acceptance_criteria": [
                        "API response time < 200ms for 95th percentile",
                        "Load testing shows 10k concurrent users supported",
                        "Database queries optimized with proper indexing",
                    ],
                },
                {
                    "title": "As an admin, I want detailed performance metrics",
                    "points": 5,
                    "priority": "medium",
                    "acceptance_criteria": [
                        "Dashboard shows real-time performance metrics",
                        "Historical data retained for 90 days",
                        "Alerts configured for performance degradation",
                    ],
                },
                {
                    "title": "As a developer, I want API rate limiting",
                    "points": 3,
                    "priority": "medium",
                    "acceptance_criteria": [
                        "Rate limiting implemented per API key",
                        "Configurable limits per tier",
                        "Clear error messages when limit exceeded",
                    ],
                },
            ]

            story_ids = []
            total_points = 0

            for story in user_stories:
                # Create user story
                acceptance_args = []
                for criterion in story["acceptance_criteria"]:
                    acceptance_args.extend(["--acceptance", criterion])

                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        story["title"],
                        "--epic",
                        sprint_epic_id,
                        "--priority",
                        story["priority"],
                        "--story-points",
                        str(story["points"]),
                        "--tag",
                        "user-story",
                        "--tag",
                        f"sprint-{sprint_number}",
                    ]
                    + acceptance_args,
                )
                assert result.exit_code == 0
                story_ids.append(self._extract_id(result.stdout, "TSK"))
                total_points += story["points"]

            # Break down stories into tasks
            story_tasks = {
                story_ids[0]: [  # API performance story
                    ("Analyze current API performance", "backend-dev-1", "1d"),
                    ("Implement caching layer", "backend-dev-2", "2d"),
                    ("Optimize database queries", "dba", "2d"),
                    ("Load testing and tuning", "perf-engineer", "1d"),
                ],
                story_ids[1]: [  # Metrics dashboard story
                    ("Design metrics dashboard", "ui-designer", "1d"),
                    ("Implement metrics collection", "backend-dev-1", "2d"),
                    ("Create dashboard frontend", "frontend-dev", "2d"),
                    ("Configure alerting", "devops", "1d"),
                ],
                story_ids[2]: [  # Rate limiting story
                    ("Design rate limiting strategy", "architect", "0.5d"),
                    ("Implement rate limiter", "backend-dev-2", "1d"),
                    ("Add configuration UI", "frontend-dev", "1d"),
                    ("Write documentation", "tech-writer", "0.5d"),
                ],
            }

            all_task_ids = []
            for story_id, tasks in story_tasks.items():
                for title, assignee, estimate in tasks:
                    result = runner.invoke(
                        app,
                        [
                            "task",
                            "create",
                            title,
                            "--parent",
                            story_id,
                            "--assignee",
                            assignee,
                            "--estimate",
                            estimate,
                            "--tag",
                            f"sprint-{sprint_number}",
                        ],
                    )
                    assert result.exit_code == 0
                    all_task_ids.append(self._extract_id(result.stdout, "TSK"))

            # Sprint commitment
            result = runner.invoke(
                app,
                [
                    "sprint",
                    "commit",
                    "--sprint",
                    str(sprint_number),
                    "--points",
                    str(total_points),
                    "--tasks",
                    ",".join(all_task_ids),
                ],
            )
            assert result.exit_code == 0

            # Daily standup simulation (day 3 of sprint)
            standup_updates = [
                (
                    "backend-dev-1",
                    all_task_ids[0],
                    "completed",
                    "Finished API analysis, found bottlenecks",
                ),
                (
                    "backend-dev-1",
                    all_task_ids[5],
                    "in_progress",
                    "Started metrics collection implementation",
                ),
                (
                    "backend-dev-2",
                    all_task_ids[1],
                    "in_progress",
                    "Caching layer 50% complete",
                ),
                ("dba", all_task_ids[2], "blocked", "Waiting for production DB access"),
                (
                    "ui-designer",
                    all_task_ids[4],
                    "completed",
                    "Dashboard designs approved",
                ),
            ]

            for assignee, task_id, status, note in standup_updates:
                with patch.dict(os.environ, {"AITRACKDOWN_USER": assignee}):
                    result = runner.invoke(
                        app,
                        [
                            "standup",
                            "update",
                            "--task",
                            task_id,
                            "--status",
                            status,
                            "--note",
                            note,
                            "--date",
                            (sprint_start + timedelta(days=3)).isoformat(),
                        ],
                    )
                    assert result.exit_code == 0

            # Generate standup report
            result = runner.invoke(
                app,
                [
                    "standup",
                    "report",
                    "--date",
                    (sprint_start + timedelta(days=3)).isoformat(),
                    "--format",
                    "summary",
                ],
            )
            assert result.exit_code == 0

            # Mid-sprint: scope change request
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Emergency: Fix critical security vulnerability",
                    "--priority",
                    "critical",
                    "--assignee",
                    "security-engineer",
                    "--estimate",
                    "2d",
                    "--tag",
                    f"sprint-{sprint_number}",
                    "--tag",
                    "scope-change",
                ],
            )
            assert result.exit_code == 0
            emergency_task_id = self._extract_id(result.stdout, "TSK")

            # Add to sprint with impact analysis
            result = runner.invoke(
                app,
                [
                    "sprint",
                    "add-task",
                    "--sprint",
                    str(sprint_number),
                    "--task",
                    emergency_task_id,
                    "--impact",
                    "May affect rate limiting story completion",
                ],
            )
            assert result.exit_code == 0

            # Sprint progress tracking (day 7)
            completed_tasks = all_task_ids[:5]  # First 5 tasks completed
            in_progress_tasks = all_task_ids[5:8]  # Next 3 in progress

            for task_id in completed_tasks:
                runner.invoke(app, ["task", "complete", task_id])

            for task_id in in_progress_tasks:
                runner.invoke(
                    app, ["task", "update", task_id, "--status", "in_progress"]
                )

            # Generate burndown data
            result = runner.invoke(
                app,
                [
                    "sprint",
                    "burndown",
                    "--sprint",
                    str(sprint_number),
                    "--as-of",
                    (sprint_start + timedelta(days=7)).isoformat(),
                ],
            )
            assert result.exit_code == 0

            # Sprint review preparation
            result = runner.invoke(
                app,
                [
                    "sprint",
                    "review",
                    "prepare",
                    "--sprint",
                    str(sprint_number),
                    "--include-demos",
                    "--include-metrics",
                ],
            )
            assert result.exit_code == 0

            # Sprint retrospective
            retro_items = [
                (
                    "backend-dev-1",
                    "went-well",
                    "Great collaboration on API optimization",
                ),
                ("frontend-dev", "went-well", "Dashboard came together quickly"),
                ("dba", "improvement", "Need better process for prod DB access"),
                (
                    "backend-dev-2",
                    "improvement",
                    "Caching implementation took longer than estimated",
                ),
                (
                    "perf-engineer",
                    "action-item",
                    "Set up automated performance regression tests",
                ),
            ]

            for participant, category, item in retro_items:
                result = runner.invoke(
                    app,
                    [
                        "retro",
                        "add",
                        "--sprint",
                        str(sprint_number),
                        "--category",
                        category,
                        "--item",
                        item,
                        "--participant",
                        participant,
                    ],
                )
                assert result.exit_code == 0

            # Generate sprint report
            result = runner.invoke(
                app,
                [
                    "sprint",
                    "report",
                    "--sprint",
                    str(sprint_number),
                    "--include-velocity",
                    "--include-burndown",
                    "--include-retro",
                    "--format",
                    "pdf",
                    "--output",
                    f"sprint-{sprint_number}-report.pdf",
                ],
            )
            assert result.exit_code == 0

    def test_backlog_grooming_workflow(self, enterprise_environment):
        """Test product backlog grooming and prioritization."""
        runner = enterprise_environment["runner"]
        web_project = enterprise_environment["projects"]["web"]

        with patch("os.getcwd", return_value=str(web_project)):
            # Create product backlog items
            backlog_items = [
                {
                    "title": "Implement social login (OAuth)",
                    "type": "feature",
                    "business_value": 8,
                    "effort": 5,
                    "risk": 3,
                    "dependencies": [],
                },
                {
                    "title": "Migrate to microservices architecture",
                    "type": "technical",
                    "business_value": 6,
                    "effort": 13,
                    "risk": 8,
                    "dependencies": [],
                },
                {
                    "title": "Add multi-language support",
                    "type": "feature",
                    "business_value": 7,
                    "effort": 8,
                    "risk": 4,
                    "dependencies": [],
                },
                {
                    "title": "Implement GDPR compliance",
                    "type": "compliance",
                    "business_value": 10,
                    "effort": 8,
                    "risk": 9,
                    "dependencies": [],
                },
                {
                    "title": "Redesign user dashboard",
                    "type": "feature",
                    "business_value": 6,
                    "effort": 5,
                    "risk": 2,
                    "dependencies": ["Implement social login (OAuth)"],
                },
            ]

            item_ids = []
            for item in backlog_items:
                dep_args = []
                for dep in item["dependencies"]:
                    dep_args.extend(["--depends-on", dep])

                result = runner.invoke(
                    app,
                    [
                        "backlog",
                        "add",
                        "--title",
                        item["title"],
                        "--type",
                        item["type"],
                        "--business-value",
                        str(item["business_value"]),
                        "--effort",
                        str(item["effort"]),
                        "--risk",
                        str(item["risk"]),
                        "--status",
                        "backlog",
                    ]
                    + dep_args,
                )
                assert result.exit_code == 0
                item_ids.append(self._extract_id(result.stdout, "TSK"))

            # Calculate priority scores (WSJF - Weighted Shortest Job First)
            result = runner.invoke(
                app,
                [
                    "backlog",
                    "prioritize",
                    "--method",
                    "wsjf",
                    "--factors",
                    "business_value,time_criticality,risk_reduction,effort",
                ],
            )
            assert result.exit_code == 0

            # Grooming session
            grooming_decisions = [
                (item_ids[0], "ready", "Clear requirements, can start next sprint"),
                (item_ids[1], "needs-refinement", "Architecture design needed first"),
                (item_ids[2], "ready", "Requirements clear, UI mockups done"),
                (item_ids[3], "ready", "Legal requirements documented"),
                (item_ids[4], "blocked", "Waiting for dependency"),
            ]

            for item_id, status, note in grooming_decisions:
                result = runner.invoke(
                    app,
                    [
                        "backlog",
                        "groom",
                        "--item",
                        item_id,
                        "--status",
                        status,
                        "--note",
                        note,
                    ],
                )
                assert result.exit_code == 0

            # Generate groomed backlog report
            result = runner.invoke(
                app,
                [
                    "backlog",
                    "report",
                    "--status",
                    "ready",
                    "--order-by",
                    "priority",
                    "--include-dependencies",
                    "--format",
                    "markdown",
                ],
            )
            assert result.exit_code == 0

    def test_pi_planning_workflow(self, enterprise_environment):
        """Test Program Increment (PI) planning for scaled agile."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Create Program Increment
            pi_number = 4
            pi_start = date.today()
            pi_end = pi_start + timedelta(weeks=10)  # 5 sprints

            result = runner.invoke(
                app,
                [
                    "pi",
                    "create",
                    "--number",
                    str(pi_number),
                    "--name",
                    f"PI {pi_number}: Digital Transformation",
                    "--start-date",
                    pi_start.isoformat(),
                    "--end-date",
                    pi_end.isoformat(),
                    "--teams",
                    "platform,mobile,web,data",
                ],
            )
            assert result.exit_code == 0
            pi_id = self._extract_id(result.stdout, "PI")

            # PI Objectives per team
            pi_objectives = {
                "platform": [
                    ("Implement service mesh", 8, "committed"),
                    ("Zero-downtime deployments", 5, "committed"),
                    ("API gateway implementation", 3, "stretch"),
                ],
                "mobile": [
                    ("Native biometric authentication", 8, "committed"),
                    ("Offline mode support", 5, "committed"),
                    ("Push notification system", 3, "stretch"),
                ],
                "web": [
                    ("Progressive Web App conversion", 8, "committed"),
                    ("Accessibility WCAG 2.1 compliance", 5, "committed"),
                    ("A/B testing framework", 2, "stretch"),
                ],
                "data": [
                    ("Real-time analytics pipeline", 8, "committed"),
                    ("Data lake implementation", 5, "committed"),
                    ("ML model deployment platform", 3, "stretch"),
                ],
            }

            team_objectives = {}
            for team, objectives in pi_objectives.items():
                team_objectives[team] = []
                for title, business_value, commitment in objectives:
                    result = runner.invoke(
                        app,
                        [
                            "pi",
                            "add-objective",
                            "--pi",
                            pi_id,
                            "--team",
                            team,
                            "--title",
                            title,
                            "--business-value",
                            str(business_value),
                            "--commitment",
                            commitment,
                        ],
                    )
                    assert result.exit_code == 0
                    team_objectives[team].append(self._extract_id(result.stdout, "OBJ"))

            # Cross-team dependencies
            dependencies = [
                (
                    "mobile",
                    "Native biometric authentication",
                    "platform",
                    "API gateway implementation",
                ),
                (
                    "web",
                    "Progressive Web App conversion",
                    "platform",
                    "Service mesh implementation",
                ),
                (
                    "data",
                    "Real-time analytics pipeline",
                    "platform",
                    "Service mesh implementation",
                ),
            ]

            for from_team, from_obj, to_team, to_obj in dependencies:
                result = runner.invoke(
                    app,
                    [
                        "pi",
                        "add-dependency",
                        "--from-team",
                        from_team,
                        "--from-objective",
                        from_obj,
                        "--to-team",
                        to_team,
                        "--to-objective",
                        to_obj,
                        "--type",
                        "requires",
                    ],
                )
                assert result.exit_code == 0

            # Risk identification
            risks = [
                {
                    "title": "Service mesh learning curve",
                    "probability": "high",
                    "impact": "medium",
                    "mitigation": "Training sessions and POC in Sprint 1",
                    "owner": "platform-lead",
                },
                {
                    "title": "Third-party API reliability",
                    "probability": "medium",
                    "impact": "high",
                    "mitigation": "Implement circuit breakers and fallbacks",
                    "owner": "architect",
                },
            ]

            for risk in risks:
                result = runner.invoke(
                    app,
                    [
                        "pi",
                        "add-risk",
                        "--pi",
                        pi_id,
                        "--title",
                        risk["title"],
                        "--probability",
                        risk["probability"],
                        "--impact",
                        risk["impact"],
                        "--mitigation",
                        risk["mitigation"],
                        "--owner",
                        risk["owner"],
                    ],
                )
                assert result.exit_code == 0

            # Generate PI plan
            result = runner.invoke(
                app,
                [
                    "pi",
                    "plan",
                    "generate",
                    "--pi",
                    pi_id,
                    "--include-dependencies",
                    "--include-risks",
                    "--include-capacity",
                    "--format",
                    "html",
                    "--output",
                    f"pi-{pi_number}-plan.html",
                ],
            )
            assert result.exit_code == 0

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        import re

        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestEnterpriseIntegrationWorkflows:
    """Test enterprise system integration workflows."""

    def test_erp_integration_workflow(self, enterprise_environment):
        """Test integration with ERP systems for project tracking."""
        runner = enterprise_environment["runner"]
        data_project = enterprise_environment["projects"]["data"]

        with patch("os.getcwd", return_value=str(data_project)):
            # Configure ERP integration
            result = runner.invoke(
                app,
                [
                    "integrate",
                    "configure",
                    "sap",
                    "--endpoint",
                    "https://erp.company.com/api",
                    "--auth-type",
                    "oauth2",
                    "--client-id",
                    "aitrackdown_client",
                    "--project-mapping",
                    "WBS:epic,Task:task",
                ],
            )
            assert result.exit_code == 0

            # Import project structure from ERP
            mock_erp_response = {
                "projects": [
                    {
                        "wbs": "IT.2024.001",
                        "name": "Data Platform Modernization",
                        "budget": 2500000,
                        "start_date": "2024-01-01",
                        "end_date": "2024-12-31",
                        "tasks": [
                            {
                                "id": "IT.2024.001.01",
                                "name": "Requirements Analysis",
                                "assigned_cost_center": "IT-4100",
                                "planned_hours": 320,
                                "actual_hours": 280,
                            },
                            {
                                "id": "IT.2024.001.02",
                                "name": "Architecture Design",
                                "assigned_cost_center": "IT-4200",
                                "planned_hours": 480,
                                "actual_hours": 120,
                            },
                        ],
                    }
                ]
            }

            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = mock_erp_response
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                result = runner.invoke(
                    app,
                    [
                        "integrate",
                        "import",
                        "sap",
                        "--type",
                        "projects",
                        "--sync-financials",
                    ],
                )
                assert result.exit_code == 0

            # Sync time tracking back to ERP
            time_entries = [
                (
                    "developer1",
                    "IT.2024.001.02",
                    "2024-11-01",
                    8,
                    "Architecture review",
                ),
                ("developer2", "IT.2024.001.02", "2024-11-01", 6, "Component design"),
                ("developer1", "IT.2024.001.02", "2024-11-02", 8, "API design"),
            ]

            for user, task_ref, date, hours, description in time_entries:
                result = runner.invoke(
                    app,
                    [
                        "time",
                        "track",
                        "--user",
                        user,
                        "--task",
                        task_ref,
                        "--date",
                        date,
                        "--hours",
                        str(hours),
                        "--description",
                        description,
                    ],
                )
                assert result.exit_code == 0

            # Push time entries to ERP
            with patch("requests.post") as mock_post:
                mock_post.return_value.status_code = 201
                result = runner.invoke(
                    app,
                    [
                        "integrate",
                        "push",
                        "sap",
                        "--type",
                        "timesheet",
                        "--period",
                        "2024-11",
                    ],
                )
                assert result.exit_code == 0

    def test_crm_integration_workflow(self, enterprise_environment):
        """Test CRM integration for customer-driven development."""
        runner = enterprise_environment["runner"]
        web_project = enterprise_environment["projects"]["web"]

        with patch("os.getcwd", return_value=str(web_project)):
            # Configure Salesforce integration
            result = runner.invoke(
                app,
                [
                    "integrate",
                    "configure",
                    "salesforce",
                    "--instance",
                    "https://company.my.salesforce.com",
                    "--api-version",
                    "v57.0",
                    "--sync-cases",
                    "true",
                    "--sync-opportunities",
                    "true",
                ],
            )
            assert result.exit_code == 0

            # Import customer cases as issues
            mock_sf_cases = {
                "records": [
                    {
                        "Id": "5003000000ABC123",
                        "CaseNumber": "00123456",
                        "Subject": "Unable to export reports",
                        "Priority": "High",
                        "Status": "Open",
                        "Account": {"Name": "Enterprise Customer A"},
                        "Description": "Customer cannot export reports to PDF",
                    },
                    {
                        "Id": "5003000000ABC124",
                        "CaseNumber": "00123457",
                        "Subject": "Feature Request: Dark mode",
                        "Priority": "Medium",
                        "Status": "Open",
                        "Account": {"Name": "Enterprise Customer B"},
                        "Description": "Multiple users requesting dark mode",
                    },
                ]
            }

            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = mock_sf_cases
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                result = runner.invoke(
                    app,
                    [
                        "integrate",
                        "import",
                        "salesforce",
                        "--type",
                        "cases",
                        "--query",
                        "Status = 'Open' AND Priority IN ('High', 'Medium')",
                    ],
                )
                assert result.exit_code == 0

            # Link opportunities to epics for roadmap planning
            mock_opportunities = {
                "records": [
                    {
                        "Id": "0063000000XYZ789",
                        "Name": "Enterprise Customer C - Expansion",
                        "Amount": 250000,
                        "Probability": 75,
                        "CloseDate": "2024-12-31",
                        "Stage": "Negotiation",
                        "Feature_Requirements__c": "Advanced analytics, Custom dashboards",
                    }
                ]
            }

            with patch("requests.get") as mock_get:
                mock_response = Mock()
                mock_response.json.return_value = mock_opportunities
                mock_response.status_code = 200
                mock_get.return_value = mock_response

                result = runner.invoke(
                    app,
                    [
                        "integrate",
                        "import",
                        "salesforce",
                        "--type",
                        "opportunities",
                        "--create-epics",
                        "--min-value",
                        "100000",
                    ],
                )
                assert result.exit_code == 0

    def test_bi_reporting_integration(self, enterprise_environment):
        """Test Business Intelligence reporting integration."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Configure BI tool integration
            result = runner.invoke(
                app,
                [
                    "integrate",
                    "configure",
                    "powerbi",
                    "--workspace",
                    "Engineering Metrics",
                    "--dataset",
                    "AI-Trackdown-Analytics",
                    "--refresh-schedule",
                    "0 6 * * *",  # Daily at 6 AM
                ],
            )
            assert result.exit_code == 0

            # Export data for BI consumption
            result = runner.invoke(
                app,
                [
                    "export",
                    "bi-dataset",
                    "--format",
                    "parquet",
                    "--include",
                    "tasks,issues,epics,time_tracking,team_metrics",
                    "--period",
                    "last-90-days",
                    "--output-dir",
                    "/tmp/bi-export",
                ],
            )
            assert result.exit_code == 0

            # Generate executive dashboard data
            result = runner.invoke(
                app,
                [
                    "report",
                    "executive-metrics",
                    "--metrics",
                    [
                        "velocity-trend",
                        "defect-escape-rate",
                        "cycle-time",
                        "team-utilization",
                        "sprint-predictability",
                        "customer-satisfaction",
                    ],
                    "--format",
                    "json",
                    "--output",
                    "exec-metrics.json",
                ],
            )
            assert result.exit_code == 0

            # Push to BI platform
            with patch("requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                result = runner.invoke(
                    app,
                    [
                        "integrate",
                        "push",
                        "powerbi",
                        "--dataset",
                        "AI-Trackdown-Analytics",
                        "--tables",
                        "tasks,metrics,team_performance",
                    ],
                )
                assert result.exit_code == 0

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        import re

        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestComplianceAndAuditWorkflows:
    """Test compliance and audit trail workflows."""

    def test_sox_compliance_workflow(self, enterprise_environment):
        """Test SOX compliance for change management."""
        runner = enterprise_environment["runner"]
        platform_project = enterprise_environment["projects"]["platform"]

        with patch("os.getcwd", return_value=str(platform_project)):
            # Enable SOX compliance mode
            result = runner.invoke(
                app,
                [
                    "compliance",
                    "enable",
                    "sox",
                    "--require-approvals",
                    "2",
                    "--segregation-of-duties",
                    "true",
                    "--audit-trail",
                    "immutable",
                ],
            )
            assert result.exit_code == 0

            # Create change request
            result = runner.invoke(
                app,
                [
                    "change",
                    "create",
                    "--title",
                    "Database schema update for customer table",
                    "--type",
                    "database-change",
                    "--risk",
                    "medium",
                    "--impact",
                    "high",
                    "--systems",
                    "customer-db,billing-service",
                    "--requestor",
                    "developer1",
                    "--business-justification",
                    "Required for new billing features",
                ],
            )
            assert result.exit_code == 0
            change_id = self._extract_id(result.stdout, "CHG")

            # Attach evidence
            evidence_files = [
                ("test-results.xml", "Test execution results"),
                ("code-review.pdf", "Peer review documentation"),
                ("rollback-plan.md", "Rollback procedures"),
            ]

            for filename, description in evidence_files:
                result = runner.invoke(
                    app,
                    [
                        "change",
                        "attach-evidence",
                        "--change",
                        change_id,
                        "--file",
                        f"/tmp/{filename}",
                        "--description",
                        description,
                        "--checksum",
                        "sha256",
                    ],
                )
                assert result.exit_code == 0

            # Request approvals
            approvers = [
                ("manager1", "manager", "Business approval"),
                ("architect1", "technical", "Technical approval"),
                ("security1", "security", "Security review"),
            ]

            for approver, role, reason in approvers:
                result = runner.invoke(
                    app,
                    [
                        "change",
                        "request-approval",
                        "--change",
                        change_id,
                        "--approver",
                        approver,
                        "--role",
                        role,
                        "--reason",
                        reason,
                    ],
                )
                assert result.exit_code == 0

            # Simulate approvals
            for approver, role, _ in approvers[:2]:  # First 2 approve
                with patch.dict(os.environ, {"AITRACKDOWN_USER": approver}):
                    result = runner.invoke(
                        app,
                        [
                            "change",
                            "approve",
                            "--change",
                            change_id,
                            "--comment",
                            f"Approved by {role}",
                        ],
                    )
                    assert result.exit_code == 0

            # Implementation tracking
            result = runner.invoke(
                app,
                [
                    "change",
                    "implement",
                    "--change",
                    change_id,
                    "--start-time",
                    datetime.now().isoformat(),
                    "--implementer",
                    "developer1",
                ],
            )
            assert result.exit_code == 0

            # Verification steps
            verification_steps = [
                ("Pre-deployment health check", "passed", "All systems operational"),
                ("Database migration", "passed", "Schema updated successfully"),
                ("Service deployment", "passed", "New version deployed"),
                ("Post-deployment validation", "passed", "All tests passing"),
            ]

            for step, status, notes in verification_steps:
                result = runner.invoke(
                    app,
                    [
                        "change",
                        "verify",
                        "--change",
                        change_id,
                        "--step",
                        step,
                        "--status",
                        status,
                        "--notes",
                        notes,
                    ],
                )
                assert result.exit_code == 0

            # Close change
            result = runner.invoke(
                app,
                [
                    "change",
                    "close",
                    "--change",
                    change_id,
                    "--outcome",
                    "successful",
                    "--lessons-learned",
                    "Smooth deployment, good coordination",
                ],
            )
            assert result.exit_code == 0

            # Generate audit report
            result = runner.invoke(
                app,
                [
                    "compliance",
                    "audit-report",
                    "--framework",
                    "sox",
                    "--period",
                    "2024-Q4",
                    "--include-changes",
                    "--include-approvals",
                    "--include-evidence",
                    "--format",
                    "pdf",
                    "--output",
                    "sox-audit-q4.pdf",
                ],
            )
            assert result.exit_code == 0

    def test_gdpr_compliance_workflow(self, enterprise_environment):
        """Test GDPR compliance for data privacy."""
        runner = enterprise_environment["runner"]
        data_project = enterprise_environment["projects"]["data"]

        with patch("os.getcwd", return_value=str(data_project)):
            # Enable GDPR compliance
            result = runner.invoke(
                app,
                [
                    "compliance",
                    "enable",
                    "gdpr",
                    "--data-retention",
                    "90d",
                    "--pii-encryption",
                    "true",
                    "--audit-access",
                    "true",
                ],
            )
            assert result.exit_code == 0

            # Register data processing activities
            processing_activities = [
                {
                    "name": "User Profile Management",
                    "purpose": "Store and manage user profiles",
                    "legal_basis": "consent",
                    "data_categories": ["name", "email", "preferences"],
                    "retention": "account_lifetime",
                    "recipients": ["internal", "email_provider"],
                },
                {
                    "name": "Analytics Tracking",
                    "purpose": "Improve service quality",
                    "legal_basis": "legitimate_interest",
                    "data_categories": ["usage_data", "ip_address"],
                    "retention": "90_days",
                    "recipients": ["internal", "analytics_provider"],
                },
            ]

            for activity in processing_activities:
                result = runner.invoke(
                    app,
                    [
                        "gdpr",
                        "register-processing",
                        "--name",
                        activity["name"],
                        "--purpose",
                        activity["purpose"],
                        "--legal-basis",
                        activity["legal_basis"],
                        "--retention",
                        activity["retention"],
                        "--data-categories",
                        ",".join(activity["data_categories"]),
                        "--recipients",
                        ",".join(activity["recipients"]),
                    ],
                )
                assert result.exit_code == 0

            # Handle data subject request
            result = runner.invoke(
                app,
                [
                    "gdpr",
                    "dsr",
                    "create",
                    "--type",
                    "access",
                    "--subject-email",
                    "user@example.com",
                    "--received-date",
                    date.today().isoformat(),
                ],
            )
            assert result.exit_code == 0
            dsr_id = self._extract_id(result.stdout, "DSR")

            # Process the request
            result = runner.invoke(
                app,
                [
                    "gdpr",
                    "dsr",
                    "process",
                    "--request",
                    dsr_id,
                    "--action",
                    "gather-data",
                    "--systems",
                    "user-db,analytics-db,logs",
                ],
            )
            assert result.exit_code == 0

            # Generate data export
            result = runner.invoke(
                app,
                [
                    "gdpr",
                    "dsr",
                    "export",
                    "--request",
                    dsr_id,
                    "--format",
                    "json",
                    "--include-metadata",
                    "--output",
                    f"dsr-{dsr_id}-export.json",
                ],
            )
            assert result.exit_code == 0

            # Complete request
            result = runner.invoke(
                app,
                [
                    "gdpr",
                    "dsr",
                    "complete",
                    "--request",
                    dsr_id,
                    "--response-date",
                    date.today().isoformat(),
                    "--method",
                    "secure-email",
                ],
            )
            assert result.exit_code == 0

            # Privacy impact assessment
            result = runner.invoke(
                app,
                [
                    "gdpr",
                    "pia",
                    "create",
                    "--project",
                    "New ML Feature",
                    "--description",
                    "Implement recommendation engine",
                    "--data-types",
                    "browsing_history,purchase_history",
                    "--purpose",
                    "personalized_recommendations",
                ],
            )
            assert result.exit_code == 0
            pia_id = self._extract_id(result.stdout, "PIA")

            # Assess risks
            risks = [
                ("Data breach", "medium", "high", "Encryption at rest and in transit"),
                ("Unauthorized access", "low", "medium", "Role-based access control"),
                (
                    "Data retention",
                    "medium",
                    "medium",
                    "Automated deletion after 90 days",
                ),
            ]

            for risk, probability, impact, mitigation in risks:
                result = runner.invoke(
                    app,
                    [
                        "gdpr",
                        "pia",
                        "add-risk",
                        "--assessment",
                        pia_id,
                        "--risk",
                        risk,
                        "--probability",
                        probability,
                        "--impact",
                        impact,
                        "--mitigation",
                        mitigation,
                    ],
                )
                assert result.exit_code == 0

    def test_iso27001_compliance_workflow(self, enterprise_environment):
        """Test ISO 27001 information security compliance."""
        runner = enterprise_environment["runner"]
        platform_project = enterprise_environment["projects"]["platform"]

        with patch("os.getcwd", return_value=str(platform_project)):
            # Enable ISO 27001 compliance
            result = runner.invoke(
                app,
                [
                    "compliance",
                    "enable",
                    "iso27001",
                    "--controls",
                    "A.5,A.6,A.8,A.9,A.12,A.13,A.14",
                    "--risk-assessment",
                    "required",
                    "--incident-management",
                    "true",
                ],
            )
            assert result.exit_code == 0

            # Create security incident
            result = runner.invoke(
                app,
                [
                    "incident",
                    "create",
                    "--title",
                    "Suspicious login attempts detected",
                    "--severity",
                    "medium",
                    "--category",
                    "unauthorized-access",
                    "--detected-by",
                    "siem-alert",
                    "--affected-systems",
                    "auth-service,user-db",
                ],
            )
            assert result.exit_code == 0
            incident_id = self._extract_id(result.stdout, "INC")

            # Incident response steps
            response_steps = [
                (
                    "Investigate",
                    "security-analyst",
                    "Reviewing logs and access patterns",
                ),
                ("Contain", "security-analyst", "Blocked suspicious IP addresses"),
                ("Eradicate", "security-engineer", "Reset affected user passwords"),
                ("Recover", "ops-team", "Services restored to normal operation"),
                (
                    "Lessons Learned",
                    "security-lead",
                    "Implement rate limiting on auth endpoint",
                ),
            ]

            for step, assignee, notes in response_steps:
                result = runner.invoke(
                    app,
                    [
                        "incident",
                        "update",
                        "--incident",
                        incident_id,
                        "--step",
                        step,
                        "--assignee",
                        assignee,
                        "--notes",
                        notes,
                        "--timestamp",
                        datetime.now().isoformat(),
                    ],
                )
                assert result.exit_code == 0

            # Close incident
            result = runner.invoke(
                app,
                [
                    "incident",
                    "close",
                    "--incident",
                    incident_id,
                    "--root-cause",
                    "Credential stuffing attack",
                    "--resolution",
                    "IPs blocked, passwords reset, rate limiting added",
                    "--prevented-impact",
                    "No data breach occurred",
                ],
            )
            assert result.exit_code == 0

            # Risk assessment
            result = runner.invoke(
                app,
                [
                    "risk",
                    "assess",
                    "--asset",
                    "Customer Database",
                    "--threats",
                    "data-breach,unauthorized-access,ransomware",
                    "--vulnerabilities",
                    "unpatched-systems,weak-passwords",
                    "--impact",
                    "high",
                    "--likelihood",
                    "medium",
                ],
            )
            assert result.exit_code == 0
            risk_id = self._extract_id(result.stdout, "RISK")

            # Risk treatment
            result = runner.invoke(
                app,
                [
                    "risk",
                    "treat",
                    "--risk",
                    risk_id,
                    "--strategy",
                    "mitigate",
                    "--controls",
                    "patch-management,mfa,backup-procedures",
                    "--residual-risk",
                    "low",
                ],
            )
            assert result.exit_code == 0

            # Generate compliance report
            result = runner.invoke(
                app,
                [
                    "compliance",
                    "report",
                    "iso27001",
                    "--include-controls",
                    "--include-risks",
                    "--include-incidents",
                    "--period",
                    "2024",
                    "--format",
                    "pdf",
                    "--output",
                    "iso27001-compliance-2024.pdf",
                ],
            )
            assert result.exit_code == 0

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        import re

        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestMultiTenantAndTeamWorkflows:
    """Test multi-tenant and cross-team collaboration workflows."""

    def test_multi_tenant_isolation(self, enterprise_environment):
        """Test multi-tenant data isolation and access control."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Create tenants
            tenants = [
                ("tenant-a", "Customer A", "enterprise"),
                ("tenant-b", "Customer B", "standard"),
                ("tenant-c", "Customer C", "enterprise"),
            ]

            for tenant_id, name, tier in tenants:
                result = runner.invoke(
                    app,
                    [
                        "tenant",
                        "create",
                        "--id",
                        tenant_id,
                        "--name",
                        name,
                        "--tier",
                        tier,
                        "--isolation",
                        "strict",
                    ],
                )
                assert result.exit_code == 0

            # Create users with tenant access
            users = [
                ("alice@a.com", "tenant-a", "admin"),
                ("bob@a.com", "tenant-a", "developer"),
                ("charlie@b.com", "tenant-b", "admin"),
                ("diana@c.com", "tenant-c", "developer"),
                ("eve@msp.com", "all", "support"),  # MSP support user
            ]

            for email, tenant_access, role in users:
                result = runner.invoke(
                    app,
                    [
                        "user",
                        "create",
                        "--email",
                        email,
                        "--tenant",
                        tenant_access,
                        "--role",
                        role,
                    ],
                )
                assert result.exit_code == 0

            # Test cross-tenant access control
            # Alice (tenant-a) tries to access tenant-b data
            with patch.dict(
                os.environ,
                {"AITRACKDOWN_USER": "alice@a.com", "AITRACKDOWN_TENANT": "tenant-b"},
            ):
                result = runner.invoke(app, ["task", "list"])
                assert result.exit_code == 1
                assert (
                    "access denied" in result.stdout.lower()
                    or "unauthorized" in result.stdout.lower()
                )

            # Eve (MSP support) can access all tenants
            for tenant_id, _, _ in tenants:
                with patch.dict(
                    os.environ,
                    {
                        "AITRACKDOWN_USER": "eve@msp.com",
                        "AITRACKDOWN_TENANT": tenant_id,
                    },
                ):
                    result = runner.invoke(app, ["task", "list"])
                    assert result.exit_code == 0

    def test_cross_functional_team_collaboration(self, enterprise_environment):
        """Test collaboration between different functional teams."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Create cross-functional initiative
            result = runner.invoke(
                app,
                [
                    "initiative",
                    "create",
                    "--title",
                    "Customer Portal Redesign",
                    "--teams",
                    "ux,frontend,backend,qa,devops",
                    "--duration",
                    "6m",
                    "--budget",
                    "500000",
                ],
            )
            assert result.exit_code == 0
            initiative_id = self._extract_id(result.stdout, "INIT")

            # Create team-specific work streams
            workstreams = {
                "ux": {
                    "title": "User Research and Design",
                    "deliverables": [
                        "User personas",
                        "Journey maps",
                        "Wireframes",
                        "Prototypes",
                    ],
                },
                "frontend": {
                    "title": "UI Implementation",
                    "deliverables": [
                        "Component library",
                        "Responsive layouts",
                        "Accessibility",
                    ],
                },
                "backend": {
                    "title": "API Development",
                    "deliverables": ["REST APIs", "GraphQL schema", "Authentication"],
                },
                "qa": {
                    "title": "Quality Assurance",
                    "deliverables": [
                        "Test plans",
                        "Automation suite",
                        "Performance tests",
                    ],
                },
                "devops": {
                    "title": "Infrastructure and Deployment",
                    "deliverables": ["CI/CD pipeline", "Monitoring", "Auto-scaling"],
                },
            }

            workstream_ids = {}
            for team, details in workstreams.items():
                result = runner.invoke(
                    app,
                    [
                        "workstream",
                        "create",
                        "--initiative",
                        initiative_id,
                        "--team",
                        team,
                        "--title",
                        details["title"],
                        "--deliverables",
                        json.dumps(details["deliverables"]),
                    ],
                )
                assert result.exit_code == 0
                workstream_ids[team] = self._extract_id(result.stdout, "WS")

            # Define dependencies between workstreams
            dependencies = [
                ("frontend", "ux", "UI depends on UX designs"),
                ("backend", "ux", "API design based on user requirements"),
                ("qa", "frontend", "Testing depends on UI completion"),
                ("qa", "backend", "API testing depends on backend"),
                ("devops", "backend", "Infrastructure based on backend requirements"),
            ]

            for dependent, dependency, reason in dependencies:
                result = runner.invoke(
                    app,
                    [
                        "workstream",
                        "add-dependency",
                        "--from",
                        workstream_ids[dependent],
                        "--to",
                        workstream_ids[dependency],
                        "--reason",
                        reason,
                    ],
                )
                assert result.exit_code == 0

            # Weekly sync meeting notes
            sync_notes = {
                "week": 3,
                "updates": {
                    "ux": "Personas complete, working on journey maps",
                    "frontend": "Component library 40% complete",
                    "backend": "Authentication API ready for testing",
                    "qa": "Test plan approved, starting automation",
                    "devops": "CI pipeline configured",
                },
                "blockers": {
                    "frontend": "Waiting for final design assets",
                    "qa": "Need access to staging environment",
                },
                "decisions": [
                    "Use Material-UI for component library",
                    "Implement JWT for authentication",
                    "Target 99.9% uptime SLA",
                ],
            }

            result = runner.invoke(
                app,
                [
                    "meeting",
                    "record",
                    "--type",
                    "weekly-sync",
                    "--initiative",
                    initiative_id,
                    "--date",
                    date.today().isoformat(),
                    "--attendees",
                    ",".join(workstreams.keys()),
                    "--notes",
                    json.dumps(sync_notes),
                ],
            )
            assert result.exit_code == 0

    def test_resource_allocation_across_teams(self, enterprise_environment):
        """Test resource allocation and capacity planning across teams."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Define team capacities
            teams = {
                "platform": {"members": 8, "velocity": 45},
                "mobile": {"members": 6, "velocity": 35},
                "web": {"members": 10, "velocity": 55},
                "data": {"members": 5, "velocity": 25},
            }

            for team, info in teams.items():
                result = runner.invoke(
                    app,
                    [
                        "team",
                        "configure",
                        "--name",
                        team,
                        "--members",
                        str(info["members"]),
                        "--velocity",
                        str(info["velocity"]),
                        "--sprint-length",
                        "2w",
                    ],
                )
                assert result.exit_code == 0

            # Create resource requests
            requests = [
                {
                    "project": "API Gateway Implementation",
                    "team": "platform",
                    "resources": 3,
                    "duration": "3 sprints",
                    "skills": ["kubernetes", "golang"],
                    "priority": "high",
                },
                {
                    "project": "Mobile App Redesign",
                    "team": "mobile",
                    "resources": 4,
                    "duration": "4 sprints",
                    "skills": ["ios", "android", "react-native"],
                    "priority": "medium",
                },
                {
                    "project": "Analytics Dashboard",
                    "team": "data",
                    "resources": 2,
                    "duration": "2 sprints",
                    "skills": ["python", "spark", "tableau"],
                    "priority": "medium",
                },
            ]

            request_ids = []
            for req in requests:
                result = runner.invoke(
                    app,
                    [
                        "resource",
                        "request",
                        "--project",
                        req["project"],
                        "--team",
                        req["team"],
                        "--count",
                        str(req["resources"]),
                        "--duration",
                        req["duration"],
                        "--skills",
                        ",".join(req["skills"]),
                        "--priority",
                        req["priority"],
                    ],
                )
                assert result.exit_code == 0
                request_ids.append(self._extract_id(result.stdout, "RES"))

            # Run resource allocation algorithm
            result = runner.invoke(
                app,
                [
                    "resource",
                    "allocate",
                    "--method",
                    "priority-based",
                    "--constraints",
                    "skill-match,capacity",
                    "--start-date",
                    date.today().isoformat(),
                ],
            )
            assert result.exit_code == 0

            # Check allocation results
            result = runner.invoke(
                app,
                [
                    "resource",
                    "allocation-report",
                    "--format",
                    "gantt",
                    "--output",
                    "resource-allocation.html",
                ],
            )
            assert result.exit_code == 0

            # Handle resource conflict
            result = runner.invoke(
                app,
                [
                    "resource",
                    "conflict",
                    "--team",
                    "platform",
                    "--period",
                    "next-sprint",
                    "--resolution",
                    "negotiate",
                ],
            )
            assert result.exit_code == 0

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        import re

        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


class TestAdvancedReportingAndAnalytics:
    """Test advanced reporting and analytics workflows."""

    def test_predictive_analytics_workflow(self, enterprise_environment):
        """Test predictive analytics for project management."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Train predictive models
            result = runner.invoke(
                app,
                [
                    "analytics",
                    "train",
                    "--model",
                    "delivery-predictor",
                    "--features",
                    "team_size,complexity,dependencies,historical_velocity",
                    "--target",
                    "actual_delivery_date",
                    "--algorithm",
                    "random-forest",
                    "--training-data",
                    "last-2-years",
                ],
            )
            assert result.exit_code == 0

            # Predict delivery for current projects
            projects_to_predict = [
                ("Mobile App v3.0", "mobile", 8, "high"),
                ("API Refactoring", "platform", 5, "medium"),
                ("Analytics Pipeline", "data", 13, "high"),
            ]

            for project, team, estimated_sprints, complexity in projects_to_predict:
                result = runner.invoke(
                    app,
                    [
                        "analytics",
                        "predict",
                        "--model",
                        "delivery-predictor",
                        "--project",
                        project,
                        "--team",
                        team,
                        "--estimated-sprints",
                        str(estimated_sprints),
                        "--complexity",
                        complexity,
                    ],
                )
                assert result.exit_code == 0

            # Risk prediction
            result = runner.invoke(
                app,
                [
                    "analytics",
                    "train",
                    "--model",
                    "risk-predictor",
                    "--features",
                    "team_changes,requirement_changes,technical_debt,dependencies",
                    "--target",
                    "project_delayed",
                    "--algorithm",
                    "logistic-regression",
                ],
            )
            assert result.exit_code == 0

            # Quality prediction
            result = runner.invoke(
                app,
                [
                    "analytics",
                    "train",
                    "--model",
                    "quality-predictor",
                    "--features",
                    "code_coverage,review_coverage,team_experience,complexity",
                    "--target",
                    "defect_rate",
                    "--algorithm",
                    "gradient-boosting",
                ],
            )
            assert result.exit_code == 0

            # Generate predictive dashboard
            result = runner.invoke(
                app,
                [
                    "analytics",
                    "dashboard",
                    "--type",
                    "predictive",
                    "--models",
                    "delivery-predictor,risk-predictor,quality-predictor",
                    "--projects",
                    "active",
                    "--output",
                    "predictive-analytics.html",
                ],
            )
            assert result.exit_code == 0

    def test_team_performance_analytics(self, enterprise_environment):
        """Test team performance analytics and insights."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Collect performance metrics
            metrics_config = {
                "velocity": {
                    "measure": "story_points_completed",
                    "period": "sprint",
                    "aggregation": "average",
                },
                "quality": {
                    "measure": "defect_escape_rate",
                    "period": "release",
                    "aggregation": "percentage",
                },
                "efficiency": {
                    "measure": "cycle_time",
                    "period": "task",
                    "aggregation": "median",
                },
                "collaboration": {
                    "measure": "pr_review_time",
                    "period": "day",
                    "aggregation": "average",
                },
            }

            for metric, config in metrics_config.items():
                result = runner.invoke(
                    app,
                    [
                        "metrics",
                        "configure",
                        "--name",
                        metric,
                        "--measure",
                        config["measure"],
                        "--period",
                        config["period"],
                        "--aggregation",
                        config["aggregation"],
                    ],
                )
                assert result.exit_code == 0

            # Generate team comparison report
            result = runner.invoke(
                app,
                [
                    "report",
                    "team-comparison",
                    "--teams",
                    "platform,mobile,web,data",
                    "--metrics",
                    "velocity,quality,efficiency,collaboration",
                    "--period",
                    "last-6-months",
                    "--format",
                    "interactive-html",
                    "--output",
                    "team-comparison.html",
                ],
            )
            assert result.exit_code == 0

            # Individual performance insights
            result = runner.invoke(
                app,
                [
                    "analytics",
                    "individual-insights",
                    "--anonymized",
                    "true",
                    "--metrics",
                    "task_completion_rate,code_quality,collaboration_score",
                    "--identify",
                    "top_performers,improvement_areas",
                    "--output",
                    "individual-insights.json",
                ],
            )
            assert result.exit_code == 0

            # Team health metrics
            health_indicators = [
                "burnout_risk",
                "knowledge_silos",
                "communication_patterns",
                "work_distribution",
                "skill_gaps",
            ]

            for indicator in health_indicators:
                result = runner.invoke(
                    app,
                    [
                        "analytics",
                        "team-health",
                        "--indicator",
                        indicator,
                        "--teams",
                        "all",
                        "--threshold",
                        "warning",
                    ],
                )
                assert result.exit_code == 0

    def test_executive_dashboard_generation(self, enterprise_environment):
        """Test executive dashboard and reporting."""
        runner = enterprise_environment["runner"]
        org_path = enterprise_environment["org_path"]

        with patch("os.getcwd", return_value=str(org_path)):
            # Configure executive KPIs
            kpis = [
                {
                    "name": "Time to Market",
                    "formula": "avg(release_date - project_start_date)",
                    "target": "< 90 days",
                    "weight": 0.25,
                },
                {
                    "name": "Budget Variance",
                    "formula": "(actual_cost - planned_cost) / planned_cost * 100",
                    "target": "< 10%",
                    "weight": 0.20,
                },
                {
                    "name": "Customer Satisfaction",
                    "formula": "avg(customer_feedback_score)",
                    "target": "> 4.5",
                    "weight": 0.30,
                },
                {
                    "name": "Innovation Index",
                    "formula": "new_features / total_features * 100",
                    "target": "> 30%",
                    "weight": 0.25,
                },
            ]

            for kpi in kpis:
                result = runner.invoke(
                    app,
                    [
                        "kpi",
                        "define",
                        "--name",
                        kpi["name"],
                        "--formula",
                        kpi["formula"],
                        "--target",
                        kpi["target"],
                        "--weight",
                        str(kpi["weight"]),
                    ],
                )
                assert result.exit_code == 0

            # Generate executive summary
            result = runner.invoke(
                app,
                [
                    "report",
                    "executive-summary",
                    "--period",
                    "2024-Q4",
                    "--sections",
                    [
                        "kpi-scorecard",
                        "portfolio-status",
                        "risk-summary",
                        "budget-overview",
                        "strategic-initiatives",
                        "team-utilization",
                    ],
                    "--format",
                    "pdf",
                    "--branding",
                    "corporate",
                    "--output",
                    "exec-summary-q4.pdf",
                ],
            )
            assert result.exit_code == 0

            # Real-time dashboard
            result = runner.invoke(
                app,
                [
                    "dashboard",
                    "executive",
                    "--refresh-rate",
                    "5m",
                    "--widgets",
                    [
                        "kpi-gauges",
                        "project-timeline",
                        "budget-burndown",
                        "risk-heatmap",
                        "team-capacity",
                        "delivery-forecast",
                    ],
                    "--export",
                    "shareable-link",
                ],
            )
            assert result.exit_code == 0

    def _extract_id(self, output: str, prefix: str) -> str:
        """Extract ID with given prefix from output."""
        import re

        match = re.search(rf"({prefix}-\d+)", output)
        if match:
            return match.group(1)
        return f"{prefix}-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
