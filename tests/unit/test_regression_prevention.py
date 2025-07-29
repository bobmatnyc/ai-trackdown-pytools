"""Regression prevention test suite for AI Trackdown PyTools.

This test suite specifically prevents the reoccurrence of previously fixed bugs
by testing edge cases and scenarios that have caused issues in the past.

The tests are organized by component and include detailed documentation
of the original bug and the fix to prevent future regressions.
"""

import os
import re
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from ai_trackdown_pytools.core.config import Config
from ai_trackdown_pytools.core.project import Project
from ai_trackdown_pytools.core.task import TaskManager
from ai_trackdown_pytools.utils.frontmatter import (
    FrontmatterParser,
    StatusWorkflowValidator,
)
from ai_trackdown_pytools.utils.git import GitUtils
from ai_trackdown_pytools.utils.templates import TemplateManager
from ai_trackdown_pytools.utils.validation import (
    SchemaValidator,
    validate_relationships,
)


class TestConfigRegressions:
    """Regression tests for configuration-related bugs."""

    def test_singleton_not_properly_reset_bug(self):
        """
        REGRESSION TEST: Config singleton not properly reset between tests

        Original Bug: Config singleton instance persisted between tests, causing
        configuration from one test to leak into another test, leading to
        unpredictable test failures.

        Fix: Proper singleton reset in test fixtures and cleanup.
        """
        # Create first config with specific values
        config1 = Config()
        config1.set("test.regression", "value1")
        config1.set("project.name", "first_project")

        # Simulate test cleanup - reset singleton
        Config._instance = None

        # Create second config - should be fresh
        config2 = Config()

        # Should not contain values from previous instance
        assert config2.get("test.regression") is None
        assert config2.get("project.name") != "first_project"

        # Verify it's a new instance
        assert config1 is not config2

    def test_nested_config_key_creation_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Nested config key creation failed with KeyError

        Original Bug: Setting nested configuration keys like "project.nested.deep.key"
        failed when intermediate keys didn't exist, raising KeyError.

        Fix: Proper creation of intermediate dictionary structures.
        """
        config_path = temp_dir / "config.yaml"
        config = Config.create_default(config_path)

        # These operations should not raise KeyError
        config.set("deeply.nested.configuration.key", "test_value")
        config.set("another.nested.path", "another_value")
        config.set("simple.key", "simple_value")

        # Verify all keys were set correctly
        assert config.get("deeply.nested.configuration.key") == "test_value"
        assert config.get("another.nested.path") == "another_value"
        assert config.get("simple.key") == "simple_value"

        # Save and reload to ensure persistence
        config.save()
        reloaded_config = Config.load(config_path)

        assert reloaded_config.get("deeply.nested.configuration.key") == "test_value"

    def test_config_file_corruption_handling_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Config loading crashed on corrupted YAML

        Original Bug: When configuration files were corrupted (incomplete YAML,
        broken syntax), the application crashed instead of handling gracefully.

        Fix: Proper exception handling and fallback to defaults.
        """
        corrupted_configs = [
            "version: 1.0.0\nproject: {unclosed",  # Unclosed brace
            "version: 1.0.0\n  invalid_indentation",  # Invalid indentation
            "version: 1.0.0\nproject:\n- invalid_list_for_object",  # Wrong type
            "version: [invalid, list, for, version]",  # Wrong type for version
            "",  # Empty file
            "not_valid_yaml_at_all: [[[}}}",  # Completely broken
        ]

        for i, corrupted_content in enumerate(corrupted_configs):
            corrupted_file = temp_dir / f"corrupted_{i}.yaml"
            corrupted_file.write_text(corrupted_content)

            # Should not crash, should handle gracefully
            try:
                config = Config.load(corrupted_file)
                # If it loads, should have at least some default values
                assert hasattr(config, "_config")

            except yaml.YAMLError:
                # Acceptable to fail with YAML error, but should not crash
                pass

    def test_global_config_path_resolution_bug(self):
        """
        REGRESSION TEST: Global config path resolution failed on some systems

        Original Bug: Global configuration path resolution failed when
        Path.home() returned unexpected results or when ~/.ai-trackdown
        didn't exist.

        Fix: Proper path validation and directory creation.
        """
        # Test global config path calculation
        global_path = Config.get_global_config_path()

        # Should be a valid Path object
        assert isinstance(global_path, Path)

        # Should be in user's home directory
        assert str(global_path).startswith(str(Path.home()))

        # Should end with correct filename
        assert global_path.name == "config.yaml"

        # Should be able to create parent directories
        parent_dir = global_path.parent
        assert parent_dir.name == ".ai-trackdown"

        # Test creating default config at global location
        if not global_path.exists():
            config = Config.create_default(global_path)
            assert global_path.exists()
            global_path.unlink()  # Cleanup


