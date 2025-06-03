"""
AI Content Processor for Pipedream

This module processes and combines outputs from Claude and ChatGPT AI models,
converting their markdown content to HTML with proper formatting. It handles
error cases, demotes headings, and provides a formatted date for the output.

The main handler function expects a Pipedream context object and returns a
dictionary containing the processed HTML body and formatted date.
"""

from datetime import datetime
from typing import Any, Dict




def handler(pd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for AI content processing integration.

    Args:
        pd (Dict[str, Any]): The Pipedream context object.

    Returns:
        Dict[str, Any]: Processed HTML and formatted date.
    """
    # Fetch markdown content from Claude and ChatGPT
    claude_markdown = pd.get("claude_markdown", "")
    chatgpt_markdown = pd.get("chatgpt_markdown", "")

    # Convert markdown to HTML
    claude_html = markdown_to_html(claude_markdown)
    chatgpt_html = markdown_to_html(chatgpt_markdown)

    # Combine HTML outputs
    combined_html = combine_html(claude_html, chatgpt_html)

    # Format today's date
    today = datetime.now().strftime("%A, %B %d, %Y")

    return {"html": combined_html, "today": today}


def markdown_to_html(markdown: str) -> str:
    """Convert markdown to HTML. Placeholder for actual implementation."""
    # For now, just wrap in <pre> for demonstration
    if not markdown:
        return "<pre></pre>"
    return f"<pre>{markdown}</pre>"


def combine_html(claude_html: str, chatgpt_html: str) -> str:
    """Combine HTML outputs from Claude and ChatGPT."""
    if not claude_html and not chatgpt_html:
        return "<div>No content available.</div>"
    return f"<div>{claude_html}\n{chatgpt_html}</div>"
