# Pipedream Automation Integrations

This repository contains a collection of Pipedream workflows and integrations for automating tasks between various services. The integrations are organized into modules that handle specific service interactions and data transformations.

## Project Structure

```
.
├── pipedream/                    # Pipedream-specific configurations
│   ├── workflows/               # Workflow definitions (.js files)
│   ├── components/              # Reusable components
│   │   ├── actions/            # Action components
│   │   ├── sources/            # Source components
│   │   └── common/             # Shared utilities
│   ├── sources/                # Event sources
│   └── actions/                # Custom actions
├── library/                     # Python library code
│   ├── src/                    # Source code
│   │   ├── config/             # Configuration files
│   │   ├── utils/              # Shared utility functions
│   │   │   ├── common_utils.py # Common data access and processing utilities
│   │   │   ├── notion_utils.py # Notion-specific utility functions
│   │   │   ├── retry_manager.py # Retry logic with exponential backoff
│   │   │   ├── error_enrichment.py # User-friendly error messages
│   │   │   └── structured_logger.py # JSON structured logging
│   │   └── integrations/       # Service integration modules
│   │       ├── notion_gcal/    # Notion ↔ Google Calendar integration
│   │       └── gmail_notion/   # Gmail → Notion integration
│   ├── tests/                  # Test suite
│   └── docs/                   # Library documentation
├── deployment/                  # Deployment scripts and configs
│   ├── scripts/                # Bundling and deployment scripts
│   └── templates/              # Template files
├── docs/                       # General documentation
└── .github/                    # GitHub configuration
    ├── workflows/              # CI/CD workflows
    └── ISSUE_TEMPLATE/         # Issue templates
```

## Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- pip (Python package manager)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pipedream-automation.git
   cd pipedream-automation
   ```

2. Install dependencies:
   ```bash
   cd library
   make install
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

### Development Tools

The project uses several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Code linting
- **mypy**: Static type checking
- **pydocstyle**: Docstring checking
- **pytest**: Testing framework
- **pre-commit**: Git hooks for code quality

### Common Development Tasks

Use the provided Makefile commands:

```bash
cd library
make install    # Install dependencies and pre-commit hooks
make test      # Run tests
make lint      # Run all linters
make format    # Format code
make clean     # Clean up cache and build files
```

## Testing

### Running Tests

Run the complete test suite:
```bash
cd library
make test
```

Run tests with coverage:
```bash
cd library
pytest --cov=src --cov-report=term-missing
```

### Test Coverage

- The project enforces a minimum test coverage threshold of **70%** (see `pytest.ini`).
- Coverage reports are:
  - Generated locally using pytest-cov
  - Uploaded to Codecov for pull requests
  - Available in the CI/CD pipeline

## Continuous Integration

The project uses GitHub Actions for CI/CD:

- Runs on every push to main and pull requests
- Tests against Python 3.8, 3.9, 3.10, and 3.11
- Performs code quality checks:
  - Code formatting (black)
  - Import sorting (isort)
  - Linting (flake8)
  - Type checking (mypy)
  - Docstring checking (pydocstyle)
- Generates and uploads test coverage reports

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Install development dependencies:
   ```bash
   cd library
   make install
   ```
4. Make your changes
5. Run tests and linters:
   ```bash
   cd library
   make test
   make lint
   ```
6. Submit a pull request

For more details, see our [Contributing Guidelines](.github/CONTRIBUTING.md).

## Issue Reporting

We use GitHub Issues for bug tracking and feature requests. Please use our templates:
- [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md)
- [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md)

## Security