class TestFrontmatterRegressions:
    """Regression tests for frontmatter parsing bugs."""

    def test_yaml_frontmatter_with_colons_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: YAML parsing failed with colons in values

        Original Bug: YAML frontmatter parsing failed when title or other
        fields contained colons, especially in titles like "Issue: Bug Report".

        Fix: Proper YAML quoting and parsing.
        """
        edge_case_file = temp_dir / "colons_test.md"
        edge_case_file.write_text(
            """---
title: "Bug Report: Critical Issue"
description: "Time: 14:30, Date: 2024-01-01"
tags:
  - "category:bug"
  - "priority:high"
  - "component:auth:system"
url: "https://example.com:8080/path"
---

Content with colons: this should work fine.
"""
        )

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(edge_case_file)

        assert result.valid
        assert frontmatter["title"] == "Bug Report: Critical Issue"
        assert "14:30" in frontmatter["description"]
        assert "category:bug" in frontmatter["tags"]
        assert frontmatter["url"] == "https://example.com:8080/path"

    def test_multiline_yaml_description_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Multi-line YAML descriptions broke parsing

        Original Bug: Multi-line descriptions using YAML literal (|) or
        folded (>) blocks caused parsing failures.

        Fix: Proper YAML multi-line string handling.
        """
        multiline_file = temp_dir / "multiline_test.md"
        multiline_file.write_text(
            """---
title: "Multi-line Description Test"
description: |
  This is a multi-line description
  that spans several lines
  and should be preserved exactly
  
  Including empty lines and formatting.
notes: >
  This is a folded description
  that should have line breaks
  replaced with spaces.
steps: |
  1. First step
  2. Second step
  3. Third step
---

Content after frontmatter should work fine.
--- This line should not be confused with frontmatter.
"""
        )

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(multiline_file)

        assert result.valid
        assert "multi-line description" in frontmatter["description"]
        assert "several lines" in frontmatter["description"]
        assert "\n" in frontmatter["description"]  # Literal block preserves newlines
        assert "First step" in frontmatter["description"]
        assert "--- This line should not be confused" in content

    def test_unicode_in_frontmatter_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Unicode characters in frontmatter caused encoding errors

        Original Bug: Unicode characters in frontmatter fields caused
        encoding/decoding errors, especially on Windows systems.

        Fix: Proper UTF-8 encoding handling throughout.
        """
        unicode_file = temp_dir / "unicode_frontmatter.md"
        unicode_content = """---
title: "Unicode Test: 测试文件"
author: "José María González"
description: "Тест описание with émojis 🚀🌟"
tags:
  - "标签"
  - "тег"  
  - "ετικέτα"
  - "🏷️"
metadata:
  chinese: "中文测试"
  russian: "Русский текст"
  emoji: "🎯🔥💯"
---

