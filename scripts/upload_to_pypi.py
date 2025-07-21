#!/usr/bin/env python3
"""
Script to upload AI Trackdown PyTools to PyPI.

This script provides instructions and automation for uploading
the package to PyPI after manual authentication setup.
"""
import os
import subprocess
import sys
import hashlib
from pathlib import Path


def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def main():
    """Main function to guide PyPI upload process."""
    print("AI Trackdown PyTools - PyPI Upload Script")
    print("=" * 50)
    
    # Check if we're in the correct directory
    if not os.path.exists("pyproject.toml"):
        print("Error: pyproject.toml not found. Please run this script from the project root.")
        sys.exit(1)
    
    # Check if dist directory exists
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("Error: dist/ directory not found. Please run 'python -m build' first.")
        sys.exit(1)
    
    # List distribution files
    dist_files = list(dist_dir.glob("*.whl")) + list(dist_dir.glob("*.tar.gz"))
    if not dist_files:
        print("Error: No distribution files found. Please run 'python -m build' first.")
        sys.exit(1)
    
    print(f"Found {len(dist_files)} distribution files:")
    for file in dist_files:
        size_kb = file.stat().st_size / 1024
        sha256 = calculate_sha256(file)
        print(f"  - {file.name} ({size_kb:.1f} KB)")
        print(f"    SHA256: {sha256}")
        print()
    
    print("\nPyPI Upload Instructions:")
    print("-" * 30)
    print("1. Set up PyPI API token:")
    print("   - Go to https://pypi.org/manage/account/token/")
    print("   - Create a new API token")
    print("   - Copy the token (starts with 'pypi-')")
    print()
    print("2. Configure credentials:")
    print("   Option A - Environment variable:")
    print("   export TWINE_PASSWORD='your-api-token'")
    print("   export TWINE_USERNAME='__token__'")
    print()
    print("   Option B - ~/.pypirc file:")
    print("   [pypi]")
    print("   username = __token__")
    print("   password = your-api-token")
    print()
    print("3. Upload to PyPI:")
    print("   twine upload dist/*")
    print()
    print("4. Test installation:")
    print("   pip install ai-trackdown-pytools")
    print()
    
    # Offer to run upload if credentials are available
    if os.getenv("TWINE_PASSWORD") or os.path.exists(os.path.expanduser("~/.pypirc")):
        response = input("Credentials detected. Would you like to upload now? (y/N): ")
        if response.lower() == 'y':
            print("Uploading to PyPI...")
            try:
                result = subprocess.run(
                    ["twine", "upload", "dist/*"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                print("Upload successful!")
                print(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"Upload failed: {e}")
                print(f"stderr: {e.stderr}")
                sys.exit(1)
    
    print("\nHomebrew Formula SHA256 Hash:")
    print("-" * 30)
    tar_files = list(dist_dir.glob("*.tar.gz"))
    if tar_files:
        tar_file = tar_files[0]
        sha256 = calculate_sha256(tar_file)
        print(f"Source distribution: {tar_file.name}")
        print(f"SHA256: {sha256}")
        print(f"Size: {tar_file.stat().st_size} bytes")
        print(f"\nUpdate Homebrew formula with:")
        print(f'  url "https://files.pythonhosted.org/packages/source/a/ai-trackdown-pytools/{tar_file.name}"')
        print(f'  sha256 "{sha256}"')


if __name__ == "__main__":
    main()