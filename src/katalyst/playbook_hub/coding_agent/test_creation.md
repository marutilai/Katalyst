# Playbook: Comprehensive Test Suite Generation

Description: This playbook provides a systematic approach to creating comprehensive tests for existing code. It guides through analyzing untested code, generating appropriate test cases, setting up fixtures, and ensuring complete test coverage with proper mocking and edge case handling.

**Input Requirements:**
- `target_path`: File, directory, or module to create tests for
- `test_framework` (optional): Testing framework to use (pytest, unittest, etc.) - will auto-detect if not specified
- `coverage_target` (optional): Desired test coverage percentage (default: 80%)
- `test_types` (optional): Types of tests to create (unit | integration | both) - default: both

**Output:** A comprehensive test suite including:
- Unit tests for individual functions/methods
- Integration tests for component interactions
- Test fixtures and utilities
- Proper mocking for external dependencies
- Edge case and error handling tests
- Documentation of test scenarios

## Step 1: Analyze Testing Environment

**Goal:** Understand the project's testing setup and conventions.

**Method:**
- Use `read_file` on `pyproject.toml`, `setup.py`, or `requirements.txt` to identify test dependencies
- Use `search_files` for existing test files to understand:
  - Test file naming conventions (test_*.py or *_test.py)
  - Test directory structure
  - Testing framework in use (pytest, unittest, nose)
  - Fixture patterns and test utilities
- Check for test configuration files (pytest.ini, .coveragerc, tox.ini)
- Identify any custom test base classes or utilities

## Step 2: Analyze Target Code

**Goal:** Create a comprehensive map of all code elements that need testing.

**Method:**
- Use `list_code_definitions` on the target path to identify:
  - All functions and their signatures
  - All classes and their methods
  - Module-level constants and variables
- Use `read_file` to understand:
  - Function/method complexity
  - External dependencies
  - Error handling patterns
  - Input/output types
- Create a prioritized list of items to test based on:
  - Complexity (cyclomatic complexity)
  - Public vs private (public first)
  - Critical business logic
  - Error-prone areas

## Step 3: Check Existing Test Coverage

**Goal:** Identify what tests already exist to avoid duplication.

**Method:**
- Use `search_files` to find existing tests for the target code
- For each function/class in the target:
  - Search for `test_{function_name}` or `Test{ClassName}`
  - Check for parametrized tests that might cover it
  - Look for integration tests that exercise the code
- Create a coverage map showing:
  - Fully tested elements
  - Partially tested elements
  - Untested elements
- Use `execute_command` with coverage tool if available:
  ```bash
  pytest --cov={target_module} --cov-report=term-missing
  ```

## Step 4: Generate Test Structure

**Goal:** Create the test file structure following project conventions.

**Method:**
- Determine test file location:
  - Mirror source structure in tests/ directory
  - Or place next to source file with test_ prefix
- Create test file(s) with proper naming:
  - `test_{module_name}.py` for `{module_name}.py`
  - Organize by logical groupings
- Set up basic test file structure:
  ```python
  """Tests for {module_name}."""
  import pytest
  from unittest.mock import Mock, patch
  
  from {import_path} import {items_to_test}
  
  
  class Test{MainClass}:
      """Test cases for {MainClass}."""
      
      @pytest.fixture
      def setup(self):
          """Set up test fixtures."""
          # Setup code here
          
  # Additional test functions/classes
  ```

## Step 5: Create Unit Tests

**Goal:** Generate comprehensive unit tests for each function/method.

**Method:**
For each function/method to test:

1. **Basic Happy Path Tests:**
   - Test with typical valid inputs
   - Verify expected outputs
   - Check state changes if applicable

2. **Edge Case Tests:**
   - Empty inputs (empty strings, lists, None)
   - Boundary values (0, -1, max values)
   - Special characters or formats
   - Large inputs for performance-sensitive code

3. **Error Handling Tests:**
   - Invalid input types
   - Out-of-range values
   - Missing required parameters
   - Verify proper exceptions are raised

4. **Mock External Dependencies:**
   ```python
   @patch('module.external_service')
   def test_function_with_external_call(self, mock_service):
       mock_service.return_value = expected_data
       result = function_under_test()
       mock_service.assert_called_once_with(expected_args)
       assert result == expected_result
   ```

## Step 6: Create Integration Tests

**Goal:** Test interactions between components and with external systems.

