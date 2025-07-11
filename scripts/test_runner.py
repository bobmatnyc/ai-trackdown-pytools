#!/usr/bin/env python3
"""
AI Trackdown PyTools - Enhanced Test Runner with Coverage Integration

This script provides comprehensive test execution with integrated coverage analysis,
reporting, and CI/CD integration capabilities.
"""
import argparse
import json
import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET


class TestRunner:
    """Enhanced test runner with coverage integration."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.test_reports_dir = project_root / "test-reports"
        self.test_reports_dir.mkdir(exist_ok=True)
        
        # Coverage directories
        self.coverage_dir = project_root / "coverage-reports"
        self.coverage_dir.mkdir(exist_ok=True)
    
    def run_tests_with_coverage(self,
                              test_paths: Optional[List[str]] = None,
                              coverage_threshold: float = 85.0,
                              fail_fast: bool = False,
                              verbose: bool = False,
                              markers: Optional[List[str]] = None,
                              generate_reports: bool = True) -> Dict:
        """Run tests with comprehensive coverage analysis."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        print("🧪 Starting comprehensive test execution with coverage...")
        print(f"📊 Coverage threshold: {coverage_threshold}%")
        
        # Build pytest command
        cmd = [sys.executable, "-m", "pytest"]
        
        # Add test paths
        if test_paths:
            cmd.extend(test_paths)
        else:
            cmd.append("tests/")
        
        # Coverage options
        cmd.extend([
            "--cov=ai_trackdown_pytools",
            "--cov-branch",
            f"--cov-fail-under={coverage_threshold}",
            "--cov-report=term-missing:skip-covered",
        ])
        
        # Report generation
        if generate_reports:
            cmd.extend([
                f"--cov-report=html:{self.project_root}/htmlcov",
                f"--cov-report=xml:{self.project_root}/coverage.xml",
                f"--cov-report=json:{self.project_root}/coverage.json",
                f"--cov-report=lcov:{self.project_root}/coverage.lcov",
            ])
        
        # JUnit XML for CI integration
        junit_file = self.test_reports_dir / f"junit-{timestamp}.xml"
        cmd.extend(["--junitxml", str(junit_file)])
        
        # Test execution options
        if fail_fast:
            cmd.append("-x")
        
        if verbose:
            cmd.extend(["-v", "-s"])
        else:
            cmd.append("-q")
        
        # Marker filtering
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # Additional pytest options
        cmd.extend([
            "--strict-markers",
            "--strict-config",
            "--tb=short",
            "-ra",
            "--durations=10",
        ])
        
        # Performance and output options
        cmd.extend([
            "--maxfail=10",
            "--disable-warnings",
        ])
        
        print(f"🚀 Executing: {' '.join(cmd)}")
        
        # Run tests
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.project_root / "src")}
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            test_results = self._parse_test_results(result, duration, timestamp)
            
            # Generate coverage analysis
            if generate_reports and (self.project_root / "coverage.json").exists():
                coverage_analysis = self._analyze_coverage_results()
                test_results["coverage"] = coverage_analysis
            
            # Generate comprehensive report
            self._generate_test_report(test_results, timestamp)
            
            # Print summary
            self._print_test_summary(test_results)
            
            return test_results
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Test execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_test_results(self, result: subprocess.CompletedProcess, 
                          duration: float, timestamp: str) -> Dict:
        """Parse test execution results."""
        # Parse JUnit XML if available
        junit_file = self.test_reports_dir / f"junit-{timestamp}.xml"
        test_stats = self._parse_junit_xml(junit_file) if junit_file.exists() else {}
        
        # Parse coverage from output
        coverage_info = self._extract_coverage_from_output(result.stdout)
        
        return {
            "timestamp": timestamp,
            "duration": duration,
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "test_stats": test_stats,
            "coverage_summary": coverage_info,
        }
    
    def _parse_junit_xml(self, junit_file: Path) -> Dict:
        """Parse JUnit XML file for test statistics."""
        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()
            
            # Extract test statistics
            stats = {
                "total": int(root.get("tests", 0)),
                "failures": int(root.get("failures", 0)),
                "errors": int(root.get("errors", 0)),
                "skipped": int(root.get("skipped", 0)),
                "time": float(root.get("time", 0.0)),
            }
            
            stats["passed"] = stats["total"] - stats["failures"] - stats["errors"] - stats["skipped"]
            stats["success_rate"] = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            # Extract failed test details
            failed_tests = []
            for testcase in root.findall(".//testcase"):
                failure = testcase.find("failure")
                error = testcase.find("error")
                
                if failure is not None or error is not None:
                    failed_tests.append({
                        "name": testcase.get("name"),
                        "classname": testcase.get("classname"),
                        "time": float(testcase.get("time", 0)),
                        "failure": failure.text if failure is not None else None,
                        "error": error.text if error is not None else None,
                    })
            
            stats["failed_tests"] = failed_tests
            return stats
            
        except Exception as e:
            print(f"⚠️  Failed to parse JUnit XML: {e}")
            return {}
    
    def _extract_coverage_from_output(self, output: str) -> Dict:
        """Extract coverage information from pytest output."""
        coverage_info = {}
        
        lines = output.split("\n")
        for line in lines:
            if "TOTAL" in line and "%" in line:
                # Parse coverage line: "TOTAL    5021   4708   2076      3     5%"
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        coverage_info = {
                            "statements": int(parts[1]),
                            "missing": int(parts[2]),
                            "branches": int(parts[3]) if len(parts) > 3 else 0,
                            "partial": int(parts[4]) if len(parts) > 4 else 0,
                            "coverage": float(parts[-1].rstrip("%")),
                        }
                        break
                    except (ValueError, IndexError):
                        continue
        
        return coverage_info
    
    def _analyze_coverage_results(self) -> Dict:
        """Analyze detailed coverage results from JSON report."""
        json_path = self.project_root / "coverage.json"
        
        if not json_path.exists():
            return {}
        
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
            
            totals = data.get("totals", {})
            files = data.get("files", {})
            
            # Analyze file-level coverage
            file_analysis = []
            for filename, file_data in files.items():
                summary = file_data.get("summary", {})
                file_analysis.append({
                    "filename": filename,
                    "coverage": summary.get("percent_covered", 0),
                    "statements": summary.get("num_statements", 0),
                    "missing": summary.get("missing_lines", 0),
                    "branches": summary.get("num_branches", 0),
                })
            
            # Sort by coverage percentage
            file_analysis.sort(key=lambda x: x["coverage"])
            
            # Calculate quality metrics
            total_files = len(file_analysis)
            excellent_files = len([f for f in file_analysis if f["coverage"] >= 90])
            good_files = len([f for f in file_analysis if 75 <= f["coverage"] < 90])
            poor_files = len([f for f in file_analysis if f["coverage"] < 50])
            
            return {
                "totals": totals,
                "file_count": total_files,
                "quality_distribution": {
                    "excellent": excellent_files,
                    "good": good_files,
                    "poor": poor_files,
                },
                "lowest_coverage_files": file_analysis[:5],  # Bottom 5
                "highest_coverage_files": file_analysis[-5:],  # Top 5
            }
            
        except Exception as e:
            print(f"⚠️  Failed to analyze coverage results: {e}")
            return {}
    
    def _generate_test_report(self, results: Dict, timestamp: str) -> None:
        """Generate comprehensive test execution report."""
        report_path = self.test_reports_dir / f"test-execution-report-{timestamp}.md"
        
        report = f"""# Test Execution Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Timestamp: {timestamp}

## Execution Summary

- **Status**: {'✅ PASSED' if results['success'] else '❌ FAILED'}
- **Duration**: {results['duration']:.2f}s
- **Exit Code**: {results['exit_code']}

"""
        
        # Test statistics
        if "test_stats" in results and results["test_stats"]:
            stats = results["test_stats"]
            report += f"""## Test Statistics

- **Total Tests**: {stats.get('total', 0)}
- **Passed**: {stats.get('passed', 0)}
- **Failed**: {stats.get('failures', 0)}
- **Errors**: {stats.get('errors', 0)}
- **Skipped**: {stats.get('skipped', 0)}
- **Success Rate**: {stats.get('success_rate', 0):.1f}%

"""
            
            # Failed tests details
            if stats.get("failed_tests"):
                report += "### Failed Tests\n\n"
                for test in stats["failed_tests"][:10]:  # Limit to 10
                    report += f"**{test['name']}** ({test['classname']})\n"
                    if test.get("failure"):
                        report += f"```\n{test['failure'][:500]}...\n```\n\n"
        
        # Coverage summary
        if "coverage_summary" in results and results["coverage_summary"]:
            cov = results["coverage_summary"]
            report += f"""## Coverage Summary

- **Line Coverage**: {cov.get('coverage', 0):.1f}%
- **Total Statements**: {cov.get('statements', 0)}
- **Missing Statements**: {cov.get('missing', 0)}
- **Branch Coverage**: Available in detailed reports

"""
        
        # Coverage analysis
        if "coverage" in results and results["coverage"]:
            cov_analysis = results["coverage"]
            if "quality_distribution" in cov_analysis:
                dist = cov_analysis["quality_distribution"]
                report += f"""## Coverage Quality Distribution

- **Excellent (≥90%)**: {dist.get('excellent', 0)} files
- **Good (75-89%)**: {dist.get('good', 0)} files
- **Poor (<50%)**: {dist.get('poor', 0)} files

"""
            
            # Lowest coverage files
            if "lowest_coverage_files" in cov_analysis:
                report += "### Files Needing Attention\n\n"
                for file_info in cov_analysis["lowest_coverage_files"]:
                    report += f"- **{file_info['filename']}**: {file_info['coverage']:.1f}% coverage\n"
                report += "\n"
        
        # Generated artifacts
        report += "## Generated Artifacts\n\n"
        report += "### Coverage Reports\n"
        report += f"- HTML Report: `htmlcov/index.html`\n"
        report += f"- XML Report: `coverage.xml`\n"
        report += f"- JSON Report: `coverage.json`\n"
        report += f"- LCOV Report: `coverage.lcov`\n\n"
        
        report += "### Test Reports\n"
        report += f"- JUnit XML: `test-reports/junit-{timestamp}.xml`\n"
        report += f"- Execution Report: `test-reports/test-execution-report-{timestamp}.md`\n\n"
        
        # Recommendations
        if not results["success"]:
            report += "## Recommendations\n\n"
            report += "1. Review failed test details above\n"
            report += "2. Check test output for specific error messages\n"
            report += "3. Run individual failing tests for detailed debugging\n"
            report += "4. Ensure all dependencies are properly installed\n\n"
        
        # Save report
        with open(report_path, "w") as f:
            f.write(report)
        
        print(f"📋 Test execution report saved: {report_path}")
    
    def _print_test_summary(self, results: Dict) -> None:
        """Print test execution summary to console."""
        print("\n" + "="*70)
        print("🧪 TEST EXECUTION SUMMARY")
        print("="*70)
        
        # Status
        status_emoji = "✅" if results["success"] else "❌"
        print(f"Status: {status_emoji} {'PASSED' if results['success'] else 'FAILED'}")
        print(f"Duration: {results['duration']:.2f}s")
        
        # Test statistics
        if "test_stats" in results and results["test_stats"]:
            stats = results["test_stats"]
            print(f"\nTests: {stats.get('passed', 0)}/{stats.get('total', 0)} passed")
            if stats.get("failures", 0) > 0:
                print(f"Failures: {stats['failures']}")
            if stats.get("errors", 0) > 0:
                print(f"Errors: {stats['errors']}")
            if stats.get("skipped", 0) > 0:
                print(f"Skipped: {stats['skipped']}")
        
        # Coverage
        if "coverage_summary" in results and results["coverage_summary"]:
            cov = results["coverage_summary"]
            coverage_pct = cov.get('coverage', 0)
            coverage_emoji = "🟢" if coverage_pct >= 85 else "🟡" if coverage_pct >= 75 else "🔴"
            print(f"\nCoverage: {coverage_emoji} {coverage_pct:.1f}%")
        
        # Quick recommendations
        if not results["success"]:
            print("\n🔧 Quick Actions:")
            print("  • Review failed tests in the detailed report")
            print("  • Run specific tests with -v for more details")
            print("  • Check coverage gaps for untested code")
        
        print("\n📁 Reports generated in:")
        print(f"  • HTML Coverage: htmlcov/index.html")
        print(f"  • Test Reports: test-reports/")
        print("="*70)
    
    def run_specific_test_suite(self, suite_type: str, **kwargs) -> Dict:
        """Run specific test suite with appropriate settings."""
        suite_configs = {
            "unit": {
                "test_paths": ["tests/unit/"],
                "markers": ["unit"],
                "coverage_threshold": 90.0,
                "fail_fast": False,
            },
            "integration": {
                "test_paths": ["tests/integration/"],
                "markers": ["integration"],
                "coverage_threshold": 75.0,
                "fail_fast": False,
            },
            "e2e": {
                "test_paths": ["tests/e2e/"],
                "markers": ["e2e"],
                "coverage_threshold": 60.0,
                "fail_fast": True,
            },
            "cli": {
                "test_paths": ["tests/cli/"],
                "markers": ["cli"],
                "coverage_threshold": 80.0,
                "fail_fast": False,
            },
            "fast": {
                "test_paths": ["tests/unit/", "tests/integration/"],
                "markers": ["not slow"],
                "coverage_threshold": 80.0,
                "fail_fast": True,
            },
            "full": {
                "test_paths": None,  # All tests
                "markers": None,
                "coverage_threshold": 85.0,
                "fail_fast": False,
            }
        }
        
        if suite_type not in suite_configs:
            raise ValueError(f"Unknown test suite: {suite_type}")
        
        config = suite_configs[suite_type]
        config.update(kwargs)  # Allow overrides
        
        print(f"🎯 Running {suite_type} test suite...")
        return self.run_tests_with_coverage(**config)


