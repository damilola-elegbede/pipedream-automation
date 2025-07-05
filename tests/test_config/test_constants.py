"""
Tests for configuration constants.

This module tests that all constants are properly defined
and have the expected values and formats.
"""

import re
from src.config.constants import (
    # API URLs
    NOTION_API_BASE_URL,
    NOTION_API_VERSION,
    NOTION_PAGES_URL,
    NOTION_DATABASES_URL,
    NOTION_SEARCH_URL,
    NOTION_BLOCKS_URL,
    
    # Google Calendar URLs
    GOOGLE_CALENDAR_API_BASE,
    GOOGLE_CALENDAR_EVENTS_URL,
    
    # Gmail URLs
    GMAIL_API_BASE,
    GMAIL_MESSAGES_URL,
    
    # Default Values
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    
    # Notion Property Types
    NOTION_PROPERTY_TYPES,
    
    # Error Messages
    ERROR_MESSAGES,
    
    # Success Messages
    SUCCESS_MESSAGES,
)


class TestAPIUrls:
    """Test API URL constants."""

    def test_notion_urls(self):
        """Test Notion API URLs are properly formatted."""
        assert NOTION_API_BASE_URL == "https://api.notion.com/v1"
        assert NOTION_API_VERSION == "2022-06-28"
        assert NOTION_PAGES_URL == f"{NOTION_API_BASE_URL}/pages"
        assert NOTION_DATABASES_URL == f"{NOTION_API_BASE_URL}/databases"
        assert NOTION_SEARCH_URL == f"{NOTION_API_BASE_URL}/search"
        assert NOTION_BLOCKS_URL == f"{NOTION_API_BASE_URL}/blocks"
        
        # Verify URLs are valid HTTPS URLs
        url_pattern = re.compile(r'^https://[^\s]+$')
        assert url_pattern.match(NOTION_API_BASE_URL)
        assert url_pattern.match(NOTION_PAGES_URL)

    def test_google_calendar_urls(self):
        """Test Google Calendar API URLs."""
        assert GOOGLE_CALENDAR_API_BASE == "https://www.googleapis.com/calendar/v3"
        assert GOOGLE_CALENDAR_EVENTS_URL == f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events"
        
        # Verify URLs are valid
        assert GOOGLE_CALENDAR_API_BASE.startswith("https://")
        assert "googleapis.com" in GOOGLE_CALENDAR_API_BASE

    def test_gmail_urls(self):
        """Test Gmail API URLs."""
        assert GMAIL_API_BASE == "https://www.googleapis.com/gmail/v1"
        assert GMAIL_MESSAGES_URL == f"{GMAIL_API_BASE}/users/me/messages"
        
        # Verify URLs are valid
        assert GMAIL_API_BASE.startswith("https://")
        assert "googleapis.com" in GMAIL_API_BASE


class TestDefaultValues:
    """Test default configuration values."""

    def test_timeout_values(self):
        """Test timeout is reasonable."""
        assert isinstance(DEFAULT_TIMEOUT, int)
        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT <= 60  # Should not exceed 60 seconds

    def test_retry_values(self):
        """Test retry count is reasonable."""
        assert isinstance(DEFAULT_MAX_RETRIES, int)
        assert DEFAULT_MAX_RETRIES >= 1
        assert DEFAULT_MAX_RETRIES <= 5  # Should not retry too many times

    def test_page_size_values(self):
        """Test page size is reasonable."""
        assert isinstance(DEFAULT_PAGE_SIZE, int)
        assert DEFAULT_PAGE_SIZE >= 10
        assert DEFAULT_PAGE_SIZE <= 100  # API limits


class TestNotionPropertyTypes:
    """Test Notion property type constants."""

    def test_property_types_dict(self):
        """Test property types dictionary structure."""
        assert isinstance(NOTION_PROPERTY_TYPES, dict)
        assert len(NOTION_PROPERTY_TYPES) > 0

    def test_required_property_types(self):
        """Test required property types are present."""
        required_types = [
            "title", "rich_text", "number", "select", 
            "multi_select", "date", "checkbox", "url", 
            "email", "phone_number"
        ]
        
        for prop_type in required_types:
            assert prop_type in NOTION_PROPERTY_TYPES
            assert NOTION_PROPERTY_TYPES[prop_type] == prop_type


class TestMessages:
    """Test message templates."""

    def test_error_messages_structure(self):
        """Test error messages dictionary structure."""
        assert isinstance(ERROR_MESSAGES, dict)
        assert len(ERROR_MESSAGES) > 0

    def test_error_message_keys(self):
        """Test required error message keys exist."""
        required_keys = [
            "AUTHENTICATION_FAILED",
            "VALIDATION_ERROR",
            "API_ERROR",
            "RATE_LIMIT",
            "NOT_FOUND",
            "GENERIC_ERROR",
        ]
        
        for key in required_keys:
            assert key in ERROR_MESSAGES
            assert isinstance(ERROR_MESSAGES[key], str)
            assert len(ERROR_MESSAGES[key]) > 0

    def test_error_message_placeholders(self):
        """Test error messages with placeholders."""
        # Check if placeholders are properly formatted
        if "{field}" in ERROR_MESSAGES.get("VALIDATION_ERROR", ""):
            # Test placeholder can be formatted
            msg = ERROR_MESSAGES["VALIDATION_ERROR"].format(field="test_field")
            assert "test_field" in msg

    def test_success_messages_structure(self):
        """Test success messages dictionary structure."""
        assert isinstance(SUCCESS_MESSAGES, dict)
        assert len(SUCCESS_MESSAGES) > 0

    def test_success_message_keys(self):
        """Test required success message keys exist."""
        required_keys = [
            "TASK_CREATED",
            "EVENT_CREATED",
            "PAGE_UPDATED",
            "SYNC_COMPLETED",
        ]
        
        for key in required_keys:
            assert key in SUCCESS_MESSAGES
            assert isinstance(SUCCESS_MESSAGES[key], str)
            assert len(SUCCESS_MESSAGES[key]) > 0


class TestConstantConsistency:
    """Test consistency across constants."""

    def test_url_consistency(self):
        """Test URL patterns are consistent."""
        # All Notion URLs should use the same base
        notion_urls = [NOTION_PAGES_URL, NOTION_DATABASES_URL, NOTION_SEARCH_URL, NOTION_BLOCKS_URL]
        for url in notion_urls:
            assert url.startswith(NOTION_API_BASE_URL)

        # All Google URLs should use HTTPS
        google_urls = [GOOGLE_CALENDAR_API_BASE, GMAIL_API_BASE]
        for url in google_urls:
            assert url.startswith("https://www.googleapis.com/")

    def test_no_trailing_slashes(self):
        """Test URLs don't have trailing slashes."""
        all_urls = [
            NOTION_API_BASE_URL, NOTION_PAGES_URL, NOTION_DATABASES_URL,
            GOOGLE_CALENDAR_API_BASE, GMAIL_API_BASE
        ]
        
        for url in all_urls:
            assert not url.endswith("/"), f"URL {url} should not end with /"