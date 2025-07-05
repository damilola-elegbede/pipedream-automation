"""
Tests for validation utilities.

This module tests input validation, authentication extraction,
and data sanitization functions.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime

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
from src.utils.error_handling import ValidationError


class TestValidatePipedreamInputs:
    """Test validate_pipedream_inputs function."""

    def test_valid_inputs(self):
        """Test with valid inputs."""
        pd = Mock()
        pd.inputs = {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3"
        }
        
        result = validate_pipedream_inputs(pd, ["field1", "field2"])
        assert result == {
            "field1": "value1",
            "field2": "value2"
        }

    def test_missing_required_field(self):
        """Test with missing required field."""
        pd = Mock()
        pd.inputs = {"field1": "value1"}
        
        with pytest.raises(ValidationError) as exc_info:
            validate_pipedream_inputs(pd, ["field1", "field2"])
        assert "field2" in str(exc_info.value)

    def test_no_inputs_attribute(self):
        """Test with missing inputs attribute."""
        pd = Mock()
        del pd.inputs
        
        with pytest.raises(ValidationError) as exc_info:
            validate_pipedream_inputs(pd, ["field1"])
        assert "inputs" in str(exc_info.value)

    def test_empty_required_fields(self):
        """Test with empty required fields list."""
        pd = Mock()
        pd.inputs = {"field1": "value1"}
        
        result = validate_pipedream_inputs(pd, [])
        assert result == {}


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
        """Test with missing service."""
        pd = Mock()
        pd.inputs = {}
        
        with pytest.raises(ValidationError) as exc_info:
            extract_authentication(pd, "notion")
        assert "notion" in str(exc_info.value)

    def test_missing_auth_field(self):
        """Test with missing auth field."""
        pd = Mock()
        pd.inputs = {
            "notion": {
                "$auth": {}
            }
        }
        
        with pytest.raises(ValidationError) as exc_info:
            extract_authentication(pd, "notion")
        assert "oauth_access_token" in str(exc_info.value)


class TestValidateNotionAuth:
    """Test validate_notion_auth function."""

    def test_valid_token(self):
        """Test with valid Notion token."""
        token = "secret_valid_token_123"
        assert validate_notion_auth(token) is True

    def test_invalid_token_format(self):
        """Test with invalid token format."""
        assert validate_notion_auth("invalid") is False
        assert validate_notion_auth("") is False
        assert validate_notion_auth(None) is False

    def test_token_with_secret_prefix(self):
        """Test token with secret prefix."""
        assert validate_notion_auth("secret_abc123") is True
        assert validate_notion_auth("ntn_abc123") is True


class TestValidateGoogleAuth:
    """Test validate_google_auth function."""

    def test_valid_token(self):
        """Test with valid Google token."""
        token = "ya29.valid_google_token"
        assert validate_google_auth(token) is True

    def test_invalid_token_format(self):
        """Test with invalid token format."""
        assert validate_google_auth("") is False
        assert validate_google_auth(None) is False
        assert validate_google_auth("short") is False


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
            None,
        ]
        
        for email in invalid_emails:
            assert validate_email(email) is False


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
            None,
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False


class TestValidateDateFormat:
    """Test validate_date_format function."""

    def test_valid_iso_dates(self):
        """Test with valid ISO format dates."""
        valid_dates = [
            "2024-01-01",
            "2024-12-31",
            "2024-01-01T10:30:00",
            "2024-01-01T10:30:00Z",
            "2024-01-01T10:30:00+00:00",
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
            "2024-1-1",
            "",
            None,
        ]
        
        for date in invalid_dates:
            assert validate_date_format(date) is False

    def test_custom_format(self):
        """Test with custom date format."""
        assert validate_date_format("01/31/2024", "%m/%d/%Y") is True
        assert validate_date_format("31-01-2024", "%d-%m-%Y") is True
        assert validate_date_format("invalid", "%Y-%m-%d") is False


class TestSanitizeString:
    """Test sanitize_string function."""

    def test_basic_sanitization(self):
        """Test basic string sanitization."""
        assert sanitize_string("  hello  ") == "hello"
        assert sanitize_string("hello\nworld") == "hello world"
        assert sanitize_string("hello\tworld") == "hello world"

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

    def test_empty_and_none(self):
        """Test empty and None inputs."""
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""
        assert sanitize_string("   ") == ""

    def test_special_characters(self):
        """Test with special characters."""
        assert sanitize_string("hello@world.com") == "hello@world.com"
        assert sanitize_string("price: $100") == "price: $100"
        assert sanitize_string("emoji 😊") == "emoji 😊"


class TestValidateRequiredFields:
    """Test validate_required_fields function."""

    def test_all_fields_present(self):
        """Test with all required fields present."""
        data = {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3",
        }
        
        result = validate_required_fields(data, ["field1", "field2"])
        assert result is True

    def test_missing_required_field(self):
        """Test with missing required field."""
        data = {"field1": "value1"}
        
        with pytest.raises(ValidationError) as exc_info:
            validate_required_fields(data, ["field1", "field2"])
        assert "field2" in str(exc_info.value)

    def test_empty_required_field(self):
        """Test with empty required field."""
        data = {"field1": "value1", "field2": ""}
        
        with pytest.raises(ValidationError) as exc_info:
            validate_required_fields(data, ["field1", "field2"])
        assert "field2" in str(exc_info.value)

    def test_optional_fields(self):
        """Test with optional fields."""
        data = {"field1": "value1", "optional": ""}
        
        result = validate_required_fields(
            data, 
            ["field1"], 
            optional_fields=["optional", "missing"]
        )
        assert result is True

    def test_no_data(self):
        """Test with None or empty data."""
        with pytest.raises(ValidationError):
            validate_required_fields(None, ["field1"])
        
        with pytest.raises(ValidationError):
            validate_required_fields({}, ["field1"])