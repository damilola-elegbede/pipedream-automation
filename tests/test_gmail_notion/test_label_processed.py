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