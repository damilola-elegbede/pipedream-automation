"""
Tests for Gmail Labeler for Processed Emails

This module contains tests for the handler that adds labels to Gmail messages
that have been processed by the Notion integration.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from src.integrations.gmail_notion.label_processed import get_label_id, handler


class MockPipedream:
    """Mock Pipedream context object for testing."""

    def __init__(self, steps=None, inputs=None):
        self.steps = steps or {}
        self.inputs = inputs or {}


@patch("requests.get")
def test_get_label_id_success(mock_get):
    """Test successful label ID retrieval."""
    mock_response = Mock()
    mock_response.json.return_value = {
        "labels": [
            {"name": "notiontaskcreated", "id": "label-123"},
            {"name": "other-label", "id": "label-456"},
        ]
    }
    mock_get.return_value = mock_response
    
    result = get_label_id({"Authorization": "Bearer token"}, "notiontaskcreated")
    
    assert result == "label-123"
    mock_get.assert_called_once()


@patch("requests.get")
def test_get_label_id_not_found(mock_get):
    """Test label ID retrieval when label doesn't exist."""
    mock_response = Mock()
    mock_response.json.return_value = {"labels": []}
    mock_get.return_value = mock_response
    
    result = get_label_id({"Authorization": "Bearer token"}, "notiontaskcreated")
    
    assert result is None


@patch("requests.get")
def test_get_label_id_api_error(mock_get):
    """Test label ID retrieval with API error."""
    mock_get.side_effect = requests.exceptions.RequestException("API Error")
    
    result = get_label_id({"Authorization": "Bearer token"}, "notiontaskcreated")
    
    assert result is None


@patch("requests.post")
@patch("requests.get")
def test_handler_success(mock_get, mock_post):
    """Test successful message labeling."""
    # Mock label ID retrieval
    mock_label_response = Mock()
    mock_label_response.json.return_value = {
        "labels": [{"name": "notiontaskcreated", "id": "label-123"}]
    }
    mock_get.return_value = mock_label_response
    
    # Mock message modification
    mock_post.return_value = Mock()
    
    pd = MockPipedream(
        steps={
            "notion": {
                "$return_value": {
                    "successful_mappings": [
                        {"gmail_message_id": "msg-123"},
                        {"gmail_message_id": "msg-456"},
                    ]
                }
            }
        },
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    
    result = handler(pd)
    
    assert result["status"] == "Completed"
    assert len(result["successfully_labeled_ids"]) == 2
    assert "msg-123" in result["successfully_labeled_ids"]
    assert "msg-456" in result["successfully_labeled_ids"]


@patch("requests.get")
def test_handler_missing_auth(mock_get):
    """Test handling of missing authentication."""
    pd = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": []}}},
        inputs={},  # Missing gmail auth
    )
    
    result = handler(pd)
    assert "error" in result
    assert (
        "Could not find Label ID" in result["error"]
        or "Gmail account not connected" in result["error"]
    )


@patch("requests.get")
def test_handler_label_not_found(mock_get):
    """Test handling of missing label."""
    mock_response = Mock()
    mock_response.json.return_value = {"labels": []}
    mock_get.return_value = mock_response
    
    pd = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": []}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    
    result = handler(pd)
    
    assert "error" in result
    assert "Could not find Label ID" in result["error"]


