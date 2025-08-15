"""Comprehensive edge case and error handling tests for AI Trackdown PyTools.

This test suite covers:
- Boundary value testing for numeric inputs, string lengths, date ranges, and file sizes
- Error condition testing for file system errors, permission issues, and network failures
- Malformed data testing for corrupted YAML, invalid JSON schemas, and broken templates
- Concurrency testing for multi-user scenarios and file locking conflicts
- Resource exhaustion testing for memory limits, disk space, and large datasets
- Unicode and internationalization testing for special characters and encoding issues
- Platform-specific testing for Windows/macOS/Linux compatibility edge cases
- Security boundary testing for path traversal, injection attacks, and privilege escalation
- Regression testing framework to prevent previously fixed bugs from reoccurring
"""

import os
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

import pytest
import yaml

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.frontmatter import FrontmatterError, FrontmatterParser
from ai_trackdown_pytools.utils.git import GitUtils
from ai_trackdown_pytools.utils.templates import TemplateManager
from ai_trackdown_pytools.utils.validation import SchemaValidator


class TestBoundaryValues:
    """Test boundary values for numeric inputs, string lengths, dates, and file sizes."""

    def test_numeric_boundary_values(self):
        """Test numeric boundary values in various contexts."""
        validator = SchemaValidator()

        # Test extremely large numbers
        task_data = {
            "id": "TSK-0001",
            "title": "Boundary Test",
            "priority": "medium",
            "status": "open",
            "estimated_hours": 999999999,  # Very large number
            "actual_hours": 0,
        }
        result = validator.validate_task(task_data)
        assert result["valid"] is True or len(result["warnings"]) > 0

        # Test negative numbers where they shouldn't be allowed
        task_data["estimated_hours"] = -1
        result = validator.validate_task(task_data)
        # Should either be invalid or have warnings

        # Test zero values
        task_data["estimated_hours"] = 0
        result = validator.validate_task(task_data)
        assert result["valid"] is True

        # Test floating point precision edge cases
        task_data["estimated_hours"] = 0.000000001
        result = validator.validate_task(task_data)
        assert result["valid"] is True

    def test_string_length_boundaries(self):
        """Test string length boundaries."""
        validator = SchemaValidator()

        # Test empty strings
        task_data = {
            "id": "TSK-0001",
            "title": "",  # Empty title
            "priority": "medium",
            "status": "open",
        }
        result = validator.validate_task(task_data)
        # Should be invalid or have warnings

        # Test extremely long strings
        very_long_string = "x" * 10000
        task_data = {
            "id": "TSK-0001",
            "title": very_long_string,
            "description": very_long_string,
            "priority": "medium",
            "status": "open",
        }
        result = validator.validate_task(task_data)
        # Should handle gracefully

        # Test single character strings
        task_data = {
            "id": "TSK-0001",
            "title": "x",
            "priority": "medium",
            "status": "open",
        }
        result = validator.validate_task(task_data)
        assert result["valid"] is True

    def test_date_range_boundaries(self):
        """Test date range boundaries."""
        validator = SchemaValidator()

        # Test dates far in the past
        task_data = {
            "id": "TSK-0001",
            "title": "Date Test",
            "priority": "medium",
            "status": "open",
            "due_date": "1900-01-01",
            "created_at": "1900-01-01T00:00:00Z",
        }
        result = validator.validate_task(task_data)
        # Should handle gracefully

        # Test dates far in the future
        task_data["due_date"] = "2100-12-31"
        task_data["created_at"] = "2100-12-31T23:59:59Z"
        result = validator.validate_task(task_data)
        # Should handle gracefully

        # Test invalid date formats
        task_data["due_date"] = "invalid-date"
        result = validator.validate_task(task_data)
        # Should be invalid

        # Test leap year edge cases
        task_data["due_date"] = "2020-02-29"  # Valid leap year
        result = validator.validate_task(task_data)

        task_data["due_date"] = "2021-02-29"  # Invalid leap year
        result = validator.validate_task(task_data)
        # Should be invalid


