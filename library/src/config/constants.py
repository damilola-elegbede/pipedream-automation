"""
Central configuration constants for Pipedream automation.

This module contains all shared constants used across integration modules,
eliminating duplication and providing a single source of truth.
"""

# API Base URLs
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"
NOTION_PAGES_URL = f"{NOTION_API_BASE_URL}/pages"
NOTION_DATABASES_URL = f"{NOTION_API_BASE_URL}/databases"
NOTION_BLOCKS_URL = f"{NOTION_API_BASE_URL}/blocks"
NOTION_SEARCH_URL = f"{NOTION_API_BASE_URL}/search"

GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_MESSAGES_URL = f"{GMAIL_API_BASE_URL}/messages"
GMAIL_THREADS_URL = f"{GMAIL_API_BASE_URL}/threads"
GMAIL_LABELS_URL = f"{GMAIL_API_BASE_URL}/labels"

GOOGLE_CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"

# Timeouts and Limits
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
BATCH_SIZE = 100
MAX_NOTION_BLOCKS = 100  # Notion API limit

# HTTP Headers
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
}

NOTION_HEADERS = {
    **DEFAULT_HEADERS,
    "Notion-Version": NOTION_API_VERSION,
}

# Error Messages
ERROR_MISSING_AUTH = "Authentication credentials not found"
ERROR_INVALID_INPUT = "Required input field '{}' is missing"
ERROR_API_REQUEST = "API request failed: {}"
ERROR_INVALID_RESPONSE = "Invalid response from API: {}"
ERROR_TIMEOUT = "Request timed out after {} seconds"
ERROR_RATE_LIMIT = "Rate limit exceeded. Please try again later"

# Success Messages
SUCCESS_CREATED = "Successfully created {}"
SUCCESS_UPDATED = "Successfully updated {}"
SUCCESS_DELETED = "Successfully deleted {}"
SUCCESS_PROCESSED = "Successfully processed {}"

# Gmail Labels
GMAIL_PROCESSED_LABEL = "Pipedream/Processed"
GMAIL_ERROR_LABEL = "Pipedream/Error"

# Notion Property Types
NOTION_PROPERTY_TYPES = {
    "title": "title",
    "rich_text": "rich_text",
    "number": "number",
    "select": "select",
    "multi_select": "multi_select",
    "date": "date",
    "people": "people",
    "files": "files",
    "checkbox": "checkbox",
    "url": "url",
    "email": "email",
    "phone_number": "phone_number",
    "formula": "formula",
    "relation": "relation",
    "rollup": "rollup",
    "created_time": "created_time",
    "created_by": "created_by",
    "last_edited_time": "last_edited_time",
    "last_edited_by": "last_edited_by",
}

# Google Calendar Event Status
GCAL_EVENT_STATUS = {
    "confirmed": "confirmed",
    "tentative": "tentative",
    "cancelled": "cancelled",
}

# Default Values
DEFAULT_TIMEZONE = "UTC"
DEFAULT_EVENT_DURATION = 60  # minutes
DEFAULT_REMINDER_MINUTES = 10