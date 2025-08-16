#!/usr/bin/env python3
"""Example script demonstrating ticket type conversion functionality.

This example shows how to use the new ticket conversion feature that allows
converting tickets between different types while preserving all metadata.

Supported conversions:
- TSK <-> ISS (Task to/from Issue)
- ISS <-> EP (Issue to/from Epic)

Usage:
    python examples/ticket_conversion_example.py
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: str):
    """Run a shell command and print the output."""
    print(f"\n$ {cmd}")
    print("-" * 60)
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main():
    """Demonstrate ticket conversion functionality."""
    
    print("=" * 70)
    print("TICKET TYPE CONVERSION EXAMPLE")
    print("=" * 70)
    
    # Check if we're in an AI Trackdown project
    if not Path(".ai-trackdown").exists():
        print("\n⚠️  This example must be run from an AI Trackdown project directory.")
        print("Please run 'aitrackdown init project' first.")
        return 1
    
    print("\n## 1. Creating Example Tickets\n")
    
    # Create a task
    print("Creating a task that we'll convert to an issue...")
    run_command(
        'aitrackdown create task "Implement user authentication" '
        '--description "Add OAuth2 authentication support" '
        '--priority high '
        '--tags security,backend'
    )
    
    # Create an issue
    print("\nCreating an issue that we'll convert to an epic...")
    run_command(
        'aitrackdown create issue "Performance optimization needed" '
        '--description "Application is running slowly under load" '
        '--priority critical'
    )
    
    # Create an epic
    print("\nCreating an epic that we'll convert to an issue...")
    run_command(
        'aitrackdown create epic "Q1 Feature Roadmap" '
        '--description "Major features planned for Q1 2025"'
    )
    
    print("\n## 2. Converting Tickets\n")
    
    # Convert task to issue
    print("Converting TSK-0001 (task) to an issue...")
    run_command("aitrackdown convert TSK-0001 --to issue")
    
    # Convert issue to epic
    print("\nConverting ISS-0001 (issue) to an epic...")
    run_command("aitrackdown convert ISS-0001 --to epic")
    
    # Convert epic to issue
    print("\nConverting EP-0001 (epic) back to an issue...")
    run_command("aitrackdown convert EP-0001 --to issue")
    
    print("\n## 3. Viewing Converted Tickets\n")
    
    # Show the converted tickets
    print("Showing the newly converted issue (was TSK-0001)...")
    run_command("aitrackdown show ISS-0002")
    
    print("\n## 4. Invalid Conversions (These will fail)\n")
    
    # Try invalid conversion
    print("Attempting invalid conversion (task directly to epic)...")
    run_command("aitrackdown create task 'Test invalid conversion'")
    run_command("aitrackdown convert TSK-0002 --to epic")
    
    print("\n## 5. Using --no-archive Option\n")
    
    # Convert without archiving
    print("Converting a task without archiving the original...")
    run_command("aitrackdown create task 'Test no-archive'")
    run_command("aitrackdown convert TSK-0003 --to issue --no-archive")
    
    print("\n## 6. Checking Archive\n")
    
    # List archived tickets
    print("Listing archived tickets...")
    run_command("ls -la tickets/*/archive/")
    
    print("\n" + "=" * 70)
    print("CONVERSION EXAMPLE COMPLETE")
    print("=" * 70)
    print("\nKey Points:")
    print("• Conversions preserve all metadata (title, description, priority, tags, etc.)")
    print("• Original tickets are archived by default (use --no-archive to delete instead)")
    print("• Parent/child relationships are automatically updated")
    print("• Conversion metadata is added to track the conversion history")
    print("• Only valid conversion paths are allowed: TSK <-> ISS <-> EP")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())