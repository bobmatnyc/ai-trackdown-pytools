#!/usr/bin/env python3
"""
Validate Homebrew formula for AI Trackdown PyTools.

This script checks the formula file for common issues and validates
the structure against Homebrew requirements.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class FormulaValidator:
    """Validator for Homebrew formula files."""
    
    def __init__(self, formula_path: str):
        self.formula_path = Path(formula_path)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def validate(self) -> bool:
        """Run all validation checks."""
        print(f"Validating Homebrew formula: {self.formula_path}")
        print("=" * 50)
        
        if not self.formula_path.exists():
            self.errors.append(f"Formula file not found: {self.formula_path}")
            return False
            
        content = self.formula_path.read_text()
        
        # Run validation checks
        self._validate_class_name(content)
        self._validate_required_fields(content)
        self._validate_urls(content)
        self._validate_dependencies(content)
        self._validate_install_method(content)
        self._validate_test_block(content)
        self._validate_syntax(content)
        
        # Report results
        self._report_results()
        
        return len(self.errors) == 0
        
    def _validate_class_name(self, content: str) -> None:
        """Validate the formula class name."""
        class_match = re.search(r'class\s+(\w+)\s+<\s+Formula', content)
        if not class_match:
            self.errors.append("No Formula class found")
            return
            
        class_name = class_match.group(1)
        expected_name = "AiTrackdownPytools"
        
        if class_name != expected_name:
            self.warnings.append(f"Class name '{class_name}' doesn't match expected '{expected_name}'")
            
    def _validate_required_fields(self, content: str) -> None:
        """Validate required formula fields."""
        required_fields = [
            ('desc', r'desc\s+"([^"]+)"'),
            ('homepage', r'homepage\s+"([^"]+)"'),
            ('url', r'url\s+"([^"]+)"'),
            ('sha256', r'sha256\s+"([^"]+)"'),
            ('license', r'license\s+"([^"]+)"'),
        ]
        
        for field_name, pattern in required_fields:
            if not re.search(pattern, content):
                self.errors.append(f"Missing required field: {field_name}")
            elif field_name == "sha256" and "PLACEHOLDER_SHA256" in content:
                self.warnings.append("SHA256 is still placeholder - update before publishing")
                
    def _validate_urls(self, content: str) -> None:
        """Validate URLs in the formula."""
        url_match = re.search(r'url\s+"([^"]+)"', content)
        homepage_match = re.search(r'homepage\s+"([^"]+)"', content)
        
        if url_match:
            url = url_match.group(1)
            if not url.startswith("https://files.pythonhosted.org/"):
                self.warnings.append("URL should point to PyPI files.pythonhosted.org")
                
        if homepage_match:
            homepage = homepage_match.group(1)
            if not homepage.startswith("https://github.com/"):
                self.warnings.append("Homepage should be a GitHub URL")
                
    def _validate_dependencies(self, content: str) -> None:
        """Validate Python dependencies."""
        if 'depends_on "python@3.11"' not in content:
            self.errors.append("Missing Python dependency")
            
        # Check for common Python dependencies
        expected_resources = [
            "click", "pydantic", "pyyaml", "gitpython", "rich", 
            "typer", "jinja2", "jsonschema", "toml", "pathspec"
        ]
        
        for resource in expected_resources:
            if f'resource "{resource}"' not in content:
                self.warnings.append(f"Missing resource: {resource}")
                
    def _validate_install_method(self, content: str) -> None:
        """Validate install method."""
        if "include Language::Python::Virtualenv" not in content:
            self.errors.append("Missing Python virtualenv include")
            
        if "virtualenv_install_with_resources" not in content:
            self.errors.append("Missing virtualenv_install_with_resources call")
            
        # Check for shell completions
        if "generate_completions_from_executable" not in content:
            self.warnings.append("No shell completions configured")
            
    def _validate_test_block(self, content: str) -> None:
        """Validate test block."""
        if "test do" not in content:
            self.errors.append("Missing test block")
            return
            
        # Check for basic tests
        test_checks = [
            ("--version", "version check"),
            ("--help", "help check"),
            ("init", "init functionality"),
        ]
        
        for test_cmd, description in test_checks:
            if test_cmd not in content:
                self.warnings.append(f"Missing test for {description}")
                
    def _validate_syntax(self, content: str) -> None:
        """Validate Ruby syntax basics."""
        # Check for balanced quotes
        double_quotes = content.count('"')
        if double_quotes % 2 != 0:
            self.errors.append("Unbalanced double quotes")
            
        # Check for balanced blocks - account for class, def, and do blocks
        lines = content.split('\n')
        stack = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if (stripped.endswith(' do') or 
                stripped.startswith('def ') or 
                (stripped.startswith('class ') and ' < ' in stripped)):
                stack.append(i)
            elif stripped == 'end':
                if not stack:
                    self.errors.append(f"Line {i}: 'end' without matching 'class', 'do' or 'def'")
                else:
                    stack.pop()
        
        if stack:
            self.errors.append(f"Unmatched 'class', 'do' or 'def' blocks at lines: {stack}")
            
        # Check indentation consistency
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if stripped and not line.startswith('  ') and not line.startswith('#') and i > 1:
                # Allow class/def/end at root level
                if not any(stripped.startswith(keyword) for keyword in ['class', 'def', 'end', 'resource']):
                    if not re.match(r'^\s*(desc|homepage|url|sha256|license|depends_on)', line):
                        self.warnings.append(f"Line {i}: Inconsistent indentation")
                        
    def _report_results(self) -> None:
        """Report validation results."""
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  • {error}")
                
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
                
        if not self.errors and not self.warnings:
            print("\n✅ Formula validation passed!")
        elif not self.errors:
            print(f"\n✅ Formula validation passed with {len(self.warnings)} warnings")
        else:
            print(f"\n❌ Formula validation failed with {len(self.errors)} errors and {len(self.warnings)} warnings")


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python validate_homebrew_formula.py <formula_file>")
        return 1
        
    formula_path = sys.argv[1]
    validator = FormulaValidator(formula_path)
    
    if validator.validate():
        print("\n🎉 Ready for Homebrew tap!")
        return 0
    else:
        print("\n🔧 Please fix errors before publishing")
        return 1


if __name__ == "__main__":
    sys.exit(main())