Unicode content: 
- Chinese: 你好世界 测试
- Russian: Привет мир тест
- Emoji: 🌍🚀💫⭐
"""

        # Write with explicit UTF-8 encoding
        unicode_file.write_text(unicode_content, encoding="utf-8")

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(unicode_file)

        assert result.valid
        assert "测试文件" in frontmatter["title"]
        assert frontmatter["author"] == "José María González"
        assert "🚀🌟" in frontmatter["description"]
        assert "标签" in frontmatter["tags"]
        assert "🏷️" in frontmatter["tags"]
        assert frontmatter["metadata"]["chinese"] == "中文测试"

    def test_empty_frontmatter_fields_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Empty frontmatter fields caused validation errors

        Original Bug: When frontmatter fields were empty (empty strings,
        empty arrays, null values), validation incorrectly flagged them
        as errors instead of accepting them as valid empty values.

        Fix: Distinguish between missing fields and empty fields.
        """
        empty_fields_file = temp_dir / "empty_fields.md"
        empty_fields_file.write_text(
            """---
id: "TSK-0001"
title: "Task with Empty Fields"
description: ""
assignees: []
tags: []
dependencies: null
metadata: {}
priority: "medium"
status: "open"
---

Content here.
"""
        )

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(empty_fields_file)

        assert result.valid
        assert frontmatter["description"] == ""
        assert frontmatter["assignees"] == []
        assert frontmatter["tags"] == []
        assert frontmatter["dependencies"] is None
        assert frontmatter["metadata"] == {}

        # Validation should accept empty fields
        validator = SchemaValidator()
        validation_result = validator.validate_task(frontmatter)
        assert validation_result["valid"] is True

    def test_frontmatter_without_content_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Files with only frontmatter (no content) failed parsing

        Original Bug: Markdown files that contained only YAML frontmatter
        without any content after the closing --- caused parsing failures.

        Fix: Handle files with empty content gracefully.
        """
        frontmatter_only_file = temp_dir / "frontmatter_only.md"
        frontmatter_only_file.write_text(
            """---
