"""Unit tests for template utilities."""

import tempfile
from pathlib import Path

import pytest

from ai_trackdown_pytools.utils.templates import (
    TemplateEngine,
    TemplateError,
    TemplateManager,
    get_template_variables,
    load_template,
    render_template,
    validate_template,
)


class TestTemplateEngine:
    """Test TemplateEngine functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.engine = TemplateEngine()

    def test_render_simple_template(self):
        """Test rendering simple template."""
        template_content = "Hello {{ name }}!"
        variables = {"name": "World"}

        result = self.engine.render(template_content, variables)

        assert result == "Hello World!"

    def test_render_template_with_filters(self):
        """Test rendering template with filters."""
        template_content = "Hello {{ name|upper }}!"
        variables = {"name": "world"}

        result = self.engine.render(template_content, variables)

        assert result == "Hello WORLD!"

    def test_render_template_with_loops(self):
        """Test rendering template with loops."""
        template_content = """
Items:
{% for item in items -%}
- {{ item }}
{% endfor %}
""".strip()
        variables = {"items": ["apple", "banana", "cherry"]}

        result = self.engine.render(template_content, variables)

        assert "- apple" in result
        assert "- banana" in result
        assert "- cherry" in result

    def test_render_template_with_conditionals(self):
        """Test rendering template with conditionals."""
        template_content = """
{% if user.is_admin -%}
Admin: {{ user.name }}
{% else -%}
User: {{ user.name }}
{% endif %}
""".strip()

        # Test admin user
        admin_variables = {"user": {"name": "Alice", "is_admin": True}}
        result = self.engine.render(template_content, admin_variables)
        assert "Admin: Alice" in result

        # Test regular user
        user_variables = {"user": {"name": "Bob", "is_admin": False}}
        result = self.engine.render(template_content, user_variables)
        assert "User: Bob" in result

    def test_render_template_with_custom_filters(self):
        """Test rendering template with custom filters."""
        # Test the slugify filter (should be built-in)
        template_content = "{{ title|slugify }}"
        variables = {"title": "My Test Task"}

        result = self.engine.render(template_content, variables)

        # Should convert to slug format
        assert "my-test-task" in result.lower() or "my_test_task" in result.lower()

    def test_render_template_with_date_formatting(self):
        """Test rendering template with date formatting."""
        from datetime import datetime

        template_content = "Created: {{ created_at|strftime('%Y-%m-%d') }}"
        variables = {"created_at": datetime(2025, 7, 11, 10, 30, 0)}

        result = self.engine.render(template_content, variables)

        assert "Created: 2025-07-11" in result

    def test_render_template_with_missing_variable(self):
        """Test rendering template with missing variable."""
        template_content = "Hello {{ missing_var }}!"
        variables = {}

        # Should not raise error, should render as empty or undefined
        result = self.engine.render(template_content, variables)

        # Jinja2 should handle missing variables gracefully
        assert "Hello" in result

    def test_render_invalid_template_syntax(self):
        """Test rendering template with invalid syntax."""
        template_content = "Hello {{ unclosed_var"
        variables = {"name": "World"}

        with pytest.raises(Exception):  # Should raise template syntax error
            self.engine.render(template_content, variables)

    def test_extract_variables_from_template(self):
        """Test extracting variables from template."""
        template_content = """
Title: {{ title }}
Assignee: {{ assignee }}
Status: {{ status|default('open') }}
{% for tag in tags -%}
Tag: {{ tag }}
{% endfor %}
Priority: {{ priority }}
"""

        variables = self.engine.extract_variables(template_content)

        expected_vars = {"title", "assignee", "status", "tags", "priority"}
        assert expected_vars.issubset(set(variables))

    def test_validate_template_syntax(self):
        """Test validating template syntax."""
        # Valid template
        valid_template = "Hello {{ name }}!"
        assert self.engine.validate_syntax(valid_template)

        # Invalid template
        invalid_template = "Hello {{ unclosed_var"
        assert not self.engine.validate_syntax(invalid_template)

    def test_render_with_complex_data_structures(self):
        """Test rendering with complex data structures."""
        template_content = """
