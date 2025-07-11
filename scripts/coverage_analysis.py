#!/usr/bin/env python3
"""
AI Trackdown PyTools - Coverage Analysis Tool

This script provides comprehensive coverage analysis and reporting capabilities
including gap analysis, trend tracking, and quality metrics.
"""
import argparse
import json
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
import csv


@dataclass
class CoverageMetrics:
    """Coverage metrics for a specific run."""
    timestamp: str
    total_statements: int
    covered_statements: int
    missing_statements: int
    line_coverage: float
    total_branches: int
    covered_branches: int
    missing_branches: int
    branch_coverage: float
    files_count: int
    files_with_full_coverage: int
    files_with_no_coverage: int


@dataclass
class FileCoverage:
    """Coverage information for a single file."""
    filename: str
    statements: int
    covered: int
    missing: int
    line_coverage: float
    branches: int
    partial_branches: int
    branch_coverage: float
    missing_lines: List[int]
    excluded_lines: List[int]


@dataclass
class CoverageGap:
    """Represents a coverage gap that needs attention."""
    filename: str
    gap_type: str  # 'uncovered_lines', 'uncovered_branches', 'low_coverage'
    severity: str  # 'critical', 'high', 'medium', 'low'
    description: str
    lines: List[int]
    suggested_tests: List[str]


