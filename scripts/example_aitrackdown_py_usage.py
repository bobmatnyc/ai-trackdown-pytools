#!/usr/bin/env python3
"""
Example script showing how to use the aitrackdown-py CLI endpoint.

This demonstrates the project-specific CLI command that follows
the Python package naming convention.
"""

import subprocess
import sys


def main():
    """Example usage of aitrackdown-py command."""
    print("This script demonstrates using the aitrackdown-py CLI endpoint.")
    print("The aitrackdown-py command is the preferred CLI for this project.\n")
    
    # Show available commands
    print("Available commands:")
    result = subprocess.run(["aitrackdown-py", "--help"], capture_output=True, text=True)
    if result.returncode == 0:
        # Just show the command list section
        lines = result.stdout.split('\n')
        in_commands = False
        for line in lines:
            if '─ Commands ─' in line:
                in_commands = True
            if in_commands:
                print(line)
    else:
        print("Error: aitrackdown-py command not found. Please install the package first.")
        sys.exit(1)
    
    print("\nExample usage:")
    print("  aitrackdown-py init                 # Initialize a new project")
    print("  aitrackdown-py create 'New feature' # Create a new task")
    print("  aitrackdown-py status               # Show project status")
    print("  aitrackdown-py --version            # Show version")


if __name__ == "__main__":
    main()