"""
Tests for notion_task_to_gcal.py Pipedream step.
"""
import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from steps.notion_task_to_gcal import handler, safe_get


class TestSafeGet:
    """Tests for the safe_get helper function."""

    def test_gets_nested_dict_value(self):
        data = {"a": {"b": {"c": "value"}}}
        assert safe_get(data, ["a", "b", "c"]) == "value"

    def test_gets_list_index(self):
        data = {"items": [{"name": "first"}, {"name": "second"}]}
        assert safe_get(data, ["items", 0, "name"]) == "first"

    def test_returns_default_for_missing_key(self):
        data = {"a": 1}
        assert safe_get(data, ["b", "c"], default="default") == "default"

    def test_handles_empty_list(self):
        data = {"items": []}
        assert safe_get(data, ["items", 0], default="default") == "default"


class TestHandler:
    """Tests for the main handler function."""

    def test_exits_when_due_date_missing(self, mock_pd):
        mock_pd.steps = {
            "trigger": {
                "event": {
                    "properties": {
                        "Task name": {"title": [{"plain_text": "Test Task"}]},
                        "Due Date": {"date": None},
                        "Google Event ID": {"rich_text": []}
                    },
                    "url": "https://www.notion.so/test"
                }
            }
        }

        result = handler(mock_pd)

        assert mock_pd.flow.exit_called is True
        assert "Due Date is missing" in mock_pd.flow.exit_message

    def test_exits_when_event_already_exists(self, mock_pd):
        mock_pd.steps = {
            "trigger": {
                "event": {
                    "properties": {
                        "Task name": {"title": [{"plain_text": "Test Task"}]},
                        "Due Date": {"date": {"start": "2024-01-20", "end": None}},
                        "Google Event ID": {"rich_text": [{"plain_text": "existing_event_id"}]}
                    },
                    "url": "https://www.notion.so/test"
                }
            }
        }

        result = handler(mock_pd)

        assert mock_pd.flow.exit_called is True
        assert "Google Event ID exists" in mock_pd.flow.exit_message

    def test_processes_valid_task(self, mock_pd, sample_notion_task_trigger):
        mock_pd.steps = sample_notion_task_trigger

        result = handler(mock_pd)

        assert mock_pd.flow.exit_called is False
        assert result["GCal"]["Subject"] == "Test Task"
        assert result["GCal"]["Start"] == "2024-01-20"
        assert result["GCal"]["End"] == "2024-01-21"
        assert result["GCal"]["Update"] is False  # Update=False means it's a create

    def test_uses_start_as_end_when_end_missing(self, mock_pd):
        mock_pd.steps = {
            "trigger": {
                "event": {
                    "properties": {
                        "Task name": {"title": [{"plain_text": "Single Day Task"}]},
                        "Due Date": {"date": {"start": "2024-01-20", "end": None}},
                        "Google Event ID": {"rich_text": []}
                    },
                    "url": "https://www.notion.so/single-day"
                }
            }
        }

        result = handler(mock_pd)

        # End should default to start date
        assert result["GCal"]["End"] == result["GCal"]["Start"]

    def test_includes_notion_url_in_result(self, mock_pd, sample_notion_task_trigger):
        mock_pd.steps = sample_notion_task_trigger

        result = handler(mock_pd)

        assert "Url" in result["GCal"]
        assert "notion.so" in result["GCal"]["Url"]

    def test_includes_description(self, mock_pd, sample_notion_task_trigger):
        mock_pd.steps = sample_notion_task_trigger

        result = handler(mock_pd)

        assert "Description" in result["GCal"]
        assert "Notion Task" in result["GCal"]["Description"]
