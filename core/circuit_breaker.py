"""
Circuit Breaker Implementation for External Service Calls
Provides fault tolerance and prevents cascading failures
"""

import logging
import time
from typing import Callable, Any
from functools import wraps
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import openai


class ServiceUnavailableError(Exception):
    """Raised when a service is unavailable due to circuit breaker."""
    pass


# Configure circuit breakers for different services
openai_breaker = CircuitBreaker(
    fail_max=5,  # Open circuit after 5 consecutive failures
    reset_timeout=60,  # Keep circuit open for 60 seconds
    name='openai_api',
    listeners=[
        lambda cb, exc, *args: logging.warning(
            f"Circuit breaker '{cb.name}' state changed"
        )
    ]
)

database_breaker = CircuitBreaker(
    fail_max=3,
    reset_timeout=30,
    name='database',
    listeners=[
        lambda cb, exc, *args: logging.error(
            f"Database circuit breaker opened"
        )
    ]
)

vector_store_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=45,
    name='vector_store'
)


def with_circuit_breaker(breaker: CircuitBreaker, service_name: str = None):
    """
    Decorator to protect function calls with a circuit breaker.

    Args:
        breaker: CircuitBreaker instance to use
        service_name: Name of the service for error messages

    Usage:
        @with_circuit_breaker(openai_breaker, 'OpenAI')
        async def call_openai_api():
            # Your OpenAI call here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                # Use circuit breaker to protect the call
                result = await breaker.call_async(func, *args, **kwargs)
                return result
            except CircuitBreakerError as e:
                service = service_name or breaker.name
                error_msg = f"{service} service temporarily unavailable (circuit breaker open)"
                logging.error(
                    error_msg,
                    extra={
                        'circuit_breaker': breaker.name,
                        'state': breaker.current_state,
                        'fail_counter': breaker.fail_counter
                    }
                )
                raise ServiceUnavailableError(error_msg) from e
            except Exception as e:
                # Let other exceptions propagate
                logging.error(
                    f"Error in {service_name or breaker.name} call: {e}",
                    extra={'circuit_breaker': breaker.name}
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = breaker.call(func, *args, **kwargs)
                return result
            except CircuitBreakerError as e:
                service = service_name or breaker.name
                error_msg = f"{service} service temporarily unavailable (circuit breaker open)"
                logging.error(
                    error_msg,
                    extra={
                        'circuit_breaker': breaker.name,
                        'state': breaker.current_state,
                        'fail_counter': breaker.fail_counter
                    }
                )
                raise ServiceUnavailableError(error_msg) from e
            except Exception as e:
                logging.error(
                    f"Error in {service_name or breaker.name} call: {e}",
                    extra={'circuit_breaker': breaker.name}
                )
                raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def with_retry(max_attempts: int = 3, min_wait: int = 1, max_wait: int = 10):
    """
    Decorator to add retry logic with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time between retries (seconds)
        max_wait: Maximum wait time between retries (seconds)

    Usage:
        @with_retry(max_attempts=3)
        @with_circuit_breaker(openai_breaker)
        async def call_openai():
            pass
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
        retry=retry_if_exception_type((openai.APIError, openai.RateLimitError)),
        before_sleep=lambda retry_state: logging.warning(
            f"Retrying after failure (attempt {retry_state.attempt_number}/{max_attempts})",
            extra={'attempt': retry_state.attempt_number}
        )
    )


def get_circuit_breaker_status(breaker: CircuitBreaker) -> dict:
    """
    Get current status of a circuit breaker.

    Args:
        breaker: CircuitBreaker instance

    Returns:
        Dictionary with breaker status information
    """
    return {
        'name': breaker.name,
        'state': breaker.current_state.name if hasattr(breaker.current_state, 'name') else str(breaker.current_state),
        'fail_counter': breaker.fail_counter,
        'fail_max': breaker.fail_max,
        'reset_timeout': breaker.reset_timeout,
        'last_failure': None  # pybreaker doesn't expose this directly
    }


def get_all_circuit_breakers_status() -> dict:
    """Get status of all registered circuit breakers."""
    return {
        'openai': get_circuit_breaker_status(openai_breaker),
        'database': get_circuit_breaker_status(database_breaker),
        'vector_store': get_circuit_breaker_status(vector_store_breaker)
    }


def reset_circuit_breaker(breaker: CircuitBreaker):
    """
    Manually reset a circuit breaker.
    Use with caution - only reset if you're sure the service is healthy.
    """
    try:
        breaker.close()
        logging.info(f"Circuit breaker '{breaker.name}' manually reset")
    except Exception as e:
        logging.error(f"Failed to reset circuit breaker '{breaker.name}': {e}")


# Monitoring function for metrics system
def track_circuit_breaker_metrics():
    """
    Track circuit breaker states in metrics system.
    Called periodically by monitoring system.
    """
    try:
        from monitoring.metrics_system import metrics_collector

        for name, breaker in [
            ('openai', openai_breaker),
            ('database', database_breaker),
            ('vector_store', vector_store_breaker)
        ]:
            # Track state (1 = closed/healthy, 0 = open/unhealthy)
            state_value = 1 if breaker.current_state == 'closed' else 0
            metrics_collector.gauge(
                'circuit_breaker_state',
                state_value,
                {'breaker': name}
            )

            # Track failure count
            metrics_collector.gauge(
                'circuit_breaker_failures',
                breaker.fail_counter,
                {'breaker': name}
            )

    except Exception as e:
        logging.debug(f"Error tracking circuit breaker metrics: {e}")


__all__ = [
    'with_circuit_breaker',
    'with_retry',
    'openai_breaker',
    'database_breaker',
    'vector_store_breaker',
    'ServiceUnavailableError',
    'get_circuit_breaker_status',
    'get_all_circuit_breakers_status',
    'reset_circuit_breaker',
    'track_circuit_breaker_metrics'
]