If you discover a security vulnerability, please follow our [Security Policy](.github/SECURITY.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Integrations

### Notion ↔ Google Calendar Integration

This integration provides bidirectional synchronization between Notion tasks and Google Calendar events:

1. **Notion Task to Calendar Event** (`task_to_event.py`)
   - Converts Notion tasks with due dates to Google Calendar events
   - Preserves task details and links back to Notion
   - Handles task updates and deletions

2. **Calendar Event to Notion** (`calendar_to_notion.py`)
   - Processes Google Calendar events linked to Notion pages
   - Extracts Notion page IDs from event locations
   - Updates Notion pages with event details

3. **Update Handler** (`update_handler.py`)
   - Manages updates to Notion tasks
   - Synchronizes changes with corresponding Calendar events
   - Handles error cases and edge conditions

### Gmail → Notion Integration

This integration automates the process of creating Notion tasks from Gmail emails:

1. **Email Fetcher** (`fetch_emails.py`)
   - Fetches emails from Gmail based on specified labels
   - Filters and processes email content
   - Prepares data for Notion task creation

2. **Task Creator** (`create_notion_task.py`)
   - Creates Notion tasks from email content
   - Handles HTML content and attachments
   - Links back to original emails

3. **Label Manager** (`label_processed.py`)
   - Labels processed emails in Gmail
   - Prevents duplicate processing
   - Maintains processing history

## Utility Functions

### Common Utilities (`common_utils.py`)

- `safe_get`: Safely accesses nested dictionary keys or list indices
- `extract_id_from_url`: Extracts IDs from URLs using regex patterns

### Notion Utilities (`notion_utils.py`)

- Notion-specific data extraction and formatting
- API request handling and error management
- Data validation and transformation

### Reliability & Developer Experience Utilities

The project includes enterprise-grade utilities for enhanced reliability and debugging:

#### Retry Manager (`retry_manager.py`)

Provides robust retry logic with exponential backoff for external API calls:

- **Service-specific retry policies**: Notion (5 retries), Gmail (3 retries), OpenAI (4 retries), Google Calendar (3 retries)
- **Exponential backoff with jitter**: Prevents thundering herd problems
- **Configurable retry conditions**: Customize which exceptions trigger retries
- **Request ID tracking**: Correlate retries across function calls

```python
from library.src.utils.retry_manager import with_retry

@with_retry(service='notion')
def create_notion_page(data):
    # API call with automatic retry logic
    return requests.post(url, json=data)
```

#### Error Enrichment (`error_enrichment.py`)

Enriches errors with context and provides user-friendly messages:

- **Pattern-based error matching**: Automatically categorizes common API errors
- **Service-specific error handling**: Tailored messages for different services
- **Context preservation**: Maintains original error details for debugging
- **User-friendly formatting**: Converts technical errors to actionable messages

```python
from library.src.utils.error_enrichment import enrich_error

try:
    api_call()
except Exception as e:
    enriched = enrich_error(e, 'notion', {'operation': 'create_page'})
    logger.error(enriched.user_message)
```

#### Structured Logger (`structured_logger.py`)

Provides JSON-structured logging with request tracking and context propagation:

- **Request ID correlation**: Track operations across function boundaries
- **JSON structured output**: Easy parsing for log aggregation systems
- **Context propagation**: Thread-safe context storage and retrieval
- **Performance timing**: Built-in operation duration tracking
- **Pipedream integration**: Specialized logging for Pipedream workflows

```python
from library.src.utils.structured_logger import get_pipedream_logger

logger = get_pipedream_logger('workflow_name')
with logger.request_context() as request_id:
    logger.info("Processing started", user_id="123")
    # All logs in this context include the request_id
```

## Deployment

### Bundling Python Modules

This repository uses a bundling system to create self-contained Python modules for Pipedream deployment:

```bash
# Bundle all modules
cd deployment/scripts
python bundle_for_pipedream_v2.py --all

# Bundle specific module
python bundle_for_pipedream_v2.py --module gmail_to_notion
```

The bundler creates ready-to-deploy Python files in `deployment/scripts/pipedream_modules/` that include all dependencies.

### Deploying to Pipedream

1. **Using Pipedream CLI**:
   ```bash
   # Deploy a workflow
   pd deploy pipedream/workflows/gmail-to-notion.js
   ```

2. **Using Pipedream Web Interface**:
   - Copy the bundled module content from `deployment/scripts/pipedream_modules/`
   - Paste into a new Python code step in your workflow
   - Configure the workflow inputs and triggers

See [deployment/DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) for detailed deployment instructions.

## Usage

### Notion ↔ Google Calendar Integration

1. Set up a Pipedream workflow with a Notion trigger
2. Bundle the required modules: `notion_to_gcal`, `calendar_to_notion`
3. Deploy the workflow using the bundled JavaScript files in `pipedream/workflows/`
4. Configure authentication and database IDs in the workflow settings

### Gmail → Notion Integration

1. Set up a Pipedream workflow with a Gmail trigger
2. Bundle the `gmail_to_notion` module
3. Deploy the workflow using `pipedream/workflows/gmail-to-notion.js`
4. Configure Gmail query parameters and Notion database ID

## Code Quality & Repo Hygiene

- The repository includes a `.gitignore` file to keep out virtual environments, build/test artifacts, and IDE/editor files.
- A `.cursor-rules.yaml` file is present for best practices with Cursor.
- Pre-commit hooks are set up for linting and formatting. 