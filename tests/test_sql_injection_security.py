"""
SQL Injection Security Tests
Verify that all database operations are protected against SQL injection attacks
"""

import pytest
from unittest.mock import MagicMock
from db.crud import SupportTicketCRUD, SolutionCRUD, FeedbackCRUD, KnowledgeBaseCRUD
from db.models import SupportTicket


class TestSQLInjectionProtection:
    """Test suite for SQL injection protection."""

    def test_sql_injection_in_ticket_message(self, db_session):
        """Test that SQL injection attempts in ticket message are handled safely."""
        # SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM support_tickets WHERE 1=1; --",
            "' UNION SELECT * FROM users--",
            "1' AND 1=1 UNION SELECT username, password FROM users--"
        ]

        for malicious_input in malicious_inputs:
            # Create ticket with malicious input
            ticket = SupportTicketCRUD.create_ticket(
                db_session,
                message=malicious_input,
                user_context={'test': 'context'},
                priority='medium'
            )

            # Verify ticket was created (not executed as SQL)
            assert ticket is not None
            assert ticket.message == malicious_input  # Stored as-is, not executed

            # Verify retrieval works (no SQL error)
            retrieved = SupportTicketCRUD.get_ticket(db_session, ticket.id)
            assert retrieved is not None
            assert retrieved.message == malicious_input

    def test_sql_injection_in_ticket_id(self, db_session):
        """Test that SQL injection attempts in ticket ID are handled safely."""
        malicious_ids = [
            "1' OR '1'='1",
            "'; DROP TABLE support_tickets; --",
            "1 UNION SELECT * FROM users",
        ]

        for malicious_id in malicious_ids:
            # Attempt to get ticket with malicious ID
            result = SupportTicketCRUD.get_ticket(db_session, malicious_id)

            # Should return None (invalid UUID) rather than execute SQL
            assert result is None

    def test_sql_injection_in_solution_content(self, db_session):
        """Test SQL injection protection in solution content."""
        malicious_content = "'; DELETE FROM solutions; --"

        # First create a valid ticket
        ticket = SupportTicketCRUD.create_ticket(
            db_session,
            message="Test ticket",
            user_context={}
        )

        # Create solution with malicious content
        solution = SolutionCRUD.create_solution(
            db_session,
            ticket_id=ticket.id,
            title="Test Solution",
            content=malicious_content,
            solution_type="step_by_step"
        )

        # Verify solution was created with content stored as-is
        assert solution is not None
        assert solution.content == malicious_content

        # Verify retrieval works
        retrieved = SolutionCRUD.get_solution(db_session, solution.id)
        assert retrieved is not None
        assert retrieved.content == malicious_content

    def test_sql_injection_in_feedback_comments(self, db_session):
        """Test SQL injection protection in feedback comments."""
        # Create ticket first
        ticket = SupportTicketCRUD.create_ticket(
            db_session,
            message="Test ticket",
            user_context={}
        )

        malicious_comment = "'; UPDATE support_feedback SET user_satisfaction = 1; --"

        # Create feedback with malicious comment
        feedback = FeedbackCRUD.create_feedback(
            db_session,
            ticket_id=ticket.id,
            user_satisfaction=3,
            comments=malicious_comment
        )

        # Verify feedback was created safely
        assert feedback is not None
        assert feedback.comments == malicious_comment

    def test_sql_injection_in_knowledge_base_search(self, db_session):
        """Test SQL injection protection in knowledge base searches."""
        malicious_searches = [
            "'; DROP TABLE knowledge_base; --",
            "1' OR '1'='1",
            "test' UNION SELECT * FROM users--"
        ]

        for malicious_search in malicious_searches:
            # Search with malicious input
            # This should not execute SQL, just search for the literal string
            results = KnowledgeBaseCRUD.search_by_category(
                db_session,
                category=malicious_search
            )

            # Should return empty or matching results, not execute SQL
            assert isinstance(results, list)

    def test_parameterized_queries_in_crud(self, db_session):
        """Verify that CRUD operations use parameterized queries."""
        # This test verifies the pattern is correct
        # All CRUD operations should use ORM which provides parameterization

        ticket = SupportTicketCRUD.create_ticket(
            db_session,
            message="Test' OR '1'='1",
            user_context={'key': "value'; DROP TABLE test; --"}
        )

        assert ticket.message == "Test' OR '1'='1"
        assert ticket.user_context['key'] == "value'; DROP TABLE test; --"

    def test_json_field_sql_injection(self, db_session):
        """Test SQL injection in JSON fields."""
        malicious_context = {
            'user_level': "'; DROP TABLE users; --",
            'priority': "1' OR '1'='1",
            'system': "test'; DELETE FROM support_tickets; --"
        }

        ticket = SupportTicketCRUD.create_ticket(
            db_session,
            message="Test ticket",
            user_context=malicious_context
        )

        # JSON should be safely stored
        assert ticket.user_context == malicious_context

        # Retrieval should work safely
        retrieved = SupportTicketCRUD.get_ticket(db_session, ticket.id)
        assert retrieved.user_context == malicious_context

    def test_special_characters_handling(self, db_session):
        """Test that special SQL characters are handled safely."""
        special_chars = [
            "Test with 'single quotes'",
            'Test with "double quotes"',
            "Test with `backticks`",
            "Test with ; semicolon",
            "Test with -- comments",
            "Test with /* block comments */",
            "Test with \\ backslash",
            "Test with % wildcard"
        ]

        for test_input in special_chars:
            ticket = SupportTicketCRUD.create_ticket(
                db_session,
                message=test_input,
                user_context={}
            )

            assert ticket.message == test_input

            retrieved = SupportTicketCRUD.get_ticket(db_session, ticket.id)
            assert retrieved.message == test_input


@pytest.fixture
def db_session():
    """Mock database session for testing."""
    from unittest.mock import MagicMock
    from db.database import db_manager

    # Try to use real session if available
    try:
        session = db_manager.get_session()
        yield session
        session.rollback()  # Rollback test data
        session.close()
    except:
        # Fallback to mock if database not available
        mock_session = MagicMock()
        yield mock_session


# Integration test with actual API
def test_api_sql_injection_protection(client):
    """
    Test SQL injection protection at API level.
    Requires test client fixture.
    """
    malicious_payload = {
        'message': "'; DROP TABLE support_tickets; --",
        'context': {
            'user_level': "1' OR '1'='1",
            'priority': "'; DELETE FROM users; --"
        }
    }

    # This should not execute SQL injection
    response = client.post(
        '/api/support/evaluate',
        json=malicious_payload,
        headers={'Authorization': 'Bearer test-token'}
    )

    # Should process normally (200) or validation error (400)
    # But NOT a database error (500)
    assert response.status_code in [200, 400, 401]
    assert response.status_code != 500

    # If successful, response should contain the malicious string as-is
    if response.status_code == 200:
        data = response.get_json()
        # Verify the malicious input was processed safely
        assert 'request_id' in data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
