"""
SQL Injection Prevention Tests
Tests that input validation prevents SQL injection attacks
"""

import pytest
from db.validators import InputValidator
from db.crud import SolutionCRUD, KnowledgeBaseCRUD


class TestSQLInjectionPrevention:
    """Test suite for SQL injection prevention."""

    # Common SQL injection payloads
    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE solutions--",
        "1' AND '1'='1",
        "admin'--",
        "' OR 1=1--",
        "' UNION SELECT NULL--",
        "'; DELETE FROM solutions WHERE '1'='1",
        "1' EXEC sp_executesql--",
        "' OR EXISTS(SELECT * FROM users)--",
        "1'; INSERT INTO solutions VALUES('hacked')--",
        "0x31 OR 1=1",
        "' OR ''='",
        "1' OR '1'='1' /*",
        "'; EXEC xp_cmdshell('dir')--",
    ]

    def test_search_query_validation_blocks_sql_injection(self):
        """Test that common SQL injection patterns are blocked."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            with pytest.raises(ValueError, match="Invalid search query|contains restricted"):
                InputValidator.validate_search_query(payload)

    def test_search_query_allows_legitimate_queries(self):
        """Test that legitimate search queries are allowed."""
        legitimate_queries = [
            "password reset",
            "how to configure email",
            "application crash",
            "installation guide",
            "API documentation",
            "user management",
        ]

        for query in legitimate_queries:
            # Should not raise an exception
            validated = InputValidator.validate_search_query(query)
            assert validated == query

    def test_search_query_length_validation(self):
        """Test that excessively long queries are rejected."""
        # Query longer than MAX_LENGTHS['search_query'] (500)
        long_query = "a" * 501

        with pytest.raises(ValueError, match="too long"):
            InputValidator.validate_search_query(long_query)

    def test_search_query_empty_validation(self):
        """Test that empty queries are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            InputValidator.validate_search_query("")

        with pytest.raises(ValueError, match="cannot be empty"):
            InputValidator.validate_search_query("   ")

    def test_category_validation_blocks_injection(self):
        """Test that category validation blocks SQL injection."""
        malicious_categories = [
            "technical'; DROP TABLE--",
            "' OR '1'='1",
            "UNION SELECT * FROM--",
        ]

        for category in malicious_categories:
            with pytest.raises(ValueError, match="Invalid category"):
                InputValidator.validate_category(category)

    def test_category_allowlist_enforcement(self):
        """Test that only allowed categories are accepted."""
        # Valid categories
        valid_categories = [
            "technical_solutions",
            "troubleshooting_guides",
            "configuration_guides",
        ]

        for category in valid_categories:
            validated = InputValidator.validate_category(category)
            assert validated == category

        # Invalid category
        with pytest.raises(ValueError, match="Invalid category"):
            InputValidator.validate_category("malicious_category")

    def test_uuid_validation(self):
        """Test UUID validation."""
        # Valid UUIDs
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        validated = InputValidator.validate_uuid(valid_uuid)
        assert str(validated) == valid_uuid

        # Invalid UUIDs (potential injection attempts)
        invalid_uuids = [
            "' OR '1'='1",
            "550e8400'; DROP TABLE--",
            "not-a-uuid",
            "12345",
            "",
        ]

        for invalid in invalid_uuids:
            with pytest.raises(ValueError, match="Invalid.*format|cannot be empty"):
                InputValidator.validate_uuid(invalid)

    def test_integer_validation(self):
        """Test integer validation."""
        # Valid integers
        assert InputValidator.validate_integer("10", min_val=1, max_val=100) == 10
        assert InputValidator.validate_integer(50) == 50

        # Invalid integers
        with pytest.raises(ValueError):
            InputValidator.validate_integer("'; DROP TABLE--")

        with pytest.raises(ValueError):
            InputValidator.validate_integer("not-a-number")

        # Out of range
        with pytest.raises(ValueError, match="must be >="):
            InputValidator.validate_integer(0, min_val=1)

        with pytest.raises(ValueError, match="must be <="):
            InputValidator.validate_integer(101, max_val=100)

    def test_safe_search_filter_creation(self):
        """Test that safe search filters are created correctly."""
        from db.models import Solution

        # This should not raise an exception
        validated_query = InputValidator.validate_search_query("password reset")
        search_filter = InputValidator.create_safe_search_filter(
            Solution,
            validated_query,
            ['content', 'title']
        )

        # The filter should be a valid SQLAlchemy expression
        assert search_filter is not None

    def test_suspicious_patterns_blocked(self):
        """Test that suspicious patterns are blocked."""
        suspicious_patterns = [
            "1=1",
            "1=0",
            "' OR '",
            "' AND '",
            "0x414243",  # Hex value
        ]

        for pattern in suspicious_patterns:
            with pytest.raises(ValueError, match="Invalid search query|suspicious"):
                InputValidator.validate_search_query(pattern)

    def test_sql_keywords_blocked(self):
        """Test that SQL keywords are blocked."""
        sql_keywords = [
            "DROP TABLE users",
            "DELETE FROM solutions",
            "INSERT INTO solutions",
            "UPDATE solutions SET",
            "ALTER TABLE solutions",
            "TRUNCATE TABLE solutions",
            "EXEC sp_executesql",
            "UNION SELECT",
            "/* comment */",
            "-- comment",
        ]

        for keyword in sql_keywords:
            with pytest.raises(ValueError, match="contains restricted"):
                InputValidator.validate_search_query(keyword)

    def test_case_insensitive_validation(self):
        """Test that validation is case-insensitive."""
        # Different cases of DROP should all be blocked
        drop_variants = [
            "drop table",
            "DROP TABLE",
            "DrOp TaBlE",
            "dRoP tAbLe",
        ]

        for variant in drop_variants:
            with pytest.raises(ValueError):
                InputValidator.validate_search_query(variant)

    def test_string_sanitization(self):
        """Test string sanitization."""
        # Null bytes should be removed
        value_with_null = "test\x00value"
        sanitized = InputValidator.sanitize_string(value_with_null)
        assert '\x00' not in sanitized

        # Whitespace should be trimmed
        value_with_whitespace = "  test value  "
        sanitized = InputValidator.sanitize_string(value_with_whitespace)
        assert sanitized == "test value"

        # Length validation
        long_value = "a" * 1000
        with pytest.raises(ValueError, match="too long"):
            InputValidator.sanitize_string(long_value, max_length=100)


