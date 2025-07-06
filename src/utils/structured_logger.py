"""
Structured Logger module for enhanced debugging and observability.

This module provides a structured logging system with request tracking,
context propagation, and JSON formatting for better debugging in
serverless environments like Pipedream.
"""

import logging
import json
import uuid
import time
from typing import Dict, Any, Optional, List, Union, Callable
from datetime import datetime, timezone
from contextlib import contextmanager
from functools import wraps
import traceback
import threading

UTC = timezone.utc


class LogContext:
    """Thread-safe context storage for logging."""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def data(self) -> Dict[str, Any]:
        """Get context data for current thread."""
        if not hasattr(self._local, 'data'):
            self._local.data = {}
        return self._local.data
    
    def set(self, key: str, value: Any):
        """Set context value."""
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get context value."""
        return self.data.get(key, default)
    
    def clear(self):
        """Clear all context data."""
        self.data.clear()
    
    def update(self, **kwargs):
        """Update context with multiple values."""
        self.data.update(kwargs)


# Global context instance
log_context = LogContext()


class StructuredLogger:
    """
    Enhanced logger with structured output and request tracking.
    
    Features:
    - Request ID tracking for tracing across function calls
    - Structured JSON output for easy parsing
    - Context propagation through execution
    - Performance timing
    - Error enrichment
    - Pipedream-friendly formatting
    """
    
    def __init__(
        self,
        name: str,
        level: int = logging.INFO,
        json_format: bool = True,
        include_timestamp: bool = True,
        include_caller: bool = True
    ):
        """
        Initialize StructuredLogger.
        
        Args:
            name: Logger name (typically module name)
            level: Logging level
            json_format: Whether to output JSON formatted logs
            include_timestamp: Include timestamp in logs
            include_caller: Include caller information
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.json_format = json_format
        self.include_timestamp = include_timestamp
        self.include_caller = include_caller
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []
        
        # Create and configure handler
        handler = logging.StreamHandler()
        handler.setLevel(level)
        
        if json_format:
            handler.setFormatter(self._create_json_formatter())
        else:
            handler.setFormatter(self._create_text_formatter())
        
        self.logger.addHandler(handler)
    
    def _create_json_formatter(self) -> logging.Formatter:
        """Create JSON formatter."""
        class JsonFormatter(logging.Formatter):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
                
            def format(self, record):
                log_data = {
                    'level': record.levelname,
                    'message': record.getMessage(),
                    'logger': record.name,
                }
                
                # Add timestamp
                if self.parent.include_timestamp:
                    log_data['timestamp'] = datetime.now(UTC).isoformat()
                
                # Add caller info
                if self.parent.include_caller:
                    log_data['caller'] = {
                        'filename': record.filename,
                        'line': record.lineno,
                        'function': record.funcName
                    }
                
                # Add context data
                context_data = log_context.data.copy()
                if context_data:
                    log_data['context'] = context_data
                
                # Add extra fields from record
                extra_fields = getattr(record, 'extra', {})
                if isinstance(extra_fields, dict):
                    for key, value in extra_fields.items():
                        if key not in log_data:
                            log_data[key] = value
                
                return json.dumps(log_data, default=str)
        
        return JsonFormatter(self)
    
    def _create_text_formatter(self) -> logging.Formatter:
        """Create text formatter."""
        format_parts = []
        
        if self.include_timestamp:
            format_parts.append('%(asctime)s')
        
        format_parts.extend([
            '[%(levelname)s]',
            '%(name)s'
        ])
        
        if self.include_caller:
            format_parts.append('(%(filename)s:%(lineno)d)')
        
        format_parts.append('%(message)s')
        
        return logging.Formatter(' - '.join(format_parts))
    
    @contextmanager
    def request_context(self, request_id: Optional[str] = None, **kwargs):
        """
        Context manager for request tracking.
        
        Args:
            request_id: Optional request ID (generated if not provided)
            **kwargs: Additional context data
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
        
        # Store previous context
        previous_context = log_context.data.copy()
        
        # Set new context
        log_context.set('request_id', request_id)
        log_context.update(**kwargs)
        
        self.info(f"Request started", request_id=request_id)
        start_time = time.time()
        
        try:
            yield request_id
        finally:
            # Calculate duration
            duration = time.time() - start_time
            self.info(
                f"Request completed",
                request_id=request_id,
                duration_seconds=duration
            )
            
            # Restore previous context
            log_context.clear()
            log_context.update(**previous_context)
    
    def log_operation(self, operation_name: str):
        """
        Decorator for logging operation execution.
        
        Args:
            operation_name: Name of the operation
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                self.info(f"Starting operation: {operation_name}")
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    self.info(
                        f"Operation completed: {operation_name}",
                        duration_seconds=duration,
                        status="success"
                    )
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    
                    self.error(
                        f"Operation failed: {operation_name}",
                        duration_seconds=duration,
                        status="failed",
                        error_type=type(e).__name__,
                        error_message=str(e),
                        traceback=traceback.format_exc()
                    )
                    
                    raise
            
            return wrapper
        return decorator
    
    def log_api_call(
        self,
        service: str,
        endpoint: str,
        method: str = "GET",
        **kwargs
    ):
        """
        Log API call details.
        
        Args:
            service: Service name (e.g., 'notion', 'gmail')
            endpoint: API endpoint
            method: HTTP method
            **kwargs: Additional call details
        """
        self.info(
            f"API call to {service}",
            service=service,
            endpoint=endpoint,
            method=method,
            **kwargs
        )
    
    def log_api_response(
        self,
        service: str,
        status_code: int,
        duration: float,
        **kwargs
    ):
        """
        Log API response details.
        
        Args:
            service: Service name
            status_code: HTTP status code
            duration: Request duration in seconds
            **kwargs: Additional response details
        """
        level = logging.INFO if 200 <= status_code < 400 else logging.WARNING
        
        self.log(
            level,
            f"API response from {service}",
            service=service,
            status_code=status_code,
            duration_seconds=duration,
            **kwargs
        )
    
    def log_error_with_context(
        self,
        error: Exception,
        operation: Optional[str] = None,
        **kwargs
    ):
        """
        Log error with full context.
        
        Args:
            error: The exception
            operation: Optional operation name
            **kwargs: Additional context
        """
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            **kwargs
        }
        
        if operation:
            error_data['operation'] = operation
        
        # Extract additional error info if available
        if hasattr(error, 'response'):
            response = error.response
            if hasattr(response, 'status_code'):
                error_data['status_code'] = response.status_code
            if hasattr(response, 'text'):
                error_data['response_body'] = response.text[:1000]  # Limit size
        
        self.error(
            f"Error in {operation or 'operation'}",
            **error_data
        )
    
    def log_performance_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = "seconds",
        **kwargs
    ):
        """
        Log performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            unit: Unit of measurement
            **kwargs: Additional metric tags
        """
        self.info(
            f"Performance metric: {metric_name}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **kwargs
        )
    
    # Standard logging methods with extra field support
    def debug(self, msg: str, **kwargs):
        """Log debug message with optional extra fields."""
        self.logger.debug(msg, extra={'extra': kwargs})
    
    def info(self, msg: str, **kwargs):
        """Log info message with optional extra fields."""
        self.logger.info(msg, extra={'extra': kwargs})
    
    def warning(self, msg: str, **kwargs):
        """Log warning message with optional extra fields."""
        self.logger.warning(msg, extra={'extra': kwargs})
    
    def error(self, msg: str, **kwargs):
        """Log error message with optional extra fields."""
        self.logger.error(msg, extra={'extra': kwargs})
    
    def critical(self, msg: str, **kwargs):
        """Log critical message with optional extra fields."""
        self.logger.critical(msg, extra={'extra': kwargs})
    
    def log(self, level: int, msg: str, **kwargs):
        """Log message at specified level with optional extra fields."""
        self.logger.log(level, msg, extra={'extra': kwargs})


