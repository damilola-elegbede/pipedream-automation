"""Tests for ErrorEnrichment module."""

import pytest
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime

from src.utils.error_enrichment import (
    ErrorContext, EnrichedError, ErrorEnricher,
    enrich_error, format_error
)


class TestErrorContext:
    """Test cases for ErrorContext class."""
    
    def test_init_defaults(self):
        """Test ErrorContext initialization with defaults."""
        context = ErrorContext()
        
        assert context.service is None
        assert context.operation is None
        assert context.resource_type is None
        assert context.resource_id is None
        assert context.api_endpoint is None
        assert context.request_method is None
        assert context.additional_info == {}
        assert isinstance(context.timestamp, datetime)
    
    def test_to_dict(self):
        """Test converting context to dictionary."""
        context = ErrorContext()
        context.service = 'notion'
        context.operation = 'create_page'
        context.additional_info = {'database_id': '123'}
        
        result = context.to_dict()
        
        assert result['service'] == 'notion'
        assert result['operation'] == 'create_page'
        assert result['database_id'] == '123'
        assert 'timestamp' in result


class TestEnrichedError:
    """Test cases for EnrichedError class."""
    
    def test_init_minimal(self):
        """Test EnrichedError with minimal parameters."""
        error = EnrichedError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.original_error is None
        assert error.error_code is None
        assert error.suggestions == []
        assert isinstance(error.context, ErrorContext)
        assert error.documentation_url is None
        assert error.traceback is None
    
    def test_init_full(self):
        """Test EnrichedError with all parameters."""
        original = ValueError("Original error")
        context = ErrorContext()
        context.service = 'gmail'
        
        error = EnrichedError(
            message="Enhanced error message",
            original_error=original,
            error_code="GMAIL_ERROR",
            suggestions=["Try this", "Try that"],
            context=context,
            documentation_url="https://docs.example.com"
        )
        
        assert str(error) == "Enhanced error message"
        assert error.original_error == original
        assert error.error_code == "GMAIL_ERROR"
        assert error.suggestions == ["Try this", "Try that"]
        assert error.context.service == 'gmail'
        assert error.documentation_url == "https://docs.example.com"
    
    def test_to_dict(self):
        """Test converting enriched error to dictionary."""
        original = ValueError("Original error")
        context = ErrorContext()
        context.service = 'notion'
        
        error = EnrichedError(
            message="Test error",
            original_error=original,
            error_code="TEST_ERROR",
            suggestions=["Fix this"],
            context=context
        )
        
        result = error.to_dict()
        
        assert result['message'] == "Test error"
        assert result['error_code'] == "TEST_ERROR"
        assert result['suggestions'] == ["Fix this"]
        assert result['context']['service'] == 'notion'
        assert 'original_error' in result
        assert 'traceback' in result


