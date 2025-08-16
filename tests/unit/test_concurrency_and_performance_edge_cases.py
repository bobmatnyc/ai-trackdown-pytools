"""Concurrency and performance edge case tests for AI Trackdown PyTools.

This test suite focuses on:
- Multi-threading and concurrency edge cases
- Resource exhaustion scenarios
- Performance under stress conditions
- Deadlock and race condition prevention
- Memory and file descriptor limits
- Large dataset handling
"""

import asyncio
import gc
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import psutil
import pytest

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.frontmatter import FrontmatterParser
from ai_trackdown_pytools.utils.templates import TemplateManager
from ai_trackdown_pytools.utils.validation import SchemaValidator


class TestConcurrencyEdgeCases:
    """Test concurrency-related edge cases."""

    def test_concurrent_config_modifications(self, temp_dir: Path):
        """Test concurrent modifications to configuration."""
        config_path = temp_dir / "concurrent_config.yaml"
        Config.create_default(config_path)

        results = []
        errors = []

        def modify_config(worker_id: int):
            """Modify configuration in a thread."""
            try:
                # Load fresh config instance
                config = Config.load(config_path)

                # Perform multiple operations
                for i in range(10):
                    key = f"worker_{worker_id}.operation_{i}"
                    value = f"value_{worker_id}_{i}"
                    config.set(key, value)

                    # Small delay to increase chance of race conditions
                    time.sleep(0.001)

                # Save configuration
                config.save()
                results.append(f"worker_{worker_id}_completed")

            except Exception as e:
                errors.append(f"worker_{worker_id}: {e}")

        # Start multiple worker threads
        threads = []
        num_workers = 10

        for worker_id in range(num_workers):
            thread = threading.Thread(target=modify_config, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_workers, f"Not all workers completed: {results}"

        # Verify final config integrity
        final_config = Config.load(config_path)
        config_dict = final_config.to_dict()

        # Should be valid YAML/dict
        assert isinstance(config_dict, dict)

    def test_concurrent_task_creation(self, temp_project: Project):
        """Test concurrent task creation."""
        task_manager = TaskManager(temp_project)

        created_tasks = []
        creation_errors = []

        def create_tasks_batch(batch_id: int, count: int):
            """Create a batch of tasks."""
            try:
                batch_tasks = []
                for i in range(count):
                    task_data = {
                        "title": f"Concurrent Task {batch_id}-{i}",
                        "description": f"Task created by batch {batch_id}",
                        "priority": ["low", "medium", "high"][i % 3],
                        "assignees": [f"user_{batch_id}"],
                        "tags": [f"batch_{batch_id}", f"task_{i}"],
                    }

                    task = task_manager.create_task(task_data)
                    batch_tasks.append(task)

                    # Small delay to test race conditions
                    time.sleep(0.001)

                created_tasks.extend(batch_tasks)

            except Exception as e:
                creation_errors.append(f"batch_{batch_id}: {e}")

        # Create multiple batches concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for batch_id in range(5):
                future = executor.submit(create_tasks_batch, batch_id, 10)
                futures.append(future)

            # Wait for all batches
            for future in futures:
                future.result(timeout=30)

        # Verify results
        assert len(creation_errors) == 0, f"Creation errors: {creation_errors}"
        assert len(created_tasks) == 50, f"Expected 50 tasks, got {len(created_tasks)}"

        # Verify all tasks have unique IDs
        task_ids = [task.id for task in created_tasks]
        assert len(set(task_ids)) == len(task_ids), "Duplicate task IDs found"

    def test_concurrent_file_parsing(self, temp_dir: Path):
        """Test concurrent file parsing."""
        # Create multiple test files
        test_files = []
        for i in range(20):
            test_file = temp_dir / f"test_file_{i}.md"
            test_file.write_text(
                f"""---
id: TSK-{i:04d}
title: Concurrent Test File {i}
status: open
priority: medium
---

Content for file {i}.
"""
            )
            test_files.append(test_file)

        parser = FrontmatterParser()
        parsed_results = []
        parsing_errors = []

        def parse_file_batch(file_batch):
            """Parse a batch of files."""
            try:
                batch_results = []
                for file_path in file_batch:
                    frontmatter, content, result = parser.parse_file(file_path)
                    if result.valid:
                        batch_results.append(
                            {
                                "file": file_path.name,
                                "id": frontmatter.get("id"),
                                "title": frontmatter.get("title"),
                            }
                        )

                parsed_results.extend(batch_results)

            except Exception as e:
                parsing_errors.append(str(e))

        # Split files into batches
        batch_size = 5
        file_batches = [
            test_files[i : i + batch_size]
            for i in range(0, len(test_files), batch_size)
        ]

        # Parse batches concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(parse_file_batch, batch) for batch in file_batches
            ]

            for future in futures:
                future.result(timeout=30)

        # Verify results
        assert len(parsing_errors) == 0, f"Parsing errors: {parsing_errors}"
        assert (
            len(parsed_results) == 20
        ), f"Expected 20 results, got {len(parsed_results)}"

    def test_deadlock_prevention(self, temp_dir: Path):
        """Test prevention of deadlocks in resource access."""
        config_path1 = temp_dir / "config1.yaml"
        config_path2 = temp_dir / "config2.yaml"

        Config.create_default(config_path1)
        Config.create_default(config_path2)

        deadlock_detected = False

        def worker_a():
            """Worker that accesses resources in order A -> B."""
            try:
                config1 = Config.load(config_path1)
                time.sleep(0.1)  # Hold resource A
                config2 = Config.load(config_path2)

                config1.set("worker", "A")
                config2.set("worker", "A")
                config1.save()
                config2.save()

            except Exception:
                nonlocal deadlock_detected
                deadlock_detected = True

        def worker_b():
            """Worker that accesses resources in order B -> A."""
            try:
                config2 = Config.load(config_path2)
                time.sleep(0.1)  # Hold resource B
                config1 = Config.load(config_path1)

                config2.set("worker", "B")
                config1.set("worker", "B")
                config2.save()
                config1.save()

            except Exception:
                nonlocal deadlock_detected
                deadlock_detected = True

        # Start workers that could deadlock
        thread_a = threading.Thread(target=worker_a)
        thread_b = threading.Thread(target=worker_b)

        start_time = time.time()
        thread_a.start()
        thread_b.start()

        # Wait with timeout to detect deadlock
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)

        elapsed_time = time.time() - start_time

        # Should complete within reasonable time
        assert elapsed_time < 10, "Possible deadlock detected"
        assert not deadlock_detected, "Deadlock was detected"

    def test_race_condition_in_file_creation(self, temp_dir: Path):
        """Test race conditions in file creation."""
        creation_results = []
        creation_errors = []

        def create_file_worker(worker_id: int):
            """Worker that creates files with potential name conflicts."""
            try:
                for i in range(10):
                    # Potential race condition: multiple workers creating files with similar names
                    file_path = temp_dir / f"worker_{worker_id}_file_{i}.md"

                    # Check if file exists (race condition window)
                    if not file_path.exists():
                        time.sleep(0.001)  # Increase race condition window

                        # Create file (another race condition window)
                        file_path.write_text(
                            f"""---
id: WRK-{worker_id:02d}-{i:02d}
title: Worker {worker_id} File {i}
creator: worker_{worker_id}
---

Content created by worker {worker_id}.
"""
                        )
                        creation_results.append(f"worker_{worker_id}_file_{i}")

            except Exception as e:
                creation_errors.append(f"worker_{worker_id}: {e}")

        # Start multiple workers
        threads = []
        for worker_id in range(8):
            thread = threading.Thread(target=create_file_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)

        # Verify results
        assert len(creation_errors) == 0, f"Creation errors: {creation_errors}"

        # Check that files were created successfully
        created_files = list(temp_dir.glob("worker_*_file_*.md"))
        assert len(created_files) > 0, "No files were created"


