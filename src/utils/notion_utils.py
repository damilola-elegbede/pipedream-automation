"""
Notion Utility Functions

This module contains utility functions specific to Notion integration,
including data extraction, formatting, and API request handling.
"""

import logging
from typing import Any, Dict, Optional

from src.utils.common_utils import extract_id_from_url, safe_get

# Configure basic logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def extract_notion_task_data(trigger_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts relevant data from a Notion task trigger event.

    Args:
        trigger_event: The trigger event data from Notion

    Returns:
        Dictionary containing extracted task data
    """
    properties = safe_get(trigger_event, ["properties"], default={})

    # Extract due date
    due_date = safe_get(properties, ["Due Date", "date"], default={})
    due_date_start = safe_get(due_date, ["start"])
    due_date_end = safe_get(due_date, ["end"])

    # Extract task name
    task_name = safe_get(
        properties, [
            "Task name", "title", 0, "plain_text"], default="Untitled Task")

    # Extract Google Event ID
    event_id = safe_get(
        properties, [
            "Google Event ID", "rich_text", 0, "plain_text"])
    if not event_id and isinstance(
        safe_get(properties, ["Google Event ID", "rich_text"]), list
    ):
        event_id = safe_get(properties, ["Google Event ID", "rich_text", 0])

    # Extract Notion page ID and URL
    notion_id = safe_get(trigger_event, ["id"])
    notion_url = safe_get(trigger_event, ["url"])

    task_data = {
        "due_date_start": due_date_start,
        "due_date_end": due_date_end,
        "task_name": task_name,
        "event_id": event_id,
        "notion_id": notion_id,
        "url": notion_url,
    }

    logger.info(f"Extracted task data: {task_data}")
    return task_data


def format_notion_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats Notion properties for API requests.

    Args:
        properties: Dictionary of Notion properties to format

    Returns:
        Formatted properties ready for Notion API
    """
    formatted = {}
    for key, value in properties.items():
        if isinstance(value, dict):
            # Handle different property types
            if "title" in value:
                formatted[key] = {
                    "title": [{"text": {"content": value["title"]}}]}
            elif "rich_text" in value:
                formatted[key] = {
                    "rich_text": [{"text": {"content": value["rich_text"]}}]
                }
            elif "date" in value:
                formatted[key] = {"date": {"start": value["date"]}}
            elif "select" in value:
                formatted[key] = {"select": {"name": value["select"]}}
            elif "multi_select" in value:
                formatted[key] = {"multi_select": [{"name": item}
                                                   for item in value["multi_select"]]}
        else:
            # Default to rich text for simple values
            formatted[key] = {"rich_text": [{"text": {"content": str(value)}}]}

    return formatted


def validate_notion_response(response: Dict[str, Any]) -> bool:
    """
    Validates a response from the Notion API.

    Args:
        response: The API response to validate

    Returns:
        True if the response is valid, False otherwise
    """
    if not isinstance(response, dict):
        logger.error("Invalid response type: expected dict")
        return False

    if "object" not in response:
        logger.error("Missing 'object' field in response")
        return False

    if response["object"] == "error":
        logger.error(
            f"Notion API error: {
                safe_get(
                    response,
                    ['message'],
                    'Unknown error')}")
        return False

    return True


def extract_notion_page_id_from_url(url: str) -> Optional[str]:
    """
    Extracts a Notion page ID from a URL.

    Args:
        url: The Notion page URL

    Returns:
        The extracted page ID or None if extraction fails
    """
    return extract_id_from_url(url, pattern=r"[a-f0-9]{32}$")
