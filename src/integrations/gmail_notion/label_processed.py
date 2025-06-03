"""
Gmail Labeler for Processed Emails

This module adds a label to Gmail messages that have been successfully processed
by the Notion integration. It handles authentication, label management, and
message modification through the Gmail API.

The main handler function expects a Pipedream context object and returns a summary
of labeled messages and any errors encountered.
"""

import logging
import time
from typing import Any, Dict, Optional

import requests

from src.utils.common_utils import safe_get

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
PREVIOUS_STEP_NAME = "notion"
LABEL_NAME_TO_ADD = "notiontaskcreated"
GMAIL_MODIFY_URL_BASE = "https://www.googleapis.com/gmail/v1/users/me/messages/"
GMAIL_LABELS_URL = "https://www.googleapis.com/gmail/v1/users/me/labels"


def get_label_id(service_headers: Dict[str, str],
                 label_name: str) -> Optional[str]:
    """
    Fetches the ID of a Gmail label by its name.

    Args:
        service_headers: Headers containing authentication for Gmail API
        label_name: Name of the label to find

    Returns:
        Label ID if found, None otherwise
    """
    logger.info(f"Attempting to find Label ID for: '{label_name}'")
    try:
        response = requests.get(GMAIL_LABELS_URL, headers=service_headers)
        response.raise_for_status()
        labels_data = response.json()
        labels = labels_data.get("labels", [])
        for label in labels:
            if label.get("name", "").lower() == label_name.lower():
                label_id = label.get("id")
                logger.info(f"Found Label ID: {label_id}")
                return label_id
        logger.error(
            f"Error: Label '{label_name}' not found in user's labels.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching labels: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred fetching label ID: {e}")
        return None


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Adds a label to Gmail messages that have been processed by Notion.

    Args:
        pd: The Pipedream context object containing authentication and inputs

    Returns:
        Dictionary containing summary of labeled messages and any errors

    Raises:
        Exception: If Gmail account is not connected or authentication fails
    """
    # --- 1. Get Gmail OAuth Token ---
    try:
        token = safe_get(pd.inputs, ["gmail", "$auth", "oauth_access_token"])
    except Exception:
        raise Exception(
            "Gmail account not connected or input name is not 'gmail'. Please connect a Gmail account with 'gmail.modify' and 'gmail.readonly' scopes."
        )

    common_headers = {"Authorization": f"Bearer {token}"}

    # --- 2. Get Label ID ---
    target_label_id = get_label_id(common_headers, LABEL_NAME_TO_ADD)
    if not target_label_id:
        return {
            "error": f"Could not find Label ID for '{LABEL_NAME_TO_ADD}'. Please ensure the label exists in Gmail."
        }

    # --- 3. Get Data from Previous Step (Notion Step) ---
    try:
        previous_step_output = safe_get(
            pd.steps, [PREVIOUS_STEP_NAME, "$return_value"])
    except Exception:
        logger.error(
            f"Error: Could not find return value from step '{PREVIOUS_STEP_NAME}'. Ensure the step name is correct and it exported data."
        )
        return {"error": f"Could not find data from step {PREVIOUS_STEP_NAME}"}

    if (
        not isinstance(previous_step_output, dict)
        or "successful_mappings" not in previous_step_output
    ):
        logger.error(
            f"Error: Expected a dictionary with 'successful_mappings' key from step '{PREVIOUS_STEP_NAME}', but received: {
                type(previous_step_output)}")
        return {"error": "Invalid data format from previous step."}

    mappings_to_process = previous_step_output["successful_mappings"]

    if not mappings_to_process:
        logger.info(
            "No successful mappings received from the previous step. Nothing to label."
        )
        return {"status": "No data received", "labeled_messages": 0}

    if not isinstance(mappings_to_process, list):
        logger.error(
            f"Error: Expected 'successful_mappings' to be a list, but received type {
                type(mappings_to_process)}.")
        return {"error": "Invalid data format for successful_mappings."}

    # Extract message IDs using 'gmail_message_id' key
    message_ids_to_label = []
    for item in mappings_to_process:
        if isinstance(item, dict) and "gmail_message_id" in item:
            message_ids_to_label.append(item["gmail_message_id"])
        else:
            logger.warning(
                f"Warning: Skipping item in 'successful_mappings' list as it's not a dictionary or missing 'gmail_message_id': {item}")

    if not message_ids_to_label:
        logger.warning(
            "No valid Gmail message IDs found in the 'successful_mappings' data."
        )
        return {"status": "No valid message IDs", "labeled_messages": 0}

    # --- 4. Prepare API Request Body ---
    request_body = {"addLabelIds": [target_label_id]}
    logger.info(f"Prepared request body with Label ID: {request_body}")

    # --- 5. Loop Through Message IDs and Add Label ---
    successfully_labeled_ids = []
    errors = []
    logger.info(
        f"Starting to add label '{LABEL_NAME_TO_ADD}' (ID: {target_label_id}) to {
            len(message_ids_to_label)} message(s)...")

    for index, msg_id in enumerate(message_ids_to_label):
        logger.info(
            f"\nProcessing message {index + 1}/{len(message_ids_to_label)} (ID: {msg_id})..."
        )
        modify_url = f"{GMAIL_MODIFY_URL_BASE}{msg_id}/modify"

        try:
            logger.info(f"  Sending modify request to Gmail API...")
            response = requests.post(
                modify_url, headers=common_headers, json=request_body
            )
            response.raise_for_status()

            logger.info(f"  Successfully added label to message ID: {msg_id}")
            successfully_labeled_ids.append(msg_id)

        except requests.exceptions.HTTPError as http_err:
            error_details = http_err.response.json() if http_err.response else {}
            error_message = error_details.get(
                "error", {}).get(
                "message", str(http_err))
            status_code = http_err.response.status_code
            logger.error(
                f"  HTTP Error modifying message ID {msg_id}: {status_code} - {error_message}")
            if status_code == 403:
                logger.error(
                    "  Error 403 (Forbidden): Check if the Gmail connection has the 'gmail.modify' scope enabled."
                )
            if status_code == 400:
                logger.error(
                    f"  Error 400 (Bad Request): Double-check the request body and Label ID '{target_label_id}'. Is the message ID '{msg_id}' valid?")
            if status_code == 404:
                logger.error(
                    f"  Error 404 (Not Found): Message ID '{msg_id}' might be invalid or deleted.")

            errors.append(
                {
                    "index": index + 1,
                    "gmail_message_id": msg_id,
                    "status_code": status_code,
                    "error": error_message,
                }
            )
        except requests.exceptions.RequestException as req_err:
            logger.error(
                f"  Request Exception modifying message ID {msg_id}: {req_err}"
            )
            errors.append(
                {
                    "index": index + 1,
                    "gmail_message_id": msg_id,
                    "error": f"Request failed: {req_err}",
                }
            )
        except Exception as e:
            logger.error(
                f"  An unexpected error occurred modifying message ID {msg_id}: {e}")
            errors.append(
                {
                    "index": index + 1,
                    "gmail_message_id": msg_id,
                    "error": f"Unexpected error: {e}",
                }
            )

        time.sleep(0.2)  # Sleep for 200 milliseconds

    # --- 6. Return Summary ---
    logger.info("\n--- Labeling Complete ---")
    logger.info(
        f"Successfully labeled messages: {
            len(successfully_labeled_ids)}")
    logger.info(f"Errors encountered: {len(errors)}")

    return {
        "status": "Completed",
        "total_processed": len(message_ids_to_label),
        "successfully_labeled_ids": successfully_labeled_ids,
        "errors": errors,
    }
