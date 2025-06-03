"""Tests for Notion utility functions."""



from src.utils.notion_utils import (
    extract_notion_page_id_from_url,
    extract_notion_task_data,
    format_notion_properties,
    validate_notion_response,
)


def test_extract_notion_task_data():
    """Test extracting task data from a Notion trigger event."""
    # Test with complete data
    trigger_event = {
        "properties": {
            "Due Date": {
                "date": {"start": "2024-03-20T10:00:00Z", "end": "2024-03-20T11:00:00Z"}
            },
            "Task name": {"title": [{"plain_text": "Test Task"}]},
            "Google Event ID": {"rich_text": [{"plain_text": "event123"}]},
        },
        "id": "page123",
        "url": "https://notion.so/page123",
    }

    result = extract_notion_task_data(trigger_event)
    assert result["due_date_start"] == "2024-03-20T10:00:00Z"
    assert result["due_date_end"] == "2024-03-20T11:00:00Z"
    assert result["task_name"] == "Test Task"
    assert result["event_id"] == "event123"
    assert result["notion_id"] == "page123"
    assert result["url"] == "https://notion.so/page123"

    # Test with minimal data
    minimal_event = {"properties": {"Task name": {
        "title": [{"plain_text": "Minimal Task"}]}}}

    result = extract_notion_task_data(minimal_event)
    assert result["task_name"] == "Minimal Task"
    assert result["due_date_start"] is None
    assert result["due_date_end"] is None
    assert result["event_id"] is None
    assert result["notion_id"] is None
    assert result["url"] is None

    # Test with alternative Google Event ID format
    alt_event = {
        "properties": {
            "Task name": {"title": [{"plain_text": "Alt Task"}]},
            "Google Event ID": {"rich_text": ["event456"]},
        }
    }

    result = extract_notion_task_data(alt_event)
    assert result["task_name"] == "Alt Task"
    assert result["event_id"] == "event456"


def test_format_notion_properties():
    """Test formatting Notion properties for API requests."""
    # Test title property
    properties = {"Name": {"title": "Test Title"}}
    result = format_notion_properties(properties)
    assert result["Name"]["title"][0]["text"]["content"] == "Test Title"

    # Test rich text property
    properties = {"Description": {"rich_text": "Test Description"}}
    result = format_notion_properties(properties)
    assert (result["Description"]["rich_text"][0]
            ["text"]["content"] == "Test Description")

    # Test date property
    properties = {"Due Date": {"date": "2024-03-20"}}
    result = format_notion_properties(properties)
    assert result["Due Date"]["date"]["start"] == "2024-03-20"

    # Test select property
    properties = {"Status": {"select": "In Progress"}}
    result = format_notion_properties(properties)
    assert result["Status"]["select"]["name"] == "In Progress"

    # Test multi-select property
    properties = {"Tags": {"multi_select": ["Tag1", "Tag2"]}}
    result = format_notion_properties(properties)
    assert len(result["Tags"]["multi_select"]) == 2
    assert result["Tags"]["multi_select"][0]["name"] == "Tag1"
    assert result["Tags"]["multi_select"][1]["name"] == "Tag2"

    # Test simple value
    properties = {"Simple": "Value"}
    result = format_notion_properties(properties)
    assert result["Simple"]["rich_text"][0]["text"]["content"] == "Value"


def test_validate_notion_response():
    """Test validating Notion API responses."""
    # Test valid response
    valid_response = {"object": "page", "id": "page123"}
    assert validate_notion_response(valid_response) is True

    # Test invalid response type
    assert validate_notion_response("not a dict") is False

    # Test missing object field
    assert validate_notion_response({"id": "page123"}) is False

    # Test error response
    error_response = {"object": "error", "message": "Test error"}
    assert validate_notion_response(error_response) is False


def test_extract_notion_page_id_from_url():
    """Test extracting Notion page IDs from URLs."""
    # Test valid URL
    url = "https://notion.so/1234567890abcdef1234567890abcdef"
    assert extract_notion_page_id_from_url(
        url) == "1234567890abcdef1234567890abcdef"

    # Test URL with query parameters
    url = "https://notion.so/1234567890abcdef1234567890abcdef?p=123"
    assert extract_notion_page_id_from_url(
        url) == "1234567890abcdef1234567890abcdef"

    # Test invalid URL
    url = "https://notion.so/invalid"
    assert extract_notion_page_id_from_url(url) is None

    # Test empty URL
    assert extract_notion_page_id_from_url("") is None
