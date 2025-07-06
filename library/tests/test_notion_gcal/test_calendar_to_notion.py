"""
Tests for Google Calendar to Notion Event Handler

This module contains tests for the handler that processes Google Calendar events
and extracts Notion page IDs from their location URLs.
"""

from datetime import datetime, timedelta

from src.integrations.notion_gcal.calendar_to_notion import (
    get_event_time,
    handler,
)
from src.utils.common_utils import extract_id_from_url, safe_get


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
    """Test extracting Notion page ID from various formats."""
    # Test with valid Notion URL
    assert (
        extract_id_from_url(
            "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef"
        )
        == "1234567890abcdef1234567890abcdef"
    )

    # Test with URL containing query parameters
    assert (
        extract_id_from_url(
            "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef?pvs=4"
        )
        == "1234567890abcdef1234567890abcdef"
    )

    # Test with invalid URLs
    assert extract_id_from_url("https://www.notion.so/My-Page") is None
    assert extract_id_from_url("https://www.notion.so/") is None
    assert extract_id_from_url("") is None
    assert extract_id_from_url(None) is None


def test_get_event_time():
    """Test extracting event time from various formats."""
    # Test with start and end time
    event = {
        "start": {"dateTime": "2024-01-01T10:00:00Z"},
        "end": {"dateTime": "2024-01-01T11:00:00Z"},
    }
    start_time, end_time = get_event_time(event)
    assert start_time == "2024-01-01T10:00:00Z"
    assert end_time == "2024-01-01T11:00:00Z"

    # Test with all-day event
    event = {
        "start": {"date": "2024-01-01"},
        "end": {"date": "2024-01-02"},
    }
    start_time, end_time = get_event_time(event)
    assert start_time == "2024-01-01"
    assert end_time == "2024-01-02"

    # Test with missing end time
    event = {
        "start": {"dateTime": "2024-01-01T10:00:00Z"},
    }
    start_time, end_time = get_event_time(event)
    assert start_time == "2024-01-01T10:00:00Z"
    assert end_time is None

    # Test with invalid event
    assert get_event_time({}) == (None, None)
    assert get_event_time(None) == (None, None)


def test_handler_valid_event():
    """Test handler with valid Notion-linked event data."""
    # Create test data
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    day_after = (datetime.now() + timedelta(days=2)).isoformat()

    trigger_data = {
        "summary": "Test Event",
        "location": "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef",
        "start": {"dateTime": tomorrow},
        "end": {"dateTime": day_after},
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
        "end": {"dateTime": "2024-03-20T11:00:00Z"},
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
        "end": {"dateTime": "2024-03-20T11:00:00Z"},
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
        "end": {"date": "2024-03-21"},
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
        "start": {"dateTime": "2024-03-20T10:00:00Z"},
    }

    pd = MockPipedream(trigger_data)
    result = handler(pd)

    assert result["Start"] == "2024-03-20T10:00:00Z"
    # Should fallback to start time
    assert result["End"] == "2024-03-20T10:00:00Z"


def test_handler_empty_event():
    """Test handler with empty event data."""
    pd = MockPipedream({})
    result = handler(pd)

    assert result["Subject"] == "Untitled Event"
    assert result["Start"] == ""
    assert result["End"] == ""
    assert result["Url"] == ""
    assert result["Description"] == ""
    assert "Id" not in result


def test_handler_dict_input():
    """Test handler with dictionary input instead of Pipedream object."""
    event_data = {
        "summary": "Test Event",
        "location": "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef",
        "start": {"dateTime": "2024-03-20T10:00:00Z"},
        "end": {"dateTime": "2024-03-20T11:00:00Z"},
        "htmlLink": "https://calendar.google.com/event",
        "description": "Test description"
    }

    result = handler({"event": event_data})

    assert result["Subject"] == "Test Event"
    assert result["Start"] == "2024-03-20T10:00:00Z"
    assert result["End"] == "2024-03-20T11:00:00Z"
    assert result["Url"] == "https://calendar.google.com/event"
    assert result["Description"] == "Test description"
    assert result["Id"] == "1234567890abcdef1234567890abcdef"


def test_handler_direct_event():
    """Test handler with direct event attribute."""
    class DirectEventPipedream:
        def __init__(self, event_data):
            self.event = event_data
            self.flow = MockFlow()

    event_data = {
        "summary": "Test Event",
        "location": "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef",
        "start": {"dateTime": "2024-03-20T10:00:00Z"},
        "end": {"dateTime": "2024-03-20T11:00:00Z"}
    }

    pd = DirectEventPipedream(event_data)
    result = handler(pd)

    assert result["Subject"] == "Test Event"
    assert result["Start"] == "2024-03-20T10:00:00Z"
    assert result["End"] == "2024-03-20T11:00:00Z"
    assert result["Id"] == "1234567890abcdef1234567890abcdef"


