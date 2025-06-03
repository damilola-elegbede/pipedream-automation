"""
Utility functions for content processing in Pipedream workflows.
"""
import re
from typing import List, Optional, Union


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
                if isinstance(current_level,
                              list) and 0 <= part < len(current_level):
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
                f"Warning: Content from step '{step_name}' at path '{
                    '.'.join(
                        map(
                            str,
                            path_parts))}' is None.")
            return ""
        if not isinstance(content, str):
            print(
                f"Warning: Expected a string from step '{step_name}' at path '{
                    '.'.join(
                        map(
                            str,
                            path_parts))}', but got {
                    type(content)}. Attempting to convert.")
            return str(content)
        if not content.strip():
            print(
                f"Warning: Content from step '{step_name}' at path '{
                    '.'.join(
                        map(
                            str,
                            path_parts))}' is empty or whitespace.")
            return ""
        return content
    except (KeyError, IndexError, TypeError) as e:
        print(
            f"Error accessing data from step '{step_name}'. {
                str(e)} in path '{
                '.'.join(
                    map(
                        str,
                        path_parts))}'")
        return None
    except Exception as e:
        print(
            f"An unexpected error occurred accessing data from step '{step_name}' at path '{
                '.'.join(
                    map(
                        str,
                        path_parts))}': {e}")
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
            pattern,
            replacement,
            html_content,
            flags=re.IGNORECASE)

    return html_content
