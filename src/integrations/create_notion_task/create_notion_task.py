"""
Create Notion Task from Gmail Email

This module creates Notion tasks from Gmail emails, handling authentication,
task creation, and content formatting for the Notion API.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from src.config.constants import (NOTION_API_BASE_URL, NOTION_PAGES_URL)

import requests
from bs4 import BeautifulSoup

from src.utils.common_utils import safe_get

if TYPE_CHECKING:
    import pipedream

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---


def extract_email(email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract email data from Gmail message.

    Args:
        email_data: Raw email data from Gmail API

    Returns:
        Dictionary containing extracted email data
    """
    headers = email_data.get("payload", {}).get("headers", [])
    subject = next(
        (h["value"] for h in headers if h["name"].lower() == "subject"),
        "No Subject"
    )
    sender = next(
        (h["value"] for h in headers if h["name"].lower() == "from"),
        "Unknown Sender"
    )

    # Get email body
    parts = email_data.get("payload", {}).get("parts", [])
    body = ""
    for part in parts:
        if part.get("mimeType") == "text/plain":
            body = part.get("body", {}).get("data", "")
            break

    return {
        "subject": subject,
        "sender": sender,
        "body": body
    }


def build_notion_properties(
    subject: str,
    sender: str,
    database_id: str
) -> Dict[str, Any]:
    """
    Build Notion properties for task creation.

    Args:
        subject: Email subject
        sender: Email sender
        database_id: Notion database ID

    Returns:
        Dictionary of Notion properties
    """
    return {
        "parent": {
            "database_id": database_id
        },
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": subject
                        }
                    }
                ]
            },
            "Source": {
                "rich_text": [
                    {
                        "text": {
                            "content": sender
                        }
                    }
                ]
            }
        }
    }


def get_image_url_from_html(html_content: str) -> Optional[str]:
    """
    Extract first image URL from HTML content.

    Args:
        html_content: HTML content to parse

    Returns:
        First image URL found or None
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        img_tag = soup.find("img")
        return img_tag.get("src") if img_tag else None
    except Exception as e:
        logger.error(f"Error extracting image URL: {e}")
        return None


def build_page_content_blocks(
    body: str,
    image_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Build Notion page content blocks.

    Args:
        body: Email body text
        image_url: Optional image URL to include

    Returns:
        List of Notion content blocks
    """
    blocks = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": body
                        }
                    }
                ]
            }
        }
    ]

    if image_url:
        blocks.append({
            "object": "block",
            "type": "image",
            "image": {
                "type": "external",
                "external": {
                    "url": image_url
                }
            }
        })

    return blocks


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Create Notion task from Gmail email.

    Args:
        pd: The Pipedream context object

    Returns:
        Dictionary containing created task data and any errors
    """
    try:
        # Get Notion OAuth Token
        notion_token = safe_get(
            pd.inputs,
            ["notion", "$auth", "oauth_access_token"]
        )
        if not notion_token:
            raise Exception(
                "Notion account not connected or input name is not 'notion'. "
                "Please connect a Notion account."
            )

        # Get email data
        email_data = pd.inputs.get("email_data")
        if not email_data:
            raise Exception("No email data provided")

        # Extract email content
        email = extract_email(email_data)
        if not email["body"]:
            raise Exception("No email body found")

        # Build Notion properties
        properties = build_notion_properties(
            email["subject"],
            email["sender"],
            pd.inputs["database_id"]
        )

        # Get image URL if available
        image_url = None
        if pd.inputs.get("include_image"):
            image_url = get_image_url_from_html(email["body"])

        # Build content blocks
        blocks = build_page_content_blocks(email["body"], image_url)

        # Create Notion page
        response = requests.post(
            NOTION_PAGES_URL,
            headers={
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            },
            json={
                **properties,
                "children": blocks
            }
        )
        response.raise_for_status()
        page_data = response.json()

        return {
            "message": "Successfully created Notion task",
            "task": {
                "title": email["subject"],
                "url": page_data.get("url")
            }
        }

    except Exception as e:
        logger.error(f"Error creating Notion task: {e}")
        return {
            "error": str(e)
        }
