.PHONY: help install install-dev test lint format type-check clean build publish docs

# Default target
help:
	@echo "Available targets:"
	@echo "  install      Install package"
	@echo "  install-dev  Install package in development mode with dev dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code"
	@echo "  type-check   Run type checking"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build package"
	@echo "  publish      Publish to PyPI"
	@echo "  docs         Generate documentation"

# Installation
install:
	pip install .

install-dev:
	pip install -e .[dev]
	pre-commit install

# Testing
test:
	pytest

test-cov:
	pytest --cov=ai_trackdown_pytools --cov-branch --cov-report=html --cov-report=term-missing --cov-report=xml --cov-report=json

test-verbose:
	pytest -v

# Enhanced Coverage Testing
test-coverage-full:
	python scripts/test_runner.py full --verbose

test-coverage-unit:
	python scripts/test_runner.py unit

test-coverage-integration:
	python scripts/test_runner.py integration

test-coverage-fast:
	python scripts/test_runner.py fast

# Coverage Analysis
coverage-analyze:
	python scripts/coverage_analysis.py --analyze --report --gaps

coverage-gaps:
	python scripts/coverage_analysis.py --gaps

coverage-trends:
	python scripts/coverage_analysis.py --trends

coverage-dashboard:
	python scripts/coverage_dashboard.py --format html --open

coverage-dashboard-json:
	python scripts/coverage_dashboard.py --format json

# CI Coverage
coverage-ci:
	python scripts/ci_coverage.py --fail-under 85 --generate-badges

coverage-ci-upload:
	python scripts/ci_coverage.py --fail-under 85 --upload-codecov --upload-coveralls

# Code quality
lint:
	ruff check src tests
	black --check src tests
	isort --check-only src tests

format:
	black src tests
	isort src tests
	ruff check --fix src tests

type-check:
	mypy src

# Quality checks
check: lint type-check test

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Clean
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build
build: clean
	python -m build