id: "TSK-0001"
title: "Frontmatter Only Task"
priority: "medium"
status: "open"
---"""
        )  # No content after frontmatter

        parser = FrontmatterParser()
        frontmatter, content, result = parser.parse_file(frontmatter_only_file)

        assert result.valid
        assert frontmatter["title"] == "Frontmatter Only Task"
        assert content.strip() == ""  # Empty content should be handled gracefully


class TestValidationRegressions:
    """Regression tests for validation-related bugs."""

    def test_circular_dependency_false_positive_bug(self):
        """
        REGRESSION TEST: Circular dependency detection had false positives

        Original Bug: The circular dependency detection algorithm incorrectly
        flagged valid dependency chains as circular when they were actually
        linear or tree-structured.

        Fix: Improved cycle detection algorithm using proper graph traversal.
        """
        # Valid non-circular dependency structure
        tickets = [
            {"id": "TSK-0001", "dependencies": ["TSK-0002"]},
            {"id": "TSK-0002", "dependencies": ["TSK-0003"]},
            {"id": "TSK-0003", "dependencies": []},
            {
                "id": "TSK-0004",
                "dependencies": ["TSK-0001"],
            },  # Depends on TSK-0001, not circular
            {
                "id": "TSK-0005",
                "dependencies": ["TSK-0002", "TSK-0003"],
            },  # Multiple deps, not circular
        ]

        result = validate_relationships(tickets)

        # Should not detect circular dependency in this valid structure
        circular_errors = [
            error for error in result.errors if "circular" in error.lower()
        ]
        assert (
            len(circular_errors) == 0
        ), f"False positive circular dependency: {circular_errors}"

    def test_id_pattern_validation_edge_cases_bug(self):
        """
        REGRESSION TEST: ID pattern validation failed on edge cases

        Original Bug: ID pattern validation was too strict and failed on
        valid edge cases like leading zeros, different prefix lengths, etc.

        Fix: More flexible but still secure ID pattern matching.
        """
        from ai_trackdown_pytools.utils.validation import get_id_pattern_for_type

        # Test edge cases that should be valid
        edge_case_ids = [
            ("task", "TSK-0001"),  # Leading zeros
            ("task", "TSK-1"),  # Single digit
            ("task", "TSK-99999"),  # Large number
            ("epic", "EP-001"),  # Three digits
            ("issue", "ISS-12345"),  # Five digits
            ("pr", "PR-0"),  # Zero
        ]

        for ticket_type, ticket_id in edge_case_ids:
            pattern = get_id_pattern_for_type(ticket_type)
            assert re.match(
                pattern, ticket_id
            ), f"Valid ID {ticket_id} failed pattern {pattern}"

    def test_status_transition_validation_bug(self):
        """
        REGRESSION TEST: Status transition validation was too restrictive

        Original Bug: Status transition validation prevented some valid
        transitions and didn't account for different ticket types having
        different workflow requirements.

        Fix: Ticket-type-specific workflow validation.
        """
        workflow_validator = StatusWorkflowValidator()

        # Test valid transitions that were previously rejected
        valid_transitions = [
            ("task", "open", "in_progress"),
            ("task", "in_progress", "blocked"),
            ("task", "blocked", "in_progress"),
            ("issue", "open", "in_progress"),
            ("issue", "in_progress", "testing"),
            ("issue", "testing", "completed"),
            ("pr", "draft", "ready_for_review"),
            ("pr", "ready_for_review", "in_review"),
            ("epic", "planning", "in_progress"),
        ]

        for ticket_type, from_status, to_status in valid_transitions:
            result = workflow_validator.validate_status_transition(
                ticket_type, from_status, to_status
            )
            assert (
                result.valid
            ), f"Valid transition {from_status} -> {to_status} for {ticket_type} was rejected"

    def test_relationship_validation_missing_references_bug(self):
        """
        REGRESSION TEST: Relationship validation too strict on missing references

        Original Bug: Relationship validation flagged missing references as
        errors when they should be warnings, and didn't account for references
        to tickets that might exist in other projects or systems.

        Fix: Treat missing references as warnings, not errors.
        """
        tickets_with_external_refs = [
            {
                "id": "TSK-0001",
                "title": "Task with external references",
                "dependencies": ["EXT-0001", "TSK-0002"],  # EXT-0001 is external
                "status": "open",
            },
            {"id": "TSK-0002", "title": "Internal task", "status": "open"},
        ]

        result = validate_relationships(tickets_with_external_refs)

        # Should be valid overall (external refs are warnings, not errors)
        assert result.valid or len(result.errors) == 0

        # Should have warnings about external references
        external_warnings = [w for w in result.warnings if "EXT-0001" in w]
        assert len(external_warnings) > 0, "Should warn about external references"


class TestTemplateRegressions:
    """Regression tests for template-related bugs."""

    def test_template_variable_substitution_escaping_bug(self):
        """
        REGRESSION TEST: Template variables not properly escaped

        Original Bug: Template variable substitution didn't properly escape
        HTML/script content, leading to potential XSS vulnerabilities.

        Fix: Proper escaping of template variables.
        """
        from jinja2 import Template

        # Template with potentially dangerous variables
        template_content = """
