"""
Tests for fetch_gmail_emails.py Pipedream step.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from steps.fetch_gmail_emails import handler, get_header_value, get_body_parts


class TestGetHeaderValue:
    """Tests for the get_header_value helper function."""

    def test_finds_header_by_name(self):
        headers = [
            {"name": "Subject", "value": "Test Subject"},
            {"name": "From", "value": "sender@example.com"}
        ]
        assert get_header_value(headers, "Subject") == "Test Subject"

    def test_case_insensitive_search(self):
        headers = [{"name": "Subject", "value": "Test"}]
        assert get_header_value(headers, "subject") == "Test"
        assert get_header_value(headers, "SUBJECT") == "Test"

    def test_returns_empty_string_when_not_found(self):
        headers = [{"name": "Subject", "value": "Test"}]
        assert get_header_value(headers, "From") == ""

    def test_handles_empty_headers(self):
        assert get_header_value([], "Subject") == ""


class TestGetBodyParts:
    """Tests for the get_body_parts helper function."""

    def test_extracts_plain_text(self):
        import base64
        text = "Hello, World!"
        encoded = base64.urlsafe_b64encode(text.encode()).decode()
        payload = {
            "mimeType": "text/plain",
            "body": {"data": encoded}
        }
        plain, html = get_body_parts(payload)
        assert plain == text
        assert html is None

    def test_extracts_html(self):
        import base64
        html_content = "<p>Hello, World!</p>"
        encoded = base64.urlsafe_b64encode(html_content.encode()).decode()
        payload = {
            "mimeType": "text/html",
            "body": {"data": encoded}
        }
        plain, html = get_body_parts(payload)
        assert plain is None
        assert html == html_content

    def test_handles_multipart(self):
        import base64
        text = "Plain text"
        html_content = "<p>HTML</p>"
        text_encoded = base64.urlsafe_b64encode(text.encode()).decode()
        html_encoded = base64.urlsafe_b64encode(html_content.encode()).decode()

        payload = {
            "mimeType": "multipart/alternative",
            "parts": [
                {"mimeType": "text/plain", "body": {"data": text_encoded}},
                {"mimeType": "text/html", "body": {"data": html_encoded}}
            ]
        }
        plain, html = get_body_parts(payload)
        assert plain == text
        assert html == html_content

    def test_handles_empty_payload(self):
        plain, html = get_body_parts(None)
        assert plain is None
        assert html is None


class TestHandler:
    """Tests for the main handler function."""

    def test_raises_exception_without_auth(self, mock_pd):
        """Handler should raise exception if Gmail not connected."""
        with pytest.raises(Exception) as exc_info:
            handler(mock_pd)
        assert "Gmail account not connected" in str(exc_info.value)

    @patch('steps.fetch_gmail_emails.requests.get')
    def test_uses_correct_query(self, mock_get, mock_pd, gmail_auth):
        """Handler should construct correct Gmail query."""
        mock_pd.inputs = gmail_auth
        mock_pd.inputs["required_label"] = "notion"
        mock_pd.inputs["excluded_label"] = "processed"

        # Mock empty response
        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": []}
        mock_get.return_value = mock_response

        handler(mock_pd)

        # Check the query parameter
        call_args = mock_get.call_args
        assert "q" in call_args.kwargs.get("params", {}) or "q" in call_args[1].get("params", {})

    @patch('steps.fetch_gmail_emails.requests.get')
    def test_respects_max_results(self, mock_get, mock_pd, gmail_auth):
        """Handler should limit results to max_results."""
        mock_pd.inputs = gmail_auth
        mock_pd.inputs["max_results"] = 2

        # Mock response with more messages than max_results
        mock_list_response = MagicMock()
        mock_list_response.json.return_value = {
            "messages": [
                {"id": "msg1"},
                {"id": "msg2"},
                {"id": "msg3"}
            ]
        }

        mock_detail_response = MagicMock()
        mock_detail_response.json.return_value = {
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test"}
                ]
            }
        }

        mock_get.side_effect = [mock_list_response, mock_detail_response, mock_detail_response]

        result = handler(mock_pd)

        # Should only return 2 results
        assert len(result) == 2

    @patch('steps.fetch_gmail_emails.requests.get')
    def test_handles_empty_results(self, mock_get, mock_pd, gmail_auth):
        """Handler should return empty list when no messages match."""
        mock_pd.inputs = gmail_auth

        mock_response = MagicMock()
        mock_response.json.return_value = {"messages": []}
        mock_get.return_value = mock_response

        result = handler(mock_pd)
        assert result == []

    @patch('steps.fetch_gmail_emails.requests.get')
    def test_handles_fetch_failure(self, mock_get, mock_pd, gmail_auth):
        """Handler should continue processing when individual fetch fails."""
        mock_pd.inputs = gmail_auth

        mock_list_response = MagicMock()
        mock_list_response.json.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }

        mock_detail_response = MagicMock()
        mock_detail_response.json.return_value = {
            "payload": {"headers": [{"name": "Subject", "value": "Test"}]}
        }

        import requests
        # First call succeeds (list), second fails (detail for msg1), third succeeds (detail for msg2)
        mock_get.side_effect = [
            mock_list_response,
            requests.exceptions.RequestException("API Error"),
            mock_detail_response
        ]

        result = handler(mock_pd)

        # Should have 1 successful result despite 1 failure
        assert len(result) == 1
