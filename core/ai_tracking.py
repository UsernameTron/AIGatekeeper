"""
AI Tracking Utilities
Helper functions to track OpenAI API usage in agents
"""

import logging
from typing import Any, Optional
from monitoring.ai_metrics import ai_metrics_tracker


def track_openai_completion(response: Any, agent_type: Optional[str] = None):
    """
    Track OpenAI completion response.

    Args:
        response: OpenAI API response object
        agent_type: Optional agent type for categorization
    """
    try:
        if hasattr(response, 'usage') and response.usage:
            model = getattr(response, 'model', 'unknown')
            prompt_tokens = response.usage.prompt_tokens
            completion_tokens = response.usage.completion_tokens

            ai_metrics_tracker.track_completion(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                agent_type=agent_type
            )

            logging.debug(
                f"Tracked AI usage: model={model}, prompt_tokens={prompt_tokens}, "
                f"completion_tokens={completion_tokens}, agent={agent_type}"
            )
    except Exception as e:
        logging.warning(f"Failed to track AI usage: {e}")


def track_openai_embedding(response: Any, agent_type: Optional[str] = None):
    """
    Track OpenAI embedding response.

    Args:
        response: OpenAI API response object
        agent_type: Optional agent type for categorization
    """
    try:
        if hasattr(response, 'usage') and response.usage:
            model = getattr(response, 'model', 'unknown')
            tokens = response.usage.total_tokens

            ai_metrics_tracker.track_embedding(
                model=model,
                tokens=tokens,
                agent_type=agent_type
            )

            logging.debug(
                f"Tracked embedding usage: model={model}, tokens={tokens}, agent={agent_type}"
            )
    except Exception as e:
        logging.warning(f"Failed to track embedding usage: {e}")


# Decorator for tracking AI calls
def track_ai_call(agent_type: Optional[str] = None):
    """
    Decorator to automatically track AI API calls.

    Args:
        agent_type: Optional agent type for categorization

    Usage:
        @track_ai_call(agent_type='triage')
        async def my_ai_function():
            response = await openai_client.chat.completions.create(...)
            return response
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            response = await func(*args, **kwargs)
            track_openai_completion(response, agent_type)
            return response

        def sync_wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            track_openai_completion(response, agent_type)
            return response

        # Check if function is async
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
