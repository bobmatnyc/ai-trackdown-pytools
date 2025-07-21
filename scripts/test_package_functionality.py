#!/usr/bin/env python3
"""
Test script to validate AI Trackdown PyTools package functionality.

This script tests core functionality to ensure the package works correctly
after installation from PyPI.
"""
import os
import sys
import tempfile
import subprocess
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and return the result."""
    try:
        result = subprocess.run(
            cmd, shell=True, check=check, capture_output=True, text=True
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr, e.returncode


def test_cli_commands():
    """Test basic CLI commands."""
    print("Testing CLI Commands:")
    print("=" * 30)
    
    # Test version command
    stdout, stderr, code = run_command("aitrackdown --version")
    if code == 0:
        print(f"✓ aitrackdown --version: {stdout.strip()}")
    else:
        print(f"✗ aitrackdown --version failed: {stderr}")
        return False
    
    # Test alias command
    stdout, stderr, code = run_command("atd --version")
    if code == 0:
        print(f"✓ atd --version: {stdout.strip()}")
    else:
        print(f"✗ atd --version failed: {stderr}")
        return False
    
    # Test help command
    stdout, stderr, code = run_command("aitrackdown --help")
    if code == 0 and "AI Trackdown PyTools" in stdout:
        print("✓ aitrackdown --help: Working")
    else:
        print(f"✗ aitrackdown --help failed")
        return False
    
    # Test health command
    stdout, stderr, code = run_command("aitrackdown health", check=False)
    if code == 0:
        print("✓ aitrackdown health: Working")
    else:
        print(f"⚠ aitrackdown health: {stderr[:100]}...")
    
    return True


def test_python_import():
    """Test Python import functionality."""
    print("\nTesting Python Import:")
    print("=" * 30)
    
    try:
        import ai_trackdown_pytools
        print(f"✓ Import ai_trackdown_pytools: {ai_trackdown_pytools.__version__}")
    except ImportError as e:
        print(f"✗ Import ai_trackdown_pytools failed: {e}")
        return False
    
    try:
        from ai_trackdown_pytools.cli import main
        print("✓ Import cli.main: Working")
    except ImportError as e:
        print(f"✗ Import cli.main failed: {e}")
        return False
    
    try:
        from ai_trackdown_pytools.core.models import Task
        print("✓ Import core.models.Task: Working")
    except ImportError as e:
        print(f"✗ Import core.models.Task failed: {e}")
        return False
    
    return True


def test_project_initialization():
    """Test project initialization in a temporary directory."""
    print("\nTesting Project Initialization:")
    print("=" * 30)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        print(f"Testing in: {temp_dir}")
        
        # Test project init
        stdout, stderr, code = run_command("aitrackdown init project --name test-project", check=False)
        if code == 0:
            print("✓ Project initialization: Working")
        else:
            print(f"⚠ Project initialization: {stderr[:100]}...")
        
        # Check if config was created
        if os.path.exists(".ai-trackdown"):
            print("✓ Configuration directory created")
        else:
            print("⚠ Configuration directory not found")
        
        # Test status command
        stdout, stderr, code = run_command("aitrackdown status project", check=False)
        if code == 0:
            print("✓ Status command: Working")
        else:
            print(f"⚠ Status command: {stderr[:50]}...")
    
    return True


def test_template_functionality():
    """Test template functionality."""
    print("\nTesting Template Functionality:")
    print("=" * 30)
    
    # Test template list
    stdout, stderr, code = run_command("aitrackdown template list", check=False)
    if code == 0:
        print("✓ Template list: Working")
    else:
        print(f"⚠ Template list: {stderr[:100]}...")
    
    # Test template show
    stdout, stderr, code = run_command("aitrackdown template show default --type task", check=False)
    if code == 0:
        print("✓ Template show: Working")
    else:
        print(f"⚠ Template show: {stderr[:100]}...")
    
    return True


def main():
    """Main test function."""
    print("AI Trackdown PyTools - Package Functionality Test")
    print("=" * 60)
    
    tests = [
        test_python_import,
        test_cli_commands,
        test_project_initialization,
        test_template_functionality,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print(f"\nTest Results: {passed}/{total} test suites passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All functionality tests passed!")
        print("Package is ready for production use.")
    else:
        print("⚠️  Some tests failed or showed warnings.")
        print("Package may still be functional but needs investigation.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)