"""
Input validation for database operations
Prevents SQL injection and validates data integrity
"""

import re
import uuid
from typing import Any, List, Optional
from sqlalchemy import or_


class InputValidator:
    """Validates and sanitizes user inputs for database operations."""

    # SQL keywords that should trigger warnings
    SQL_KEYWORDS = [
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE',
        'EXEC', 'EXECUTE', 'UNION', 'SELECT', '--', ';', '/*', '*/', 'XP_',
        'SP_', 'SCRIPT', 'JAVASCRIPT', 'VBSCRIPT'
    ]

    # Allowed categories for knowledge base and solutions
    ALLOWED_CATEGORIES = [
        'technical_solutions',
        'troubleshooting_guides',
        'configuration_guides',
        'user_documentation',
        'escalation_procedures',
        'best_practices',
        'common_issues',
        'system_requirements',
        'installation_guides',
        'api_documentation'
    ]

    # Maximum lengths for various fields
    MAX_LENGTHS = {
        'search_query': 500,
        'title': 200,
        'content': 50000,
        'category': 100,
        'keyword': 100,
        'comment': 5000,
    }

    @staticmethod
    def validate_uuid(value: str, field_name: str = "ID") -> uuid.UUID:
        """
        Validate and convert UUID string.

        Args:
            value: UUID string to validate
            field_name: Name of field for error messages

        Returns:
            UUID object

        Raises:
            ValueError: If UUID is invalid
        """
        if not value:
            raise ValueError(f"{field_name} cannot be empty")

        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError) as e:
            raise ValueError(f"Invalid {field_name} format: {value}") from e

    @staticmethod
    def validate_search_query(query: str) -> str:
        """
        Validate and sanitize search query.

        Args:
            query: Search query string

        Returns:
            Sanitized query string

        Raises:
            ValueError: If query is invalid or contains SQL injection patterns
        """
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Remove leading/trailing whitespace
        query = query.strip()

        # Check length
        max_len = InputValidator.MAX_LENGTHS['search_query']
        if len(query) > max_len:
            raise ValueError(
                f"Search query too long (max {max_len} characters, got {len(query)})"
            )

        # Check for SQL injection patterns (case-insensitive)
        query_upper = query.upper()
        for keyword in InputValidator.SQL_KEYWORDS:
            # Check for keyword as whole word or with special characters
            pattern = r'\b' + re.escape(keyword) + r'\b|' + re.escape(keyword)
            if re.search(pattern, query_upper):
                raise ValueError(
                    f"Invalid search query: contains restricted pattern '{keyword}'"
                )

        # Check for suspicious patterns
        suspicious_patterns = [
            r'1\s*=\s*1',  # 1=1
            r'1\s*=\s*0',  # 1=0
            r'\'\s*OR\s*\'',  # ' OR '
            r'\'\s*AND\s*\'',  # ' AND '
            r'0x[0-9a-fA-F]+',  # Hex values
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise ValueError(
                    f"Invalid search query: contains suspicious pattern"
                )

        return query

    @staticmethod
    def validate_category(category: str) -> str:
        """
        Validate category against allowlist.

        Args:
            category: Category name to validate

        Returns:
            Validated category string

        Raises:
            ValueError: If category is not in allowlist
        """
        if not category or not category.strip():
            raise ValueError("Category cannot be empty")

        category = category.strip().lower()

        if category not in InputValidator.ALLOWED_CATEGORIES:
            raise ValueError(
                f"Invalid category: {category}. "
                f"Allowed: {', '.join(InputValidator.ALLOWED_CATEGORIES)}"
            )

        return category

    @staticmethod
    def sanitize_string(value: str, max_length: int = None,
                       field_name: str = "field") -> str:
        """
        Sanitize string input.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length
            field_name: Field name for error messages

        Returns:
            Sanitized string

        Raises:
            ValueError: If validation fails
        """
        if value is None:
            return ""

        if not isinstance(value, str):
            value = str(value)

        # Remove any null bytes
        value = value.replace('\x00', '')

        # Strip leading/trailing whitespace
        value = value.strip()

        # Check length
        if max_length and len(value) > max_length:
            raise ValueError(
                f"{field_name} too long (max {max_length} characters, got {len(value)})"
            )

        return value

    @staticmethod
    def validate_integer(value: Any, min_val: int = None, max_val: int = None,
                        field_name: str = "value") -> int:
        """
        Validate integer input.

        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Field name for error messages

        Returns:
            Validated integer

        Raises:
            ValueError: If validation fails
        """
        try:
            int_val = int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"{field_name} must be an integer") from e

        if min_val is not None and int_val < min_val:
            raise ValueError(f"{field_name} must be >= {min_val}")

        if max_val is not None and int_val > max_val:
            raise ValueError(f"{field_name} must be <= {max_val}")

        return int_val

    @staticmethod
    def validate_float(value: Any, min_val: float = None, max_val: float = None,
                      field_name: str = "value") -> float:
        """
        Validate float input.

        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Field name for error messages

        Returns:
            Validated float

        Raises:
            ValueError: If validation fails
        """
        try:
            float_val = float(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"{field_name} must be a number") from e

        if min_val is not None and float_val < min_val:
            raise ValueError(f"{field_name} must be >= {min_val}")

        if max_val is not None and float_val > max_val:
            raise ValueError(f"{field_name} must be <= {max_val}")

        return float_val

    @staticmethod
    def validate_list(value: Any, max_items: int = None,
                     field_name: str = "list") -> List:
        """
        Validate list input.

        Args:
            value: Value to validate
            max_items: Maximum allowed items
            field_name: Field name for error messages

        Returns:
            Validated list

        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, list):
            raise ValueError(f"{field_name} must be a list")

        if max_items and len(value) > max_items:
            raise ValueError(
                f"{field_name} has too many items (max {max_items}, got {len(value)})"
            )

        return value

    @staticmethod
    def create_safe_search_filter(model_class, query: str, search_fields: List[str]):
        """
        Create a safe SQLAlchemy filter for text search using parameterized queries.

        Args:
            model_class: SQLAlchemy model class
            query: Validated search query
            search_fields: List of field names to search

        Returns:
            SQLAlchemy filter expression

        Example:
            filter = InputValidator.create_safe_search_filter(
                Solution,
                validated_query,
                ['content', 'title']
            )
            results = db.query(Solution).filter(filter).all()
        """
        # Query is already validated by validate_search_query
        search_pattern = f"%{query}%"

        # Build OR conditions for each search field
        conditions = []
        for field_name in search_fields:
            field = getattr(model_class, field_name)
            conditions.append(field.ilike(search_pattern))

        return or_(*conditions)