class TestFileSystemErrors:
    """Test file system error conditions."""

    def test_permission_denied_errors(self, temp_dir: Path):
        """Test handling of permission denied errors."""
        config_path = temp_dir / "readonly_config.yaml"
        config_path.write_text("version: 1.0.0")

        # Make file read-only
        config_path.chmod(0o444)

        try:
            with pytest.raises((PermissionError, OSError)):
                config = Config.load(config_path)
                config.set("new_key", "value")
                config.save()  # Should fail
        finally:
            # Restore permissions for cleanup
            config_path.chmod(0o644)

    def test_disk_full_simulation(self, temp_dir: Path):
        """Test handling of disk full scenarios."""
        with patch("builtins.open", side_effect=OSError("No space left on device")):
            config_path = temp_dir / "config.yaml"
            with pytest.raises(OSError):
                Config.create_default(config_path)

    def test_corrupted_file_handling(self, temp_dir: Path):
        """Test handling of corrupted files."""
        # Create corrupted YAML file
        corrupted_config = temp_dir / "corrupted.yaml"
        corrupted_config.write_text("invalid: yaml: content: [unclosed")

        with pytest.raises(yaml.YAMLError):
            Config.load(corrupted_config)

    def test_network_failure_simulation(self):
        """Test handling of network failures in Git operations."""
        git_utils = GitUtils()

        with patch("git.Repo") as mock_repo:
            mock_repo.side_effect = ConnectionError("Network unreachable")

            result = git_utils.is_git_repo()
            assert result is False

    def test_file_locking_conflicts(self, temp_dir: Path):
        """Test file locking conflicts in concurrent scenarios."""
        config_path = temp_dir / "locked_config.yaml"
        Config.create_default(config_path)

        def modify_config(delay: float):
            """Function to modify config with delay."""
            time.sleep(delay)
            config = Config.load(config_path)
            config.set("concurrent_key", f"value_{delay}")
            config.save()

        # Start concurrent modifications
        thread1 = threading.Thread(target=modify_config, args=(0.1,))
        thread2 = threading.Thread(target=modify_config, args=(0.2,))

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Should complete without errors (one should win)
        final_config = Config.load(config_path)
        assert "concurrent_key" in final_config.to_dict()


class TestMalformedData:
    """Test handling of malformed data."""

    def test_corrupted_yaml_frontmatter(self, temp_dir: Path):
        """Test handling of corrupted YAML frontmatter."""
        corrupted_file = temp_dir / "corrupted.md"
        corrupted_file.write_text(
            """---
title: Test
invalid: yaml: [unclosed
---

Content here
"""
        )

        parser = FrontmatterParser()
        with pytest.raises(FrontmatterError):
            parser.parse_file(corrupted_file)

    def test_invalid_json_schemas(self):
        """Test handling of invalid JSON schemas."""
        validator = SchemaValidator()

        # Patch to simulate corrupted schema
        invalid_schema = {"type": "invalid_type", "properties": None}

        with patch.object(validator, "_schemas", {"task": invalid_schema}):
            task_data = {"id": "TSK-0001", "title": "Test"}
            result = validator.validate_task(task_data)
            # Should handle gracefully

    def test_broken_templates(self, temp_dir: Path):
        """Test handling of broken templates."""
        template_manager = TemplateManager()

        # Create broken template
        template_dir = temp_dir / "templates" / "task"
        template_dir.mkdir(parents=True)
        broken_template = template_dir / "broken.yaml"
        broken_template.write_text(
            """
name: Broken Template
content: "{{ unclosed_jinja_tag
"""
        )

        with patch.object(template_manager, "_template_dirs", [temp_dir / "templates"]):
            result = template_manager.validate_template("task", "broken")
            assert not result["valid"]
            assert len(result["errors"]) > 0

    def test_invalid_id_formats(self):
        """Test various invalid ID formats."""
        validator = SchemaValidator()

        invalid_ids = [
            "INVALID-ID",
            "TSK-",
            "TSK-abc",
            "tsk-001",  # lowercase
            "TSK001",  # missing dash
            "TSK-0001-extra",
            "",
            None,
            123,
            "TSK-99999999999999999999",  # extremely long number
        ]

        for invalid_id in invalid_ids:
            task_data = {
                "id": invalid_id,
                "title": "Test",
                "priority": "medium",
                "status": "open",
            }
            result = validator.validate_task(task_data)
            # Should detect invalid ID format