class TestResourceExhaustionScenarios:
    """Test resource exhaustion scenarios."""

    def test_memory_exhaustion_handling(self):
        """Test handling of memory exhaustion scenarios."""
        initial_memory = self._get_memory_usage()

        # Create large data structures
        large_datasets = []
        validator = SchemaValidator()

        try:
            for i in range(10):  # Create multiple large datasets
                large_task_data = {
                    "id": f"TSK-{i:04d}",
                    "title": f"Large Task {i}",
                    "description": "x" * 100000,  # 100KB description
                    "assignees": [f"user_{j}" for j in range(1000)],  # 1000 assignees
                    "tags": [f"tag_{j}" for j in range(500)],  # 500 tags
                    "metadata": {
                        f"key_{j}": f"value_{j}" for j in range(1000)
                    },  # Large metadata
                    "priority": "medium",
                    "status": "open",
                }

                # Validate large dataset
                result = validator.validate_task(large_task_data)
                large_datasets.append(large_task_data)

                # Check memory usage periodically
                current_memory = self._get_memory_usage()
                memory_increase = current_memory - initial_memory

                # If memory usage is too high, break to prevent system issues
                if memory_increase > 500 * 1024 * 1024:  # 500MB limit
                    break

        finally:
            # Cleanup
            large_datasets.clear()
            gc.collect()  # Force garbage collection

        final_memory = self._get_memory_usage()
        memory_leaked = final_memory - initial_memory

        # Should not leak excessive memory
        assert (
            memory_leaked < 100 * 1024 * 1024
        ), f"Memory leak detected: {memory_leaked} bytes"

    def test_file_descriptor_exhaustion(self, temp_dir: Path):
        """Test handling of file descriptor exhaustion."""
        open_files = []

        try:
            # Try to open many files to test descriptor limits
            for i in range(500):  # Reasonable number for testing
                file_path = temp_dir / f"fd_test_{i}.txt"
                file_path.write_text(f"Content {i}")

                try:
                    file_handle = open(file_path)
                    open_files.append(file_handle)
                except OSError as e:
                    if "Too many open files" in str(e):
                        # Hit the limit, this is expected
                        break
                    else:
                        raise

        finally:
            # Cleanup file descriptors
            for file_handle in open_files:
                try:
                    file_handle.close()
                except Exception:
                    pass

        # Should handle file descriptor limits gracefully
        assert len(open_files) > 10, "Should be able to open at least 10 files"

    def test_disk_space_exhaustion_simulation(self, temp_dir: Path):
        """Test handling of disk space exhaustion."""
        # Simulate disk full condition
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            config_path = temp_dir / "config.yaml"

            # Should handle disk full gracefully
            with pytest.raises(OSError):
                Config.create_default(config_path)

    def test_cpu_intensive_operations(self):
        """Test CPU intensive operations under load."""
        validator = SchemaValidator()

        def cpu_intensive_validation():
            """Perform CPU intensive validation."""
            results = []
            for i in range(100):
                task_data = {
                    "id": f"TSK-{i:04d}",
                    "title": f"CPU Test Task {i}",
                    "description": "Complex validation task",
                    "priority": "medium",
                    "status": "open",
                    "dependencies": [
                        f"TSK-{j:04d}" for j in range(i)
                    ],  # Growing dependencies
                    "metadata": {
                        f"key_{j}": f"value_{j}" for j in range(100)
                    },  # Complex metadata
                }

                result = validator.validate_task(task_data)
                results.append(result)

            return results

        # Run CPU intensive operations concurrently
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(cpu_intensive_validation) for _ in range(4)]

            results = []
            for future in futures:
                batch_result = future.result(timeout=60)
                results.extend(batch_result)

        elapsed_time = time.time() - start_time

        # Should complete within reasonable time even under load
        assert (
            elapsed_time < 120
        ), f"CPU intensive operations took too long: {elapsed_time}s"
        assert len(results) == 400, f"Expected 400 results, got {len(results)}"

    @pytest.mark.slow
    def test_large_file_handling(self, temp_dir: Path):
        """Test handling of large files."""
        large_file = temp_dir / "large_file.md"

        # Create large file (10MB)
        large_content = "---\ntitle: Large File Test\n---\n\n"
        large_content += "This is a large file content line.\n" * 500000

        with open(large_file, "w") as f:
            f.write(large_content)

        # Test parsing large file
        parser = FrontmatterParser()
        start_time = time.time()

        frontmatter, content, result = parser.parse_file(large_file)

        parse_time = time.time() - start_time

        # Should parse successfully within reasonable time
        assert result.valid, "Large file parsing failed"
        assert parse_time < 30, f"Large file parsing took too long: {parse_time}s"
        assert frontmatter["title"] == "Large File Test"

    def test_network_timeout_simulation(self):
        """Test handling of network timeouts in Git operations."""
        from ai_trackdown_pytools.utils.git import GitUtils

        # Simulate network timeout
        with patch("git.Repo", side_effect=TimeoutError("Network timeout")):
            git_utils = GitUtils()

            # Should handle timeouts gracefully
            assert not git_utils.is_git_repo()
            assert git_utils.get_status() == {}

    def _get_memory_usage(self) -> int:
        """Get current memory usage in bytes."""
        try:
            process = psutil.Process()
            return process.memory_info().rss
        except (ImportError, psutil.NoSuchProcess):
            return 0


