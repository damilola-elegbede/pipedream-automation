"""
Tests for the AI Content Processor module.
"""
import pytest
from datetime import date
from src.integrations.ai_content_processor import get_content_from_path, demote_headings, handler

class MockPipedream:
    def __init__(self, steps):
        self.steps = steps

def test_get_content_from_path():
    # Test successful path traversal
    test_data = {
        "step1": {
            "content": ["text1", "text2"]
        }
    }
    assert get_content_from_path(test_data, ["step1", "content", 0], "step1") == "text1"
    
    # Test missing key
    assert get_content_from_path(test_data, ["step1", "nonexistent"], "step1") is None
    
    # Test index out of range
    assert get_content_from_path(test_data, ["step1", "content", 5], "step1") is None
    
    # Test None value
    test_data["step1"]["content"][0] = None
    assert get_content_from_path(test_data, ["step1", "content", 0], "step1") == ""

def test_demote_headings():
    # Test heading demotion
    input_html = "<h1>Title</h1><h2>Subtitle</h2><h3>Section</h3>"
    expected = "<h2>Title</h2><h3>Subtitle</h3><h4>Section</h4>"
    assert demote_headings(input_html) == expected
    
    # Test empty input
    assert demote_headings("") == ""
    
    # Test no headings
    input_html = "<p>Regular text</p>"
    assert demote_headings(input_html) == input_html
    
    # Test h6 remains h6
    input_html = "<h6>Smallest heading</h6>"
    assert demote_headings(input_html) == input_html

def test_handler():
    # Mock Pipedream steps with both Claude and ChatGPT content
    mock_steps = {
        "chat1": {
            "$return_value": {
                "content": [{"text": "# Claude's Markdown"}]
            }
        },
        "chat": {
            "$return_value": {
                "generated_message": {
                    "content": "# ChatGPT's Markdown"
                }
            }
        }
    }
    
    pd = MockPipedream(mock_steps)
    result = handler(pd)
    
    # Test structure of return value
    assert isinstance(result, dict)
    assert "html_body" in result
    assert "formatted_date" in result
    
    # Test HTML content
    assert "Claude's Output" in result["html_body"]
    assert "ChatGPT's Output" in result["html_body"]
    
    # Test date formatting
    today = date.today()
    expected_date = today.strftime(f"%B {today.day}, %Y")
    assert result["formatted_date"] == expected_date

def test_handler_empty_content():
    # Test with empty content
    mock_steps = {
        "chat1": {"$return_value": {"content": []}},
        "chat": {"$return_value": {"generated_message": {"content": ""}}}
    }
    
    pd = MockPipedream(mock_steps)
    result = handler(pd)
    
    assert "(No content from Claude)" in result["html_body"]
    assert "(No content from ChatGPT)" in result["html_body"]

def test_handler_missing_steps():
    # Test with missing steps
    mock_steps = {}
    
    pd = MockPipedream(mock_steps)
    result = handler(pd)
    
    assert "Error fetching Claude's content" in result["html_body"]
    assert "Error fetching ChatGPT's content" in result["html_body"] 