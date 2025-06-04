"""
AI Content Processor

This module processes AI-generated content from Claude and ChatGPT,
handling content formatting and conversion.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

import requests

if TYPE_CHECKING:
    import pipedream

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Configuration ---
API_URL = "https://api.openai.com/v1/chat/completions"


def convert_markdown_to_html(markdown_text: str, pd: "pipedream") -> str:
    """
    Convert markdown text to HTML using OpenAI API.

    Args:
        markdown_text: Markdown text to convert
        pd: The Pipedream context object

    Returns:
        Converted HTML
    """
    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {pd.inputs['openai_api_key']}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "Convert the following markdown to HTML. "
                        "Return only the HTML without any explanation."
                    },
                    {
                        "role": "user",
                        "content": markdown_text
                    }
                ]
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Error converting markdown to HTML: {e}")
        return markdown_text


def combine_html_content(
    title: str,
    content: str,
    image_url: Optional[str] = None
) -> str:
    """
    Combine title, content, and optional image into HTML format.

    Args:
        title: Content title
        content: Main content
        image_url: Optional image URL

    Returns:
        Combined HTML content
    """
    html = f"<h1>{title}</h1>\n{content}"
    if image_url:
        html = f'<img src="{image_url}" alt="{title}">\n{html}'
    return html


def handler(pd: "pipedream") -> Dict[str, Any]:
    """
    Process AI-generated content.

    Args:
        pd: The Pipedream context object

    Returns:
        Dictionary containing processed content and any errors
    """
    try:
        # Get content from input
        content = pd.inputs.get("content")
        if not content:
            raise Exception("No content provided")

        # Extract title and content
        title = content.get("title", "Untitled")
        markdown_content = content.get("content", "")
        image_url = content.get("image_url")

        # Convert markdown to HTML
        html_content = convert_markdown_to_html(markdown_content, pd)

        # Combine content
        final_content = combine_html_content(title, html_content, image_url)

        return {
            "message": "Successfully processed content",
            "content": {
                "title": title,
                "html": final_content
            }
        }

    except Exception as e:
        logger.error(f"Error processing content: {e}")
        return {
            "error": str(e)
        }
