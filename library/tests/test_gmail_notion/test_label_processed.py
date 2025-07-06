"""
Tests for the Gmail Labeler for processed emails.

This module contains tests for the Gmail Labeler functionality,
including label ID retrieval and message labeling.
"""

import unittest.mock
from unittest.mock import patch

import pytest
import requests
from requests.exceptions import HTTPError

from src.integrations.gmail_notion.label_processed import get_label_id, handler


class MockPD:
    """Mock Pipedream context for testing."""

    def __init__(self, gmail_token=None, successful_mappings=None):
        """Initialize mock Pipedream context.

        Args:
            gmail_token (str, optional): Gmail OAuth token. Defaults to None.
            successful_mappings (list, optional): List of successful mappings.
                Defaults to None.
        """
        self.inputs = (
            {"gmail": {"$auth": {"oauth_access_token": gmail_token}}}
            if gmail_token
            else {}
        )
        self.steps = (
            {
                "notion": {
                    "$return_value": {
                        "successful_mappings": successful_mappings
                    }
                }
            }
            if successful_mappings is not None
            else {}
        )


def test_get_label_id_success():
    """Test successful label ID retrieval."""
    mock_response = {
        "labels": [
            {"id": "Label_1", "name": "Processed"},
            {"id": "Label_2", "name": "Other"},
        ]
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200

        label_id = get_label_id(
            {"Authorization": "Bearer token"},
            "Processed"
        )
        assert label_id == "Label_1"


def test_get_label_id_not_found():
    """Test label ID retrieval when label doesn't exist."""
    mock_response = {"labels": [{"id": "Label_2", "name": "Other"}]}

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200

        label_id = get_label_id(
            {"Authorization": "Bearer token"},
            "Processed"
        )
        assert label_id is None


def test_get_label_id_api_error():
    """Test label ID retrieval with API error."""
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 500
        mock_get.return_value.json.return_value = {"error": "Server error"}

        label_id = get_label_id(
            {"Authorization": "Bearer token"},
            "Processed"
        )
        assert label_id is None


def test_handler_success():
    """Test successful message labeling."""
    mock_label_response = {
        "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
    }
    mock_modify_response = {"id": "msg_123", "labelIds": ["Label_1"]}

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.json.return_value = mock_label_response
        mock_get.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_modify_response
        mock_post.return_value.status_code = 200

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[{"gmail_message_id": "msg_123"}],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert "msg_123" in result["successfully_labeled_ids"]
        assert result["labeled_messages"] == 1
        assert "errors" in result
        assert len(result["errors"]) == 0


def test_handler_missing_auth():
    """Test handler with missing authentication."""
    pd = MockPD(
        gmail_token=None,
        successful_mappings=[{"gmail_message_id": "msg_123"}]
    )
    with pytest.raises(Exception) as excinfo:
        handler(pd)
    assert "Gmail account not connected" in str(excinfo.value)


def test_handler_label_not_found():
    """Test handler when label is not found."""
    mock_response = {"labels": [{"id": "Label_2", "name": "Other"}]}

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_response
        mock_get.return_value.status_code = 200

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[{"gmail_message_id": "msg_123"}],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert result["error"].startswith("Could not find Label ID")
        assert result["labeled_messages"] == 0
        assert "successfully_labeled_ids" in result
        assert "errors" in result


def test_handler_api_error():
    """Test handler with API error during message modification."""
    mock_label_response = {
        "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
    }

    def raise_http_error(*args, **kwargs):
        response = unittest.mock.Mock()
        response.status_code = 500
        response.json.return_value = {"error": "Server error"}
        raise HTTPError(response=response)

    with patch("requests.get") as mock_get, patch(
        "requests.post",
        side_effect=raise_http_error
    ):
        mock_get.return_value.json.return_value = mock_label_response
        mock_get.return_value.status_code = 200

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[{"gmail_message_id": "msg_123"}],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["gmail_message_id"] == "msg_123"
        assert result["labeled_messages"] == 0
        assert "successfully_labeled_ids" in result


def test_handler_http_errors():
    """Test handler with various HTTP error responses."""
    mock_label_response = {
        "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
    }

    def make_http_error(status_code, error_msg):
        def raise_http_error(*args, **kwargs):
            response = unittest.mock.Mock()
            response.status_code = status_code
            response.json.return_value = {"error": error_msg}
            raise HTTPError(response=response)
        return raise_http_error

    error_cases = [
        (403, "Forbidden"),
        (400, "Bad Request"),
        (404, "Not Found")
    ]

    for status_code, error_msg in error_cases:
        with patch("requests.get") as mock_get, patch(
            "requests.post",
            side_effect=make_http_error(status_code, error_msg)
        ):
            mock_get.return_value.json.return_value = mock_label_response
            mock_get.return_value.status_code = 200

            pd = MockPD(
                gmail_token="access_token",
                successful_mappings=[{"gmail_message_id": "msg_123"}],
            )
            result = handler(pd)
            assert result["status"] == "Completed"
            assert len(result["errors"]) == 1
            assert result["errors"][0]["gmail_message_id"] == "msg_123"
            assert result["labeled_messages"] == 0
            assert "successfully_labeled_ids" in result


def test_handler_invalid_data():
    """Test handler with invalid data from previous step."""
    class BadPD:
        def __init__(self):
            self.inputs = {
                "gmail": {"$auth": {"oauth_access_token": "access_token"}}
            }
            self.steps = {"notion": {"$return_value": "invalid"}}

    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {
            "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
        }
        mock_get.return_value.status_code = 200
        pd = BadPD()
        result = handler(pd)
        assert result["status"] == "Completed"
        assert result["error"] == "Invalid data format from previous step."
        assert result["labeled_messages"] == 0
        assert "successfully_labeled_ids" in result
        assert "errors" in result


def test_handler_request_exception():
    """Test handler with request exception."""
    mock_label_response = {
        "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
    }

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.json.return_value = mock_label_response
        mock_get.return_value.status_code = 200
        mock_post.side_effect = requests.RequestException("Connection error")

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[{"gmail_message_id": "msg_123"}],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["gmail_message_id"] == "msg_123"
        assert result["labeled_messages"] == 0
        assert "successfully_labeled_ids" in result


def test_handler_invalid_message_id():
    """Test handler with invalid message ID."""
    mock_label_response = {
        "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
    }

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.json.return_value = mock_label_response
        mock_get.return_value.status_code = 200
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "msg_123"}

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[{"gmail_message_id": None}],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert result["labeled_messages"] == 0
        assert "successfully_labeled_ids" in result