class CoverageAnalyzer:
    """Main coverage analysis engine."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_dir = project_root / "coverage-reports"
        self.coverage_dir.mkdir(exist_ok=True)
        
        # Database for coverage trends
        self.db_path = self.coverage_dir / "coverage_trends.db"
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize SQLite database for coverage trends."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coverage_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_statements INTEGER,
                covered_statements INTEGER,
                line_coverage REAL,
                total_branches INTEGER,
                covered_branches INTEGER,
                branch_coverage REAL,
                files_count INTEGER,
                git_commit TEXT,
                git_branch TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_coverage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                filename TEXT,
                statements INTEGER,
                covered INTEGER,
                line_coverage REAL,
                branches INTEGER,
                branch_coverage REAL,
                FOREIGN KEY (run_id) REFERENCES coverage_runs (id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def run_coverage_analysis(self, 
                            test_path: Optional[str] = None,
                            output_formats: List[str] = None) -> CoverageMetrics:
        """Run coverage analysis with pytest."""
        if output_formats is None:
            output_formats = ['html', 'xml', 'json', 'lcov']
        
        print("🧪 Running coverage analysis...")
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=ai_trackdown_pytools",
            "--cov-branch",
        ]
        
        # Add output format options
        if 'html' in output_formats:
            cmd.append("--cov-report=html:htmlcov")
        if 'xml' in output_formats:
            cmd.append("--cov-report=xml:coverage.xml")
        if 'json' in output_formats:
            cmd.append("--cov-report=json:coverage.json")
        if 'lcov' in output_formats:
            cmd.append("--cov-report=lcov:coverage.lcov")
        
        cmd.append("--cov-report=term-missing")
        
        if test_path:
            cmd.append(test_path)
        
        # Run coverage
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False
            )
            
            print(f"✅ Coverage analysis completed (exit code: {result.returncode})")
            if result.stdout:
                print("📊 Coverage output:")
                print(result.stdout)
            
            return self._parse_coverage_results()
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Coverage analysis failed: {e}")
            raise
    
    def _parse_coverage_results(self) -> CoverageMetrics:
        """Parse coverage results from various output files."""
        timestamp = datetime.now().isoformat()
        
        # Parse XML coverage report
        xml_path = self.project_root / "coverage.xml"
        json_path = self.project_root / "coverage.json"
        
        if json_path.exists():
            return self._parse_json_coverage(json_path, timestamp)
        elif xml_path.exists():
            return self._parse_xml_coverage(xml_path, timestamp)
        else:
            raise FileNotFoundError("No coverage report files found")
    
    def _parse_json_coverage(self, json_path: Path, timestamp: str) -> CoverageMetrics:
        """Parse JSON coverage report."""
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        totals = data.get('totals', {})
        files = data.get('files', {})
        
        return CoverageMetrics(
            timestamp=timestamp,
            total_statements=totals.get('num_statements', 0),
            covered_statements=totals.get('covered_lines', 0),
            missing_statements=totals.get('missing_lines', 0),
            line_coverage=totals.get('percent_covered', 0.0),
            total_branches=totals.get('num_branches', 0),
            covered_branches=totals.get('covered_branches', 0),
            missing_branches=totals.get('missing_branches', 0),
            branch_coverage=totals.get('percent_covered_branches', 0.0),
            files_count=len(files),
            files_with_full_coverage=len([f for f in files.values() 
                                       if f.get('summary', {}).get('percent_covered', 0) == 100]),
            files_with_no_coverage=len([f for f in files.values() 
                                     if f.get('summary', {}).get('percent_covered', 0) == 0])
        )
    
    def _parse_xml_coverage(self, xml_path: Path, timestamp: str) -> CoverageMetrics:
        """Parse XML coverage report."""
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Get overall coverage from root element
        line_rate = float(root.get('line-rate', 0))
        branch_rate = float(root.get('branch-rate', 0))
        lines_valid = int(root.get('lines-valid', 0))
        lines_covered = int(root.get('lines-covered', 0))
        branches_valid = int(root.get('branches-valid', 0))
        branches_covered = int(root.get('branches-covered', 0))
        
        # Count files
        packages = root.findall('.//package')
        files_count = 0
        files_full_coverage = 0
        files_no_coverage = 0
        
        for package in packages:
            classes = package.findall('.//class')
            for cls in classes:
                files_count += 1
                cls_line_rate = float(cls.get('line-rate', 0))
                if cls_line_rate == 1.0:
                    files_full_coverage += 1
                elif cls_line_rate == 0.0:
                    files_no_coverage += 1
        
        return CoverageMetrics(
            timestamp=timestamp,
            total_statements=lines_valid,
            covered_statements=lines_covered,
            missing_statements=lines_valid - lines_covered,
            line_coverage=line_rate * 100,
            total_branches=branches_valid,
            covered_branches=branches_covered,
            missing_branches=branches_valid - branches_covered,
            branch_coverage=branch_rate * 100,
            files_count=files_count,
            files_with_full_coverage=files_full_coverage,
            files_with_no_coverage=files_no_coverage
        )
    
    def analyze_coverage_gaps(self) -> List[CoverageGap]:
        """Analyze coverage gaps and prioritize testing efforts."""
        print("🔍 Analyzing coverage gaps...")
        
        gaps = []
        json_path = self.project_root / "coverage.json"
        
        if not json_path.exists():
            print("⚠️  No JSON coverage report found. Run coverage analysis first.")
            return gaps
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        files = data.get('files', {})
        
        for filename, file_data in files.items():
            summary = file_data.get('summary', {})
            missing_lines = file_data.get('missing_lines', [])
            excluded_lines = file_data.get('excluded_lines', [])
            
            coverage_percent = summary.get('percent_covered', 0)
            
            # Determine severity based on coverage percentage and file importance
            if self._is_critical_file(filename):
                if coverage_percent < 50:
                    severity = 'critical'
                elif coverage_percent < 75:
                    severity = 'high'
                elif coverage_percent < 90:
                    severity = 'medium'
                else:
                    severity = 'low'
            else:
                if coverage_percent < 25:
                    severity = 'high'
                elif coverage_percent < 50:
                    severity = 'medium'
                else:
                    severity = 'low'
            
            if missing_lines:
                gap = CoverageGap(
                    filename=filename,
                    gap_type='uncovered_lines',
                    severity=severity,
                    description=f"File has {len(missing_lines)} uncovered lines ({coverage_percent:.1f}% coverage)",
                    lines=missing_lines,
                    suggested_tests=self._suggest_tests_for_file(filename, missing_lines)
                )
                gaps.append(gap)
        
        # Sort by severity
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        gaps.sort(key=lambda x: (severity_order[x.severity], x.filename))
        
        return gaps
    
    def _is_critical_file(self, filename: str) -> bool:
        """Determine if a file is critical (core functionality)."""
        critical_patterns = [
            '/core/',
            '/cli.py',
            '/models.py',
            '/config.py',
            '/task.py',
            '/project.py'
        ]
        return any(pattern in filename for pattern in critical_patterns)
    
    def _suggest_tests_for_file(self, filename: str, missing_lines: List[int]) -> List[str]:
        """Suggest test types for uncovered lines in a file."""
        suggestions = []
        
        if '/cli.py' in filename or '/commands/' in filename:
            suggestions.extend([
                "Add CLI integration tests",
                "Test command-line argument parsing",
                "Test error handling and validation"
            ])
        elif '/core/' in filename:
            suggestions.extend([
                "Add unit tests for core functionality",
                "Test edge cases and error conditions",
                "Add integration tests for component interaction"
            ])
        elif '/utils/' in filename:
            suggestions.extend([
                "Add utility function unit tests",
                "Test input validation and error handling",
                "Test different input scenarios"
            ])
        else:
            suggestions.append("Add comprehensive unit tests")
        
        return suggestions
    
    def generate_coverage_report(self, metrics: CoverageMetrics, gaps: List[CoverageGap]) -> str:
        """Generate comprehensive coverage analysis report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
