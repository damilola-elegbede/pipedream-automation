# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Recent Updates (2025-07-05)

- Consolidated all API constants into `src/config/constants.py`
- Created validation utilities in `src/utils/validation.py`
- Added comprehensive error handling in `src/utils/error_handling.py`
- Built module bundler for Pipedream deployment (`scripts/bundle_for_pipedream_v2.py`)
- Generated bundled modules in `pipedream_modules/` directory

## Commands

### Development Setup
```bash
make install    # Install dependencies and pre-commit hooks
```

### Testing
```bash
make test                                      # Run all tests with coverage
pytest                                         # Run all tests (basic)
pytest tests/test_specific_file.py            # Run a specific test file
pytest tests/test_file.py::test_function      # Run a specific test
pytest -k "test_name"                         # Run tests matching pattern
pytest -m unit                                # Run only unit tests
pytest -m integration                         # Run only integration tests
pytest --cov=src --cov-report=term-missing   # Run with detailed coverage report
```

### Code Quality
```bash
make lint       # Run all linters (flake8, mypy, pydocstyle)
make format     # Format code with black and isort
flake8 src tests                              # Run flake8 only
mypy src                                      # Run type checking only
black src tests --check                       # Check formatting without changing
isort src tests --check-only                  # Check import sorting
```

### Clean
```bash
make clean      # Remove all cache, build artifacts, and coverage files
```

### Bundling for Pipedream
```bash
python scripts/bundle_for_pipedream_v2.py --all              # Bundle all modules
python scripts/bundle_for_pipedream_v2.py --module gmail_to_notion  # Bundle specific module
python scripts/update_imports.py                             # Update files to use centralized constants
```

## Architecture

This is a Pipedream automation project that provides integrations between various services (Gmail, Notion, Google Calendar). The architecture follows a modular pattern optimized for Pipedream workflows.

### Core Architecture Pattern

Each integration module follows a consistent handler pattern:
1. **Handler Function**: `handler(pd)` serves as the entry point, receiving Pipedream context
2. **Input Processing**: Flexible parsing of inputs from various Pipedream step formats
3. **Validation**: Early validation of required fields using dedicated validation functions
4. **Error Handling**: Consistent error responses with `{"error": "message"}` format
5. **Success Response**: Structured responses with `{"success": {...}}` format

### Directory Structure

- **src/integrations/**: Individual integration modules for Pipedream workflows
  - `notion_gcal/`: Bidirectional Notion-Google Calendar synchronization
  - `gmail_notion/`: Gmail to Notion task creation pipeline
  - `ai_content_processor.py`: AI-powered content transformation
  
- **src/utils/**: Shared utilities used across integrations
  - `common_utils.py`: Generic helper functions (safe_get, validation, error formatting)
  - `notion_utils.py`: Notion API helpers and property formatting
  - `content_processing.py`: Content transformation and metadata extraction

### Key Integration Flows

**Notion ↔ Google Calendar**:
- `task_to_event.py`: Creates/updates Google Calendar events from Notion tasks
- `calendar_to_notion.py`: Syncs calendar event changes back to Notion
- `update_handler.py`: Manages bidirectional updates
- Uses event IDs stored in Notion for synchronization

**Gmail → Notion**:
- `fetch_emails.py`: Retrieves emails from Gmail with label filtering
- `create_notion_task.py`: Creates Notion tasks from email content
- `label_processed.py`: Marks emails as processed to prevent duplicates

### Common Patterns

**Authentication Handling**:
```python
# Supports both nested and flat authentication structures
token = safe_get(inputs, ["notion", "$auth", "oauth_access_token"])
if not token:
    token = inputs.get("notion_auth")
```

**Input Processing**:
```python
# Flexible input handling for different Pipedream contexts
if hasattr(pd, 'inputs'):
    inputs = pd.inputs
else:
    inputs = pd.get('inputs', pd)
```

**Error Response Pattern**:
All modules return consistent error responses for Pipedream error handling.

## Testing Requirements

- Minimum coverage: 70% (enforced in pytest.ini)
- Test structure mirrors source structure in `tests/` directory
- Test files must start with `test_`
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`

## Code Style

- Python 3.8-3.12 compatible
- Black formatting (80 char line length)
- isort for imports (Black-compatible profile)
- Google-style docstrings (enforced by pydocstyle)
- Type hints throughout (validated by mypy in strict mode)
- flake8 for linting (ignoring E203, F821, W503)

## Integration with Pipedream

All integration modules are designed to work as Pipedream code steps:
1. Receive context via `pd` parameter
2. Extract inputs, authentication, and step data from `pd`
3. Return structured responses that Pipedream can process
4. Handle errors gracefully with informative messages

## Environment Configuration

- Use `.env` file for local development (copy from `.env.example`)
- Store API keys and sensitive configuration in environment variables
- Never commit credentials or API keys to the repository