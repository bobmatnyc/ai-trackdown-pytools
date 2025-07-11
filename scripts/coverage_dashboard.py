#!/usr/bin/env python3
"""
AI Trackdown PyTools - Coverage Dashboard

This script generates an interactive coverage dashboard with trends,
gap analysis, and actionable insights for improving test coverage.
"""
import argparse
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import sys


class CoverageDashboard:
    """Interactive coverage dashboard generator."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.coverage_dir = project_root / "coverage-reports"
        self.coverage_dir.mkdir(exist_ok=True)
        
        # Database for trends
        self.db_path = self.coverage_dir / "coverage_trends.db"
    
    def generate_dashboard(self, output_format: str = "html") -> str:
        """Generate comprehensive coverage dashboard."""
        print("📊 Generating coverage dashboard...")
        
        # Get current coverage data
        current_coverage = self._get_current_coverage()
        
        # Get trend data
        trend_data = self._get_trend_data()
        
        # Get gap analysis
        gap_analysis = self._get_gap_analysis()
        
        # Get quality metrics
        quality_metrics = self._get_quality_metrics()
        
        if output_format == "html":
            return self._generate_html_dashboard(
                current_coverage, trend_data, gap_analysis, quality_metrics
            )
        elif output_format == "json":
            return self._generate_json_dashboard(
                current_coverage, trend_data, gap_analysis, quality_metrics
            )
        else:
            return self._generate_text_dashboard(
                current_coverage, trend_data, gap_analysis, quality_metrics
            )
    
    def _get_current_coverage(self) -> Dict:
        """Get current coverage metrics."""
        json_path = self.project_root / "coverage.json"
        
        if not json_path.exists():
            print("⚠️  No coverage data found. Running coverage analysis...")
            self._run_coverage_analysis()
        
        if json_path.exists():
            with open(json_path, "r") as f:
                data = json.load(f)
                return data.get("totals", {})
        
        return {}
    
    def _get_trend_data(self, days: int = 30) -> List[Dict]:
        """Get coverage trend data from database."""
        if not self.db_path.exists():
            return []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get last 30 days of data
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT timestamp, line_coverage, branch_coverage, 
                   total_statements, covered_statements,
                   git_commit, git_branch
            FROM coverage_runs 
            WHERE timestamp >= ?
            ORDER BY timestamp ASC
        """, (since_date,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "timestamp": row[0],
                "line_coverage": row[1],
                "branch_coverage": row[2],
                "total_statements": row[3],
                "covered_statements": row[4],
                "git_commit": row[5],
                "git_branch": row[6],
            }
            for row in rows
        ]
    
    def _get_gap_analysis(self) -> Dict:
        """Get coverage gap analysis."""
        json_path = self.project_root / "coverage.json"
        
        if not json_path.exists():
            return {}
        
        with open(json_path, "r") as f:
            data = json.load(f)
        
        files = data.get("files", {})
        gaps = []
        
        for filename, file_data in files.items():
            summary = file_data.get("summary", {})
            coverage = summary.get("percent_covered", 0)
            missing_lines = file_data.get("missing_lines", [])
            
            if coverage < 85:  # Below target threshold
                priority = self._calculate_gap_priority(filename, coverage, len(missing_lines))
                gaps.append({
                    "filename": filename,
                    "coverage": coverage,
                    "missing_lines": len(missing_lines),
                    "priority": priority,
                    "category": self._categorize_file(filename),
                })
        
        # Sort by priority
        gaps.sort(key=lambda x: (x["priority"], -x["missing_lines"]))
        
        return {
            "total_gaps": len(gaps),
            "critical_gaps": len([g for g in gaps if g["priority"] == "critical"]),
            "high_gaps": len([g for g in gaps if g["priority"] == "high"]),
            "medium_gaps": len([g for g in gaps if g["priority"] == "medium"]),
            "gaps": gaps[:20],  # Top 20 gaps
        }
    
    def _get_quality_metrics(self) -> Dict:
        """Calculate coverage quality metrics."""
        json_path = self.project_root / "coverage.json"
        
        if not json_path.exists():
            return {}
        
        with open(json_path, "r") as f:
            data = json.load(f)
        
        files = data.get("files", {})
        totals = data.get("totals", {})
        
        # File-level metrics
        coverage_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}
        category_coverage = {}
        
        for filename, file_data in files.items():
            summary = file_data.get("summary", {})
            coverage = summary.get("percent_covered", 0)
            
            # Coverage distribution
            if coverage >= 90:
                coverage_distribution["excellent"] += 1
            elif coverage >= 75:
                coverage_distribution["good"] += 1
            elif coverage >= 50:
                coverage_distribution["fair"] += 1
            else:
                coverage_distribution["poor"] += 1
            
            # Category-based coverage
            category = self._categorize_file(filename)
            if category not in category_coverage:
                category_coverage[category] = {"total": 0, "covered": 0, "files": 0}
            
            category_coverage[category]["total"] += summary.get("num_statements", 0)
            category_coverage[category]["covered"] += summary.get("covered_lines", 0)
            category_coverage[category]["files"] += 1
        
        # Calculate category percentages
        for category in category_coverage:
            total = category_coverage[category]["total"]
            covered = category_coverage[category]["covered"]
            category_coverage[category]["percentage"] = (covered / total * 100) if total > 0 else 0
        
        return {
            "overall_coverage": totals.get("percent_covered", 0),
            "branch_coverage": totals.get("percent_covered_branches", 0),
            "total_files": len(files),
            "coverage_distribution": coverage_distribution,
            "category_coverage": category_coverage,
            "quality_score": self._calculate_quality_score(totals, coverage_distribution),
        }
    
    def _calculate_gap_priority(self, filename: str, coverage: float, missing_lines: int) -> str:
        """Calculate priority level for coverage gap."""
        is_critical_file = any(pattern in filename for pattern in [
            "/core/", "/cli.py", "/models.py", "/config.py"
        ])
        
        if is_critical_file:
            if coverage < 50:
                return "critical"
            elif coverage < 75:
                return "high"
            else:
                return "medium"
        else:
            if coverage < 25:
                return "high"
            elif coverage < 50:
                return "medium"
            else:
                return "low"
    
    def _categorize_file(self, filename: str) -> str:
        """Categorize file by type/purpose."""
        if "/core/" in filename:
            return "core"
        elif "/commands/" in filename or "/cli.py" in filename:
            return "cli"
        elif "/utils/" in filename:
            return "utils"
        elif "/models/" in filename or "models.py" in filename:
            return "models"
        elif "/config/" in filename or "config.py" in filename:
            return "config"
        else:
            return "other"
    
    def _calculate_quality_score(self, totals: Dict, distribution: Dict) -> float:
        """Calculate overall quality score (0-100)."""
        line_coverage = totals.get("percent_covered", 0)
        branch_coverage = totals.get("percent_covered_branches", 0)
        
        total_files = sum(distribution.values())
        if total_files == 0:
            return 0
        
        # Weighted score based on coverage and distribution
        coverage_score = (line_coverage * 0.6) + (branch_coverage * 0.4)
        
        # Distribution bonus/penalty
        excellent_ratio = distribution["excellent"] / total_files
        poor_ratio = distribution["poor"] / total_files
        
        distribution_score = (excellent_ratio * 20) - (poor_ratio * 15)
        
        final_score = min(100, max(0, coverage_score + distribution_score))
        return round(final_score, 1)
    
    def _run_coverage_analysis(self) -> None:
        """Run coverage analysis to get current data."""
        cmd = [
            sys.executable, "-m", "pytest",
            "--cov=ai_trackdown_pytools",
            "--cov-branch",
            "--cov-report=json:coverage.json",
            "--quiet",
        ]
        
        subprocess.run(cmd, cwd=self.project_root, capture_output=True)
    
    def _generate_html_dashboard(self, current: Dict, trends: List[Dict], 
                               gaps: Dict, quality: Dict) -> str:
        """Generate HTML dashboard."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Trackdown PyTools - Coverage Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #334155;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: linear-gradient(135deg, #1e293b 0%, #475569 100%);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
        }
        .header h1 { font-size: 2.5rem; margin-bottom: 0.5rem; }
        .header .subtitle { opacity: 0.9; font-size: 1.1rem; }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #3b82f6;
        }
        .metric-card.excellent { border-left-color: #22c55e; }
        .metric-card.good { border-left-color: #84cc16; }
        .metric-card.fair { border-left-color: #eab308; }
        .metric-card.poor { border-left-color: #ef4444; }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .metric-label {
            color: #64748b;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .section {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .section h2 {
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            color: #1e293b;
        }
        
        .gap-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            margin-bottom: 0.5rem;
        }
        .gap-item.critical { border-left: 4px solid #dc2626; }
        .gap-item.high { border-left: 4px solid #ea580c; }
        .gap-item.medium { border-left: 4px solid #ca8a04; }
        .gap-item.low { border-left: 4px solid #65a30d; }
        
        .gap-filename { font-family: 'SF Mono', monospace; font-size: 0.9rem; }
        .gap-coverage { font-weight: 600; }
        
        .chart-container {
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f1f5f9;
            border-radius: 8px;
            margin: 1rem 0;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin: 0.5rem 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #22c55e 0%, #84cc16 100%);
            transition: width 0.3s ease;
        }
        .progress-fill.poor { background: linear-gradient(90deg, #ef4444 0%, #f97316 100%); }
        .progress-fill.fair { background: linear-gradient(90deg, #eab308 0%, #f59e0b 100%); }
        
        .category-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .category-item {
            text-align: center;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 8px;
        }
        .category-name {
            font-weight: 600;
            margin-bottom: 0.5rem;
            text-transform: capitalize;
        }
        .category-percentage {
            font-size: 1.5rem;
            font-weight: 700;
            color: #1e293b;
        }
        
        .timestamp {
            text-align: center;
            color: #64748b;
            font-size: 0.9rem;
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #e2e8f0;
        }
        
        @media (max-width: 768px) {
            .metrics-grid { grid-template-columns: 1fr; }
            .container { padding: 10px; }
            .header { padding: 1rem; }
            .section { padding: 1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Coverage Dashboard</h1>
            <div class="subtitle">AI Trackdown PyTools Coverage Analysis</div>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card {line_coverage_class}">
                <div class="metric-value">{line_coverage:.1f}%</div>
                <div class="metric-label">Line Coverage</div>
            </div>
            
            <div class="metric-card {branch_coverage_class}">
                <div class="metric-value">{branch_coverage:.1f}%</div>
                <div class="metric-label">Branch Coverage</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{quality_score}</div>
                <div class="metric-label">Quality Score</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-value">{total_files}</div>
                <div class="metric-label">Total Files</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 Coverage Distribution</h2>
            <div class="category-grid">
                <div class="category-item">
                    <div class="category-name">Excellent (≥90%)</div>
                    <div class="category-percentage" style="color: #22c55e;">{excellent_files}</div>
                </div>
                <div class="category-item">
                    <div class="category-name">Good (75-89%)</div>
                    <div class="category-percentage" style="color: #84cc16;">{good_files}</div>
                </div>
                <div class="category-item">
                    <div class="category-name">Fair (50-74%)</div>
                    <div class="category-percentage" style="color: #eab308;">{fair_files}</div>
                </div>
                <div class="category-item">
                    <div class="category-name">Poor (<50%)</div>
                    <div class="category-percentage" style="color: #ef4444;">{poor_files}</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🎯 Category Coverage</h2>
            {category_coverage_html}
        </div>
        
        <div class="section">
            <h2>🔍 Top Coverage Gaps</h2>
            <div class="gap-list">
                {gaps_html}
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Coverage Trends</h2>
            <div class="chart-container">
                {trends_message}
            </div>
        </div>
        
        <div class="timestamp">
            Generated: {timestamp}
        </div>
    </div>
</body>
</html>
"""
        
        # Prepare data for template
        line_coverage = current.get("percent_covered", 0)
        branch_coverage = current.get("percent_covered_branches", 0)
        
        # Coverage classes
        def get_coverage_class(coverage):
            if coverage >= 90: return "excellent"
            elif coverage >= 75: return "good"
            elif coverage >= 50: return "fair"
            else: return "poor"
        
        # Generate category coverage HTML
        category_html = ""
        for category, data in quality.get("category_coverage", {}).items():
            percentage = data["percentage"]
            progress_class = get_coverage_class(percentage)
            category_html += f"""
            <div style="margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                    <span style="text-transform: capitalize; font-weight: 600;">{category}</span>
                    <span style="font-weight: 600;">{percentage:.1f}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill {progress_class}" style="width: {percentage}%;"></div>
                </div>
                <div style="font-size: 0.8rem; color: #64748b;">{data['files']} files</div>
            </div>
            """
        
        # Generate gaps HTML
        gaps_html = ""
        for gap in gaps.get("gaps", [])[:10]:
            gaps_html += f"""
            <div class="gap-item {gap['priority']}">
                <div>
                    <div class="gap-filename">{gap['filename']}</div>
                    <div style="font-size: 0.8rem; color: #64748b;">
                        {gap['missing_lines']} missing lines • {gap['category']} • {gap['priority']} priority
                    </div>
                </div>
                <div class="gap-coverage">{gap['coverage']:.1f}%</div>
            </div>
            """
        
        # Trends message
        trends_message = f"📈 {len(trends)} data points collected" if trends else "No trend data available yet"
        
        # Fill template
        html = html_template.format(
            line_coverage=line_coverage,
            branch_coverage=branch_coverage,
            line_coverage_class=get_coverage_class(line_coverage),
            branch_coverage_class=get_coverage_class(branch_coverage),
            quality_score=quality.get("quality_score", 0),
            total_files=quality.get("total_files", 0),
            excellent_files=quality.get("coverage_distribution", {}).get("excellent", 0),
            good_files=quality.get("coverage_distribution", {}).get("good", 0),
            fair_files=quality.get("coverage_distribution", {}).get("fair", 0),
            poor_files=quality.get("coverage_distribution", {}).get("poor", 0),
            category_coverage_html=category_html,
            gaps_html=gaps_html,
            trends_message=trends_message,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # Save dashboard
        dashboard_path = self.coverage_dir / "dashboard.html"
        with open(dashboard_path, "w") as f:
            f.write(html)
        
        print(f"📊 Coverage dashboard generated: {dashboard_path}")
        return str(dashboard_path)
    
    def _generate_json_dashboard(self, current: Dict, trends: List[Dict], 
                               gaps: Dict, quality: Dict) -> str:
        """Generate JSON dashboard data."""
        dashboard_data = {
            "timestamp": datetime.now().isoformat(),
            "current_coverage": current,
            "trends": trends,
            "gaps": gaps,
            "quality_metrics": quality,
        }
        
        dashboard_path = self.coverage_dir / "dashboard.json"
        with open(dashboard_path, "w") as f:
            json.dump(dashboard_data, f, indent=2)
        
        return str(dashboard_path)
    
    def _generate_text_dashboard(self, current: Dict, trends: List[Dict], 
                               gaps: Dict, quality: Dict) -> str:
        """Generate text dashboard summary."""
        line_coverage = current.get("percent_covered", 0)
        branch_coverage = current.get("percent_covered_branches", 0)
        
        text = f"""
AI Trackdown PyTools - Coverage Dashboard
=========================================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

CURRENT COVERAGE
----------------
Line Coverage:   {line_coverage:.1f}%
Branch Coverage: {branch_coverage:.1f}%
Quality Score:   {quality.get('quality_score', 0)}

COVERAGE DISTRIBUTION
--------------------
Excellent (≥90%): {quality.get('coverage_distribution', {}).get('excellent', 0)} files
Good (75-89%):    {quality.get('coverage_distribution', {}).get('good', 0)} files
Fair (50-74%):    {quality.get('coverage_distribution', {}).get('fair', 0)} files
Poor (<50%):      {quality.get('coverage_distribution', {}).get('poor', 0)} files

TOP COVERAGE GAPS
-----------------
"""
        
        for i, gap in enumerate(gaps.get("gaps", [])[:5], 1):
            text += f"{i}. {gap['filename']} ({gap['coverage']:.1f}%) - {gap['priority']} priority\n"
        
        text += f"""
CATEGORY COVERAGE
-----------------
"""
        
        for category, data in quality.get("category_coverage", {}).items():
            text += f"{category.title()}: {data['percentage']:.1f}% ({data['files']} files)\n"
        
        text += f"""
TRENDS
------
Data points collected: {len(trends)}
"""
        
        dashboard_path = self.coverage_dir / "dashboard.txt"
        with open(dashboard_path, "w") as f:
            f.write(text)
        
        return str(dashboard_path)


def main():
    """Main CLI interface for coverage dashboard."""
    parser = argparse.ArgumentParser(
        description="AI Trackdown PyTools Coverage Dashboard"
    )
    
    parser.add_argument(
        "--format", choices=["html", "json", "text"], default="html",
        help="Output format for dashboard"
    )
    
    parser.add_argument(
        "--open", action="store_true",
        help="Open HTML dashboard in browser"
    )
    
    args = parser.parse_args()
    
    # Determine project root
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Not in a Python project directory (no pyproject.toml found)")
        sys.exit(1)
    
    dashboard = CoverageDashboard(project_root)
    
    try:
        output_path = dashboard.generate_dashboard(args.format)
        print(f"✅ Dashboard generated: {output_path}")
        
        if args.open and args.format == "html":
            import webbrowser
            webbrowser.open(f"file://{output_path}")
        
    except Exception as e:
        print(f"❌ Dashboard generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()