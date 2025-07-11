#!/usr/bin/env python3
"""Demonstration of the AI Trackdown PyTools validation system.

This script demonstrates:
1. JSON Schema validation for all ticket types
2. Pydantic model validation with type safety
3. YAML frontmatter parsing and validation
4. Status workflow validation
5. Relationship validation between tickets
6. Comprehensive error reporting
"""

import json
import tempfile
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Import validation components
try:
    from ai_trackdown_pytools.utils.validation import (
        SchemaValidator, ValidationResult,
        validate_ticket_file, validate_relationships,
        validate_id_format
    )
    from ai_trackdown_pytools.utils.frontmatter import (
        FrontmatterParser, StatusWorkflowValidator
    )
    from ai_trackdown_pytools.core.models import (
        TaskModel, EpicModel, IssueModel, PRModel, ProjectModel
    )
except ImportError as e:
    print(f"Error importing validation modules: {e}")
    print("Please ensure ai-trackdown-pytools is properly installed.")
    exit(1)

console = Console()


def demo_schema_validation():
    """Demonstrate JSON schema validation."""
    console.print("\n[bold blue]1. JSON Schema Validation Demo[/bold blue]")
    
    validator = SchemaValidator()
    
    # Valid task data
    valid_task = {
        "id": "TSK-0001",
        "title": "Implement user authentication",
        "description": "Add login and registration functionality",
        "status": "open",
        "priority": "high",
        "assignees": ["alice", "bob"],
        "tags": ["auth", "security"],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "estimated_hours": 16.0
    }
    
    result = validator.validate_ticket(valid_task, "task")
    console.print(f"[green]✓ Valid task validation:[/green] {result.valid}")
    
    # Invalid task data
    invalid_task = {
        "id": "INVALID-001",  # Wrong ID format
        "title": "",  # Empty title
        "status": "invalid_status",  # Invalid status
        "priority": "super_urgent",  # Invalid priority
        "created_at": "not-a-date",  # Invalid date
        "dependencies": ["TSK-0001", "TSK-0001"]  # Self-dependency will be caught
    }
    
    result = validator.validate_ticket(invalid_task, "task")
    console.print(f"[red]✗ Invalid task validation:[/red] {result.valid}")
    console.print(f"  Errors: {len(result.errors)}")
    for error in result.errors[:3]:  # Show first 3 errors
        console.print(f"    • {error}")
    if len(result.errors) > 3:
        console.print(f"    ... and {len(result.errors) - 3} more errors")


def demo_pydantic_validation():
    """Demonstrate Pydantic model validation."""
    console.print("\n[bold blue]2. Pydantic Model Validation Demo[/bold blue]")
    
    # Valid epic creation
    try:
        epic = EpicModel(
            id="EP-0001",
            title="User Management Epic",
            description="Complete user management system",
            goal="Enable user registration, authentication, and profile management",
            business_value="Allows user onboarding and personalization",
            success_criteria="Users can register, login, and manage profiles",
            status="planning",
            priority="high",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            target_date=date(2025, 12, 31)
        )
        console.print(f"[green]✓ Valid epic created:[/green] {epic.id} - {epic.title}")
    except Exception as e:
        console.print(f"[red]✗ Epic creation failed:[/red] {e}")
    
    # Invalid issue creation (should fail)
    try:
        issue = IssueModel(
            id="WRONG-001",  # Wrong prefix for issue
            title="Test Issue",
            issue_type="bug",
            severity="medium",
            status="open",
            priority="medium",
            created_at=datetime.now(),
            updated_at=datetime(2020, 1, 1)  # Updated before created (should fail)
        )
        console.print(f"[red]✗ Invalid issue should have failed but didn't[/red]")
    except Exception as e:
        console.print(f"[green]✓ Invalid issue correctly rejected:[/green] {type(e).__name__}")


