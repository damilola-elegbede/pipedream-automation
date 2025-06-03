"""
Notion Task to Google Calendar Event Converter

This module handles the conversion of Notion tasks to Google Calendar events.
It processes task data from a Notion trigger, validates the data, and prepares
it for Google Calendar event creation.

The main handler function expects a Pipedream context object and returns a
dictionary containing the formatted data for Google Calendar event creation.
"""

import logging
from src.utils.notion_utils import extract_notion_task_data

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(pd: "pipedream"):
    """
    Processes Notion task data from a Pipedream trigger, ensuring safe access
    to potentially missing data paths and handling create/update logic.

    Args:
        pd (pipedream): The Pipedream context object containing the trigger event

    Returns:
        dict: A dictionary containing the formatted data for Google Calendar event creation
    """
    # --- 1. Extract data using the utility function ---
    trigger_event = pd.steps.get("trigger", {}).get("event", {})
    task_data = extract_notion_task_data(trigger_event)

    # --- 2. Check conditions and decide action ---
    # Exit if Due Date is missing
    if task_data["due_date_start"] is None:
        exit_message = f"Due Date is missing -- Skipping task: '{task_data['task_name']}'"
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # Exit if it looks like an existing event (should be handled by an update flow)
    if task_data["event_id"]:
        exit_message = f"Google Event ID exists -- Should be an update, skipping creation for: '{task_data['task_name']}'"
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # --- 3. Prepare data for event creation (if checks above passed) ---
    logger.info(f"Preparing to create event for task: '{task_data['task_name']}'")

    # Use start date as end date if end date is not provided
    final_end_date = task_data["due_date_end"] if task_data["due_date_end"] is not None else task_data["due_date_start"]

    # Log extracted details
    logger.info(f"Subject: {task_data['task_name']}")
    logger.info(f"Start: {task_data['due_date_start']}")
    logger.info(f"End: {final_end_date}")
    logger.info(f"Notion ID: {task_data['notion_id']}")
    logger.info(f"Notion URL: {task_data['url']}")

    # Structure the return object for the next step (e.g., Google Calendar create event)
    ret_obj = {
        "GCal": {
            "Subject": task_data["task_name"],
            "Start": task_data["due_date_start"],
            "End": final_end_date,
            "Update": False,  # Explicitly setting as False for clarity
            "NotionId": task_data["notion_id"],
            "Url": task_data["url"],
            "Description": f"Notion Task: {task_data['task_name']}\nLink: {task_data['url'] or 'N/A'}"
        }
    }

    # --- 4. Return data for use in subsequent steps ---
    return ret_obj 