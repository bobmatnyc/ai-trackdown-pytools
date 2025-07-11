#!/usr/bin/env python3
"""
AI Trackdown PyTools - CI/CD Coverage Integration

This script provides CI/CD integration for coverage reporting including
GitHub Actions, GitLab CI, and generic CI/CD platform support.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET


class CICoverageIntegration:
    """CI/CD coverage integration handler."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.ci_platform = self._detect_ci_platform()
        
    def _detect_ci_platform(self) -> str:
        """Detect the current CI/CD platform."""
        if os.getenv("GITHUB_ACTIONS"):
            return "github"
        elif os.getenv("GITLAB_CI"):
            return "gitlab"
        elif os.getenv("JENKINS_URL"):
            return "jenkins"
        elif os.getenv("TRAVIS"):
            return "travis"
        elif os.getenv("CIRCLECI"):
            return "circleci"
        elif os.getenv("AZURE_PIPELINES"):
            return "azure"
        else:
            return "generic"
    
    def run_coverage_for_ci(self, 
                          fail_under: float = 85.0,
                          upload_to_codecov: bool = False,
                          upload_to_coveralls: bool = False,
                          generate_badges: bool = True) -> Dict:
        """Run coverage analysis optimized for CI/CD environments."""
        print(f"🤖 Running coverage analysis for {self.ci_platform.upper()} CI")
        
        # Run tests with coverage
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=ai_trackdown_pytools",
            "--cov-branch",
            f"--cov-fail-under={fail_under}",
            "--cov-report=term-missing",
            "--cov-report=xml:coverage.xml",
            "--cov-report=json:coverage.json",
            "--cov-report=lcov:coverage.lcov",
            "--cov-report=html:htmlcov",
            "--junitxml=test-results.xml",
            "--tb=short",
            "-q",
        ]
        
        print(f"🚀 Executing: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parse coverage results
            coverage_data = self._parse_coverage_results()
            
            # Generate CI-specific outputs
            ci_outputs = {
                "coverage_data": coverage_data,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
            
            # Platform-specific integrations
            if self.ci_platform == "github":
                ci_outputs.update(self._github_integration(coverage_data))
            elif self.ci_platform == "gitlab":
                ci_outputs.update(self._gitlab_integration(coverage_data))
            
            # External service uploads
            if upload_to_codecov:
                self._upload_to_codecov()
            
            if upload_to_coveralls:
                self._upload_to_coveralls()
            
            if generate_badges:
                self._generate_ci_badges(coverage_data)
            
            # Set CI status
            self._set_ci_status(coverage_data, result.returncode == 0)
            
            return ci_outputs
            
        except Exception as e:
            print(f"❌ CI coverage analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_coverage_results(self) -> Dict:
        """Parse coverage results from generated reports."""
        coverage_data = {}
        
        # Parse JSON coverage report
        json_path = self.project_root / "coverage.json"
        if json_path.exists():
            with open(json_path, "r") as f:
                data = json.load(f)
                totals = data.get("totals", {})
                coverage_data.update({
                    "line_coverage": totals.get("percent_covered", 0),
                    "branch_coverage": totals.get("percent_covered_branches", 0),
                    "total_statements": totals.get("num_statements", 0),
                    "covered_statements": totals.get("covered_lines", 0),
                    "missing_statements": totals.get("missing_lines", 0),
                    "total_branches": totals.get("num_branches", 0),
                    "covered_branches": totals.get("covered_branches", 0),
                })
        
        # Parse XML for additional data
        xml_path = self.project_root / "coverage.xml"
        if xml_path.exists():
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            coverage_data.update({
                "xml_line_rate": float(root.get("line-rate", 0)) * 100,
                "xml_branch_rate": float(root.get("branch-rate", 0)) * 100,
                "timestamp": root.get("timestamp"),
            })
        
        return coverage_data
    
    def _github_integration(self, coverage_data: Dict) -> Dict:
        """GitHub Actions specific integration."""
        print("🐙 Configuring GitHub Actions integration...")
        
        # Set GitHub Actions outputs
        github_outputs = {}
        
        if os.getenv("GITHUB_OUTPUT"):
            output_file = os.getenv("GITHUB_OUTPUT")
            with open(output_file, "a") as f:
                f.write(f"coverage={coverage_data.get('line_coverage', 0):.2f}\n")
                f.write(f"branch-coverage={coverage_data.get('branch_coverage', 0):.2f}\n")
                f.write(f"coverage-status={'passing' if coverage_data.get('line_coverage', 0) >= 85 else 'failing'}\n")
        
        # Generate GitHub Actions step summary
        if os.getenv("GITHUB_STEP_SUMMARY"):
            summary_file = os.getenv("GITHUB_STEP_SUMMARY")
            self._generate_github_summary(coverage_data, summary_file)
        
        # Generate PR comment data
        if os.getenv("GITHUB_EVENT_NAME") == "pull_request":
            github_outputs["pr_comment"] = self._generate_pr_comment(coverage_data)
        
        return {"github": github_outputs}
    
    def _gitlab_integration(self, coverage_data: Dict) -> Dict:
        """GitLab CI specific integration."""
        print("🦊 Configuring GitLab CI integration...")
        
        # Generate GitLab coverage badge
        coverage_pct = coverage_data.get("line_coverage", 0)
        
        # Write coverage percentage for GitLab badge
        with open("coverage_percentage.txt", "w") as f:
            f.write(f"{coverage_pct:.1f}")
        
        # Generate GitLab pages report
        self._generate_gitlab_pages(coverage_data)
        
        return {"gitlab": {"coverage_percentage": coverage_pct}}
    
    def _generate_github_summary(self, coverage_data: Dict, summary_file: str) -> None:
        """Generate GitHub Actions step summary."""
        line_cov = coverage_data.get("line_coverage", 0)
        branch_cov = coverage_data.get("branch_coverage", 0)
        
        # Determine status emoji
        status_emoji = "✅" if line_cov >= 85 else "⚠️" if line_cov >= 75 else "❌"
        
        summary = f"""
# {status_emoji} Coverage Report

## Overall Coverage
- **Line Coverage**: {line_cov:.2f}%
- **Branch Coverage**: {branch_cov:.2f}%

## Quality Assessment
{self._get_coverage_quality_assessment(line_cov)}

## 📁 Reports
- [HTML Coverage Report](./htmlcov/index.html)
- [Coverage XML](./coverage.xml)
- [Coverage JSON](./coverage.json)

---
*Generated by AI Trackdown PyTools Coverage System*
"""
        
        with open(summary_file, "a") as f:
            f.write(summary)
    
    def _generate_pr_comment(self, coverage_data: Dict) -> str:
        """Generate PR comment with coverage information."""
        line_cov = coverage_data.get("line_coverage", 0)
        branch_cov = coverage_data.get("branch_coverage", 0)
        
        status_emoji = "✅" if line_cov >= 85 else "⚠️" if line_cov >= 75 else "❌"
        
        return f"""
## {status_emoji} Coverage Report

| Metric | Value | Status |
|--------|--------|---------|
| Line Coverage | {line_cov:.2f}% | {'✅' if line_cov >= 85 else '❌'} |
| Branch Coverage | {branch_cov:.2f}% | {'✅' if branch_cov >= 80 else '❌'} |

{self._get_coverage_quality_assessment(line_cov)}

<details>
<summary>📊 Detailed Coverage Information</summary>

- **Total Statements**: {coverage_data.get('total_statements', 0)}
- **Covered Statements**: {coverage_data.get('covered_statements', 0)}
- **Missing Statements**: {coverage_data.get('missing_statements', 0)}
- **Total Branches**: {coverage_data.get('total_branches', 0)}
- **Covered Branches**: {coverage_data.get('covered_branches', 0)}

</details>

---
*🤖 Generated by AI Trackdown PyTools*
"""
    
    def _generate_gitlab_pages(self, coverage_data: Dict) -> None:
        """Generate GitLab Pages compatible coverage report."""
        public_dir = self.project_root / "public"
        public_dir.mkdir(exist_ok=True)
        
        # Copy HTML coverage report to public directory
        import shutil
        htmlcov_dir = self.project_root / "htmlcov"
        if htmlcov_dir.exists():
            shutil.copytree(htmlcov_dir, public_dir / "coverage", dirs_exist_ok=True)
        
        # Generate index page
        index_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Trackdown PyTools - Coverage Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .coverage-summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
        .metric {{ margin: 10px 0; }}
        .percentage {{ font-weight: bold; font-size: 1.2em; }}
    </style>
</head>
<body>
    <h1>AI Trackdown PyTools - Coverage Report</h1>
    
    <div class="coverage-summary">
        <div class="metric">
            <span>Line Coverage:</span>
            <span class="percentage">{coverage_data.get('line_coverage', 0):.2f}%</span>
        </div>
        <div class="metric">
            <span>Branch Coverage:</span>
            <span class="percentage">{coverage_data.get('branch_coverage', 0):.2f}%</span>
        </div>
    </div>
    
    <h2>Reports</h2>
    <ul>
        <li><a href="coverage/index.html">Detailed HTML Coverage Report</a></li>
    </ul>
    
    <p><em>Generated: {coverage_data.get('timestamp', 'Unknown')}</em></p>
</body>
</html>
"""
        
        with open(public_dir / "index.html", "w") as f:
            f.write(index_html)
    
    def _get_coverage_quality_assessment(self, coverage: float) -> str:
        """Get coverage quality assessment text."""
        if coverage >= 90:
            return "🟢 **Excellent** - Coverage is excellent!"
        elif coverage >= 85:
            return "🟢 **Good** - Coverage meets target threshold."
        elif coverage >= 75:
            return "🟡 **Fair** - Coverage could be improved."
        elif coverage >= 50:
            return "🟠 **Poor** - Coverage needs significant improvement."
        else:
            return "🔴 **Critical** - Coverage is critically low!"
    
    def _upload_to_codecov(self) -> None:
        """Upload coverage to Codecov."""
        print("📤 Uploading coverage to Codecov...")
        
        try:
            # Use codecov CLI if available
            subprocess.run(
                ["codecov", "-f", "coverage.xml"],
                cwd=self.project_root,
                check=True
            )
            print("✅ Successfully uploaded to Codecov")
        except subprocess.CalledProcessError:
            print("⚠️  Codecov upload failed or CLI not available")
        except FileNotFoundError:
            print("⚠️  Codecov CLI not found")
    
    def _upload_to_coveralls(self) -> None:
        """Upload coverage to Coveralls."""
        print("📤 Uploading coverage to Coveralls...")
        
        try:
            # Use coveralls CLI if available
            subprocess.run(
                ["coveralls"],
                cwd=self.project_root,
                check=True
            )
            print("✅ Successfully uploaded to Coveralls")
        except subprocess.CalledProcessError:
            print("⚠️  Coveralls upload failed or CLI not available")
        except FileNotFoundError:
            print("⚠️  Coveralls CLI not found")
    
    def _generate_ci_badges(self, coverage_data: Dict) -> None:
        """Generate coverage badges for README."""
        coverage = coverage_data.get("line_coverage", 0)
        
        # Determine badge color
        if coverage >= 90:
            color = "brightgreen"
        elif coverage >= 85:
            color = "green"
        elif coverage >= 75:
            color = "yellowgreen"
        elif coverage >= 60:
            color = "yellow"
        else:
            color = "red"
        
        # Generate badge URLs
        badges = {
            "shields_io": f"https://img.shields.io/badge/coverage-{coverage:.1f}%25-{color}",
            "codecov": "https://codecov.io/gh/ai-trackdown/ai-trackdown-pytools/branch/main/graph/badge.svg",
            "coveralls": "https://coveralls.io/repos/github/ai-trackdown/ai-trackdown-pytools/badge.svg?branch=main",
        }
        
        # Save badge information
        badge_file = self.project_root / "coverage-badges.json"
        with open(badge_file, "w") as f:
            json.dump(badges, f, indent=2)
        
        print(f"🏷️  Coverage badges generated: {badge_file}")
    
    def _set_ci_status(self, coverage_data: Dict, tests_passed: bool) -> None:
        """Set CI status based on coverage and test results."""
        coverage = coverage_data.get("line_coverage", 0)
        
        # Overall status
        overall_status = tests_passed and coverage >= 85
        
        # Set exit code for CI
        if not overall_status:
            print(f"❌ CI Status: FAILED (Coverage: {coverage:.1f}%, Tests: {'PASSED' if tests_passed else 'FAILED'})")
            sys.exit(1)
        else:
            print(f"✅ CI Status: PASSED (Coverage: {coverage:.1f}%, Tests: PASSED)")
    
    def generate_ci_config_templates(self) -> None:
        """Generate CI/CD configuration templates."""
        templates_dir = self.project_root / ".github" / "workflows"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # GitHub Actions template
        github_workflow = """
name: Tests and Coverage

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, "3.10", "3.11", "3.12"]

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -e .[test]
    
    - name: Run tests with coverage
      run: |
        python scripts/ci_coverage.py --fail-under 85 --upload-codecov
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Archive coverage reports
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report-${{ matrix.python-version }}
        path: htmlcov/
"""
        
        with open(templates_dir / "test-coverage.yml", "w") as f:
            f.write(github_workflow)
        
        print("📝 Generated GitHub Actions workflow template")


def main():
    """Main CLI interface for CI coverage integration."""
    parser = argparse.ArgumentParser(
        description="AI Trackdown PyTools CI/CD Coverage Integration"
    )
    
    parser.add_argument(
        "--fail-under", type=float, default=85.0,
        help="Minimum coverage percentage required"
    )
    
    parser.add_argument(
        "--upload-codecov", action="store_true",
        help="Upload coverage to Codecov"
    )
    
    parser.add_argument(
        "--upload-coveralls", action="store_true",
        help="Upload coverage to Coveralls"
    )
    
    parser.add_argument(
        "--generate-badges", action="store_true", default=True,
        help="Generate coverage badges"
    )
    
    parser.add_argument(
        "--generate-templates", action="store_true",
        help="Generate CI/CD configuration templates"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Not in a Python project directory (no pyproject.toml found)")
        sys.exit(1)
    
    ci_integration = CICoverageIntegration(project_root)
    
    if args.generate_templates:
        ci_integration.generate_ci_config_templates()
        return
    
    try:
        results = ci_integration.run_coverage_for_ci(
            fail_under=args.fail_under,
            upload_to_codecov=args.upload_codecov,
            upload_to_coveralls=args.upload_coveralls,
            generate_badges=args.generate_badges
        )
        
        print("✅ CI coverage integration completed successfully")
        
    except Exception as e:
        print(f"❌ CI coverage integration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()