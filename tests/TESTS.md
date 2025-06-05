# Katalyst Tests

This directory contains all tests for the Katalyst project, organized by type:

## Directory Structure

- `unit/` - Unit tests for individual components
- `functional/` - Functional tests for the Katalyst agent

## Running Tests

### Unit Tests
```bash
# Run all unit tests
pytest tests/unit/

# Run specific unit test file
pytest tests/unit/test_specific_file.py
```

### Functional Tests
```bash
# Run all functional tests
python -m tests.functional.run_tests

# Run specific test suite
python -m tests.functional.run_tests --suite basic
python -m tests.functional.run_tests --suite search
python -m tests.functional.run_tests --suite code
python -m tests.functional.run_tests --suite diff
python -m tests.functional.run_tests --suite command
python -m tests.functional.run_tests --suite complex

# Auto-approve user interactions (for automated testing)
python -m tests.functional.run_tests --auto-approve

# Specify custom report file
python -m tests.functional.run_tests --report custom_report.json
```

## Test Coverage

To generate and view test coverage reports:

```bash
# Run tests with coverage
pytest --cov=katalyst_agent tests/

# Generate HTML report
pytest --cov=katalyst_agent --cov-report=html tests/

# Generate terminal report
pytest --cov=katalyst_agent --cov-report=term-missing tests/
```

The HTML report will be generated in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to view detailed coverage information.

Coverage reports show:
- Overall coverage percentage
- Coverage by module
- Line-by-line coverage details
- Missing lines (with --cov-report=term-missing)

// ... existing code ...