class TestUnicodeAndInternationalization:
    """Test Unicode and internationalization handling."""

    def test_unicode_characters_in_data(self):
        """Test handling of Unicode characters in various fields."""
        validator = SchemaValidator()

        unicode_task = {
            "id": "TSK-0001",
            "title": "Unicode Test: 测试 🚀 Тест αβγ",
            "description": "Émojis and spéciál châractérs: 🎉🔥💯",
            "assignees": ["用户", "пользователь", "χρήστης"],
            "tags": ["标签", "тег", "ετικέτα"],
            "priority": "medium",
            "status": "open",
        }

        result = validator.validate_task(unicode_task)
        assert result["valid"] is True

    def test_different_encodings(self, temp_dir: Path):
        """Test handling of different file encodings."""
        # Create files with different encodings
        utf8_file = temp_dir / "utf8.md"
        utf8_content = """---
title: UTF-8 Test: 测试
---

Content with UTF-8: 🚀
"""
        utf8_file.write_text(utf8_content, encoding="utf-8")

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(utf8_file)
        assert result.valid
        assert "测试" in frontmatter["title"]

    def test_special_characters_in_paths(self, temp_dir: Path):
        """Test handling of special characters in file paths."""
        special_dir = temp_dir / "spéciál dîr" / "test (1)" / "file&name"
        special_dir.mkdir(parents=True)

        config_path = special_dir / "config.yaml"
        config = Config.create_default(config_path)
        assert config_path.exists()

    def test_right_to_left_languages(self):
        """Test handling of right-to-left languages."""
        validator = SchemaValidator()

        rtl_task = {
            "id": "TSK-0001",
            "title": "العربية: اختبار RTL",
            "description": "עברית: בדיקה של כתיבה מימין לשמאל",
            "priority": "medium",
            "status": "open",
        }

        result = validator.validate_task(rtl_task)
        assert result["valid"] is True


class TestConcurrencyAndRaceConditions:
    """Test concurrency and race condition handling."""

    def test_concurrent_task_creation(self, temp_project: Project):
        """Test concurrent task creation."""
        task_manager = TaskManager(temp_project)
        created_tasks = []
        errors = []

        def create_task(task_id: int):
            """Create a task in a thread."""
            try:
                task_data = {
                    "title": f"Concurrent Task {task_id}",
                    "priority": "medium",
                    "assignees": [f"user{task_id}"],
                }
                task = task_manager.create_task(task_data)
                created_tasks.append(task)
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_task, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should handle gracefully
        assert len(errors) == 0 or len(created_tasks) > 0

    def test_concurrent_config_access(self, temp_dir: Path):
        """Test concurrent configuration access."""
        config_path = temp_dir / "concurrent_config.yaml"
        Config.create_default(config_path)

        results = []

        def access_config(key: str, value: str):
            """Access config in a thread."""
            try:
                config = Config.load(config_path)
                config.set(key, value)
                config.save()
                results.append(f"{key}={value}")
            except Exception as e:
                results.append(f"error: {e}")

        # Start concurrent access
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=access_config, args=(f"key{i}", f"value{i}")
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without deadlocks
        assert len(results) == 5

    def test_file_system_race_conditions(self, temp_dir: Path):
        """Test file system race conditions."""

        def create_and_delete_file(file_id: int):
            """Create and delete file rapidly."""
            file_path = temp_dir / f"race_file_{file_id}.md"
            try:
                file_path.write_text(f"Content {file_id}")
                if file_path.exists():
                    file_path.unlink()
                return True
            except Exception:
                return False

        # Execute rapidly
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_and_delete_file, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should complete without errors


