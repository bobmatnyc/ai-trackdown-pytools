#!/usr/bin/env python3
"""Test script for issue add-task and remove-task commands."""

import subprocess
import sys

def run_command(cmd):
    """Run a command and return stdout, stderr, and return code."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout, result.stderr, result.returncode

def main():
    print("Testing issue add-task and remove-task commands...")
    
    # Create test issue
    print("\n1. Creating test issue...")
    stdout, stderr, rc = run_command("aitrackdown issue create 'Test Issue for Subtasks' --type feature")
    if rc != 0:
        print(f"Failed to create issue: {stderr}")
        return 1
    
    # Extract issue ID from output
    issue_id = None
    for line in stdout.split('\n'):
        if 'ID:' in line and 'ISS-' in line:
            issue_id = line.split('ISS-')[1].split()[0]
            issue_id = f"ISS-{issue_id}"
            break
    
    if not issue_id:
        print("Failed to extract issue ID from output")
        return 1
    
    print(f"Created issue: {issue_id}")
    
    # Create test tasks
    print("\n2. Creating test tasks...")
    task_ids = []
    for i in range(3):
        stdout, stderr, rc = run_command(f"aitrackdown create 'Test Task {i+1}' --tag test")
        if rc != 0:
            print(f"Failed to create task {i+1}: {stderr}")
            return 1
        
        # Extract task ID
        for line in stdout.split('\n'):
            if 'ID:' in line and 'TSK-' in line:
                task_id = line.split('TSK-')[1].split()[0]
                task_id = f"TSK-{task_id}"
                task_ids.append(task_id)
                break
    
    print(f"Created tasks: {', '.join(task_ids)}")
    
    # Test add-task command
    print(f"\n3. Adding tasks to issue {issue_id}...")
    cmd = f"aitrackdown issue add-task {issue_id} {' '.join(task_ids)}"
    stdout, stderr, rc = run_command(cmd)
    if rc != 0:
        print(f"Failed to add tasks: {stderr}")
        return 1
    print(stdout)
    
    # Verify tasks were added
    print(f"\n4. Verifying issue shows subtasks...")
    stdout, stderr, rc = run_command(f"aitrackdown issue show {issue_id}")
    if rc != 0:
        print(f"Failed to show issue: {stderr}")
        return 1
    print(stdout)
    
    # Verify task shows parent
    print(f"\n5. Verifying task shows parent...")
    stdout, stderr, rc = run_command(f"aitrackdown show {task_ids[0]}")
    if rc != 0:
        print(f"Failed to show task: {stderr}")
        return 1
    print(stdout)
    
    # Test remove-task command
    print(f"\n6. Removing one task from issue...")
    stdout, stderr, rc = run_command(f"aitrackdown issue remove-task {issue_id} {task_ids[0]}")
    if rc != 0:
        print(f"Failed to remove task: {stderr}")
        return 1
    print(stdout)
    
    # Verify task was removed
    print(f"\n7. Verifying issue updated...")
    stdout, stderr, rc = run_command(f"aitrackdown issue show {issue_id} --detailed")
    if rc != 0:
        print(f"Failed to show issue: {stderr}")
        return 1
    print(stdout)
    
    # Test error cases
    print(f"\n8. Testing error cases...")
    
    # Try to add non-existent task
    stdout, stderr, rc = run_command(f"aitrackdown issue add-task {issue_id} TSK-99999")
    print(f"Adding non-existent task: {stdout}")
    
    # Try to remove task not linked to issue
    stdout, stderr, rc = run_command(f"aitrackdown issue remove-task {issue_id} {task_ids[0]}")
    print(f"Removing already removed task: {stdout}")
    
    print("\n✅ All tests completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())