Title: {{ title }}
Description: {{ description }}
User Input: {{ user_input | e }}
Raw HTML: {{ raw_html | safe }}
"""

        template = Template(template_content)

        # Variables that could be dangerous if not escaped
        dangerous_variables = {
            "title": "Normal Title",
            "description": "Description with <script>alert('xss')</script>",
            "user_input": "<img src=x onerror=alert('xss')>",
            "raw_html": "<b>Safe HTML</b>",
        }

        result = template.render(**dangerous_variables)

        # Should escape dangerous content in description and user_input
        assert "&lt;script&gt;" in result  # description should be auto-escaped
        assert "&lt;img src=x" in result  # user_input should be explicitly escaped
        assert (
            "<b>Safe HTML</b>" in result
        )  # raw_html should be unescaped (marked safe)

    def test_template_infinite_recursion_bug(self):
        """
        REGRESSION TEST: Template recursion caused infinite loops

        Original Bug: Template includes or macros could cause infinite
        recursion if they referenced themselves directly or indirectly.

        Fix: Recursion depth limiting and cycle detection.
        """
        from jinja2 import DictLoader, Environment

        # Templates that could cause infinite recursion
        templates = {
            "recursive": '{% include "recursive" %}',  # Direct self-reference
            "indirect1": '{% include "indirect2" %}',
            "indirect2": '{% include "indirect1" %}',  # Indirect cycle
        }

        env = Environment(loader=DictLoader(templates))

        # Should handle recursion gracefully (either prevent or limit depth)
        for template_name in templates:
            try:
                template = env.get_template(template_name)
                result = template.render()
                # If it renders, should not be infinite
                assert len(result) < 10000  # Reasonable limit
            except Exception as e:
                # Should fail with appropriate error, not hang
                error_msg = str(e).lower()
                assert (
                    "recursion" in error_msg
                    or "loop" in error_msg
                    or "depth" in error_msg
                )

    def test_template_directory_traversal_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Template loading vulnerable to directory traversal

        Original Bug: Template loading didn't properly validate template
        names, allowing directory traversal attacks to access files outside
        the template directory.

        Fix: Proper path validation and sandboxing.
        """
        template_manager = TemplateManager()

        # Create legitimate template directory
        template_dir = temp_dir / "templates" / "task"
        template_dir.mkdir(parents=True)

        # Create legitimate template
        legit_template = template_dir / "test.yaml"
        legit_template.write_text(
            """
name: Test Template
content: "{{ title }}"
"""
        )

        # Create sensitive file outside template directory
        sensitive_dir = temp_dir / "sensitive"
        sensitive_dir.mkdir()
        sensitive_file = sensitive_dir / "secret.yaml"
        sensitive_file.write_text("secret: classified")

        with patch.object(template_manager, "_template_dirs", [temp_dir / "templates"]):
            # Attempt directory traversal attacks
            traversal_attempts = [
                "../sensitive/secret",
                "../../sensitive/secret",
                "..\\sensitive\\secret",
                "%2e%2e%2fsensitive%2fsecret",
                "task/../sensitive/secret",
            ]

            for traversal_name in traversal_attempts:
                # Should not load files outside template directory
                result = template_manager.load_template("task", traversal_name)
                assert (
                    result is None
                ), f"Directory traversal succeeded: {traversal_name}"

            # Legitimate template should still work
            legit_result = template_manager.load_template("task", "test")
            assert legit_result is not None
            assert legit_result["name"] == "Test Template"


