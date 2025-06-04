"""
Gmail Email Fetcher for Notion Integration

This module fetches emails from Gmail based on specific labels and prepares them
for processing by the Notion integration. It handles authentication, message
retrieval, and content extraction from Gmail messages.

The main handler function expects a Pipedream context object and returns a list
of email details including headers, body content, and metadata.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import requests
from requests.exceptions import HTTPError, RequestException

from src.utils.common_utils import safe_get

if TYPE_CHECKING:
    import pipedream

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
GMAIL_MESSAGES_URL = f"{GMAIL_API_BASE_URL}/messages"
GMAIL_THREADS_URL = f"{GMAIL_API_BASE_URL}/threads"
MAX_RESULTS = 10


def get_header_value(headers: List[Dict[str, str]], name: str) -> Optional[str]:
    """
    Extracts a header value from a list of email headers.

    Args:
        headers: List of header dictionaries containing name-value pairs
        name: Name of the header to find (case-insensitive)

    Returns:
        Header value if found, None otherwise
    """
    if not headers:
        return None

    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value")

    return None


def process_message_part(
    part: Dict[str, Any],
    plain_text: Optional[str],
    html_content: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Process a single message part to extract text content.

    Args:
        part: Message part data
        plain_text: Current plain text content
        html_content: Current HTML content

    Returns:
        Tuple of (plain_text, html_content)
    """
    mime_type = part.get("mimeType", "").lower()
    data = None

    if "body" in part and isinstance(part["body"], dict):
        data = part["body"].get("data")
    elif "data" in part:
        data = part["data"]

    if mime_type == "text/plain" and not plain_text:
        plain_text = data
    elif mime_type == "text/html" and not html_content:
        html_content = data
    elif "parts" in part:
        for subpart in part["parts"]:
            plain_text, html_content = process_message_part(
                subpart,
                plain_text,
                html_content
            )

    return plain_text, html_content


def get_body_parts(message: Dict[str, Any]) -> Tuple[str, str]:
    """
    Extracts plain text and HTML content from an email message.

    Args:
        message: The email message data containing payload and parts

    Returns:
        Tuple of (plain_text, html_content), with empty strings as defaults
    """
    plain_text = None
    html_content = None

    if message and "payload" in message:
        plain_text, html_content = process_message_part(
            message["payload"],
            plain_text,
            html_content
        )

    return plain_text or "", html_content or ""


def fetch_messages(token: str) -> List[Dict[str, Any]]:
    """
    Fetch list of messages from Gmail API.

    Args:
        token: Gmail OAuth access token

    Returns:
        List of message metadata
    """
    try:
        response = requests.get(
            f"{GMAIL_API_BASE_URL}/messages?maxResults={MAX_RESULTS}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json().get("messages", [])

    except RequestException as e:
        logger.error(f"Error fetching messages: {e}")
        return []


def fetch_message_details(token: str, message_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch detailed message data from Gmail API.

    Args:
        token: Gmail OAuth access token
        message_id: ID of the message to fetch

    Returns:
        Message data if successful, None otherwise
    """
    try:
        response = requests.get(
            f"{GMAIL_API_BASE_URL}/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()

    except RequestException as e:
        logger.error(f"Error fetching message {message_id}: {e}")
        return None


def process_message(
    token: str,
    message: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Process a single message and extract relevant data.

    Args:
        token: Gmail OAuth access token
        message: Message metadata

    Returns:
        Processed message data if successful, None otherwise
    """
    try:
        msg_id = message["id"]
        msg_data = fetch_message_details(token, msg_id)
        if not msg_data:
            return None

        headers_list = msg_data.get("payload", {}).get("headers", [])
        subject = get_header_value(headers_list, "Subject") or "No Subject"
        sender = get_header_value(headers_list, "From") or "Unknown Sender"
        receiver = get_header_value(headers_list, "To") or "Unknown Receiver"

        plain_text, html_content = get_body_parts(msg_data)

        return {
            "message_id": msg_id,
            "subject": subject,
            "sender": sender,
            "receiver": receiver,
            "plain_text_body": plain_text,
            "html_body": html_content,
            "url": f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"
        }

    except Exception as e:
        logger.error(f"Error processing message {message.get('id')}: {e}")
        return None


def handler(pd: "pipedream") -> List[Dict[str, Any]]:
    """
    Fetches emails from Gmail and prepares them for processing.

    Args:
        pd: The Pipedream context object containing authentication

    Returns:
        List of processed email data
    """
    try:
        token = safe_get(pd.inputs, ["gmail", "$auth", "oauth_access_token"])
        if not token:
            raise Exception(
                "Gmail account not connected or input name is not 'gmail'. "
                "Please connect a Gmail account."
            )

        query = pd.inputs.get("query", "in:inbox")
        max_results = pd.inputs.get("max_results", 10)

        response = requests.get(
            GMAIL_MESSAGES_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "maxResults": max_results}
        )
        response.raise_for_status()
        messages_data = response.json()

        processed_emails = []
        for message in messages_data.get("messages", []):
            processed = process_message(token, message)
            if processed:
                processed_emails.append(processed)

        return processed_emails

    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return []
