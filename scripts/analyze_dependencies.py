#!/usr/bin/env python3
"""Analyze and report dependency issues in the project."""

import sys
import json
import tomllib
from pathlib import Path
from typing import Dict, List, Tuple, Set

def load_pyproject():
    """Load pyproject.toml file."""
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        return tomllib.load(f)

def analyze_dependencies(data: dict) -> Dict[str, List[str]]:
    """Analyze dependencies for issues."""
    issues = {
        "version_conflicts": [],
        "security_concerns": [],
        "redundant_deps": [],
        "missing_constraints": [],
        "python_compat": []
    }
    
    # Core dependencies
    core_deps = data["project"]["dependencies"]
    
    # Check for known issues
    dep_map = {}
    for dep in core_deps:
        if ">=" in dep:
            name, version = dep.split(">=")
            dep_map[name] = version
        elif ">" in dep:
            name, version = dep.split(">")
            dep_map[name] = version
        else:
            issues["missing_constraints"].append(f"{dep} - No version constraint")
    
    # Known issues to fix
    
    # 1. Click and Typer conflict
    if "click" in dep_map and "typer" in dep_map:
        issues["version_conflicts"].append(
            "Click and Typer both present - Typer includes Click, remove direct Click dependency"
        )
    
    # 2. aiohttp version too old for Python 3.12
    if "aiohttp" in dep_map:
        if dep_map["aiohttp"] < "3.9.0":
            issues["python_compat"].append(
                "aiohttp>=3.8.0 may have issues with Python 3.12, update to >=3.9.0"
            )
    
    # 3. GitPython security issue
    if "gitpython" in dep_map:
        if dep_map["gitpython"] < "3.1.40":
            issues["security_concerns"].append(
                "GitPython<3.1.40 has known security vulnerabilities"
            )
    
    # 4. Missing upper bounds for stability
    for name, version in dep_map.items():
        if name in ["pydantic", "aiohttp", "jinja2"]:
            issues["missing_constraints"].append(
                f"{name}>={version} should have upper bound for stability (e.g., {name}>={version},<{int(version.split('.')[0])+1}.0.0)"
            )
    
    # Check optional dependencies
    opt_deps = data["project"].get("optional-dependencies", {})
    
    # Check for duplicates in dev dependencies
    dev_deps = opt_deps.get("dev", [])
    test_deps = opt_deps.get("test", [])
    
    dev_packages = set()
    for dep in dev_deps:
        pkg_name = dep.split(">=")[0].split(">")[0].split("[")[0]
        dev_packages.add(pkg_name)
    
    test_packages = set()
    for dep in test_deps:
        pkg_name = dep.split(">=")[0].split(">")[0].split("[")[0]
        test_packages.add(pkg_name)
    
    duplicates = dev_packages & test_packages
    if duplicates:
        issues["redundant_deps"].append(
            f"Duplicated in dev and test: {', '.join(duplicates)}"
        )
    
    return issues

def main():
    """Main analysis function."""
    print("Analyzing dependencies in pyproject.toml...\n")
    
    try:
        data = load_pyproject()
        issues = analyze_dependencies(data)
        
        print("=" * 60)
        print("DEPENDENCY ANALYSIS REPORT")
        print("=" * 60)
        
        has_issues = False
        for category, items in issues.items():
            if items:
                has_issues = True
                print(f"\n{category.upper().replace('_', ' ')}:")
                for item in items:
                    print(f"  - {item}")
        
        if not has_issues:
            print("\n✓ No dependency issues found!")
        else:
            print("\n" + "=" * 60)
            print("RECOMMENDATIONS:")
            print("=" * 60)
            print("""
1. Remove Click dependency (Typer includes it)
2. Update aiohttp to >=3.9.0 for Python 3.12 support
3. Update GitPython to >=3.1.40 for security
4. Add upper bounds to major dependencies
5. Consolidate duplicate dev/test dependencies
6. Consider using dependency groups for optional adapters
""")
        
        return 0 if not has_issues else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())