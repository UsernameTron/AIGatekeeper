"""
Request validation for API endpoints
Prevents injection attacks, validates data integrity, and sanitizes inputs
"""

from typing import Dict, Any, List
from flask import request
import bleach
import re


class RequestValidator:
    """Comprehensive request validation for API endpoints."""

    MAX_MESSAGE_LENGTH = 10000  # 10KB
    MAX_CONTEXT_SIZE = 5000     # 5KB
    MAX_FEEDBACK_LENGTH = 5000
    ALLOWED_CONTENT_TYPES = ['application/json']

    @classmethod
    def validate_support_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate support request payload.

        Args:
            data: Request data dictionary

        Returns:
            Validated and sanitized data

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Check content type
        if request.content_type not in cls.ALLOWED_CONTENT_TYPES:
            errors.append(f"Invalid content-type: {request.content_type}")

        # Check payload size
        if request.content_length and request.content_length > 50000:
            errors.append("Payload too large (max 50KB)")

        # Validate message
        message = data.get('message', '').strip()
        if not message:
            errors.append("Message is required")
        elif len(message) > cls.MAX_MESSAGE_LENGTH:
            errors.append(f"Message too long (max {cls.MAX_MESSAGE_LENGTH} chars)")
        else:
            # Sanitize HTML
            message = bleach.clean(message, tags=[], strip=True)
            data['message'] = message

        # Validate context
        context = data.get('context', {})
        if not isinstance(context, dict):
            errors.append("Context must be a dictionary")
        else:
            # Validate context size
            context_str = str(context)
            if len(context_str) > cls.MAX_CONTEXT_SIZE:
                errors.append(f"Context too large (max {cls.MAX_CONTEXT_SIZE} chars)")

            # Validate user_level
            if 'user_level' in context:
                allowed_levels = ['beginner', 'intermediate', 'advanced']
                if context['user_level'] not in allowed_levels:
                    errors.append(f"Invalid user_level: {context['user_level']}")

            # Validate priority
            if 'priority' in context:
                allowed_priorities = ['low', 'medium', 'high', 'critical']
                if context['priority'] not in allowed_priorities:
                    errors.append(f"Invalid priority: {context['priority']}")

            # Sanitize system field
            if 'system' in context:
                context['system'] = bleach.clean(str(context['system']), tags=[], strip=True)[:500]

        if errors:
            raise ValueError("; ".join(errors))

        return data

    @classmethod
    def validate_uuid(cls, uuid_str: str, field_name: str = "ID") -> str:
        """
        Validate UUID format.

        Args:
            uuid_str: UUID string to validate
            field_name: Name of field for error messages

        Returns:
            Validated UUID string

        Raises:
            ValueError: If UUID format is invalid
        """
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, uuid_str.lower()):
            raise ValueError(f"Invalid {field_name} format")
        return uuid_str

    @classmethod
    def validate_feedback(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate feedback payload.

        Args:
            data: Feedback data dictionary

        Returns:
            Validated and sanitized data

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Validate request_id
        request_id = data.get('request_id', '').strip()
        if not request_id:
            errors.append("request_id is required")
        else:
            try:
                cls.validate_uuid(request_id, "request_id")
            except ValueError as e:
                errors.append(str(e))

        # Validate rating
        rating = data.get('rating')
        if rating is not None:
            if not isinstance(rating, int) or rating < 1 or rating > 5:
                errors.append("rating must be an integer between 1 and 5")

        # Validate and sanitize feedback text
        feedback_text = data.get('feedback', '').strip()
        if feedback_text:
            if len(feedback_text) > cls.MAX_FEEDBACK_LENGTH:
                errors.append(f"feedback text too long (max {cls.MAX_FEEDBACK_LENGTH} chars)")
            else:
                data['feedback'] = bleach.clean(feedback_text, tags=[], strip=True)

        # Validate outcome
        outcome = data.get('outcome')
        if outcome:
            allowed_outcomes = ['resolved', 'not_resolved', 'partially_resolved']
            if outcome not in allowed_outcomes:
                errors.append(f"Invalid outcome: {outcome}")

        # Validate confidence_accuracy
        confidence_accuracy = data.get('confidence_accuracy')
        if confidence_accuracy is not None:
            if not isinstance(confidence_accuracy, (int, float)) or confidence_accuracy < 0 or confidence_accuracy > 1:
                errors.append("confidence_accuracy must be between 0.0 and 1.0")

        if errors:
            raise ValueError("; ".join(errors))

        return data

    @classmethod
    def validate_solution_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate solution generation request.

        Args:
            data: Solution request data

        Returns:
            Validated and sanitized data

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Validate request_id
        request_id = data.get('request_id', '').strip()
        if not request_id:
            errors.append("request_id is required")
        else:
            try:
                cls.validate_uuid(request_id, "request_id")
            except ValueError as e:
                errors.append(str(e))

        # Validate include_alternatives flag
        include_alternatives = data.get('include_alternatives')
        if include_alternatives is not None and not isinstance(include_alternatives, bool):
            errors.append("include_alternatives must be a boolean")

        if errors:
            raise ValueError("; ".join(errors))

        return data

    @classmethod
    def validate_handoff_request(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate human handoff request.

        Args:
            data: Handoff request data

        Returns:
            Validated and sanitized data

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Validate request_id
        request_id = data.get('request_id', '').strip()
        if not request_id:
            errors.append("request_id is required")
        else:
            try:
                cls.validate_uuid(request_id, "request_id")
            except ValueError as e:
                errors.append(str(e))

        # Validate and sanitize reason
        reason = data.get('reason', '').strip()
        if reason:
            if len(reason) > 1000:
                errors.append("reason too long (max 1000 chars)")
            else:
                data['reason'] = bleach.clean(reason, tags=[], strip=True)

        # Validate and sanitize notes
        notes = data.get('notes', '').strip()
        if notes:
            if len(notes) > 5000:
                errors.append("notes too long (max 5000 chars)")
            else:
                data['notes'] = bleach.clean(notes, tags=[], strip=True)

        if errors:
            raise ValueError("; ".join(errors))

        return data


def limit_content_length(max_length: int):
    """
    Decorator to limit request content length.

    Args:
        max_length: Maximum content length in bytes

    Returns:
        Decorator function
    """
    def decorator(f):
        from functools import wraps

        @wraps(f)
        def wrapper(*args, **kwargs):
            if request.content_length and request.content_length > max_length:
                from flask import jsonify
                return jsonify({
                    'error': 'Request entity too large',
                    'max_size': max_length,
                    'actual_size': request.content_length
                }), 413
            return f(*args, **kwargs)
        return wrapper
    return decorator