@patch("requests.post")
@patch("requests.get")
def test_handler_api_error(mock_get, mock_post):
    """Test handling of API errors during message modification."""
    # Mock label ID retrieval
    mock_label_response = Mock()
    mock_label_response.json.return_value = {
        "labels": [{"name": "notiontaskcreated", "id": "label-123"}]
    }
    mock_get.return_value = mock_label_response
    
    # Mock message modification error
    mock_error_response = Mock()
    mock_error_response.status_code = 500
    mock_error_response.json.return_value = {"error": {"message": "API Error"}}
    mock_post.side_effect = requests.exceptions.HTTPError(response=mock_error_response)
    
    pd = MockPipedream(
        steps={
            "notion": {
                "$return_value": {
                    "successful_mappings": [{"gmail_message_id": "msg-123"}]
                }
            }
        },
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    
    result = handler(pd)
    
    assert result["status"] == "Completed"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["gmail_message_id"] == "msg-123"


def test_handler_invalid_data():
    """Test handling of invalid data from previous step."""
    pd = MockPipedream(
        steps={"notion": {"$return_value": "invalid data"}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    
    result = handler(pd)
    assert "error" in result
    assert (
        "Invalid data format" in result["error"]
        or "Could not find Label ID" in result["error"]
    )


@patch("requests.post")
@patch("requests.get")
def test_handler_http_error_403(mock_get, mock_post):
    """Test handling of HTTP 403 error during message modification."""
    mock_label_response = Mock()
    mock_label_response.json.return_value = {
        "labels": [{"name": "notiontaskcreated", "id": "label-123"}]
    }
    mock_get.return_value = mock_label_response
    
    mock_error_response = Mock()
    mock_error_response.status_code = 403
    mock_error_response.json.return_value = {"error": {"message": "Forbidden"}}
    mock_post.side_effect = requests.exceptions.HTTPError(response=mock_error_response)
    
    pd = MockPipedream(
        steps={
            "notion": {
                "$return_value": {
                    "successful_mappings": [{"gmail_message_id": "msg-123"}]
                }
            }
        },
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result = handler(pd)
    assert result["status"] == "Completed"
    assert result["errors"][0]["status_code"] == 403
    assert "Forbidden" in result["errors"][0]["error"]


@patch("requests.post")
@patch("requests.get")
def test_handler_http_error_400_and_404(mock_get, mock_post):
    """Test handling of HTTP 400 and 404 errors during message modification."""
    mock_label_response = Mock()
    mock_label_response.json.return_value = {
        "labels": [{"name": "notiontaskcreated", "id": "label-123"}]
    }
    mock_get.return_value = mock_label_response
    
    # 400 Bad Request
    mock_error_response_400 = Mock()
    mock_error_response_400.status_code = 400
    mock_error_response_400.json.return_value = {"error": {"message": "Bad Request"}}
    # 404 Not Found
    mock_error_response_404 = Mock()
    mock_error_response_404.status_code = 404
    mock_error_response_404.json.return_value = {"error": {"message": "Not Found"}}
    
    # Test 400
    mock_post.side_effect = requests.exceptions.HTTPError(response=mock_error_response_400)
    pd_400 = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": [{"gmail_message_id": "msg-400"}]}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result_400 = handler(pd_400)
    assert result_400["errors"][0]["status_code"] == 400
    assert "Bad Request" in result_400["errors"][0]["error"]
    
    # Test 404
    mock_post.side_effect = requests.exceptions.HTTPError(response=mock_error_response_404)
    pd_404 = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": [{"gmail_message_id": "msg-404"}]}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result_404 = handler(pd_404)
    assert result_404["errors"][0]["status_code"] == 404
    assert "Not Found" in result_404["errors"][0]["error"]


@patch("requests.post")
@patch("requests.get")
def test_handler_request_exception(mock_get, mock_post):
    """Test handling of RequestException during message modification."""
    mock_label_response = Mock()
    mock_label_response.json.return_value = {
        "labels": [{"name": "notiontaskcreated", "id": "label-123"}]
    }
    mock_get.return_value = mock_label_response
    mock_post.side_effect = requests.exceptions.RequestException("Network error")
    pd = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": [{"gmail_message_id": "msg-req"}]}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result = handler(pd)
    assert result["errors"][0]["error"].startswith("Request failed:")


@patch("requests.post")
@patch("requests.get")
def test_handler_unexpected_exception(mock_get, mock_post):
    """Test handling of unexpected Exception during message modification."""
    mock_label_response = Mock()
    mock_label_response.json.return_value = {
        "labels": [{"name": "notiontaskcreated", "id": "label-123"}]
    }
    mock_get.return_value = mock_label_response
    mock_post.side_effect = Exception("Unexpected!")
    pd = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": [{"gmail_message_id": "msg-x"}]}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result = handler(pd)
    assert result["errors"][0]["error"].startswith("Unexpected error:")


@patch("src.integrations.gmail_notion.label_processed.get_label_id", return_value="label-123")
def test_handler_no_valid_message_ids(mock_label_id):
    """Test handling of mappings with no valid gmail_message_id."""
    pd = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": [{"not_gmail_id": "x"}]}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result = handler(pd)
    assert result["status"] == "No valid message IDs"
    assert result["labeled_messages"] == 0


@patch("src.integrations.gmail_notion.label_processed.get_label_id", return_value="label-123")
def test_handler_no_data_received(mock_label_id):
    """Test handling of empty successful_mappings list."""
    pd = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": []}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result = handler(pd)
    assert result["status"] == "No data received"
    assert result["labeled_messages"] == 0


@patch("src.integrations.gmail_notion.label_processed.get_label_id", return_value="label-123")
def test_handler_non_list_successful_mappings(mock_label_id):
    """Test handling of non-list successful_mappings."""
    pd = MockPipedream(
        steps={"notion": {"$return_value": {"successful_mappings": "notalist"}}},
        inputs={"gmail": {"$auth": {"oauth_access_token": "test-token"}}},
    )
    result = handler(pd)
    assert result["error"] == "Invalid data format for successful_mappings." 