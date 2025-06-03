"""
Common Utility Functions

This module contains utility functions that are shared across different integrations.
These functions provide common functionality for data access, validation, and processing.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Configure basic logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def safe_get(data: Any, keys: Union[str, List[Union[str, int]]], default: Any = None) -> Any:
    """
    Safely accesses nested dictionary keys or list indices.

    Args:
        data: The dictionary or list to access
        keys: A single key or list of keys/indices representing the path
        default: The value to return if the path is not found or an error occurs

    Returns:
        The value at the nested path or the default value
    """
    current = data
    if not isinstance(keys, list):
        keys = [keys]

    for key in keys:
        try:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list):
                # Ensure the key is a valid integer index
                if isinstance(key, int) and 0 <= key < len(current):
                    current = current[key]
                else:
                    # Log only if index access is attempted, not for .get() on list
                    if isinstance(key, int):
                        logger.warning(f"Invalid list index '{key}' for list: {current}")
                    return default
            else:
                # If current is None or not a dict/list at an intermediate step
                logger.warning(f"Cannot access key '{key}' in non-dict/list item: {current}")
                return default

            # If .get() returned None or list index access resulted in None
            if current is None:
                return default

        except (TypeError, IndexError, AttributeError) as e:
            logger.warning(f"Error accessing key '{key}': {e}")
            return default
    return current

def extract_id_from_url(url: str, pattern: str = r'[a-f0-9]{32}') -> Optional[str]:
    """
    Extracts an ID from a URL using a regex pattern.

    Args:
        url: The URL to extract the ID from
        pattern: The regex pattern to match the ID (default matches Notion page IDs)

    Returns:
        The extracted ID or None if extraction fails
    """
    try:
        import re
        # Remove query parameters and fragments
        url = url.split('?')[0].split('#')[0]
        # Find all matches and take the last one (most specific)
        matches = re.findall(pattern, url)
        if matches:
            return matches[-1]
    except Exception as e:
        logger.error(f"Error extracting ID from URL '{url}': {e}")
    return None 