class TestErrorEnricher:
    """Test cases for ErrorEnricher class."""
    
    def test_init(self):
        """Test ErrorEnricher initialization."""
        enricher = ErrorEnricher()
        assert enricher.logger is not None
    
    def test_pattern_matching_connection_refused(self):
        """Test pattern matching for connection refused errors."""
        enricher = ErrorEnricher()
        error = ConnectionError("Connection refused")
        
        enriched = enricher.enrich_error(error)
        
        assert enriched.error_code == 'CONNECTION_REFUSED'
        assert str(enriched) == 'Unable to connect to the service'
        assert len(enriched.suggestions) > 0
        assert any('network connectivity' in s for s in enriched.suggestions)
    
    def test_pattern_matching_timeout(self):
        """Test pattern matching for timeout errors."""
        enricher = ErrorEnricher()
        error = TimeoutError("Request timeout after 30s")
        
        enriched = enricher.enrich_error(error)
        
        assert enriched.error_code == 'REQUEST_TIMEOUT'
        assert str(enriched) == 'Request timed out'
        assert any('retry logic' in s for s in enriched.suggestions)
    
    def test_pattern_matching_unauthorized(self):
        """Test pattern matching for authentication errors."""
        enricher = ErrorEnricher()
        error = Exception("401 Unauthorized")
        
        enriched = enricher.enrich_error(error)
        
        assert enriched.error_code == 'AUTH_FAILED'
        assert str(enriched) == 'Authentication failed'
        assert any('API credentials' in s for s in enriched.suggestions)
    
    def test_pattern_matching_rate_limit(self):
        """Test pattern matching for rate limit errors."""
        enricher = ErrorEnricher()
        error = Exception("429 Too Many Requests")
        
        enriched = enricher.enrich_error(error)
        
        assert enriched.error_code == 'RATE_LIMITED'
        assert str(enriched) == 'Rate limit exceeded'
        assert any('exponential backoff' in s for s in enriched.suggestions)
    
    def test_service_specific_notion_database_error(self):
        """Test service-specific enrichment for Notion database errors."""
        enricher = ErrorEnricher()
        error = Exception("Database not found")
        context = ErrorContext()
        context.service = 'notion'
        
        enriched = enricher.enrich_error(error, context)
        
        assert enriched.error_code == 'NOTION_DB_NOT_FOUND'
        assert str(enriched) == 'Notion database not found'
        assert any('database ID' in s for s in enriched.suggestions)
        assert enriched.documentation_url == 'https://developers.notion.com/reference/errors'
    
    def test_service_specific_gmail_quota_error(self):
        """Test service-specific enrichment for Gmail quota errors."""
        enricher = ErrorEnricher()
        error = Exception("Quota exceeded for gmail API")
        context = ErrorContext()
        context.service = 'gmail'
        
        enriched = enricher.enrich_error(error, context)
        
        assert enriched.error_code == 'GMAIL_QUOTA_EXCEEDED'
        assert str(enriched) == 'Gmail API quota exceeded'
        assert any('quota reset' in s for s in enriched.suggestions)
    
    def test_service_specific_openai_context_error(self):
        """Test service-specific enrichment for OpenAI context errors."""
        enricher = ErrorEnricher()
        error = Exception("Context length exceeded maximum tokens")
        context = ErrorContext()
        context.service = 'openai'
        
        enriched = enricher.enrich_error(error, context)
        
        assert enriched.error_code == 'OPENAI_CONTEXT_TOO_LONG'
        assert str(enriched) == 'OpenAI context length exceeded'
        assert any('text length' in s for s in enriched.suggestions)
    
    def test_default_enrichment(self):
        """Test default enrichment for unmatched errors."""
        enricher = ErrorEnricher()
        error = Exception("Some random error")
        
        enriched = enricher.enrich_error(error)
        
        assert enriched.error_code == 'GENERIC_ERROR'
        assert 'An error occurred' in str(enriched)
        assert len(enriched.suggestions) > 0
        assert any('debug logging' in s for s in enriched.suggestions)
    
    def test_context_kwargs(self):
        """Test passing context via kwargs."""
        enricher = ErrorEnricher()
        error = Exception("Test error")
        
        enriched = enricher.enrich_error(
            error,
            service='notion',
            operation='update_page',
            custom_field='custom_value'
        )
        
        assert enriched.context.service == 'notion'
        assert enriched.context.operation == 'update_page'
        assert enriched.context.additional_info['custom_field'] == 'custom_value'
    
    def test_extract_context_from_response_error(self):
        """Test extracting context from errors with response objects."""
        enricher = ErrorEnricher()
        
        # Mock error with response
        error = Mock()
        error.response = Mock()
        error.response.url = 'https://api.notion.com/v1/pages'
        error.response.request = Mock(method='POST')
        error.response.text = json.dumps({
            'error': 'Invalid request',
            'message': 'Missing required field'
        })
        
        context = enricher.extract_context_from_error(error)
        
        assert context.service == 'notion'
        assert context.api_endpoint == 'https://api.notion.com/v1/pages'
        assert context.request_method == 'POST'
        assert context.additional_info['error'] == 'Invalid request'
        assert context.additional_info['message'] == 'Missing required field'
    
    def test_extract_context_service_detection(self):
        """Test service detection from URL."""
        enricher = ErrorEnricher()
        
        test_cases = [
            ('https://api.notion.com/v1/pages', 'notion'),
            ('https://gmail.googleapis.com/gmail/v1', 'gmail'),
            ('https://api.openai.com/v1/completions', 'openai'),
            ('https://mystore.myshopify.com/admin/api', 'shopify'),
        ]
        
        for url, expected_service in test_cases:
            error = Mock()
            error.response = Mock(url=url)
            
            context = enricher.extract_context_from_error(error)
            assert context.service == expected_service
    
    def test_format_error_for_user_basic(self):
        """Test basic error formatting for users."""
        enricher = ErrorEnricher()
        
        enriched = EnrichedError(
            message="Authentication failed",
            error_code="AUTH_FAILED",
            suggestions=["Check API key", "Verify permissions"]
        )
        
        formatted = enricher.format_error_for_user(enriched)
        
        assert "❌ Authentication failed" in formatted
        assert "Error Code: AUTH_FAILED" in formatted
        assert "💡 Suggestions:" in formatted
        assert "1. Check API key" in formatted
        assert "2. Verify permissions" in formatted
    
    def test_format_error_for_user_with_context(self):
        """Test error formatting with context information."""
        enricher = ErrorEnricher()
        
        context = ErrorContext()
        context.service = 'notion'
        context.operation = 'create_page'
        
        enriched = EnrichedError(
            message="Database not found",
            error_code="NOTION_DB_NOT_FOUND",
            context=context,
            documentation_url="https://docs.notion.com"
        )
        
        formatted = enricher.format_error_for_user(enriched)
        
        assert "Service: notion" in formatted
        assert "Operation: create_page" in formatted
        assert "📚 Documentation: https://docs.notion.com" in formatted
    
    def test_format_error_for_user_technical_details(self):
        """Test error formatting with technical details."""
        enricher = ErrorEnricher()
        
        original = ValueError("Original technical error")
        context = ErrorContext()
        context.api_endpoint = 'https://api.example.com/v1/test'
        
        enriched = EnrichedError(
            message="Something went wrong",
            original_error=original,
            context=context
        )
        
        formatted = enricher.format_error_for_user(enriched, include_technical=True)
        
        assert "🔧 Technical Details:" in formatted
        assert "Original Error: Original technical error" in formatted
        assert "Endpoint: https://api.example.com/v1/test" in formatted
    
    def test_format_error_for_user_no_technical(self):
        """Test error formatting without technical details."""
        enricher = ErrorEnricher()
        
        original = ValueError("Technical stuff")
        enriched = EnrichedError(
            message="User-friendly message",
            original_error=original
        )
        
        formatted = enricher.format_error_for_user(enriched, include_technical=False)
        
        assert "Technical stuff" not in formatted
        assert "🔧 Technical Details:" not in formatted


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_enrich_error_function(self):
        """Test the enrich_error convenience function."""
        error = ConnectionError("Connection refused")
        
        enriched = enrich_error(
            error,
            service='notion',
            operation='fetch_database'
        )
        
        assert isinstance(enriched, EnrichedError)
        assert enriched.context.service == 'notion'
        assert enriched.context.operation == 'fetch_database'
        assert enriched.error_code == 'CONNECTION_REFUSED'
    
    def test_format_error_function(self):
        """Test the format_error convenience function."""
        error = Exception("401 Unauthorized")
        
        formatted = format_error(error, service='gmail')
        
        assert "❌" in formatted
        assert "Authentication failed" in formatted
        assert "Service: gmail" in formatted
        assert "💡 Suggestions:" in formatted
    
    def test_format_error_function_technical(self):
        """Test format_error with technical details."""
        error = ValueError("Technical error details")
        
        formatted = format_error(error, include_technical=True)
        
        assert "Technical error details" in formatted
        assert "🔧 Technical Details:" in formatted


