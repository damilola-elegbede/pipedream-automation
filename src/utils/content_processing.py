"""
Content Processing Utilities

This module provides utilities for processing and transforming content,
including text formatting, HTML conversion, and content extraction.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple, Union

import markdown
from bs4 import BeautifulSoup

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def convert_markdown_to_html(markdown_text: str) -> str:
    """
    Convert markdown text to HTML.

    Args:
        markdown_text: Markdown text to convert

    Returns:
        Converted HTML
    """
    try:
        return markdown.markdown(markdown_text)
    except Exception as e:
        logger.error(f"Error converting markdown to HTML: {e}")
        return markdown_text


def extract_text_from_html(html_content: str) -> str:
    """
    Extract plain text from HTML content.

    Args:
        html_content: HTML content to extract from

    Returns:
        Extracted plain text
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        logger.error(f"Error extracting text from HTML: {e}")
        return html_content


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing line endings.

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    try:
        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text)
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        return text.strip()
    except Exception as e:
        logger.error(f"Error cleaning text: {e}")
        return text


def extract_metadata(content: str) -> Dict[str, Any]:
    """
    Extract metadata from content.

    Args:
        content: Content to extract metadata from

    Returns:
        Dictionary of metadata
    """
    try:
        metadata = {}
        # Extract title
        title_match = re.search(r"#\s*(.+)$", content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        # Extract tags
        tags_match = re.search(r"tags:\s*(.+)$", content, re.MULTILINE)
        if tags_match:
            metadata["tags"] = [tag.strip() for tag in tags_match.group(1).split(",")]
        return metadata
    except Exception as e:
        logger.error(f"Error extracting metadata: {e}")
        return {}


def format_content(content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Format content by cleaning and extracting metadata.

    Args:
        content: Content to format

    Returns:
        Tuple of (formatted content, metadata)
    """
    try:
        # Clean content
        cleaned_content = clean_text(content)
        # Extract metadata
        metadata = extract_metadata(cleaned_content)
        return cleaned_content, metadata
    except Exception as e:
        logger.error(f"Error formatting content: {e}")
        return content, {}


def combine_content(title: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Combine title, content, and metadata into a single string.

    Args:
        title: Content title
        content: Content body
        metadata: Optional metadata dictionary

    Returns:
        Combined content string
    """
    try:
        parts = [f"# {title}\n"]
        if metadata:
            if metadata.get("tags"):
                parts.append(f"tags: {', '.join(metadata['tags'])}\n")
        parts.append(content)
        return "\n".join(parts)
    except Exception as e:
        logger.error(f"Error combining content: {e}")
        return content


def get_content_from_path(
    data: dict, path_parts: List[Union[str, int]], step_name: str
) -> Optional[str]:
    """
    Safely get content from a nested dictionary using a path of keys/indices.

    Args:
        data (dict): The dictionary to traverse
        path_parts (List[Union[str, int]]): List of keys/indices to traverse
        step_name (str): Name of the step for error messages

    Returns:
        Optional[str]: The content if found, None if there was an error
    """
    current_level = data
    try:
        for part in path_parts:
            if isinstance(part, str):
                current_level = current_level[part]
            elif isinstance(part, int):
                if isinstance(current_level, list) and 0 <= part < len(
                    current_level
                ):
                    current_level = current_level[part]
                else:
                    raise IndexError(
                        f"Index {part} out of range for list in step '{step_name}' "
                        f"at path '{'.'.join(map(str, path_parts))}'. "
                        f"List length: {len(current_level) if isinstance(current_level, list) else 'N/A'}."
                    )
            else:
                raise TypeError(
                    f"Invalid path part type: {type(part)} in step '{step_name}' "
                    f"at path '{'.'.join(map(str, path_parts))}'"
                )

        content = current_level
        if content is None:
            print(
                f"Warning: Content from step '{step_name}' at path '{'.'.join(map(str, path_parts))}' is None."
            )
            return ""
        if not isinstance(content, str):
            print(
                f"Warning: Expected a string from step '{step_name}' at path '{'.'.join(map(str, path_parts))}', "
                f"but got {type(content)}. Attempting to convert."
            )
            return str(content)
        if not content.strip():
            print(
                f"Warning: Content from step '{step_name}' at path '{'.'.join(map(str, path_parts))}' is empty or whitespace."
            )
            return ""
        return content
    except (KeyError, IndexError, TypeError) as e:
        print(
            f"Error accessing data from step '{step_name}'. {str(e)} in path '{'.'.join(map(str, path_parts))}'"
        )
        return None
    except Exception as e:
        print(
            f"An unexpected error occurred accessing data from step '{step_name}' at path '{'.'.join(map(str, path_parts))}': {e}"
        )
        return None


def demote_headings(html_content: str) -> str:
    """
    Demotes HTML headings by one level (h1->h2, h2->h3, ..., h5->h6).

    Args:
        html_content (str): The HTML content to process

    Returns:
        str: The processed HTML content with demoted headings
    """
    if not html_content:
        return ""

    # Order of replacement is important to avoid multi-step demotion of the
    # same tag
    replacements = [
        (r"<(/?)h5\b(.*?)>", r"<\1h6\2>"),
        (r"<(/?)h4\b(.*?)>", r"<\1h5\2>"),
        (r"<(/?)h3\b(.*?)>", r"<\1h4\2>"),
        (r"<(/?)h2\b(.*?)>", r"<\1h3\2>"),
        (r"<(/?)h1\b(.*?)>", r"<\1h2\2>"),
    ]

    for pattern, replacement in replacements:
        html_content = re.sub(
            pattern, replacement, html_content, flags=re.IGNORECASE
        )

    return html_content
