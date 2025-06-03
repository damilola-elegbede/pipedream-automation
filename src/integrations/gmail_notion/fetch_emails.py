"""
Gmail Email Fetcher for Notion Integration

This module fetches emails from Gmail based on specific labels and prepares them
for processing by the Notion integration. It handles authentication, message
retrieval, and content extraction from Gmail messages.

The main handler function expects a Pipedream context object and returns a list
of email details including headers, body content, and metadata.
"""

import requests
import time
import base64
import logging
from typing import Any, Dict, List, Optional
from src.utils.common_utils import safe_get

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_header_value(headers: List[Dict[str, str]], name: str) -> Optional[str]:
    for header in headers:
        if safe_get(header, "name", "").lower() == name.lower():
            return safe_get(header, "value")
    return None

def get_body_parts(parts: List[Dict[str, Any]]) -> Dict[str, str]:
    result = {"text": "", "html": ""}
    for part in parts:
        mime_type = safe_get(part, ["mimeType"])
        if mime_type == "text/plain":
            data = safe_get(part, ["body", "data"])
            if data:
                result["text"] = base64.urlsafe_b64decode(data).decode()
        elif mime_type == "text/html":
            data = safe_get(part, ["body", "data"])
            if data:
                result["html"] = base64.urlsafe_b64decode(data).decode()
        elif safe_get(part, ["parts"]):
            nested_result = get_body_parts(safe_get(part, ["parts"], []))
            result["text"] += nested_result["text"]
            result["html"] += nested_result["html"]
    return result

def handler(pd: "pipedream") -> List[Dict[str, Any]]:
    """
    Processes Gmail messages based on specified labels and extracts their content.

    Args:
        pd: The Pipedream context object containing authentication and inputs

    Returns:
        List of dictionaries containing email details including headers and content

    Raises:
        Exception: If Gmail account is not connected or authentication fails
    """
    access_token = safe_get(pd.steps, ["oauth", "access_token"])
    if not access_token:
        logger.error("No access token found in Pipedream context")
        return []
    required_labels = ["INBOX", "UNREAD"]
    excluded_labels = ["SENT", "DRAFT", "SPAM", "TRASH"]
    search_query = " ".join([f"label:{label}" for label in required_labels] + [f"-label:{label}" for label in excluded_labels])
    message_ids = []
    page_token = None
    while True:
        try:
            list_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            params = {"q": search_query, "maxResults": 100}
            if page_token:
                params["pageToken"] = page_token
            response = requests.get(list_url, headers={"Authorization": f"Bearer {access_token}"}, params=params)
            response.raise_for_status()
            data = response.json()
            messages = safe_get(data, ["messages"], [])
            message_ids.extend([msg["id"] for msg in messages])
            page_token = safe_get(data, ["nextPageToken"])
            if not page_token:
                break
            time.sleep(0.1)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching message list: {e}")
            break
    email_details = []
    for msg_id in message_ids:
        try:
            msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
            response = requests.get(msg_url, headers={"Authorization": f"Bearer {access_token}"})
            response.raise_for_status()
            message = response.json()
            headers = safe_get(message, ["payload", "headers"], [])
            subject = get_header_value(headers, "Subject") or "No Subject"
            from_addr = get_header_value(headers, "From") or "Unknown Sender"
            to_addr = get_header_value(headers, "To") or "Unknown Recipient"
            date = get_header_value(headers, "Date") or "Unknown Date"
            body_parts = get_body_parts([safe_get(message, ["payload"], {})])
            gmail_url = f"https://mail.google.com/mail/u/0/#inbox/{msg_id}"
            email_details.append({
                "id": msg_id,
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "text_content": body_parts["text"],
                "html_content": body_parts["html"],
                "url": gmail_url
            })
            time.sleep(0.1)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching message {msg_id}: {e}")
            continue
    logger.info(f"Found {len(email_details)} matching emails")
    return email_details 