class TestIntegrationScenarios:
    """Integration tests for real-world error scenarios."""
    
    def test_notion_api_error_flow(self):
        """Test complete error flow for Notion API error."""
        # Create an error that will match the Notion database pattern
        error = Exception("Database not found")
        
        # Process error with Notion context
        enricher = ErrorEnricher()
        context = ErrorContext()
        context.service = 'notion'
        context.api_endpoint = 'https://api.notion.com/v1/databases/invalid-id'
        context.request_method = 'GET'
        
        enriched = enricher.enrich_error(error, context)
        formatted = enricher.format_error_for_user(enriched)
        
        # Verify results
        assert enriched.error_code == 'NOTION_DB_NOT_FOUND'
        assert enriched.context.service == 'notion'
        assert 'Notion database not found' in formatted
        assert 'database ID' in formatted
    
    def test_network_error_flow(self):
        """Test complete error flow for network errors."""
        # Simulate connection error
        error = ConnectionError("Failed to establish a new connection: Connection refused")
        
        # Process error with context
        enriched = enrich_error(
            error,
            service='gmail',
            operation='send_email',
            api_endpoint='https://gmail.googleapis.com/gmail/v1/send'
        )
        
        # Format for user
        enricher = ErrorEnricher()
        formatted = enricher.format_error_for_user(enriched, include_technical=True)
        
        # Verify results
        assert enriched.error_code == 'CONNECTION_REFUSED'
        assert 'network connectivity' in formatted
        assert 'Service: gmail' in formatted
        assert 'Operation: send_email' in formatted
    
    def test_rate_limit_with_retry_suggestion(self):
        """Test rate limit error with retry suggestions."""
        # Create rate limit error that matches pattern
        error = Exception("429 Too Many Requests - Rate limit exceeded")
        
        # Enrich error
        enricher = ErrorEnricher()
        enriched = enricher.enrich_error(error)
        
        # Verify suggestions include retry logic
        assert enriched.error_code == 'RATE_LIMITED'
        assert any('exponential backoff' in s for s in enriched.suggestions)
        assert any('rate limit' in s for s in enriched.suggestions)