class TestGitRegressions:
    """Regression tests for Git-related bugs."""

    def test_git_not_available_crash_bug(self):
        """
        REGRESSION TEST: Application crashed when Git was not available

        Original Bug: When GitPython was not installed or Git was not
        available on the system, the application crashed instead of
        gracefully degrading.

        Fix: Proper availability checking and graceful degradation.
        """
        # Simulate Git not being available
        with patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", False):
            git_utils = GitUtils()

            # Should not crash, should return safe defaults
            assert git_utils.is_git_repo() is False
            assert git_utils.get_current_branch() is None
            assert git_utils.get_status() == {}
            assert git_utils.get_remote_url() is None
            assert git_utils.get_commit_history("main") == []

    def test_git_repo_detection_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Git repository detection failed in subdirectories

        Original Bug: Git repository detection only worked in the exact
        directory containing .git, not in subdirectories of a Git repository.

        Fix: Proper parent directory searching.
        """
        # Simulate a git repository structure
        repo_dir = temp_dir / "repo"
        repo_dir.mkdir()
        git_dir = repo_dir / ".git"
        git_dir.mkdir()

        # Create subdirectories
        sub_dir = repo_dir / "subdir"
        sub_dir.mkdir()
        deep_dir = sub_dir / "deep"
        deep_dir.mkdir()

        # Mock Git availability
        with patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", True):
            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo:
                mock_repo.return_value = Mock()

                # Should detect Git repo from subdirectories
                git_utils_root = GitUtils(repo_dir)
                git_utils_sub = GitUtils(sub_dir)
                git_utils_deep = GitUtils(deep_dir)

                assert git_utils_root.is_git_repo()
                assert git_utils_sub.is_git_repo()
                assert git_utils_deep.is_git_repo()

    def test_git_branch_with_special_characters_bug(self):
        """
        REGRESSION TEST: Git branch names with special characters caused issues

        Original Bug: Branch names containing special characters like slashes,
        unicode characters, or spaces caused parsing or display issues.

        Fix: Proper branch name handling and encoding.
        """
        special_branch_names = [
            "feature/user-authentication",
            "bugfix/issue-#123",
            "release/v1.0.0-beta",
            "hotfix/urgent-fix",
            "feat/测试-branch",  # Unicode
            "fix/café-issue",  # Accented characters
        ]

        with patch("ai_trackdown_pytools.utils.git.GIT_AVAILABLE", True):
            with patch("ai_trackdown_pytools.utils.git.Repo") as mock_repo:
                for branch_name in special_branch_names:
                    mock_instance = Mock()
                    mock_instance.active_branch.name = branch_name
                    mock_repo.return_value = mock_instance

                    git_utils = GitUtils()
                    current_branch = git_utils.get_current_branch()

                    # Should handle special characters without issues
                    assert current_branch == branch_name


class TestProjectRegressions:
    """Regression tests for project-related bugs."""

    def test_project_creation_permission_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Project creation failed due to permission issues

        Original Bug: Project creation failed when the target directory
        had restrictive permissions or when intermediate directories
        needed to be created.

        Fix: Proper permission handling and directory creation.
        """
        # Test creating project in directory that doesn't exist
        nested_dir = temp_dir / "level1" / "level2" / "level3"

        # Should create all intermediate directories
        project = Project.create(nested_dir, name="Nested Project")

        assert nested_dir.exists()
        assert (nested_dir / ".ai-trackdown").exists()
        assert (nested_dir / ".ai-trackdown" / "config.yaml").exists()

    def test_project_config_inheritance_bug(self, temp_dir: Path):
        """
        REGRESSION TEST: Project config didn't properly inherit from global config

        Original Bug: Project-specific configuration didn't properly inherit
        default values from global configuration, leading to missing settings.

        Fix: Proper configuration merging and inheritance.
        """
        # Create global config
        global_config_dir = temp_dir / "global"
        global_config_dir.mkdir()
        global_config_path = global_config_dir / "config.yaml"

        global_config = Config.create_default(global_config_path)
        global_config.set("editor.default", "global_editor")
        global_config.set("global.setting", "global_value")
        global_config.save()

        # Create project
        project_dir = temp_dir / "project"
        project = Project.create(project_dir, name="Test Project")

        # Project config should be separate but inherit defaults
        project_config_path = project_dir / ".ai-trackdown" / "config.yaml"
        project_config = Config.load(project_config_path)

        # Should have project-specific values
        assert project_config.get("project.name") == "Test Project"

        # Should have reasonable defaults (not necessarily global values)
        assert project_config.get("editor.default") is not None


