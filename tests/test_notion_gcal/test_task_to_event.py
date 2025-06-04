"""
Tests for the Notion Task to Google Calendar Event integration.

This module contains tests for converting Notion tasks to Google Calendar events,
including task parsing, date handling, and event creation functionality.
"""

import unittest.mock
import requests

from src.integrations.notion_gcal.task_to_event import handler
from src.utils.common_utils import safe_get


class MockPipedream:
    def __init__(self, steps):
        self.steps = steps
        self.flow = MockFlow()


class MockFlow:
    def exit(self, message):
        raise SystemExit(message)


def test_safe_get():
    """Test the safe_get utility function."""
    # Test dictionary access
    test_dict = {"a": {"b": {"c": 1}}}
    assert safe_get(test_dict, ["a", "b", "c"]) == 1
    assert safe_get(test_dict, ["a", "b", "d"], default=0) == 0

    # Test list access
    test_list = [1, [2, 3], 4]
    assert safe_get(test_list, [1, 0]) == 2
    assert safe_get(test_list, [1, 5], default=0) == 0

    # Test invalid access
    assert safe_get(test_dict, ["a", "b", "c", "d"], default=0) == 0
    assert safe_get(test_list, [5], default=0) == 0


@unittest.mock.patch("requests.post")
def test_handler_valid_task(mock_post):
    """Test handler with valid task data."""
    # Mock Google Calendar API response
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "event_123",
        "htmlLink": "https://calendar.google.com/event/123",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Create test task
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
            "Description": {"rich_text": [{"text": {"content": "Test Description"}}]},
            "Location": {"rich_text": [{"text": {"content": "Test Location"}}]},
        },
        "url": "https://notion.so/task_123",
    }

    # Create mock Pipedream context
    pd = {
        "task": task,
        "calendar_auth": "test_calendar_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" in result
    assert "error" not in result
    assert result["success"]["event_id"] == "event_123"
    assert result["success"]["event_url"] == "https://calendar.google.com/event/123"


def test_handler_missing_due_date():
    """Test handler with missing due date."""
    # Create test task without due date
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Description": {"rich_text": [{"text": {"content": "Test Description"}}]},
            "Location": {"rich_text": [{"text": {"content": "Test Location"}}]},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_calendar_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "due date" in result["error"].lower()


@unittest.mock.patch("requests.post")
def test_handler_existing_event(mock_post):
    """Test handler with existing event."""
    # Mock Google Calendar API response for existing event
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "event_123",
        "htmlLink": "https://calendar.google.com/event/123",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Create test task with existing event ID
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
            "Description": {"rich_text": [{"text": {"content": "Test Description"}}]},
            "Location": {"rich_text": [{"text": {"content": "Test Location"}}]},
            "Event ID": {"rich_text": [{"text": {"content": "event_123"}}]},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_calendar_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" in result
    assert "error" not in result
    assert result["success"]["event_id"] == "event_123"


def test_handler_untitled_task():
    """Test handler with untitled task."""
    # Create test task without title
    task = {
        "properties": {
            "Due date": {"date": {"start": "2024-01-01"}},
            "Description": {"rich_text": [{"text": {"content": "Test Description"}}]},
            "Location": {"rich_text": [{"text": {"content": "Test Location"}}]},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_calendar_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "title" in result["error"].lower()


@unittest.mock.patch("requests.post")
def test_handler_api_error(mock_post):
    """Test handler with API error."""
    # Mock Google Calendar API error
    mock_post.side_effect = requests.exceptions.RequestException("API Error")

    # Create test task
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
            "Description": {"rich_text": [{"text": {"content": "Test Description"}}]},
            "Location": {"rich_text": [{"text": {"content": "Test Location"}}]},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_calendar_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "API Error" in result["error"]


@unittest.mock.patch("requests.post")
def test_handler_missing_auth(mock_post):
    """Test handler with missing authentication."""
    # Create test task
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
            "Description": {"rich_text": [{"text": {"content": "Test Description"}}]},
            "Location": {"rich_text": [{"text": {"content": "Test Location"}}]},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "authentication" in result["error"].lower()


@unittest.mock.patch("requests.post")
def test_handler_missing_calendar_id(mock_post):
    """Test handler with missing calendar ID."""
    # Create test task
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
            "Description": {"rich_text": [{"text": {"content": "Test Description"}}]},
            "Location": {"rich_text": [{"text": {"content": "Test Location"}}]},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_calendar_auth",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "calendar id" in result["error"].lower()


@unittest.mock.patch("requests.post")
def test_handler_401_error(mock_post):
    """Test handler with 401 authentication error."""
    mock_post.side_effect = requests.exceptions.RequestException("401 Unauthorized")

    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "invalid_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "Invalid calendar authentication" in result["error"]


@unittest.mock.patch("requests.post")
def test_handler_404_error(mock_post):
    """Test handler with 404 calendar not found error."""
    mock_post.side_effect = requests.exceptions.RequestException("404 Not Found")

    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "nonexistent",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "Calendar not found" in result["error"]


@unittest.mock.patch("requests.post")
def test_handler_empty_description_and_location(mock_post):
    """Test handler with empty description and location."""
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "event_123",
        "htmlLink": "https://calendar.google.com/event/123",
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
            "Description": {"rich_text": []},
            "Location": {"rich_text": []},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" in result
    assert "error" not in result
    assert result["success"]["event_id"] == "event_123"


@unittest.mock.patch("requests.post")
def test_handler_missing_task(mock_post):
    """Test handler with missing task data."""
    pd = {
        "calendar_auth": "test_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "No task data provided" in result["error"]


@unittest.mock.patch("requests.post")
def test_handler_generic_request_error(mock_post):
    """Test handler with generic request error."""
    mock_post.side_effect = requests.exceptions.RequestException("Connection error")

    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Test Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
        },
        "url": "https://notion.so/task_123",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "primary",
    }

    result = handler(pd)
    assert "success" not in result
    assert "error" in result
    assert "Connection error" in result["error"]


def test_handler_missing_task_properties():
    """Test handler with missing task properties."""
    pd = {
        "task": {"properties": {}},
        "calendar_auth": "test_auth",
        "calendar_id": "primary"
    }
    result = handler(pd)
    assert "error" in result
    assert result["error"] == "Task has no title"


@unittest.mock.patch("requests.post")
def test_handler_with_event_id_uses_update_url(mock_post):
    """Test handler updates existing event when event ID is present."""
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "event_456",
        "htmlLink": "https://calendar.google.com/event/456"
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Update Task"}}]},
            "Due date": {"date": {"start": "2024-02-01"}},
            "Event ID": {"rich_text": [{"text": {"content": "event_456"}}]},
        },
        "url": "https://notion.so/task_456",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "primary"
    }

    result = handler(pd)
    assert "success" in result
    assert result["success"]["event_id"] == "event_456"
    assert result["success"]["event_url"] == "https://calendar.google.com/event/456"


