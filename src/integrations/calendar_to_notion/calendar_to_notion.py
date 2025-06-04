"""
Calendar to Notion Integration

This module syncs calendar events to Notion, handling authentication,
event retrieval, and task creation.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import requests

from src.utils.common_utils import safe_get

if TYPE_CHECKING:
    import pipedream

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"
CALENDAR_EVENTS_URL = f"{CALENDAR_API_BASE_URL}/calendars/primary/events"
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_PAGES_URL = f"{NOTION_API_BASE_URL}/pages"


def get_calendar_events(
    token: str,
    time_min: str,
    time_max: str
) -> List[Dict[str, Any]]:
    """
    Get calendar events from Google Calendar API.

    Args:
        token: Google Calendar API access token
        time_min: Start time for event search
        time_max: End time for event search

    Returns:
        List of calendar events
    """
    try:
        response = requests.get(
            CALENDAR_EVENTS_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "timeMin": time_min,
                "timeMax": time_max,
                "singleEvents": True,
                "orderBy": "startTime"
            }
        )
        response.raise_for_status()
        return response.json().get("items", [])
    except Exception as e:
        logger.error(f"Error getting calendar events: {e}")
        return []


def build_notion_properties(
    event: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build Notion properties from calendar event.

    Args:
        event: Calendar event data

    Returns:
        Dictionary of Notion properties
    """
    start = event.get("start", {}).get("dateTime", "")
    end = event.get("end", {}).get("dateTime", "")
    location = event.get("location", "")

    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": event.get("summary", "Untitled Event")
                    }
                }
            ]
        }
    }

    if start:
        properties["Start Time"] = {
            "date": {
                "start": start
            }
        }

    if end:
        properties["End Time"] = {
            "date": {
                "start": end
            }
        }

    if location:
        properties["Location"] = {
            "rich_text": [
                {
                    "text": {
                        "content": location
                    }
                }
            ]
        }

    return properties


def create_notion_page(
    token: str,
    database_id: str,
    properties: Dict[str, Any],
    description: str
) -> Optional[Dict[str, Any]]:
    """
    Create a new page in Notion.

    Args:
        token: Notion API access token
        database_id: Notion database ID
        properties: Page properties
        description: Page description

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
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": description
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error creating Notion page: {e}")
        return None


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Sync calendar events to Notion.

    Args:
        pd: The Pipedream context object

    Returns:
        Dictionary containing sync results and any errors
    """
    try:
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

        # Get time range from input
        time_min = pd.inputs.get("time_min")
        time_max = pd.inputs.get("time_max")
        if not time_min or not time_max:
            raise Exception("time_min and time_max are required inputs")

        # Get calendar events
        events = get_calendar_events(calendar_token, time_min, time_max)
        if not events:
            return {
                "message": "No events found in the specified time range",
                "events": []
            }

        # Create Notion pages
        created_pages = []
        for event in events:
            properties = build_notion_properties(event)
            description = event.get("description", "")
            page = create_notion_page(
                notion_token,
                pd.inputs["database_id"],
                properties,
                description
            )
            if page:
                created_pages.append({
                    "title": event.get("summary", "Untitled Event"),
                    "url": page.get("url")
                })

        return {
            "message": f"Successfully created {len(created_pages)} pages",
            "events": created_pages
        }

    except Exception as e:
        logger.error(f"Error syncing calendar to Notion: {e}")
        return {
            "error": str(e)
        }
