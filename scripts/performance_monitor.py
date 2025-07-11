#!/usr/bin/env python3
"""
AI Trackdown PyTools - Performance Monitoring and Benchmarking System

This script provides comprehensive performance monitoring, benchmarking,
and regression detection for the AI Trackdown PyTools project.
"""

import argparse
import json
import os
import sys
import time
import sqlite3
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import subprocess
import psutil
import pytest
from contextlib import contextmanager
import threading
import gc
import tracemalloc


class PerformanceMonitor:
    """Advanced performance monitoring and benchmarking system."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.benchmark_db = project_root / "performance_data.db"
        self.reports_dir = project_root / "performance-reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # Initialize performance database
        self._init_database()
        
        # Performance thresholds
        self.thresholds = {
            "test_execution_time_seconds": 300,  # 5 minutes max
            "memory_usage_mb": 1000,  # 1GB max
            "coverage_analysis_seconds": 60,  # 1 minute max
            "cli_response_time_ms": 500,  # 500ms max
            "import_time_ms": 100,  # 100ms max
        }
    
    def _init_database(self) -> None:
        """Initialize performance tracking database."""
        with sqlite3.connect(self.benchmark_db) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS performance_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    commit_hash TEXT,
                    branch TEXT,
                    python_version TEXT,
                    platform TEXT,
                    ci_environment BOOLEAN DEFAULT FALSE
                );
                
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    test_name TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES performance_runs (id)
                );
                
                CREATE TABLE IF NOT EXISTS memory_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    function_name TEXT NOT NULL,
                    peak_memory_mb REAL NOT NULL,
                    memory_growth_mb REAL,
                    allocations_count INTEGER,
                    FOREIGN KEY (run_id) REFERENCES performance_runs (id)
                );
                
                CREATE TABLE IF NOT EXISTS regression_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    metric_name TEXT NOT NULL,
                    current_value REAL NOT NULL,
                    baseline_value REAL NOT NULL,
                    regression_percentage REAL NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES performance_runs (id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_benchmarks_test_metric ON benchmarks (test_name, metric_name);
                CREATE INDEX IF NOT EXISTS idx_performance_runs_timestamp ON performance_runs (timestamp);
            """)
    
    @contextmanager
    def _performance_context(self, test_name: str):
        """Context manager for performance measurement."""
        # Start memory tracking
        tracemalloc.start()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        start_time = time.perf_counter()
        
        try:
            yield
        finally:
            # Capture performance metrics
            end_time = time.perf_counter()
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            
            # Memory profiling
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            execution_time = end_time - start_time
            memory_growth = end_memory - start_memory
            peak_memory_mb = peak / 1024 / 1024
            
            print(f"📊 Performance metrics for {test_name}:")
            print(f"   ⏱️  Execution time: {execution_time:.3f}s")
            print(f"   🧠 Memory growth: {memory_growth:.1f}MB")
            print(f"   📈 Peak memory: {peak_memory_mb:.1f}MB")
    
    def run_performance_benchmarks(self, 
                                 benchmark_type: str = "full",
                                 store_results: bool = True) -> Dict[str, Any]:
        """Run comprehensive performance benchmarks."""
        print("🚀 Starting performance benchmark suite...")
        
        # Create performance run record
        run_id = None
        if store_results:
            run_id = self._create_performance_run()
        
        results = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "benchmark_type": benchmark_type,
            "benchmarks": {},
            "memory_profiles": {},
            "regressions": []
        }
        
        # 1. Test execution benchmarks
        if benchmark_type in ["full", "tests"]:
            print("\n🧪 Running test execution benchmarks...")
            test_benchmarks = self._benchmark_test_execution()
            results["benchmarks"].update(test_benchmarks)
        
        # 2. CLI performance benchmarks
        if benchmark_type in ["full", "cli"]:
            print("\n💻 Running CLI performance benchmarks...")
            cli_benchmarks = self._benchmark_cli_performance()
            results["benchmarks"].update(cli_benchmarks)
        
        # 3. Import performance benchmarks
        if benchmark_type in ["full", "imports"]:
            print("\n📦 Running import performance benchmarks...")
            import_benchmarks = self._benchmark_import_performance()
            results["benchmarks"].update(import_benchmarks)
        
        # 4. Memory usage benchmarks
        if benchmark_type in ["full", "memory"]:
            print("\n🧠 Running memory usage benchmarks...")
            memory_benchmarks = self._benchmark_memory_usage()
            results["benchmarks"].update(memory_benchmarks)
            results["memory_profiles"] = memory_benchmarks.get("profiles", {})
        
        # 5. Coverage analysis benchmarks
        if benchmark_type in ["full", "coverage"]:
            print("\n📊 Running coverage analysis benchmarks...")
            coverage_benchmarks = self._benchmark_coverage_analysis()
            results["benchmarks"].update(coverage_benchmarks)
        
        # Store results and check for regressions
        if store_results and run_id:
            self._store_benchmark_results(run_id, results)
            regressions = self._check_for_regressions(run_id, results["benchmarks"])
            results["regressions"] = regressions
        
        # Generate performance report
        report_path = self._generate_performance_report(results)
        results["report_path"] = str(report_path)
        
        print(f"\n✅ Performance benchmarks completed")
        print(f"📄 Report saved: {report_path}")
        
        return results
    
    def _benchmark_test_execution(self) -> Dict[str, float]:
        """Benchmark test execution performance."""
        benchmarks = {}
        
        test_suites = [
            ("unit_tests", ["tests/unit/"]),
            ("integration_tests", ["tests/integration/"]),
            ("cli_tests", ["tests/cli/"]),
            ("full_test_suite", ["tests/"]),
        ]
        
        for suite_name, test_paths in test_suites:
            print(f"   🔍 Benchmarking {suite_name}...")
            
            with self._performance_context(suite_name):
                start_time = time.perf_counter()
                
                # Run pytest with minimal output for performance testing
                cmd = [
                    sys.executable, "-m", "pytest",
                    "--quiet",
                    "--tb=no",
                    "--disable-warnings",
                    *test_paths
                ]
                
                try:
                    result = subprocess.run(
                        cmd,
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=self.thresholds["test_execution_time_seconds"]
                    )
                    
                    execution_time = time.perf_counter() - start_time
                    benchmarks[f"{suite_name}_execution_time_seconds"] = execution_time
                    benchmarks[f"{suite_name}_success"] = result.returncode == 0
                    
                    print(f"     ✅ {suite_name}: {execution_time:.2f}s")
                    
                except subprocess.TimeoutExpired:
                    benchmarks[f"{suite_name}_execution_time_seconds"] = self.thresholds["test_execution_time_seconds"]
                    benchmarks[f"{suite_name}_success"] = False
                    print(f"     ⚠️ {suite_name}: TIMEOUT")
        
        return benchmarks
    
    def _benchmark_cli_performance(self) -> Dict[str, float]:
        """Benchmark CLI command performance."""
        benchmarks = {}
        
        cli_commands = [
            ("help", ["aitrackdown", "--help"]),
            ("version", ["aitrackdown", "--version"]),
            ("status", ["aitrackdown", "status"]),
            ("health", ["aitrackdown", "health"]),
        ]
        
        for cmd_name, cmd_args in cli_commands:
            print(f"   🔍 Benchmarking CLI command: {cmd_name}...")
            
            times = []
            for i in range(5):  # Run multiple times for average
                start_time = time.perf_counter()
                
                try:
                    result = subprocess.run(
                        cmd_args,
                        cwd=self.project_root,
                        capture_output=True,
                        text=True,
                        timeout=5  # 5 second timeout
                    )
                    
                    execution_time = time.perf_counter() - start_time
                    times.append(execution_time * 1000)  # Convert to milliseconds
                    
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    times.append(5000)  # 5 second timeout as ms
            
            avg_time = statistics.mean(times)
            benchmarks[f"cli_{cmd_name}_response_time_ms"] = avg_time
            benchmarks[f"cli_{cmd_name}_success"] = avg_time < self.thresholds["cli_response_time_ms"]
            
            print(f"     ✅ CLI {cmd_name}: {avg_time:.1f}ms (avg)")
        
        return benchmarks
    
    def _benchmark_import_performance(self) -> Dict[str, float]:
        """Benchmark module import performance."""
        benchmarks = {}
        
        imports_to_test = [
            ("main_package", "import ai_trackdown_pytools"),
            ("cli_module", "from ai_trackdown_pytools import cli"),
            ("core_models", "from ai_trackdown_pytools.core import models"),
            ("utils", "from ai_trackdown_pytools.utils import validation"),
        ]
        
        for import_name, import_statement in imports_to_test:
            print(f"   🔍 Benchmarking import: {import_name}...")
            
            times = []
            for i in range(10):  # Multiple runs for accuracy
                # Clear module cache to ensure fresh import
                modules_to_clear = [k for k in sys.modules.keys() if k.startswith('ai_trackdown_pytools')]
                for module in modules_to_clear:
                    if module in sys.modules:
                        del sys.modules[module]
                
                start_time = time.perf_counter()
                
                try:
                    exec(import_statement)
                    execution_time = time.perf_counter() - start_time
                    times.append(execution_time * 1000)  # Convert to milliseconds
                except ImportError:
                    times.append(1000)  # 1 second penalty for failed import
            
            avg_time = statistics.mean(times)
            benchmarks[f"import_{import_name}_time_ms"] = avg_time
            benchmarks[f"import_{import_name}_success"] = avg_time < self.thresholds["import_time_ms"]
            
            print(f"     ✅ Import {import_name}: {avg_time:.1f}ms (avg)")
        
        return benchmarks
    
    def _benchmark_memory_usage(self) -> Dict[str, Any]:
        """Benchmark memory usage patterns."""
        benchmarks = {}
        profiles = {}
        
        # Test memory usage of key operations
        operations = [
            ("project_initialization", self._memory_test_project_init),
            ("large_task_processing", self._memory_test_large_tasks),
            ("concurrent_operations", self._memory_test_concurrent_ops),
        ]
        
        for op_name, op_func in operations:
            print(f"   🔍 Memory profiling: {op_name}...")
            
            # Clear memory before test
            gc.collect()
            tracemalloc.start()
            
            start_memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            try:
                result = op_func()
                
                end_memory = psutil.Process().memory_info().rss / 1024 / 1024
                current, peak = tracemalloc.get_traced_memory()
                
                memory_growth = end_memory - start_memory
                peak_memory_mb = peak / 1024 / 1024
                
                benchmarks[f"memory_{op_name}_growth_mb"] = memory_growth
                benchmarks[f"memory_{op_name}_peak_mb"] = peak_memory_mb
                benchmarks[f"memory_{op_name}_within_limits"] = peak_memory_mb < self.thresholds["memory_usage_mb"]
                
                profiles[op_name] = {
                    "growth_mb": memory_growth,
                    "peak_mb": peak_memory_mb,
                    "result": result
                }
                
                print(f"     ✅ {op_name}: Growth {memory_growth:.1f}MB, Peak {peak_memory_mb:.1f}MB")
                
            except Exception as e:
                print(f"     ❌ {op_name}: Error - {e}")
                benchmarks[f"memory_{op_name}_error"] = True
            
            finally:
                tracemalloc.stop()
                gc.collect()
        
        benchmarks["profiles"] = profiles
        return benchmarks
    
    def _memory_test_project_init(self) -> Dict:
        """Test memory usage of project initialization."""
        from ai_trackdown_pytools.core.project import Project
        
        # Simulate project initialization
        projects = []
        for i in range(10):
            project = Project(name=f"test_project_{i}", path=f"/tmp/test_{i}")
            projects.append(project)
        
        return {"projects_created": len(projects)}
    
    def _memory_test_large_tasks(self) -> Dict:
        """Test memory usage with large task sets."""
        from ai_trackdown_pytools.core.task import Task
        
        # Create large number of tasks
        tasks = []
        for i in range(1000):
            task = Task(
                title=f"Task {i}",
                description=f"Description for task {i}" * 10,  # Make it larger
                metadata={"index": i, "data": list(range(100))}
            )
            tasks.append(task)
        
        return {"tasks_created": len(tasks)}
    
    def _memory_test_concurrent_ops(self) -> Dict:
        """Test memory usage under concurrent operations."""
        import threading
        import time
        
        results = []
        
        def worker(worker_id):
            from ai_trackdown_pytools.core.models import ProjectModel
            
            # Simulate concurrent work
            for i in range(50):
                model = ProjectModel(
                    name=f"project_{worker_id}_{i}",
                    path=f"/tmp/concurrent_{worker_id}_{i}"
                )
                results.append(model)
                time.sleep(0.001)  # Small delay
        
        # Run concurrent workers
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        return {"concurrent_results": len(results)}
    
    def _benchmark_coverage_analysis(self) -> Dict[str, float]:
        """Benchmark coverage analysis performance."""
        benchmarks = {}
        
        print("   🔍 Benchmarking coverage analysis...")
        
        with self._performance_context("coverage_analysis"):
            start_time = time.perf_counter()
            
            # Run coverage analysis
            try:
                result = subprocess.run([
                    sys.executable, "scripts/coverage_analysis.py",
                    "--analyze", "--report"
                ], 
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=self.thresholds["coverage_analysis_seconds"]
                )
                
                execution_time = time.perf_counter() - start_time
                benchmarks["coverage_analysis_time_seconds"] = execution_time
                benchmarks["coverage_analysis_success"] = result.returncode == 0
                
                print(f"     ✅ Coverage analysis: {execution_time:.2f}s")
                
            except subprocess.TimeoutExpired:
                benchmarks["coverage_analysis_time_seconds"] = self.thresholds["coverage_analysis_seconds"]
                benchmarks["coverage_analysis_success"] = False
                print("     ⚠️ Coverage analysis: TIMEOUT")
        
        return benchmarks
    
    def _create_performance_run(self) -> int:
        """Create a new performance run record."""
        git_info = self._get_git_info()
        
        with sqlite3.connect(self.benchmark_db) as conn:
            cursor = conn.execute("""
                INSERT INTO performance_runs 
                (timestamp, commit_hash, branch, python_version, platform, ci_environment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                git_info.get("commit_hash", "unknown"),
                git_info.get("branch", "unknown"),
                f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                sys.platform,
                os.getenv("CI", "false").lower() == "true"
            ))
            
            return cursor.lastrowid
    
    def _get_git_info(self) -> Dict[str, str]:
        """Get current git information."""
        try:
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
    
    def _store_benchmark_results(self, run_id: int, results: Dict[str, Any]) -> None:
        """Store benchmark results in database."""
        with sqlite3.connect(self.benchmark_db) as conn:
            for metric_name, value in results["benchmarks"].items():
                if isinstance(value, (int, float)):
                    # Determine unit from metric name
                    unit = "count"
                    if "time" in metric_name:
                        if "ms" in metric_name:
                            unit = "milliseconds"
                        else:
                            unit = "seconds"
                    elif "memory" in metric_name or "mb" in metric_name:
                        unit = "megabytes"
                    elif "success" in metric_name:
                        unit = "boolean"
                    
                    conn.execute("""
                        INSERT INTO benchmarks (run_id, test_name, metric_name, value, unit)
                        VALUES (?, ?, ?, ?, ?)
                    """, (run_id, "performance_suite", metric_name, float(value), unit))
    
    def _check_for_regressions(self, run_id: int, current_benchmarks: Dict[str, float]) -> List[Dict]:
        """Check for performance regressions."""
        regressions = []
        
        with sqlite3.connect(self.benchmark_db) as conn:
            for metric_name, current_value in current_benchmarks.items():
                if not isinstance(current_value, (int, float)):
                    continue
                
                # Get historical data for this metric
                cursor = conn.execute("""
                    SELECT AVG(value) as baseline
                    FROM benchmarks b
                    JOIN performance_runs pr ON b.run_id = pr.id
                    WHERE b.metric_name = ?
                    AND pr.timestamp > datetime('now', '-30 days')
                    AND b.run_id != ?
                """, (metric_name, run_id))
                
                result = cursor.fetchone()
                if result and result[0] is not None:
                    baseline = result[0]
                    
                    # Calculate regression percentage
                    if "time" in metric_name or "memory" in metric_name:
                        # For time/memory metrics, higher is worse
                        regression_pct = ((current_value - baseline) / baseline) * 100 if baseline > 0 else 0
                    else:
                        # For other metrics, lower might be worse
                        regression_pct = ((baseline - current_value) / baseline) * 100 if baseline > 0 else 0
                    
                    # Check for significant regression
                    if regression_pct > 20:  # 20% regression threshold
                        severity = "critical" if regression_pct > 50 else "warning"
                        
                        regression = {
                            "metric": metric_name,
                            "current_value": current_value,
                            "baseline_value": baseline,
                            "regression_percentage": regression_pct,
                            "severity": severity
                        }
                        
                        regressions.append(regression)
                        
                        # Store regression alert
                        conn.execute("""
                            INSERT INTO regression_alerts 
                            (run_id, metric_name, current_value, baseline_value, 
                             regression_percentage, severity, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            run_id, metric_name, current_value, baseline,
                            regression_pct, severity, datetime.now().isoformat()
                        ))
        
        return regressions
    
    def _generate_performance_report(self, results: Dict[str, Any]) -> Path:
        """Generate comprehensive performance report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"performance_report_{timestamp}.md"
        
        with open(report_path, "w") as f:
            f.write(f"""# Performance Benchmark Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Benchmark Type**: {results['benchmark_type']}
