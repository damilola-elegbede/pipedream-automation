"""
Gmail Labeler for Processed Emails

This module adds a label to Gmail messages that have been
successfully processed by the Notion integration. It handles
authentication, label management, and message modification
through the Gmail API.

The main handler function expects a Pipedream context object
and returns a summary of labeled messages and any errors encountered.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import requests
from requests.exceptions import HTTPError, RequestException

from src.utils.common_utils import safe_get
from src.utils.retry_manager import with_retry
from src.utils.error_enrichment import enrich_error, format_error
from src.utils.structured_logger import get_pipedream_logger

if TYPE_CHECKING:
    import pipedream

# Configure structured logging for Pipedream
logger = get_pipedream_logger('gmail_label_processor')

# --- Configuration ---
PREVIOUS_STEP_NAME = "notion"
LABEL_NAME_TO_ADD = "notiontaskcreated"
GMAIL_API_BASE_URL = "https://www.googleapis.com/gmail/v1/users/me"
GMAIL_MODIFY_URL = f"{GMAIL_API_BASE_URL}/messages"
GMAIL_LABELS_URL = f"{GMAIL_API_BASE_URL}/labels"

# Error Messages
AUTH_ERROR_MSG = (
    "Gmail account not connected or input name is not 'gmail'. "
    "Please connect a Gmail account with 'gmail.modify' and "
    "'gmail.readonly' scopes."
)
STEP_DATA_ERROR_MSG = (
    f"Could not find return value from step '{PREVIOUS_STEP_NAME}'. "
    "Ensure the step name is correct and it exported data."
)
INVALID_DATA_ERROR_MSG = (
    f"Expected a dictionary with 'successful_mappings' key from step "
    f"'{PREVIOUS_STEP_NAME}', but received: {{}}"
)
INVALID_MAPPINGS_ERROR_MSG = (
    "Expected 'successful_mappings' to be a list, but received type {}."
)
NO_LABEL_ERROR_MSG = (
    f"Could not find Label ID for '{LABEL_NAME_TO_ADD}'. "
    "Please ensure the label exists in Gmail."
)


@with_retry(service='gmail')
def get_label_id(
    service_headers: Dict[str, str],
    label_name: str
) -> Optional[str]:
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
        logger.log_api_call('gmail', '/gmail/v1/users/me/labels', 'GET', label_name=label_name)
        response = requests.get(GMAIL_LABELS_URL, headers=service_headers)
        response.raise_for_status()
        logger.log_api_response('gmail', response.status_code, 0.0)
        
        labels_data = response.json()
        labels = labels_data.get("labels", [])
        for label in labels:
            if label.get("name", "").lower() == label_name.lower():
                label_id = label.get("id")
                logger.info(f"Found Label ID: {label_id}")
                return label_id
        logger.error(
            f"Error: Label '{label_name}' not found in user's labels."
        )
        return None
    except RequestException as e:
        enriched_error = enrich_error(e, service='gmail', operation='get_label_id', label_name=label_name)
        logger.log_error_with_context(enriched_error, operation='get_label_id')
        return None
    except Exception as e:
        enriched_error = enrich_error(e, service='gmail', operation='get_label_id', label_name=label_name)
        logger.log_error_with_context(enriched_error, operation='get_label_id')
        return None


def validate_previous_step_data(
    previous_step_output: Any
) -> Tuple[bool, Optional[str], Optional[List[Dict[str, Any]]]]:
    """
    Validate data from the previous step.

    Args:
        previous_step_output: Output data from the previous step

    Returns:
        Tuple of (is_valid, error_message, mappings)
    """
    if not isinstance(previous_step_output, dict):
        return (
            False,
            INVALID_DATA_ERROR_MSG.format(
                type(previous_step_output)
            ),
            None
        )
    mappings = previous_step_output.get("successful_mappings")
    if not mappings:
        return True, None, []
    if not isinstance(mappings, list):
        return (
            False,
            INVALID_MAPPINGS_ERROR_MSG.format(
                type(mappings)
            ),
            None
        )
    return True, None, mappings


def extract_message_ids(
    mappings: List[Dict[str, Any]]
) -> List[str]:
    """
    Extract valid message IDs from mappings.

    Args:
        mappings: List of mapping dictionaries

    Returns:
        List of valid message IDs
    """
    message_ids = []
    for item in mappings:
        if (
            isinstance(item, dict)
            and "gmail_message_id" in item
            and item["gmail_message_id"] is not None
        ):
            message_ids.append(item["gmail_message_id"])
        else:
            logger.warning(
                "Warning: Skipping item in 'successful_mappings' list as it's "
                f"not a dictionary, missing or None 'gmail_message_id': {item}"
            )
    return message_ids


@with_retry(service='gmail')
def add_label_to_message(
    headers: Dict[str, str],
    msg_id: str,
    label_id: str,
    index: int
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Add a label to a Gmail message.

    Args:
        headers: Request headers with authentication
        msg_id: ID of the message to label
        label_id: ID of the label to add
        index: Index of the message in the processing list

    Returns:
        Tuple of (success, error_details)
    """
    modify_url = f"{GMAIL_MODIFY_URL}/{msg_id}/modify"
    request_body = {"addLabelIds": [label_id]}
    try:
        logger.log_api_call('gmail', f'/gmail/v1/users/me/messages/{msg_id}/modify', 'POST', 
                           message_id=msg_id, label_id=label_id)
        response = requests.post(
            modify_url,
            headers=headers,
            json=request_body
        )
        response.raise_for_status()
        logger.log_api_response('gmail', response.status_code, 0.0)
        logger.info(f"Successfully added label to message ID: {msg_id}")
        return True, None
    except HTTPError as http_err:
        error_details = http_err.response.json() if http_err.response else {}
        error_field = error_details.get("error", {})
        error_message = (
            error_field.get("message", str(http_err))
            if isinstance(error_field, dict)
            else error_field or str(http_err)
        )
        status_code = http_err.response.status_code
        logger.error(
            "HTTP Error modifying message ID %s: %s - %s",
            msg_id,
            status_code,
            error_message
        )
        if status_code == 403:
            logger.error(
                "Error 403 (Forbidden): Check if the Gmail connection has "
                "the 'gmail.modify' scope enabled."
            )
        elif status_code == 400:
            logger.error(
                "Error 400 (Bad Request): Double-check the request body and "
                f"Label ID '{label_id}'. Is the message ID '{msg_id}' valid?"
            )
        elif status_code == 404:
            logger.error(
                f"Error 404 (Not Found): Message ID '{msg_id}' might be "
                "invalid or deleted."
            )
        return False, {
            "index": index + 1,
            "gmail_message_id": msg_id,
            "status_code": status_code,
            "error": error_message
        }
    except RequestException as req_err:
        logger.error(
            f"Request Exception modifying message ID {msg_id}: {req_err}"
        )
        return False, {
            "index": index + 1,
            "gmail_message_id": msg_id,
            "error": str(req_err)
        }
    except Exception as e:
        logger.error(f"Unexpected error modifying message ID {msg_id}: {e}")
        return False, {
            "index": index + 1,
            "gmail_message_id": msg_id,
            "error": str(e)
        }


