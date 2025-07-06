"""
Notion Utilities

This module provides utility functions for working with the Notion API,
including authentication, data formatting, and API interactions.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from src.config.constants import (NOTION_API_BASE_URL, NOTION_PAGES_URL, NOTION_BLOCKS_URL, NOTION_DATABASES_URL)

import requests

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---


def format_notion_properties(properties: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format properties for Notion API.

    Args:
        properties: Dictionary of properties to format

    Returns:
        Formatted properties dictionary
    """
    formatted = {}
    
    for key, value in properties.items():
        if isinstance(value, dict):
            if "title" in value:
                formatted[key] = {
                    "title": [
                        {"text": {"content": value["title"]}}
                    ]
                }
            elif "rich_text" in value:
                formatted[key] = {
                    "rich_text": [
                        {"text": {"content": value["rich_text"]}}
                    ]
                }
            elif "date" in value:
                if isinstance(value["date"], str):
                    formatted[key] = {"date": {"start": value["date"]}}
                elif isinstance(value["date"], dict):
                    formatted[key] = {"date": value["date"]}
            elif "select" in value:
                formatted[key] = {"select": {"name": value["select"]}}
            elif "multi_select" in value:
                formatted[key] = {
                    "multi_select": [
                        {"name": v} for v in value["multi_select"]
                    ]
                }
            else:
                formatted[key] = value
        elif isinstance(value, str):
            # Default to rich_text for simple string values
            formatted[key] = {
                "rich_text": [
                    {"text": {"content": value}}
                ]
            }
        elif isinstance(value, list):
            formatted[key] = {
                "multi_select": [
                    {"name": v} for v in value
                ]
            }
        else:
            formatted[key] = value
    
    return formatted


def extract_notion_page_id_from_url(url: str) -> Optional[str]:
    """
    Extract Notion page ID from a Notion URL.

    Args:
        url: Notion URL

    Returns:
        Page ID or None if not found
    """
    if not url:
        return None

    # Try to match Notion URL patterns
    patterns = [
        r'notion\.so/([a-zA-Z0-9]{32})',  # Direct page ID
        r'notion\.so/[^/]+-([a-zA-Z0-9]{32})',  # Page with title
        r'notion\.so/[^/]+/([a-zA-Z0-9]{32})',  # Page in workspace
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def extract_notion_task_data(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract relevant data from a Notion task/trigger event.
    Args:
        task: Notion task data
    Returns:
        Dictionary containing extracted task data
    """
    properties = task.get("properties", {})
    # Task name
    task_name = None
    if "Task name" in properties:
        title_val = properties["Task name"].get("title")
        if isinstance(title_val, list) and title_val:
            task_name = title_val[0].get("plain_text") or title_val[0].get("text", {}).get("content")
    # Due date
    due_date_start = None
    due_date_end = None
    if "Due Date" in properties:
        date_val = properties["Due Date"].get("date")
        if isinstance(date_val, dict):
            due_date_start = date_val.get("start")
            due_date_end = date_val.get("end")
        elif isinstance(date_val, str):
            due_date_start = date_val
    # Google Event ID
    event_id = None
    if "Google Event ID" in properties:
        rich_text = properties["Google Event ID"].get("rich_text")
        if isinstance(rich_text, list) and rich_text:
            event_id = rich_text[0].get("plain_text") if isinstance(rich_text[0], dict) else rich_text[0]
        elif isinstance(rich_text, str):
            event_id = rich_text
    # Notion ID and URL
    notion_id = task.get("id")
    url = task.get("url")
    return {
        "due_date_start": due_date_start,
        "due_date_end": due_date_end,
        "task_name": task_name,
        "event_id": event_id,
        "notion_id": notion_id,
        "url": url,
    }


def get_notion_page(token: str, page_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Notion page details.

    Args:
        token: Notion API access token
        page_id: Notion page ID

    Returns:
        Page data or None if error
    """
    try:
        response = requests.get(
            f"{NOTION_PAGES_URL}/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28"
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting Notion page: {e}")
        return None


def get_notion_database(token: str, database_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Notion database details.

    Args:
        token: Notion API access token
        database_id: Notion database ID

    Returns:
        Database data or None if error
    """
    try:
        response = requests.get(
            f"{NOTION_DATABASES_URL}/{database_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28"
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting Notion database: {e}")
        return None


def query_notion_database(
    token: str,
    database_id: str,
    filter_criteria: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Query Notion database with optional filter criteria.

    Args:
        token: Notion API access token
        database_id: Notion database ID
        filter_criteria: Optional filter criteria

    Returns:
        List of database entries
    """
    try:
        response = requests.post(
            f"{NOTION_DATABASES_URL}/{database_id}/query",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={"filter": filter_criteria} if filter_criteria else {}
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        logger.error(f"Error querying Notion database: {e}")
        return []


def create_notion_page(
    token: str,
    database_id: str,
    properties: Dict[str, Any],
    content: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Create a new page in Notion.

    Args:
        token: Notion API access token
        database_id: Notion database ID
        properties: Page properties
        content: Optional page content blocks

    Returns:
        Created page data or None if error
    """
    try:
        response = requests.post(
            NOTION_PAGES_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={
                "parent": {
                    "database_id": database_id
                },
                "properties": properties,
                "children": content or []
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error creating Notion page: {e}")
        return None


def update_notion_page(
    token: str,
    page_id: str,
    properties: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Update an existing Notion page.

    Args:
        token: Notion API access token
        page_id: Notion page ID
        properties: Updated properties

    Returns:
        Updated page data or None if error
    """
    try:
        response = requests.patch(
            f"{NOTION_PAGES_URL}/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={"properties": properties}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error updating Notion page: {e}")
        return None


def append_notion_blocks(
    token: str,
    block_id: str,
    blocks: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Append blocks to a Notion page.

    Args:
        token: Notion API access token
        block_id: Notion block ID
        blocks: Blocks to append

    Returns:
        Updated block data or None if error
    """
    try:
        response = requests.patch(
            f"{NOTION_BLOCKS_URL}/{block_id}/children",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={"children": blocks}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error appending Notion blocks: {e}")
        return None


def validate_notion_response(response):
    """
    Validate a Notion API response.
    Returns True if response is a dict, has an 'object' key, and is not an error object.
    """
    if not isinstance(response, dict):
        return False
    if response.get("object") == "error":
        return False
    return "object" in response