class PipedreamLogger(StructuredLogger):
    """
    Pipedream-specific logger with workflow tracking.
    
    Adds Pipedream-specific features:
    - Workflow execution tracking
    - Step timing
    - Event correlation
    - $.flow and $.event context
    """
    
    def __init__(
        self,
        workflow_name: str,
        step_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Pipedream logger.
        
        Args:
            workflow_name: Name of the Pipedream workflow
            step_name: Name of the current step
            **kwargs: Additional arguments for StructuredLogger
        """
        super().__init__(
            name=f"pipedream.{workflow_name}",
            json_format=True,  # Always use JSON for Pipedream
            **kwargs
        )
        
        self.workflow_name = workflow_name
        self.step_name = step_name
        
        # Set workflow context
        log_context.set('workflow', workflow_name)
        if step_name:
            log_context.set('step', step_name)
    
    @contextmanager
    def step_context(self, step_name: str, **kwargs):
        """
        Context manager for step execution.
        
        Args:
            step_name: Name of the step
            **kwargs: Additional step context
        """
        previous_step = log_context.get('step')
        log_context.set('step', step_name)
        log_context.update(**kwargs)
        
        self.info(f"Step started: {step_name}")
        start_time = time.time()
        
        try:
            yield
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"Step failed: {step_name}",
                duration_seconds=duration,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            raise
        else:
            duration = time.time() - start_time
            self.info(
                f"Step completed: {step_name}",
                duration_seconds=duration
            )
        finally:
            # Restore previous step
            if previous_step:
                log_context.set('step', previous_step)
            else:
                log_context.data.pop('step', None)
    
    def log_event(self, event_data: Dict[str, Any]):
        """
        Log incoming Pipedream event.
        
        Args:
            event_data: The $.event object
        """
        # Extract key event info
        event_summary = {
            'event_id': event_data.get('id'),
            'event_type': event_data.get('type'),
            'source': event_data.get('source'),
        }
        
        # Add to context
        log_context.set('event_id', event_summary.get('event_id'))
        
        self.info(
            "Processing event",
            **event_summary
        )
    
    def log_flow_data(self, flow_data: Dict[str, Any]):
        """
        Log Pipedream flow data.
        
        Args:
            flow_data: The $.flow object
        """
        self.debug(
            "Flow data",
            flow_keys=list(flow_data.keys()),
            flow_size=len(str(flow_data))
        )


# Convenience functions
def get_logger(
    name: str,
    level: int = logging.INFO,
    **kwargs
) -> StructuredLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name
        level: Logging level
        **kwargs: Additional logger configuration
        
    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, level, **kwargs)


def get_pipedream_logger(
    workflow_name: str,
    step_name: Optional[str] = None,
    **kwargs
) -> PipedreamLogger:
    """
    Get a Pipedream-specific logger.
    
    Args:
        workflow_name: Workflow name
        step_name: Optional step name
        **kwargs: Additional configuration
        
    Returns:
        PipedreamLogger instance
    """
    return PipedreamLogger(workflow_name, step_name, **kwargs)


# Decorators for common use cases
def log_function_call(logger: Optional[StructuredLogger] = None):
    """
    Decorator to log function calls.
    
    Args:
        logger: Optional logger instance (creates one if not provided)
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(
                f"Calling {func.__name__}",
                function=func.__name__,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.debug(
                    f"Function completed: {func.__name__}",
                    function=func.__name__,
                    duration_seconds=duration
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Function failed: {func.__name__}",
                    function=func.__name__,
                    duration_seconds=duration,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )
                raise
        
        return wrapper
    return decorator


def log_api_request(service: str, logger: Optional[StructuredLogger] = None):
    """
    Decorator for logging API requests.
    
    Args:
        service: Service name
        logger: Optional logger instance
    """
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(f"api.{service}")
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to extract endpoint from args/kwargs
            endpoint = kwargs.get('endpoint', args[0] if args else 'unknown')
            method = kwargs.get('method', 'GET')
            
            logger.log_api_call(service, endpoint, method)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Try to extract status code from result
                status_code = getattr(result, 'status_code', 200)
                
                logger.log_api_response(
                    service,
                    status_code,
                    duration
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.log_error_with_context(
                    e,
                    operation=f"{service}_api_call",
                    endpoint=endpoint,
                    method=method,
                    duration_seconds=duration
                )
                raise
        
        return wrapper
    return decorator