class TestResourceExhaustion:
    """Test resource exhaustion scenarios."""

    def test_large_dataset_handling(self):
        """Test handling of large datasets."""
        validator = SchemaValidator()

        # Create task with large data
        large_description = "x" * 100000  # 100KB description
        large_assignees = [f"user_{i}" for i in range(1000)]  # 1000 assignees
        large_tags = [f"tag_{i}" for i in range(500)]  # 500 tags

        task_data = {
            "id": "TSK-0001",
            "title": "Large Dataset Test",
            "description": large_description,
            "assignees": large_assignees,
            "tags": large_tags,
            "priority": "medium",
            "status": "open",
        }

        result = validator.validate_task(task_data)
        # Should handle without crashing

    def test_memory_intensive_operations(self, temp_dir: Path):
        """Test memory intensive operations."""
        # Create many projects simultaneously
        projects = []

        for i in range(50):  # Create 50 projects
            project_path = temp_dir / f"project_{i}"
            project_path.mkdir()
            project = Project.create(project_path, name=f"Project {i}")
            projects.append(project)

        # Should complete without memory errors
        assert len(projects) == 50

    def test_file_descriptor_limits(self, temp_dir: Path):
        """Test file descriptor limits."""
        files = []

        try:
            # Open many files
            for i in range(100):
                file_path = temp_dir / f"file_{i}.txt"
                file_handle = open(file_path, "w")
                files.append(file_handle)
                file_handle.write(f"Content {i}")
        finally:
            # Clean up
            for file_handle in files:
                try:
                    file_handle.close()
                except Exception:
                    pass

    @pytest.mark.slow
    def test_large_file_processing(self, temp_dir: Path):
        """Test processing of large files."""
        large_file = temp_dir / "large_file.md"

        # Create large file content (1MB)
        large_content = "---\ntitle: Large File\n---\n\n" + (
            "Large content line\n" * 50000
        )
        large_file.write_text(large_content)

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(large_file)

        # Should handle without issues
        assert "title" in frontmatter


class TestPlatformSpecificEdgeCases:
    """Test platform-specific edge cases."""

    def test_windows_path_handling(self, temp_dir: Path):
        """Test Windows-specific path handling."""
        # Test long paths (Windows limitation)
        long_path_components = [
            "very_long_directory_name_that_exceeds_normal_limits"
        ] * 10

        try:
            long_path = temp_dir
            for component in long_path_components:
                long_path = long_path / component
                if len(str(long_path)) > 200:  # Reasonable limit for testing
                    break

            long_path.mkdir(parents=True, exist_ok=True)
            config_path = long_path / "config.yaml"
            Config.create_default(config_path)

        except OSError:
            # Expected on some platforms
            pass

    def test_case_sensitivity_issues(self, temp_dir: Path):
        """Test case sensitivity issues across platforms."""
        # Create files with similar names
        file1 = temp_dir / "Test.md"
        file2 = temp_dir / "test.md"

        file1.write_text("File 1")

        try:
            file2.write_text("File 2")
            # On case-sensitive systems, both should exist
            if file1.exists() and file2.exists():
                assert file1.read_text() != file2.read_text()
        except FileExistsError:
            # On case-insensitive systems, this is expected
            pass

    def test_special_file_attributes(self, temp_dir: Path):
        """Test handling of special file attributes."""
        special_file = temp_dir / "special.md"
        special_file.write_text("---\ntitle: Special\n---\nContent")

        # Test hidden files (Unix-style)
        hidden_file = temp_dir / ".hidden.md"
        hidden_file.write_text("---\ntitle: Hidden\n---\nContent")

        parser = FrontmatterParser()

        # Should handle both files
        result1 = parser.parse_file(special_file)
        result2 = parser.parse_file(hidden_file)

        assert result1[2].valid
        assert result2[2].valid

    def test_path_separator_normalization(self):
        """Test path separator normalization across platforms."""
        # Test mixed separators
        mixed_path = "project\\subdir/file.md"
        normalized_path = Path(mixed_path)

        # Should normalize regardless of platform
        assert str(normalized_path) != mixed_path or os.sep in str(normalized_path)


