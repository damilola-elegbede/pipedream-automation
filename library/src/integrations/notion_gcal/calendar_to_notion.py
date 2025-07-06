"""
Google Calendar to Notion Event Handler

This module processes Google Calendar event triggers, checks if they originated from Notion,
and extracts relevant details including the Notion Page ID from the location URL. It handles
data extraction, validation, and formatting for the Notion API.

The main handler function expects a Pipedream context object and returns a dictionary
containing the formatted data for Notion page updates.
"""

import logging
import re
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from src.utils.structured_logger import get_pipedream_logger
from src.utils.error_enrichment import enrich_error

if TYPE_CHECKING:
    import pipedream

# Configure structured logging for Pipedream
logger = get_pipedream_logger('gcal_to_notion_event_handler')


def extract_notion_page_id(url: str) -> Optional[str]:
    """
    Extracts a Notion page ID from a URL.

    Args:
        url: The Notion page URL

    Returns:
        The extracted page ID or None if not found
    """
    if not url:
        return None
    match = re.search(r"([a-f0-9]{32})", url)
    return match.group(1) if match else None


def get_event_time(
    event: Optional[Dict[str, Any]],
    time_key: str = "dateTime"
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extracts start and end times from a Google Calendar event.

    Args:
        event: The Google Calendar event object
        time_key: The key to use for time extraction ("dateTime" or "date")

    Returns:
        Tuple of (start_time, end_time) as ISO format strings
    """
    if not event:
        return None, None

    start = event.get("start", {})
    end = event.get("end", {})

    # Handle all-day events
    if "date" in start:
        return start.get("date"), end.get("date")

    # Handle regular events
    start_time = start.get(time_key)
    end_time = end.get(time_key)

    return start_time, end_time


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Process Google Calendar event data and prepare it for Notion task creation.

    Args:
        pd: Pipedream context containing event data

    Returns:
        Dictionary with task details for Notion
    """
    with logger.step_context('process_gcal_event_for_notion'):
        # UNTESTED: event extraction logic for steps, event, dict
        event = None
        if hasattr(pd, "steps") and isinstance(pd.steps, dict):
            event = pd.steps.get("trigger", {}).get("event")
        elif hasattr(pd, "event"):
            event = pd.event
        elif isinstance(pd, dict):
            event = pd.get("event")
        
        logger.debug("Event extraction completed", event_found=event is not None)

    # Always build the result dict with all expected keys
    summary = event.get("summary", "Untitled Event") if event else "Untitled Event"
    location = event.get("location", "") if event else ""
    start_time, end_time = get_event_time(event) if event else ("", "")
    notion_page_id = None

    if location and "notion.so" in location:
        notion_page_id = extract_notion_page_id(location)

    result = {
        "Subject": summary,
        "Start": start_time or "",
        "End": end_time or (start_time or ""),
        "Url": event.get("htmlLink", "") if event else "",
        "Description": event.get("description", "") if event else ""
    }

    if notion_page_id:
        result["Id"] = notion_page_id
    elif location and "notion.so" in location:
        result["Error"] = "Invalid Notion URL format"

    # If no Notion link, call flow.exit if available, but still return result
    if (not location or "notion.so" not in location) and hasattr(pd, "flow"):
        if hasattr(pd.flow, "exit"):
            pd.flow.exit(f"Event '{summary}' does not have a Notion URL in location.")

    return result
