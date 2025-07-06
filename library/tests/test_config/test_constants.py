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
    GOOGLE_CALENDAR_API_BASE_URL,
    
    # Gmail URLs
    GMAIL_API_BASE_URL,
    GMAIL_MESSAGES_URL,
    
    # Default Values
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    BATCH_SIZE,
    
    # Notion Property Types
    NOTION_PROPERTY_TYPES,
    
    # Error Messages
    ERROR_MISSING_AUTH,
    ERROR_INVALID_INPUT,
    ERROR_API_REQUEST,
    
    # Success Messages
    SUCCESS_CREATED,
    SUCCESS_UPDATED,
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
        assert GOOGLE_CALENDAR_API_BASE_URL == "https://www.googleapis.com/calendar/v3"
        
        # Verify URLs are valid
        assert GOOGLE_CALENDAR_API_BASE_URL.startswith("https://")
        assert "googleapis.com" in GOOGLE_CALENDAR_API_BASE_URL

    def test_gmail_urls(self):
        """Test Gmail API URLs."""
        assert GMAIL_API_BASE_URL == "https://gmail.googleapis.com/gmail/v1/users/me"
        assert GMAIL_MESSAGES_URL == f"{GMAIL_API_BASE_URL}/messages"
        
        # Verify URLs are valid
        assert GMAIL_API_BASE_URL.startswith("https://")
        assert "googleapis.com" in GMAIL_API_BASE_URL


class TestDefaultValues:
    """Test default configuration values."""

    def test_timeout_values(self):
        """Test timeout is reasonable."""
        assert isinstance(DEFAULT_TIMEOUT, int)
        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT <= 60  # Should not exceed 60 seconds

    def test_retry_values(self):
        """Test retry count is reasonable."""
        assert isinstance(MAX_RETRIES, int)
        assert MAX_RETRIES >= 1
        assert MAX_RETRIES <= 5  # Should not retry too many times

    def test_batch_size_values(self):
        """Test batch size is reasonable."""
        assert isinstance(BATCH_SIZE, int)
        assert BATCH_SIZE >= 10
        assert BATCH_SIZE <= 1000  # Reasonable batch size


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

    def test_error_messages(self):
        """Test error message constants."""
        assert isinstance(ERROR_MISSING_AUTH, str)
        assert isinstance(ERROR_INVALID_INPUT, str)
        assert isinstance(ERROR_API_REQUEST, str)
        
        # Test messages are not empty
        assert len(ERROR_MISSING_AUTH) > 0
        assert len(ERROR_INVALID_INPUT) > 0
        assert len(ERROR_API_REQUEST) > 0

    def test_error_message_placeholders(self):
        """Test error messages with placeholders."""
        # Test ERROR_INVALID_INPUT placeholder
        assert "{}" in ERROR_INVALID_INPUT
        msg = ERROR_INVALID_INPUT.format("test_field")
        assert "test_field" in msg
        
        # Test ERROR_API_REQUEST placeholder
        assert "{}" in ERROR_API_REQUEST
        msg = ERROR_API_REQUEST.format("Connection error")
        assert "Connection error" in msg

    def test_success_messages(self):
        """Test success message constants."""
        assert isinstance(SUCCESS_CREATED, str)
        assert isinstance(SUCCESS_UPDATED, str)
        
        # Test messages are not empty
        assert len(SUCCESS_CREATED) > 0
        assert len(SUCCESS_UPDATED) > 0
        
        # Test placeholders
        assert "{}" in SUCCESS_CREATED
        assert "{}" in SUCCESS_UPDATED


class TestConstantConsistency:
    """Test consistency across constants."""

    def test_url_consistency(self):
        """Test URL patterns are consistent."""
        # All Notion URLs should use the same base
        notion_urls = [NOTION_PAGES_URL, NOTION_DATABASES_URL, NOTION_SEARCH_URL, NOTION_BLOCKS_URL]
        for url in notion_urls:
            assert url.startswith(NOTION_API_BASE_URL)

        # All Google URLs should use HTTPS
        google_urls = [GOOGLE_CALENDAR_API_BASE_URL]
        for url in google_urls:
            assert url.startswith("https://www.googleapis.com/")
        
        # Gmail uses different subdomain
        assert GMAIL_API_BASE_URL.startswith("https://gmail.googleapis.com/")

    def test_no_trailing_slashes(self):
        """Test URLs don't have trailing slashes."""
        all_urls = [
            NOTION_API_BASE_URL, NOTION_PAGES_URL, NOTION_DATABASES_URL,
            GOOGLE_CALENDAR_API_BASE_URL, GMAIL_API_BASE_URL
        ]
        
        for url in all_urls:
            assert not url.endswith("/"), f"URL {url} should not end with /"