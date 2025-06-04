"""
Common Utilities

This module provides common utility functions used across the project.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union

# Configure basic logging for Pipedream
logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


def format_error_message(error: Union[str, Exception]) -> str:
    """
    Format error message for consistent error handling.

    Args:
        error: Error message or exception

    Returns:
        Formatted error message
    """
    if isinstance(error, Exception):
        return str(error)
    return error


def validate_required_fields(data: Dict[str, Any], fields: List[str]) -> Optional[str]:
    """
    Validate that required fields are present in data.

    Args:
        data: Dictionary to validate
        fields: List of required field names

    Returns:
        Error message if validation fails, None otherwise
    """
    missing = [field for field in fields if field not in data]
    if missing:
        return f"Missing required fields: {', '.join(missing)}"
    return None


def extract_id_from_url(url: str, pattern: str = None) -> Optional[str]:
    """
    Extract ID from a URL using a default or custom pattern.
    Args:
        url: URL to extract ID from
        pattern: Optional custom regex pattern
    Returns:
        Extracted ID or None if not found
    """
    if not url:
        return None
    try:
        if pattern:
            match = re.search(pattern, url)
            if match:
                if match.groups():
                    return match.group(1)
                return match.group(0)
            return None
        # Default patterns for Notion and common IDs
        patterns = [
            r'([a-fA-F0-9]{32})',  # 32-char hex
            r'([a-fA-F0-9]{24})',  # 24-char hex
            r'([a-fA-F0-9]{16})',  # 16-char hex
            r'([a-fA-F0-9]{8})',   # 8-char hex
            r'([a-zA-Z0-9-]{36})',  # UUID
        ]
        for pat in patterns:
            match = re.search(pat, url)
            if match:
                return match.group(1)
    except Exception:
        return None
    return None
