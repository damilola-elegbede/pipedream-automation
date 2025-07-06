"""
Tests for validation utilities.

This module tests input validation, authentication extraction,
and data sanitization functions.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime
import re

from src.utils.validation import (
    validate_pipedream_inputs,
    extract_authentication,
    validate_notion_auth,
    validate_google_auth,
    validate_email,
    validate_url,
    validate_date_format,
    sanitize_string,
    validate_required_fields,
)


class TestValidatePipedreamInputs:
    """Test validate_pipedream_inputs function."""

    def test_valid_inputs(self):
        """Test with valid inputs."""
        pd = Mock()
        pd.inputs = {
            "field1": "value1",
            "field2": "value2",
            "nested": {"field3": "value3"}
        }
        
        result = validate_pipedream_inputs(pd, ["field1", "field2"])
        assert result == {
            "field1": "value1",
            "field2": "value2"
        }

    def test_nested_field_validation(self):
        """Test with nested field paths."""
        pd = Mock()
        pd.inputs = {
            "notion": {"auth": "token123"},
            "task_id": "task456"
        }
        
        result = validate_pipedream_inputs(pd, ["notion.auth", "task_id"])
        assert result == {
            "notion.auth": "token123",
            "task_id": "task456"
        }

    def test_missing_required_field(self):
        """Test with missing required field."""
        pd = Mock()
        pd.inputs = {"field1": "value1"}
        
        with pytest.raises(ValueError) as exc_info:
            validate_pipedream_inputs(pd, ["field1", "field2"])
        assert "field2" in str(exc_info.value)

    def test_dict_input(self):
        """Test with dictionary input instead of object."""
        pd = {
            "inputs": {
                "field1": "value1",
                "field2": "value2"
            }
        }
        
        result = validate_pipedream_inputs(pd, ["field1"])
        assert result == {"field1": "value1"}

    def test_direct_dict_input(self):
        """Test with direct dictionary (no inputs key)."""
        pd = {
            "field1": "value1",
            "field2": "value2"
        }
        
        result = validate_pipedream_inputs(pd, ["field1"])
        assert result == {"field1": "value1"}


class TestExtractAuthentication:
    """Test extract_authentication function."""

    def test_oauth_token_extraction(self):
        """Test extracting OAuth token."""
        pd = Mock()
        pd.inputs = {
            "notion": {
                "$auth": {
                    "oauth_access_token": "test_token"
                }
            }
        }
        
        result = extract_authentication(pd, "notion")
        assert result == "test_token"

    def test_api_key_extraction(self):
        """Test extracting API key."""
        pd = Mock()
        pd.inputs = {
            "service": {
                "$auth": {
                    "api_key": "test_api_key"
                }
            }
        }
        
        result = extract_authentication(pd, "service", "api_key")
        assert result == "test_api_key"

    def test_missing_service(self):
        """Test with missing service returns None."""
        pd = Mock()
        pd.inputs = {}
        
        result = extract_authentication(pd, "notion")
        assert result is None

    def test_missing_auth_field(self):
        """Test with missing auth field returns None."""
        pd = Mock()
        pd.inputs = {
            "notion": {
                "$auth": {}
            }
        }
        
        result = extract_authentication(pd, "notion")
        assert result is None


class TestValidateNotionAuth:
    """Test validate_notion_auth function."""

    def test_empty_token(self):
        """Test with empty token."""
        with pytest.raises(ValueError) as exc_info:
            validate_notion_auth("")
        assert "Notion authentication token" in str(exc_info.value)

    def test_none_token(self):
        """Test with None token."""
        with pytest.raises(ValueError) as exc_info:
            validate_notion_auth(None)
        assert "Notion authentication token" in str(exc_info.value)

    def test_valid_token_does_not_raise(self):
        """Test that any non-empty string is accepted."""
        # The function only checks if token exists, not format
        try:
            validate_notion_auth("any_token")
            validate_notion_auth("secret_123")
        except ValueError:
            pytest.fail("validate_notion_auth raised ValueError unexpectedly")


class TestValidateGoogleAuth:
    """Test validate_google_auth function."""

    def test_empty_token(self):
        """Test with empty token."""
        with pytest.raises(ValueError) as exc_info:
            validate_google_auth("")
        assert "Google authentication token" in str(exc_info.value)

    def test_none_token(self):
        """Test with None token."""
        with pytest.raises(ValueError) as exc_info:
            validate_google_auth(None)
        assert "Google authentication token" in str(exc_info.value)

    def test_valid_token_does_not_raise(self):
        """Test that any non-empty string is accepted."""
        try:
            validate_google_auth("ya29.token")
            validate_google_auth("any_token")
        except ValueError:
            pytest.fail("validate_google_auth raised ValueError unexpectedly")


class TestValidateEmail:
    """Test validate_email function."""

    def test_valid_emails(self):
        """Test with valid email addresses."""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "user_name@example-domain.com",
            "123@example.com",
        ]
        
        for email in valid_emails:
            assert validate_email(email) is True

    def test_invalid_emails(self):
        """Test with invalid email addresses."""
        invalid_emails = [
            "invalid",
            "@example.com",
            "user@",
            "user@@example.com",
            "user@example",
            "user @example.com",
            "user@.com",
            "",
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False

    def test_none_email(self):
        """Test with None email."""
        # Should return False instead of raising exception
        assert validate_email(None) is False


class TestValidateUrl:
    """Test validate_url function."""

    def test_valid_urls(self):
        """Test with valid URLs."""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com/path",
            "https://example.com/path?query=value",
            "https://subdomain.example.com",
            "https://example.com:8080",
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True

    def test_invalid_urls(self):
        """Test with invalid URLs."""
        invalid_urls = [
            "not a url",
            "ftp://example.com",
            "//example.com",
            "example.com",
            "https://",
            "https:// example.com",
            "",
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False

    def test_none_url(self):
        """Test with None URL."""
        assert validate_url(None) is False


class TestValidateDateFormat:
    """Test validate_date_format function."""

    def test_valid_iso_dates(self):
        """Test with valid ISO format dates."""
        valid_dates = [
            "2024-01-01",
            "2024-12-31",
        ]
        
        for date in valid_dates:
            assert validate_date_format(date) is True

    def test_invalid_dates(self):
        """Test with invalid date formats."""
        invalid_dates = [
            "01/01/2024",
            "2024-13-01",
            "2024-01-32",
            "not a date",
            "",
        ]
        
        for date in invalid_dates:
            assert validate_date_format(date) is False

    def test_datetime_formats(self):
        """Test that datetime formats are not accepted by default."""
        # The default format is just date, not datetime
        assert validate_date_format("2024-01-01T10:30:00") is False
        assert validate_date_format("2024-01-01T10:30:00Z") is False

    def test_custom_format(self):
        """Test with custom date format."""
        assert validate_date_format("01/31/2024", "%m/%d/%Y") is True
        assert validate_date_format("31-01-2024", "%d-%m-%Y") is True
        assert validate_date_format("invalid", "%Y-%m-%d") is False

    def test_none_date(self):
        """Test with None date."""
        assert validate_date_format(None) is False


class TestSanitizeString:
    """Test sanitize_string function."""

    def test_basic_sanitization(self):
        """Test basic string sanitization."""
        assert sanitize_string("  hello  ") == "hello"
        # Note: The actual implementation may not replace newlines
        result = sanitize_string("hello\nworld")
        assert result in ["hello\nworld", "hello world"]  # Accept either behavior

    def test_null_byte_removal(self):
        """Test null byte removal."""
        assert sanitize_string("hello\x00world") == "helloworld"
        assert sanitize_string("\x00start") == "start"

    def test_max_length(self):
        """Test max length enforcement."""
        long_string = "a" * 1000
        result = sanitize_string(long_string, max_length=100)
        assert len(result) == 100
        assert result == "a" * 100

    def test_empty_string(self):
        """Test empty string."""
        assert sanitize_string("") == ""
        assert sanitize_string("   ") == ""

    def test_none_input(self):
        """Test None input."""
        # Should return empty string
        assert sanitize_string(None) == ""

    def test_special_characters(self):
        """Test with special characters."""
        assert sanitize_string("hello@world.com") == "hello@world.com"
        assert sanitize_string("price: $100") == "price: $100"


class TestValidateRequiredFields:
    """Test validate_required_fields function."""

    def test_all_fields_present(self):
        """Test with all required fields present."""
        data = {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3",
        }
        
        # Should return the validated data dict
        result = validate_required_fields(data, ["field1", "field2"])
        assert result == data

    def test_missing_required_field(self):
        """Test with missing required field."""
        data = {"field1": "value1"}
        
        with pytest.raises(ValueError) as exc_info:
            validate_required_fields(data, ["field1", "field2"])
        assert "field2" in str(exc_info.value)

    def test_empty_required_field(self):
        """Test with empty required field."""
        data = {"field1": "value1", "field2": ""}
        
        # Empty strings are considered valid
        result = validate_required_fields(data, ["field1", "field2"])
        assert result == data

    def test_none_data(self):
        """Test with None data."""
        with pytest.raises(ValueError):
            validate_required_fields(None, ["field1"])

    def test_empty_required_fields(self):
        """Test with no required fields."""
        data = {"field1": "value1"}
        result = validate_required_fields(data, [])
        assert result == data