"""
Tests for the Notion Task to Google Calendar Event converter.
"""
import pytest
from datetime import datetime, timedelta
from src.utils.common_utils import safe_get
from src.integrations.notion_gcal.task_to_event import handler

class MockPipedream:
    def __init__(self, steps):
        self.steps = steps
        self.flow = MockFlow()

class MockFlow:
    def exit(self, message):
        raise SystemExit(message)

def test_safe_get():
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

def test_handler_valid_task():
    # Create test data
    start_date = datetime.now().isoformat()
    end_date = (datetime.now() + timedelta(hours=1)).isoformat()
    
    mock_steps = {
        "trigger": {
            "event": {
                "id": "notion-123",
                "url": "https://notion.so/task-123",
                "properties": {
                    "Due Date": {
                        "date": {
                            "start": start_date,
                            "end": end_date
                        }
                    },
                    "Task name": {
                        "title": [
                            {
                                "plain_text": "Test Task"
                            }
                        ]
                    },
                    "Google Event ID": {
                        "rich_text": []
                    }
                }
            }
        }
    }
    
    pd = MockPipedream(mock_steps)
    result = handler(pd)
    
    # Test structure of return value
    assert isinstance(result, dict)
    assert "GCal" in result
    assert result["GCal"]["Subject"] == "Test Task"
    assert result["GCal"]["Start"] == start_date
    assert result["GCal"]["End"] == end_date
    assert result["GCal"]["Update"] is False
    assert result["GCal"]["NotionId"] == "notion-123"
    assert result["GCal"]["Url"] == "https://notion.so/task-123"

def test_handler_missing_due_date():
    mock_steps = {
        "trigger": {
            "event": {
                "properties": {
                    "Task name": {
                        "title": [
                            {
                                "plain_text": "Test Task"
                            }
                        ]
                    }
                }
            }
        }
    }
    
    pd = MockPipedream(mock_steps)
    with pytest.raises(SystemExit) as exc_info:
        handler(pd)
    assert "Due Date is missing" in str(exc_info.value)

def test_handler_existing_event():
    mock_steps = {
        "trigger": {
            "event": {
                "properties": {
                    "Due Date": {
                        "date": {
                            "start": datetime.now().isoformat()
                        }
                    },
                    "Task name": {
                        "title": [
                            {
                                "plain_text": "Test Task"
                            }
                        ]
                    },
                    "Google Event ID": {
                        "rich_text": ["existing-event-id"]
                    }
                }
            }
        }
    }
    
    pd = MockPipedream(mock_steps)
    with pytest.raises(SystemExit) as exc_info:
        handler(pd)
    assert "Google Event ID exists" in str(exc_info.value)

def test_handler_untitled_task():
    start_date = datetime.now().isoformat()
    mock_steps = {
        "trigger": {
            "event": {
                "properties": {
                    "Due Date": {
                        "date": {
                            "start": start_date
                        }
                    },
                    "Task name": {
                        "title": []
                    },
                    "Google Event ID": {
                        "rich_text": []
                    }
                }
            }
        }
    }
    
    pd = MockPipedream(mock_steps)
    result = handler(pd)
    assert result["GCal"]["Subject"] == "Untitled Task" 