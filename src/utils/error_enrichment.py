"""
Error Enrichment module for transforming generic errors into actionable messages.

This module provides intelligent error enrichment that transforms low-level
technical errors into user-friendly, actionable messages with context and
suggested solutions.
"""

import re
import json
import traceback
from typing import Dict, Any, Optional, List, Union, Type
from datetime import datetime, timezone
UTC = timezone.utc
import logging


class ErrorContext:
    """Container for error context information."""
    
    def __init__(self):
        self.service: Optional[str] = None
        self.operation: Optional[str] = None
        self.resource_type: Optional[str] = None
        self.resource_id: Optional[str] = None
        self.api_endpoint: Optional[str] = None
        self.request_method: Optional[str] = None
        self.additional_info: Dict[str, Any] = {}
        self.timestamp: datetime = datetime.now(UTC)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'service': self.service,
            'operation': self.operation,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'api_endpoint': self.api_endpoint,
            'request_method': self.request_method,
            'timestamp': self.timestamp.isoformat(),
            **self.additional_info
        }


class EnrichedError(Exception):
    """Enhanced exception with rich context and actionable information."""
    
    def __init__(
        self,
        message: str,
        original_error: Optional[Exception] = None,
        error_code: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        context: Optional[ErrorContext] = None,
        documentation_url: Optional[str] = None
    ):
        super().__init__(message)
        self.original_error = original_error
        self.error_code = error_code
        self.suggestions = suggestions or []
        self.context = context or ErrorContext()
        self.documentation_url = documentation_url
        self.traceback = traceback.format_exc() if original_error else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert enriched error to dictionary for logging/debugging."""
        return {
            'message': str(self),
            'error_code': self.error_code,
            'suggestions': self.suggestions,
            'context': self.context.to_dict(),
            'documentation_url': self.documentation_url,
            'original_error': str(self.original_error) if self.original_error else None,
            'traceback': self.traceback
        }


class ErrorEnricher:
    """
    Transforms generic errors into actionable, user-friendly messages.
    
    Features:
    - Pattern-based error detection and enrichment
    - Service-specific error handling
    - Contextual suggestions for resolution
    - Error code mapping
    - Documentation links
    """
    
    # Common error patterns and their enrichments
    ERROR_PATTERNS = {
        # Network and Connection Errors
        r'.*connection.*refused.*': {
            'message': 'Unable to connect to the service',
            'code': 'CONNECTION_REFUSED',
            'suggestions': [
                'Check if the service is running and accessible',
                'Verify network connectivity',
                'Check firewall settings',
                'Confirm the service URL and port are correct'
            ]
        },
        r'.*timeout.*': {
            'message': 'Request timed out',
            'code': 'REQUEST_TIMEOUT',
            'suggestions': [
                'The service may be experiencing high load',
                'Try again with a longer timeout value',
                'Check your network connection',
                'Consider implementing retry logic'
            ]
        },
        r'.*SSL.*certificate.*': {
            'message': 'SSL certificate verification failed',
            'code': 'SSL_ERROR',
            'suggestions': [
                'Verify the SSL certificate is valid',
                'Check if the certificate has expired',
                'Ensure the certificate chain is complete',
                'Update your certificate bundle'
            ]
        },
        
        # Authentication Errors
        r'.*(401|unauthorized|authentication).*': {
            'message': 'Authentication failed',
            'code': 'AUTH_FAILED',
            'suggestions': [
                'Verify your API credentials are correct',
                'Check if the token has expired',
                'Ensure you have the required permissions',
                'Try regenerating your API key'
            ]
        },
        r'.*(403|forbidden|permission.*denied).*': {
            'message': 'Access forbidden',
            'code': 'ACCESS_FORBIDDEN',
            'suggestions': [
                'Check if you have the required permissions',
                'Verify your API key has the necessary scopes',
                'Contact your administrator for access',
                'Review the service\'s permission requirements'
            ]
        },
        
        # Rate Limiting
        r'.*(429|rate.*limit|too.*many.*requests).*': {
            'message': 'Rate limit exceeded',
            'code': 'RATE_LIMITED',
            'suggestions': [
                'Wait before making more requests',
                'Implement exponential backoff',
                'Check rate limit headers for reset time',
                'Consider upgrading your API plan'
            ]
        },
        
        # Data Validation Errors
        r'.*invalid.*json.*': {
            'message': 'Invalid JSON format',
            'code': 'INVALID_JSON',
            'suggestions': [
                'Verify the JSON syntax is correct',
                'Check for missing quotes or commas',
                'Use a JSON validator tool',
                'Ensure proper character encoding'
            ]
        },
        r'.*missing.*required.*field.*': {
            'message': 'Required field missing',
            'code': 'MISSING_FIELD',
            'suggestions': [
                'Review the API documentation for required fields',
                'Check your request payload structure',
                'Ensure all mandatory fields are included',
                'Verify field names match the API specification'
            ]
        },
        
        # Resource Errors
        r'.*(404|not.*found).*': {
            'message': 'Resource not found',
            'code': 'NOT_FOUND',
            'suggestions': [
                'Verify the resource ID is correct',
                'Check if the resource exists',
                'Ensure you\'re using the correct API endpoint',
                'Confirm you have access to this resource'
            ]
        },
        r'.*(409|conflict).*': {
            'message': 'Resource conflict',
            'code': 'CONFLICT',
            'suggestions': [
                'The resource may already exist',
                'Check for duplicate entries',
                'Verify unique constraints',
                'Try updating instead of creating'
            ]
        }
    }
    
    # Service-specific error enrichments
    SERVICE_ERRORS = {
        'notion': {
            'database_not_found': {
                'message': 'Notion database not found',
                'code': 'NOTION_DB_NOT_FOUND',
                'suggestions': [
                    'Verify the database ID is correct',
                    'Ensure the integration has access to the database',
                    'Check if the database was recently deleted',
                    'Try reconnecting the Notion integration'
                ],
                'doc_url': 'https://developers.notion.com/reference/errors'
            },
            'invalid_property': {
                'message': 'Invalid Notion property',
                'code': 'NOTION_INVALID_PROPERTY',
                'suggestions': [
                    'Check if the property exists in the database',
                    'Verify the property type matches your data',
                    'Review the database schema',
                    'Ensure property names are exact matches'
                ]
            }
        },
        'gmail': {
            'invalid_query': {
                'message': 'Invalid Gmail search query',
                'code': 'GMAIL_INVALID_QUERY',
                'suggestions': [
                    'Check Gmail search syntax',
                    'Escape special characters properly',
                    'Use valid search operators',
                    'Test the query in Gmail web interface'
                ],
                'doc_url': 'https://support.google.com/mail/answer/7190'
            },
            'quota_exceeded': {
                'message': 'Gmail API quota exceeded',
                'code': 'GMAIL_QUOTA_EXCEEDED',
                'suggestions': [
                    'Wait for quota reset (usually daily)',
                    'Implement batch operations',
                    'Request quota increase from Google',
                    'Optimize API usage patterns'
                ]
            }
        },
        'openai': {
            'context_length_exceeded': {
                'message': 'OpenAI context length exceeded',
                'code': 'OPENAI_CONTEXT_TOO_LONG',
                'suggestions': [
                    'Reduce the input text length',
                    'Use a model with larger context window',
                    'Implement text chunking strategy',
                    'Consider summarization before processing'
                ]
            },
            'invalid_api_key': {
                'message': 'Invalid OpenAI API key',
                'code': 'OPENAI_INVALID_KEY',
                'suggestions': [
                    'Verify your API key is correct',
                    'Check if the key has been revoked',
                    'Ensure no extra spaces in the key',
                    'Generate a new API key if needed'
                ],
                'doc_url': 'https://platform.openai.com/docs/api-reference/authentication'
            }
        }
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize ErrorEnricher.
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def enrich_error(
        self,
        error: Exception,
        context: Optional[ErrorContext] = None,
        **kwargs
    ) -> EnrichedError:
        """
        Enrich an error with actionable information.
        
        Args:
            error: The original exception
            context: Optional error context
            **kwargs: Additional context information
            
        Returns:
            EnrichedError with enhanced information
        """
        # Create or update context
        if context is None:
            context = ErrorContext()
        
        # Add any kwargs to context
        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)
            else:
                context.additional_info[key] = value
        
        # Get error string for pattern matching
        error_str = str(error).lower()
        
        # Try service-specific enrichment first
        if context.service:
            enriched = self._try_service_enrichment(
                error, error_str, context.service, context
            )
            if enriched:
                return enriched
        
        # Try pattern-based enrichment
        enriched = self._try_pattern_enrichment(error, error_str, context)
        if enriched:
            return enriched
        
        # Default enrichment
        return self._default_enrichment(error, context)
    
    def _try_service_enrichment(
        self,
        error: Exception,
        error_str: str,
        service: str,
        context: ErrorContext
    ) -> Optional[EnrichedError]:
        """Try to enrich error using service-specific patterns."""
        service = service.lower()
        if service not in self.SERVICE_ERRORS:
            return None
        
        service_errors = self.SERVICE_ERRORS[service]
        
        for error_key, enrichment in service_errors.items():
            # Check if error matches this service error
            if error_key.replace('_', ' ') in error_str:
                return EnrichedError(
                    message=enrichment['message'],
                    original_error=error,
                    error_code=enrichment['code'],
                    suggestions=enrichment.get('suggestions', []),
                    context=context,
                    documentation_url=enrichment.get('doc_url')
                )
        
        return None
    
    def _try_pattern_enrichment(
        self,
        error: Exception,
        error_str: str,
        context: ErrorContext
    ) -> Optional[EnrichedError]:
        """Try to enrich error using pattern matching."""
        for pattern, enrichment in self.ERROR_PATTERNS.items():
            if re.match(pattern, error_str, re.IGNORECASE):
                # Add context-specific suggestions
                suggestions = enrichment['suggestions'].copy()
                
                if context.service:
                    suggestions.append(
                        f'Check {context.service} service status'
                    )
                
                if context.api_endpoint:
                    suggestions.append(
                        f'Verify endpoint: {context.api_endpoint}'
                    )
                
                return EnrichedError(
                    message=enrichment['message'],
                    original_error=error,
                    error_code=enrichment['code'],
                    suggestions=suggestions,
                    context=context
                )
        
        return None
    
    def _default_enrichment(
        self,
        error: Exception,
        context: ErrorContext
    ) -> EnrichedError:
        """Provide default enrichment for unmatched errors."""
        # Extract HTTP status code if present
        status_code = None
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            status_code = error.response.status_code
        
        # Generate default suggestions based on error type
        suggestions = []
        
        if isinstance(error, (ConnectionError, TimeoutError)):
            suggestions.extend([
                'Check network connectivity',
                'Verify service availability',
                'Review timeout settings'
            ])
        elif isinstance(error, (ValueError, TypeError)):
            suggestions.extend([
                'Verify input data format',
                'Check data types match requirements',
                'Review API documentation'
            ])
        elif status_code:
            if 400 <= status_code < 500:
                suggestions.append('Check request parameters and authentication')
            elif 500 <= status_code < 600:
                suggestions.append('The service is experiencing issues, try again later')
        
        # Always add generic suggestions
        suggestions.extend([
            'Enable debug logging for more details',
            'Check service documentation',
            'Contact support if issue persists'
        ])
        
        return EnrichedError(
            message=f'An error occurred: {str(error)}',
            original_error=error,
            error_code='GENERIC_ERROR',
            suggestions=suggestions,
            context=context
        )
    
    def extract_context_from_error(
        self,
        error: Exception
    ) -> ErrorContext:
        """
        Extract context information from an error.
        
        Args:
            error: The exception to extract context from
            
        Returns:
            ErrorContext with extracted information
        """
        context = ErrorContext()
        
        # Try to extract from response object
        if hasattr(error, 'response'):
            response = error.response
            
            # Extract URL/endpoint
            if hasattr(response, 'url'):
                context.api_endpoint = response.url
                
                # Try to determine service from URL
                url_lower = response.url.lower()
                if 'notion' in url_lower:
                    context.service = 'notion'
                elif 'gmail' in url_lower or 'google' in url_lower:
                    context.service = 'gmail'
                elif 'openai' in url_lower:
                    context.service = 'openai'
                elif 'shopify' in url_lower:
                    context.service = 'shopify'
            
            # Extract method
            if hasattr(response, 'request') and hasattr(response.request, 'method'):
                context.request_method = response.request.method
            
            # Extract additional info from response
            if hasattr(response, 'text'):
                try:
                    response_data = json.loads(response.text)
                    if isinstance(response_data, dict):
                        # Look for common error fields
                        for field in ['error', 'message', 'error_description', 'detail']:
                            if field in response_data:
                                context.additional_info[field] = response_data[field]
                except:
                    pass
        
        return context
    
    def format_error_for_user(
        self,
        enriched_error: EnrichedError,
        include_technical: bool = False
    ) -> str:
        """
        Format enriched error for user display.
        
        Args:
            enriched_error: The enriched error
            include_technical: Whether to include technical details
            
        Returns:
            Formatted error message
        """
        lines = []
        
        # Main message
        lines.append(f"❌ {str(enriched_error)}")
        
        # Error code
        if enriched_error.error_code:
            lines.append(f"Error Code: {enriched_error.error_code}")
        
        # Context information
        context = enriched_error.context
        if context.service:
            lines.append(f"Service: {context.service}")
        if context.operation:
            lines.append(f"Operation: {context.operation}")
        
        # Suggestions
        if enriched_error.suggestions:
            lines.append("\n💡 Suggestions:")
            for i, suggestion in enumerate(enriched_error.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
        
        # Documentation
        if enriched_error.documentation_url:
            lines.append(f"\n📚 Documentation: {enriched_error.documentation_url}")
        
        # Technical details
        if include_technical and enriched_error.original_error:
            lines.append(f"\n🔧 Technical Details:")
            lines.append(f"Original Error: {str(enriched_error.original_error)}")
            if context.api_endpoint:
                lines.append(f"Endpoint: {context.api_endpoint}")
        
        return "\n".join(lines)


# Convenience functions
def enrich_error(
    error: Exception,
    service: Optional[str] = None,
    operation: Optional[str] = None,
    **kwargs
) -> EnrichedError:
    """
    Quick function to enrich an error.
    
    Args:
        error: The exception to enrich
        service: Optional service name
        operation: Optional operation name
        **kwargs: Additional context
        
    Returns:
        EnrichedError instance
    """
    enricher = ErrorEnricher()
    
    # Create context
    context = ErrorContext()
    if service:
        context.service = service
    if operation:
        context.operation = operation
    
    return enricher.enrich_error(error, context, **kwargs)


def format_error(
    error: Exception,
    service: Optional[str] = None,
    include_technical: bool = False
) -> str:
    """
    Format an error for user display.
    
    Args:
        error: The exception to format
        service: Optional service name
        include_technical: Whether to include technical details
        
    Returns:
        Formatted error message
    """
    enricher = ErrorEnricher()
    
    # Extract or create context
    context = enricher.extract_context_from_error(error)
    if service:
        context.service = service
    
    # Enrich and format
    enriched = enricher.enrich_error(error, context)
    return enricher.format_error_for_user(enriched, include_technical)