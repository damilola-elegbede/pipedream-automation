"""
Notion to Google Calendar Update Handler

This module processes Notion page updates and prepares data for updating
corresponding Google Calendar events. It handles data extraction, validation,
and formatting for the Google Calendar API.

The main handler function expects a Pipedream context object and returns a
dictionary containing the formatted data for updating a Google Calendar event.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import pipedream

from src.utils.common_utils import safe_get

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def validate_required_data(
    task_name: str,
    due_date_start: Optional[str],
    event_id: Optional[str]
) -> Optional[str]:
    """
    Validate required data for updating a Google Calendar event.

    Args:
        task_name: The name of the Notion task
        due_date_start: The start date of the task
        event_id: The Google Calendar event ID

    Returns:
        Error message if validation fails, None otherwise
    """
    if due_date_start is None:
        return f"Due Date is missing -- Cannot update event for task: '{task_name}'"

    if not event_id:
        return (
            f"Google Event ID is missing -- Cannot update, "
            f"should be a create event for task: '{task_name}'"
        )

    return None


def extract_task_data(pd: "pipedream") -> Dict[str, Any]:
    """
    Extract task data from the Pipedream context.

    Args:
        pd: The Pipedream context object

    Returns:
        Dictionary containing extracted task data
    """
    trigger_event_page = safe_get(
        pd.steps, ["trigger", "event", "page"], default={}
    )
    properties = safe_get(trigger_event_page, ["properties"], default={})

    return {
        "task_name": safe_get(
            properties,
            ["Task name", "title", 0, "plain_text"],
            default="Untitled Task",
        ),
        "due_date_start": safe_get(
            properties, ["Due Date", "date", "start"]
        ),
        "due_date_end": safe_get(
            properties, ["Due Date", "date", "end"]
        ),
        "event_id": safe_get(
            properties,
            ["Google Event ID", "rich_text", 0, "plain_text"]
        ),
        "notion_url": safe_get(trigger_event_page, ["url"])
    }


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Process Notion page update data for Google Calendar event update.

    Args:
        pd: The Pipedream context object containing the trigger event data

    Returns:
        Dictionary containing formatted data for Google Calendar event update

    Raises:
        SystemExit: If required data (due date or event ID) is missing
    """
    # Extract task data
    task_data = extract_task_data(pd)

    # Validate required data
    error_msg = validate_required_data(
        task_data["task_name"],
        task_data["due_date_start"],
        task_data["event_id"]
    )

    if error_msg:
        logger.info(error_msg)
        pd.flow.exit(error_msg)
        return {}

    # Log update preparation
    logger.info(
        f"Preparing to update event '{task_data['event_id']}' "
        f"for task: '{task_data['task_name']}'"
    )

    # Use start date as end date if end date is not provided
    final_end_date = (
        task_data["due_date_end"]
        if task_data["due_date_end"] is not None
        else task_data["due_date_start"]
    )

    # Log extracted details
    logger.info(f"Event ID: {task_data['event_id']}")
    logger.info(f"Subject: {task_data['task_name']}")
    logger.info(f"Start: {task_data['due_date_start']}")
    logger.info(f"End: {final_end_date}")
    logger.info(f"Notion URL: {task_data['notion_url']}")

    # Structure the return object for Google Calendar update
    return {
        "GCal": {
            "Subject": task_data["task_name"],
            "Start": task_data["due_date_start"],
            "End": final_end_date,
            "Update": True,
            "EventId": task_data["event_id"],
            "Url": task_data["notion_url"],
            "Description": (
                f"Notion Task: {task_data['task_name']}\n"
                f"Link: {task_data['notion_url'] or 'N/A'}"
            ),
        }
    }