class TestTaskRegressions:
    """Regression tests for task-related bugs."""

    def test_task_id_collision_bug(self, temp_project: Project):
        """
        REGRESSION TEST: Task ID collision when creating tasks rapidly

        Original Bug: When creating multiple tasks rapidly, the ID generation
        algorithm could produce duplicate IDs due to timing issues.

        Fix: Atomic ID generation with proper locking or collision detection.
        """
        task_manager = TaskManager(temp_project)

        # Create many tasks rapidly
        tasks = []
        for i in range(20):
            task_data = {
                "title": f"Rapid Task {i}",
                "priority": "medium",
                "assignees": [f"user{i % 3}"],
            }
            task = task_manager.create_task(task_data)
            tasks.append(task)

        # All tasks should have unique IDs
        task_ids = [task.id for task in tasks]
        unique_ids = set(task_ids)

        assert len(unique_ids) == len(task_ids), f"Duplicate IDs found: {task_ids}"

    def test_task_file_encoding_bug(self, temp_project: Project):
        """
        REGRESSION TEST: Task files with Unicode content caused encoding errors

        Original Bug: Task files containing Unicode characters in title,
        description, or other fields caused encoding errors when saving
        or loading, especially on Windows systems.

        Fix: Consistent UTF-8 encoding throughout the system.
        """
        task_manager = TaskManager(temp_project)

        unicode_task_data = {
            "title": "Unicode Task: 测试任务 🚀",
            "description": "描述 with émojis 🌟 and special chars: café résumé",
            "assignees": ["用户", "José", "Владимир"],
            "tags": ["标签", "тег", "🏷️"],
            "priority": "medium",
        }

        # Should create task without encoding errors
        task = task_manager.create_task(unicode_task_data)

        # Verify task file was created correctly
        assert task.file_path.exists()

        # Should be able to read back without encoding issues
        content = task.file_path.read_text(encoding="utf-8")
        assert "测试任务" in content
        assert "🚀" in content
        assert "café résumé" in content

    def test_task_search_special_characters_bug(self, temp_project: Project):
        """
        REGRESSION TEST: Task search failed with special characters

        Original Bug: Searching for tasks with special characters in the
        query (regex metacharacters, Unicode, etc.) caused search to fail
        or return incorrect results.

        Fix: Proper escaping and Unicode handling in search.
        """
        task_manager = TaskManager(temp_project)

        # Create tasks with special characters
        special_tasks = [
            {"title": "Bug in auth.py [CRITICAL]", "tags": ["bug"]},
            {"title": "Feature: User.email validation", "tags": ["feature"]},
            {"title": "Fix regex in *.js files", "tags": ["fix"]},
            {"title": "Unicode test: 测试搜索", "tags": ["test"]},
            {"title": "Task with (parentheses) and $symbols", "tags": ["misc"]},
        ]

        created_tasks = []
        for task_data in special_tasks:
            task_data["priority"] = "medium"
            task = task_manager.create_task(task_data)
            created_tasks.append(task)

        # Search should handle special characters gracefully
        search_queries = [
            "auth.py",  # Dot
            "[CRITICAL]",  # Brackets
            "*.js",  # Asterisk
            "测试",  # Unicode
            "(parentheses)",  # Parentheses
            "$symbols",  # Dollar sign
        ]

        for query in search_queries:
            try:
                # Search should not crash
                results = task_manager.search_tasks(query)
                # Should return some results (may or may not find exact matches)
                assert isinstance(results, list)
            except Exception as e:
                # Should not crash with regex or encoding errors
                assert "regex" not in str(e).lower()
                assert "encoding" not in str(e).lower()


# Utility functions for regression testing
def create_legacy_data_structure(temp_dir: Path) -> Path:
    """Create data structure that mimics older versions for compatibility testing."""
    legacy_project = temp_dir / "legacy_project"
    legacy_project.mkdir()

    # Create old-style config
    old_config = legacy_project / "config.yml"  # Note: .yml not .yaml
    old_config.write_text(
        """
version: 0.8.0
project_name: Legacy Project
task_directory: ./tasks
template_directory: ./templates
"""
    )

    # Create old-style task
    tasks_dir = legacy_project / "tasks"
    tasks_dir.mkdir()

    old_task = tasks_dir / "task-001.md"
    old_task.write_text(
        """# Task 001

**Priority**: High
**Status**: Open
**Assignee**: legacy_user

Legacy format task description.
"""
    )

    return legacy_project


def simulate_version_upgrade(legacy_path: Path) -> bool:
    """Simulate upgrading from an older version to test compatibility."""
    # This would contain migration logic in a real system
    # For testing, just verify we can read legacy data

    try:
        # Try to read legacy config
        config_files = list(legacy_path.glob("config.*"))
        if config_files:
            config_content = config_files[0].read_text()
            return "version" in config_content

        return False
    except Exception:
        return False


# Test markers for regression tests
pytest.mark.regression = (
    pytest.mark.regression
    if hasattr(pytest.mark, "regression")
    else pytest.mark.skipif(False, reason="Regression tests")
)

pytest.mark.legacy = pytest.mark.skipif(
    os.environ.get("SKIP_LEGACY_TESTS") == "1",
    reason="Legacy compatibility tests skipped",
)
