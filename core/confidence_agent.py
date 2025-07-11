"""
Confidence Scoring Agent - Core implementation for request similarity matching
"""

import numpy as np
import openai
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import logging
from datetime import datetime

@dataclass
class SimilarityMatch:
    content: str
    similarity_score: float
    metadata: Dict[str, Any]

@dataclass
class ConfidenceResult:
    confidence_score: float
    primary_matches: List[SimilarityMatch]
    reasoning: str
    factors: Dict[str, float]

class ConfidenceAgent:
    """Agent that scores confidence by comparing requests to knowledge base"""
    
    def __init__(self, openai_client, embedding_model="text-embedding-3-small"):
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self.knowledge_embeddings = {}
        self.knowledge_content = {}
        
    async def load_knowledge_base(self, knowledge_items: List[Dict[str, Any]]):
        """Load knowledge base and generate embeddings"""
        logging.info(f"Loading {len(knowledge_items)} knowledge items...")
        
        for item in knowledge_items:
            item_id = item['id']
            content = item['content']
            
            # Generate embedding
            embedding = await self._get_embedding(content)
            
            self.knowledge_embeddings[item_id] = embedding
            self.knowledge_content[item_id] = item
            
        logging.info("Knowledge base loaded successfully")
    
    async def score_confidence(self, request: str, context: Dict[str, Any] = None) -> ConfidenceResult:
        """Main method to score confidence for a request"""
        
        # Get request embedding
        request_embedding = await self._get_embedding(request)
        
        # Find similar items
        similarities = await self._calculate_similarities(request_embedding)
        
        # Calculate confidence factors
        factors = await self._calculate_confidence_factors(request, similarities, context or {})
        
        # Compute final confidence score
        confidence_score = await self._compute_final_score(factors)
        
        # Get top matches for explanation
        top_matches = self._get_top_matches(similarities, limit=3)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(factors, top_matches)
        
        return ConfidenceResult(
            confidence_score=confidence_score,
            primary_matches=top_matches,
            reasoning=reasoning,
            factors=factors
        )
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text.strip()
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logging.error(f"Embedding generation failed: {e}")
            raise
    
    async def _calculate_similarities(self, request_embedding: np.ndarray) -> List[Tuple[str, float]]:
        """Calculate cosine similarities with knowledge base"""
        similarities = []
        
        for item_id, kb_embedding in self.knowledge_embeddings.items():
            similarity = self._cosine_similarity(request_embedding, kb_embedding)
            similarities.append((item_id, similarity))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    async def _calculate_confidence_factors(self, request: str, similarities: List[Tuple[str, float]], context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate various confidence factors"""
        
        # Factor 1: Best similarity match
        best_similarity = similarities[0][1] if similarities else 0.0
        
        # Factor 2: Multiple good matches (consensus)
        good_matches = [s for _, s in similarities[:5] if s > 0.7]
        consensus_factor = min(len(good_matches) / 3.0, 1.0)
        
        # Factor 3: Request complexity (simple requests = higher confidence)
        complexity_factor = await self._assess_request_complexity(request)
        
        # Factor 4: User experience level
        user_level = context.get('user_level', 'intermediate')
        user_factor = {'beginner': 0.8, 'intermediate': 1.0, 'advanced': 1.1}.get(user_level, 1.0)
        
        # Factor 5: Request clarity
        clarity_factor = await self._assess_request_clarity(request)
        
        return {
            'similarity': best_similarity,
            'consensus': consensus_factor,
            'complexity': complexity_factor,
            'user_level': user_factor,
            'clarity': clarity_factor
        }
    
    async def _compute_final_score(self, factors: Dict[str, float]) -> float:
        """Compute weighted final confidence score"""
        
        # Weighted combination of factors
        weights = {
            'similarity': 0.4,    # Primary factor
            'consensus': 0.2,     # Multiple matches
            'complexity': 0.2,    # Request complexity
            'user_level': 0.1,    # User experience
            'clarity': 0.1        # Request clarity
        }
        
        weighted_score = sum(factors[factor] * weights[factor] for factor in weights)
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, weighted_score))
    
    async def _assess_request_complexity(self, request: str) -> float:
        """Assess request complexity (simple = higher confidence)"""
        # Simple heuristics
        word_count = len(request.split())
        
        if word_count <= 10:
            return 1.0  # Simple request
        elif word_count <= 20:
            return 0.8  # Medium complexity
        else:
            return 0.6  # Complex request
    
    async def _assess_request_clarity(self, request: str) -> float:
        """Assess how clear the request is"""
        # Check for question words, clear intent
        clarity_indicators = ['how', 'what', 'why', 'when', 'where', 'help', 'issue', 'problem']
        
        request_lower = request.lower()
        indicator_count = sum(1 for indicator in clarity_indicators if indicator in request_lower)
        
        return min(indicator_count / 2.0, 1.0)
    
    def _get_top_matches(self, similarities: List[Tuple[str, float]], limit: int = 3) -> List[SimilarityMatch]:
        """Get top similarity matches"""
        matches = []
        
        for item_id, similarity in similarities[:limit]:
            if item_id in self.knowledge_content:
                content_item = self.knowledge_content[item_id]
                match = SimilarityMatch(
                    content=content_item.get('content', '')[:200] + '...',
                    similarity_score=similarity,
                    metadata=content_item.get('metadata', {})
                )
                matches.append(match)
        
        return matches
    
    def _generate_reasoning(self, factors: Dict[str, float], matches: List[SimilarityMatch]) -> str:
        """Generate human-readable reasoning for the confidence score"""
        
        similarity = factors['similarity']
        consensus = factors['consensus']
        
        if similarity > 0.8:
            similarity_desc = "very similar to known solutions"
        elif similarity > 0.6:
            similarity_desc = "moderately similar to known solutions"
        else:
            similarity_desc = "limited similarity to known solutions"
        
        if consensus > 0.7:
            consensus_desc = "with strong consensus from multiple sources"
        elif consensus > 0.4:
            consensus_desc = "with moderate consensus"
        else:
            consensus_desc = "with limited consensus"
        
        return f"Request is {similarity_desc} {consensus_desc}. Top match: {matches[0].content[:100] + '...' if matches else 'None'}"