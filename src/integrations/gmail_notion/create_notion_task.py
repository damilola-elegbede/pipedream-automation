"""
Gmail to Notion Task Creator

This module creates Notion tasks from Gmail emails, handling authentication,
task creation, and content formatting for the Notion API.
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
NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_PAGES_URL = f"{NOTION_API_BASE_URL}/pages"
NOTION_BLOCKS_URL = f"{NOTION_API_BASE_URL}/blocks"


def extract_email(text: str) -> Optional[str]:
    """
    Extract email address from a string.

    Args:
        text: String containing an email address

    Returns:
        Extracted email address or None if not found
    """
    if not text:
        return None
    return text.strip()


def build_notion_properties(
    title: str,
    email: Optional[str] = None,
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Build Notion properties dictionary for task creation.

    Args:
        title: Task title
        email: Optional email address
        due_date: Optional due date

    Returns:
        Dictionary of Notion properties
    """
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": title
                    }
                }
            ]
        }
    }

    if email:
        properties["Email"] = {
            "email": email
        }

    if due_date:
        properties["Due Date"] = {
            "date": {
                "start": due_date
            }
        }

    return properties


def get_image_url_from_html(html_content: str) -> Optional[str]:
    """
    Get image URL from HTML content using render API.

    Args:
        html_content: HTML content to process

    Returns:
        Image URL if found, None otherwise
    """
    try:
        response = requests.post(
            "https://api.render.com/v1/services/html-to-image/render",
            json={"html": html_content}
        )
        response.raise_for_status()
        return response.json().get("image_url")
    except Exception as e:
        logger.error(f"Error getting image URL: {e}")
        return None


def build_page_content_blocks(
    plain_text: str,
    image_url: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Build Notion page content blocks from text and optional image.

    Args:
        plain_text: Main text content
        image_url: Optional image URL

    Returns:
        List of Notion block objects
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
                            "content": plain_text
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


def handler(pd) -> Dict[str, Any]:
    """
    Create Notion task from Gmail email.
    Args:
        pd: The Pipedream context object or a dict
    Returns:
        Dictionary containing task details and any errors
    """
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

        # Get Notion OAuth Token (support both nested and flat dicts)
        token = safe_get(inputs, ["notion", "$auth", "oauth_access_token"])
        if not token:
            token = inputs.get("notion_auth")
        if not token:
            return {"error": "Notion authentication is missing. Please provide a Notion account or token."}

        # Get database_id (support both nested and flat dicts)
        database_id = inputs.get("database_id")
        if not database_id:
            database_id = safe_get(inputs, ["notion", "database_id"])
        if not database_id:
            return {"error": "Database ID is missing. Please provide a Notion database ID."}

        # Get email data from previous step or directly from pd
        email_data = safe_get(steps, ["gmail", "$return_value"])
        if email_data is None:
            email_data = inputs.get("email")
        if email_data is None:
            return {"error": "No email data provided"}

        # Extract email details
        subject = email_data.get("subject", "")
        sender = email_data.get("from", "")
        html_content = email_data.get("html", "")
        plain_text = email_data.get("text", "")
        if not plain_text and "body" in email_data:
            plain_text = email_data["body"]

        # Get image URL if HTML content exists
        image_url = None
        if html_content:
            image_url = get_image_url_from_html(html_content)

        # Build Notion properties
        properties = build_notion_properties(
            subject,
            extract_email(sender)
        )

        # Build page content
        blocks = build_page_content_blocks(plain_text, image_url)

        # Create Notion page
        try:
            response = requests.post(
                NOTION_PAGES_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json"
                },
                json={
                    "parent": {
                        "database_id": database_id
                    },
                    "properties": properties,
                    "children": blocks
                }
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            msg = str(e)
            if "401" in msg:
                return {"error": "Invalid Notion authentication"}
            if "404" in msg:
                return {"error": "Database not found"}
            return {"error": msg}

        data = response.json()
        return {
            "success": {
                "task_id": data.get("id"),
                "task_url": data.get("url"),
                "image_url": image_url
            }
        }

    except Exception as e:
        logger.error(f"Error creating Notion task: {e}")
        return {"error": str(e)}