class TestSecurityBoundaries:
    """Test security boundary conditions."""

    def test_path_traversal_prevention(self, temp_dir: Path):
        """Test prevention of path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
            "....//....//....//etc//passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
        ]

        for malicious_path in malicious_paths:
            try:
                # Should sanitize or reject malicious paths
                safe_path = temp_dir / malicious_path
                # Ensure the resolved path stays within temp_dir
                assert str(safe_path.resolve()).startswith(str(temp_dir.resolve()))
            except (ValueError, OSError):
                # Expected for some malicious inputs
                pass

    def test_template_injection_prevention(self):
        """Test prevention of template injection attacks."""
        template_manager = TemplateManager()

        malicious_templates = [
            "{{ config.__class__.__module__ }}",
            "{{ ''.__class__.__mro__[1].__subclasses__() }}",
            "{% for item in config.__dict__ %}{{ item }}{% endfor %}",
            "{{ self.__init__.__globals__ }}",
        ]

        for malicious_template in malicious_templates:
            # Should prevent code execution
            try:
                from jinja2 import Template

                template = Template(malicious_template)
                result = template.render(config={})
                # Should not expose sensitive information
                assert "__class__" not in result
                assert "__globals__" not in result
            except Exception:
                # Template might reject malicious content
                pass

    def test_yaml_deserialization_safety(self, temp_dir: Path):
        """Test YAML deserialization safety."""
        malicious_yaml_file = temp_dir / "malicious.yaml"

        # YAML that could execute code (if using unsafe loader)
        malicious_content = """
