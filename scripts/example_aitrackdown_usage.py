#!/usr/bin/env python3
"""
Example script showing how to use the aitrackdown CLI.

This demonstrates the primary CLI command for AI Trackdown Python Tools.
"""

import subprocess
import sys


def main():
    """Example usage of aitrackdown command."""
    print("This script demonstrates using the aitrackdown CLI.")
    print("The aitrackdown command is the primary CLI for this project.\n")
    
    # Show available commands
    print("Available commands:")
    result = subprocess.run(["aitrackdown", "--help"], capture_output=True, text=True)
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
        print("Error: aitrackdown command not found. Please install the package first.")
        sys.exit(1)
    
    print("\nExample usage:")
    print("  aitrackdown init                 # Initialize a new project")
    print("  aitrackdown create 'New feature' # Create a new task")
    print("  aitrackdown status               # Show project status")
    print("  aitrackdown --version            # Show version")


if __name__ == "__main__":
    main()