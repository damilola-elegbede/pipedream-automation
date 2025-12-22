"""
Notion Task to Google Calendar Event Creator

Processes Notion task data from a Pipedream trigger and prepares it for
Google Calendar event creation. Skips tasks without due dates or those
that already have a Google Event ID (should be handled by update flow).

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
    Processes Notion task data from a Pipedream trigger, ensuring safe access
    to potentially missing data paths and handling create/update logic.
    """
    # --- 1. Safely extract data using the helper function ---
    trigger_event = safe_get(pd.steps, ["trigger", "event"], default={})
    properties = safe_get(trigger_event, ["properties"], default={})

    # Due Date information
    due_date_obj = safe_get(properties, ["Due Date", "date"])
    due_date_start = safe_get(due_date_obj, ["start"])
    due_date_end = safe_get(due_date_obj, ["end"])

    # Task Name information
    task_name_list = safe_get(properties, ["Task name", "title"], default=[])
    task_name = ""
    if task_name_list:
        task_name = safe_get(task_name_list, [0, "plain_text"], default="Untitled Task")
    else:
        task_name = "Untitled Task"

    # Google Event ID information
    google_event_id_list = safe_get(properties, ["Google Event ID", "rich_text"], default=[])

    # Other event details
    notion_id = safe_get(trigger_event, ["id"])
    notion_url = safe_get(trigger_event, ["url"])

    # --- 2. Check conditions and decide action ---

    # Exit if Due Date is missing
    if due_date_start is None:
        exit_message = f"Due Date is missing -- Skipping task: '{task_name}'"
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # Exit if it looks like an existing event (should be handled by an update flow)
    if google_event_id_list:
        exit_message = f"Google Event ID exists -- Should be an update, skipping creation for: '{task_name}'"
        logger.info(exit_message)
        pd.flow.exit(exit_message)
        return

    # --- 3. Prepare data for event creation (if checks above passed) ---
    logger.info(f"Preparing to create event for task: '{task_name}'")

    # Use start date as end date if end date is not provided
    final_end_date = due_date_end if due_date_end is not None else due_date_start

    # Log extracted details
    logger.info(f"Subject: {task_name}")
    logger.info(f"Start: {due_date_start}")
    logger.info(f"End: {final_end_date}")
    logger.info(f"Notion ID: {notion_id}")
    logger.info(f"Notion URL: {notion_url}")

    # Structure the return object for the next step (e.g., Google Calendar create event)
    ret_obj = {
        "GCal": {
            "Subject": task_name,
            "Start": due_date_start,
            "End": final_end_date,
            "Update": False,
            "NotionId": notion_id,
            "Url": notion_url,
            "Description": f"Notion Task: {task_name}\nLink: {notion_url or 'N/A'}"
        }
    }

    # --- 4. Return data for use in subsequent steps ---
    return ret_obj