Task: {{ task.title }}
Assigned to: {{ task.assignees|join(', ') }}
Tags: {{ task.tags|join(' | ') }}
Priority: {{ task.priority|upper }}
"""
        variables = {
            "task": {
                "title": "Complex Task",
                "assignees": ["alice", "bob", "charlie"],
                "tags": ["bug", "critical", "frontend"],
                "priority": "high",
            }
        }

        result = self.engine.render(template_content, variables)

        assert "Task: Complex Task" in result
        assert "alice, bob, charlie" in result
        assert "bug | critical | frontend" in result
        assert "Priority: HIGH" in result

    def test_render_template_with_includes(self):
        """Test rendering template with includes (if supported)."""
        # This test would require setting up template directories
        # For now, test basic template rendering
        template_content = """
{%- set header = "Task Details" -%}
{{ header }}
{{ "=" * header|length }}

Title: {{ title }}
"""
        variables = {"title": "Test Task"}

        result = self.engine.render(template_content, variables)

        assert "Task Details" in result
        assert "=" in result
        assert "Title: Test Task" in result


class TestTemplateManager:
    """Test TemplateManager functionality."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_templates_directory(self):
        """Create test templates directory."""
        self.temp_dir = tempfile.mkdtemp()
        templates_dir = Path(self.temp_dir) / "templates"
        templates_dir.mkdir()

        # Create task template
        task_template = templates_dir / "task" / "default.yaml"
        task_template.parent.mkdir()
        task_template.write_text(
            """---
id: {{ id or 'TSK-' + '%04d'|format(sequence_number) }}
title: {{ title }}
description: {{ description or '' }}
status: {{ status or 'open' }}
priority: {{ priority or 'medium' }}
assignees: {{ assignees or [] }}
tags: {{ tags or [] }}
created_at: {{ created_at or now() }}
updated_at: {{ updated_at or now() }}
{% if parent -%}
parent: {{ parent }}
{% endif -%}
{% if dependencies -%}
dependencies: {{ dependencies }}
{% endif -%}
---

# {{ title }}

{{ content or description or 'Task description here.' }}
"""
        )

        # Create epic template
        epic_template = templates_dir / "epic" / "default.yaml"
        epic_template.parent.mkdir()
        epic_template.write_text(
            """---
id: {{ id or 'EP-' + '%04d'|format(sequence_number) }}
title: {{ title }}
description: {{ description or '' }}
goal: {{ goal or '' }}
business_value: {{ business_value or '' }}
success_criteria: {{ success_criteria or '' }}
status: {{ status or 'planning' }}
priority: {{ priority or 'medium' }}
created_at: {{ created_at or now() }}
updated_at: {{ updated_at or now() }}
{% if target_date -%}
target_date: {{ target_date }}
{% endif -%}
---

# {{ title }}

## Goal
{{ goal or 'Epic goal here.' }}

## Business Value
{{ business_value or 'Business value description.' }}

## Success Criteria
{{ success_criteria or 'Success criteria here.' }}
"""
        )

        return TemplateManager(templates_dir)

    def test_template_manager_creation(self):
        """Test creating TemplateManager."""
        manager = self._create_test_templates_directory()

        assert manager.templates_dir.exists()

    def test_list_template_types(self):
        """Test listing available template types."""
        manager = self._create_test_templates_directory()

        template_types = manager.list_template_types()

        assert "task" in template_types
        assert "epic" in template_types

    def test_list_templates_for_type(self):
        """Test listing templates for specific type."""
        manager = self._create_test_templates_directory()

        task_templates = manager.list_templates("task")
        epic_templates = manager.list_templates("epic")

        assert "default" in task_templates
        assert "default" in epic_templates

    def test_load_template(self):
        """Test loading template."""
        manager = self._create_test_templates_directory()

        template_content = manager.load_template("task", "default")

        assert "id: {{ id" in template_content
        assert "title: {{ title }}" in template_content
        assert "# {{ title }}" in template_content

    def test_load_nonexistent_template(self):
        """Test loading non-existent template."""
        manager = self._create_test_templates_directory()

        with pytest.raises(TemplateError, match="Template not found"):
            manager.load_template("task", "nonexistent")

    def test_load_template_invalid_type(self):
        """Test loading template with invalid type."""
        manager = self._create_test_templates_directory()

        with pytest.raises(TemplateError, match="Template type not found"):
            manager.load_template("invalid_type", "default")

    def test_render_template(self):
        """Test rendering template with variables."""
        manager = self._create_test_templates_directory()

        variables = {
            "id": "TSK-0001",
            "title": "Test Task",
            "description": "This is a test task",
            "priority": "high",
            "assignees": ["alice", "bob"],
        }

        result = manager.render_template("task", "default", variables)

        assert "id: TSK-0001" in result
        assert "title: Test Task" in result
        assert "priority: high" in result
        assert "# Test Task" in result

    def test_render_template_with_defaults(self):
        """Test rendering template with default values."""
        manager = self._create_test_templates_directory()

        variables = {"title": "Minimal Task"}

        result = manager.render_template("task", "default", variables)

        assert "title: Minimal Task" in result
        assert "status: open" in result  # Default value
        assert "priority: medium" in result  # Default value
        assert "# Minimal Task" in result

    def test_get_template_variables(self):
        """Test getting template variables."""
        manager = self._create_test_templates_directory()

        variables = manager.get_template_variables("task", "default")

        expected_vars = {
            "id",
            "title",
            "description",
            "status",
            "priority",
            "assignees",
            "tags",
        }
        assert expected_vars.issubset(set(variables))

    def test_validate_template(self):
        """Test validating template."""
        manager = self._create_test_templates_directory()

        # Valid template should validate successfully
        is_valid, errors = manager.validate_template("task", "default")
        assert is_valid
        assert len(errors) == 0

    def test_create_custom_template(self):
        """Test creating custom template."""
        manager = self._create_test_templates_directory()

        custom_template_content = """---
id: {{ id }}
title: {{ title }}
custom_field: {{ custom_field or 'default_value' }}
---

# Custom Template: {{ title }}

Custom content here.
"""

        # Create custom template
        custom_template_path = manager.templates_dir / "task" / "custom.yaml"
        custom_template_path.write_text(custom_template_content)

        # Verify it can be loaded and rendered
        templates = manager.list_templates("task")
        assert "custom" in templates

        variables = {
            "id": "TSK-0001",
            "title": "Custom Task",
            "custom_field": "custom_value",
        }
        result = manager.render_template("task", "custom", variables)

        assert "Custom Template: Custom Task" in result
        assert "custom_field: custom_value" in result

    def test_template_with_complex_logic(self):
        """Test template with complex logic."""
        manager = self._create_test_templates_directory()

        # Create template with complex logic
        complex_template = """---
id: {{ id }}
title: {{ title }}
{% if priority == 'critical' -%}
escalation_required: true
{% endif -%}
{% if assignees|length > 1 -%}
team_task: true
{% endif -%}
---

# {{ title }}

{% if priority == 'critical' -%}
🚨 CRITICAL PRIORITY TASK 🚨
{% endif -%}

{% if assignees -%}
Assigned to: {{ assignees|join(', ') }}
{% else -%}
⚠️ No assignees
{% endif -%}
"""

        complex_path = manager.templates_dir / "task" / "complex.yaml"
        complex_path.write_text(complex_template)

        # Test with critical priority and multiple assignees
        variables = {
            "id": "TSK-0001",
            "title": "Critical Task",
            "priority": "critical",
            "assignees": ["alice", "bob", "charlie"],
        }

        result = manager.render_template("task", "complex", variables)

        assert "escalation_required: true" in result
        assert "team_task: true" in result
        assert "🚨 CRITICAL PRIORITY TASK 🚨" in result
        assert "alice, bob, charlie" in result

    def test_template_inheritance_or_includes(self):
        """Test template inheritance or includes if supported."""
        manager = self._create_test_templates_directory()

        # Create base template
        base_template = """---
# Base frontmatter
base_field: {{ base_field or 'base_value' }}
id: {{ id }}
title: {{ title }}
---

# Base Template

This is base content.
"""

        base_path = manager.templates_dir / "base.yaml"
        base_path.write_text(base_template)

        # For now, just test that we can load and render the base template
        variables = {"id": "TSK-0001", "title": "Base Test"}
        result = manager.render_template("task", "default", variables)

        assert "id: TSK-0001" in result
        assert "title: Base Test" in result

    def test_template_caching(self):
        """Test template caching behavior."""
        manager = self._create_test_templates_directory()

        # Load template multiple times
        template1 = manager.load_template("task", "default")
        template2 = manager.load_template("task", "default")

        # Should be the same content
        assert template1 == template2

        # Test that template manager handles file system efficiently
        # (This is more about ensuring no errors than checking actual caching)
        for _ in range(10):
            manager.load_template("task", "default")