def demo_frontmatter_parsing():
    """Demonstrate YAML frontmatter parsing and validation."""
    console.print("\n[bold blue]3. YAML Frontmatter Parsing Demo[/bold blue]")
    
    parser = FrontmatterParser(validate_schema=True)
    
    # Create a sample markdown file with frontmatter
    sample_content = """---
id: TSK-0002
title: "Fix database connection pool"
description: "Resolve issues with connection pool exhaustion"
status: open
priority: critical
assignees:
  - "database-team"
tags:
  - "database"
  - "performance"
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T10:00:00
estimated_hours: 8.0
---

# Fix Database Connection Pool

## Problem
The application is experiencing connection pool exhaustion during peak hours.

## Solution
1. Investigate current pool configuration
2. Optimize connection lifecycle
3. Add monitoring and alerting

## Acceptance Criteria
- [ ] No connection pool exhaustion errors
- [ ] Response times under 100ms
- [ ] Proper monitoring in place
"""
    
    # Parse the content
    frontmatter, content, result = parser.parse_string(sample_content)
    
    if result.valid:
        console.print(f"[green]✓ Frontmatter parsed successfully[/green]")
        console.print(f"  Task ID: {frontmatter.get('id')}")
        console.print(f"  Title: {frontmatter.get('title')}")
        console.print(f"  Priority: {frontmatter.get('priority')}")
        console.print(f"  Content length: {len(content)} characters")
    else:
        console.print(f"[red]✗ Frontmatter parsing failed[/red]")
        for error in result.errors:
            console.print(f"    • {error}")
    
    # Test with invalid YAML
    invalid_content = """---
invalid: yaml: content: here
---

# Invalid File
"""
    
    _, _, invalid_result = parser.parse_string(invalid_content)
    console.print(f"[green]✓ Invalid YAML correctly rejected:[/green] {not invalid_result.valid}")


def demo_workflow_validation():
    """Demonstrate status workflow validation."""
    console.print("\n[bold blue]4. Status Workflow Validation Demo[/bold blue]")
    
    workflow_validator = StatusWorkflowValidator()
    
    # Valid transitions
    valid_transitions = [
        ("task", "open", "in_progress"),
        ("task", "in_progress", "completed"),
        ("epic", "planning", "in_progress"),
        ("pr", "draft", "ready_for_review"),
        ("pr", "approved", "merged")
    ]
    
    console.print("[green]Valid transitions:[/green]")
    for ticket_type, from_status, to_status in valid_transitions:
        result = workflow_validator.validate_status_transition(ticket_type, from_status, to_status)
        status = "✓" if result.valid else "✗"
        console.print(f"  {status} {ticket_type}: {from_status} → {to_status}")
    
    # Invalid transitions
    invalid_transitions = [
        ("task", "completed", "open"),  # Can't reopen completed task
        ("pr", "merged", "draft"),      # Can't change merged PR to draft
        ("epic", "completed", "planning")  # Can't go back from completed
    ]
    
    console.print("\n[red]Invalid transitions:[/red]")
    for ticket_type, from_status, to_status in invalid_transitions:
        result = workflow_validator.validate_status_transition(ticket_type, from_status, to_status)
        status = "✗" if not result.valid else "✓"
        console.print(f"  {status} {ticket_type}: {from_status} → {to_status}")
        if not result.valid and result.errors:
            console.print(f"    Error: {result.errors[0]}")


def demo_relationship_validation():
    """Demonstrate relationship validation between tickets."""
    console.print("\n[bold blue]5. Relationship Validation Demo[/bold blue]")
    
    # Valid relationship hierarchy
    valid_tickets = [
        {
            "id": "EP-0001",
            "title": "User Management Epic",
            "child_issues": ["ISS-0001", "ISS-0002"]
        },
        {
            "id": "ISS-0001",
            "title": "User Registration",
            "parent": "EP-0001",
            "child_tasks": ["TSK-0001", "TSK-0002"]
        },
        {
            "id": "ISS-0002",
            "title": "User Authentication",
            "parent": "EP-0001",
            "child_tasks": ["TSK-0003"]
        },
        {
            "id": "TSK-0001",
            "title": "Create registration form",
            "parent": "ISS-0001"
        },
        {
            "id": "TSK-0002",
            "title": "Add email validation",
            "parent": "ISS-0001",
            "dependencies": ["TSK-0001"]
        },
        {
            "id": "TSK-0003",
            "title": "Implement JWT authentication",
            "parent": "ISS-0002"
        }
    ]
    
    result = validate_relationships(valid_tickets)
    console.print(f"[green]✓ Valid relationships:[/green] {result.valid}")
    
    # Invalid relationships (circular dependency)
    invalid_tickets = [
        {
            "id": "TSK-0001",
            "title": "Task 1",
            "dependencies": ["TSK-0002"]
        },
        {
            "id": "TSK-0002",
            "title": "Task 2",
            "dependencies": ["TSK-0003"]
        },
        {
            "id": "TSK-0003",
            "title": "Task 3",
            "dependencies": ["TSK-0001"]  # Circular dependency
        }
    ]
    
    result = validate_relationships(invalid_tickets)
    console.print(f"[red]✗ Invalid relationships:[/red] {result.valid}")
    if result.errors:
        console.print(f"  Error: {result.errors[0]}")