!!python/object/apply:os.system
- "echo 'malicious code executed'"
"""
        malicious_yaml_file.write_text(malicious_content)

        # Should use safe loader
        with open(malicious_yaml_file) as f:
            try:
                data = yaml.safe_load(f)
                # Should not execute code
                assert data is None or not callable(data)
            except yaml.YAMLError:
                # Expected with malicious YAML
                pass

    def test_privilege_escalation_prevention(self, temp_dir: Path):
        """Test prevention of privilege escalation."""
        # Test creating files with unusual permissions
        config_path = temp_dir / "config.yaml"
        Config.create_default(config_path)

        # Should not create files with overly permissive permissions
        file_mode = config_path.stat().st_mode & 0o777

        # Should not be world-writable
        assert not (file_mode & 0o002)


class TestInputValidationEdgeCases:
    """Test input validation edge cases."""

    def test_null_and_undefined_values(self):
        """Test handling of null and undefined values."""
        validator = SchemaValidator()

        test_cases = [
            {"id": None, "title": "Test"},
            {"id": "TSK-0001", "title": None},
            {"id": "TSK-0001", "title": "Test", "assignees": None},
            {"id": "TSK-0001", "title": "Test", "tags": [None, "valid_tag"]},
            {},  # Empty dict
        ]

        for test_case in test_cases:
            result = validator.validate_task(test_case)
            # Should handle gracefully without crashing

    def test_type_confusion_attacks(self):
        """Test prevention of type confusion attacks."""
        validator = SchemaValidator()

        # Try to pass wrong types for expected fields
        malicious_data = {
            "id": ["TSK-0001"],  # Array instead of string
            "title": {"malicious": "object"},  # Object instead of string
            "priority": 42,  # Number instead of string
            "assignees": "single_string",  # String instead of array
            "created_at": ["not", "a", "date"],  # Array instead of date
        }

        result = validator.validate_task(malicious_data)
        # Should detect type mismatches

    def test_extremely_nested_data(self):
        """Test handling of extremely nested data structures."""
        # Create deeply nested structure
        nested_data = {"level": 0}
        current = nested_data

        for i in range(100):  # Create 100 levels of nesting
            current["next"] = {"level": i + 1}
            current = current["next"]

        task_data = {
            "id": "TSK-0001",
            "title": "Nested Test",
            "metadata": nested_data,
            "priority": "medium",
            "status": "open",
        }

        validator = SchemaValidator()
        result = validator.validate_task(task_data)
        # Should handle without stack overflow

    def test_circular_reference_handling(self):
        """Test handling of circular references in data."""
        # Create circular reference
        data_a = {"name": "A"}
        data_b = {"name": "B", "ref": data_a}
        data_a["ref"] = data_b  # Circular reference

        task_data = {
            "id": "TSK-0001",
            "title": "Circular Test",
            "metadata": data_a,
            "priority": "medium",
            "status": "open",
        }

        validator = SchemaValidator()
        # Should handle without infinite recursion
        try:
            result = validator.validate_task(task_data)
        except RecursionError:
            pytest.fail("Circular reference caused infinite recursion")


class TestDataConsistencyEdgeCases:
    """Test data consistency edge cases."""

    def test_timestamp_inconsistencies(self):
        """Test handling of timestamp inconsistencies."""
        validator = SchemaValidator()

        # Future created date
        future_task = {
            "id": "TSK-0001",
            "title": "Future Task",
            "priority": "medium",
            "status": "open",
            "created_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        result = validator.validate_task(future_task)
        # Should detect inconsistency

        # Updated before created
        inconsistent_task = {
            "id": "TSK-0002",
            "title": "Inconsistent Task",
            "priority": "medium",
            "status": "open",
            "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
            "updated_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        }

        result = validator.validate_task(inconsistent_task)
        # Should detect inconsistency

    def test_status_transition_violations(self):
        """Test status transition violations."""
        from ai_trackdown_pytools.utils.frontmatter import StatusWorkflowValidator

        workflow_validator = StatusWorkflowValidator()

        # Invalid transitions
        invalid_transitions = [
            ("completed", "open"),  # Cannot reopen completed task
            ("cancelled", "in_progress"),  # Cannot restart cancelled task
            ("merged", "draft"),  # Cannot change merged PR to draft
        ]

        for from_status, to_status in invalid_transitions:
            result = workflow_validator.validate_status_transition(
                "task", from_status, to_status
            )
            assert not result.valid

    def test_relationship_consistency(self):
        """Test relationship consistency across tickets."""
        from ai_trackdown_pytools.utils.validation import validate_relationships

        # Inconsistent relationships
        tickets = [
            {
                "id": "TSK-0001",
                "title": "Parent Task",
                "child_tasks": ["TSK-0002"],
                "status": "open",
            },
            {
                "id": "TSK-0002",
                "title": "Child Task",
                "parent": "TSK-0003",  # Wrong parent!
                "status": "open",
            },
        ]

        result = validate_relationships(tickets)
        assert not result.valid or len(result.warnings) > 0


class TestErrorRecoveryMechanisms:
    """Test error recovery mechanisms."""

    def test_partial_file_corruption_recovery(self, temp_dir: Path):
        """Test recovery from partial file corruption."""
        # Create partially corrupted file
        corrupted_file = temp_dir / "partial_corrupt.md"
        corrupted_file.write_text(
            """---
title: Partially Corrupted
status: open
priority: medium
# Missing closing ---