**Run ID**: {results.get('run_id', 'N/A')}

## Executive Summary

""")
            
            # Overall status
            total_benchmarks = len(results["benchmarks"])
            successful_benchmarks = sum(1 for k, v in results["benchmarks"].items() 
                                      if "success" in k and v is True)
            
            f.write(f"- **Total Benchmarks**: {total_benchmarks}\n")
            f.write(f"- **Successful**: {successful_benchmarks}\n")
            f.write(f"- **Regressions Detected**: {len(results['regressions'])}\n\n")
            
            # Performance benchmarks
            f.write("## Performance Benchmarks\n\n")
            f.write("| Metric | Value | Status |\n")
            f.write("|--------|-------|--------|\n")
            
            for metric, value in sorted(results["benchmarks"].items()):
                if isinstance(value, (int, float)):
                    # Determine status
                    status = "✅"
                    if "time" in metric and "seconds" in metric and value > 60:
                        status = "⚠️"
                    elif "time" in metric and "ms" in metric and value > 1000:
                        status = "⚠️"
                    elif "memory" in metric and value > 500:
                        status = "⚠️"
                    
                    # Format value
                    if isinstance(value, float):
                        formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = str(value)
                    
                    f.write(f"| {metric} | {formatted_value} | {status} |\n")
            
            # Regressions
            if results["regressions"]:
                f.write("\n## 🚨 Performance Regressions\n\n")
                for regression in results["regressions"]:
                    severity_emoji = "🔴" if regression["severity"] == "critical" else "🟡"
                    f.write(f"### {severity_emoji} {regression['metric']}\n\n")
                    f.write(f"- **Current Value**: {regression['current_value']:.2f}\n")
                    f.write(f"- **Baseline Value**: {regression['baseline_value']:.2f}\n")
                    f.write(f"- **Regression**: {regression['regression_percentage']:.1f}%\n")
                    f.write(f"- **Severity**: {regression['severity']}\n\n")
            
            # Memory profiles
            if results.get("memory_profiles"):
                f.write("## Memory Usage Profiles\n\n")
                for profile_name, profile_data in results["memory_profiles"].items():
                    f.write(f"### {profile_name}\n\n")
                    f.write(f"- **Memory Growth**: {profile_data['growth_mb']:.1f} MB\n")
                    f.write(f"- **Peak Memory**: {profile_data['peak_mb']:.1f} MB\n\n")
            
            # Recommendations
            f.write("## Recommendations\n\n")
            if results["regressions"]:
                f.write("### Immediate Actions Required\n\n")
                for regression in results["regressions"]:
                    if regression["severity"] == "critical":
                        f.write(f"- 🔴 **Critical**: Investigate {regression['metric']} regression\n")
                
                f.write("\n### Performance Optimization Opportunities\n\n")
                for regression in results["regressions"]:
                    if regression["severity"] == "warning":
                        f.write(f"- 🟡 **Warning**: Monitor {regression['metric']} trends\n")
            else:
                f.write("- ✅ No performance regressions detected\n")
                f.write("- 📈 Continue monitoring performance trends\n")
                f.write("- 🎯 Consider optimization opportunities for high-usage scenarios\n")
            
            # Appendix
            f.write("\n## Appendix\n\n")
            f.write("### Environment Information\n\n")
            f.write(f"- **Python Version**: {sys.version}\n")
            f.write(f"- **Platform**: {sys.platform}\n")
            f.write(f"- **CPU Count**: {psutil.cpu_count()}\n")
            f.write(f"- **Total Memory**: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} GB\n")
            
            f.write("\n### Benchmark Details\n\n")
            f.write("See performance database for historical trends and detailed metrics.\n")
        
        return report_path
    
    def generate_trends_report(self, days: int = 30) -> Path:
        """Generate performance trends report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.reports_dir / f"performance_trends_{timestamp}.md"
        
        with sqlite3.connect(self.benchmark_db) as conn:
            # Get performance trends
            cursor = conn.execute("""
                SELECT 
                    pr.timestamp,
                    pr.commit_hash,
                    pr.branch,
                    b.metric_name,
                    b.value
                FROM performance_runs pr
                JOIN benchmarks b ON pr.id = b.run_id
                WHERE pr.timestamp > datetime('now', '-{} days')
                ORDER BY pr.timestamp DESC, b.metric_name
            """.format(days))
            
            trends_data = cursor.fetchall()
        
        # Generate trends report
        with open(report_path, "w") as f:
            f.write(f"""# Performance Trends Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Period**: Last {days} days
**Data Points**: {len(trends_data)}

## Trend Analysis

""")
            
            if trends_data:
                # Group by metric
                metrics = {}
                for timestamp, commit, branch, metric, value in trends_data:
                    if metric not in metrics:
                        metrics[metric] = []
                    metrics[metric].append((timestamp, value))
                
                for metric, values in metrics.items():
                    if len(values) > 1:
                        trend_direction = "📈" if values[0][1] > values[-1][1] else "📉"
                        f.write(f"### {trend_direction} {metric}\n\n")
                        f.write(f"- **Recent Value**: {values[0][1]:.2f}\n")
                        f.write(f"- **Oldest Value**: {values[-1][1]:.2f}\n")
                        f.write(f"- **Data Points**: {len(values)}\n\n")
            else:
                f.write("No performance data available for the specified period.\n")
        
        return report_path


