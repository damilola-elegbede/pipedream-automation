"""
Tests for the AI Content Processor module.

This module contains tests for the AI Content Processor functionality,
including markdown to HTML conversion and content combination.
"""

import unittest.mock
from datetime import datetime

from src.integrations.ai_content_processor import (
    combine_html_content,
    convert_markdown_to_html,
    handler,
)


class MockPipedream:
    """Mock class to simulate Pipedream context object."""

    def __init__(self, inputs=None):
        self.inputs = inputs or {}

    def get(self, key, default=None):
        """Simulate dictionary-like access."""
        return self.inputs.get(key, default)


def test_convert_markdown_to_html():
    """Test markdown to HTML conversion."""
    # Mock the requests.post response
    with unittest.mock.patch('requests.post') as mock_post:
        mock_post.return_value.json.return_value = {
            "choices": [{"message": {"content": "<h1>Heading</h1><p><strong>Bold</strong> and <em>italic</em> text</p>"}}]
        }
        mock_post.return_value.raise_for_status = lambda: None

        pd = MockPipedream({"openai_api_key": "test_key"})
        markdown = "# Heading\n\n**Bold** and *italic* text"
        html = convert_markdown_to_html(markdown, pd)
        assert "<h1>Heading</h1>" in html
        assert "<strong>Bold</strong>" in html
        assert "<em>italic</em>" in html


def test_combine_html_content():
    """Test combining HTML content."""
    # Test with title and content
    title = "Test Title"
    content = "<p>Test content</p>"
    combined = combine_html_content(title, content)
    assert f"<h1>{title}</h1>" in combined
    assert content in combined

    # Test with image
    image_url = "https://example.com/image.jpg"
    combined = combine_html_content(title, content, image_url)
    assert f'<img src="{image_url}" alt="{title}">' in combined
    assert f"<h1>{title}</h1>" in combined
    assert content in combined


def test_handler_success():
    """Test successful handler execution."""
    # Mock the convert_markdown_to_html function
    with unittest.mock.patch('src.integrations.ai_content_processor.convert_markdown_to_html') as mock_convert:
        mock_convert.return_value = "<p>Converted content</p>"

        # Create mock Pipedream context with correct input structure
        pd = MockPipedream({
            "content": {
                "title": "Test Title",
                "content": "# Test Content\n\nSome text",
                "image_url": "https://example.com/image.jpg"
            }
        })

        # Call handler
        result = handler(pd)

        # Verify result structure
        assert "message" in result
        assert result["message"] == "Successfully processed content"
        assert "content" in result
        assert result["content"]["title"] == "Test Title"
        assert "<p>Converted content</p>" in result["content"]["html"]


def test_handler_empty_content():
    """Test handler with empty content."""
    pd = MockPipedream({"content": {}})
    result = handler(pd)
    assert "error" in result
    assert "No content provided" in result["error"]


def test_handler_missing_content():
    """Test handler with missing content."""
    pd = MockPipedream({})
    result = handler(pd)
    assert "error" in result
    assert "No content provided" in result["error"]
