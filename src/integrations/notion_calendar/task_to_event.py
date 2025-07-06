"""
Notion Task to Calendar Event Integration

This module syncs Notion tasks to Google Calendar events, handling authentication,
task retrieval, and event creation.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from src.config.constants import (NOTION_API_BASE_URL, NOTION_DATABASES_URL)

import requests
from requests.exceptions import HTTPError, RequestException

from src.utils.common_utils import safe_get

if TYPE_CHECKING:
    import pipedream

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"
CALENDAR_EVENTS_URL = f"{CALENDAR_API_BASE_URL}/calendars/primary/events"


def get_notion_tasks(
    token: str,
    database_id: str
) -> List[Dict[str, Any]]:
    """
    Get tasks from Notion database.

    Args:
        token: Notion API access token
        database_id: Notion database ID

    Returns:
        List of Notion tasks
    """
    try:
        response = requests.post(
            f"{NOTION_DATABASES_URL}/{database_id}/query",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        logger.error(f"Error getting Notion tasks: {e}")
        return []


def build_calendar_event(
    task: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build Google Calendar event from Notion task.

    Args:
        task: Notion task data

    Returns:
        Dictionary containing calendar event data
    """
    properties = task.get("properties", {})
    name = properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled Task")
    due_date = properties.get("Due Date", {}).get("date", {}).get("start")
    description = properties.get("Description", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "")

    event = {
        "summary": name,
        "description": description
    }

    if due_date:
        event["start"] = {
            "dateTime": due_date,
            "timeZone": "UTC"
        }
        event["end"] = {
            "dateTime": due_date,
            "timeZone": "UTC"
        }

    return event


def create_calendar_event(
    token: str,
    event: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Create event in Google Calendar.

    Args:
        token: Google Calendar API access token
        event: Event data

    Returns:
        Created event data or None if error
    """
    try:
        response = requests.post(
            CALENDAR_EVENTS_URL,
            headers={"Authorization": f"Bearer {token}"},
            json=event
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        return None


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Sync Notion tasks to Google Calendar.

    Args:
        pd: The Pipedream context object

    Returns:
        Dictionary containing sync results and any errors
    """
    try:
        # Get Notion OAuth Token
        notion_token = safe_get(
            pd.inputs,
            ["notion", "$auth", "oauth_access_token"]
        )
        if not notion_token:
            raise Exception(
                "Notion account not connected or input name is not 'notion'. "
                "Please connect a Notion account."
            )

        # Get Google Calendar OAuth Token
        calendar_token = safe_get(
            pd.inputs,
            ["calendar", "$auth", "oauth_access_token"]
        )
        if not calendar_token:
            raise Exception(
                "Google Calendar account not connected or input name is not "
                "'calendar'. Please connect a Google Calendar account."
            )

        # Get Notion tasks
        tasks = get_notion_tasks(notion_token, pd.inputs["database_id"])
        if not tasks:
            return {
                "message": "No tasks found in the Notion database",
                "events": []
            }

        # Create calendar events
        created_events = []
        for task in tasks:
            event_data = build_calendar_event(task)
            event = create_calendar_event(calendar_token, event_data)
            if event:
                created_events.append({
                    "title": event.get("summary", "Untitled Event"),
                    "url": event.get("htmlLink")
                })

        return {
            "message": f"Successfully created {len(created_events)} events",
            "events": created_events
        }

    except Exception as e:
        logger.error(f"Error syncing Notion to Calendar: {e}")
        return {
            "error": str(e)
        }
