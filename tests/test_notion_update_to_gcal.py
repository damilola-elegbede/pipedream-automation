"""
Tests for notion_update_to_gcal.py Pipedream step.
"""
import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from steps.notion_update_to_gcal import handler, safe_get


class TestSafeGet:
    """Tests for the safe_get helper function."""

    def test_gets_nested_dict_value(self):
        data = {"page": {"properties": {"name": "value"}}}
        assert safe_get(data, ["page", "properties", "name"]) == "value"

    def test_returns_default_on_missing(self):
        data = {"a": 1}
        assert safe_get(data, ["b"], default="default") == "default"


class TestHandler:
    """Tests for the main handler function."""

    def test_exits_when_due_date_missing(self, mock_pd):
        mock_pd.steps = {
            "trigger": {
                "event": {
                    "page": {
                        "properties": {
                            "Task name": {"title": [{"plain_text": "Test Task"}]},
                            "Due Date": {"date": None},
                            "Google Event ID": {"rich_text": [{"plain_text": "event_123"}]}
                        },
                        "url": "https://www.notion.so/test"
                    }
                }
            }
        }

        result = handler(mock_pd)

        assert mock_pd.flow.exit_called is True
        assert "Due Date is missing" in mock_pd.flow.exit_message

    def test_exits_when_google_event_id_missing(self, mock_pd):
        """Without event ID, this should be a create, not update."""
        mock_pd.steps = {
            "trigger": {
                "event": {
                    "page": {
                        "properties": {
                            "Task name": {"title": [{"plain_text": "Test Task"}]},
                            "Due Date": {"date": {"start": "2024-01-20", "end": None}},
                            "Google Event ID": {"rich_text": []}  # Empty = no event
                        },
                        "url": "https://www.notion.so/test"
                    }
                }
            }
        }

        result = handler(mock_pd)

        assert mock_pd.flow.exit_called is True
        assert "Google Event ID is missing" in mock_pd.flow.exit_message

    def test_processes_valid_update(self, mock_pd, sample_notion_update_trigger):
        mock_pd.steps = sample_notion_update_trigger

        result = handler(mock_pd)

        assert mock_pd.flow.exit_called is False
        assert result["GCal"]["Subject"] == "Updated Task"
        assert result["GCal"]["Update"] is True
        assert result["GCal"]["EventId"] == "gcal_event_xyz789"

    def test_uses_start_as_end_when_end_missing(self, mock_pd, sample_notion_update_trigger):
        mock_pd.steps = sample_notion_update_trigger

        result = handler(mock_pd)

        # End should default to start when None
        assert result["GCal"]["End"] == result["GCal"]["Start"]

    def test_includes_notion_url(self, mock_pd, sample_notion_update_trigger):
        mock_pd.steps = sample_notion_update_trigger

        result = handler(mock_pd)

        assert "Url" in result["GCal"]
        assert "notion.so" in result["GCal"]["Url"]

    def test_includes_description_with_link(self, mock_pd, sample_notion_update_trigger):
        mock_pd.steps = sample_notion_update_trigger

        result = handler(mock_pd)

        assert "Description" in result["GCal"]
        assert "Link:" in result["GCal"]["Description"]
