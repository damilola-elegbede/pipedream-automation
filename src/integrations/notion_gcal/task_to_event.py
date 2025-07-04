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

if TYPE_CHECKING:
    import pipedream

from src.utils.notion_utils import extract_notion_task_data
from src.utils.common_utils import safe_get

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
