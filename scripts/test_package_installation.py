#!/usr/bin/env python3
"""Test package installation and functionality.

This script tests that the built package can be installed and works correctly.
"""

import subprocess
import sys
import tempfile
import os
import shutil
from pathlib import Path


def run_command(cmd, cwd=None):
    """Run a command and return output."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd, 
        capture_output=True, 
        text=True, 
        cwd=cwd
    )
    if result.stdout:
        print(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        print(f"STDERR:\n{result.stderr}")
    return result


def test_package_installation():
    """Test package installation in a fresh virtual environment."""
    # Get the project root and dist directory
    project_root = Path(__file__).parent.parent
    dist_dir = project_root / "dist"
    
    # Find the wheel file
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        print("ERROR: No wheel file found in dist/")
        return False
    
    wheel_file = wheel_files[0]
    print(f"\nTesting installation of: {wheel_file.name}")
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\nCreating test environment in: {tmpdir}")
        
        # Create virtual environment
        venv_path = Path(tmpdir) / "test_venv"
        result = run_command([sys.executable, "-m", "venv", str(venv_path)])
        if result.returncode != 0:
            print("ERROR: Failed to create virtual environment")
            return False
        
        # Get python and pip paths
        if sys.platform == "win32":
            python_path = venv_path / "Scripts" / "python.exe"
            pip_path = venv_path / "Scripts" / "pip.exe"
        else:
            python_path = venv_path / "bin" / "python"
            pip_path = venv_path / "bin" / "pip"
        
        # Install the package
        print("\nInstalling package...")
        result = run_command([str(pip_path), "install", str(wheel_file)])
        if result.returncode != 0:
            print("ERROR: Failed to install package")
            return False
        
        # Test imports
        print("\nTesting imports...")
        test_imports = [
            "import ai_trackdown_pytools",
            "from ai_trackdown_pytools import __version__",
            "from ai_trackdown_pytools.cli import main",
            "from ai_trackdown_pytools.core import models",
            "import ai_trackdown_pytools; print(f'Version: {ai_trackdown_pytools.__version__}')"
        ]
        
        for import_test in test_imports:
            print(f"  Testing: {import_test}")
            result = run_command(
                [str(python_path), "-c", import_test]
            )
            if result.returncode != 0:
                print(f"  ERROR: Import failed")
                return False
            print(f"  ✓ Success")
        
        # Test CLI commands
        print("\nTesting CLI commands...")
        cli_tests = [
            ["aitrackdown", "--version"],
            ["aitrackdown", "--help"],
            ["atd", "--version"],
            ["atd", "--help"],
        ]
        
        # Update PATH to include the venv bin directory
        env = os.environ.copy()
        if sys.platform == "win32":
            env["PATH"] = str(venv_path / "Scripts") + os.pathsep + env["PATH"]
        else:
            env["PATH"] = str(venv_path / "bin") + os.pathsep + env["PATH"]
        
        for cmd in cli_tests:
            print(f"  Testing: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            if result.returncode != 0:
                print(f"  ERROR: Command failed")
                print(f"  STDOUT: {result.stdout}")
                print(f"  STDERR: {result.stderr}")
                return False
            print(f"  ✓ Success")
            if "--version" in cmd:
                print(f"    Output: {result.stdout.strip()}")
        
        print("\n✅ All tests passed!")
        return True


if __name__ == "__main__":
    success = test_package_installation()
    sys.exit(0 if success else 1)