"""
Notion to Google Calendar Update Handler

This module processes Notion page updates and prepares data for updating
corresponding Google Calendar events. It handles data extraction, validation,
and formatting for the Google Calendar API.

The main handler function expects a Pipedream context object and returns a
dictionary containing the formatted data for updating a Google Calendar event.
"""

import logging
from typing import Any, Dict

from src.utils.common_utils import safe_get

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Processes Notion page update data from a Pipedream trigger for updating
    a Google Calendar event, ensuring safe access to data.

    Args:
        pd: The Pipedream context object containing the trigger event data

    Returns:
        Dictionary containing formatted data for Google Calendar event update

    Raises:
        SystemExit: If required data (due date or event ID) is missing
    """
    # --- 1. Safely extract data using the helper function ---
    trigger_event_page = safe_get(
        pd.steps, ["trigger", "event", "page"], default={})
    properties = safe_get(trigger_event_page, ["properties"], default={})

    # Task Name
    task_name = safe_get(
        properties, [
            "Task name", "title", 0, "plain_text"], default="Untitled Task")

    # Due Date information
    due_date_start = safe_get(properties, ["Due Date", "date", "start"])
    due_date_end = safe_get(properties, ["Due Date", "date", "end"])

    # Google Event ID - Crucial for update
    event_id = safe_get(
        properties, [
            "Google Event ID", "rich_text", 0, "plain_text"])

    # Notion Page URL
    notion_url = safe_get(trigger_event_page, ["url"])

    # --- 2. Check prerequisites for an update ---
    # Exit if Due Date is missing (required for calendar events)
    if due_date_start is None:
        exit_message = (
            f"Due Date is missing -- Cannot update event for task: '{task_name}'")
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # Exit if Google Event ID is missing (required to know which event to
    # update)
    if not event_id:
        exit_message = f"Google Event ID is missing -- Cannot update, should be a create event for task: '{task_name}'"
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # --- 3. Prepare data for event update (if checks passed) ---
    logger.info(
        f"Preparing to update event '{event_id}' for task: '{task_name}'")

    # Use start date as end date if end date is not provided
    final_end_date = due_date_end if due_date_end is not None else due_date_start

    # Log extracted details
    logger.info(f"Event ID: {event_id}")
    logger.info(f"Subject: {task_name}")
    logger.info(f"Start: {due_date_start}")
    logger.info(f"End: {final_end_date}")
    logger.info(f"Notion URL: {notion_url}")

    # --- 4. Structure the return object for Google Calendar update ---
    return {
        "GCal": {
            "Subject": task_name,
            "Start": due_date_start,
            "End": final_end_date,
            "Update": True,
            "EventId": event_id,
            "Url": notion_url,
            "Description": f"Notion Task: {task_name}\nLink: {
                notion_url or 'N/A'}",
        }}
