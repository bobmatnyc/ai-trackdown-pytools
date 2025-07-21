#!/usr/bin/env python3
"""Test script to verify VERSION file is the single source of truth."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def test_version_consistency():
    """Test that all version references use VERSION file."""
    # Read VERSION file
    version_file = Path(__file__).parent.parent / "VERSION"
    version_from_file = version_file.read_text().strip()
    print(f"✓ VERSION file exists: {version_from_file}")
    
    # Import module and check version
    import ai_trackdown_pytools
    module_version = ai_trackdown_pytools.__version__
    print(f"✓ Module version: {module_version}")
    
    # Check they match
    if version_from_file == module_version:
        print(f"✅ Version consistency verified: {version_from_file}")
    else:
        print(f"❌ Version mismatch!")
        print(f"   VERSION file: {version_from_file}")
        print(f"   Module: {module_version}")
        return False
    
    # Test version.py functions
    from ai_trackdown_pytools.version import get_version, get_version_info, CURRENT_VERSION
    
    if get_version() == version_from_file:
        print(f"✓ get_version() returns: {get_version()}")
    else:
        print(f"❌ get_version() mismatch: {get_version()}")
        return False
    
    version_info = get_version_info()
    if str(version_info) == version_from_file:
        print(f"✓ get_version_info() returns: {version_info}")
    else:
        print(f"❌ get_version_info() mismatch: {version_info}")
        return False
    
    if str(CURRENT_VERSION) == version_from_file:
        print(f"✓ CURRENT_VERSION is: {CURRENT_VERSION}")
    else:
        print(f"❌ CURRENT_VERSION mismatch: {CURRENT_VERSION}")
        return False
    
    print("\n✅ All version references use VERSION file as single source of truth!")
    return True

if __name__ == "__main__":
    success = test_version_consistency()
    sys.exit(0 if success else 1)