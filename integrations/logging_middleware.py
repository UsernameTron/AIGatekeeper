"""
Request Logging Middleware
Adds correlation IDs, request/response logging, and performance tracking
"""

import time
import uuid
import logging
from flask import request, g
from functools import wraps
from core.logging_config import request_id_var, user_id_var, session_id_var


def add_logging_middleware(app):
    """
    Add request logging middleware to Flask app.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request_logging():
        """Log request start and set correlation ID."""
        # Generate or use existing correlation ID
        correlation_id = request.headers.get('X-Correlation-ID')
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        g.correlation_id = correlation_id
        g.request_start_time = time.time()

        # Set context vars for structured logging
        request_id_var.set(correlation_id)

        # Set user context if available
        if hasattr(g, 'user') and g.user:
            user_id = g.user.get('user_id', '')
            user_id_var.set(user_id)

        # Set session context if available
        session_id = request.headers.get('X-Session-ID', '')
        if session_id:
            session_id_var.set(session_id)

        # Log request
        logging.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'extra_data': {
                    'event_type': 'request_start',
                    'correlation_id': correlation_id,
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                    'content_length': request.content_length,
                    'referrer': request.headers.get('Referer', '')
                }
            }
        )

    @app.after_request
    def after_request_logging(response):
        """Log request completion."""
        if hasattr(g, 'correlation_id'):
            response.headers['X-Correlation-ID'] = g.correlation_id

        duration = time.time() - g.get('request_start_time', time.time())
        duration_ms = round(duration * 1000, 2)

        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        logging.log(
            log_level,
            f"Request completed: {request.method} {request.path} - {response.status_code} in {duration_ms}ms",
            extra={
                'extra_data': {
                    'event_type': 'request_complete',
                    'correlation_id': g.get('correlation_id', ''),
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': duration_ms,
                    'content_length': response.content_length
                }
            }
        )

        return response

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Log unhandled exceptions."""
        from flask import jsonify

        correlation_id = g.get('correlation_id', 'unknown')

        logging.error(
            f"Unhandled exception: {str(e)}",
            exc_info=True,
            extra={
                'extra_data': {
                    'event_type': 'unhandled_exception',
                    'correlation_id': correlation_id,
                    'method': request.method,
                    'path': request.path,
                    'exception_type': type(e).__name__,
                    'exception_message': str(e)
                }
            }
        )

        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'correlation_id': correlation_id
        }), 500

    logging.info("Logging middleware configured successfully")


def log_operation(operation_name: str):
    """
    Decorator to log operation execution.

    Args:
        operation_name: Name of the operation

    Usage:
        @log_operation('user_creation')
        def create_user(data):
            # ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            logging.info(
                f"Operation started: {operation_name}",
                extra={
                    'extra_data': {
                        'event_type': 'operation_start',
                        'operation': operation_name
                    }
                }
            )

            try:
                result = func(*args, **kwargs)

                duration = time.time() - start_time
                logging.info(
                    f"Operation completed: {operation_name} in {duration:.2f}s",
                    extra={
                        'extra_data': {
                            'event_type': 'operation_complete',
                            'operation': operation_name,
                            'duration_seconds': duration,
                            'success': True
                        }
                    }
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logging.error(
                    f"Operation failed: {operation_name} after {duration:.2f}s - {str(e)}",
                    exc_info=True,
                    extra={
                        'extra_data': {
                            'event_type': 'operation_failed',
                            'operation': operation_name,
                            'duration_seconds': duration,
                            'success': False,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    }
                )
                raise

        return wrapper
    return decorator


def log_async_operation(operation_name: str):
    """
    Decorator to log async operation execution.

    Args:
        operation_name: Name of the operation

    Usage:
        @log_async_operation('async_user_creation')
        async def create_user_async(data):
            # ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            logging.info(
                f"Async operation started: {operation_name}",
                extra={
                    'extra_data': {
                        'event_type': 'async_operation_start',
                        'operation': operation_name
                    }
                }
            )

            try:
                result = await func(*args, **kwargs)

                duration = time.time() - start_time
                logging.info(
                    f"Async operation completed: {operation_name} in {duration:.2f}s",
                    extra={
                        'extra_data': {
                            'event_type': 'async_operation_complete',
                            'operation': operation_name,
                            'duration_seconds': duration,
                            'success': True
                        }
                    }
                )

                return result

            except Exception as e:
                duration = time.time() - start_time
                logging.error(
                    f"Async operation failed: {operation_name} after {duration:.2f}s - {str(e)}",
                    exc_info=True,
                    extra={
                        'extra_data': {
                            'event_type': 'async_operation_failed',
                            'operation': operation_name,
                            'duration_seconds': duration,
                            'success': False,
                            'error_type': type(e).__name__,
                            'error_message': str(e)
                        }
                    }
                )
                raise

        return wrapper
    return decorator
