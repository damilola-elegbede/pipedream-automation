"""
Tests for the Gmail Email Fetcher.

This module contains tests for the Gmail Email Fetcher functionality,
including email retrieval, header extraction, and body parsing.
"""

from unittest.mock import patch

import requests

from src.integrations.gmail_notion.fetch_emails import (
    get_body_parts,
    get_header_value,
    handler,
)


class MockPD:
    def __init__(self, gmail_token=None):
        self.inputs = (
            {"gmail": {"$auth": {"oauth_access_token": gmail_token}}}
            if gmail_token
            else {}
        )
        self.steps = {}


def test_get_header_value():
    """Test extraction of header values from email headers."""
    headers = [
        {"name": "Subject", "value": "Test Subject"},
        {"name": "From", "value": "sender@example.com"},
        {"name": "To", "value": "recipient@example.com"},
    ]

    # Test existing headers
    assert get_header_value(headers, "Subject") == "Test Subject"
    assert get_header_value(headers, "From") == "sender@example.com"
    assert get_header_value(headers, "To") == "recipient@example.com"

    # Test non-existent header
    assert get_header_value(headers, "Date") is None

    # Test empty headers
    assert get_header_value([], "Subject") is None

    # Test None headers
    assert get_header_value(None, "Subject") is None


def test_get_body_parts():
    """Test extraction of body parts from email messages."""
    # Test plain text body
    message = {
        "payload": {
            "mimeType": "text/plain",
            "body": {
                "data": "SGVsbG8gV29ybGQ="  # Base64 encoded "Hello World"
            },
        }
    }
    text, html = get_body_parts(message)
    assert text == "SGVsbG8gV29ybGQ="
    assert html == ""

    # Test HTML body
    message = {
        "payload": {
            "mimeType": "text/html",
            "body": {
                "data": "PGgxPkhlbGxvPC9oMT4="  # Base64 encoded "<h1>Hello</h1>"
            },
        }
    }
    text, html = get_body_parts(message)
    assert text == ""
    assert html == "PGgxPkhlbGxvPC9oMT4="

    # Test nested parts
    message = {
        "payload": {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": "SGVsbG8gV29ybGQ="},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": "PGgxPkhlbGxvPC9oMT4="},
                },
            ]
        }
    }
    text, html = get_body_parts(message)
    assert text == "SGVsbG8gV29ybGQ="
    assert html == "PGgxPkhlbGxvPC9oMT4="

    # Test empty message
    text, html = get_body_parts({})
    assert text == ""
    assert html == ""

    # Test None message
    text, html = get_body_parts(None)
    assert text == ""
    assert html == ""


def test_handler_success():
    """Test successful email fetching."""
    mock_list_response = {
        "messages": [
            {"id": "msg_1", "threadId": "thread_1"},
            {"id": "msg_2", "threadId": "thread_2"},
        ]
    }

    mock_message_response = {
        "id": "msg_1",
        "threadId": "thread_1",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Email"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
            ],
            "body": {"data": "SGVsbG8gV29ybGQ="},
        },
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.side_effect = [
            mock_list_response,
            mock_message_response,
            mock_message_response,
        ]
        mock_get.return_value.status_code = 200

        pd = MockPD(gmail_token="access_token")
        result = handler(pd)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["subject"] == "Test Email"
        assert "message_id" in result[0]
        assert "url" in result[0]


def test_handler_no_emails():
    """Test handler when no emails are found."""
    mock_list_response = {"messages": []}

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_list_response
        mock_get.return_value.status_code = 200

        pd = MockPD(gmail_token="access_token")
        result = handler(pd)
        assert isinstance(result, list)
        assert result == []


def test_handler_missing_auth():
    """Test handler with missing authentication."""
    pd = MockPD(gmail_token=None)
    result = handler(pd)
    assert result == []


def test_handler_api_error():
    """Test handler with API error."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("API Error")

        pd = MockPD(gmail_token="access_token")
        result = handler(pd)
        assert result == []


def test_handler_pagination():
    """Test handler with paginated results."""
    mock_list_response_1 = {
        "messages": [
            {"id": "msg_1", "threadId": "thread_1"},
            {"id": "msg_2", "threadId": "thread_2"},
        ],
        "nextPageToken": "next_page",
    }

    mock_list_response_2 = {
        "messages": [{"id": "msg_3", "threadId": "thread_3"}]
    }

    mock_message_response = {
        "id": "msg_1",
        "threadId": "thread_1",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Email"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com"},
            ],
            "body": {"data": "SGVsbG8gV29ybGQ="},
        },
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.side_effect = [
            mock_list_response_1,
            mock_message_response,
            mock_message_response,
            mock_list_response_2,
            mock_message_response,
        ]
        mock_get.return_value.status_code = 200

        pd = MockPD(gmail_token="access_token")
        result = handler(pd)
        assert isinstance(result, list)
        assert len(result) == 2
        assert all("message_id" in email for email in result)
        assert all("url" in email for email in result)
