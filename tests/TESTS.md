# Katalyst Tests

## Structure

- `unit/` - Fast unit tests with mocked dependencies
- `integration/` - Tests with real file system and external services  
- `agent_tests/` - End-to-end agent workflow tests

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

# With coverage
pytest --cov=katalyst tests/
```

## Agent Test Suites

```bash
python -m tests.agent_tests.test_suite --suite basic
python -m tests.agent_tests.test_suite --auto-approve
```

## Adding Tests

- **Unit**: `tests/unit/` - Mock dependencies, use `pytestmark = pytest.mark.unit`
- **Integration**: `tests/integration/` - Real files/commands, use `pytestmark = pytest.mark.integration`  
- **Agent**: `tests/agent_tests/` - Full workflows, use `pytestmark = pytest.mark.agent`