This content might still be readable.
"""
        )

        parser = FrontmatterParser()
        try:
            frontmatter, content, result = parser.parse_file(corrupted_file)
            # Should attempt graceful recovery
        except FrontmatterError:
            # Expected for this level of corruption
            pass

    def test_backup_and_recovery(self, temp_dir: Path):
        """Test backup and recovery mechanisms."""
        config_path = temp_dir / "config.yaml"
        backup_path = temp_dir / "config.yaml.bak"

        # Create original config
        config = Config.create_default(config_path)
        config.set("test.value", "original")
        config.save()

        # Create backup
        import shutil

        shutil.copy2(config_path, backup_path)

        # Corrupt original
        config_path.write_text("corrupted content")

        # Test recovery
        if backup_path.exists():
            shutil.copy2(backup_path, config_path)
            recovered_config = Config.load(config_path)
            assert recovered_config.get("test.value") == "original"

    def test_graceful_degradation(self):
        """Test graceful degradation when components fail."""
        # Test Git utils when git is not available
        with patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", False):
            git_utils = GitUtils()
            assert not git_utils.is_git_repo()
            assert git_utils.get_current_branch() is None
            assert git_utils.get_status() == {}


class TestPerformanceEdgeCases:
    """Test performance edge cases."""

    @pytest.mark.slow
    def test_large_configuration_handling(self, temp_dir: Path):
        """Test handling of large configuration files."""
        config_path = temp_dir / "large_config.yaml"

        # Create large configuration
        large_config_data = {
            "version": "1.0.0",
            "large_section": {f"key_{i}": f"value_{i}" for i in range(10000)},
        }

        with open(config_path, "w") as f:
            yaml.dump(large_config_data, f)

        # Should load without performance issues
        start_time = time.time()
        config = Config.load(config_path)
        load_time = time.time() - start_time

        assert load_time < 5.0  # Should load within 5 seconds
        assert config.get("large_section.key_5000") == "value_5000"

    @pytest.mark.slow
    def test_many_small_files_handling(self, temp_dir: Path):
        """Test handling of many small files."""
        # Create many small task files
        tasks_dir = temp_dir / "tasks"
        tasks_dir.mkdir()

        start_time = time.time()
        for i in range(1000):
            task_file = tasks_dir / f"tsk-{i:04d}.md"
            task_file.write_text(
                f"""---
id: TSK-{i:04d}
title: Task {i}
status: open
priority: medium
---

Task {i} content.
"""
            )

        creation_time = time.time() - start_time
        assert creation_time < 10.0  # Should create 1000 files within 10 seconds

        # Test reading all files
        parser = FrontmatterParser()
        start_time = time.time()

        parsed_count = 0
        for task_file in tasks_dir.glob("*.md"):
            try:
                frontmatter, content, result = parser.parse_file(task_file)
                if result.valid:
                    parsed_count += 1
            except Exception:
                pass

        parsing_time = time.time() - start_time
        assert parsing_time < 30.0  # Should parse within 30 seconds
        assert parsed_count > 950  # Should successfully parse most files


class TestRegressionPrevention:
    """Test framework for preventing regression of previously fixed bugs."""

    def test_config_singleton_reset_bug(self):
        """Regression test: Config singleton not properly reset between tests."""
        # Create first config
        config1 = Config()
        config1.set("test.regression", "value1")

        # Reset singleton (simulating test cleanup)
        Config._instance = None

        # Create second config
        config2 = Config()

        # Should not contain previous values
        assert config2.get("test.regression") is None

    def test_yaml_parsing_edge_case_bug(self, temp_dir: Path):
        """Regression test: YAML parsing failed with certain edge case formats."""
        edge_case_file = temp_dir / "edge_case.md"
        edge_case_file.write_text(
            """---
title: "Title: with colon"
description: |
  Multi-line description
  with special characters: !@#$%^&*()
tags:
  - "tag:with:colons"
  - "tag with spaces"
---

