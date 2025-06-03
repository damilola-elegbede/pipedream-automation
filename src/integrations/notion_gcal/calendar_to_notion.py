"""
Google Calendar to Notion Event Handler

This module processes Google Calendar event triggers, checks if they originated from Notion,
and extracts relevant details including the Notion Page ID from the location URL. It handles
data extraction, validation, and formatting for the Notion API.

The main handler function expects a Pipedream context object and returns a dictionary
containing the formatted data for Notion page updates.
"""

import logging
from typing import Any, Dict, Optional
from src.utils.common_utils import safe_get, extract_id_from_url

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_event_time(time_obj: Dict[str, Any]) -> Optional[str]:
    """
    Extracts the date/time from a Google Calendar event time object.

    Args:
        time_obj: The time object from the Google Calendar event

    Returns:
        The extracted date/time string or None if extraction fails
    """
    if time_obj is None:
        return None

    # Try dateTime first (for timed events)
    time_str = safe_get(time_obj, ["dateTime"])
    if time_str is not None:
        return time_str

    # Try date (for all-day events)
    time_str = safe_get(time_obj, ["date"])
    if time_str is not None:
        return time_str

    # Fallback to string representation of the object
    logger.warning(f"Could not find 'dateTime' or 'date' in time object: {time_obj}")
    return str(time_obj)

def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Processes Google Calendar event triggers, checks if they originated from Notion,
    and extracts relevant details including the Notion Page ID from the location URL.

    Args:
        pd: The Pipedream context object containing the trigger event data

    Returns:
        Dictionary containing formatted data for Notion page updates

    Raises:
        SystemExit: If the event is not Notion-related or if the Notion Page ID cannot be extracted
    """
    # --- 1. Extract and validate event data ---
    event_data = safe_get(pd.steps, ["trigger", "event"], default={})
    location = safe_get(event_data, ["location"])
    event_summary = safe_get(event_data, ["summary"], default="Untitled Event")

    # Validate if the event is Notion-related
    if not location or "https://www.notion.so/" not in location:
        exit_message = f"Event '{event_summary}' does not have a Notion URL in location. Skipping."
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    logger.info(f"Processing Notion-linked event: '{event_summary}'")

    # --- 2. Extract Notion Page ID ---
    page_id = extract_id_from_url(location)
    if not page_id:
        exit_message = f"Could not reliably extract Notion Page ID from location: '{location}' for event '{event_summary}'. Skipping."
        logger.warning(exit_message)
        pd.flow.exit(exit_message)
        return

    logger.info(f"Extracted Notion Page ID: {page_id}")

    # --- 3. Extract Start and End Times ---
    start_time = get_event_time(safe_get(event_data, ["start"], default={}))
    end_time = get_event_time(safe_get(event_data, ["end"], default={}))

    # Fallback end time to start time if missing
    if end_time is None or end_time == "{}":
        logger.warning("End time is missing. Using start time as fallback.")
        end_time = start_time

    logger.info(f"Start: {start_time}")
    logger.info(f"End: {end_time}")

    # --- 4. Prepare and Return Data ---
    return {
        "Subject": event_summary,
        "Start": start_time,
        "End": end_time,
        "Id": page_id
    } 