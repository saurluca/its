# FastAPI Application Tests

This directory contains comprehensive tests for the FastAPI application, covering all routers and endpoints.

## Test Structure

### Test Files

- **`conftest.py`** - Main pytest configuration with fixtures and test setup
- **`test_tasks_crud.py`** - CRUD tests for tasks and answer options endpoints
- **`test_tasks_llm.py`** - LLM-dependent tests for task generation and answer evaluation
- **`test_documents_crud.py`** - CRUD tests for documents and file upload functionality
- **`test_auth.py`** - Authentication and user management tests
- **`test_repositories_crud.py`** - CRUD tests for repositories and document links
- **`run_tests.py`** - Convenient test runner script

### Test Categories

Tests are organized into different categories using pytest markers:

- **`@pytest.mark.crud`** - Basic CRUD operations (Create, Read, Update, Delete)
- **`@pytest.mark.llm`** - Tests involving LLM services (task generation, answer evaluation)
- **`@pytest.mark.auth`** - Authentication and authorization tests
- **`@pytest.mark.unit`** - Unit tests for individual components
- **`@pytest.mark.integration`** - Integration tests
- **`@pytest.mark.slow`** - Tests that take longer to run (LLM calls, file processing)

## Running Tests

### Prerequisites

Make sure you have the required dependencies installed:

```bash
uv sync
```

### Basic Test Commands

Run all tests:

```bash
uv run pytest tests/
```

Run tests with verbose output:

```bash
uv run pytest tests/ -v
```

Run specific test categories:

```bash
# CRUD tests only
uv run pytest tests/ -m crud

# LLM-dependent tests only
uv run pytest tests/ -m llm

# Authentication tests only
uv run pytest tests/ -m auth

# Skip slow tests
uv run pytest tests/ -m "not slow"
```

### Using the Test Runner Script

The `run_tests.py` script provides a convenient way to run different types of tests:

```bash
# Run all tests
python tests/run_tests.py --all

# Run CRUD tests only
python tests/run_tests.py --type crud

# Run LLM tests with verbose output
python tests/run_tests.py --type llm -v

# Run all tests with coverage
python tests/run_tests.py --all --coverage
```

### Test Coverage

To run tests with coverage reporting:

```bash
uv run pytest tests/ --cov=. --cov-report=html --cov-report=term
```

This will generate:

- A terminal coverage report
- An HTML coverage report in `htmlcov/` directory

## Test Database

Tests use an in-memory SQLite database that is created and destroyed for each test. This ensures:

- Tests are isolated from each other
- No external database setup is required
- Tests run quickly
- No data pollution between tests

## Mocking

The tests use extensive mocking to:

- **Isolate LLM dependencies** - LLM service calls are mocked to avoid external API calls
- **Speed up tests** - External services are mocked to make tests run faster
- **Test error conditions** - Service failures are simulated to test error handling

### Key Mocked Services

- `tasks.service.generate_questions` - Task generation from documents
- `tasks.service.evaluate_student_answer` - Answer evaluation
- `documents.service.generate_document_title` - Document title generation
- `auth.service.*` - Authentication and user management services

## Test Fixtures

### Database Fixtures

- **`db_session`** - Fresh database session for each test
- **`client`** - TestClient with overridden database dependencies

### Authentication Fixtures

- **`mock_user`** - Mock user for testing
- **`mock_current_user`** - Mock current user dependency
- **`auth_headers`** - Authentication headers for protected endpoints

### Service Fixtures

- **`mock_llm_service`** - Mocked LLM services
- **`temp_file`** - Temporary file for upload testing

### Data Fixtures

- **`sample_*_data`** - Sample data for different models

## Test Patterns

### CRUD Tests

Each CRUD test follows this pattern:

1. **Setup** - Create test data in database
2. **Action** - Make API request
3. **Assert** - Verify response and database state
4. **Cleanup** - Database is automatically cleaned up

### LLM Tests

LLM tests follow this pattern:

1. **Setup** - Create test data and mock LLM services
2. **Mock** - Configure mock responses
3. **Action** - Make API request
4. **Assert** - Verify response and mock calls
5. **Cleanup** - Automatic cleanup

### Error Handling Tests

Error tests verify:

- Invalid input handling
- Missing resource handling
- Service failure handling
- Authentication/authorization errors

## Adding New Tests

### For New Endpoints

1. Create test functions with descriptive names
2. Use appropriate pytest markers
3. Follow the established patterns
4. Include both success and error cases
5. Test edge cases and validation

### For New Services

1. Mock external dependencies
2. Test both success and failure scenarios
3. Verify service calls are made correctly
4. Test error propagation

### Example Test Structure

```python
@pytest.mark.crud
def test_new_endpoint_success(self, client, db_session):
    """Test successful operation of new endpoint"""
    # Setup
    test_data = create_test_data(db_session)
    
    # Action
    response = client.post("/new-endpoint/", json=test_data)
    
    # Assert
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["expected_field"] == "expected_value"

@pytest.mark.crud
def test_new_endpoint_error(self, client):
    """Test error handling of new endpoint"""
    # Action
    response = client.post("/new-endpoint/", json={})
    
    # Assert
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
```

## Best Practices

1. **Test Isolation** - Each test should be independent
2. **Descriptive Names** - Test names should clearly describe what they test
3. **Comprehensive Coverage** - Test both success and failure scenarios
4. **Fast Execution** - Tests should run quickly (use mocking)
5. **Clear Assertions** - Assertions should be specific and meaningful
6. **Documentation** - Include docstrings explaining test purpose

## Troubleshooting

### Common Issues

1. **Import Errors** - Make sure you're running from the backend directory
2. **Database Errors** - Check that test database is properly configured
3. **Mock Issues** - Verify mock paths match actual import paths
4. **Authentication Errors** - Check that auth fixtures are properly configured

### Debug Mode

To run tests in debug mode:

```bash
uv run pytest tests/ -v -s --pdb
```

This will:

- Show print statements (`-s`)
- Drop into debugger on failures (`--pdb`)
- Show verbose output (`-v`)