**Method:**
- Identify component boundaries and interactions
- Create tests that exercise multiple components together
- Test data flow through the system
- Use real or test databases/services where appropriate
- Test configuration and initialization
- Verify proper cleanup and resource management

Example structure:
```python
class TestIntegration:
    """Integration tests for component interactions."""
    
    def test_full_workflow(self):
        """Test complete workflow from input to output."""
        # Setup
        component_a = ComponentA()
        component_b = ComponentB()
        
        # Execute workflow
        intermediate = component_a.process(input_data)
        result = component_b.transform(intermediate)
        
        # Verify
        assert result.status == 'completed'
```

## Step 7: Create Test Fixtures and Utilities

**Goal:** Build reusable test infrastructure for efficient testing.

**Method:**
- Create fixtures for common test data:
  ```python
  @pytest.fixture
  def sample_user():
      """Provide a sample user object."""
      return User(name="Test User", email="test@example.com")
  ```
- Build factory functions for complex objects
- Create mock builders for external services
- Set up test database fixtures
- Add parameterized test helpers:
  ```python
  @pytest.mark.parametrize("input,expected", [
      ("valid", True),
      ("", False),
      (None, False),
  ])
  def test_validation(input, expected):
      assert validate(input) == expected
  ```

## Step 8: Add Property-Based Tests (if applicable)

**Goal:** Use property-based testing for more thorough coverage.

**Method:**
- For functions with mathematical properties or invariants
- Use hypothesis or similar framework:
  ```python
  from hypothesis import given, strategies as st
  
  @given(st.lists(st.integers()))
  def test_sort_properties(input_list):
      sorted_list = sort_function(input_list)
      assert len(sorted_list) == len(input_list)
      assert all(sorted_list[i] <= sorted_list[i+1] 
                 for i in range(len(sorted_list)-1))
  ```

## Step 9: Document Test Scenarios

**Goal:** Ensure tests are understandable and maintainable.

**Method:**
- Add clear docstrings to test functions explaining:
  - What is being tested
  - Why it's important
  - Any special setup or conditions
- Use descriptive test names:
  - `test_calculate_discount_applies_percentage_correctly`
  - `test_save_user_raises_error_on_duplicate_email`
- Group related tests in classes
- Add comments for complex test logic
- Document any test utilities or fixtures

## Step 10: Verify Test Quality

**Goal:** Ensure tests are effective and maintainable.

**Method:**
- Run tests to ensure they pass:
  ```bash
  pytest {test_file} -v
  ```
- Check test coverage:
  ```bash
  pytest --cov={module} --cov-report=html
  ```
- Verify tests fail when code is broken (mutation testing concept)
- Check for:
  - Proper isolation (no test interdependencies)
  - Appropriate use of mocks
  - Clear assertions
  - No hardcoded values that might break
- Run tests with different random seeds
- Ensure tests run quickly (mock slow operations)

## Step 11: Generate Test Summary

**Goal:** Provide a comprehensive report of test creation.

**Method:**
- Create summary including:
  - Number of tests created by type
  - Coverage before and after
  - List of components tested
  - Any gaps or limitations
  - Recommendations for additional testing
- Document any special test requirements:
  - Environment variables needed
  - External services to mock
  - Test data setup requirements
- Update test documentation/README if exists

## Error Handling and Best Practices

### Test Design Principles:
- **Arrange-Act-Assert**: Clear test structure
- **One assertion per test**: When possible
- **Independent tests**: No shared state
- **Fast tests**: Mock external calls
- **Deterministic**: Same result every run

### Common Pitfalls to Avoid:
- Testing implementation details instead of behavior
- Overly brittle tests that break with refactoring
- Incomplete mocking leading to flaky tests
- Not testing error paths
- Ignoring performance implications

### Framework-Specific Considerations:
- **pytest**: Use fixtures, marks, and plugins
- **unittest**: Use setUp/tearDown methods
- **asyncio**: Use pytest-asyncio for async tests
- **Django**: Use TestCase classes and fixtures

## Strict Execution Requirements

- Always analyze existing tests before creating new ones
- Follow project's established testing patterns
- Ensure all tests are independent and can run in any order
- Mock all external dependencies in unit tests
- Use meaningful test data that represents real scenarios
- Verify tests actually test the intended behavior
- Keep tests simple and focused on one aspect
- Update or create test documentation
- Ensure tests run in CI/CD pipeline