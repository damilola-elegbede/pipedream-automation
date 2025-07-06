"""Tests for StructuredLogger module."""

import pytest
import logging
import json
import time
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

from src.utils.structured_logger import (
    LogContext, log_context, StructuredLogger, PipedreamLogger,
    get_logger, get_pipedream_logger, log_function_call, log_api_request
)


class TestLogContext:
    """Test cases for LogContext class."""
    
    def test_init(self):
        """Test LogContext initialization."""
        context = LogContext()
        assert isinstance(context.data, dict)
        assert len(context.data) == 0
    
    def test_set_get(self):
        """Test setting and getting context values."""
        context = LogContext()
        
        context.set('request_id', '123')
        assert context.get('request_id') == '123'
        
        context.set('user_id', 456)
        assert context.get('user_id') == 456
    
    def test_get_default(self):
        """Test getting with default value."""
        context = LogContext()
        
        assert context.get('missing_key') is None
        assert context.get('missing_key', 'default') == 'default'
    
    def test_clear(self):
        """Test clearing context."""
        context = LogContext()
        
        context.set('key1', 'value1')
        context.set('key2', 'value2')
        
        context.clear()
        assert len(context.data) == 0
    
    def test_update(self):
        """Test updating multiple values."""
        context = LogContext()
        
        context.update(
            request_id='123',
            user_id=456,
            service='notion'
        )
        
        assert context.get('request_id') == '123'
        assert context.get('user_id') == 456
        assert context.get('service') == 'notion'
    
    def test_thread_safety(self):
        """Test thread-local storage."""
        context = LogContext()
        
        # Set value in main thread
        context.set('main_thread', 'value1')
        
        # Values set in different thread
        from threading import Thread
        
        def set_in_thread():
            context.set('other_thread', 'value2')
            assert context.get('other_thread') == 'value2'
            # Should not see main thread value
            assert context.get('main_thread') is None
        
        thread = Thread(target=set_in_thread)
        thread.start()
        thread.join()
        
        # Main thread should not see other thread value
        assert context.get('other_thread') is None
        assert context.get('main_thread') == 'value1'


