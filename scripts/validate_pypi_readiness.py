#!/usr/bin/env python3
"""Validate PyPI readiness for ai-trackdown-pytools.

This script performs comprehensive checks to ensure the package is ready for PyPI publication.
"""

import subprocess
import sys
import os
from pathlib import Path
import json
import toml


def run_command(cmd, capture=True):
    """Run a command and return result."""
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    if capture:
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    else:
        return subprocess.run(cmd).returncode == 0, "", ""


def check_dist_files():
    """Check if distribution files exist."""
    print("\n📦 Checking distribution files...")
    
    dist_dir = Path("dist")
    if not dist_dir.exists():
        print("  ❌ dist/ directory not found")
        return False
    
    wheel_files = list(dist_dir.glob("*.whl"))
    tar_files = list(dist_dir.glob("*.tar.gz"))
    
    if not wheel_files:
        print("  ❌ No wheel file found")
        return False
    
    if not tar_files:
        print("  ❌ No source distribution found")
        return False
    
    print(f"  ✅ Wheel: {wheel_files[0].name}")
    print(f"  ✅ Source: {tar_files[0].name}")
    return True


def check_version_consistency():
    """Check version consistency across files."""
    print("\n🔢 Checking version consistency...")
    
    # Read pyproject.toml version
    with open("pyproject.toml", "r") as f:
        data = toml.load(f)
        pyproject_version = data["project"]["version"]
    
    # Read __init__.py for version
    init_file = Path("src/ai_trackdown_pytools/__init__.py")
    version_py = None
    if init_file.exists():
        with open(init_file, "r") as f:
            for line in f:
                if "__version__" in line and '"' in line and "=" in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        version_py = parts[1]
                        break
    
    print(f"  📄 pyproject.toml: {pyproject_version}")
    if version_py:
        print(f"  📄 __init__.py: {version_py}")
        if version_py != pyproject_version:
            print("  ❌ Version mismatch!")
            return False
    
    # Check dist file versions
    dist_versions = set()
    dist_dir = Path("dist")
    if dist_dir.exists():
        for file in dist_dir.glob("ai_trackdown_pytools-*.whl"):
            # Extract version from filename like ai_trackdown_pytools-1.0.0-py3-none-any.whl
            parts = file.stem.split("-")  # stem removes .whl extension
            if len(parts) >= 2:
                dist_versions.add(parts[1])
        
        for file in dist_dir.glob("ai_trackdown_pytools-*.tar.gz"):
            # Extract version from filename like ai_trackdown_pytools-1.0.0.tar.gz
            name_without_ext = file.name.replace(".tar.gz", "")
            parts = name_without_ext.split("-")
            if len(parts) >= 2:
                dist_versions.add(parts[1])
    
    if dist_versions:
        dist_version = dist_versions.pop()
        print(f"  📦 Distribution: {dist_version}")
        if dist_version != pyproject_version:
            print("  ❌ Distribution version mismatch!")
            return False
    
    print("  ✅ All versions consistent")
    return True


def check_twine_validation():
    """Run twine check on distribution files."""
    print("\n🔍 Running twine validation...")
    
    success, stdout, stderr = run_command("twine check dist/*")
    
    if success:
        print("  ✅ Twine validation passed")
        if stdout:
            for line in stdout.strip().split("\n"):
                print(f"     {line}")
        return True
    else:
        print("  ❌ Twine validation failed")
        if stderr:
            print(f"     Error: {stderr}")
        return False


def check_required_files():
    """Check if all required files exist."""
    print("\n📋 Checking required files...")
    
    required_files = [
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "pyproject.toml",
        "setup.py",
        "MANIFEST.in"
    ]
    
    all_exist = True
    for file in required_files:
        if Path(file).exists():
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MISSING")
            all_exist = False
    
    return all_exist


def check_package_metadata():
    """Check package metadata completeness."""
    print("\n📝 Checking package metadata...")
    
    with open("pyproject.toml", "r") as f:
        data = toml.load(f)
        project = data.get("project", {})
    
    required_fields = [
        "name",
        "version",
        "description",
        "authors",
        "readme",
        "license",
        "classifiers",
        "dependencies"
    ]
    
    all_present = True
    for field in required_fields:
        if field in project:
            print(f"  ✅ {field}: Present")
        else:
            print(f"  ❌ {field}: MISSING")
            all_present = False
    
    # Check URLs
    urls = project.get("urls", {})
    if urls:
        print("  ✅ Project URLs defined:")
        for key, url in urls.items():
            print(f"     - {key}: {url}")
    else:
        print("  ⚠️  No project URLs defined")
    
    return all_present


def check_python_compatibility():
    """Check Python version compatibility."""
    print("\n🐍 Checking Python compatibility...")
    
    with open("pyproject.toml", "r") as f:
        data = toml.load(f)
        requires_python = data["project"].get("requires-python", "")
    
    print(f"  📋 Requires Python: {requires_python}")
    
    current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    print(f"  🖥️  Current Python: {current_version}")
    
    return True


def check_dependencies():
    """Check if all dependencies are properly specified."""
    print("\n📚 Checking dependencies...")
    
    with open("pyproject.toml", "r") as f:
        data = toml.load(f)
        deps = data["project"].get("dependencies", [])
    
    print(f"  📦 {len(deps)} runtime dependencies")
    
    # Check for optional dependencies
    optional = data["project"].get("optional-dependencies", {})
    if optional:
        print("  📦 Optional dependency groups:")
        for group, deps in optional.items():
            print(f"     - {group}: {len(deps)} dependencies")
    
    return True


def check_entry_points():
    """Check console script entry points."""
    print("\n🚀 Checking entry points...")
    
    with open("pyproject.toml", "r") as f:
        data = toml.load(f)
        scripts = data["project"].get("scripts", {})
    
    if scripts:
        print(f"  ✅ {len(scripts)} console scripts defined:")
        for name, target in scripts.items():
            print(f"     - {name} → {target}")
        return True
    else:
        print("  ⚠️  No console scripts defined")
        return False


def main():
    """Run all validation checks."""
    print("🔍 PyPI Publishing Readiness Check")
    print("=" * 50)
    
    checks = [
        ("Distribution Files", check_dist_files),
        ("Version Consistency", check_version_consistency),
        ("Twine Validation", check_twine_validation),
        ("Required Files", check_required_files),
        ("Package Metadata", check_package_metadata),
        ("Python Compatibility", check_python_compatibility),
        ("Dependencies", check_dependencies),
        ("Entry Points", check_entry_points),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Package is ready for PyPI publication!")
        print("\nNext steps:")
        print("1. Review docs/pypi/PYPI_MANUAL_PUBLISHING_GUIDE.md")
        print("2. Set up PyPI API token")
        print("3. Test with: twine upload --repository testpypi dist/*")
        print("4. Publish with: twine upload dist/*")
    else:
        print("\n⚠️  Package needs attention before publishing")
        print("Please fix the failed checks above.")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())