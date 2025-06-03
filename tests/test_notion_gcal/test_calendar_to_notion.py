"""
Tests for Google Calendar to Notion Event Handler

This module contains tests for the handler that processes Google Calendar events
and extracts Notion page IDs from their location URLs.
"""

import pytest
from datetime import datetime, timedelta
from src.integrations.notion_gcal.calendar_to_notion import (
    safe_get,
    extract_notion_page_id,
    get_event_time,
    handler
)

class MockPipedream:
    """Mock Pipedream context object for testing."""
    def __init__(self, trigger_data=None):
        self.steps = {"trigger": {"event": trigger_data or {}}}
        self.flow = MockFlow()

class MockFlow:
    """Mock Flow object for testing exit conditions."""
    def __init__(self):
        self.exit_called = False
        self.exit_message = None

    def exit(self, message):
        self.exit_called = True
        self.exit_message = message

def test_safe_get():
    """Test the safe_get function for accessing nested data structures."""
    # Test dictionary access
    test_dict = {"a": {"b": {"c": 1}}}
    assert safe_get(test_dict, ["a", "b", "c"]) == 1
    assert safe_get(test_dict, "a") == {"b": {"c": 1}}
    assert safe_get(test_dict, ["a", "b", "d"], "default") == "default"
    assert safe_get(test_dict, ["x", "y"], "default") == "default"

    # Test list access
    test_list = [1, [2, 3], {"a": 4}]
    assert safe_get(test_list, [1, 1]) == 3
    assert safe_get(test_list, [2, "a"]) == 4
    assert safe_get(test_list, [0, 0], "default") == "default"

    # Test None and invalid access
    assert safe_get(None, ["a"], "default") == "default"
    assert safe_get({}, ["a", "b"], "default") == "default"
    assert safe_get([], [0], "default") == "default"

def test_extract_notion_page_id():
    """Test the extract_notion_page_id function."""
    # Valid Notion URLs
    assert extract_notion_page_id("https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef") == "1234567890abcdef1234567890abcdef"
    assert extract_notion_page_id("https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef?pvs=4") == "1234567890abcdef1234567890abcdef"

    # Invalid URLs
    assert extract_notion_page_id("https://www.notion.so/My-Page") is None
    assert extract_notion_page_id("https://example.com/page-123") is None
    assert extract_notion_page_id("") is None
    assert extract_notion_page_id(None) is None

def test_get_event_time():
    """Test the get_event_time function."""
    # Test dateTime format
    time_obj = {"dateTime": "2024-03-20T10:00:00Z"}
    assert get_event_time(time_obj) == "2024-03-20T10:00:00Z"

    # Test date format (all-day event)
    time_obj = {"date": "2024-03-20"}
    assert get_event_time(time_obj) == "2024-03-20"

    # Test missing time
    time_obj = {}
    assert get_event_time(time_obj) == "{}"

    # Test invalid object
    assert get_event_time(None) is None

def test_handler_valid_event():
    """Test handler with valid Notion-linked event data."""
    # Create test data
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    day_after = (datetime.now() + timedelta(days=2)).isoformat()
    
    trigger_data = {
        "summary": "Test Event",
        "location": "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef",
        "start": {"dateTime": tomorrow},
        "end": {"dateTime": day_after}
    }

    pd = MockPipedream(trigger_data)
    result = handler(pd)

    # Verify result structure
    assert result["Subject"] == "Test Event"
    assert result["Start"] == tomorrow
    assert result["End"] == day_after
    assert result["Id"] == "1234567890abcdef1234567890abcdef"

def test_handler_non_notion_event():
    """Test handler with non-Notion event."""
    trigger_data = {
        "summary": "Test Event",
        "location": "https://example.com/meeting",
        "start": {"dateTime": "2024-03-20T10:00:00Z"},
        "end": {"dateTime": "2024-03-20T11:00:00Z"}
    }

    pd = MockPipedream(trigger_data)
    handler(pd)

    assert pd.flow.exit_called
    assert "does not have a Notion URL" in pd.flow.exit_message

def test_handler_missing_location():
    """Test handler with missing location."""
    trigger_data = {
        "summary": "Test Event",
        "start": {"dateTime": "2024-03-20T10:00:00Z"},
        "end": {"dateTime": "2024-03-20T11:00:00Z"}
    }

    pd = MockPipedream(trigger_data)
    handler(pd)

    assert pd.flow.exit_called
    assert "does not have a Notion URL" in pd.flow.exit_message

def test_handler_all_day_event():
    """Test handler with all-day event."""
    trigger_data = {
        "summary": "Test Event",
        "location": "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef",
        "start": {"date": "2024-03-20"},
        "end": {"date": "2024-03-21"}
    }

    pd = MockPipedream(trigger_data)
    result = handler(pd)

    assert result["Start"] == "2024-03-20"
    assert result["End"] == "2024-03-21"

def test_handler_missing_end_time():
    """Test handler with missing end time."""
    trigger_data = {
        "summary": "Test Event",
        "location": "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef",
        "start": {"dateTime": "2024-03-20T10:00:00Z"}
    }

    pd = MockPipedream(trigger_data)
    result = handler(pd)

    assert result["Start"] == "2024-03-20T10:00:00Z"
    assert result["End"] == "2024-03-20T10:00:00Z"  # Should fallback to start time 