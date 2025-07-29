# Test Creation Guide

When creating tests, follow these critical patterns:

## Setup
1. Check existing tests: `search_files` for `test_{function_name}`
2. Match project conventions: Look for `test_*.py` or `*_test.py` patterns
3. Place tests in `tests/` mirroring source structure

## Essential Patterns
```python
# Every function needs: happy path + edge cases + error handling
@pytest.mark.parametrize("input,expected", [
    ("valid", "result"),     # happy path
    ("", ValueError),        # empty
    (None, TypeError),       # null  
    (-1, ValueError),        # boundary
])
def test_function_cases(input, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            function(input)
    else:
        assert function(input) == expected

# Mock external dependencies
@patch('module.external_service')
def test_with_mock(mock_service):
    mock_service.return_value = {"data": "mocked"}
    result = function_under_test()
    mock_service.assert_called_once()
    assert result == expected
```

## Key Rules
- Test behavior, not implementation
- Each test runs independently (no shared state)
- Mock ALL external calls (DB, API, file I/O)
- Test name format: `test_{function}_{scenario}`
- Always test: success, edge cases, errors
- Use fixtures for common test data

## Quick Check
After creating tests, verify:
- `pytest {test_file}` - all pass
- `pytest --cov={module}` - good coverage
- Tests fail when code is intentionally broken