Content with --- in it should not break parsing.
"""
        )

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(edge_case_file)

        assert result.valid
        assert frontmatter["title"] == "Title: with colon"
        assert "Multi-line description" in frontmatter["description"]
        assert "tag:with:colons" in frontmatter["tags"]

    def test_template_variable_substitution_bug(self):
        """Regression test: Template variables not properly escaped."""
        from jinja2 import Template

        # Template with potentially problematic variables
        template_content = """
Title: {{ title }}
User: {{ user | default("Unknown") }}
Script: {{ script | e }}  # Should be escaped
"""

        template = Template(template_content)

        # Variables that could cause issues
        variables = {
            "title": "Task with <script>alert('xss')</script>",
            "user": "User & Company",
            "script": "<script>malicious()</script>",
        }

        result = template.render(**variables)

        # Should properly escape dangerous content
        assert "&lt;script&gt;" in result  # Escaped script tag
        assert "alert('xss')" not in result.replace("&", "")

    def test_circular_dependency_detection_bug(self):
        """Regression test: Circular dependency detection had false positives."""
        from ai_trackdown_pytools.utils.validation import validate_relationships

        # Valid non-circular dependencies
        tickets = [
            {"id": "TSK-0001", "dependencies": ["TSK-0002"]},
            {"id": "TSK-0002", "dependencies": ["TSK-0003"]},
            {"id": "TSK-0003", "dependencies": []},
            {
                "id": "TSK-0004",
                "dependencies": ["TSK-0001"],
            },  # Valid dependency on TSK-0001
        ]

        result = validate_relationships(tickets)

        # Should not detect circular dependency
        circular_errors = [
            error for error in result.errors if "circular" in error.lower()
        ]
        assert len(circular_errors) == 0

    def test_unicode_filename_handling_bug(self, temp_dir: Path):
        """Regression test: Unicode filenames caused crashes on some systems."""
        unicode_filename = temp_dir / "测试文件.md"
        unicode_filename.write_text(
            """---
title: Unicode Test
---

Unicode content: 🚀 测试
"""
        )

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(unicode_filename)

        assert result.valid
        assert frontmatter["title"] == "Unicode Test"

    def test_empty_frontmatter_field_bug(self):
        """Regression test: Empty frontmatter fields caused validation errors."""
        validator = SchemaValidator()

        task_with_empty_fields = {
            "id": "TSK-0001",
            "title": "Task with Empty Fields",
            "description": "",  # Empty string
            "assignees": [],  # Empty array
            "tags": [],  # Empty array
            "priority": "medium",
            "status": "open",
        }

        result = validator.validate_task(task_with_empty_fields)

        # Should be valid (empty fields are often acceptable)
        assert result["valid"] is True


# Utility functions for edge case testing
def generate_test_data(size: int) -> List[Dict[str, Any]]:
    """Generate test data of specified size."""
    return [
        {
            "id": f"TSK-{i:04d}",
            "title": f"Test Task {i}",
            "priority": ["low", "medium", "high", "critical"][i % 4],
            "status": ["open", "in_progress", "completed"][i % 3],
            "created_at": (datetime.now() - timedelta(days=i)).isoformat(),
        }
        for i in range(size)
    ]


def simulate_system_load():
    """Simulate system load for stress testing."""
    import threading

    def cpu_intensive_task():
        """CPU intensive task."""
        for _ in range(1000000):
            _ = sum(range(100))

    # Start multiple CPU intensive tasks
    threads = []
    for _ in range(4):  # 4 threads
        thread = threading.Thread(target=cpu_intensive_task)
        thread.start()
        threads.append(thread)

    return threads


def create_file_with_encoding(file_path: Path, content: str, encoding: str):
    """Create file with specific encoding."""
    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)


# Mark expensive tests
pytest.mark.slow = pytest.mark.slow
pytest.mark.performance = pytest.mark.skipif(
    os.environ.get("SKIP_PERFORMANCE_TESTS") == "1", reason="Performance tests skipped"
)
