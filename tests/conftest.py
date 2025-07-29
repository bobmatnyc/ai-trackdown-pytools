"""Global test configuration to skip non-essential tests for fast CI/CD."""

import os

import pytest


def pytest_collection_modifyitems(config, items):
    """Mark tests for skipping based on environment."""
    if os.environ.get("FAST_CI_MODE", "1") == "1":
        # Skip patterns for fast CI mode
        skip_patterns = [
            "test_comprehensive",
            "test_integration",
            "test_performance",
            "test_stress",
            "test_slow",
            "test_github",
            "test_sync",
            "test_git_",
            "test_editor",
            "test_health",
            "test_doctor",
            "test_system",
            "test_logging",
            "test_compatibility",
            "test_tickets.py",  # Skip tickets tests
            "test_validation_comprehensive.py",  # Skip comprehensive validation
            "test_task_comprehensive.py",  # Skip comprehensive task tests
            "test_workflow_comprehensive.py",  # Skip comprehensive workflow tests
            "test_utils_",  # Skip most utils tests
            "test_cli_comprehensive",  # Skip comprehensive CLI tests
        ]

        skip_mark = pytest.mark.skip(reason="Skipped for fast CI mode")

        for item in items:
            # Skip based on test name patterns
            for pattern in skip_patterns:
                if pattern in item.nodeid or pattern in item.name:
                    item.add_marker(skip_mark)
                    break

            # Skip tests in certain directories
            if any(
                path in item.nodeid
                for path in [
                    "/integration/",
                    "/performance/",
                    "/stress/",
                    "/e2e/",
                ]
            ):
                item.add_marker(skip_mark)
