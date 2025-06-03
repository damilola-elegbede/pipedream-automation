"""
Tests for the AI Content Processor module.
"""
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.integrations.ai_content_processor import handler, markdown_to_html, combine_html


class MockPipedream:
    """Mock Pipedream context object for testing."""
    def __init__(self, steps=None):
        self.steps = steps or {}
    
    def get(self, key, default=None):
        """Simulate dictionary get method."""
        return self.steps.get(key, default)


def test_markdown_to_html():
    """Test markdown to HTML conversion."""
    # Test with content
    markdown = "# Test Heading\n\nSome content"
    result = markdown_to_html(markdown)
    assert result == "<pre># Test Heading\n\nSome content</pre>"
    
    # Test empty content
    assert markdown_to_html("") == "<pre></pre>"
    
    # Test None content
    assert markdown_to_html(None) == "<pre></pre>"


def test_combine_html():
    """Test combining HTML from multiple sources."""
    # Test with both contents
    claude_html = "<pre>Claude's content</pre>"
    chatgpt_html = "<pre>ChatGPT's content</pre>"
    result = combine_html(claude_html, chatgpt_html)
    assert result == "<div><pre>Claude's content</pre>\n<pre>ChatGPT's content</pre></div>"
    
    # Test with empty content
    assert combine_html("", "") == "<div>No content available.</div>"
    
    # Test with one empty content
    result = combine_html(claude_html, "")
    assert result == "<div><pre>Claude's content</pre>\n</div>"


@patch("src.integrations.ai_content_processor.datetime")
def test_handler_success(mock_datetime):
    """Test successful handler execution."""
    # Mock datetime
    mock_datetime.now.return_value = datetime(2024, 3, 20)
    
    # Test with both contents
    pd = MockPipedream({
        "claude_markdown": "# Claude's content",
        "chatgpt_markdown": "# ChatGPT's content"
    })
    
    result = handler(pd)
    
    assert isinstance(result, dict)
    assert "html" in result
    assert "today" in result
    assert result["today"] == "Wednesday, March 20, 2024"
    assert "Claude's content" in result["html"]
    assert "ChatGPT's content" in result["html"]


def test_handler_empty_content():
    """Test handler with empty content."""
    pd = MockPipedream({
        "claude_markdown": "",
        "chatgpt_markdown": ""
    })
    
    result = handler(pd)
    
    assert isinstance(result, dict)
    assert "html" in result
    assert "today" in result
    assert "<pre></pre>" in result["html"]


def test_handler_missing_content():
    """Test handler with missing content."""
    pd = MockPipedream({})
    
    result = handler(pd)
    
    assert isinstance(result, dict)
    assert "html" in result
    assert "today" in result
    assert "<pre></pre>" in result["html"]
