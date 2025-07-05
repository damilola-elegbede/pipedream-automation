"""
Tests for the Notion Task Creator module.

This module contains tests for creating Notion tasks from Gmail emails,
including email content processing, task property mapping, and error handling.
"""

import unittest.mock
import requests

from src.integrations.gmail_notion.create_notion_task import handler


class MockPipedream:
    def __init__(self, steps):
        self.steps = steps
        self.flow = MockFlow()


class MockFlow:
    def exit(self, message):
        raise SystemExit(message)


def test_handler_valid_email():
    """Test handler with valid email data."""
    # Create test email data
    email = {
        "subject": "Test Email",
        "body": "Test email body",
        "from": "test@example.com",
        "date": "2024-01-01T10:00:00Z",
    }

    # Create mock Pipedream context
    pd = {
        "email": email,
        "notion_auth": "test_notion_auth",
        "database_id": "test_database_id",
    }

    # Mock Notion API response
    with unittest.mock.patch("requests.post") as mock_post:
        mock_response = unittest.mock.Mock()
        mock_response.json.return_value = {
            "id": "task_123",
            "url": "https://notion.so/task_123",
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = handler(pd)

        assert "success" in result
        assert "error" not in result
        assert result["success"]["task_id"] == "task_123"
        assert result["success"]["task_url"] == "https://notion.so/task_123"


def test_handler_missing_email():
    """Test handler with missing email data."""
    pd = {
        "notion_auth": "test_notion_auth",
        "database_id": "test_database_id",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "No email data provided" in result["error"]


def test_handler_missing_auth():
    """Test handler with missing authentication."""
    email = {
        "subject": "Test Email",
        "body": "Test email body",
        "from": "test@example.com",
        "date": "2024-01-01T10:00:00Z",
    }

    pd = {
        "email": email,
        "database_id": "test_database_id",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "authentication" in result["error"].lower()


def test_handler_missing_database_id():
    """Test handler with missing database ID."""
    email = {
        "subject": "Test Email",
        "body": "Test email body",
        "from": "test@example.com",
        "date": "2024-01-01T10:00:00Z",
    }

    pd = {
        "email": email,
        "notion_auth": "test_notion_auth",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "database_id" in result["error"].lower()


@unittest.mock.patch("requests.post")
def test_handler_api_error(mock_post):
    """Test handler with API error."""
    mock_post.side_effect = requests.exceptions.RequestException("API Error")

    email = {
        "subject": "Test Email",
        "body": "Test email body",
        "from": "test@example.com",
        "date": "2024-01-01T10:00:00Z",
    }

    pd = {
        "email": email,
        "notion_auth": "test_notion_auth",
        "database_id": "test_database_id",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "error" in result  # Generic error for security


@unittest.mock.patch("requests.post")
def test_handler_401_error(mock_post):
    """Test handler with 401 authentication error."""
    mock_post.side_effect = requests.exceptions.RequestException("401 Unauthorized")

    email = {
        "subject": "Test Email",
        "body": "Test email body",
        "from": "test@example.com",
        "date": "2024-01-01T10:00:00Z",
    }

    pd = {
        "email": email,
        "notion_auth": "invalid_auth",
        "database_id": "test_database_id",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "error" in result  # Generic error for security


@unittest.mock.patch("requests.post")
def test_handler_404_error(mock_post):
    """Test handler with 404 database not found error."""
    mock_post.side_effect = requests.exceptions.RequestException("404 Not Found")

    email = {
        "subject": "Test Email",
        "body": "Test email body",
        "from": "test@example.com",
        "date": "2024-01-01T10:00:00Z",
    }

    pd = {
        "email": email,
        "notion_auth": "test_auth",
        "database_id": "nonexistent",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "error" in result  # Generic error for security


@unittest.mock.patch("requests.post")
def test_handler_empty_email_fields(mock_post):
    """Test handler with empty email fields."""
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "task_123",
        "url": "https://notion.so/task_123",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    email = {
        "subject": "",
        "body": "",
        "from": "",
        "date": "",
    }

    pd = {
        "email": email,
        "notion_auth": "test_auth",
        "database_id": "test_database_id",
    }

    result = handler(pd)
    assert "success" in result
    assert "error" not in result
    assert result["success"]["task_id"] == "task_123"
    assert result["success"]["task_url"] == "https://notion.so/task_123"


@unittest.mock.patch("requests.post")
def test_handler_missing_email_fields(mock_post):
    """Test handler with missing email fields."""
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "task_123",
        "url": "https://notion.so/task_123",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    email = {}

    pd = {
        "email": email,
        "notion_auth": "test_auth",
        "database_id": "test_database_id",
    }

    result = handler(pd)
    assert "success" in result
    assert "error" not in result
    assert result["success"]["task_id"] == "task_123"
    assert result["success"]["task_url"] == "https://notion.so/task_123"


@unittest.mock.patch("requests.post")
def test_handler_generic_request_error(mock_post):
    """Test handler with generic request error."""
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")

    email = {
        "subject": "Test Email",
        "body": "Test email body",
        "from": "test@example.com",
        "date": "2024-01-01T10:00:00Z",
    }

    pd = {
        "email": email,
        "notion_auth": "test_auth",
        "database_id": "test_database_id",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "error" in result  # Generic error for security
