"""
Security Headers Middleware
Adds comprehensive security headers to all HTTP responses
"""

import logging
from flask import Flask
import os


def add_security_headers(app: Flask):
    """
    Add security headers to all responses.

    Headers added:
    - Content-Security-Policy: Prevents XSS and injection attacks
    - X-Content-Type-Options: Prevents MIME-sniffing
    - X-Frame-Options: Prevents clickjacking
    - X-XSS-Protection: Legacy XSS protection
    - Strict-Transport-Security: Enforces HTTPS
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features

    Args:
        app: Flask application instance
    """

    # Security headers configuration from environment
    csp_enabled = os.getenv('CSP_ENABLED', 'true').lower() == 'true'
    hsts_enabled = os.getenv('HSTS_ENABLED', 'true').lower() == 'true'
    hsts_max_age = int(os.getenv('HSTS_MAX_AGE', '31536000'))  # 1 year default

    @app.after_request
    def apply_security_headers(response):
        """Apply security headers to response."""

        # Content Security Policy
        if csp_enabled:
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust based on needs
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ]
            response.headers['Content-Security-Policy'] = "; ".join(csp_directives)

        # Prevent MIME-type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'

        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'

        # Legacy XSS protection (for older browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'

        # Strict Transport Security (HSTS)
        if hsts_enabled:
            response.headers['Strict-Transport-Security'] = (
                f'max-age={hsts_max_age}; includeSubDomains; preload'
            )

        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions Policy (formerly Feature-Policy)
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()"
        ]
        response.headers['Permissions-Policy'] = ", ".join(permissions_policy)

        # Additional security headers
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        response.headers['X-Download-Options'] = 'noopen'

        # Remove server header (reduce information disclosure)
        if 'Server' in response.headers:
            response.headers.pop('Server', None)

        # Remove X-Powered-By header if present
        if 'X-Powered-By' in response.headers:
            response.headers.pop('X-Powered-By', None)

        return response

    logging.info("Security headers middleware configured")


def get_security_headers_config() -> dict:
    """
    Get current security headers configuration.

    Returns:
        Dictionary with security headers settings
    """
    return {
        'csp_enabled': os.getenv('CSP_ENABLED', 'true').lower() == 'true',
        'hsts_enabled': os.getenv('HSTS_ENABLED', 'true').lower() == 'true',
        'hsts_max_age': int(os.getenv('HSTS_MAX_AGE', '31536000')),
        'headers': {
            'Content-Security-Policy': 'Configured' if os.getenv('CSP_ENABLED', 'true').lower() == 'true' else 'Disabled',
            'Strict-Transport-Security': 'Configured' if os.getenv('HSTS_ENABLED', 'true').lower() == 'true' else 'Disabled',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'Configured'
        }
    }


__all__ = ['add_security_headers', 'get_security_headers_config']
