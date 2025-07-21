#!/usr/bin/env python3
"""
Calculate SHA256 for AI Trackdown PyTools package for Homebrew formula.

This script downloads the package from PyPI and calculates the SHA256 hash
needed for the Homebrew formula.
"""

import hashlib
import sys
import urllib.request
from pathlib import Path


def calculate_sha256(url: str, filename: str) -> str:
    """Download file and calculate SHA256 hash."""
    print(f"Downloading {url}...")
    
    try:
        # Download the file
        urllib.request.urlretrieve(url, filename)
        print(f"Downloaded to {filename}")
        
        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        with open(filename, "rb") as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return ""


def main():
    """Main function to calculate SHA256 for the package."""
    # Package information
    package_name = "ai-trackdown-pytools"
    version = "0.9.0"
    
    # PyPI URL for the source distribution
    url = f"https://files.pythonhosted.org/packages/source/a/{package_name}/{package_name}-{version}.tar.gz"
    filename = f"{package_name}-{version}.tar.gz"
    
    print(f"Calculating SHA256 for {package_name} v{version}")
    print("=" * 50)
    
    # Calculate SHA256
    sha256 = calculate_sha256(url, filename)
    
    if sha256:
        print(f"\nSHA256: {sha256}")
        print("\nUpdate your Homebrew formula with this SHA256:")
        print(f'sha256 "{sha256}"')
        
        # Optionally clean up downloaded file
        try:
            Path(filename).unlink()
            print(f"\nCleaned up {filename}")
        except Exception:
            print(f"\nNote: {filename} left in current directory")
            
    else:
        print("Failed to calculate SHA256", file=sys.stderr)
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main())