# Publish
publish: build
	python -m twine upload dist/*

publish-test: build
	python -m twine upload --repository testpypi dist/*

# Documentation
docs:
	@echo "Documentation generation not yet implemented"

# Development helpers
dev-setup: install-dev
	@echo "Development environment set up successfully!"
	@echo "Run 'aitrackdown --help' to get started"

# CI simulation
ci: format lint type-check test
	@echo "All CI checks passed!"

# Version bump helpers
version-patch:
	@echo "Bumping patch version..."
	@python -c "import toml; pyproject = toml.load('pyproject.toml'); version = pyproject['project']['version'].split('.'); version[2] = str(int(version[2]) + 1); pyproject['project']['version'] = '.'.join(version); toml.dump(pyproject, open('pyproject.toml', 'w'))"

version-minor:
	@echo "Bumping minor version..."
	@python -c "import toml; pyproject = toml.load('pyproject.toml'); version = pyproject['project']['version'].split('.'); version[1] = str(int(version[1]) + 1); version[2] = '0'; pyproject['project']['version'] = '.'.join(version); toml.dump(pyproject, open('pyproject.toml', 'w'))"

version-major:
	@echo "Bumping major version..."
	@python -c "import toml; pyproject = toml.load('pyproject.toml'); version = pyproject['project']['version'].split('.'); version[0] = str(int(version[0]) + 1); version[1] = '0'; version[2] = '0'; pyproject['project']['version'] = '.'.join(version); toml.dump(pyproject, open('pyproject.toml', 'w'))"

# Demo and examples
demo:
	@echo "Running AI Trackdown PyTools demo..."
	aitrackdown --help
	aitrackdown info
	aitrackdown health

# Enhanced CI/CD automation targets

# Performance monitoring
performance-benchmark:
	python scripts/performance_monitor.py benchmark --type full

performance-benchmark-fast:
	python scripts/performance_monitor.py benchmark --type fast

performance-trends:
	python scripts/performance_monitor.py trends --days 30

performance-regressions:
	python scripts/performance_monitor.py regressions

# Test result aggregation
test-aggregate:
	python scripts/test_results_aggregator.py aggregate

test-historical:
	python scripts/test_results_aggregator.py historical --days 30

test-trends:
	python scripts/test_results_aggregator.py trends --days 14

# Enhanced security scanning
security-full:
	bandit -r src -f json -o security-reports/bandit-report.json
	safety check --json --output security-reports/safety-report.json
	pip-audit --format=json --output=security-reports/pip-audit-report.json
	semgrep --config=auto src/ --json --output=security-reports/semgrep-report.json

security-sbom:
	cyclonedx-py -o security-reports/sbom.json

security-licenses:
	pip-licenses --format=json --output-file=security-reports/licenses-report.json

# Parallel testing
test-parallel:
	pytest -n auto --dist worksteal

test-parallel-verbose:
	pytest -n auto --dist worksteal -v

# Stress testing
test-stress:
	pytest -m stress --timeout=600

# Performance testing
test-performance:
	pytest --benchmark-only --benchmark-json=benchmark_results.json

# Memory profiling
test-memory:
	python -m memory_profiler scripts/test_runner.py fast

# Test with all environments
test-all-envs:
	tox

# CI simulation (comprehensive)
ci-full: clean install-dev pre-commit security-full test-coverage-full performance-benchmark test-aggregate
	@echo "🎉 Full CI simulation completed successfully!"

# CI simulation (fast)
ci-fast: format lint type-check test-coverage-fast
	@echo "🚀 Fast CI simulation completed!"

# Quality gates
quality-gate:
	python scripts/test_results_aggregator.py aggregate --quality-gate 85.0
	python scripts/performance_monitor.py benchmark --threshold-check

# Release preparation
release-prepare: clean format lint type-check test-coverage-full security-full performance-benchmark
	@echo "📦 Release preparation completed"

# Release validation
release-validate: build
	twine check dist/*
	pip install dist/*.whl
	python -c "import ai_trackdown_pytools; print('✅ Package validation passed')"
	aitrackdown --version

# Automated dependency updates
deps-update:
	pip install --upgrade pip setuptools wheel
	pip install --upgrade -r requirements.txt || true
	pre-commit autoupdate

# Health check
health-check:
	@echo "🏥 Running comprehensive health check..."
	python -c "import ai_trackdown_pytools; print('✅ Package import successful')"
	aitrackdown --version
	python scripts/test_runner.py fast --no-reports
	@echo "✅ Health check passed!"

# Database maintenance
db-backup:
	@mkdir -p backups
	cp test_results.db backups/test_results_$(shell date +%Y%m%d_%H%M%S).db || true
	cp performance_data.db backups/performance_data_$(shell date +%Y%m%d_%H%M%S).db || true

db-cleanup:
	python -c "
	import sqlite3
	from datetime import datetime, timedelta
	cutoff = (datetime.now() - timedelta(days=90)).isoformat()
	with sqlite3.connect('test_results.db') as conn:
	    conn.execute('DELETE FROM test_runs WHERE timestamp < ?', (cutoff,))
	    print('Cleaned test results older than 90 days')
	" || true

# Report generation
reports-generate:
	python scripts/test_results_aggregator.py aggregate
	python scripts/test_results_aggregator.py historical --days 30
	python scripts/performance_monitor.py benchmark --type full
	python scripts/performance_monitor.py trends --days 30

# Monitoring and alerting
monitor-quality:
	python scripts/test_results_aggregator.py trends --days 7
	python scripts/performance_monitor.py regressions

# Development environment validation
dev-validate:
	@echo "🔍 Validating development environment..."
	python --version
	pip --version
	git --version
	pre-commit --version
	pytest --version
	black --version
	ruff --version
	mypy --version
	@echo "✅ Development environment validation passed!"

# Comprehensive clean
clean-all: clean
	rm -rf test_results.db
	rm -rf performance_data.db
	rm -rf security-reports/
	rm -rf aggregated-reports/
	rm -rf performance-reports/
	rm -rf benchmark_results.json
	rm -rf .tox/
	rm -rf .mypy_cache/
	rm -rf .pytest_cache/
	find . -name "*.orig" -delete
	find . -name "*.rej" -delete

# Help with new targets
help-extended:
	@echo "Extended Make targets for AI Trackdown PyTools:"
	@echo ""
	@echo "Performance Monitoring:"
	@echo "  performance-benchmark    - Run full performance benchmarks"
	@echo "  performance-benchmark-fast - Run fast performance benchmarks"
	@echo "  performance-trends       - Generate performance trends report"
	@echo "  performance-regressions  - Check for performance regressions"
	@echo ""
	@echo "Test Automation:"
	@echo "  test-aggregate          - Aggregate test results from multiple sources"
	@echo "  test-historical         - Generate historical test analysis"
	@echo "  test-trends             - Show test trends"
	@echo "  test-parallel           - Run tests in parallel"
	@echo "  test-stress             - Run stress tests"
	@echo "  test-performance        - Run performance tests only"
	@echo ""
	@echo "Security:"
	@echo "  security-full           - Comprehensive security scanning"
	@echo "  security-sbom           - Generate Software Bill of Materials"
	@echo "  security-licenses       - Check license compliance"
	@echo ""
	@echo "CI/CD:"
	@echo "  ci-full                 - Full CI simulation"
	@echo "  ci-fast                 - Fast CI simulation"
	@echo "  quality-gate            - Run quality gate checks"
	@echo "  release-prepare         - Prepare for release"
	@echo "  release-validate        - Validate release package"
	@echo ""
	@echo "Maintenance:"
	@echo "  health-check            - Run health check"
	@echo "  dev-validate            - Validate development environment"
	@echo "  reports-generate        - Generate all reports"
	@echo "  monitor-quality         - Monitor quality metrics"
	@echo "  clean-all               - Clean everything including databases"