# Katalyst Tests

## Structure

- `unit/` - Fast unit tests with mocked dependencies
- `integration/` - Tests with real file system and external services  
- `agent_tests/` - End-to-end agent workflow tests
  - `test_cases/` - Agent test cases organized by category
    - `basic_tests.py` - Basic agent functionality tests
    - `search_read_tests.py` - Search and file reading tests
    - `code_analysis_tests.py` - Code analysis and definition tests
    - `diff_syntax_tests.py` - Diff application and syntax tests
    - `command_tests.py` - Command execution tests
    - `complex_tests.py` - Complex multi-step workflow tests

## Running Tests

```bash
# All tests
pytest tests/

# By category
pytest -m unit tests/
pytest -m integration tests/
pytest -m agent tests/

# By directory
pytest tests/unit/
pytest tests/integration/
pytest tests/agent_tests/

# Specific agent test categories
pytest tests/agent_tests/test_cases/basic_tests.py
pytest tests/agent_tests/test_cases/search_read_tests.py
pytest tests/agent_tests/test_cases/complex_tests.py

# With coverage
pytest --cov=katalyst tests/
```

## Adding Tests

- **Unit**: `tests/unit/` - Mock dependencies, use `pytestmark = pytest.mark.unit`
- **Integration**: `tests/integration/` - Real files/commands, use `pytestmark = pytest.mark.integration`  
- **Agent**: `tests/agent_tests/test_cases/` - Full workflows, use `pytestmark = pytest.mark.agent`
