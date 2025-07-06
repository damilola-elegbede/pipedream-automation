"""
Tests for content processing utilities.

This module contains tests for utility functions that process and transform
content in Pipedream workflows.
"""

from src.utils.content_processing import demote_headings, get_content_from_path


def test_get_content_from_path_success():
    """Test successful content retrieval from nested dictionary."""
    test_data = {
        "step1": {"content": ["text1", "text2"], "metadata": {"author": "test"}}
    }

    # Test string key
    assert (
        get_content_from_path(
            test_data, ["step1", "metadata", "author"], "step1"
        )
        == "test"
    )

    # Test integer index
    assert (
        get_content_from_path(test_data, ["step1", "content", 0], "step1")
        == "text1"
    )

    # Test nested path
    assert (
        get_content_from_path(test_data, ["step1", "content", 1], "step1")
        == "text2"
    )


def test_get_content_from_path_missing_key():
    """Test handling of missing keys in path."""
    test_data = {"step1": {"content": ["text1"]}}

    result = get_content_from_path(test_data, ["step1", "nonexistent"], "step1")
    assert result is None


def test_get_content_from_path_index_error():
    """Test handling of index out of range."""
    test_data = {"step1": {"content": ["text1"]}}

    result = get_content_from_path(test_data, ["step1", "content", 5], "step1")
    assert result is None


def test_get_content_from_path_type_error():
    """Test handling of invalid path part type."""
    test_data = {"step1": {"content": ["text1"]}}

    result = get_content_from_path(
        test_data, ["step1", "content", "invalid"], "step1"
    )
    assert result is None


def test_get_content_from_path_none_value():
    """Test handling of None values in path."""
    test_data = {"step1": {"content": [None, "text2"]}}

    result = get_content_from_path(test_data, ["step1", "content", 0], "step1")
    assert result == ""


def test_get_content_from_path_non_string():
    """Test handling of non-string content."""
    test_data = {"step1": {"content": [123, "text2"]}}

    result = get_content_from_path(test_data, ["step1", "content", 0], "step1")
    assert result == "123"


def test_get_content_from_path_empty_content():
    """Test handling of empty or whitespace content."""
    test_data = {"step1": {"content": ["   ", "text2"]}}

    result = get_content_from_path(test_data, ["step1", "content", 0], "step1")
    assert result == ""


def test_get_content_from_path_list_result():
    test_data = {"step1": {"content": [[1, 2, 3]]}}
    result = get_content_from_path(test_data, ["step1", "content", 0], "step1")
    assert result == "[1, 2, 3]"


def test_get_content_from_path_bool_and_float():
    test_data = {"step1": {"content": [True, 3.14]}}
    assert (
        get_content_from_path(test_data, ["step1", "content", 0], "step1")
        == "True"
    )
    assert (
        get_content_from_path(test_data, ["step1", "content", 1], "step1")
        == "3.14"
    )


def test_get_content_from_path_empty_path():
    test_data = {"step1": {"content": ["abc"]}}
    # The function returns the string representation of the input dict if path is empty
    assert get_content_from_path(test_data, [], "step1") == str(test_data)


def test_get_content_from_path_non_list_path():
    test_data = {"step1": {"content": ["abc"]}}
    assert get_content_from_path(test_data, "step1", "step1") is None


def test_get_content_from_path_invalid_path_type():
    test_data = {"step1": {"content": ["abc"]}}
    # dict as path part
    assert get_content_from_path(test_data, ["step1", {}], "step1") is None


def test_get_content_from_path_generic_exception():
    class Bad:
        def __getitem__(self, key):
            raise Exception("bad access")

    test_data = {"step1": Bad()}
    assert (
        get_content_from_path(test_data, ["step1", "content"], "step1") is None
    )


def test_demote_headings_success():
    """Test successful heading demotion."""
    input_html = """
    <h1>Main Title</h1>
    <h2>Subtitle</h2>
    <h3>Section</h3>
    <h4>Subsection</h4>
    <h5>Minor Section</h5>
    <h6>Smallest Heading</h6>
    """

    expected = """
    <h2>Main Title</h2>
    <h3>Subtitle</h3>
    <h4>Section</h4>
    <h5>Subsection</h5>
    <h6>Minor Section</h6>
    <h6>Smallest Heading</h6>
    """

    result = demote_headings(input_html)
    assert result.strip() == expected.strip()


def test_demote_headings_empty():
    """Test handling of empty input."""
    assert demote_headings("") == ""
    assert demote_headings(None) == ""


def test_demote_headings_no_headings():
    """Test handling of content without headings."""
    input_html = "<p>Regular text</p><div>Some content</div>"
    assert demote_headings(input_html) == input_html


def test_demote_headings_mixed_case():
    """Test handling of mixed case heading tags."""
    input_html = "<H1>Title</H1><h2>Subtitle</h2>"
    expected = "<h2>Title</h2><h3>Subtitle</h3>"
    assert demote_headings(input_html) == expected


def test_demote_headings_with_attributes():
    """Test handling of headings with attributes."""
    input_html = '<h1 class="title" id="main">Title</h1>'
    expected = '<h2 class="title" id="main">Title</h2>'
    assert demote_headings(input_html) == expected


def test_demote_headings_malformed_html():
    input_html = "<h1>Title<h2>Subtitle"
    expected = "<h2>Title<h3>Subtitle"
    assert demote_headings(input_html) == expected


def test_demote_headings_extra_attributes_whitespace():
    input_html = '<h1   class="x"   >Title</h1>'
    expected = '<h2   class="x"   >Title</h2>'
    assert demote_headings(input_html) == expected
