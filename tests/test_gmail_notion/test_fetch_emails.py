"""
Tests for Gmail Email Fetcher

This module contains tests for the handler that fetches emails from Gmail
and prepares them for processing by the Notion integration.
"""

import base64
from unittest.mock import Mock, patch

import pytest
import requests

from src.integrations.gmail_notion.fetch_emails import (
    get_body_parts,
    get_header_value,
    handler,
)


class MockPipedream:
    """Mock Pipedream context object for testing."""

    def __init__(self, steps=None):
        self.steps = steps or {}


def test_get_header_value():
    """Test extracting header values from email headers."""
    headers = [
        {"name": "Subject", "value": "Test Subject"},
        {"name": "From", "value": "sender@example.com"},
        {"name": "To", "value": "recipient@example.com"},
    ]
    
    assert get_header_value(headers, "Subject") == "Test Subject"
    assert get_header_value(headers, "From") == "sender@example.com"
    assert get_header_value(headers, "To") == "recipient@example.com"
    assert get_header_value(headers, "Date") is None


def test_get_body_parts():
    """Test extracting body parts from email message."""
    # Test plain text
    text_content = "Hello, World!"
    text_encoded = base64.urlsafe_b64encode(text_content.encode()).decode()
    
    parts = [
        {
            "mimeType": "text/plain",
            "body": {"data": text_encoded},
        }
    ]
    
    result = get_body_parts(parts)
    assert result["text"] == text_content
    assert result["html"] == ""
    
    # Test HTML
    html_content = "<p>Hello, World!</p>"
    html_encoded = base64.urlsafe_b64encode(html_content.encode()).decode()
    
    parts = [
        {
            "mimeType": "text/html",
            "body": {"data": html_encoded},
        }
    ]
    
    result = get_body_parts(parts)
    assert result["text"] == ""
    assert result["html"] == html_content
    
    # Test nested parts
    parts = [
        {
            "mimeType": "multipart/alternative",
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": text_encoded},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": html_encoded},
                },
            ],
        }
    ]
    
    result = get_body_parts(parts)
    assert result["text"] == text_content
    assert result["html"] == html_content


@patch("requests.get")
def test_handler_success(mock_get):
    """Test successful email fetching."""
    # Mock message list response
    mock_list_response = Mock()
    mock_list_response.json.return_value = {
        "messages": [{"id": "msg-123"}, {"id": "msg-456"}],
    }
    
    # Mock individual message responses
    mock_msg_responses = []
    for i in range(2):
        mock_msg = Mock()
        mock_msg.json.return_value = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": f"Test Email {i+1}"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "2024-03-20"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Test content").decode()},
            }
        }
        mock_msg_responses.append(mock_msg)
    
    mock_get.side_effect = [mock_list_response] + mock_msg_responses
    
    pd = MockPipedream(steps={"oauth": {"access_token": "test-token"}})
    result = handler(pd)
    
    assert len(result) == 2
    assert result[0]["subject"] == "Test Email 1"
    assert result[1]["subject"] == "Test Email 2"
    assert all("id" in email for email in result)
    assert all("url" in email for email in result)


@patch("requests.get")
def test_handler_no_emails(mock_get):
    """Test handling of no emails found."""
    mock_response = Mock()
    mock_response.json.return_value = {"messages": []}
    mock_get.return_value = mock_response
    
    pd = MockPipedream(steps={"oauth": {"access_token": "test-token"}})
    result = handler(pd)
    
    assert result == []


def test_handler_missing_auth():
    """Test handling of missing authentication."""
    pd = MockPipedream(steps={})  # Missing oauth token
    result = handler(pd)
    
    assert result == []


@patch("requests.get")
def test_handler_api_error(mock_get):
    """Test handling of API errors."""
    mock_get.side_effect = requests.exceptions.RequestException("API Error")
    
    pd = MockPipedream(steps={"oauth": {"access_token": "test-token"}})
    result = handler(pd)
    
    assert result == []


@patch("requests.get")
def test_handler_pagination(mock_get):
    """Test handling of paginated results."""
    # Mock first page response
    mock_page1 = Mock()
    mock_page1.json.return_value = {
        "messages": [{"id": "msg-1"}, {"id": "msg-2"}],
        "nextPageToken": "token-123",
    }
    
    # Mock second page response
    mock_page2 = Mock()
    mock_page2.json.return_value = {
        "messages": [{"id": "msg-3"}],
    }
    
    # Mock message detail responses
    mock_msg_responses = []
    for i in range(3):
        mock_msg = Mock()
        mock_msg.json.return_value = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": f"Test Email {i+1}"},
                ],
                "body": {"data": base64.urlsafe_b64encode(b"Test content").decode()},
            }
        }
        mock_msg_responses.append(mock_msg)
    
    mock_get.side_effect = [mock_page1, mock_page2] + mock_msg_responses
    
    pd = MockPipedream(steps={"oauth": {"access_token": "test-token"}})
    result = handler(pd)
    
    assert len(result) == 3
    assert all(f"Test Email {i+1}" in [email["subject"] for email in result] for i in range(3)) 