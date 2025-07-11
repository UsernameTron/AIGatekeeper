#!/usr/bin/env python3
"""
Comprehensive tests for Confidence Agent
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.confidence_agent import ConfidenceAgent, ConfidenceResult, SimilarityMatch
from knowledge.knowledge_loader import KnowledgeLoader

class TestConfidenceAgent:
    
    @pytest.fixture
    def mock_openai_client(self):
        client = Mock()
        client.embeddings = Mock()
        client.embeddings.create = AsyncMock()
        
        # Mock embedding response
        mock_response = Mock()
        mock_response.data = [Mock()]
        mock_response.data[0].embedding = [0.1] * 1536  # Standard embedding size
        client.embeddings.create.return_value = mock_response
        
        return client
    
    @pytest.fixture
    async def confidence_agent(self, mock_openai_client):
        agent = ConfidenceAgent(mock_openai_client)
        
        # Load test knowledge
        knowledge_items = await KnowledgeLoader.load_sample_knowledge()
        await agent.load_knowledge_base(knowledge_items)
        
        return agent
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, mock_openai_client):
        agent = ConfidenceAgent(mock_openai_client)
        assert agent.openai_client == mock_openai_client
        assert agent.embedding_model == "text-embedding-3-small"
        assert len(agent.knowledge_embeddings) == 0
    
    @pytest.mark.asyncio
    async def test_knowledge_base_loading(self, mock_openai_client):
        agent = ConfidenceAgent(mock_openai_client)
        
        knowledge_items = await KnowledgeLoader.load_sample_knowledge()
        await agent.load_knowledge_base(knowledge_items)
        
        assert len(agent.knowledge_embeddings) == len(knowledge_items)
        assert len(agent.knowledge_content) == len(knowledge_items)
    
    @pytest.mark.asyncio
    async def test_confidence_scoring_password_reset(self, confidence_agent):
        request = "I forgot my password and need to reset it"
        
        result = await confidence_agent.score_confidence(request)
        
        assert isinstance(result, ConfidenceResult)
        assert 0.0 <= result.confidence_score <= 1.0
        assert len(result.primary_matches) > 0
        assert result.reasoning is not None
        assert 'similarity' in result.factors
        
        # Should have high confidence for password reset
        assert result.confidence_score > 0.6
    
    @pytest.mark.asyncio
    async def test_confidence_scoring_complex_request(self, confidence_agent):
        request = "I'm having a very complex issue with my custom enterprise integration that involves multiple APIs and complex authentication protocols"
        
        result = await confidence_agent.score_confidence(request)
        
        assert isinstance(result, ConfidenceResult)
        assert 0.0 <= result.confidence_score <= 1.0
        
        # Should have lower confidence for complex request
        assert result.confidence_score < 0.8
    
    @pytest.mark.asyncio
    async def test_confidence_factors_calculation(self, confidence_agent):
        request = "How do I reset my password?"
        context = {'user_level': 'beginner'}
        
        result = await confidence_agent.score_confidence(request, context)
        
        factors = result.factors
        assert 'similarity' in factors
        assert 'consensus' in factors
        assert 'complexity' in factors
        assert 'user_level' in factors
        assert 'clarity' in factors
        
        # All factors should be valid
        for factor_value in factors.values():
            assert 0.0 <= factor_value <= 2.0  # Some factors can be > 1.0
    
    @pytest.mark.asyncio
    async def test_user_level_impact(self, confidence_agent):
        request = "How do I configure email settings?"
        
        # Test beginner user
        result_beginner = await confidence_agent.score_confidence(
            request, {'user_level': 'beginner'}
        )
        
        # Test advanced user
        result_advanced = await confidence_agent.score_confidence(
            request, {'user_level': 'advanced'}
        )
        
        # Advanced users should get slightly higher confidence
        assert result_advanced.confidence_score >= result_beginner.confidence_score
    
    def test_cosine_similarity_calculation(self, confidence_agent):
        vec1 = np.array([1, 0, 0])
        vec2 = np.array([1, 0, 0])  # Identical
        vec3 = np.array([0, 1, 0])  # Orthogonal
        
        # Identical vectors should have similarity = 1
        similarity_identical = confidence_agent._cosine_similarity(vec1, vec2)
        assert abs(similarity_identical - 1.0) < 0.001
        
        # Orthogonal vectors should have similarity = 0
        similarity_orthogonal = confidence_agent._cosine_similarity(vec1, vec3)
        assert abs(similarity_orthogonal - 0.0) < 0.001
    
    @pytest.mark.asyncio
    async def test_request_complexity_assessment(self, confidence_agent):
        # Simple request
        simple_complexity = await confidence_agent._assess_request_complexity("Reset password")
        assert simple_complexity == 1.0
        
        # Complex request
        complex_request = "I need help with a complex multi-step integration process involving multiple third-party services and custom authentication"
        complex_complexity = await confidence_agent._assess_request_complexity(complex_request)
        assert complex_complexity < 1.0
    
    @pytest.mark.asyncio
    async def test_request_clarity_assessment(self, confidence_agent):
        # Clear request
        clear_request = "How do I reset my password?"
        clear_score = await confidence_agent._assess_request_clarity(clear_request)
        assert clear_score > 0.0
        
        # Unclear request
        unclear_request = "Things are broken and stuff doesn't work"
        unclear_score = await confidence_agent._assess_request_clarity(unclear_request)
        assert unclear_score <= clear_score

class TestKnowledgeLoader:
    
    @pytest.mark.asyncio
    async def test_load_sample_knowledge(self):
        knowledge_items = await KnowledgeLoader.load_sample_knowledge()
        
        assert len(knowledge_items) > 0
        
        # Check structure of first item
        item = knowledge_items[0]
        assert 'id' in item
        assert 'content' in item
        assert 'title' in item
        assert 'category' in item
        assert 'keywords' in item
        assert 'metadata' in item
    
    @pytest.mark.asyncio
    async def test_knowledge_content_quality(self):
        knowledge_items = await KnowledgeLoader.load_sample_knowledge()
        
        for item in knowledge_items:
            # Each item should have substantial content
            assert len(item['content']) > 50
            
            # Should have relevant keywords
            assert len(item['keywords']) > 0
            
            # Should have proper metadata
            assert 'difficulty' in item['metadata']
            assert 'category' in item['metadata']

class TestIntegration:
    
    @pytest.mark.asyncio
    async def test_end_to_end_confidence_workflow(self, mock_openai_client):
        """Test complete workflow from request to confidence score"""
        
        # Initialize agent
        agent = ConfidenceAgent(mock_openai_client)
        
        # Load knowledge
        knowledge_items = await KnowledgeLoader.load_sample_knowledge()
        await agent.load_knowledge_base(knowledge_items)
        
        # Test various requests
        test_requests = [
            "How do I reset my password?",
            "My application keeps crashing",
            "I need help with network connectivity",
            "Email setup is not working",
            "Complex custom integration issue"
        ]
        
        for request in test_requests:
            result = await agent.score_confidence(request)
            
            # Validate result structure
            assert isinstance(result, ConfidenceResult)
            assert 0.0 <= result.confidence_score <= 1.0
            assert len(result.primary_matches) > 0
            assert result.reasoning is not None
            assert len(result.factors) == 5
            
            print(f"Request: {request}")
            print(f"Confidence: {result.confidence_score:.3f}")
            print(f"Reasoning: {result.reasoning}")
            print("-" * 50)

def run_manual_tests():
    """Run manual tests with real OpenAI API (if available)"""
    
    import openai
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("No OpenAI API key found, skipping manual tests")
        return
    
    async def manual_test():
        client = openai.AsyncOpenAI(api_key=api_key)
        agent = ConfidenceAgent(client)
        
        # Load knowledge
        knowledge_items = await KnowledgeLoader.load_sample_knowledge()
        await agent.load_knowledge_base(knowledge_items)
        
        # Test real requests
        test_requests = [
            "I can't log in to my account",
            "My computer is running very slowly",
            "How do I set up my email?",
            "The application crashed when I tried to save",
            "I need to integrate our system with a third-party API using OAuth2"
        ]
        
        print("\n🧪 Manual Tests with Real OpenAI API")
        print("=" * 50)
        
        for request in test_requests:
            result = await agent.score_confidence(request)
            
            print(f"\nRequest: {request}")
            print(f"Confidence: {result.confidence_score:.3f}")
            print(f"Top match: {result.primary_matches[0].content[:100]}...")
            print(f"Similarity: {result.primary_matches[0].similarity_score:.3f}")
            print(f"Reasoning: {result.reasoning}")
            print("-" * 30)
    
    # Run manual test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(manual_test())
    finally:
        loop.close()

if __name__ == "__main__":
    # Run pytest
    pytest.main([__file__, "-v"])
    
    # Run manual tests if API key available
    run_manual_tests()