"""
Notion to Google Calendar Sync
Generated: 2025-07-05 17:21:23
Bundled for Pipedream deployment
"""

import logging
import json
import requests
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from requests.exceptions import HTTPError, RequestException

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# === EMBEDDED DEPENDENCIES ===
# === UTILITY FUNCTIONS ===
# From src/utils/common_utils.py
def safe_get(obj, path, default=None):
    """
    Safely get a value from a nested dictionary or list using a path.
    Args:
        obj: Dictionary or list to get value from
        path: List of keys/indices or a single key/index
        default: Value to return if path is not found
    Returns:
        Value at path or default if not found
    """
    if obj is None:
        return default
    if path is None or path == []:
        return default
    if not isinstance(path, list):
        path = [path]
    current = obj
    try:
        for key in path:
            if isinstance(current, dict):
                current = current.get(key, default)
            elif isinstance(current, list) and isinstance(key, int):
                if 0 <= key < len(current):
                    current = current[key]
                else:
                    return default
            else:
                return default
        return current
    except Exception:
        return default


# From src/utils/notion_utils.py
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




# === MAIN MODULE ===
"""
Notion Task to Google Calendar Event Converter

This module handles the conversion of Notion tasks to Google Calendar events.
It processes task data from a Notion trigger, validates the data, and prepares
it for Google Calendar event creation.

The main handler function expects a Pipedream context object and returns a
dictionary containing the formatted data for Google Calendar event creation.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING
import requests
from requests.exceptions import RequestException


# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_task_data(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate task data and extract required fields.

    Args:
        task: The Notion task data to validate

    Returns:
        Dictionary containing validation result and extracted data
    """
    if not task:
        return {"error": "No task data provided"}

    properties = task.get("properties", {})
    if not isinstance(properties, dict):
        return {"error": "Task properties must be a dict"}

    title_data = properties.get("Name", {}).get("title", [])
    if not isinstance(title_data, list) or not title_data:
        return {"error": "Task has no title"}

    title = (
        title_data[0].get("text", {}).get("content", "Untitled Task")
        if isinstance(title_data[0], dict)
        else "Untitled Task"
    )

    due_date_field = properties.get("Due date", {}).get("date", {})
    if not isinstance(due_date_field, dict):
        return {"error": "Task has no due date"}

    due_date = due_date_field.get("start")
    if not due_date:
        return {"error": "Task has no due date"}

    description_data = properties.get("Description", {}).get("rich_text", [])
    description = (
        description_data[0].get("text", {}).get("content")
        if isinstance(description_data, list) and description_data
        else ""
    )

    location_data = properties.get("Location", {}).get("rich_text", [])
    location = (
        location_data[0].get("text", {}).get("content")
        if isinstance(location_data, list) and location_data
        else ""
    )

    event_id = None
    event_id_data = properties.get("Event ID", {}).get("rich_text", [])
    if isinstance(event_id_data, list) and event_id_data:
        event_id = event_id_data[0].get("text", {}).get("content")

    return {
        "success": {
            "title": title,
            "due_date": due_date,
            "description": description,
            "location": location,
            "event_id": event_id,
            "task_url": task.get("url", "")
        }
    }


def create_calendar_event(
    event_data: Dict[str, Any],
    calendar_id: str,
    calendar_auth: str,
    event_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create or update a Google Calendar event.

    Args:
        event_data: The event data to create/update
        calendar_id: The Google Calendar ID
        calendar_auth: The Google Calendar authentication token
        event_id: Optional event ID for updates

    Returns:
        Dictionary containing the API response or error
    """
    url = (
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
        if not event_id
        else f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
    )

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {calendar_auth}",
                "Content-Type": "application/json",
            },
            json=event_data,
        )
        response.raise_for_status()
        return {"success": response.json()}
    except RequestException as e:
        error_msg = str(e)
        if "401" in error_msg:
            return {"error": "Invalid calendar authentication"}
        elif "404" in error_msg:
            return {"error": "Calendar not found"}
        else:
            return {"error": error_msg}


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Process Notion task data and prepare it for Google Calendar event creation.

    Args:
        pd: Pipedream context containing task data and authentication

    Returns:
        Dictionary with success and error information
    """
    # Validate required inputs
    task = pd.get("task")
    if not task:
        return {"error": "No task data provided"}

    calendar_auth = pd.get("calendar_auth")
    if not calendar_auth:
        return {"error": "Missing calendar authentication"}

    calendar_id = pd.get("calendar_id")
    if not calendar_id:
        return {"error": "Missing calendar ID"}

    # Validate and extract task data
    task_validation = validate_task_data(task)
    if "error" in task_validation:
        return task_validation

    task_data = task_validation["success"]

    # Prepare event data
    event = {
        "summary": task_data["title"],
        "description": task_data["description"],
        "location": task_data["location"],
        "start": {"dateTime": task_data["due_date"]},
        "end": {"dateTime": task_data["due_date"]},
    }

    # Create or update event
    result = create_calendar_event(
        event,
        calendar_id,
        calendar_auth,
        task_data["event_id"]
    )

    if "error" in result:
        return result

    event_data = result["success"]
    return {
        "success": {
            "event_id": event_data["id"],
            "event_url": event_data["htmlLink"],
            "task_url": task_data["task_url"]
        }
    }

# === PIPEDREAM HANDLER ===
# The handler function is the entry point for Pipedream
# Usage: return handler(pd)
