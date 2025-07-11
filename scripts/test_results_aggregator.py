#!/usr/bin/env python3
"""
AI Trackdown PyTools - Test Results Aggregation and Reporting System

This script provides comprehensive test result aggregation, analysis, and
reporting capabilities for CI/CD integration and quality monitoring.
"""

import argparse
import json
import os
import sys
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import glob
import statistics
from dataclasses import dataclass
import requests


@dataclass
class TestResult:
    """Test execution result data."""
    name: str
    classname: str
    time: float
    status: str  # passed, failed, error, skipped
    failure_message: Optional[str] = None
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None


@dataclass 
class TestSuite:
    """Test suite execution data."""
    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    time: float
    timestamp: datetime
    platform: str
    python_version: str
    test_results: List[TestResult]


@dataclass
class CoverageData:
    """Coverage analysis data."""
    line_coverage: float
    branch_coverage: float
    function_coverage: float
    statements: int
    missing: int
    branches: int
    covered_branches: int
    files_analyzed: int


class TestResultsAggregator:
    """Advanced test results aggregation and analysis system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results_db = project_root / "test_results.db"
        self.reports_dir = project_root / "aggregated-reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize test results database."""
        with sqlite3.connect(self.results_db) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS test_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    commit_hash TEXT,
                    branch TEXT,
                    platform TEXT,
                    python_version TEXT,
                    ci_environment BOOLEAN DEFAULT FALSE,
                    total_tests INTEGER,
                    passed_tests INTEGER,
                    failed_tests INTEGER,
                    error_tests INTEGER,
                    skipped_tests INTEGER,
                    execution_time REAL,
                    success_rate REAL
                );
                
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    test_name TEXT NOT NULL,
                    test_class TEXT,
                    test_file TEXT,
                    line_number INTEGER,
                    status TEXT NOT NULL,
                    execution_time REAL,
                    failure_message TEXT,
                    error_message TEXT,
                    FOREIGN KEY (run_id) REFERENCES test_runs (id)
                );
                
                CREATE TABLE IF NOT EXISTS coverage_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    line_coverage REAL,
                    branch_coverage REAL,
                    function_coverage REAL,
                    statements INTEGER,
                    missing INTEGER,
                    branches INTEGER,
                    covered_branches INTEGER,
                    files_analyzed INTEGER,
                    FOREIGN KEY (run_id) REFERENCES test_runs (id)
                );
                
                CREATE TABLE IF NOT EXISTS flaky_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    test_name TEXT NOT NULL,
                    test_class TEXT,
                    failure_count INTEGER DEFAULT 1,
                    success_count INTEGER DEFAULT 0,
                    first_seen TEXT,
                    last_seen TEXT,
                    flakiness_score REAL,
                    PRIMARY KEY (test_name, test_class)
                );
                
                CREATE TABLE IF NOT EXISTS test_trends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    trend_direction TEXT,
                    PRIMARY KEY (date, metric_name)
                );
                
                CREATE INDEX IF NOT EXISTS idx_test_runs_timestamp ON test_runs (timestamp);
                CREATE INDEX IF NOT EXISTS idx_test_results_name ON test_results (test_name);
                CREATE INDEX IF NOT EXISTS idx_coverage_run ON coverage_data (run_id);
            """)
    
    def aggregate_test_results(self, 
                             sources: Optional[List[str]] = None,
                             store_results: bool = True) -> Dict[str, Any]:
        """Aggregate test results from multiple sources."""
        print("📊 Aggregating test results...")
        
        # Auto-discover sources if not provided
        if not sources:
            sources = self._discover_test_result_sources()
        
        aggregated_data = {
            "timestamp": datetime.now().isoformat(),
            "sources": sources,
            "test_suites": [],
            "coverage_data": None,
            "summary": {},
            "quality_metrics": {},
            "flaky_tests": [],
            "trends": {}
        }
        
        # Process each source
        total_suites = 0
        for source in sources:
            print(f"   📁 Processing: {source}")
            
            if source.endswith('.xml') and 'junit' in source.lower():
                suite = self._parse_junit_xml(source)
                if suite:
                    aggregated_data["test_suites"].append(suite)
                    total_suites += 1
            
            elif source.endswith('.json') and 'coverage' in source.lower():
                coverage = self._parse_coverage_json(source)
                if coverage:
                    aggregated_data["coverage_data"] = coverage
        
        print(f"   ✅ Processed {total_suites} test suites")
        
        # Generate summary statistics
        aggregated_data["summary"] = self._generate_summary_statistics(
            aggregated_data["test_suites"]
        )
        
        # Calculate quality metrics
        aggregated_data["quality_metrics"] = self._calculate_quality_metrics(
            aggregated_data["test_suites"], 
            aggregated_data["coverage_data"]
        )
        
        # Detect flaky tests
        aggregated_data["flaky_tests"] = self._detect_flaky_tests(
            aggregated_data["test_suites"]
        )
        
        # Store results if requested
        if store_results:
            run_id = self._store_aggregated_results(aggregated_data)
            aggregated_data["run_id"] = run_id
            
            # Update trends
            self._update_trends(aggregated_data)
            
            # Get trends for reporting
            aggregated_data["trends"] = self._get_recent_trends()
        
        # Generate comprehensive report
        report_path = self._generate_aggregated_report(aggregated_data)
        aggregated_data["report_path"] = str(report_path)
        
        print(f"📄 Aggregated report generated: {report_path}")
        
        return aggregated_data
    
    def _discover_test_result_sources(self) -> List[str]:
        """Auto-discover test result files."""
        sources = []
        
        # Common test result patterns
        patterns = [
            "test-reports/**/*.xml",
            "test-reports/**/*.json",
            "**/junit*.xml",
            "**/coverage*.json",
            "**/coverage*.xml",
            "htmlcov/coverage.json",
            "reports/**/*.xml",
            "reports/**/*.json",
        ]
        
        for pattern in patterns:
            files = glob.glob(str(self.project_root / pattern), recursive=True)
            sources.extend(files)
        
        # Remove duplicates and sort
        sources = sorted(list(set(sources)))
        
        print(f"   🔍 Discovered {len(sources)} test result files")
        
        return sources
    
    def _parse_junit_xml(self, file_path: str) -> Optional[TestSuite]:
        """Parse JUnit XML test results."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract test suite information
            suite_name = root.get('name', Path(file_path).stem)
            tests = int(root.get('tests', 0))
            failures = int(root.get('failures', 0))
            errors = int(root.get('errors', 0))
            skipped = int(root.get('skipped', 0))
            time = float(root.get('time', 0.0))
            
            # Extract platform and version info from properties if available
            platform = "unknown"
            python_version = "unknown"
            
            properties = root.find('properties')
            if properties is not None:
                for prop in properties.findall('property'):
                    name = prop.get('name', '')
                    value = prop.get('value', '')
                    
                    if 'platform' in name.lower():
                        platform = value
                    elif 'python' in name.lower() and 'version' in name.lower():
                        python_version = value
            
            # Parse individual test results
            test_results = []
            for testcase in root.findall('.//testcase'):
                test_name = testcase.get('name', '')
                classname = testcase.get('classname', '')
                test_time = float(testcase.get('time', 0.0))
                file_path = testcase.get('file')
                line_number = testcase.get('line')
                
                # Determine test status
                failure = testcase.find('failure')
                error = testcase.find('error')
                skipped_elem = testcase.find('skipped')
                
                if failure is not None:
                    status = "failed"
                    failure_message = failure.text
                    error_message = None
                elif error is not None:
                    status = "error"
                    failure_message = None
                    error_message = error.text
                elif skipped_elem is not None:
                    status = "skipped"
                    failure_message = None
                    error_message = None
                else:
                    status = "passed"
                    failure_message = None
                    error_message = None
                
                test_result = TestResult(
                    name=test_name,
                    classname=classname,
                    time=test_time,
                    status=status,
                    failure_message=failure_message,
                    error_message=error_message,
                    file_path=file_path,
                    line_number=int(line_number) if line_number else None
                )
                
                test_results.append(test_result)
            
            return TestSuite(
                name=suite_name,
                tests=tests,
                failures=failures,
                errors=errors,
                skipped=skipped,
                time=time,
                timestamp=datetime.now(),
                platform=platform,
                python_version=python_version,
                test_results=test_results
            )
            
        except Exception as e:
            print(f"   ⚠️ Failed to parse JUnit XML {file_path}: {e}")
            return None
    
    def _parse_coverage_json(self, file_path: str) -> Optional[CoverageData]:
        """Parse coverage JSON results."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            totals = data.get('totals', {})
            
            return CoverageData(
                line_coverage=totals.get('percent_covered', 0.0),
                branch_coverage=totals.get('percent_covered_branches', 0.0),
                function_coverage=totals.get('percent_covered_functions', 0.0),
                statements=totals.get('num_statements', 0),
                missing=totals.get('missing_lines', 0),
                branches=totals.get('num_branches', 0),
                covered_branches=totals.get('covered_branches', 0),
                files_analyzed=len(data.get('files', {}))
            )
            
        except Exception as e:
            print(f"   ⚠️ Failed to parse coverage JSON {file_path}: {e}")
            return None
    
    def _generate_summary_statistics(self, test_suites: List[TestSuite]) -> Dict[str, Any]:
        """Generate summary statistics from test suites."""
        if not test_suites:
            return {}
        
        total_tests = sum(suite.tests for suite in test_suites)
        total_failures = sum(suite.failures for suite in test_suites)
        total_errors = sum(suite.errors for suite in test_suites)
        total_skipped = sum(suite.skipped for suite in test_suites)
        total_passed = total_tests - total_failures - total_errors - total_skipped
        total_time = sum(suite.time for suite in test_suites)
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate execution time statistics
        suite_times = [suite.time for suite in test_suites]
        avg_suite_time = statistics.mean(suite_times) if suite_times else 0
        max_suite_time = max(suite_times) if suite_times else 0
        
        # Platform distribution
        platforms = {}
        python_versions = {}
        for suite in test_suites:
            platforms[suite.platform] = platforms.get(suite.platform, 0) + 1
            python_versions[suite.python_version] = python_versions.get(suite.python_version, 0) + 1
        
        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failures,
            "errors": total_errors,
            "skipped": total_skipped,
            "success_rate": round(success_rate, 2),
            "total_execution_time": round(total_time, 2),
            "average_suite_time": round(avg_suite_time, 2),
            "max_suite_time": round(max_suite_time, 2),
            "test_suites_count": len(test_suites),
            "platforms": platforms,
            "python_versions": python_versions
        }
    
    def _calculate_quality_metrics(self, 
                                 test_suites: List[TestSuite], 
                                 coverage_data: Optional[CoverageData]) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics."""
        metrics = {}
        
        if test_suites:
            # Test stability metrics
            all_test_results = []
            for suite in test_suites:
                all_test_results.extend(suite.test_results)
            
            if all_test_results:
                # Test execution time distribution
                test_times = [result.time for result in all_test_results if result.time > 0]
                if test_times:
                    metrics["test_time_stats"] = {
                        "mean": round(statistics.mean(test_times), 3),
                        "median": round(statistics.median(test_times), 3),
                        "max": round(max(test_times), 3),
                        "p95": round(sorted(test_times)[int(0.95 * len(test_times))], 3)
                    }
                
                # Failure distribution
                failed_tests = [r for r in all_test_results if r.status in ['failed', 'error']]
                if failed_tests:
                    failure_classes = {}
                    for test in failed_tests:
                        class_name = test.classname or "Unknown"
                        failure_classes[class_name] = failure_classes.get(class_name, 0) + 1
                    
                    metrics["failure_distribution"] = failure_classes
                
                # Test file distribution
                test_files = {}
                for test in all_test_results:
                    if test.file_path:
                        test_files[test.file_path] = test_files.get(test.file_path, 0) + 1
                
                metrics["test_file_distribution"] = test_files
        
        # Coverage quality metrics
        if coverage_data:
            coverage_grade = "A"
            if coverage_data.line_coverage < 90:
                coverage_grade = "B"
            if coverage_data.line_coverage < 80:
                coverage_grade = "C"
            if coverage_data.line_coverage < 70:
                coverage_grade = "D"
            if coverage_data.line_coverage < 60:
                coverage_grade = "F"
            
            metrics["coverage_quality"] = {
                "grade": coverage_grade,
                "line_coverage": coverage_data.line_coverage,
                "branch_coverage": coverage_data.branch_coverage,
                "function_coverage": coverage_data.function_coverage,
                "completeness": round(
                    (coverage_data.statements - coverage_data.missing) / coverage_data.statements * 100 
                    if coverage_data.statements > 0 else 0, 2
                )
            }
        
        # Overall quality score (0-100)
        quality_score = 100
        
        # Deduct for failures
        if test_suites:
            total_tests = sum(suite.tests for suite in test_suites)
            total_failures = sum(suite.failures + suite.errors for suite in test_suites)
            if total_tests > 0:
                failure_penalty = (total_failures / total_tests) * 30
                quality_score -= failure_penalty
        
        # Deduct for low coverage
        if coverage_data and coverage_data.line_coverage < 85:
            coverage_penalty = (85 - coverage_data.line_coverage) * 0.5
            quality_score = max(0, quality_score - coverage_penalty)
        
        metrics["overall_quality_score"] = round(max(0, quality_score), 1)
        
        return metrics
    
    def _detect_flaky_tests(self, test_suites: List[TestSuite]) -> List[Dict[str, Any]]:
        """Detect potentially flaky tests based on historical data."""
        flaky_tests = []
        
        # For now, identify tests that failed in some suites but passed in others
        test_results_by_name = {}
        
        for suite in test_suites:
            for test in suite.test_results:
                test_key = f"{test.classname}.{test.name}"
                if test_key not in test_results_by_name:
                    test_results_by_name[test_key] = []
                test_results_by_name[test_key].append(test.status)
        
        # Look for tests with mixed results
        for test_name, statuses in test_results_by_name.items():
            if len(set(statuses)) > 1:  # Mixed results
                passed_count = statuses.count('passed')
                failed_count = statuses.count('failed') + statuses.count('error')
                total_count = len(statuses)
                
                if failed_count > 0 and passed_count > 0:
                    flakiness_score = failed_count / total_count
                    
                    flaky_tests.append({
                        "test_name": test_name,
                        "total_runs": total_count,
                        "passed_runs": passed_count,
                        "failed_runs": failed_count,
                        "flakiness_score": round(flakiness_score, 3),
                        "severity": "high" if flakiness_score > 0.3 else "medium"
                    })
        
        # Sort by flakiness score
        flaky_tests.sort(key=lambda x: x["flakiness_score"], reverse=True)
        
        return flaky_tests
    
    def _store_aggregated_results(self, aggregated_data: Dict[str, Any]) -> int:
        """Store aggregated results in database."""
        git_info = self._get_git_info()
        summary = aggregated_data["summary"]
        
        with sqlite3.connect(self.results_db) as conn:
            # Store test run
            cursor = conn.execute("""
                INSERT INTO test_runs 
                (timestamp, commit_hash, branch, platform, python_version, ci_environment,
                 total_tests, passed_tests, failed_tests, error_tests, skipped_tests,
                 execution_time, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                aggregated_data["timestamp"],
                git_info.get("commit_hash", "unknown"),
                git_info.get("branch", "unknown"),
                list(summary.get("platforms", {}).keys())[0] if summary.get("platforms") else "unknown",
                list(summary.get("python_versions", {}).keys())[0] if summary.get("python_versions") else "unknown",
                os.getenv("CI", "false").lower() == "true",
                summary.get("total_tests", 0),
                summary.get("passed", 0),
                summary.get("failed", 0),
                summary.get("errors", 0),
                summary.get("skipped", 0),
                summary.get("total_execution_time", 0),
                summary.get("success_rate", 0)
            ))
            
            run_id = cursor.lastrowid
            
            # Store individual test results
            for suite in aggregated_data["test_suites"]:
                for test in suite.test_results:
                    conn.execute("""
                        INSERT INTO test_results
                        (run_id, test_name, test_class, test_file, line_number,
                         status, execution_time, failure_message, error_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        run_id, test.name, test.classname, test.file_path,
                        test.line_number, test.status, test.time,
                        test.failure_message, test.error_message
                    ))
            
            # Store coverage data
            coverage = aggregated_data["coverage_data"]
            if coverage:
                conn.execute("""
                    INSERT INTO coverage_data
                    (run_id, line_coverage, branch_coverage, function_coverage,
                     statements, missing, branches, covered_branches, files_analyzed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id, coverage.line_coverage, coverage.branch_coverage,
                    coverage.function_coverage, coverage.statements, coverage.missing,
                    coverage.branches, coverage.covered_branches, coverage.files_analyzed
                ))
            
            return run_id
    
    def _get_git_info(self) -> Dict[str, str]:
        """Get current git information."""
        try:
            import subprocess
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                text=True
            ).strip()
            
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.project_root,
                text=True
            ).strip()
            
            return {"commit_hash": commit_hash, "branch": branch}
        except:
            return {"commit_hash": "unknown", "branch": "unknown"}
    
    def _update_trends(self, aggregated_data: Dict[str, Any]) -> None:
        """Update trend data."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        summary = aggregated_data["summary"]
        coverage = aggregated_data["coverage_data"]
        quality = aggregated_data["quality_metrics"]
        
        trends_data = [
            ("success_rate", summary.get("success_rate", 0)),
            ("total_tests", summary.get("total_tests", 0)),
            ("execution_time", summary.get("total_execution_time", 0)),
            ("quality_score", quality.get("overall_quality_score", 0)),
        ]
        
        if coverage:
            trends_data.extend([
                ("line_coverage", coverage.line_coverage),
                ("branch_coverage", coverage.branch_coverage),
            ])
        
        with sqlite3.connect(self.results_db) as conn:
            for metric_name, metric_value in trends_data:
                conn.execute("""
                    INSERT OR REPLACE INTO test_trends (date, metric_name, metric_value)
                    VALUES (?, ?, ?)
                """, (date_str, metric_name, metric_value))
    
    def _get_recent_trends(self, days: int = 14) -> Dict[str, List]:
        """Get recent trend data."""
        trends = {}
        
        with sqlite3.connect(self.results_db) as conn:
            cursor = conn.execute("""
                SELECT metric_name, date, metric_value
                FROM test_trends
                WHERE date > date('now', '-{} days')
                ORDER BY metric_name, date
            """.format(days))
            
            for metric_name, date, value in cursor.fetchall():
                if metric_name not in trends:
                    trends[metric_name] = []
                trends[metric_name].append({"date": date, "value": value})
        
        return trends
    
    def _generate_aggregated_report(self, aggregated_data: Dict[str, Any]) -> Path:
        """Generate comprehensive aggregated test report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"aggregated_test_report_{timestamp}.md"
        
        summary = aggregated_data["summary"]
        quality = aggregated_data["quality_metrics"]
        coverage = aggregated_data["coverage_data"]
        flaky_tests = aggregated_data["flaky_tests"]
        trends = aggregated_data["trends"]
        
        with open(report_path, "w") as f:
            f.write(f"""# Comprehensive Test Results Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Sources Processed**: {len(aggregated_data['sources'])}
**Test Suites**: {summary.get('test_suites_count', 0)}

## Executive Summary

""")
            
            # Status emoji based on success rate
            success_rate = summary.get('success_rate', 0)
            status_emoji = "🟢" if success_rate >= 95 else "🟡" if success_rate >= 85 else "🔴"
            
            f.write(f"**Overall Status**: {status_emoji} {success_rate:.1f}% Success Rate\n\n")
            
            # Key metrics
            f.write("### Key Metrics\n\n")
            f.write(f"- **Total Tests**: {summary.get('total_tests', 0):,}\n")
            f.write(f"- **Passed**: {summary.get('passed', 0):,} ✅\n")
            f.write(f"- **Failed**: {summary.get('failed', 0):,} ❌\n")
            f.write(f"- **Errors**: {summary.get('errors', 0):,} 💥\n")
            f.write(f"- **Skipped**: {summary.get('skipped', 0):,} ⏭️\n")
            f.write(f"- **Execution Time**: {summary.get('total_execution_time', 0):.1f}s\n")
            
            if quality.get('overall_quality_score') is not None:
                score = quality['overall_quality_score']
                score_emoji = "🟢" if score >= 90 else "🟡" if score >= 75 else "🔴"
                f.write(f"- **Quality Score**: {score_emoji} {score}/100\n")
            
            # Coverage information
            if coverage:
                cov_emoji = "🟢" if coverage.line_coverage >= 85 else "🟡" if coverage.line_coverage >= 75 else "🔴"
                f.write(f"- **Line Coverage**: {cov_emoji} {coverage.line_coverage:.1f}%\n")
                f.write(f"- **Branch Coverage**: {coverage.branch_coverage:.1f}%\n")
            
            f.write("\n")
            
            # Platform distribution
            if summary.get('platforms'):
                f.write("### Platform Distribution\n\n")
                for platform, count in summary['platforms'].items():
                    f.write(f"- **{platform}**: {count} test suite(s)\n")
                f.write("\n")
            
            # Python version distribution
            if summary.get('python_versions'):
                f.write("### Python Version Distribution\n\n")
                for version, count in summary['python_versions'].items():
                    f.write(f"- **Python {version}**: {count} test suite(s)\n")
                f.write("\n")
            
            # Test performance analysis
            if quality.get('test_time_stats'):
                stats = quality['test_time_stats']
                f.write("### Test Performance Analysis\n\n")
                f.write(f"- **Average Test Time**: {stats['mean']:.3f}s\n")
                f.write(f"- **Median Test Time**: {stats['median']:.3f}s\n")
                f.write(f"- **Slowest Test**: {stats['max']:.3f}s\n")
                f.write(f"- **95th Percentile**: {stats['p95']:.3f}s\n\n")
            
            # Flaky tests
            if flaky_tests:
                f.write("## 🚨 Flaky Tests Detected\n\n")
                f.write("Tests showing inconsistent behavior across multiple runs:\n\n")
                f.write("| Test Name | Runs | Failed | Flakiness | Severity |\n")
                f.write("|-----------|------|---------|-----------|----------|\n")
                
                for test in flaky_tests[:10]:  # Top 10 flaky tests
                    severity_emoji = "🔴" if test['severity'] == 'high' else "🟡"
                    f.write(f"| {test['test_name']} | {test['total_runs']} | {test['failed_runs']} | {test['flakiness_score']:.1%} | {severity_emoji} {test['severity']} |\n")
                
                f.write("\n")
            
            # Failure analysis
            if quality.get('failure_distribution'):
                f.write("## Failure Analysis\n\n")
                f.write("### Failures by Test Class\n\n")
                f.write("| Test Class | Failure Count |\n")
                f.write("|------------|---------------|\n")
                
                sorted_failures = sorted(
                    quality['failure_distribution'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                
                for class_name, count in sorted_failures[:10]:
                    f.write(f"| {class_name} | {count} |\n")
                
                f.write("\n")
            
            # Coverage analysis
            if coverage:
                f.write("## Coverage Analysis\n\n")
                
                if quality.get('coverage_quality'):
                    cov_quality = quality['coverage_quality']
                    grade_emoji = {
                        'A': '🟢', 'B': '🟡', 'C': '🟠', 'D': '🔴', 'F': '💀'
                    }.get(cov_quality['grade'], '❓')
                    
                    f.write(f"**Coverage Grade**: {grade_emoji} {cov_quality['grade']}\n\n")
                
                f.write(f"- **Line Coverage**: {coverage.line_coverage:.1f}%\n")
                f.write(f"- **Branch Coverage**: {coverage.branch_coverage:.1f}%\n")
                f.write(f"- **Function Coverage**: {coverage.function_coverage:.1f}%\n")
                f.write(f"- **Files Analyzed**: {coverage.files_analyzed}\n")
                f.write(f"- **Total Statements**: {coverage.statements:,}\n")
                f.write(f"- **Missing Coverage**: {coverage.missing:,}\n\n")
            
            # Trends analysis
            if trends:
                f.write("## Trends Analysis (Last 14 Days)\n\n")
                
                for metric_name, trend_data in trends.items():
                    if len(trend_data) >= 2:
                        latest = trend_data[-1]['value']
                        previous = trend_data[-2]['value']
                        change = latest - previous
                        
                        if change > 0:
                            trend_emoji = "📈" if metric_name in ['success_rate', 'line_coverage', 'quality_score'] else "📉"
                        elif change < 0:
                            trend_emoji = "📉" if metric_name in ['success_rate', 'line_coverage', 'quality_score'] else "📈"
                        else:
                            trend_emoji = "➡️"
                        
                        f.write(f"- **{metric_name.replace('_', ' ').title()}**: {trend_emoji} {latest:.1f} (Δ{change:+.1f})\n")
                
                f.write("\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            
            # Performance recommendations
            if success_rate < 95:
                f.write("### Test Reliability\n")
                f.write(f"- 🔴 **Critical**: Success rate ({success_rate:.1f}%) below target (95%)\n")
                f.write("- 🔧 **Action**: Investigate and fix failing tests\n")
                if flaky_tests:
                    f.write("- 🔧 **Action**: Address flaky tests to improve reliability\n")
                f.write("\n")
            
            if coverage and coverage.line_coverage < 85:
                f.write("### Coverage Improvement\n")
                f.write(f"- 🟡 **Warning**: Line coverage ({coverage.line_coverage:.1f}%) below target (85%)\n")
                f.write("- 🔧 **Action**: Add tests for uncovered code paths\n")
                f.write("- 🔧 **Action**: Review coverage gaps in critical modules\n\n")
            
            if quality.get('test_time_stats', {}).get('p95', 0) > 5.0:
                f.write("### Performance Optimization\n")
                f.write("- ⚠️ **Notice**: Some tests are running slowly (>5s)\n")
                f.write("- 🔧 **Action**: Profile and optimize slow tests\n")
                f.write("- 🔧 **Action**: Consider parallel test execution\n\n")
            
            # General recommendations
            f.write("### General Quality Improvements\n")
            f.write("- 📊 **Monitor**: Track test trends over time\n")
            f.write("- 🧪 **Expand**: Add more integration and end-to-end tests\n")
            f.write("- 🔄 **Automate**: Ensure CI/CD pipeline includes all quality gates\n")
            f.write("- 📈 **Measure**: Set up alerting for quality regressions\n\n")
            
            # Data sources
            f.write("## Data Sources\n\n")
            for i, source in enumerate(aggregated_data['sources'], 1):
                f.write(f"{i}. `{source}`\n")
            
            f.write(f"\n---\n*Report generated by AI Trackdown PyTools Test Results Aggregator*\n")
        
        return report_path
    
    def generate_historical_analysis(self, days: int = 30) -> Path:
        """Generate historical test analysis report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"historical_analysis_{timestamp}.md"
        
        with sqlite3.connect(self.results_db) as conn:
            # Get historical test data
            cursor = conn.execute("""
                SELECT 
                    date(timestamp) as test_date,
                    AVG(success_rate) as avg_success_rate,
                    AVG(total_tests) as avg_total_tests,
                    AVG(execution_time) as avg_execution_time,
                    COUNT(*) as runs_count
                FROM test_runs
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY date(timestamp)
                ORDER BY test_date
            """.format(days))
            
            historical_data = cursor.fetchall()
            
            # Get coverage trends
            cursor = conn.execute("""
                SELECT 
                    tr.timestamp,
                    cd.line_coverage,
                    cd.branch_coverage
                FROM test_runs tr
                LEFT JOIN coverage_data cd ON tr.id = cd.run_id
                WHERE tr.timestamp > datetime('now', '-{} days')
                ORDER BY tr.timestamp
            """.format(days))
            
            coverage_trends = cursor.fetchall()
        
        # Generate report
        with open(report_path, "w") as f:
            f.write(f"""# Historical Test Analysis Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analysis Period**: Last {days} days
**Data Points**: {len(historical_data)} days

## Trend Summary

""")
            
            if historical_data:
                # Calculate overall trends
                first_day = historical_data[0]
                last_day = historical_data[-1]
                
                success_trend = last_day[1] - first_day[1]
                tests_trend = last_day[2] - first_day[2]
                time_trend = last_day[3] - first_day[3]
                
                f.write(f"- **Success Rate Trend**: {success_trend:+.1f}% over {days} days\n")
                f.write(f"- **Test Count Trend**: {tests_trend:+.0f} tests\n")
                f.write(f"- **Execution Time Trend**: {time_trend:+.1f}s\n\n")
                
                # Daily breakdown
                f.write("## Daily Test Results\n\n")
                f.write("| Date | Success Rate | Total Tests | Execution Time | Runs |\n")
                f.write("|------|--------------|-------------|----------------|------|\n")
                
                for date, success, tests, time, runs in historical_data:
                    f.write(f"| {date} | {success:.1f}% | {int(tests)} | {time:.1f}s | {runs} |\n")
                
                f.write("\n")
            
            if coverage_trends:
                f.write("## Coverage Trends\n\n")
                f.write("Coverage data over time:\n\n")
                f.write("| Date | Line Coverage | Branch Coverage |\n")
                f.write("|------|---------------|------------------|\n")
                
                for timestamp, line_cov, branch_cov in coverage_trends[-10:]:  # Last 10
                    date = timestamp.split('T')[0]
                    line_str = f"{line_cov:.1f}%" if line_cov else "N/A"
                    branch_str = f"{branch_cov:.1f}%" if branch_cov else "N/A"
                    f.write(f"| {date} | {line_str} | {branch_str} |\n")
            
            f.write(f"\n---\n*Historical analysis generated by AI Trackdown PyTools*\n")
        
        return report_path


def main():
    """Main CLI interface for test results aggregation."""
    parser = argparse.ArgumentParser(
        description="AI Trackdown PyTools Test Results Aggregator"
    )
    
    parser.add_argument(
        "command",
        choices=["aggregate", "historical", "trends"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--sources", nargs="+",
        help="Specific test result files to process"
    )
    
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of days for historical analysis"
    )
    
    parser.add_argument(
        "--no-store", action="store_true",
        help="Don't store results in database"
    )
    
    parser.add_argument(
        "--quality-gate", type=float, default=85.0,
        help="Quality gate threshold for success rate"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Not in a Python project directory")
        sys.exit(1)
    
    aggregator = TestResultsAggregator(project_root)
    
    try:
        if args.command == "aggregate":
            results = aggregator.aggregate_test_results(
                sources=args.sources,
                store_results=not args.no_store
            )
            
            # Check quality gate
            success_rate = results["summary"].get("success_rate", 0)
            if success_rate < args.quality_gate:
                print(f"❌ Quality gate failed: {success_rate:.1f}% < {args.quality_gate}%")
                sys.exit(1)
            
            print(f"✅ Test results aggregated successfully")
            print(f"📊 Success rate: {success_rate:.1f}%")
            print(f"📄 Report: {results['report_path']}")
            
        elif args.command == "historical":
            report_path = aggregator.generate_historical_analysis(days=args.days)
            print(f"📈 Historical analysis report: {report_path}")
            
        elif args.command == "trends":
            trends = aggregator._get_recent_trends(days=args.days)
            print(f"📊 Test trends (last {args.days} days):")
            for metric, data in trends.items():
                if data:
                    latest = data[-1]['value']
                    print(f"  {metric}: {latest:.1f}")
        
    except Exception as e:
        print(f"❌ Test results aggregation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()