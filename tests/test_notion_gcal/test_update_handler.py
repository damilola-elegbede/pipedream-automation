"""
Tests for Notion to Google Calendar Update Handler

This module contains tests for the handler that processes Notion page updates
and prepares data for updating corresponding Google Calendar events.
"""

import pytest
from datetime import datetime, timedelta
from src.integrations.notion_gcal.update_handler import safe_get, handler

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

def test_handler_valid_update():
    """Test handler with valid update data."""
    # Create test data
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    day_after = (datetime.now() + timedelta(days=2)).isoformat()
    
    trigger_data = {
        "page": {
            "url": "https://notion.so/test",
            "properties": {
                "Task name": {
                    "title": [{"plain_text": "Test Task"}]
                },
                "Due Date": {
                    "date": {
                        "start": tomorrow,
                        "end": day_after
                    }
                },
                "Google Event ID": {
                    "rich_text": [{"plain_text": "event123"}]
                }
            }
        }
    }

    pd = MockPipedream(trigger_data)
    result = handler(pd)

    # Verify result structure
    assert "GCal" in result
    assert result["GCal"]["Subject"] == "Test Task"
    assert result["GCal"]["Start"] == tomorrow
    assert result["GCal"]["End"] == day_after
    assert result["GCal"]["EventId"] == "event123"
    assert result["GCal"]["Update"] is True
    assert "Notion Task: Test Task" in result["GCal"]["Description"]
    assert "https://notion.so/test" in result["GCal"]["Description"]

def test_handler_missing_due_date():
    """Test handler with missing due date."""
    trigger_data = {
        "page": {
            "url": "https://notion.so/test",
            "properties": {
                "Task name": {
                    "title": [{"plain_text": "Test Task"}]
                },
                "Google Event ID": {
                    "rich_text": [{"plain_text": "event123"}]
                }
            }
        }
    }

    pd = MockPipedream(trigger_data)
    handler(pd)

    assert pd.flow.exit_called
    assert "Due Date is missing" in pd.flow.exit_message

def test_handler_missing_event_id():
    """Test handler with missing Google Event ID."""
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    
    trigger_data = {
        "page": {
            "url": "https://notion.so/test",
            "properties": {
                "Task name": {
                    "title": [{"plain_text": "Test Task"}]
                },
                "Due Date": {
                    "date": {
                        "start": tomorrow
                    }
                }
            }
        }
    }

    pd = MockPipedream(trigger_data)
    handler(pd)

    assert pd.flow.exit_called
    assert "Google Event ID is missing" in pd.flow.exit_message

def test_handler_untitled_task():
    """Test handler with missing task name."""
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    
    trigger_data = {
        "page": {
            "url": "https://notion.so/test",
            "properties": {
                "Due Date": {
                    "date": {
                        "start": tomorrow
                    }
                },
                "Google Event ID": {
                    "rich_text": [{"plain_text": "event123"}]
                }
            }
        }
    }

    pd = MockPipedream(trigger_data)
    result = handler(pd)

    assert result["GCal"]["Subject"] == "Untitled Task"

def test_handler_same_start_end_date():
    """Test handler when start and end dates are the same."""
    tomorrow = (datetime.now() + timedelta(days=1)).isoformat()
    
    trigger_data = {
        "page": {
            "url": "https://notion.so/test",
            "properties": {
                "Task name": {
                    "title": [{"plain_text": "Test Task"}]
                },
                "Due Date": {
                    "date": {
                        "start": tomorrow
                    }
                },
                "Google Event ID": {
                    "rich_text": [{"plain_text": "event123"}]
                }
            }
        }
    }

    pd = MockPipedream(trigger_data)
    result = handler(pd)

    assert result["GCal"]["Start"] == tomorrow
    assert result["GCal"]["End"] == tomorrow 