class TestStructuredLogger:
    """Test cases for StructuredLogger class."""
    
    def test_init_defaults(self):
        """Test StructuredLogger initialization with defaults."""
        logger = StructuredLogger('test_logger')
        
        assert logger.logger.name == 'test_logger'
        assert logger.logger.level == logging.INFO
        assert logger.json_format is True
        assert logger.include_timestamp is True
        assert logger.include_caller is True
    
    def test_init_custom(self):
        """Test StructuredLogger initialization with custom settings."""
        logger = StructuredLogger(
            'custom_logger',
            level=logging.DEBUG,
            json_format=False,
            include_timestamp=False,
            include_caller=False
        )
        
        assert logger.logger.level == logging.DEBUG
        assert logger.json_format is False
        assert logger.include_timestamp is False
        assert logger.include_caller is False
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_json_logging(self, mock_stderr):
        """Test JSON formatted logging."""
        logger = StructuredLogger('json_test', json_format=True)
        
        logger.info('Test message', user_id=123, action='test')
        
        output = mock_stderr.getvalue()
        log_data = json.loads(output.strip())
        
        assert log_data['level'] == 'INFO'
        assert log_data['message'] == 'Test message'
        assert log_data['logger'] == 'json_test'
        assert log_data['user_id'] == 123
        assert log_data['action'] == 'test'
        assert 'timestamp' in log_data
        assert 'caller' in log_data
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_text_logging(self, mock_stderr):
        """Test text formatted logging."""
        logger = StructuredLogger('text_test', json_format=False)
        
        logger.info('Test message')
        
        output = mock_stderr.getvalue()
        assert '[INFO]' in output
        assert 'text_test' in output
        assert 'Test message' in output
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_request_context(self, mock_stderr):
        """Test request context management."""
        logger = StructuredLogger('context_test')
        
        with logger.request_context(request_id='req-123', user_id=456):
            logger.info('Inside request')
            
            # Check context is set
            assert log_context.get('request_id') == 'req-123'
            assert log_context.get('user_id') == 456
        
        # Context should be cleared after exit
        assert log_context.get('request_id') is None
        assert log_context.get('user_id') is None
        
        # Check logs
        logs = [json.loads(line) for line in mock_stderr.getvalue().strip().split('\n')]
        
        # Should have start and end logs
        assert len(logs) >= 3
        assert 'Request started' in logs[0]['message']
        assert 'Inside request' in logs[1]['message']
        assert 'Request completed' in logs[2]['message']
        assert 'duration_seconds' in logs[2]
    
    def test_log_operation_decorator_success(self):
        """Test log_operation decorator with successful execution."""
        logger = StructuredLogger('operation_test')
        
        @logger.log_operation('test_operation')
        def successful_operation():
            return 'success'
        
        with patch.object(logger, 'info') as mock_info:
            result = successful_operation()
            
            assert result == 'success'
            assert mock_info.call_count == 2
            
            # Check start log
            start_call = mock_info.call_args_list[0]
            assert 'Starting operation: test_operation' in start_call[0][0]
            
            # Check completion log
            end_call = mock_info.call_args_list[1]
            assert 'Operation completed: test_operation' in end_call[0][0]
            assert end_call[1]['status'] == 'success'
            assert 'duration_seconds' in end_call[1]
    
    def test_log_operation_decorator_failure(self):
        """Test log_operation decorator with failure."""
        logger = StructuredLogger('operation_test')
        
        @logger.log_operation('failing_operation')
        def failing_operation():
            raise ValueError('Test error')
        
        with patch.object(logger, 'info') as mock_info:
            with patch.object(logger, 'error') as mock_error:
                with pytest.raises(ValueError):
                    failing_operation()
                
                # Should log start
                assert mock_info.call_count == 1
                
                # Should log error
                assert mock_error.call_count == 1
                error_call = mock_error.call_args_list[0]
                assert 'Operation failed: failing_operation' in error_call[0][0]
                assert error_call[1]['status'] == 'failed'
                assert error_call[1]['error_type'] == 'ValueError'
                assert error_call[1]['error_message'] == 'Test error'
    
    def test_log_api_call(self):
        """Test API call logging."""
        logger = StructuredLogger('api_test')
        
        with patch.object(logger, 'info') as mock_info:
            logger.log_api_call(
                'notion',
                '/v1/pages',
                'POST',
                payload_size=1024
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert 'API call to notion' in call_args[0][0]
            assert call_args[1]['service'] == 'notion'
            assert call_args[1]['endpoint'] == '/v1/pages'
            assert call_args[1]['method'] == 'POST'
            assert call_args[1]['payload_size'] == 1024
    
    def test_log_api_response(self):
        """Test API response logging."""
        logger = StructuredLogger('api_test')
        
        # Test successful response
        with patch.object(logger, 'log') as mock_log:
            logger.log_api_response('gmail', 200, 0.5)
            
            mock_log.assert_called_once_with(
                logging.INFO,
                'API response from gmail',
                service='gmail',
                status_code=200,
                duration_seconds=0.5
            )
        
        # Test error response
        with patch.object(logger, 'log') as mock_log:
            logger.log_api_response('openai', 429, 1.2)
            
            mock_log.assert_called_once_with(
                logging.WARNING,
                'API response from openai',
                service='openai',
                status_code=429,
                duration_seconds=1.2
            )
    
    def test_log_error_with_context(self):
        """Test error logging with context."""
        logger = StructuredLogger('error_test')
        
        # Create error with response
        error = Mock()
        error.__class__.__name__ = 'APIError'
        error.response = Mock(
            status_code=404,
            text='{"error": "Not found"}'
        )
        
        with patch.object(logger, 'error') as mock_error:
            logger.log_error_with_context(
                error,
                operation='fetch_page',
                page_id='123'
            )
            
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            
            assert 'Error in fetch_page' in call_args[0][0]
            assert call_args[1]['error_type'] == 'APIError'
            assert call_args[1]['operation'] == 'fetch_page'
            assert call_args[1]['page_id'] == '123'
            assert call_args[1]['status_code'] == 404
            assert '{"error": "Not found"}' in call_args[1]['response_body']
    
    def test_log_performance_metric(self):
        """Test performance metric logging."""
        logger = StructuredLogger('perf_test')
        
        with patch.object(logger, 'info') as mock_info:
            logger.log_performance_metric(
                'api_latency',
                0.234,
                unit='seconds',
                service='notion',
                endpoint='/v1/pages'
            )
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            
            assert 'Performance metric: api_latency' in call_args[0][0]
            assert call_args[1]['metric_name'] == 'api_latency'
            assert call_args[1]['metric_value'] == 0.234
            assert call_args[1]['metric_unit'] == 'seconds'
            assert call_args[1]['service'] == 'notion'
    
    def test_standard_logging_methods(self):
        """Test standard logging methods."""
        logger = StructuredLogger('standard_test')
        
        with patch.object(logger.logger, 'debug') as mock_debug:
            logger.debug('Debug message', extra_field='value')
            mock_debug.assert_called_once_with(
                'Debug message',
                extra={'extra': {'extra_field': 'value'}}
            )
        
        with patch.object(logger.logger, 'info') as mock_info:
            logger.info('Info message')
            mock_info.assert_called_once_with('Info message', extra={'extra': {}})
        
        with patch.object(logger.logger, 'warning') as mock_warning:
            logger.warning('Warning message')
            mock_warning.assert_called_once()
        
        with patch.object(logger.logger, 'error') as mock_error:
            logger.error('Error message')
            mock_error.assert_called_once()
        
        with patch.object(logger.logger, 'critical') as mock_critical:
            logger.critical('Critical message')
            mock_critical.assert_called_once()


class TestPipedreamLogger:
    """Test cases for PipedreamLogger class."""
    
    def setup_method(self):
        """Setup method to clear context before each test."""
        log_context.clear()
    
    def test_init(self):
        """Test PipedreamLogger initialization."""
        logger = PipedreamLogger('test_workflow', 'test_step')
        
        assert logger.logger.name == 'pipedream.test_workflow'
        assert logger.workflow_name == 'test_workflow'
        assert logger.step_name == 'test_step'
        assert logger.json_format is True
        
        # Check context
        assert log_context.get('workflow') == 'test_workflow'
        assert log_context.get('step') == 'test_step'
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_step_context_success(self, mock_stderr):
        """Test step context with successful execution."""
        logger = PipedreamLogger('workflow1')
        
        with logger.step_context('process_data', input_size=100):
            logger.info('Processing data')
            assert log_context.get('step') == 'process_data'
            assert log_context.get('input_size') == 100
        
        # Step should be cleared
        assert log_context.get('step') is None
        
        # Check logs
        logs = [json.loads(line) for line in mock_stderr.getvalue().strip().split('\n')]
        
        assert any('Step started: process_data' in log['message'] for log in logs)
        assert any('Step completed: process_data' in log['message'] for log in logs)
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_step_context_failure(self, mock_stderr):
        """Test step context with failure."""
        logger = PipedreamLogger('workflow1')
        
        with pytest.raises(ValueError):
            with logger.step_context('failing_step'):
                raise ValueError('Step error')
        
        # Check error was logged
        logs = [json.loads(line) for line in mock_stderr.getvalue().strip().split('\n')]
        
        error_logs = [log for log in logs if log['level'] == 'ERROR']
        assert len(error_logs) == 1
        assert 'Step failed: failing_step' in error_logs[0]['message']
        assert error_logs[0]['error_type'] == 'ValueError'
    
    def test_log_event(self):
        """Test event logging."""
        logger = PipedreamLogger('workflow1')
        
        event_data = {
            'id': 'evt_123',
            'type': 'http',
            'source': 'webhook',
            'body': {'key': 'value'}
        }
        
        with patch.object(logger, 'info') as mock_info:
            logger.log_event(event_data)
            
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            
            assert 'Processing event' in call_args[0][0]
            assert call_args[1]['event_id'] == 'evt_123'
            assert call_args[1]['event_type'] == 'http'
            assert call_args[1]['source'] == 'webhook'
            
            # Check context
            assert log_context.get('event_id') == 'evt_123'
    
    def test_log_flow_data(self):
        """Test flow data logging."""
        logger = PipedreamLogger('workflow1')
        
        flow_data = {
            'step1': {'result': 'data1'},
            'step2': {'result': 'data2'},
            'step3': {'result': 'data3'}
        }
        
        with patch.object(logger, 'debug') as mock_debug:
            logger.log_flow_data(flow_data)
            
            mock_debug.assert_called_once()
            call_args = mock_debug.call_args
            
            assert 'Flow data' in call_args[0][0]
            assert call_args[1]['flow_keys'] == ['step1', 'step2', 'step3']
            assert call_args[1]['flow_size'] > 0


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_logger(self):
        """Test get_logger function."""
        logger = get_logger('test_module', level=logging.DEBUG)
        
        assert isinstance(logger, StructuredLogger)
        assert logger.logger.name == 'test_module'
        assert logger.logger.level == logging.DEBUG
    
    def test_get_pipedream_logger(self):
        """Test get_pipedream_logger function."""
        logger = get_pipedream_logger('my_workflow', 'my_step')
        
        assert isinstance(logger, PipedreamLogger)
        assert logger.workflow_name == 'my_workflow'
        assert logger.step_name == 'my_step'
    
    def test_log_function_call_decorator(self):
        """Test log_function_call decorator."""
        logger = StructuredLogger('decorator_test')
        
        @log_function_call(logger)
        def test_function(arg1, arg2, key='value'):
            return f"{arg1}-{arg2}-{key}"
        
        with patch.object(logger, 'debug') as mock_debug:
            result = test_function('a', 'b', key='c')
            
            assert result == 'a-b-c'
            assert mock_debug.call_count == 2
            
            # Check function call log
            call_log = mock_debug.call_args_list[0]
            assert 'Calling test_function' in call_log[0][0]
            assert call_log[1]['function'] == 'test_function'
            assert call_log[1]['args_count'] == 2
            assert call_log[1]['kwargs_keys'] == ['key']
            
            # Check completion log
            complete_log = mock_debug.call_args_list[1]
            assert 'Function completed: test_function' in complete_log[0][0]
            assert 'duration_seconds' in complete_log[1]
    
    def test_log_function_call_decorator_failure(self):
        """Test log_function_call decorator with failure."""
        @log_function_call()
        def failing_function():
            raise RuntimeError('Function failed')
        
        # Logger should be created automatically
        with pytest.raises(RuntimeError):
            failing_function()
    
    def test_log_api_request_decorator(self):
        """Test log_api_request decorator."""
        logger = StructuredLogger('api_decorator_test')
        
        @log_api_request('notion', logger)
        def api_call(endpoint, method='GET'):
            response = Mock(status_code=200)
            return response
        
        with patch.object(logger, 'log_api_call') as mock_api_call:
            with patch.object(logger, 'log_api_response') as mock_api_response:
                result = api_call('/v1/pages', method='POST')
                
                assert result.status_code == 200
                
                # Check API call log
                mock_api_call.assert_called_once_with(
                    'notion',
                    '/v1/pages',
                    'POST'
                )
                
                # Check API response log
                mock_api_response.assert_called_once()
                call_args = mock_api_response.call_args[0]
                assert call_args[0] == 'notion'
                assert call_args[1] == 200
                assert call_args[2] > 0  # duration
    
    def test_log_api_request_decorator_failure(self):
        """Test log_api_request decorator with API failure."""
        @log_api_request('gmail')
        def failing_api_call(endpoint):
            raise ConnectionError('API unavailable')
        
        with pytest.raises(ConnectionError):
            failing_api_call('/v1/messages')


class TestIntegrationScenarios:
    """Integration tests for real-world logging scenarios."""
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_complete_request_flow(self, mock_stderr):
        """Test complete request flow with structured logging."""
        logger = StructuredLogger('integration_test')
        
        with logger.request_context(request_id='req-456', user_id='user-123'):
            # Log API call
            logger.log_api_call('notion', '/v1/databases/db-123', 'GET')
            
            # Simulate processing
            time.sleep(0.01)
            
            # Log API response
            logger.log_api_response('notion', 200, 0.1)
            
            # Log performance metric
            logger.log_performance_metric('db_query_time', 0.05)
        
        # Parse all logs
        logs = [json.loads(line) for line in mock_stderr.getvalue().strip().split('\n')]
        
        # Verify all logs have request context
        for log in logs:
            if 'context' in log:
                assert log['context']['request_id'] == 'req-456'
                assert log['context']['user_id'] == 'user-123'
    
    @patch('sys.stderr', new_callable=StringIO)
    def test_pipedream_workflow_execution(self, mock_stderr):
        """Test Pipedream workflow execution logging."""
        logger = get_pipedream_logger('data_sync_workflow')
        
        # Log event
        logger.log_event({
            'id': 'evt-789',
            'type': 'schedule',
            'source': 'cron'
        })
        
        # Execute steps
        with logger.step_context('fetch_data'):
            logger.info('Fetching data from source')
            time.sleep(0.01)
        
        with logger.step_context('transform_data'):
            logger.info('Transforming data')
            time.sleep(0.01)
        
        # Test error handling in step
        try:
            with logger.step_context('save_data'):
                logger.info('Saving to destination')
                # Simulate error
                raise ValueError('Database connection failed')
        except ValueError as e:
            logger.log_error_with_context(e, operation='database_write')
    
    def test_concurrent_context_isolation(self):
        """Test context isolation in concurrent execution."""
        logger = StructuredLogger('concurrent_test')
        
        from threading import Thread
        import queue
        
        results = queue.Queue()
        
        def worker(worker_id):
            with logger.request_context(request_id=f'req-{worker_id}'):
                time.sleep(0.01)
                # Each worker should see only its own context
                results.put(log_context.get('request_id'))
        
        # Start multiple workers
        threads = []
        for i in range(5):
            t = Thread(target=worker, args=(i,))
            t.start()
            threads.append(t)
        
        # Wait for all to complete
        for t in threads:
            t.join()
        
        # Collect results
        worker_results = []
        while not results.empty():
            worker_results.append(results.get())
        
        # Each worker should have seen its own request ID
        assert sorted(worker_results) == ['req-0', 'req-1', 'req-2', 'req-3', 'req-4']