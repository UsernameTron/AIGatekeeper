"""
Enhanced Confidence Agent with Advanced Learning and Prediction
"""

import numpy as np
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging
import sys
import os

# Add shared agents to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared_agents'))

from shared_agents.core.agent_factory import AgentBase, AgentResponse, AgentCapability

@dataclass
class PredictionModel:
    feature_weights: Dict[str, float]
    bias: float
    accuracy_history: List[float]
    last_updated: datetime

class EnhancedConfidenceAgent(AgentBase):
    """
    Advanced confidence agent with machine learning and predictive capabilities
    """
    
    REQUIRED_CONFIG_FIELDS = ['openai_client']
    DEFAULT_CAPABILITIES = [
        AgentCapability.VECTOR_SEARCH,
        AgentCapability.RAG_PROCESSING,
        AgentCapability.DATA_PROCESSING
    ]
    
    def __init__(self, name: str, agent_type: str, config: Dict[str, Any]):
        super().__init__(name, agent_type, config, self.DEFAULT_CAPABILITIES)
        
        self.openai_client = config['openai_client']
        self.embedding_model = config.get('embedding_model', 'text-embedding-3-small')
        
        # Knowledge base and embeddings
        self.knowledge_embeddings = {}
        self.knowledge_content = {}
        
        # Advanced learning components
        self.prediction_model = PredictionModel(
            feature_weights={
                'similarity': 0.4,
                'consensus': 0.2,
                'complexity': 0.15,
                'user_match': 0.15,
                'historical': 0.1
            },
            bias=0.0,
            accuracy_history=[],
            last_updated=datetime.now()
        )
        
        self.confidence_history = []
        self.outcome_feedback = []
        
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Execute enhanced confidence scoring with learning"""
        
        request_text = input_data.get('query', input_data.get('support_request', ''))
        user_context = input_data.get('context', {})
        
        if not request_text:
            raise ValueError("No request text provided for confidence scoring")
        
        # Generate comprehensive confidence analysis
        confidence_analysis = await self._comprehensive_confidence_analysis(request_text, user_context)
        
        # Apply predictive modeling
        predicted_confidence = await self._apply_predictive_model(confidence_analysis)
        
        # Generate confidence reasoning
        reasoning = await self._generate_confidence_reasoning(confidence_analysis, predicted_confidence)
        
        # Store for learning
        await self._store_confidence_decision(request_text, confidence_analysis, predicted_confidence)
        
        result = {
            'confidence_score': predicted_confidence,
            'analysis': confidence_analysis,
            'reasoning': reasoning,
            'prediction_factors': confidence_analysis['factors'],
            'model_accuracy': np.mean(self.prediction_model.accuracy_history) if self.prediction_model.accuracy_history else 0.0,
            'learning_confidence': len(self.outcome_feedback) / 100  # Improves with more feedback
        }
        
        return AgentResponse(
            success=True,
            result=result,
            agent_type=self.agent_type,
            timestamp=self._get_timestamp(),
            metadata={
                'analysis_type': 'enhanced_predictive',
                'model_version': '1.0',
                'feature_count': len(confidence_analysis['factors'])
            }
        )
    
    async def load_knowledge_base(self, knowledge_items: List[Dict[str, Any]]):
        """Load and process knowledge base with advanced indexing"""
        
        logging.info(f"Loading {len(knowledge_items)} knowledge items with enhanced processing...")
        
        for item in knowledge_items:
            item_id = item['id']
            content = item['content']
            
            # Generate embeddings
            embedding = await self._get_embedding(content)
            
            # Enhanced content processing
            processed_content = await self._process_knowledge_item(item)
            
            self.knowledge_embeddings[item_id] = embedding
            self.knowledge_content[item_id] = processed_content
        
        logging.info("Enhanced knowledge base loaded successfully")
    
    async def _comprehensive_confidence_analysis(self, request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive multi-factor confidence analysis"""
        
        # Get request embedding
        request_embedding = await self._get_embedding(request)
        
        # Calculate similarities
        similarities = await self._calculate_advanced_similarities(request_embedding, request)
        
        # Multi-factor analysis
        factors = await self._calculate_enhanced_factors(request, similarities, context)
        
        # Contextual adjustments
        contextual_factors = await self._calculate_contextual_factors(request, context)
        
        # Historical pattern matching
        historical_factors = await self._calculate_historical_factors(request, context)
        
        # Combine all factors
        combined_factors = {**factors, **contextual_factors, **historical_factors}
        
        return {
            'request': request,
            'similarities': similarities[:5],  # Top 5 matches
            'factors': combined_factors,
            'context_analysis': contextual_factors,
            'historical_insights': historical_factors
        }
    
    async def _calculate_advanced_similarities(self, request_embedding: np.ndarray, request_text: str) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Calculate advanced similarities with multiple metrics"""
        
        similarities = []
        
        for item_id, kb_embedding in self.knowledge_embeddings.items():
            # Cosine similarity
            cosine_sim = self._cosine_similarity(request_embedding, kb_embedding)
            
            # Text-based similarity for validation
            text_sim = await self._calculate_text_similarity(request_text, self.knowledge_content[item_id]['content'])
            
            # Keyword overlap
            keyword_sim = await self._calculate_keyword_similarity(request_text, self.knowledge_content[item_id])
            
            # Combined similarity score
            combined_sim = (cosine_sim * 0.6 + text_sim * 0.3 + keyword_sim * 0.1)
            
            similarities.append((item_id, combined_sim, {
                'cosine': cosine_sim,
                'text': text_sim,
                'keyword': keyword_sim,
                'content': self.knowledge_content[item_id]
            }))
        
        # Sort by combined similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities
    
    async def _calculate_enhanced_factors(self, request: str, similarities: List[Tuple], context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate enhanced confidence factors"""
        
        # Basic similarity factor
        best_similarity = similarities[0][1] if similarities else 0.0
        
        # Consensus factor (multiple good matches)
        good_matches = [s for _, s, _ in similarities[:10] if s > 0.6]
        consensus_factor = min(len(good_matches) / 5.0, 1.0)
        
        # Complexity assessment
        complexity_factor = await self._assess_request_complexity_advanced(request)
        
        # Quality of matches
        quality_factor = await self._assess_match_quality(similarities[:5])
        
        # Diversity factor (different types of matches)
        diversity_factor = await self._assess_match_diversity(similarities[:5])
        
        return {
            'similarity': best_similarity,
            'consensus': consensus_factor,
            'complexity': complexity_factor,
            'quality': quality_factor,
            'diversity': diversity_factor
        }
    
    async def _calculate_contextual_factors(self, request: str, context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate context-specific confidence factors"""
        
        # User experience factor
        user_level = context.get('user_level', 'intermediate')
        user_factor = {'beginner': 0.7, 'intermediate': 1.0, 'advanced': 1.2}.get(user_level, 1.0)
        
        # Priority impact
        priority = context.get('priority', 'medium')
        priority_factor = {'low': 1.1, 'medium': 1.0, 'high': 0.9, 'critical': 0.8}.get(priority, 1.0)
        
        # System context
        system_factor = await self._assess_system_context(context.get('system', ''))
        
        # Time context (if urgent, lower confidence for safety)
        time_factor = 0.9 if context.get('urgent', False) else 1.0
        
        return {
            'user_experience': user_factor,
            'priority_impact': priority_factor,
            'system_context': system_factor,
            'time_pressure': time_factor
        }
    
    async def _calculate_historical_factors(self, request: str, context: Dict[str, Any]) -> Dict[str, float]:
        """Calculate factors based on historical performance"""
        
        if not self.confidence_history:
            return {'historical_accuracy': 0.5, 'pattern_strength': 0.0}
        
        # Find similar historical requests
        similar_historical = []
        request_words = set(request.lower().split())
        
        for hist_entry in self.confidence_history[-100:]:  # Last 100 entries
            hist_words = set(hist_entry['request'].lower().split())
            overlap = len(request_words & hist_words)
            if overlap >= 2:
                similar_historical.append(hist_entry)
        
        if not similar_historical:
            return {'historical_accuracy': 0.5, 'pattern_strength': 0.0}
        
        # Calculate historical accuracy for similar requests
        accurate_predictions = sum(1 for entry in similar_historical 
                                 if abs(entry['predicted_confidence'] - entry.get('actual_outcome', 0.5)) < 0.2)
        
        historical_accuracy = accurate_predictions / len(similar_historical)
        pattern_strength = min(1.0, len(similar_historical) / 10)
        
        return {
            'historical_accuracy': historical_accuracy,
            'pattern_strength': pattern_strength
        }
    
    async def _apply_predictive_model(self, analysis: Dict[str, Any]) -> float:
        """Apply machine learning model to predict confidence"""
        
        factors = analysis['factors']
        
        # Calculate weighted score using learned weights
        weighted_score = 0.0
        total_weight = 0.0
        
        for factor_name, weight in self.prediction_model.feature_weights.items():
            if factor_name in factors:
                weighted_score += factors[factor_name] * weight
                total_weight += weight
        
        # Normalize and add bias
        if total_weight > 0:
            normalized_score = weighted_score / total_weight
        else:
            normalized_score = 0.5
        
        final_score = normalized_score + self.prediction_model.bias
        
        # Apply bounds
        return max(0.0, min(1.0, final_score))
    
    async def _generate_confidence_reasoning(self, analysis: Dict[str, Any], predicted_confidence: float) -> str:
        """Generate human-readable reasoning for confidence score"""
        
        factors = analysis['factors']
        similarities = analysis['similarities']
        
        # Identify primary confidence drivers
        primary_factors = sorted(factors.items(), key=lambda x: abs(x[1] - 0.5), reverse=True)[:3]
        
        reasoning_parts = []
        
        # Similarity assessment
        if similarities:
            best_match = similarities[0]
            sim_score = best_match[1]
            if sim_score > 0.8:
                reasoning_parts.append(f"Strong match found (similarity: {sim_score:.2f})")
            elif sim_score > 0.6:
                reasoning_parts.append(f"Good match found (similarity: {sim_score:.2f})")
            else:
                reasoning_parts.append(f"Limited similarity to known solutions (similarity: {sim_score:.2f})")
        
        # Factor explanations
        for factor_name, factor_value in primary_factors:
            if factor_name == 'consensus' and factor_value > 0.7:
                reasoning_parts.append("Multiple supporting sources found")
            elif factor_name == 'complexity' and factor_value < 0.5:
                reasoning_parts.append("High complexity may require expert attention")
            elif factor_name == 'quality' and factor_value > 0.8:
                reasoning_parts.append("High-quality knowledge matches available")
        
        # Historical performance
        hist_factors = analysis.get('historical_insights', {})
        if hist_factors.get('historical_accuracy', 0) > 0.7:
            reasoning_parts.append("Strong historical accuracy for similar requests")
        
        # Combine reasoning
        if reasoning_parts:
            reasoning = ". ".join(reasoning_parts) + "."
        else:
            reasoning = f"Confidence based on analysis of {len(factors)} factors."
        
        return reasoning
    
    async def _get_embedding(self, text: str) -> np.ndarray:
        """Generate enhanced embedding with error handling"""
        
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text.strip()[:8000]  # Limit input length
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            logging.error(f"Embedding generation failed: {e}")
            # Return zero vector as fallback
            return np.zeros(1536)  # Standard embedding size
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity with error handling"""
        
        try:
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return np.dot(a, b) / (norm_a * norm_b)
        except Exception:
            return 0.0
    
    async def _process_knowledge_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced processing of knowledge base items"""
        
        processed = item.copy()
        
        # Extract keywords intelligently
        content = item.get('content', '')
        title = item.get('title', '')
        
        # Add computed metadata
        processed['word_count'] = len(content.split())
        processed['has_steps'] = 'step' in content.lower() or any(str(i) in content for i in range(1, 10))
        processed['complexity_indicators'] = sum(1 for word in ['advanced', 'complex', 'difficult', 'expert'] 
                                               if word in content.lower())
        processed['solution_type'] = await self._classify_solution_type(content)
        
        return processed
    
    async def _classify_solution_type(self, content: str) -> str:
        """Classify the type of solution in knowledge base item"""
        
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['step', 'procedure', 'guide']):
            return 'procedural'
        elif any(word in content_lower for word in ['troubleshoot', 'problem', 'issue', 'error']):
            return 'troubleshooting'
        elif any(word in content_lower for word in ['configure', 'setup', 'install']):
            return 'configuration'
        elif any(word in content_lower for word in ['explain', 'what is', 'definition']):
            return 'informational'
        else:
            return 'general'
    
    async def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using word overlap"""
        
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    async def _calculate_keyword_similarity(self, request: str, kb_item: Dict[str, Any]) -> float:
        """Calculate similarity based on keywords"""
        
        request_words = set(request.lower().split())
        kb_keywords = set(kb_item.get('keywords', []))
        
        if not kb_keywords:
            return 0.0
        
        matches = len(request_words & kb_keywords)
        return matches / len(kb_keywords) if kb_keywords else 0.0
    
    async def _assess_request_complexity_advanced(self, request: str) -> float:
        """Advanced complexity assessment"""
        
        complexity_indicators = {
            'length': len(request.split()) / 20,  # Longer = more complex
            'technical_terms': sum(1 for word in ['api', 'integration', 'configuration', 'database', 'server'] 
                                 if word in request.lower()) / 5,
            'uncertainty_words': sum(1 for word in ['somehow', 'maybe', 'unclear', 'confusing'] 
                                   if word in request.lower()) / 4,
            'multiple_issues': len([s for s in request.split('.') if s.strip()]) / 3
        }
        
        avg_complexity = sum(complexity_indicators.values()) / len(complexity_indicators)
        return 1.0 - min(1.0, avg_complexity)  # Invert: high complexity = low confidence
    
    async def _assess_match_quality(self, top_matches: List[Tuple]) -> float:
        """Assess quality of knowledge base matches"""
        
        if not top_matches:
            return 0.0
        
        quality_scores = []
        for _, similarity, metadata in top_matches:
            content_info = metadata.get('content', {})
            
            quality = similarity  # Base on similarity
            
            # Boost for procedural content
            if content_info.get('solution_type') == 'procedural':
                quality += 0.1
            
            # Boost for substantial content
            if content_info.get('word_count', 0) > 100:
                quality += 0.05
            
            # Reduce for very complex content
            if content_info.get('complexity_indicators', 0) > 2:
                quality -= 0.1
            
            quality_scores.append(max(0.0, min(1.0, quality)))
        
        return sum(quality_scores) / len(quality_scores)
    
    async def _assess_match_diversity(self, top_matches: List[Tuple]) -> float:
        """Assess diversity of match types"""
        
        if not top_matches:
            return 0.0
        
        solution_types = set()
        categories = set()
        
        for _, _, metadata in top_matches:
            content_info = metadata.get('content', {})
            solution_types.add(content_info.get('solution_type', 'general'))
            categories.add(content_info.get('category', 'general'))
        
        # More diverse matches = higher confidence
        type_diversity = len(solution_types) / min(5, len(top_matches))
        category_diversity = len(categories) / min(5, len(top_matches))
        
        return (type_diversity + category_diversity) / 2
    
    async def _assess_system_context(self, system_info: str) -> float:
        """Assess confidence based on system context"""
        
        if not system_info or system_info == 'unknown':
            return 0.8  # Neutral
        
        # Known systems get slight boost
        known_systems = ['windows', 'mac', 'linux', 'android', 'ios']
        if any(sys in system_info.lower() for sys in known_systems):
            return 1.0
        
        return 0.9  # Slight reduction for unknown systems
    
    async def _store_confidence_decision(self, request: str, analysis: Dict[str, Any], confidence: float):
        """Store confidence decision for learning"""
        
        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'request': request,
            'request_hash': hash(request),
            'predicted_confidence': confidence,
            'analysis_factors': analysis['factors'],
            'top_similarity': analysis['similarities'][0][1] if analysis['similarities'] else 0.0
        }
        
        self.confidence_history.append(decision_record)
        
        # Keep recent history
        if len(self.confidence_history) > 2000:
            self.confidence_history = self.confidence_history[-2000:]
    
    def update_prediction_accuracy(self, request_hash: int, actual_outcome: float):
        """Update model based on actual outcomes"""
        
        # Find corresponding prediction
        for entry in reversed(self.confidence_history):
            if entry['request_hash'] == request_hash:
                entry['actual_outcome'] = actual_outcome
                
                # Calculate prediction error
                error = abs(entry['predicted_confidence'] - actual_outcome)
                accuracy = 1.0 - error
                
                self.prediction_model.accuracy_history.append(accuracy)
                
                # Update feature weights based on error (simple gradient descent)
                learning_rate = 0.01
                for factor_name, factor_value in entry['analysis_factors'].items():
                    if factor_name in self.prediction_model.feature_weights:
                        # Adjust weight based on error direction
                        if entry['predicted_confidence'] > actual_outcome:
                            # Over-predicted, reduce weight
                            self.prediction_model.feature_weights[factor_name] *= (1 - learning_rate * factor_value)
                        else:
                            # Under-predicted, increase weight
                            self.prediction_model.feature_weights[factor_name] *= (1 + learning_rate * factor_value)
                
                # Keep recent accuracy history
                if len(self.prediction_model.accuracy_history) > 1000:
                    self.prediction_model.accuracy_history = self.prediction_model.accuracy_history[-1000:]
                
                self.prediction_model.last_updated = datetime.now()
                break