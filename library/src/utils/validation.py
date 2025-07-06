"""
Input validation utilities for Pipedream automation.

This module provides functions to validate and extract inputs from Pipedream
context objects, ensuring all required fields are present and properly formatted.
"""

from typing import List, Dict, Any, Optional, Union
from src.utils.common_utils import safe_get
from src.config.constants import ERROR_INVALID_INPUT, ERROR_MISSING_AUTH


def validate_pipedream_inputs(
    pd: Any, required_fields: List[str]
) -> Dict[str, Any]:
    """
    Validate and extract required fields from Pipedream context.
    
    Args:
        pd: Pipedream context object
        required_fields: List of required field paths (e.g., ['notion.auth', 'task_id'])
        
    Returns:
        Dict with validated inputs
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # Extract inputs from various possible locations
    if hasattr(pd, 'inputs'):
        inputs = pd.inputs
    elif isinstance(pd, dict) and 'inputs' in pd:
        inputs = pd['inputs']
    else:
        inputs = pd
    
    validated = {}
    
    for field_path in required_fields:
        # Split the path into keys
        keys = field_path.split('.')
        
        # Try to get the value
        value = safe_get(inputs, keys)
        
        if value is None:
            raise ValueError(ERROR_INVALID_INPUT.format(field_path))
        
        # Store using the full path as key
        validated[field_path] = value
    
    return validated


def extract_authentication(
    pd: Any, 
    service: str = "notion",
    auth_type: str = "oauth"
) -> Optional[str]:
    """
    Extract authentication token from Pipedream context.
    
    Args:
        pd: Pipedream context object
        service: Service name (e.g., 'notion', 'google')
        auth_type: Authentication type (e.g., 'oauth', 'api_key')
        
    Returns:
        Authentication token or None if not found
    """
    # Common authentication paths
    auth_paths = [
        [service, "$auth", "oauth_access_token"],
        [service, "auth", "oauth_access_token"],
        [service, "$auth", "api_key"],
        [service, "auth", "api_key"],
        [f"{service}_auth"],
        [f"{service}_token"],
        ["auth", service, "token"],
        ["auth", service, "access_token"],
    ]
    
    # Extract inputs
    if hasattr(pd, 'inputs'):
        inputs = pd.inputs
    elif isinstance(pd, dict) and 'inputs' in pd:
        inputs = pd['inputs']
    else:
        inputs = pd
    
    # Try each path
    for path in auth_paths:
        token = safe_get(inputs, path)
        if token:
            return token
    
    return None


def validate_notion_auth(pd: Any) -> str:
    """
    Validate and extract Notion authentication token.
    
    Args:
        pd: Pipedream context object
        
    Returns:
        Notion authentication token
        
    Raises:
        ValueError: If authentication is missing
    """
    token = extract_authentication(pd, "notion")
    if not token:
        raise ValueError(f"{ERROR_MISSING_AUTH}: Notion authentication token")
    return token


def validate_google_auth(pd: Any) -> str:
    """
    Validate and extract Google authentication token.
    
    Args:
        pd: Pipedream context object
        
    Returns:
        Google authentication token
        
    Raises:
        ValueError: If authentication is missing
    """
    token = extract_authentication(pd, "google")
    if not token:
        raise ValueError(f"{ERROR_MISSING_AUTH}: Google authentication token")
    return token


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_date_format(date_str: str, format: str = "%Y-%m-%d") -> bool:
    """
    Validate date string format.
    
    Args:
        date_str: Date string to validate
        format: Expected date format
        
    Returns:
        True if valid, False otherwise
    """
    from datetime import datetime
    try:
        datetime.strptime(date_str, format)
        return True
    except ValueError:
        return False


def sanitize_string(value: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize string input by removing potentially harmful content.
    
    Args:
        value: String to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    # Remove null bytes and control characters
    sanitized = value.replace('\x00', '').strip()
    
    # Limit length if specified
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_required_fields(
    data: Dict[str, Any], 
    required: List[str],
    optional: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Validate that required fields exist in data dictionary.
    
    Args:
        data: Dictionary to validate
        required: List of required field names
        optional: List of optional field names
        
    Returns:
        Dictionary with only required and optional fields
        
    Raises:
        ValueError: If required fields are missing
    """
    validated = {}
    
    # Check required fields
    for field in required:
        if field not in data or data[field] is None:
            raise ValueError(ERROR_INVALID_INPUT.format(field))
        validated[field] = data[field]
    
    # Add optional fields if present
    if optional:
        for field in optional:
            if field in data and data[field] is not None:
                validated[field] = data[field]
    
    return validated