def test_handler_invalid_notion_url():
    pd = MockPipedream()
    pd.event = {"summary": "Test Event", "location": "https://notion.so/invalid"}
    pd.steps = {"trigger": {"event": pd.event}}
    result = handler(pd)
    assert result["Subject"] == "Test Event"
    assert "Error" in result
    assert result["Error"] == "Invalid Notion URL format"


def test_get_event_time_invalid_format():
    """Test get_event_time with invalid time format."""
    event = {
        "start": {"invalid": "2024-01-01T10:00:00Z"},
        "end": {"invalid": "2024-01-01T11:00:00Z"}
    }

    start_time, end_time = get_event_time(event)
    assert start_time is None
    assert end_time is None


def test_get_event_time_mixed_formats():
    """Test get_event_time with mixed date and dateTime formats."""
    event = {
        "start": {"date": "2024-01-01"},
        "end": {"dateTime": "2024-01-01T11:00:00Z"}
    }

    start_time, end_time = get_event_time(event)
    assert start_time == "2024-01-01"
    assert end_time is None


def test_handler_missing_event():
    pd = MockPipedream()
    result = handler(pd)
    assert result["Subject"] == "Untitled Event"
    assert result["Start"] == ""
    assert result["End"] == ""
    assert result["Url"] == ""
    assert result["Description"] == ""


def test_handler_steps_dict_input():
    class StepsObj:
        def __init__(self, event):
            self.steps = {"trigger": {"event": event}}
            self.flow = MockFlow()
    event = {"summary": "Steps Event", "location": "https://www.notion.so/Page-1234567890abcdef1234567890abcdef"}
    pd = StepsObj(event)
    result = handler(pd)
    assert result["Subject"] == "Steps Event"
    assert result["Id"] == "1234567890abcdef1234567890abcdef"


def test_handler_event_attr_only():
    class EventObj:
        def __init__(self, event):
            self.event = event
            self.flow = MockFlow()
    event = {"summary": "Attr Event", "location": "https://www.notion.so/Page-1234567890abcdef1234567890abcdef"}
    pd = EventObj(event)
    result = handler(pd)
    assert result["Subject"] == "Attr Event"
    assert result["Id"] == "1234567890abcdef1234567890abcdef"


def test_handler_no_event_or_steps():
    class EmptyObj:
        def __init__(self):
            self.flow = MockFlow()
    pd = EmptyObj()
    result = handler(pd)
    assert result["Subject"] == "Untitled Event"
    assert result["Start"] == ""
    assert result["End"] == ""
    assert result["Url"] == ""
    assert result["Description"] == ""


def test_handler_flow_exit_on_non_notion_location():
    class FlowExitObj:
        def __init__(self):
            self.steps = {"trigger": {"event": {"summary": "No Notion", "location": "https://example.com"}}}
            self.flow = MockFlow()
    pd = FlowExitObj()
    handler(pd)
    assert pd.flow.exit_called
    assert "does not have a Notion URL" in pd.flow.exit_message


def test_handler_flow_exit_on_missing_location():
    class FlowExitObj:
        def __init__(self):
            self.steps = {"trigger": {"event": {"summary": "No Location"}}}
            self.flow = MockFlow()
    pd = FlowExitObj()
    handler(pd)
    assert pd.flow.exit_called
    assert "does not have a Notion URL" in pd.flow.exit_message


def test_handler_dict_input_event():
    event = {"summary": "Dict Event", "location": "https://www.notion.so/Page-1234567890abcdef1234567890abcdef"}
    pd = {"event": event}
    result = handler(pd)
    assert result["Subject"] == "Dict Event"
    assert result["Id"] == "1234567890abcdef1234567890abcdef"


def test_handler_object_no_steps_no_event():
    class NoStepsNoEvent:
        pass
    pd = NoStepsNoEvent()
    result = handler(pd)
    assert result["Subject"] == "Untitled Event"
    assert result["Start"] == ""
    assert result["End"] == ""
    assert result["Url"] == ""
    assert result["Description"] == ""


def test_handler_invalid_notion_url_error():
    event = {"summary": "Invalid Notion", "location": "https://www.notion.so/invalid"}
    pd = {"event": event}
    result = handler(pd)
    assert result["Subject"] == "Invalid Notion"
    assert "Error" in result
    assert result["Error"] == "Invalid Notion URL format"