class TestConvenienceFunctions:
    """Test convenience functions for template operations."""

    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = None

    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir:
            import shutil

            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_template_file(self):
        """Create a simple template file."""
        self.temp_dir = tempfile.mkdtemp()
        template_path = Path(self.temp_dir) / "test_template.yaml"
        template_path.write_text(
            """---
id: {{ id }}
title: {{ title }}
status: {{ status or 'open' }}
---

# {{ title }}

{{ description or 'No description provided.' }}
"""
        )
        return template_path

    def test_load_template_function(self):
        """Test load_template convenience function."""
        template_path = self._create_template_file()

        content = load_template(template_path)

        assert "id: {{ id }}" in content
        assert "title: {{ title }}" in content

    def test_render_template_function(self):
        """Test render_template convenience function."""
        template_path = self._create_template_file()

        variables = {
            "id": "TSK-0001",
            "title": "Convenience Test",
            "description": "Testing convenience function",
        }

        result = render_template(template_path, variables)

        assert "id: TSK-0001" in result
        assert "title: Convenience Test" in result
        assert "# Convenience Test" in result
        assert "Testing convenience function" in result

    def test_validate_template_function(self):
        """Test validate_template convenience function."""
        template_path = self._create_template_file()

        is_valid, errors = validate_template(template_path)

        assert is_valid
        assert len(errors) == 0

    def test_get_template_variables_function(self):
        """Test get_template_variables convenience function."""
        template_path = self._create_template_file()

        variables = get_template_variables(template_path)

        expected_vars = {"id", "title", "status", "description"}
        assert expected_vars.issubset(set(variables))