@unittest.mock.patch("requests.post")
def test_handler_empty_description_and_location_fields(mock_post):
    """Test handler with empty description and location fields."""
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "event_789",
        "htmlLink": "https://calendar.google.com/event/789"
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "No Desc/Loc"}}]},
            "Due date": {"date": {"start": "2024-03-01"}},
            "Description": {"rich_text": []},
            "Location": {"rich_text": []},
        },
        "url": "https://notion.so/task_789",
    }

    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "primary"
    }

    result = handler(pd)
    assert "success" in result
    assert result["success"]["event_id"] == "event_789"
    assert result["success"]["event_url"] == "https://calendar.google.com/event/789"


@unittest.mock.patch("requests.post")
def test_handler_malformed_properties(mock_post):
    """Test handler with malformed task properties."""
    task = {"properties": None, "url": "https://notion.so/task_999"}
    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "primary"
    }
    result = handler(pd)
    assert "error" in result
    assert result["error"] == "Task properties must be a dict"


@unittest.mock.patch("requests.post")
def test_handler_generic_request_exception(mock_post):
    """Test handler with generic request exception."""
    mock_post.side_effect = requests.exceptions.RequestException("Some generic error")
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Generic Error Task"}}]},
            "Due date": {"date": {"start": "2024-04-01"}},
        },
        "url": "https://notion.so/task_000",
    }
    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "primary"
    }
    result = handler(pd)
    assert "error" in result
    assert "Some generic error" in result["error"]


def test_handler_properties_not_dict():
    """Test handler with non-dict properties."""
    task = {"properties": "not_a_dict"}
    pd = {
        "task": task,
        "calendar_auth": "auth",
        "calendar_id": "primary"
    }
    result = handler(pd)
    assert "error" in result
    assert result["error"] == "Task properties must be a dict"


def test_handler_name_title_not_list():
    """Test handler with non-list name title."""
    task = {"properties": {"Name": {"title": "not_a_list"}}}
    pd = {
        "task": task,
        "calendar_auth": "auth",
        "calendar_id": "primary"
    }
    result = handler(pd)
    assert "error" in result
    assert "title" in result["error"].lower()


def test_handler_due_date_not_dict():
    """Test handler with non-dict due date."""
    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Task"}}]},
            "Due date": {"date": "not_a_dict"}
        }
    }
    pd = {
        "task": task,
        "calendar_auth": "auth",
        "calendar_id": "primary"
    }
    result = handler(pd)
    assert "error" in result
    assert "due date" in result["error"].lower()


@unittest.mock.patch("requests.post")
def test_handler_event_id_not_list(mock_post):
    """Test handler with non-list event ID."""
    mock_response = unittest.mock.Mock()
    mock_response.json.return_value = {
        "id": "event_000",
        "htmlLink": "https://calendar.google.com/event/000"
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    task = {
        "properties": {
            "Name": {"title": [{"text": {"content": "Task"}}]},
            "Due date": {"date": {"start": "2024-01-01"}},
            "Event ID": {"rich_text": "not_a_list"}
        }
    }
    pd = {
        "task": task,
        "calendar_auth": "test_auth",
        "calendar_id": "primary"
    }
    result = handler(pd)
    assert "success" in result
