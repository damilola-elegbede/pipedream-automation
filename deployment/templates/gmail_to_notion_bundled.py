"""
Gmail to Notion Task Creator
Generated: 2025-07-05 17:21:23
Bundled for Pipedream deployment
"""

import logging
import json
import requests
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from requests.exceptions import HTTPError, RequestException

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# === EMBEDDED DEPENDENCIES ===
# === CONSTANTS ===
NOTION_API_VERSION = "2022-06-28"
NOTION_API_BASE_URL = "https://api.notion.com/v1"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
}
NOTION_HEADERS = {
    **DEFAULT_HEADERS,
    "Notion-Version": NOTION_API_VERSION,
}
NOTION_PAGES_URL = f"{NOTION_API_BASE_URL}/pages"
NOTION_BLOCKS_URL = f"{NOTION_API_BASE_URL}/blocks"
ERROR_INVALID_INPUT = "Required input field '{}' is missing"
SUCCESS_CREATED = "Successfully created {}"

# === UTILITY FUNCTIONS ===
# From src/utils/common_utils.py
def safe_get(obj, path, default=None):
    """
    Safely get a value from a nested dictionary or list using a path.
    Args:
        obj: Dictionary or list to get value from
        path: List of keys/indices or a single key/index
        default: Value to return if path is not found
    Returns:
        Value at path or default if not found
    """
    if obj is None:
        return default
    if path is None or path == []:
        return default
    if not isinstance(path, list):
        path = [path]
    current = obj
    try:
        for key in path:
            if isinstance(current, dict):
                current = current.get(key, default)
            elif isinstance(current, list) and isinstance(key, int):
                if 0 <= key < len(current):
                    current = current[key]
                else:
                    return default
            else:
                return default
        return current
    except Exception:
        return default




# === MAIN MODULE ===
"""
Gmail to Notion Task Creator

This module creates Notion tasks from Gmail emails, handling authentication,
task creation, and content formatting for the Notion API.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

import requests
from requests.exceptions import HTTPError, RequestException

    NOTION_API_BASE_URL,
    NOTION_PAGES_URL,
    NOTION_BLOCKS_URL,
    NOTION_HEADERS,
    ERROR_INVALID_INPUT,
    SUCCESS_CREATED
)

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


@pipedream_error_handler
def handler(pd) -> Dict[str, Any]:
    """
    Create Notion task from Gmail email.
    Args:
        pd: The Pipedream context object or a dict
    Returns:
        Dictionary containing task details and any errors
    """
    # Extract inputs based on pd structure
    if hasattr(pd, 'inputs'):
        inputs = pd.inputs
    else:
        inputs = pd.get('inputs', pd)
    if hasattr(pd, 'steps'):
        steps = pd.steps
    else:
        steps = pd.get('steps', pd)

    # Validate and extract Notion authentication
    token = validate_notion_auth(pd)
    
    # Validate required inputs
    required_fields = ["database_id"]
    validated_inputs = validate_pipedream_inputs(pd, required_fields)
    database_id = validated_inputs["database_id"]

    # Get email data from previous step or directly from pd
    email_data = safe_get(steps, ["gmail", "$return_value"])
    if email_data is None:
        email_data = inputs.get("email")
    if email_data is None:
        raise ValueError("No email data provided")

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
    headers = {
        **NOTION_HEADERS,
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(
        NOTION_PAGES_URL,
        headers=headers,
        json={
            "parent": {
                "database_id": database_id
            },
            "properties": properties,
            "children": blocks
        }
    )
    
    # Handle API response
    data = handle_api_response(response, "Notion")
    
    return {
        "success": {
            "task_id": data.get("id"),
            "task_url": data.get("url"),
            "image_url": image_url
        }
    }

# === PIPEDREAM HANDLER ===
# The handler function is the entry point for Pipedream
# Usage: return handler(pd)