def handler(pd) -> Dict[str, Any]:
    """
    Adds a label to Gmail messages that have been processed by Notion.
    Args:
        pd: The Pipedream context object or a dict
    Returns:
        Dictionary containing summary of labeled messages and any errors
    """
    # Get Gmail OAuth Token
    try:
        # Support both object and dict for pd.inputs and pd.steps
        if hasattr(pd, 'inputs'):
            inputs = pd.inputs
        else:
            inputs = pd.get('inputs', pd)
        if hasattr(pd, 'steps'):
            steps = pd.steps
        else:
            steps = pd.get('steps', pd)

        token = safe_get(inputs, ["gmail", "$auth", "oauth_access_token"])
        if not token:
            token = inputs.get("gmail_token")
        if not token:
            raise Exception("Gmail account not connected or input name is not 'gmail'. Please connect a Gmail account with 'gmail.modify' and 'gmail.readonly' scopes.")
    except Exception as e:
        raise e

    common_headers = {"Authorization": f"Bearer {token}"}

    # Get Data from Previous Step
    try:
        previous_step_output = safe_get(
            steps,
            [PREVIOUS_STEP_NAME, "$return_value"]
        )
        if not previous_step_output:
            previous_step_output = inputs.get("successful_mappings")
            if previous_step_output is not None:
                previous_step_output = {"successful_mappings": previous_step_output}
    except Exception:
        logger.error(STEP_DATA_ERROR_MSG)
        return {
            "status": "Completed",
            "error": "No data from previous step.",
            "labeled_messages": 0,
            "successfully_labeled_ids": [],
            "errors": []
        }

    # Validate Previous Step Data
    if previous_step_output is None:
        return {
            "status": "Completed",
            "error": "No data from previous step.",
            "labeled_messages": 0,
            "successfully_labeled_ids": [],
            "errors": []
        }
    is_valid, error_msg, mappings = validate_previous_step_data(
        previous_step_output
    )
    if not is_valid:
        return {
            "status": "Completed",
            "error": "Invalid data format from previous step.",
            "labeled_messages": 0,
            "successfully_labeled_ids": [],
            "errors": []
        }

    if not mappings:
        logger.info(
            "No successful mappings received from the previous step. "
            "Nothing to label."
        )
        return {
            "status": "Completed",
            "labeled_messages": 0,
            "successfully_labeled_ids": [],
            "errors": []
        }

    # Extract Message IDs and collect errors for invalid mappings
    message_ids_to_label = []
    errors = []
    for idx, item in enumerate(mappings):
        if (
            isinstance(item, dict)
            and "gmail_message_id" in item
            and item["gmail_message_id"] is not None
        ):
            message_ids_to_label.append(item["gmail_message_id"])
        else:
            errors.append({
                "index": idx + 1,
                "gmail_message_id": item.get("gmail_message_id") if isinstance(item, dict) else None,
                "error": "Invalid mapping: missing or None 'gmail_message_id'"
            })
            logger.warning(
                "Warning: Skipping item in 'successful_mappings' list as it's "
                f"not a dictionary, missing or None 'gmail_message_id': {item}"
            )

    if not message_ids_to_label:
        logger.warning(
            "No valid Gmail message IDs found in the "
            "'successful_mappings' data."
        )
        return {
            "status": "Completed",
            "labeled_messages": 0,
            "successfully_labeled_ids": [],
            "errors": errors
        }

    # Get Label ID
    target_label_id = get_label_id(common_headers, LABEL_NAME_TO_ADD)
    if not target_label_id:
        return {
            "status": "Completed",
            "error": NO_LABEL_ERROR_MSG,
            "labeled_messages": 0,
            "successfully_labeled_ids": [],
            "errors": errors
        }

    # Process Messages
    logger.info(
        f"Starting to add label '{LABEL_NAME_TO_ADD}' (ID: {target_label_id}) "
        f"to {len(message_ids_to_label)} message(s)..."
    )

    successfully_labeled_ids = []

    for index, msg_id in enumerate(message_ids_to_label):
        logger.info(
            f"\nProcessing message {index + 1}/{len(message_ids_to_label)} "
            f"(ID: {msg_id})..."
        )
        try:
            success, error = add_label_to_message(
                common_headers,
                msg_id,
                target_label_id,
                index
            )
            if success:
                successfully_labeled_ids.append(msg_id)
            elif error:
                errors.append(error)
        except requests.exceptions.HTTPError as http_err:
            # Robustly handle HTTPError with no response or invalid JSON
            error_message = str(http_err)
            status_code = None
            if hasattr(http_err, 'response') and http_err.response is not None:
                try:
                    error_json = http_err.response.json()
                    error_message = error_json.get('error', {}).get('message', error_message)
                    status_code = http_err.response.status_code
                except Exception:
                    error_message = str(http_err)
            errors.append({
                "index": index + 1,
                "gmail_message_id": msg_id,
                "status_code": status_code,
                "error": error_message
            })
        except Exception as e:
            errors.append({
                "index": index + 1,
                "gmail_message_id": msg_id,
                "error": str(e)
            })

    return {
        "status": "Completed",
        "labeled_messages": len(successfully_labeled_ids),
        "successfully_labeled_ids": successfully_labeled_ids,
        "errors": errors
    }