class TestStressConditions:
    """Test system behavior under stress conditions."""

    @pytest.mark.slow
    def test_rapid_file_operations(self, temp_dir: Path):
        """Test rapid file creation, modification, and deletion."""
        operation_count = 0
        errors = []

        def rapid_operations(worker_id: int):
            """Perform rapid file operations."""
            nonlocal operation_count
            try:
                for i in range(100):
                    file_path = temp_dir / f"rapid_{worker_id}_{i}.md"

                    # Create
                    file_path.write_text(
                        f"---\ntitle: Rapid {worker_id}-{i}\n---\nContent"
                    )
                    operation_count += 1

                    # Modify
                    file_path.write_text(
                        f"---\ntitle: Modified {worker_id}-{i}\n---\nModified"
                    )
                    operation_count += 1

                    # Delete
                    file_path.unlink()
                    operation_count += 1

                    # No delay - maximum stress

            except Exception as e:
                errors.append(f"worker_{worker_id}: {e}")

        # Start multiple workers for maximum stress
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(rapid_operations, i) for i in range(8)]

            for future in futures:
                future.result(timeout=60)

        # Verify stress test results
        assert len(errors) == 0, f"Errors during stress test: {errors}"
        assert (
            operation_count > 1000
        ), f"Expected >1000 operations, got {operation_count}"

    def test_validation_under_stress(self):
        """Test validation system under stress conditions."""
        validator = SchemaValidator()
        validation_count = 0
        validation_errors = []

        def stress_validation(batch_id: int):
            """Perform stress validation."""
            nonlocal validation_count
            try:
                for i in range(50):
                    # Create complex task data
                    task_data = {
                        "id": f"STR-{batch_id:02d}-{i:03d}",
                        "title": f"Stress Test Task {batch_id}-{i}",
                        "description": f"Complex task for stress testing batch {batch_id}",
                        "priority": ["low", "medium", "high", "critical"][i % 4],
                        "status": ["open", "in_progress", "completed"][i % 3],
                        "assignees": [f"user_{j}" for j in range(i % 10 + 1)],
                        "tags": [f"tag_{j}" for j in range(i % 5 + 1)],
                        "dependencies": [
                            f"STR-{batch_id:02d}-{j:03d}" for j in range(min(i, 5))
                        ],
                        "metadata": {f"key_{j}": f"value_{j}" for j in range(i % 20)},
                    }

                    result = validator.validate_task(task_data)
                    validation_count += 1

                    # Validate rapidly without delays

            except Exception as e:
                validation_errors.append(f"batch_{batch_id}: {e}")

        # Run stress validation
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(stress_validation, i) for i in range(10)]

            for future in futures:
                future.result(timeout=120)

        elapsed_time = time.time() - start_time

        # Verify stress test results
        assert len(validation_errors) == 0, f"Validation errors: {validation_errors}"
        assert (
            validation_count == 500
        ), f"Expected 500 validations, got {validation_count}"
        assert elapsed_time < 60, f"Stress validation took too long: {elapsed_time}s"

    def test_template_processing_under_load(self, temp_dir: Path):
        """Test template processing under heavy load."""
        # Create test templates
        template_dir = temp_dir / "templates" / "task"
        template_dir.mkdir(parents=True)

        template_file = template_dir / "stress.yaml"
        template_file.write_text(
            """
name: Stress Template
description: Template for stress testing
type: task
content: |
  # {{ title }}
  
  **Priority**: {{ priority }}
  **Assignee**: {{ assignee }}
  
  ## Description
  {{ description }}
  
  ## Generated Data
  {% for i in range(100) %}
  - Item {{ i }}: {{ title }}-{{ i }}
  {% endfor %}
"""
        )

        template_manager = TemplateManager()
        with patch.object(template_manager, "_template_dirs", [temp_dir / "templates"]):
            processing_count = 0
            processing_errors = []

            def process_templates(batch_id: int):
                """Process templates under load."""
                nonlocal processing_count
                try:
                    for i in range(20):
                        variables = {
                            "title": f"Stress Task {batch_id}-{i}",
                            "priority": ["low", "medium", "high"][i % 3],
                            "assignee": f"user_{batch_id}",
                            "description": f"Template processing stress test {batch_id}-{i}",
                        }

                        # Apply template
                        success = template_manager.apply_template(
                            "task",
                            "stress",
                            temp_dir,
                            variables,
                            temp_dir / f"output_{batch_id}_{i}.md",
                        )

                        if success:
                            processing_count += 1

                except Exception as e:
                    processing_errors.append(f"batch_{batch_id}: {e}")

            # Process templates under load
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(process_templates, i) for i in range(5)]

                for future in futures:
                    future.result(timeout=60)

            # Verify template processing results
            assert (
                len(processing_errors) == 0
            ), f"Processing errors: {processing_errors}"
            assert processing_count > 0, "No templates were processed successfully"


