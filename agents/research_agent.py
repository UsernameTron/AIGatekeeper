"""
Advanced Research Agent with Multi-Source Intelligence and Learning
"""

import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import sys
import os

# Add shared agents to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared_agents'))

from shared_agents.core.agent_factory import AgentBase, AgentResponse, AgentCapability
from core.ai_tracking import track_openai_completion

class AdvancedResearchAgent(AgentBase):
    """
    Intelligent research agent that synthesizes information from multiple sources
    Uses advanced reasoning and learns from solution effectiveness
    """
    
    REQUIRED_CONFIG_FIELDS = ['openai_client']
    DEFAULT_CAPABILITIES = [
        AgentCapability.RESEARCH,
        AgentCapability.TEXT_GENERATION,
        AgentCapability.RAG_PROCESSING,
        AgentCapability.VECTOR_SEARCH
    ]
    
    def __init__(self, name: str, agent_type: str, config: Dict[str, Any]):
        super().__init__(name, agent_type, config, self.DEFAULT_CAPABILITIES)
        
        self.openai_client = config['openai_client']
        self.model = config.get('model', 'gpt-4o')
        self.search_system = config.get('search_system')
        
        # Learning components
        self.solution_effectiveness = {}
        self.research_patterns = []
        self.synthesis_history = []
        
        # Research strategies
        self.research_strategies = {
            'direct_match': {'weight': 0.4, 'description': 'Direct knowledge base matching'},
            'semantic_synthesis': {'weight': 0.3, 'description': 'Semantic synthesis from multiple sources'},
            'pattern_recognition': {'weight': 0.2, 'description': 'Pattern-based solution generation'},
            'adaptive_reasoning': {'weight': 0.1, 'description': 'Adaptive reasoning based on context'}
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Execute advanced research and solution generation"""
        
        query = input_data.get('query', '')
        context = input_data.get('context', {})
        search_type = input_data.get('search_type', 'comprehensive')
        knowledge_base_results = input_data.get('knowledge_base_results', [])
        
        if not query:
            raise ValueError("No query provided for research")
        
        # Multi-strategy research approach
        research_results = await self._conduct_comprehensive_research(query, context, knowledge_base_results)
        
        # Synthesize findings
        synthesis = await self._synthesize_research_findings(research_results, context)
        
        # Generate solution
        solution = await self._generate_intelligent_solution(query, synthesis, context)
        
        # Validate and enhance solution
        validated_solution = await self._validate_and_enhance_solution(solution, context)
        
        # Store for learning
        await self._store_research_session(query, research_results, validated_solution)
        
        return AgentResponse(
            success=True,
            result=validated_solution,
            agent_type=self.agent_type,
            timestamp=self._get_timestamp(),
            metadata={
                'research_strategies_used': len(research_results),
                'synthesis_confidence': synthesis.get('confidence', 0.5),
                'solution_type': validated_solution.get('type', 'comprehensive')
            }
        )
    
    async def _conduct_comprehensive_research(self, query: str, context: Dict[str, Any], 
                                           kb_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Conduct multi-strategy research"""
        
        research_results = {}
        
        # Strategy 1: Knowledge base search
        if self.search_system:
            research_results['knowledge_base'] = await self._search_knowledge_base(query, context)
        else:
            research_results['knowledge_base'] = kb_results
        
        # Strategy 2: Pattern matching from history
        research_results['pattern_match'] = await self._pattern_based_research(query, context)
        
        # Strategy 3: Semantic decomposition
        research_results['semantic_analysis'] = await self._semantic_decomposition(query)
        
        # Strategy 4: Contextual reasoning
        research_results['contextual_insights'] = await self._contextual_reasoning(query, context)
        
        # Strategy 5: Adaptive learning application
        research_results['adaptive_insights'] = await self._apply_adaptive_learning(query, context)
        
        return research_results
    
    async def _search_knowledge_base(self, query: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhanced knowledge base search with intelligent query expansion"""
        
        if not self.search_system:
            return []
        
        try:
            # Primary search
            primary_results = await self.search_system.assisted_search(
                vector_store_ids=['technical_solutions', 'troubleshooting_guides'],
                query=query,
                num_results=10
            )
            
            # Query expansion for broader search
            expanded_query = await self._generate_expanded_query(query, context)
            secondary_results = await self.search_system.assisted_search(
                vector_store_ids=['configuration_guides', 'best_practices'],
                query=expanded_query,
                num_results=5
            )
            
            # Combine and rank results
            all_results = (primary_results or []) + (secondary_results or [])
            return await self._rank_search_results(all_results, query)
            
        except Exception as e:
            logging.error(f"Knowledge base search failed: {e}")
            return []
    
    async def _generate_expanded_query(self, query: str, context: Dict[str, Any]) -> str:
        """Generate expanded search query using AI"""
        
        prompt = f"""Expand this search query to find more relevant solutions:

Original Query: "{query}"
Context: {json.dumps(context, indent=2) if context else "None"}

Generate 3-5 related search terms that would help find solutions for this issue.
Focus on:
- Technical keywords and synonyms
- Related problem areas
- Alternative descriptions
- Root cause possibilities

Return as a single expanded search string."""

        try:
            response = await self.openai_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )

            # Track AI usage
            track_openai_completion(response, agent_type='research')

            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Query expansion failed: {e}")
            return query
    
    async def _pattern_based_research(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Find patterns from previous successful solutions"""
        
        if not self.solution_effectiveness:
            return {'patterns': [], 'confidence': 0.0}
        
        # Find similar queries from history
        similar_patterns = []
        query_words = set(query.lower().split())
        
        for solution_id, effectiveness_data in self.solution_effectiveness.items():
            if effectiveness_data.get('success_rate', 0) > 0.7:  # Successful solutions only
                hist_query = effectiveness_data.get('original_query', '')
                hist_words = set(hist_query.lower().split())
                
                # Calculate similarity
                overlap = len(query_words & hist_words)
                if overlap >= 2:  # At least 2 word overlap
                    similar_patterns.append({
                        'solution_id': solution_id,
                        'overlap_score': overlap / len(query_words | hist_words),
                        'success_rate': effectiveness_data['success_rate'],
                        'solution_type': effectiveness_data.get('solution_type', 'general')
                    })
        
        # Sort by relevance
        similar_patterns.sort(key=lambda x: x['overlap_score'] * x['success_rate'], reverse=True)
        
        return {
            'patterns': similar_patterns[:5],  # Top 5 patterns
            'confidence': min(1.0, len(similar_patterns) / 3)  # More patterns = higher confidence
        }
    
    async def _semantic_decomposition(self, query: str) -> Dict[str, Any]:
        """Decompose query into semantic components for better understanding"""
        
        prompt = f"""Decompose this support query into semantic components:

Query: "{query}"

Analyze and extract:
1. Primary action/intent (what user wants to accomplish)
2. Object/system (what they're working with)
3. Problem type (error, configuration, how-to, etc.)
4. Context clues (urgency, complexity indicators)
5. Technical domain (networking, software, hardware, etc.)
6. Skill level indicators
7. Emotional state indicators

Provide JSON response with these components and confidence levels."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0]
            
            return json.loads(content)
            
        except Exception as e:
            logging.error(f"Semantic decomposition failed: {e}")
            return {
                'primary_action': 'seek_help',
                'object_system': 'unknown',
                'problem_type': 'general',
                'confidence': 0.3
            }
    
    async def _contextual_reasoning(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply contextual reasoning to understand deeper implications"""
        
        user_level = context.get('user_level', 'intermediate')
        system_info = context.get('system', 'unknown')
        priority = context.get('priority', 'medium')
        
        prompt = f"""Analyze this support request with contextual reasoning:

Query: "{query}"
User Level: {user_level}
System: {system_info}
Priority: {priority}

Provide contextual insights:
1. What might the user really be trying to accomplish? (deeper intent)
2. What are likely pain points for a {user_level} user?
3. What system-specific considerations apply?
4. What are potential follow-up questions?
5. What success criteria would the user have?
6. What could go wrong with standard solutions?

Return detailed JSON analysis."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=600
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0]
            
            return json.loads(content)
            
        except Exception as e:
            logging.error(f"Contextual reasoning failed: {e}")
            return {
                'deeper_intent': 'accomplish_task',
                'pain_points': ['complexity', 'time_pressure'],
                'success_criteria': ['problem_resolved'],
                'confidence': 0.4
            }
    
    async def _apply_adaptive_learning(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply learning from past solution effectiveness"""
        
        if not self.solution_effectiveness:
            return {'learning_insights': [], 'confidence': 0.0}
        
        # Analyze successful solution characteristics
        successful_patterns = []
        for solution_id, data in self.solution_effectiveness.items():
            if data.get('success_rate', 0) > 0.8:
                successful_patterns.append(data.get('characteristics', {}))
        
        if not successful_patterns:
            return {'learning_insights': [], 'confidence': 0.0}
        
        # Extract common characteristics of successful solutions
        common_traits = {}
        for pattern in successful_patterns:
            for trait, value in pattern.items():
                if trait not in common_traits:
                    common_traits[trait] = []
                common_traits[trait].append(value)
        
        # Identify most common successful traits
        learning_insights = []
        for trait, values in common_traits.items():
            if len(values) >= len(successful_patterns) * 0.6:  # 60% consensus
                most_common = max(set(values), key=values.count)
                learning_insights.append({
                    'trait': trait,
                    'recommended_value': most_common,
                    'confidence': values.count(most_common) / len(values)
                })
        
        return {
            'learning_insights': learning_insights,
            'confidence': min(1.0, len(learning_insights) / 3)
        }
    
    async def _synthesize_research_findings(self, research_results: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize findings from all research strategies"""
        
        # Weight and combine findings
        synthesis = {
            'knowledge_sources': len(research_results.get('knowledge_base', [])),
            'pattern_matches': len(research_results.get('pattern_match', {}).get('patterns', [])),
            'semantic_components': research_results.get('semantic_analysis', {}),
            'contextual_insights': research_results.get('contextual_insights', {}),
            'learning_applications': research_results.get('adaptive_insights', {})
        }
        
        # Calculate overall research confidence
        confidence_factors = [
            min(1.0, synthesis['knowledge_sources'] / 5),  # More sources = higher confidence
            research_results.get('pattern_match', {}).get('confidence', 0.0),
            research_results.get('semantic_analysis', {}).get('confidence', 0.0),
            research_results.get('contextual_insights', {}).get('confidence', 0.0),
            research_results.get('adaptive_insights', {}).get('confidence', 0.0)
        ]
        
        synthesis['confidence'] = sum(confidence_factors) / len(confidence_factors)
        synthesis['research_depth'] = sum(1 for cf in confidence_factors if cf > 0.5)
        
        return synthesis
    
    async def _generate_intelligent_solution(self, query: str, synthesis: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate intelligent solution based on research synthesis"""
        
        user_level = context.get('user_level', 'intermediate')
        
        # Build comprehensive prompt with all research findings
        prompt = f"""Generate a comprehensive solution based on extensive research:

Original Query: "{query}"
User Level: {user_level}
Research Confidence: {synthesis['confidence']:.2f}

Research Findings:
- Knowledge Sources Found: {synthesis['knowledge_sources']}
- Pattern Matches: {synthesis['pattern_matches']}
- Semantic Analysis: {json.dumps(synthesis['semantic_components'], indent=2)}
- Contextual Insights: {json.dumps(synthesis['contextual_insights'], indent=2)}

Generate a detailed solution that includes:
1. Clear step-by-step instructions appropriate for {user_level} user
2. Explanation of why this approach works
3. Potential issues and troubleshooting
4. Success validation steps
5. Alternative approaches if main solution fails
6. Estimated time and difficulty
7. Prerequisites and warnings

Format as JSON with:
- title: Clear solution title
- summary: Brief overview
- steps: Detailed step array with title, description, commands, expected_result
- troubleshooting: Common issues and fixes
- alternatives: Alternative approaches
- estimated_time: Time estimate
- difficulty_level: easy/medium/hard
- prerequisites: Requirements
- warnings: Important cautions
- success_criteria: How to verify success
- confidence_score: Your confidence in this solution (0.0-1.0)

Be comprehensive, accurate, and user-focused."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0]
            
            solution = json.loads(content)
            
            # Add metadata
            solution['research_synthesis'] = synthesis
            solution['generated_at'] = datetime.now().isoformat()
            solution['agent_confidence'] = synthesis['confidence']
            
            return solution
            
        except Exception as e:
            logging.error(f"Solution generation failed: {e}")
            return await self._generate_fallback_solution(query, context)
    
    async def _generate_fallback_solution(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback solution when main generation fails"""
        
        return {
            'title': f'General Guidance for: {query[:50]}...',
            'summary': 'Providing general troubleshooting guidance',
            'steps': [
                {
                    'title': 'Identify the Problem',
                    'description': 'Clearly define what exactly is not working as expected',
                    'commands': [],
                    'expected_result': 'Clear understanding of the issue'
                },
                {
                    'title': 'Gather Information',
                    'description': 'Collect relevant error messages, system information, and steps to reproduce',
                    'commands': [],
                    'expected_result': 'Comprehensive problem details'
                },
                {
                    'title': 'Try Basic Solutions',
                    'description': 'Attempt common solutions like restarting, updating, or resetting',
                    'commands': [],
                    'expected_result': 'Issue potentially resolved'
                },
                {
                    'title': 'Seek Expert Help',
                    'description': 'Contact technical support with detailed information if issue persists',
                    'commands': [],
                    'expected_result': 'Expert assistance obtained'
                }
            ],
            'troubleshooting': 'If steps do not resolve the issue, escalate to human support',
            'estimated_time': '15-30 minutes',
            'difficulty_level': 'medium',
            'confidence_score': 0.4,
            'fallback': True
        }
    
    async def _validate_and_enhance_solution(self, solution: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and enhance the generated solution"""
        
        # Validate solution structure
        required_fields = ['title', 'steps', 'estimated_time']
        for field in required_fields:
            if field not in solution:
                solution[field] = f"Missing {field}"
        
        # Enhance based on context
        user_level = context.get('user_level', 'intermediate')
        
        if user_level == 'beginner':
            # Add more explanatory details
            for step in solution.get('steps', []):
                if 'explanation' not in step:
                    step['explanation'] = 'This step helps resolve the issue by addressing the underlying cause.'
        
        elif user_level == 'advanced':
            # Add technical details and alternatives
            solution['technical_notes'] = 'For advanced users: Consider command-line alternatives and automation options.'
        
        # Add learning tracking ID
        solution['solution_id'] = f"sol_{hash(str(solution))}_{int(datetime.now().timestamp())}"
        
        return solution
    
    async def _rank_search_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Rank search results by relevance and quality"""
        
        if not results:
            return []
        
        query_words = set(query.lower().split())
        
        for result in results:
            # Calculate relevance score
            content = result.get('content', '') + ' ' + result.get('title', '')
            content_words = set(content.lower().split())
            
            overlap = len(query_words & content_words)
            relevance = overlap / len(query_words) if query_words else 0
            
            # Add quality factors
            quality_score = 1.0
            if result.get('metadata', {}).get('difficulty') == 'easy':
                quality_score += 0.1
            if len(content) > 200:  # Substantial content
                quality_score += 0.1
            
            result['relevance_score'] = relevance * quality_score
        
        # Sort by relevance
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return results
    
    async def _store_research_session(self, query: str, research_results: Dict[str, Any], solution: Dict[str, Any]):
        """Store research session for learning"""
        
        session_record = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'query_hash': hash(query),
            'research_strategies_used': list(research_results.keys()),
            'solution_id': solution.get('solution_id'),
            'confidence': solution.get('confidence_score', 0.5),
            'solution_type': solution.get('difficulty_level', 'medium')
        }
        
        self.research_patterns.append(session_record)
        
        # Keep recent patterns
        if len(self.research_patterns) > 1000:
            self.research_patterns = self.research_patterns[-1000:]
    
    def update_solution_effectiveness(self, solution_id: str, effectiveness_data: Dict[str, Any]):
        """Update learning from solution effectiveness feedback"""
        
        self.solution_effectiveness[solution_id] = {
            'timestamp': datetime.now().isoformat(),
            'success_rate': effectiveness_data.get('success_rate', 0.5),
            'user_satisfaction': effectiveness_data.get('user_satisfaction', 0.5),
            'resolution_time': effectiveness_data.get('resolution_time', 0),
            'original_query': effectiveness_data.get('original_query', ''),
            'solution_type': effectiveness_data.get('solution_type', 'general'),
            'characteristics': effectiveness_data.get('characteristics', {})
        }