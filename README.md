# Pipedream Automation - Gmail, Notion & Google Tasks

This repository contains Python workflow steps for Pipedream that automate tasks between Gmail, Notion, and Google Tasks.

## Overview

The integrations provide:
- **Gmail → Notion**: Automatically create Notion tasks from labeled emails
- **Notion → Google Tasks**: Create Google Tasks from Notion tasks with due dates
- **Google Tasks → Notion**: Sync task completion status back to Notion

## Project Structure

```
.
├── src/
│   └── steps/                    # Pipedream Python step handlers
│       ├── fetch_gmail_emails.py # Fetch emails by label from Gmail
│       ├── create_notion_task.py # Create Notion tasks from emails
│       ├── label_gmail_processed.py # Label processed emails
│       ├── notion_task_to_google.py # Create Google Tasks from Notion tasks
│       ├── notion_update_to_google.py # Update Google Tasks from Notion changes
│       └── google_to_notion.py   # Sync Google Task changes to Notion
├── tests/                        # Test suite
├── docs/                         # Additional documentation
└── .github/workflows/            # CI/CD pipeline
```

## Pipedream Steps

Each file in `src/steps/` is a self-contained Python script designed to be copied into a Pipedream Python step.

### Gmail to Notion Workflow

1. **fetch_gmail_emails.py** - Fetches emails with a specific label (e.g., "notion") and extracts content
2. **create_notion_task.py** - Creates Notion database entries from email data, with duplicate detection
3. **label_gmail_processed.py** - Labels processed emails to prevent re-processing

### Notion to Google Tasks Workflow

4. **notion_task_to_google.py** - Prepares Notion task data for creating Google Tasks
5. **notion_update_to_google.py** - Handles Notion updates to sync to existing Google Tasks (including completion status)

### Google Tasks to Notion Sync

6. **google_to_notion.py** - Syncs Google Task changes (completion status, due dates) back to Notion

## Setup

### Prerequisites

- Python 3.8+
- Pipedream account with connected:
  - Gmail (with `gmail.readonly` and `gmail.modify` scopes)
  - Notion (OAuth connection)
  - Google Tasks (for task sync workflows)

### Environment Variables in Pipedream

Set these in **Pipedream Settings → Environment Variables**:

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_DATABASE_ID` | Yes | Your Notion database ID (32-char hex) |
| `HCTI_USER_ID` | Optional | HTML/CSS to Image API user ID |
| `HCTI_API_KEY` | Optional | HTML/CSS to Image API key |

### Deploying to Pipedream

1. Create a new Pipedream workflow
2. Add a trigger (Gmail, Notion webhook, or Google Calendar)
3. Add a Python code step
4. Copy the contents of the appropriate `src/steps/*.py` file
5. Configure the step inputs (connect accounts)
6. Rename the step to match the expected step names (e.g., "gmail", "notion")

## Development

### Installation

```bash
git clone https://github.com/yourusername/pipedream-automation.git
cd pipedream-automation
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Run specific test file
pytest tests/test_create_notion_task.py -v
```

### Code Formatting

```bash
make format
```

## Key Features

### Duplicate Detection

The `create_notion_task.py` step includes duplicate detection:
- Stores Gmail Message ID in each Notion task
- Queries Notion before creating to skip duplicates
- Always returns `successful_mappings` for downstream labeling

### Robust Error Handling

- Exponential backoff with Retry-After header support for rate limits
- All steps handle API errors gracefully
- Failed operations are tracked and reported
- Partial successes are handled (some emails succeed, some fail)

### Bidirectional Completion Sync

- **Notion → Google Tasks**: "List" field set to "Completed" marks Google Task as complete
- **Google Tasks → Notion**: Completing a task in Google Tasks sets Notion "List" to "Completed"
- Tasks use the `notes` field to store Notion URL for reverse sync identification

### Efficient API Usage

- Gmail Batch API for labeling (up to 100 messages per request)
- Pipedream Data Store caching for label IDs
- RFC 3339 date format for Google Tasks compatibility

### Pagination Limits

- `fetch_gmail_emails.py` respects a configurable `max_results` limit (default: 50)
- Prevents timeout issues with large email volumes

## Testing

The test suite covers:
- Unit tests for helper functions
- Integration tests for handlers with mocked APIs
- Edge cases (missing data, API errors, duplicates)

```bash
# Run tests
pytest tests/ -v
```

## CI/CD

GitHub Actions runs on every push/PR to main:
- Tests against Python 3.8 and 3.12
- Reports to Codecov

## License

MIT License - see [LICENSE](LICENSE)