class TestCRUDSecurty:
    """Test that CRUD operations are protected against SQL injection."""

    def test_search_solutions_validates_input(self):
        """Test that search_solutions validates and sanitizes input."""
        # This test verifies that the method will reject malicious input
        # even before database interaction

        # Mock database session
        from unittest.mock import Mock
        db = Mock()

        # SQL injection attempt should raise ValueError
        with pytest.raises(ValueError):
            SolutionCRUD.search_solutions(db, "' OR '1'='1")

        with pytest.raises(ValueError):
            SolutionCRUD.search_solutions(db, "'; DROP TABLE--")

    def test_search_knowledge_validates_input(self):
        """Test that search_knowledge validates and sanitizes input."""
        from unittest.mock import Mock
        db = Mock()

        # SQL injection attempt should raise ValueError
        with pytest.raises(ValueError):
            KnowledgeBaseCRUD.search_knowledge(db, "' OR '1'='1")

        with pytest.raises(ValueError):
            KnowledgeBaseCRUD.search_knowledge(db, "UNION SELECT--")

    def test_search_with_malicious_category(self):
        """Test that malicious category values are rejected."""
        from unittest.mock import Mock
        db = Mock()

        with pytest.raises(ValueError, match="Invalid category"):
            SolutionCRUD.search_solutions(
                db,
                "legitimate query",
                category="'; DROP TABLE--"
            )

    def test_search_with_malicious_limit(self):
        """Test that malicious limit values are rejected."""
        from unittest.mock import Mock
        db = Mock()

        # String that's not a number
        with pytest.raises(ValueError):
            SolutionCRUD.search_solutions(
                db,
                "legitimate query",
                limit="'; DROP TABLE--"
            )

        # Negative limit
        with pytest.raises(ValueError):
            SolutionCRUD.search_solutions(
                db,
                "legitimate query",
                limit=-1
            )

        # Excessive limit
        with pytest.raises(ValueError):
            SolutionCRUD.search_solutions(
                db,
                "legitimate query",
                limit=10000
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
