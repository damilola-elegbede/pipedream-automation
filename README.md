# Pipedream Automation Integrations

This repository contains a collection of Pipedream workflows and integrations for automating tasks between various services. The integrations are organized into modules that handle specific service interactions and data transformations.

## Project Structure

```
.
├── src/                    # Source code
│   ├── utils/             # Shared utility functions
│   │   ├── common_utils.py # Common data access and processing utilities
│   │   └── notion_utils.py # Notion-specific utility functions
│   └── integrations/      # Service integration modules
│       ├── notion_gcal/   # Notion ↔ Google Calendar integration
│       └── gmail_notion/  # Gmail → Notion integration
├── tests/                 # Test suite
├── .github/              # GitHub configuration
│   ├── workflows/        # CI/CD workflows
│   └── ISSUE_TEMPLATE/   # Issue templates
└── docs/                 # Documentation
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
make test
```

Run tests with coverage:
```bash
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
   make install
   ```
4. Make your changes
5. Run tests and linters:
   ```bash
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

## Usage

### Notion ↔ Google Calendar Integration

1. Set up a Pipedream workflow with a Notion trigger
2. Add the `task_to_event.py` step to create Calendar events
3. Configure the `update_handler.py` step to handle updates
4. Add the `calendar_to_notion.py` step to process Calendar events

### Gmail → Notion Integration

1. Set up a Pipedream workflow with a Gmail trigger
2. Add the `fetch_emails.py` step to get emails
3. Configure the `create_notion_task.py` step to create Notion tasks
4. Add the `label_processed.py` step to manage email labels

## Code Quality & Repo Hygiene

- The repository includes a `.gitignore` file to keep out virtual environments, build/test artifacts, and IDE/editor files.
- A `.cursor-rules.yaml` file is present for best practices with Cursor.
- Pre-commit hooks are set up for linting and formatting. 