class TestAsyncOperations:
    """Test asynchronous operations and event handling."""

    @pytest.mark.asyncio
    async def test_async_file_operations(self, temp_dir: Path):
        """Test asynchronous file operations."""

        async def async_file_worker(worker_id: int):
            """Async worker for file operations."""
            results = []
            for i in range(10):
                file_path = temp_dir / f"async_{worker_id}_{i}.md"

                # Simulate async file operation
                await asyncio.sleep(0.01)

                file_path.write_text(
                    f"""---
id: ASYNC-{worker_id:02d}-{i:02d}
title: Async Task {worker_id}-{i}
worker: {worker_id}
---

Async content {worker_id}-{i}.
"""
                )
                results.append(file_path.name)

            return results

        # Run async workers
        tasks = [async_file_worker(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify async results
        all_files = [file for worker_result in results for file in worker_result]
        assert len(all_files) == 50, f"Expected 50 files, got {len(all_files)}"

        # Verify files exist
        for worker_result in results:
            for file_name in worker_result:
                file_path = temp_dir / file_name
                assert file_path.exists(), f"Async file {file_name} not found"

    @pytest.mark.asyncio
    async def test_async_validation_pipeline(self):
        """Test asynchronous validation pipeline."""
        validator = SchemaValidator()

        async def async_validate_batch(batch_data):
            """Async validation batch."""
            results = []
            for task_data in batch_data:
                # Simulate async validation
                await asyncio.sleep(0.001)

                result = validator.validate_task(task_data)
                results.append(result)

            return results

        # Create test batches
        batches = []
        for batch_id in range(5):
            batch = []
            for i in range(10):
                task_data = {
                    "id": f"ASYNC-{batch_id:02d}-{i:02d}",
                    "title": f"Async Validation Task {batch_id}-{i}",
                    "priority": "medium",
                    "status": "open",
                }
                batch.append(task_data)
            batches.append(batch)

        # Run async validation
        validation_tasks = [async_validate_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*validation_tasks)

        # Verify async validation results
        total_validations = sum(len(batch_result) for batch_result in batch_results)
        assert (
            total_validations == 50
        ), f"Expected 50 validations, got {total_validations}"

        # Check that all validations were successful
        all_valid = all(
            result["valid"] for batch_result in batch_results for result in batch_result
        )
        assert all_valid, "Some async validations failed"


# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor performance during tests."""

    def __init__(self):
        self.start_time = None
        self.start_memory = None
        self.start_cpu = None

    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        try:
            process = psutil.Process()
            self.start_memory = process.memory_info().rss
            self.start_cpu = process.cpu_percent()
        except (ImportError, psutil.NoSuchProcess):
            self.start_memory = 0
            self.start_cpu = 0

    def stop(self):
        """Stop monitoring and return metrics."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0

        try:
            process = psutil.Process()
            memory_used = process.memory_info().rss - self.start_memory
            cpu_used = process.cpu_percent() - self.start_cpu
        except (ImportError, psutil.NoSuchProcess):
            memory_used = 0
            cpu_used = 0

        return {
            "elapsed_time": elapsed_time,
            "memory_used": memory_used,
            "cpu_used": cpu_used,
        }


# Test configuration for performance tests
pytest.mark.performance = pytest.mark.skipif(
    os.environ.get("SKIP_PERFORMANCE_TESTS") == "1", reason="Performance tests skipped"
)

pytest.mark.stress = pytest.mark.skipif(
    os.environ.get("SKIP_STRESS_TESTS") == "1", reason="Stress tests skipped"
)
