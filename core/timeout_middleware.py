"""
Request Timeout Monitoring Middleware
Tracks and warns about long-running requests
"""

import time
import logging
from flask import g, request
from functools import wraps


def add_timeout_monitoring(app):
    """
    Add timeout monitoring to Flask application.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def start_request_timer():
        """Record request start time."""
        g.request_start_time = time.time()

    @app.after_request
    def check_request_timeout(response):
        """Check if request exceeded timeout threshold."""
        if hasattr(g, 'request_start_time'):
            elapsed = time.time() - g.request_start_time
            timeout_threshold = app.config.get('REQUEST_TIMEOUT', 120)

            # Add timing header
            response.headers['X-Response-Time'] = f"{elapsed:.3f}s"

            # Log warnings for slow requests
            if elapsed > timeout_threshold:
                logging.error(
                    f"Request exceeded timeout threshold",
                    extra={
                        'extra_data': {
                            'event_type': 'timeout_exceeded',
                            'method': request.method,
                            'path': request.path,
                            'elapsed_seconds': elapsed,
                            'threshold_seconds': timeout_threshold,
                            'correlation_id': g.get('correlation_id')
                        }
                    }
                )
            elif elapsed > (timeout_threshold * 0.8):
                # Warning at 80% of timeout
                logging.warning(
                    f"Request approaching timeout threshold",
                    extra={
                        'extra_data': {
                            'event_type': 'timeout_warning',
                            'method': request.method,
                            'path': request.path,
                            'elapsed_seconds': elapsed,
                            'threshold_seconds': timeout_threshold
                        }
                    }
                )

        return response

    logging.info("Timeout monitoring middleware configured")


def timeout_required(timeout_seconds: int = None):
    """
    Decorator to enforce timeout on specific endpoints.

    Args:
        timeout_seconds: Maximum allowed execution time

    Usage:
        @app.route('/api/long-operation')
        @timeout_required(30)
        def long_operation():
            # Must complete in 30 seconds
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import current_app

            timeout = timeout_seconds or current_app.config.get('REQUEST_TIMEOUT', 120)
            start_time = time.time()

            try:
                result = func(*args, **kwargs)

                # Check if timeout was exceeded
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    logging.warning(
                        f"Function {func.__name__} exceeded timeout",
                        extra={
                            'function': func.__name__,
                            'elapsed': elapsed,
                            'timeout': timeout
                        }
                    )

                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logging.error(
                    f"Function {func.__name__} failed after {elapsed:.2f}s",
                    extra={
                        'function': func.__name__,
                        'elapsed': elapsed,
                        'error': str(e)
                    }
                )
                raise

        return wrapper
    return decorator


__all__ = ['add_timeout_monitoring', 'timeout_required']
