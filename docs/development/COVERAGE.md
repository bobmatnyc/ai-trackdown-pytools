# Test Coverage

## Overview

AI Trackdown PyTools maintains high test coverage to ensure code quality and reliability.

## Coverage Requirements

- **Target Coverage**: 85% line coverage
- **Branch Coverage**: Enabled for comprehensive analysis
- **Fail Threshold**: Tests fail if coverage drops below 85%

## Running Tests with Coverage

### Basic Coverage

```bash
# Run tests with coverage
pytest --cov=ai_trackdown_pytools

# Generate HTML coverage report
pytest --cov=ai_trackdown_pytools --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Advanced Coverage Analysis

```bash
# Run full coverage analysis
python scripts/coverage_analysis.py --analyze --report --gaps

# Analyze coverage gaps only
python scripts/coverage_analysis.py --gaps
```

## Makefile Commands

Convenient make targets for coverage operations:

```bash
# Basic coverage testing
make test-cov                    # Run tests with coverage
make test-coverage-full          # Full test suite with detailed reporting

# Coverage analysis
make coverage-analyze            # Full coverage analysis with gap report
make coverage-gaps               # Identify coverage gaps
```

## Coverage Reports

The system generates multiple report formats:

- **HTML Report** (`htmlcov/index.html`) - Interactive browsable coverage report
- **XML Report** (`coverage.xml`) - Cobertura-compatible XML format for CI/CD
- **JSON Report** (`coverage.json`) - Programmatic access to coverage data

## Best Practices

1. **Focus on Business Logic**: Prioritize testing core functionality
2. **Test Edge Cases**: Cover error conditions and boundary cases
3. **Use Parametrized Tests**: Efficiently test multiple scenarios
4. **Mock External Dependencies**: Isolate code under test
5. **Test Both Success and Failure Paths**: Ensure comprehensive branch coverage

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed with `pip install -e .[test]`
2. **Path Issues**: Run commands from project root directory
3. **CI Failures**: Check coverage threshold and adjust if needed

For detailed coverage analysis and advanced features, see the scripts in the `scripts/` directory.