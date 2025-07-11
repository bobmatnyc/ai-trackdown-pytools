# Comprehensive CLI Testing Guide

This document provides a complete guide to the CLI testing suite for ai-trackdown-pytools.

## Overview

The CLI testing suite provides comprehensive coverage of all command-line interface functionality including:

- **Option and Argument Testing**: All CLI options, flags, and arguments across all command groups
- **Interactive Prompt Testing**: Rich prompts, confirmations, and input validation
- **Output Format Testing**: JSON, CSV, XML, YAML, and table formatting options
- **Error Condition Testing**: Invalid inputs, network failures, permission errors, etc.
- **End-to-End Workflow Testing**: Complete ticket lifecycle from creation to deletion
- **Performance Testing**: Large datasets and concurrent operations

## Test Structure

```
tests/cli/
├── __init__.py                           # CLI testing module
├── CLI_TESTING_GUIDE.md                 # This guide
├── run_cli_tests.py                     # Test runner script
├── test_comprehensive_cli_options.py    # Comprehensive option testing
├── test_interactive_prompts.py          # Interactive UI testing
├── test_e2e_ticket_lifecycle.py         # End-to-end workflow testing
└── test_output_formats_errors.py        # Output formats and error testing
```

## Test Categories

### 1. Comprehensive CLI Options (`test_comprehensive_cli_options.py`)

Tests all CLI options and arguments:

- **Main CLI Options**: `--version`, `--verbose`, `--config`, `--project-dir`
- **Command Groups**: All 13+ command groups (init, status, create, task, etc.)
- **Option Combinations**: Testing multiple options together
- **Argument Validation**: Required vs optional arguments
- **Flag Behavior**: Short vs long flags (`-v` vs `--verbose`)

#### Key Test Classes:
- `TestMainCLIOptions`: Global options and callbacks
- `TestCommandGroups`: Command group help and structure
- `TestInitCommandOptions`: Project initialization options
- `TestCreateCommandOptions`: Task/issue/epic creation options
- `TestTaskCommandOptions`: Task management options
- `TestStatusCommandOptions`: Status and reporting options
- `TestSearchCommandOptions`: Search and filtering options
- `TestBuiltinCommands`: Built-in commands (info, health, doctor, version)

### 2. Interactive Prompts (`test_interactive_prompts.py`)

Tests Rich-based interactive functionality:

- **Interactive Task Creation**: Multi-step prompts with validation
- **Template Selection**: Dynamic template application
- **Configuration Setup**: Interactive config building
- **Search Refinement**: Interactive search query building
- **Validation Fixes**: Interactive problem resolution

#### Key Test Classes:
- `TestInteractiveTaskCreation`: Task creation workflows
- `TestInteractiveEpicCreation`: Epic creation with task generation
- `TestInteractiveIssueCreation`: Bug reports and feature requests
- `TestInteractiveTemplateSelection`: Template browsing and application
- `TestInteractiveConfiguration`: Config setup and updates
- `TestRichUIElements`: Table formatting, panels, progress bars

### 3. End-to-End Workflows (`test_e2e_ticket_lifecycle.py`)

Tests complete ticket lifecycle workflows:

- **Complete Ticket Lifecycle**: Project → Epic → Issue → Task → Comments → Deletion
- **Portfolio Management**: Multi-project coordination
- **Sync Operations**: External platform integration
- **Template Workflows**: Custom template creation and usage
- **AI Integration**: AI-powered features and workflows
- **Validation Workflows**: Comprehensive validation and fixing

#### Key Test Classes:
- `TestCompleteTicketLifecycle`: Full workflow testing
- `TestConcurrentOperations`: Race conditions and concurrent access
- `TestErrorRecovery`: Partial failure recovery

### 4. Output Formats and Errors (`test_output_formats_errors.py`)

Tests output formats and error handling:

- **Output Formats**: JSON, CSV, XML, YAML export
- **Table Formatting**: Various table styles and customization
- **Error Conditions**: Invalid commands, missing files, network failures
- **Unicode Handling**: International characters and emojis
- **Large Data**: Performance with large datasets

#### Key Test Classes:
- `TestJSONOutputFormat`: JSON export functionality
- `TestCSVOutputFormat`: CSV export and tabular data
- `TestTableFormattingOptions`: Rich table customization
- `TestErrorConditions`: Comprehensive error handling
- `TestUnicodeHandling`: International character support
- `TestLargeDataHandling`: Performance and scalability

## Running Tests

### Quick Start

```bash
# Run all CLI tests
python tests/cli/run_cli_tests.py

# Run specific test categories
python tests/cli/run_cli_tests.py --test-type options
python tests/cli/run_cli_tests.py --test-type interactive
python tests/cli/run_cli_tests.py --test-type e2e
python tests/cli/run_cli_tests.py --test-type formats
python tests/cli/run_cli_tests.py --test-type errors
```

### Advanced Options

```bash
# Verbose output with coverage
python tests/cli/run_cli_tests.py --verbose --coverage

# Parallel execution
python tests/cli/run_cli_tests.py --parallel

# Specific markers
python tests/cli/run_cli_tests.py --marker cli --marker "not slow"

# JSON output format
python tests/cli/run_cli_tests.py --output-format json

# List available tests
python tests/cli/run_cli_tests.py --list-tests
```

