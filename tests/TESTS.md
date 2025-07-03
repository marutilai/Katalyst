# Katalyst Tests

## Structure

- `unit/` - Fast unit tests with mocked dependencies
- `integration/` - Tests with real file system and external services  
- `e2e/` - End-to-end tests that use real LLMs
  - `test_cases/` - Agent test cases organized by category
    - `basic_tests.py` - Basic agent functionality tests
    - `search_read_tests.py` - Search and file reading tests
    - `code_analysis_tests.py` - Code analysis and definition tests
    - `diff_syntax_tests.py` - Diff application and syntax tests
    - `command_tests.py` - Command execution tests
    - `complex_tests.py` - Complex multi-step workflow tests
  - `test_ollama_model_benchmark.py` - Benchmark tests for Ollama models

## Running Tests

```bash
# All tests
pytest tests/

# By category
pytest -m unit tests/
pytest -m integration tests/
pytest -m e2e tests/

# By directory
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Specific e2e test categories
pytest tests/e2e/test_cases/basic_tests.py
pytest tests/e2e/test_cases/search_read_tests.py
pytest tests/e2e/test_cases/complex_tests.py

# With coverage
pytest --cov=katalyst tests/
```

## Test Reports

E2E tests generate detailed JSON reports in the `test_reports/` directory (gitignored):

- **Location**: `test_reports/test_report_<test_name>.json`
- **Content**: LLM evaluations, rubric scoring, execution details, file changes
- **Structure**: Summary stats, individual test results with detailed feedback
- **Usage**: Reports are automatically generated and printed to console during test execution

Each report includes:
- Test case details and execution results
- LLM evaluation with rubric scoring per criterion
- Files created/modified by the agent
- Error messages and execution time
- Custom validation checks

## Adding Tests

- **Unit**: `tests/unit/` - Mock dependencies, use `pytestmark = pytest.mark.unit`
- **Integration**: `tests/integration/` - Real files/commands, use `pytestmark = pytest.mark.integration`  
- **E2E**: `tests/e2e/test_cases/` - Full workflows with real LLMs, use `pytestmark = pytest.mark.e2e`
