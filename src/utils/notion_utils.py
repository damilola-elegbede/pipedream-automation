"""
Notion Utility Functions

This module contains utility functions specific to Notion integration,
including data extraction, formatting, and API request handling.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from src.utils.common_utils import safe_get, extract_id_from_url

# Configure basic logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def extract_notion_task_data(trigger_event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts relevant data from a Notion task trigger event.

    Args:
        trigger_event: The Notion trigger event data

    Returns:
        Dictionary containing extracted task data:
        - due_date: Task due date
        - task_name: Name of the task
        - event_id: Google Calendar event ID (if exists)
        - notion_id: Notion page ID
        - url: Notion page URL
    """
    # Extract basic task data
    task_data = {
        "due_date": safe_get(trigger_event, ["properties", "Due date", "date", "start"]),
        "task_name": safe_get(trigger_event, ["properties", "Name", "title", 0, "text", "content"], "Untitled Task"),
        "event_id": safe_get(trigger_event, ["properties", "Google Event ID", "rich_text", 0, "text", "content"]),
        "notion_id": safe_get(trigger_event, ["id"]),
        "url": safe_get(trigger_event, ["url"])
    }

    # Log extracted data
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
                    "title": [{"text": {"content": value["title"]}}]
                }
            elif "rich_text" in value:
                formatted[key] = {
                    "rich_text": [{"text": {"content": value["rich_text"]}}]
                }
            elif "date" in value:
                formatted[key] = {
                    "date": {"start": value["date"]}
                }
            elif "select" in value:
                formatted[key] = {
                    "select": {"name": value["select"]}
                }
            elif "multi_select" in value:
                formatted[key] = {
                    "multi_select": [{"name": item} for item in value["multi_select"]]
                }
        else:
            # Default to rich text for simple values
            formatted[key] = {
                "rich_text": [{"text": {"content": str(value)}}]
            }

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
        logger.error(f"Notion API error: {safe_get(response, ['message'], 'Unknown error')}")
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
    return extract_id_from_url(url, pattern=r'[a-f0-9]{32}$') 