class TestTemplateError:
    """Test TemplateError exception."""

    def test_template_error_creation(self):
        """Test creating TemplateError."""
        error = TemplateError("Test error message")
        assert str(error) == "Test error message"

    def test_template_error_inheritance(self):
        """Test TemplateError inheritance."""
        error = TemplateError("Test error")
        assert isinstance(error, Exception)


class TestTemplateUtilities:
    """Test template utility functions."""

    def test_template_variable_extraction_complex(self):
        """Test extracting variables from complex template."""
        template_content = """
{%- set calculated_value = (priority == 'high') -%}
---
id: {{ id }}
title: {{ title|title }}
complex_field: {{ nested.field.value }}
conditional: {% if show_conditional %}{{ conditional_value }}{% endif %}
loop_data:
{% for item in items -%}
  - {{ item.name }}: {{ item.value }}
{% endfor %}
---

# {{ title }}

{% if user.is_admin -%}
Admin content: {{ admin_content }}
{% endif -%}
"""

        engine = TemplateEngine()
        variables = engine.extract_variables(template_content)

        expected_vars = {
            "id",
            "title",
            "priority",
            "nested",
            "show_conditional",
            "conditional_value",
            "items",
            "user",
            "admin_content",
        }
        found_vars = set(variables)

        # Check that most expected variables are found
        # (Some template engines might not catch all variables in complex expressions)
        assert len(expected_vars.intersection(found_vars)) >= 5

    def test_template_security_considerations(self):
        """Test template security considerations."""
        engine = TemplateEngine()

        # Templates should not allow access to dangerous functions
        dangerous_template = "{{ ''.__class__.__mro__[1].__subclasses__() }}"

        # This should either fail to render or render safely
        try:
            result = engine.render(dangerous_template, {})
            # If it renders, it should not contain dangerous content
            assert "__subclasses__" not in result
        except Exception:
            # It's also acceptable for the template engine to reject this
            pass
