#!/usr/bin/env python3
"""Test PyPI upload script for ai-trackdown-pytools.

This script helps test the PyPI upload process using test.pypi.org
"""

import subprocess
import sys
import os
from pathlib import Path


def check_twine():
    """Check if twine is installed."""
    try:
        subprocess.run(["twine", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Twine is not installed. Please run: pip install twine")
        return False


def check_dist_files():
    """Check if distribution files exist."""
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("❌ No dist/ directory found. Please build the package first.")
        return False
    
    files = list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz"))
    if not files:
        print("❌ No distribution files found in dist/")
        return False
    
    print("📦 Found distribution files:")
    for f in files:
        print(f"   - {f.name}")
    return True


def check_pypirc():
    """Check if .pypirc file exists with test PyPI configuration."""
    pypirc_path = Path.home() / ".pypirc"
    if not pypirc_path.exists():
        print("⚠️  No ~/.pypirc file found.")
        print("\nYou'll need to create ~/.pypirc with this content:")
        print("""
[distutils]
index-servers =
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <your-test-pypi-token>
""")
        return False
    
    # Check if testpypi is configured
    with open(pypirc_path, 'r') as f:
        content = f.read()
        if 'testpypi' not in content:
            print("⚠️  No testpypi configuration found in ~/.pypirc")
            return False
    
    print("✅ ~/.pypirc configured for testpypi")
    return True


def upload_to_test_pypi():
    """Upload packages to test PyPI."""
    print("\n🚀 Uploading to test.pypi.org...")
    print("=" * 50)
    
    cmd = ["twine", "upload", "--repository", "testpypi", "dist/*"]
    
    # Check if we should use environment variables instead
    if os.environ.get("TWINE_USERNAME") and os.environ.get("TWINE_PASSWORD"):
        print("📝 Using environment variables for authentication")
    
    print(f"Running: {' '.join(cmd)}")
    print("\nNote: You'll be prompted for authentication if not configured.\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ Upload successful!")
        print("\nTo test installation:")
        print("pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ai-trackdown-pytools")
    else:
        print("\n❌ Upload failed!")
        print("\nCommon issues:")
        print("1. Invalid token - regenerate at https://test.pypi.org/manage/account/token/")
        print("2. Version already exists - increment version number")
        print("3. Network issues - check your connection")
    
    return result.returncode == 0


def main():
    """Main function."""
    print("🧪 Test PyPI Upload Helper")
    print("=" * 50)
    
    # Run checks
    if not check_twine():
        return 1
    
    if not check_dist_files():
        return 1
    
    # Check for configuration
    has_pypirc = check_pypirc()
    has_env_vars = bool(os.environ.get("TWINE_USERNAME") and os.environ.get("TWINE_PASSWORD"))
    
    if not has_pypirc and not has_env_vars:
        print("\n⚠️  No authentication configured!")
        print("\nOptions:")
        print("1. Create ~/.pypirc file (see above)")
        print("2. Set environment variables:")
        print("   export TWINE_USERNAME=__token__")
        print("   export TWINE_PASSWORD=<your-token>")
        print("3. Use interactive authentication (you'll be prompted)")
        
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            return 1
    
    # Perform upload
    if upload_to_test_pypi():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())