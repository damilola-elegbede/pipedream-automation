"""
Tests for Common Utility Functions

This module contains tests for the common utility functions that are shared across
different integrations. These tests ensure the reliability and correctness of
core functionality used throughout the application.
"""


from src.utils.common_utils import extract_id_from_url, safe_get


def test_safe_get_dict_access():
    """Test safe_get with dictionary access."""
    test_dict = {
        "a": 1,
        "b": {"c": 2, "d": [3, 4]},
        "e": None,
        "f": {"g": {"h": 5}},
    }

    # Test simple key access
    assert safe_get(test_dict, "a") == 1
    assert safe_get(test_dict, "x", "default") == "default"

    # Test nested dictionary access
    assert safe_get(test_dict, ["b", "c"]) == 2
    assert safe_get(test_dict, ["b", "x"], "default") == "default"

    # Test nested list access
    assert safe_get(test_dict, ["b", "d", 0]) == 3
    assert safe_get(test_dict, ["b", "d", 2], "default") == "default"

    # Test deep nesting
    assert safe_get(test_dict, ["f", "g", "h"]) == 5
    assert safe_get(test_dict, ["f", "g", "x"], "default") == "default"

    # Test None handling
    assert safe_get(test_dict, "e") is None
    assert safe_get(test_dict, ["e", "x"], "default") == "default"


def test_safe_get_list_access():
    """Test safe_get with list access."""
    test_list = [1, [2, 3], {"a": 4}, None]

    # Test simple index access (should be a list path)
    assert safe_get(test_list, [0]) == 1
    assert safe_get(test_list, [1, 1]) == 3
    assert safe_get(test_list, [2, "a"]) == 4
    assert safe_get(test_list, [3]) is None
    assert safe_get(test_list, [4]) is None


def test_safe_get_invalid_input():
    """Test safe_get with invalid inputs."""
    # Test None input
    assert safe_get(None, "a", "default") == "default"
    assert safe_get(None, ["a", "b"], "default") == "default"

    # Test empty containers
    assert safe_get({}, "a", "default") == "default"
    assert safe_get([], 0, "default") == "default"

    # Test invalid key types
    assert safe_get({"a": 1}, 0, "default") == "default"
    assert safe_get([1, 2], "a", "default") == "default"

    # Test invalid path
    assert safe_get({"a": 1}, ["a", "b", "c"], "default") == "default"


def test_safe_get_path_not_list():
    test_dict = {"a": 1}
    assert safe_get(test_dict, "a") == 1
    assert safe_get(test_dict, None, "default") == "default"


def test_safe_get_empty_path():
    test_dict = {"a": 1}
    assert safe_get(test_dict, [], "default") == "default"


def test_safe_get_invalid_path_type():
    test_dict = {"a": 1}
    assert safe_get(test_dict, ["a", {}], "default") == "default"


def test_safe_get_generic_exception():
    class Bad:
        def get(self, key):
            raise Exception("bad access")

    test_dict = {"a": Bad()}
    assert safe_get(test_dict, ["a", "b"], "default") == "default"


def test_extract_id_from_url_notion():
    """Test extract_id_from_url with Notion URLs."""
    # Valid Notion URLs
    assert (
        extract_id_from_url(
            "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef"
        )
        == "1234567890abcdef1234567890abcdef"
    )

    assert (
        extract_id_from_url(
            "https://www.notion.so/My-Page-1234567890abcdef1234567890abcdef?pvs=4"
        )
        == "1234567890abcdef1234567890abcdef"
    )

    # Invalid Notion URLs
    assert extract_id_from_url("https://www.notion.so/My-Page") is None
    assert extract_id_from_url("https://www.notion.so/") is None
    assert extract_id_from_url("") is None
    assert extract_id_from_url(None) is None


def test_extract_id_from_url_custom_pattern():
    """Test extract_id_from_url with custom patterns."""
    # Test with custom pattern for different ID format
    custom_pattern = r"/([A-Z]{2}-\d{3})(?:/|$)"

    assert (
        extract_id_from_url(
            "https://example.com/ticket/AB-123", pattern=custom_pattern
        )
        == "AB-123"
    )

    assert (
        extract_id_from_url(
            "https://example.com/ticket/AB-123/details", pattern=custom_pattern
        )
        == "AB-123"
    )

    # Invalid IDs
    assert (
        extract_id_from_url(
            "https://example.com/ticket/123-AB", pattern=custom_pattern
        )
        is None
    )

    assert (
        extract_id_from_url(
            "https://example.com/ticket/ABC-123", pattern=custom_pattern
        )
        is None
    )


def test_extract_id_from_url_error_handling():
    """Test extract_id_from_url error handling."""
    # Test with invalid pattern
    assert (
        extract_id_from_url(
            "https://example.com/page-123", pattern="[invalid pattern"
        )
        is None
    )

    # Test with non-string URL
    assert extract_id_from_url(None) is None
    assert extract_id_from_url(123) is None
    assert extract_id_from_url({}) is None


def test_extract_id_from_url_multiple_groups():
    url = "https://example.com/abc-123-xyz"
    pattern = r"abc-(\d+)-(xyz)"
    # Should return the first group if present
    assert extract_id_from_url(url, pattern) == "123"


def test_extract_id_from_url_no_groups():
    url = "https://example.com/abc-123"
    pattern = r"abc-\d+"
    assert extract_id_from_url(url, pattern) == "abc-123"


def test_extract_id_from_url_start_of_string():
    url = "123-abc"
    pattern = r"^(\d+)-abc"
    assert extract_id_from_url(url, pattern) == "123"


def test_extract_id_from_url_end_of_string():
    url = "abc-123"
    pattern = r"abc-(\d+)$"
    assert extract_id_from_url(url, pattern) == "123"


def test_extract_id_from_url_empty_match():
    url = "abc-"
    pattern = r"abc-()"
    assert extract_id_from_url(url, pattern) == ""


def test_extract_id_from_url_pattern_not_string():
    url = "abc-123"
    pattern = 123  # not a string
    try:
        result = extract_id_from_url(url, pattern)
    except Exception:
        result = None
    assert result is None
