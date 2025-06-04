"""
Notion Task Update Handler

This module handles updates to Notion tasks and syncs them to Google Calendar,
managing authentication, task updates, and event synchronization.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import requests
from requests.exceptions import HTTPError, RequestException

from src.utils.common_utils import safe_get

if TYPE_CHECKING:
    import pipedream

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_PAGES_URL = f"{NOTION_API_BASE_URL}/pages"
CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"
CALENDAR_EVENTS_URL = f"{CALENDAR_API_BASE_URL}/calendars/primary/events"


def get_notion_page(
    token: str,
    page_id: str
) -> Optional[Dict[str, Any]]:
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


def build_calendar_event(
    page: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build Google Calendar event from Notion page.

    Args:
        page: Notion page data

    Returns:
        Dictionary containing calendar event data
    """
    properties = page.get("properties", {})
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
    Handle Notion task updates and sync to Google Calendar.

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

        # Get updated page ID from input
        page_id = pd.inputs.get("page_id")
        if not page_id:
            raise Exception("page_id is required")

        # Get updated page
        page = get_notion_page(notion_token, page_id)
        if not page:
            return {
                "error": f"Could not find Notion page with ID: {page_id}"
            }

        # Create calendar event
        event_data = build_calendar_event(page)
        event = create_calendar_event(calendar_token, event_data)
        if not event:
            return {
                "error": "Failed to create calendar event"
            }

        return {
            "message": "Successfully created calendar event",
            "event": {
                "title": event.get("summary", "Untitled Event"),
                "url": event.get("htmlLink")
            }
        }

    except Exception as e:
        logger.error(f"Error handling Notion update: {e}")
        return {
            "error": str(e)
        }
