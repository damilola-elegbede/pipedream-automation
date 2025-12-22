"""
Notion Update to Google Calendar Update

Processes Notion page update events and prepares data for updating the
corresponding Google Calendar event. Only processes tasks that already
have a Google Event ID.

Usage: Copy-paste into a Pipedream Python step
"""
import logging

# Configure logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def safe_get(data, keys, default=None):
    """
    Safely accesses nested dictionary keys or list indices.

    Args:
        data: The dictionary or list to access.
        keys: A list of keys/indices representing the path.
        default: The value to return if the path is not found or an error occurs.

    Returns:
        The value at the nested path or the default value.
    """
    current = data
    for key in keys:
        try:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                if isinstance(key, int) and 0 <= key < len(current):
                    current = current[key]
                else:
                    logger.warning(f"Invalid list index '{key}' for list: {current}")
                    return default
            else:
                logger.warning(f"Cannot access key '{key}' in non-dict/list item: {current}")
                return default

            if current is None:
                return default

        except (TypeError, IndexError) as e:
            logger.warning(f"Error accessing key '{key}': {e}")
            return default
    return current


def handler(pd: "pipedream"):
    """
    Processes Notion page update data from a Pipedream trigger for updating
    a Google Calendar event, ensuring safe access to data.
    """
    # --- 1. Safely extract data using the helper function ---
    # Base path adjustments: using ["page"] where appropriate
    trigger_event_page = safe_get(pd.steps, ["trigger", "event", "page"], default={})
    properties = safe_get(trigger_event_page, ["properties"], default={})

    # Task Name
    task_name = safe_get(properties, ["Task name", "title", 0, "plain_text"], default="Untitled Task")

    # Due Date information
    due_date_start = safe_get(properties, ["Due Date", "date", "start"])
    due_date_end = safe_get(properties, ["Due Date", "date", "end"])

    # Google Event ID - Crucial for update
    event_id = safe_get(properties, ["Google Event ID", "rich_text", 0, "plain_text"])

    # Notion Page URL
    notion_url = safe_get(trigger_event_page, ["url"])

    # --- 2. Check prerequisites for an update ---

    # Exit if Due Date is missing (required for calendar events)
    if due_date_start is None:
        exit_message = f"Due Date is missing -- Cannot update event for task: '{task_name}'"
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # Exit if Google Event ID is missing (required to know *which* event to update)
    if not event_id:
        exit_message = f"Google Event ID is missing -- Cannot update, should be a create event for task: '{task_name}'"
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # --- 3. Prepare data for event update (if checks passed) ---
    logger.info(f"Preparing to update event '{event_id}' for task: '{task_name}'")

    # Use start date as end date if end date is not provided
    final_end_date = due_date_end if due_date_end is not None else due_date_start

    # Log extracted details
    logger.info(f"Event ID: {event_id}")
    logger.info(f"Subject: {task_name}")
    logger.info(f"Start: {due_date_start}")
    logger.info(f"End: {final_end_date}")
    logger.info(f"Notion URL: {notion_url}")

    # Structure the return object for the next step (e.g., Google Calendar update event)
    ret_obj = {
        "GCal": {
            "Subject": task_name,
            "Start": due_date_start,
            "End": final_end_date,
            "Update": True,
            "EventId": event_id,
            "Url": notion_url,
            "Description": f"Notion Task: {task_name}\nLink: {notion_url or 'N/A'}"
        }
    }

    # --- 4. Return data for use in subsequent steps ---
    return ret_obj