### Using pytest directly

```bash
# Run all CLI tests
pytest tests/cli/ -v

# Run specific test file
pytest tests/cli/test_comprehensive_cli_options.py -v

# Run specific test class
pytest tests/cli/test_interactive_prompts.py::TestInteractiveTaskCreation -v

# Run with markers
pytest tests/cli/ -m "cli and not slow" -v

# Generate coverage report
pytest tests/cli/ --cov=ai_trackdown_pytools --cov-report=html
```

## Test Patterns and Best Practices

### Mocking Strategy

The CLI tests use comprehensive mocking to isolate CLI logic:

```python
@patch('ai_trackdown_pytools.core.project.Project.exists')
@patch('ai_trackdown_pytools.core.task.TaskManager.create_task')
def test_task_creation(self, mock_create, mock_exists, cli_runner):
    mock_exists.return_value = True
    mock_task = Mock(id="TSK-001", title="Test Task")
    mock_create.return_value = mock_task
    
    result = cli_runner.invoke(app, ["task", "create", "Test Task"])
    assert result.exit_code == 0
```

### Interactive Testing

Interactive prompts are tested by mocking Rich components:

```python
@patch('rich.prompt.Prompt.ask')
@patch('rich.prompt.Confirm.ask')
def test_interactive_creation(self, mock_confirm, mock_prompt, cli_runner):
    mock_prompt.side_effect = ["Task Title", "Description", "high"]
    mock_confirm.side_effect = [True, False]  # Yes to create, No to edit
    
    result = cli_runner.invoke(app, ["task", "create", "--interactive"])
    assert result.exit_code == 0
```

### Error Testing

Error conditions are tested with side effects and exception mocking:

```python
@patch('builtins.open', side_effect=PermissionError("Permission denied"))
def test_permission_error(self, mock_open, cli_runner):
    result = cli_runner.invoke(app, ["config", "set", "key", "value"])
    # Should handle permission error gracefully
    assert "Permission" in result.output or result.exit_code != 0
```

## Test Coverage Goals

### Command Coverage
- [ ] All 50+ CLI commands tested
- [ ] All command options and flags tested
- [ ] All command combinations tested
- [ ] All help text validated

### Option Coverage
- [ ] Global options (`--verbose`, `--config`, `--project-dir`)
- [ ] Command-specific options for each command
- [ ] Short and long flag variants
- [ ] Option value validation

### Interactive Coverage
- [ ] All interactive prompts tested
- [ ] Rich UI component testing
- [ ] Input validation testing
- [ ] Multi-step workflow testing

### Error Coverage
- [ ] Invalid command/option handling
- [ ] File system errors
- [ ] Network errors
- [ ] Validation errors
- [ ] Permission errors

### Output Format Coverage
- [ ] JSON export functionality
- [ ] CSV export functionality
- [ ] XML export functionality
- [ ] YAML export functionality
- [ ] Table formatting options

## Integration with Main Test Suite

CLI tests integrate with the main test suite through:

1. **Shared Fixtures**: Use common fixtures from `conftest.py`
2. **Markers**: Use pytest markers for categorization
3. **Coverage Integration**: Contribute to overall coverage metrics
4. **CI Integration**: Run as part of continuous integration

## Performance Considerations

### Large Dataset Testing
- Tests with 1000+ tasks to verify performance
- Memory usage monitoring
- Response time validation

### Concurrent Operation Testing
- Multiple simultaneous operations
- Race condition detection
- State consistency validation

## Maintenance Guidelines

### Adding New Tests
1. Follow the established test class patterns
2. Use appropriate mocking strategies
3. Add docstrings describing test purpose
4. Include both positive and negative test cases

### Test Organization
1. Group related tests in the same class
2. Use descriptive test method names
3. Keep test methods focused on single functionality
4. Use parametrized tests for multiple similar cases

### Debugging Failed Tests
1. Use `--verbose` flag for detailed output
2. Check mock configurations and side effects
3. Verify CLI argument ordering and format
4. Review Rich component interactions

## Contributing

When adding new CLI functionality:

1. **Add Option Tests**: Test all new options and flags
2. **Add Interactive Tests**: Test any new prompts or UI elements
3. **Add Error Tests**: Test error conditions and edge cases
4. **Update Documentation**: Update this guide with new test patterns
5. **Run Full Suite**: Ensure all existing tests still pass

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Ensure src is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

**Mock Failures**
- Check that mock paths match actual import paths
- Verify mock return values match expected types
- Ensure mock side effects are configured correctly

**Rich Component Issues**
- Verify Rich components are properly mocked
- Check for console output capture
- Ensure prompt responses match expected types

### Debug Commands

```bash
# Run single test with full output
pytest tests/cli/test_comprehensive_cli_options.py::TestMainCLIOptions::test_version_option_short -v -s

# Run with pdb debugging
pytest tests/cli/test_interactive_prompts.py --pdb

# Show test coverage
pytest tests/cli/ --cov=ai_trackdown_pytools --cov-report=term-missing
```

## Conclusion

The comprehensive CLI testing suite ensures robust command-line interface functionality across all features and edge cases. Regular execution of these tests validates that the CLI remains reliable, user-friendly, and performant as the codebase evolves.