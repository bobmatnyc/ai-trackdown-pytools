#!/usr/bin/env python3
"""Test script for ticket type conversion functionality.

This script tests the new ticket conversion feature that allows converting
tickets between different types (TSK <-> ISS <-> EP).

Usage:
    python scripts/test_ticket_conversion.py
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
import yaml
from datetime import datetime


def run_command(cmd: list, cwd: Path = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, and stderr."""
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def create_test_project():
    """Create a temporary test project."""
    temp_dir = Path(tempfile.mkdtemp(prefix="aitrackdown_test_"))
    print(f"Created test project at: {temp_dir}")
    
    # Initialize the project
    ret, out, err = run_command(["aitrackdown", "init", "project", "test-conversion"], cwd=temp_dir)
    if ret != 0:
        print(f"Failed to initialize project: {err}")
        return None
    
    project_dir = temp_dir / "test-conversion"
    return project_dir


def load_ticket_file(file_path: Path) -> dict:
    """Load and parse a ticket file."""
    if not file_path.exists():
        return None
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Extract frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            return frontmatter
    
    return None


def test_task_to_issue_conversion(project_dir: Path):
    """Test converting a task to an issue."""
    print("\n=== Testing TSK -> ISS conversion ===")
    
    # Create a task
    ret, out, err = run_command([
        "aitrackdown", "create", "task",
        "Test task for conversion",
        "--description", "This task will be converted to an issue",
        "--priority", "high",
        "--tags", "test,conversion"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to create task: {err}")
        return False
    
    # Extract task ID from output
    task_id = None
    for line in out.split('\n'):
        if 'TSK-' in line:
            import re
            match = re.search(r'TSK-\d+', line)
            if match:
                task_id = match.group()
                break
    
    if not task_id:
        print("Could not find task ID in output")
        return False
    
    print(f"Created task: {task_id}")
    
    # Load the original task
    task_file = project_dir / "tickets" / "tasks" / f"{task_id}.md"
    original_data = load_ticket_file(task_file)
    if not original_data:
        print(f"Failed to load task file: {task_file}")
        return False
    
    # Convert task to issue
    ret, out, err = run_command([
        "aitrackdown", "convert", task_id, "--to", "issue"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to convert task to issue: {err}")
        return False
    
    # Extract new issue ID from output
    issue_id = None
    for line in out.split('\n'):
        if 'ISS-' in line:
            import re
            match = re.search(r'ISS-\d+', line)
            if match:
                issue_id = match.group()
                break
    
    if not issue_id:
        print("Could not find issue ID in output")
        return False
    
    print(f"Converted to issue: {issue_id}")
    
    # Verify the new issue exists
    issue_file = project_dir / "tickets" / "issues" / f"{issue_id}.md"
    if not issue_file.exists():
        print(f"Issue file not found: {issue_file}")
        return False
    
    # Load the new issue
    new_data = load_ticket_file(issue_file)
    if not new_data:
        print(f"Failed to load issue file: {issue_file}")
        return False
    
    # Verify metadata is preserved
    assert new_data['title'] == original_data['title'], "Title not preserved"
    assert new_data['description'] == original_data['description'], "Description not preserved"
    assert new_data['priority'] == original_data['priority'], "Priority not preserved"
    assert new_data['tags'] == original_data['tags'], "Tags not preserved"
    
    # Verify conversion metadata
    assert 'converted_from' in new_data['metadata'], "Missing converted_from metadata"
    assert new_data['metadata']['converted_from'] == task_id, "Incorrect converted_from value"
    assert new_data['metadata']['converted_from_type'] == 'task', "Incorrect converted_from_type"
    assert 'converted_at' in new_data['metadata'], "Missing converted_at metadata"
    
    # Verify original is archived
    archive_file = project_dir / "tickets" / "tasks" / "archive" / f"{task_id}.md"
    if not archive_file.exists():
        print(f"Original task not archived: {archive_file}")
        return False
    
    print("✓ Task to Issue conversion successful")
    return True


def test_issue_to_epic_conversion(project_dir: Path):
    """Test converting an issue to an epic."""
    print("\n=== Testing ISS -> EP conversion ===")
    
    # Create an issue
    ret, out, err = run_command([
        "aitrackdown", "create", "issue",
        "Test issue for epic conversion",
        "--description", "This issue will become an epic",
        "--priority", "critical"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to create issue: {err}")
        return False
    
    # Extract issue ID
    issue_id = None
    for line in out.split('\n'):
        if 'ISS-' in line:
            import re
            match = re.search(r'ISS-\d+', line)
            if match:
                issue_id = match.group()
                break
    
    if not issue_id:
        print("Could not find issue ID in output")
        return False
    
    print(f"Created issue: {issue_id}")
    
    # Convert issue to epic
    ret, out, err = run_command([
        "aitrackdown", "convert", issue_id, "--to", "epic"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to convert issue to epic: {err}")
        return False
    
    # Extract epic ID
    epic_id = None
    for line in out.split('\n'):
        if 'EP-' in line:
            import re
            match = re.search(r'EP-\d+', line)
            if match:
                epic_id = match.group()
                break
    
    if not epic_id:
        print("Could not find epic ID in output")
        return False
    
    print(f"Converted to epic: {epic_id}")
    
    # Verify the epic exists
    epic_file = project_dir / "tickets" / "epics" / f"{epic_id}.md"
    if not epic_file.exists():
        print(f"Epic file not found: {epic_file}")
        return False
    
    print("✓ Issue to Epic conversion successful")
    return True


def test_bidirectional_conversion(project_dir: Path):
    """Test bidirectional conversion (EP -> ISS -> EP)."""
    print("\n=== Testing bidirectional conversion ===")
    
    # Create an epic
    ret, out, err = run_command([
        "aitrackdown", "create", "epic",
        "Test bidirectional conversion",
        "--description", "Epic for bidirectional test"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to create epic: {err}")
        return False
    
    # Extract epic ID
    epic_id = None
    for line in out.split('\n'):
        if 'EP-' in line:
            import re
            match = re.search(r'EP-\d+', line)
            if match:
                epic_id = match.group()
                break
    
    if not epic_id:
        print("Could not find epic ID in output")
        return False
    
    print(f"Created epic: {epic_id}")
    
    # Convert epic to issue
    ret, out, err = run_command([
        "aitrackdown", "convert", epic_id, "--to", "issue"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to convert epic to issue: {err}")
        return False
    
    # Extract issue ID
    issue_id = None
    for line in out.split('\n'):
        if 'ISS-' in line:
            import re
            match = re.search(r'ISS-\d+', line)
            if match:
                issue_id = match.group()
                break
    
    print(f"Converted to issue: {issue_id}")
    
    # Convert back to epic
    ret, out, err = run_command([
        "aitrackdown", "convert", issue_id, "--to", "epic"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to convert issue back to epic: {err}")
        return False
    
    # Extract new epic ID
    new_epic_id = None
    for line in out.split('\n'):
        if 'EP-' in line:
            import re
            match = re.search(r'EP-\d+', line)
            if match:
                new_epic_id = match.group()
                break
    
    print(f"Converted back to epic: {new_epic_id}")
    
    print("✓ Bidirectional conversion successful")
    return True


def test_invalid_conversions(project_dir: Path):
    """Test that invalid conversions are rejected."""
    print("\n=== Testing invalid conversions ===")
    
    # Create a task
    ret, out, err = run_command([
        "aitrackdown", "create", "task", "Test invalid conversion"
    ], cwd=project_dir)
    
    task_id = None
    for line in out.split('\n'):
        if 'TSK-' in line:
            import re
            match = re.search(r'TSK-\d+', line)
            if match:
                task_id = match.group()
                break
    
    # Try invalid conversion: task -> epic (should fail)
    ret, out, err = run_command([
        "aitrackdown", "convert", task_id, "--to", "epic"
    ], cwd=project_dir)
    
    if ret == 0:
        print("ERROR: Task to Epic conversion should have failed")
        return False
    
    print("✓ Invalid conversion (TSK -> EP) correctly rejected")
    
    # Try converting to same type (should be no-op)
    ret, out, err = run_command([
        "aitrackdown", "convert", task_id, "--to", "task"
    ], cwd=project_dir)
    
    if ret != 0 or "already a task" not in (out + err).lower():
        print("ERROR: Same-type conversion not handled correctly")
        return False
    
    print("✓ Same-type conversion correctly handled")
    
    return True


def test_no_archive_option(project_dir: Path):
    """Test conversion without archiving."""
    print("\n=== Testing --no-archive option ===")
    
    # Create a task
    ret, out, err = run_command([
        "aitrackdown", "create", "task", "Test no-archive conversion"
    ], cwd=project_dir)
    
    task_id = None
    for line in out.split('\n'):
        if 'TSK-' in line:
            import re
            match = re.search(r'TSK-\d+', line)
            if match:
                task_id = match.group()
                break
    
    print(f"Created task: {task_id}")
    
    # Convert with --no-archive
    ret, out, err = run_command([
        "aitrackdown", "convert", task_id, "--to", "issue", "--no-archive"
    ], cwd=project_dir)
    
    if ret != 0:
        print(f"Failed to convert with --no-archive: {err}")
        return False
    
    # Verify original is NOT archived
    archive_file = project_dir / "tickets" / "tasks" / "archive" / f"{task_id}.md"
    if archive_file.exists():
        print(f"Task should not be archived with --no-archive: {archive_file}")
        return False
    
    # Verify original is deleted
    original_file = project_dir / "tickets" / "tasks" / f"{task_id}.md"
    if original_file.exists():
        print(f"Original task should be deleted: {original_file}")
        return False
    
    print("✓ --no-archive option works correctly")
    return True


def main():
    """Run all conversion tests."""
    print("=== Testing Ticket Type Conversion Feature ===")
    
    # Create test project
    project_dir = create_test_project()
    if not project_dir:
        print("Failed to create test project")
        return 1
    
    try:
        # Run tests
        tests = [
            test_task_to_issue_conversion,
            test_issue_to_epic_conversion,
            test_bidirectional_conversion,
            test_invalid_conversions,
            test_no_archive_option,
        ]
        
        results = []
        for test_func in tests:
            try:
                success = test_func(project_dir)
                results.append(success)
            except Exception as e:
                print(f"Test {test_func.__name__} failed with exception: {e}")
                results.append(False)
        
        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        
        passed = sum(1 for r in results if r)
        total = len(results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if all(results):
            print("\n✅ All tests passed!")
            return 0
        else:
            print("\n❌ Some tests failed")
            return 1
            
    finally:
        # Clean up
        import shutil
        if project_dir.parent.exists():
            shutil.rmtree(project_dir.parent)
            print(f"\nCleaned up test project")


if __name__ == "__main__":
    sys.exit(main())