# Coverage Analysis Report
Generated: {timestamp}

## Overall Coverage Metrics

- **Line Coverage**: {metrics.line_coverage:.2f}% ({metrics.covered_statements}/{metrics.total_statements} lines)
- **Branch Coverage**: {metrics.branch_coverage:.2f}% ({metrics.covered_branches}/{metrics.total_branches} branches)
- **Files Analyzed**: {metrics.files_count}
- **Files with 100% Coverage**: {metrics.files_with_full_coverage}
- **Files with 0% Coverage**: {metrics.files_with_no_coverage}

## Coverage Quality Assessment

"""
        
        # Coverage quality assessment
        if metrics.line_coverage >= 90:
            quality = "🟢 Excellent"
        elif metrics.line_coverage >= 75:
            quality = "🟡 Good"
        elif metrics.line_coverage >= 50:
            quality = "🟠 Fair"
        else:
            quality = "🔴 Poor"
        
        report += f"**Overall Quality**: {quality} ({metrics.line_coverage:.1f}%)\n\n"
        
        # Coverage gaps analysis
        if gaps:
            report += "## Coverage Gaps Analysis\n\n"
            
            # Group gaps by severity
            gaps_by_severity = {}
            for gap in gaps:
                if gap.severity not in gaps_by_severity:
                    gaps_by_severity[gap.severity] = []
                gaps_by_severity[gap.severity].append(gap)
            
            for severity in ['critical', 'high', 'medium', 'low']:
                if severity in gaps_by_severity:
                    severity_emoji = {
                        'critical': '🚨',
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }
                    
                    report += f"### {severity_emoji[severity]} {severity.title()} Priority\n\n"
                    
                    for gap in gaps_by_severity[severity][:5]:  # Limit to top 5 per severity
                        report += f"**{gap.filename}**\n"
                        report += f"- {gap.description}\n"
                        report += f"- Uncovered lines: {len(gap.lines)}\n"
                        if gap.suggested_tests:
                            report += f"- Suggested tests: {', '.join(gap.suggested_tests[:3])}\n"
                        report += "\n"
        
        # Recommendations
        report += "## Recommendations\n\n"
        
        if metrics.line_coverage < 85:
            report += "1. **Increase overall coverage** to reach the 85% target\n"
        
        if gaps:
            critical_gaps = [g for g in gaps if g.severity == 'critical']
            if critical_gaps:
                report += f"2. **Address {len(critical_gaps)} critical coverage gaps** immediately\n"
        
        if metrics.files_with_no_coverage > 0:
            report += f"3. **Add basic tests** for {metrics.files_with_no_coverage} untested files\n"
        
        if metrics.branch_coverage < metrics.line_coverage:
            report += "4. **Improve branch coverage** by testing conditional logic paths\n"
        
        report += "\n## Next Steps\n\n"
        report += "1. Run `make test-cov` to generate detailed coverage reports\n"
        report += "2. Review HTML coverage report in `htmlcov/index.html`\n"
        report += "3. Focus on critical and high-priority gaps first\n"
        report += "4. Add tests for core functionality modules\n"
        report += "5. Set up coverage monitoring in CI/CD pipeline\n"
        
        return report
    
    def save_coverage_trend(self, metrics: CoverageMetrics) -> None:
        """Save coverage metrics to trend database."""
        # Get git information
        git_commit = self._get_git_commit()
        git_branch = self._get_git_branch()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO coverage_runs 
            (timestamp, total_statements, covered_statements, line_coverage,
             total_branches, covered_branches, branch_coverage, files_count,
             git_commit, git_branch)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metrics.timestamp,
            metrics.total_statements,
            metrics.covered_statements,
            metrics.line_coverage,
            metrics.total_branches,
            metrics.covered_branches,
            metrics.branch_coverage,
            metrics.files_count,
            git_commit,
            git_branch
        ))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Coverage trend saved to database")
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def _get_git_branch(self) -> Optional[str]:
        """Get current git branch name."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return None
    
    def generate_coverage_badge(self, metrics: CoverageMetrics) -> str:
        """Generate coverage badge SVG."""
        coverage = metrics.line_coverage
        
        # Determine color based on coverage percentage
        if coverage >= 90:
            color = "brightgreen"
        elif coverage >= 75:
            color = "green"
        elif coverage >= 60:
            color = "yellowgreen"
        elif coverage >= 40:
            color = "yellow"
        else:
            color = "red"
        
        badge_url = f"https://img.shields.io/badge/coverage-{coverage:.1f}%25-{color}"
        
        return f"![Coverage]({badge_url})"
    
    def export_coverage_csv(self, output_path: Path) -> None:
        """Export coverage trends to CSV."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, line_coverage, branch_coverage, 
                   total_statements, covered_statements, files_count,
                   git_commit, git_branch
            FROM coverage_runs 
            ORDER BY timestamp DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'Timestamp', 'Line Coverage %', 'Branch Coverage %',
                'Total Statements', 'Covered Statements', 'Files Count',
                'Git Commit', 'Git Branch'
            ])
            writer.writerows(rows)
        
        print(f"📊 Coverage trends exported to {output_path}")


def main():
    """Main CLI interface for coverage analysis."""
    parser = argparse.ArgumentParser(
        description="AI Trackdown PyTools Coverage Analysis Tool"
    )
    
    parser.add_argument(
        "--analyze", action="store_true",
        help="Run coverage analysis"
    )
    
    parser.add_argument(
        "--test-path", 
        help="Specific test path to analyze"
    )
    
    parser.add_argument(
        "--formats", nargs="+", 
        choices=["html", "xml", "json", "lcov"],
        default=["html", "xml", "json"],
        help="Output formats to generate"
    )
    
    parser.add_argument(
        "--report", action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--gaps", action="store_true",
        help="Analyze coverage gaps"
    )
    
    parser.add_argument(
        "--trends", action="store_true",
        help="Show coverage trends"
    )
    
    parser.add_argument(
        "--export-csv", 
        help="Export coverage trends to CSV file"
    )
    
    parser.add_argument(
        "--badge", action="store_true",
        help="Generate coverage badge"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Not in a Python project directory (no pyproject.toml found)")
        sys.exit(1)
    
    analyzer = CoverageAnalyzer(project_root)
    
    if args.analyze:
        metrics = analyzer.run_coverage_analysis(
            test_path=args.test_path,
            output_formats=args.formats
        )
        analyzer.save_coverage_trend(metrics)
        
        if args.gaps:
            gaps = analyzer.analyze_coverage_gaps()
            
            if args.report:
                report = analyzer.generate_coverage_report(metrics, gaps)
                report_path = project_root / "coverage-reports" / "coverage-analysis.md"
                report_path.parent.mkdir(exist_ok=True)
                
                with open(report_path, 'w') as f:
                    f.write(report)
                
                print(f"📋 Coverage report generated: {report_path}")
                print(report)
        
        if args.badge:
            badge = analyzer.generate_coverage_badge(metrics)
            print(f"🏷️  Coverage badge: {badge}")
    
    elif args.gaps:
        gaps = analyzer.analyze_coverage_gaps()
        if gaps:
            print(f"\n🔍 Found {len(gaps)} coverage gaps:")
            for gap in gaps[:10]:  # Show top 10
                print(f"  {gap.severity.upper()}: {gap.filename} - {gap.description}")
        else:
            print("✅ No significant coverage gaps found!")
    
    elif args.export_csv and args.export_csv:
        analyzer.export_coverage_csv(Path(args.export_csv))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()