def main():
    """Main CLI interface for performance monitoring."""
    parser = argparse.ArgumentParser(
        description="AI Trackdown PyTools Performance Monitor"
    )
    
    parser.add_argument(
        "command",
        choices=["benchmark", "trends", "regressions"],
        help="Command to run"
    )
    
    parser.add_argument(
        "--type", default="full",
        choices=["full", "tests", "cli", "imports", "memory", "coverage"],
        help="Type of benchmarks to run"
    )
    
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of days for trends analysis"
    )
    
    parser.add_argument(
        "--no-store", action="store_true",
        help="Don't store results in database"
    )
    
    parser.add_argument(
        "--threshold-check", action="store_true",
        help="Exit with error code if thresholds exceeded"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Not in a Python project directory")
        sys.exit(1)
    
    monitor = PerformanceMonitor(project_root)
    
    try:
        if args.command == "benchmark":
            results = monitor.run_performance_benchmarks(
                benchmark_type=args.type,
                store_results=not args.no_store
            )
            
            # Check thresholds if requested
            if args.threshold_check and results["regressions"]:
                critical_regressions = [r for r in results["regressions"] 
                                      if r["severity"] == "critical"]
                if critical_regressions:
                    print(f"❌ Critical performance regressions detected: {len(critical_regressions)}")
                    sys.exit(1)
            
            print(f"✅ Performance benchmarks completed successfully")
            
        elif args.command == "trends":
            report_path = monitor.generate_trends_report(days=args.days)
            print(f"📈 Performance trends report generated: {report_path}")
            
        elif args.command == "regressions":
            # Check for recent regressions
            with sqlite3.connect(monitor.benchmark_db) as conn:
                cursor = conn.execute("""
                    SELECT metric_name, regression_percentage, severity
                    FROM regression_alerts
                    WHERE timestamp > datetime('now', '-7 days')
                    ORDER BY regression_percentage DESC
                """)
                regressions = cursor.fetchall()
            
            if regressions:
                print("🚨 Recent performance regressions:")
                for metric, percentage, severity in regressions:
                    emoji = "🔴" if severity == "critical" else "🟡"
                    print(f"  {emoji} {metric}: {percentage:.1f}% regression ({severity})")
                
                if any(severity == "critical" for _, _, severity in regressions):
                    sys.exit(1)
            else:
                print("✅ No recent performance regressions detected")
        
    except Exception as e:
        print(f"❌ Performance monitoring failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()