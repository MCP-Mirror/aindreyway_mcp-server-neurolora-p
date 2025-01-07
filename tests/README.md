# Testing Guide

This directory contains tests for the NeuroLoRA MCP server. The tests are organized into different categories and can be run individually or all together.

## Test Structure

```
tests/
├── unit/                 # Unit tests
│   ├── test_*.py        # Individual unit test files
│   └── conftest.py      # Unit test fixtures
├── integration/         # Integration tests
│   ├── test_*.py       # Individual integration test files
│   └── conftest.py     # Integration test fixtures
├── e2e/                # End-to-end tests (if needed)
├── fixtures/           # Common test fixtures and data
├── conftest.py         # Common test configuration
└── run_all_tests.py    # Test runner script
```

## Running Tests

You can run tests using the `run_all_tests.py` script:

```bash
# Run all tests
python tests/run_all_tests.py

# Run only unit tests
python tests/run_all_tests.py --unit

# Run only integration tests
python tests/run_all_tests.py --integration

# Run only slow tests
python tests/run_all_tests.py --slow

# Run with specific pytest arguments
python tests/run_all_tests.py -v -k "test_specific"
```

## Test Categories

### Unit Tests

- Test individual components in isolation
- Fast execution
- No external dependencies
- Mark with `@pytest.mark.unit`

### Integration Tests

- Test component interactions
- Test external API integrations
- May be slower than unit tests
- Mark with `@pytest.mark.integration`

### Slow Tests

- Tests that take longer to execute
- Mark with `@pytest.mark.slow`

## Coverage Requirements

- Minimum coverage: 80%
- Coverage reports are generated in HTML and XML formats
- View HTML report in `coverage_html/index.html`

## Writing Tests

1. Choose the appropriate test category (unit/integration)
2. Create test file in corresponding directory
3. Add appropriate marker:

   ```python
   import pytest

   @pytest.mark.unit  # or integration/slow
   def test_something():
       assert True
   ```

4. Use fixtures from conftest.py files
5. Follow type hints and use mypy for type checking

## Common Fixtures

- `test_server`: MCP server instance for testing
- `tool_executor`: Tool executor instance
- `mock_api_response`: Mock API responses
- `mock_tools`: Mock tool definitions
- `setup_test_env`: Automatic environment setup (autouse)
- `mock_env_config`: Mock environment configuration

## Best Practices

1. Use appropriate markers for test categorization
2. Keep tests focused and isolated
3. Use meaningful test names
4. Add docstrings to test functions
5. Follow type hints
6. Use fixtures for common setup
7. Clean up resources after tests
8. Mock external dependencies
9. Use parametrize for multiple test cases
10. Keep tests maintainable and readable
