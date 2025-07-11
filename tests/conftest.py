"""
pytest configuration and fixtures for AI Gatekeeper tests
"""

import os
import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask

# Set test environment
os.environ['ENVIRONMENT'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['OPENAI_API_KEY'] = 'test-key'

# Import after setting environment
from app import create_app
from db.database import Base
from db.models import SupportTicket, Solution, SupportFeedback, KnowledgeBase
from shared_agents.config.shared_config import SharedConfig
from core.support_request_processor import SupportRequestProcessor
from auth.middleware import JWTManager

@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()

@pytest.fixture
def test_db():
    """Create test database."""
    # Create in-memory SQLite database
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()

@pytest.fixture
def shared_config():
    """Create shared configuration for testing."""
    config = SharedConfig()
    config.environment = 'testing'
    config.debug = True
    return config

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = Mock()
    
    # Mock chat completion
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "Test response"
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock embeddings
    mock_embedding = Mock()
    mock_embedding.data = [Mock()]
    mock_embedding.data[0].embedding = [0.1] * 1536
    mock_client.embeddings.create.return_value = mock_embedding
    
    return mock_client

@pytest.fixture
def mock_support_processor(shared_config, mock_openai_client):
    """Create mock support processor."""
    processor = SupportRequestProcessor(shared_config)
    processor.openai_client = mock_openai_client
    return processor

@pytest.fixture
def jwt_manager():
    """Create JWT manager for testing."""
    return JWTManager(secret_key='test-secret-key')

@pytest.fixture
def admin_token(jwt_manager):
    """Create admin token for testing."""
    return jwt_manager.generate_token(
        user_id='test-admin',
        email='admin@test.com',
        role='admin'
    )

@pytest.fixture
def api_user_token(jwt_manager):
    """Create API user token for testing."""
    return jwt_manager.generate_token(
        user_id='test-user',
        email='user@test.com',
        role='api_user'
    )

@pytest.fixture
def sample_support_ticket(test_db):
    """Create sample support ticket."""
    ticket = SupportTicket(
        message="Test support request",
        user_context={"user_id": "test-user"},
        priority="medium",
        status="new",
        confidence_score=0.8,
        risk_score=0.2
    )
    test_db.add(ticket)
    test_db.commit()
    test_db.refresh(ticket)
    return ticket

@pytest.fixture
def sample_solution(test_db):
    """Create sample solution."""
    solution = Solution(
        title="Test Solution",
        content="This is a test solution",
        solution_type="automated",
        success_rate=0.9,
        usage_count=5
    )
    test_db.add(solution)
    test_db.commit()
    test_db.refresh(solution)
    return solution

@pytest.fixture
def sample_feedback(test_db, sample_support_ticket):
    """Create sample feedback."""
    feedback = SupportFeedback(
        ticket_id=str(sample_support_ticket.id),
        user_satisfaction=4,
        solution_helpful=True,
        comments="Great solution!"
    )
    test_db.add(feedback)
    test_db.commit()
    test_db.refresh(feedback)
    return feedback

@pytest.fixture
def sample_knowledge_base(test_db):
    """Create sample knowledge base item."""
    kb_item = KnowledgeBase(
        title="Test Knowledge",
        content="This is test knowledge",
        category="technical",
        effectiveness_score=0.85,
        usage_count=10
    )
    test_db.add(kb_item)
    test_db.commit()
    test_db.refresh(kb_item)
    return kb_item

@pytest.fixture
def temp_directory():
    """Create temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing."""
    mock_store = Mock()
    mock_store.health_check.return_value = True
    mock_store.search_documents.return_value = [
        {
            'id': 'test-doc-1',
            'content': 'Test document content',
            'metadata': {'title': 'Test Doc'},
            'similarity': 0.85
        }
    ]
    return mock_store

@pytest.fixture
def mock_slack_client():
    """Mock Slack client for testing."""
    mock_client = Mock()
    mock_client.auth_test.return_value = {'user_id': 'test-bot-id'}
    mock_client.users_info.return_value = {
        'user': {'name': 'testuser', 'profile': {'email': 'test@example.com'}}
    }
    mock_client.conversations_info.return_value = {
        'channel': {'name': 'support'}
    }
    return mock_client

# Test data factories
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_support_request_data():
        """Create sample support request data."""
        return {
            'message': 'My application crashes when I try to save files',
            'context': {
                'user_level': 'intermediate',
                'system': 'Windows 10',
                'application': 'Test App v1.0'
            }
        }
    
    @staticmethod
    def create_feedback_data():
        """Create sample feedback data."""
        return {
            'request_id': 'test-request-123',
            'rating': 4,
            'feedback': 'The solution was helpful',
            'outcome': 'resolved',
            'confidence_accuracy': 0.85,
            'solution_helpful': True
        }
    
    @staticmethod
    def create_handoff_data():
        """Create sample handoff data."""
        return {
            'ticket_id': 'test-ticket-123',
            'handoff_reason': 'Complex technical issue',
            'priority': 'high',
            'escalation_type': 'technical',
            'context_notes': 'User experiencing recurring crashes'
        }

@pytest.fixture
def test_data_factory():
    """Provide test data factory."""
    return TestDataFactory

# Mock environment variables
@pytest.fixture
def mock_env_vars():
    """Mock environment variables."""
    with patch.dict(os.environ, {
        'CONFIDENCE_THRESHOLD': '0.8',
        'RISK_THRESHOLD': '0.3',
        'SLACK_BOT_TOKEN': 'xoxb-test-token',
        'SLACK_SIGNING_SECRET': 'test-signing-secret',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'ADMIN_API_KEY': 'test-admin-key'
    }):
        yield