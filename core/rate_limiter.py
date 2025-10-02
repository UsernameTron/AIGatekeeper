"""
Rate limiting configuration for AI Gatekeeper
Protects against DoS attacks and ensures fair resource usage
"""

import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, g


def get_user_identifier():
    """
    Get user identifier for rate limiting.
    Uses authenticated user ID if available, otherwise falls back to IP address.
    """
    # Try to get authenticated user first
    if hasattr(g, 'user') and g.user:
        user_id = g.user.get('user_id')
        if user_id:
            return f"user:{user_id}"

    # Fall back to IP address
    return f"ip:{get_remote_address()}"


# Initialize rate limiter
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[
        "1000 per day",   # Daily limit
        "100 per hour",   # Hourly limit
        "10 per minute"   # Minute limit for burst protection
    ],
    storage_uri=os.getenv('RATE_LIMIT_STORAGE_URI', 'memory://'),
    # Use Redis for production: redis://localhost:6379
    strategy="fixed-window",
    headers_enabled=True,  # Add rate limit headers to responses
    swallow_errors=True    # Don't crash if rate limiter fails
)


# Custom rate limit configurations for different endpoint types
RATE_LIMITS = {
    # AI Processing endpoints (more expensive)
    'ai_processing': [
        "100 per day",
        "20 per hour",
        "5 per minute"
    ],

    # Authentication endpoints
    'authentication': [
        "20 per hour",
        "5 per minute"
    ],

    # Feedback endpoints (less critical)
    'feedback': [
        "500 per day",
        "50 per hour"
    ],

    # Status/monitoring endpoints (read-only, cheap)
    'status': [
        "2000 per day",
        "200 per hour",
        "30 per minute"
    ],

    # Health checks (very frequent, public)
    'health': [
        "10000 per day",
        "1000 per hour"
    ]
}


def get_rate_limit(limit_type: str) -> list:
    """
    Get rate limit configuration for a specific endpoint type.

    Args:
        limit_type: Type of rate limit to apply

    Returns:
        List of rate limit strings
    """
    return RATE_LIMITS.get(limit_type, limiter._default_limits)


def init_rate_limiter(app):
    """
    Initialize rate limiter with Flask app.

    Args:
        app: Flask application instance
    """
    limiter.init_app(app)

    # Add rate limit exceeded handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        from flask import jsonify
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': 'You have exceeded the rate limit. Please try again later.',
            'retry_after': e.description
        }), 429

    return limiter