def demo_id_format_validation():
    """Demonstrate ID format validation."""
    console.print("\n[bold blue]6. ID Format Validation Demo[/bold blue]")
    
    # Test various ID formats
    test_cases = [
        ("TSK-0001", "task", True),
        ("EP-0001", "epic", True),
        ("ISS-0001", "issue", True),
        ("PR-0001", "pr", True),
        ("PROJ-0001", "project", True),
        ("INVALID-001", "task", False),
        ("TSK-INVALID", "task", False),
        ("EP-0001", "task", False),  # Epic ID for task type
    ]
    
    table = Table(title="ID Format Validation Results")
    table.add_column("ID", style="cyan")
    table.add_column("Type", style="blue")
    table.add_column("Expected", style="white")
    table.add_column("Result", style="white")
    table.add_column("Status", style="white")
    
    for ticket_id, ticket_type, expected in test_cases:
        result = validate_id_format(ticket_id, ticket_type)
        actual = result.valid
        status = "✓" if actual == expected else "✗"
        status_style = "green" if actual == expected else "red"
        
        table.add_row(
            ticket_id,
            ticket_type,
            "Valid" if expected else "Invalid",
            "Valid" if actual else "Invalid",
            f"[{status_style}]{status}[/{status_style}]"
        )
    
    console.print(table)


def demo_comprehensive_validation():
    """Demonstrate comprehensive file validation."""
    console.print("\n[bold blue]7. Comprehensive File Validation Demo[/bold blue]")
    
    # Create a temporary file with complete ticket data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("""---
id: TSK-0001
title: "Implement comprehensive validation system"
description: "Build a complete validation system for all ticket types"
status: in_progress
priority: high
assignees:
  - "validation-team"
tags:
  - "validation"
  - "schema"
  - "pydantic"
created_at: 2025-07-11T10:00:00
updated_at: 2025-07-11T11:30:00
estimated_hours: 24.0
actual_hours: 16.0
dependencies: []
parent: "ISS-0001"
labels:
  - "enhancement"
  - "core-feature"
metadata:
  complexity: "high"
  reviewed: true
---

# Implement Comprehensive Validation System

## Overview
This task involves implementing a complete validation system that supports:
- JSON Schema validation
- Pydantic model validation
- YAML frontmatter parsing
- Status workflow validation
- Relationship validation

## Implementation Details
1. Create JSON schemas for all ticket types
2. Implement Pydantic models with comprehensive validation
3. Build YAML frontmatter parser
4. Add status workflow validation
5. Implement relationship validation
6. Create comprehensive test suite

## Acceptance Criteria
- [ ] All ticket types have JSON schemas
- [ ] Pydantic models validate correctly
- [ ] YAML frontmatter parsing works
- [ ] Status transitions are validated
- [ ] Relationships are validated
- [ ] Comprehensive error reporting
- [ ] Full test coverage

## Notes
This is a foundational feature that will improve data quality and prevent errors in the ticket management system.
""")
        temp_path = Path(f.name)
    
    try:
        # Validate the file
        result = validate_ticket_file(temp_path)
        
        if result.valid:
            console.print(f"[green]✓ File validation passed[/green]")
        else:
            console.print(f"[red]✗ File validation failed[/red]")
        
        if result.warnings:
            console.print(f"[yellow]Warnings ({len(result.warnings)}):[/yellow]")
            for warning in result.warnings:
                console.print(f"  • {warning}")
        
        if result.errors:
            console.print(f"[red]Errors ({len(result.errors)}):[/red]")
            for error in result.errors:
                console.print(f"  • {error}")
    
    finally:
        # Clean up temporary file
        temp_path.unlink()


def main():
    """Run all validation demos."""
    console.print(Panel.fit(
        "[bold]AI Trackdown PyTools - Validation System Demo[/bold]\n\n"
        "This demonstration showcases the comprehensive ticket validation system including:\n"
        "• JSON Schema validation for all ticket types\n"
        "• Pydantic model validation with type safety\n"
        "• YAML frontmatter parsing and validation\n"
        "• Status workflow validation\n"
        "• Relationship validation between tickets\n"
        "• ID format validation\n"
        "• Comprehensive error reporting",
        title="Validation Demo",
        border_style="blue"
    ))
    
    try:
        demo_schema_validation()
        demo_pydantic_validation()
        demo_frontmatter_parsing()
        demo_workflow_validation()
        demo_relationship_validation()
        demo_id_format_validation()
        demo_comprehensive_validation()
        
        console.print("\n[bold green]🎉 All validation demos completed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Demo failed with error: {e}[/bold red]")
        import traceback
        console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
