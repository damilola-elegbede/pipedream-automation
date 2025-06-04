"""
Fetch Emails from Gmail

This module fetches emails from Gmail using the Gmail API, handling
authentication, message retrieval, and content extraction.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

import requests

from src.utils.common_utils import safe_get

if TYPE_CHECKING:
    import pipedream

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
GMAIL_MESSAGES_URL = "https://www.googleapis.com/gmail/v1/users/me/messages"
GMAIL_THREADS_URL = "https://www.googleapis.com/gmail/v1/users/me/threads"


def get_message_details(token: str, message_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed message data from Gmail API.

    Args:
        token: Gmail API access token
        message_id: Gmail message ID

    Returns:
        Message data or None if error
    """
    try:
        response = requests.get(
            f"{GMAIL_MESSAGES_URL}/{message_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting message details: {e}")
        return None


def get_thread_details(token: str, thread_id: str) -> Optional[Dict[str, Any]]:
    """
    Get thread data from Gmail API.

    Args:
        token: Gmail API access token
        thread_id: Gmail thread ID

    Returns:
        Thread data or None if error
    """
    try:
        response = requests.get(
            f"{GMAIL_THREADS_URL}/{thread_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error getting thread details: {e}")
        return None


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Fetch emails from Gmail.

    Args:
        pd: The Pipedream context object

    Returns:
        Dictionary containing fetched emails and any errors
    """
    try:
        # Get Gmail OAuth Token
        gmail_token = safe_get(
            pd.inputs,
            ["gmail", "$auth", "oauth_access_token"]
        )
        if not gmail_token:
            raise Exception(
                "Gmail account not connected or input name is not 'gmail'. "
                "Please connect a Gmail account."
            )

        # Get search parameters
        query = pd.inputs.get("query", "in:inbox")
        max_results = pd.inputs.get("max_results", 10)

        # Fetch messages
        response = requests.get(
            GMAIL_MESSAGES_URL,
            headers={"Authorization": f"Bearer {gmail_token}"},
            params={
                "q": query,
                "maxResults": max_results
            }
        )
        response.raise_for_status()
        messages = response.json().get("messages", [])

        # Get message details
        email_data = []
        for message in messages:
            message_details = get_message_details(gmail_token, message["id"])
            if message_details:
                email_data.append(message_details)

        return {
            "message": f"Successfully fetched {len(email_data)} emails",
            "emails": email_data
        }

    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        return {
            "error": str(e)
        }