def main():
    """Main CLI interface for the test runner."""
    parser = argparse.ArgumentParser(
        description="AI Trackdown PyTools Enhanced Test Runner"
    )
    
    parser.add_argument(
        "suite", nargs="?", default="full",
        choices=["unit", "integration", "e2e", "cli", "fast", "full"],
        help="Test suite to run"
    )
    
    parser.add_argument(
        "--threshold", type=float, default=85.0,
        help="Coverage threshold percentage"
    )
    
    parser.add_argument(
        "--fail-fast", action="store_true",
        help="Stop on first failure"
    )
    
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--markers", nargs="+",
        help="Pytest markers to filter tests"
    )
    
    parser.add_argument(
        "--paths", nargs="+",
        help="Specific test paths to run"
    )
    
    parser.add_argument(
        "--no-reports", action="store_true",
        help="Skip report generation"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Not in a Python project directory (no pyproject.toml found)")
        sys.exit(1)
    
    runner = TestRunner(project_root)
    
    try:
        if args.paths:
            # Custom test paths
            results = runner.run_tests_with_coverage(
                test_paths=args.paths,
                coverage_threshold=args.threshold,
                fail_fast=args.fail_fast,
                verbose=args.verbose,
                markers=args.markers,
                generate_reports=not args.no_reports
            )
        else:
            # Predefined test suite
            results = runner.run_specific_test_suite(
                args.suite,
                coverage_threshold=args.threshold,
                fail_fast=args.fail_fast,
                verbose=args.verbose,
                markers=args.markers,
                generate_reports=not args.no_reports
            )
        
        # Exit with appropriate code
        sys.exit(0 if results["success"] else 1)
        
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()