def test_handler_missing_previous_step():
    """Test handler with missing previous step data."""
    pd = MockPD(gmail_token="access_token")
    result = handler(pd)
    assert result["status"] == "Completed"
    assert result["error"] == "No data from previous step."
    assert result["labeled_messages"] == 0
    assert "successfully_labeled_ids" in result
    assert "errors" in result


def test_handler_empty_mappings():
    """Test handler with empty successful mappings."""
    pd = MockPD(
        gmail_token="access_token",
        successful_mappings=[]
    )
    result = handler(pd)
    assert result["status"] == "Completed"
    assert result["labeled_messages"] == 0
    assert "successfully_labeled_ids" in result
    assert "errors" in result


def test_handler_invalid_mappings_type():
    """Test handler with invalid mappings type."""
    pd = MockPD(
        gmail_token="access_token",
        successful_mappings="invalid"
    )
    result = handler(pd)
    assert result["status"] == "Completed"
    assert result["error"] == "Invalid data format from previous step."
    assert result["labeled_messages"] == 0
    assert "successfully_labeled_ids" in result
    assert "errors" in result


def test_handler_mixed_valid_invalid_mappings():
    """Test handler with mix of valid and invalid mappings."""
    mock_label_response = {
        "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
    }
    mock_modify_response = {"id": "msg_123", "labelIds": ["Label_1"]}

    with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
        mock_get.return_value.json.return_value = mock_label_response
        mock_get.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_modify_response
        mock_post.return_value.status_code = 200

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[
                {"gmail_message_id": "msg_123"},
                {"gmail_message_id": None},
                {"invalid": "data"}
            ],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert "msg_123" in result["successfully_labeled_ids"]
        assert result["labeled_messages"] == 1
        assert len(result["errors"]) == 2


def test_handler_http_error_without_response():
    """Test handler with HTTP error without response."""
    def raise_http_error(*args, **kwargs):
        raise HTTPError("No response")

    with patch("requests.get") as mock_get, patch(
        "requests.post",
        side_effect=raise_http_error
    ):
        mock_get.return_value.json.return_value = {
            "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
        }
        mock_get.return_value.status_code = 200

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[{"gmail_message_id": "msg_123"}],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["gmail_message_id"] == "msg_123"
        assert result["labeled_messages"] == 0


def test_handler_http_error_with_invalid_error_format():
    """Test handler with HTTP error with invalid error format."""
    def raise_http_error(*args, **kwargs):
        response = unittest.mock.Mock()
        response.status_code = 500
        response.json.side_effect = ValueError("Invalid JSON")
        raise HTTPError(response=response)

    with patch("requests.get") as mock_get, patch(
        "requests.post",
        side_effect=raise_http_error
    ):
        mock_get.return_value.json.return_value = {
            "labels": [{"id": "Label_1", "name": "notiontaskcreated"}]
        }
        mock_get.return_value.status_code = 200

        pd = MockPD(
            gmail_token="access_token",
            successful_mappings=[{"gmail_message_id": "msg_123"}],
        )
        result = handler(pd)
        assert result["status"] == "Completed"
        assert len(result["errors"]) == 1
        assert result["errors"][0]["gmail_message_id"] == "msg_123"
        assert result["labeled_messages"] == 0
