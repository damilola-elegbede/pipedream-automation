"""
AI Content Processor

This module processes AI-generated content from Claude and ChatGPT,
handling content formatting and conversion.
"""

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

import requests

from src.utils.retry_manager import with_retry
from src.utils.error_enrichment import enrich_error, format_error
from src.utils.structured_logger import get_pipedream_logger

if TYPE_CHECKING:
    import pipedream

# Configure structured logging for Pipedream
logger = get_pipedream_logger('ai_content_processor')

# --- Configuration ---
API_URL = "https://api.openai.com/v1/chat/completions"


@with_retry(service='openai')
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
        logger.log_api_call('openai', '/v1/chat/completions', 'POST',
                           model='gpt-3.5-turbo',
                           input_length=len(markdown_text))
        
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
        
        logger.log_api_response('openai', response.status_code, 0)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        enriched_error = enrich_error(e, service='openai', operation='markdown_to_html')
        logger.log_error_with_context(enriched_error, operation='convert_markdown_to_html')
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
    with logger.step_context('process_ai_content'):
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
            enriched_error = enrich_error(e, service='openai', operation='process_content')
            formatted_error = format_error(enriched_error.original_error, service='openai')
            logger.log_error_with_context(enriched_error, operation='handler_main')
            return {
                "error": formatted_error
            }
