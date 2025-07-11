"""
Advanced Triage Agent with Multi-Model Reasoning and Learning
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

class AdvancedTriageAgent(AgentBase):
    """
    Intelligent triage agent that analyzes requests and routes them optimally
    Uses multiple reasoning strategies and learns from outcomes
    """
    
    REQUIRED_CONFIG_FIELDS = ['openai_client']
    DEFAULT_CAPABILITIES = [
        AgentCapability.STRATEGIC_PLANNING,
        AgentCapability.WORKFLOW_ORCHESTRATION,
        AgentCapability.TEXT_GENERATION
    ]
    
    def __init__(self, name: str, agent_type: str, config: Dict[str, Any]):
        super().__init__(name, agent_type, config, self.DEFAULT_CAPABILITIES)
        
        self.openai_client = config['openai_client']
        self.model = config.get('model', 'gpt-4o')
        self.fast_model = config.get('fast_model', 'gpt-4o-mini')
        
        # Learning components
        self.routing_history = []
        self.outcome_feedback = {}
        
        # Triage categories and routing rules
        self.triage_categories = {
            'password_reset': {'confidence_boost': 0.2, 'complexity': 'low', 'risk': 'low'},
            'technical_issue': {'confidence_boost': 0.0, 'complexity': 'medium', 'risk': 'medium'},
            'configuration': {'confidence_boost': 0.1, 'complexity': 'medium', 'risk': 'low'},
            'integration_issue': {'confidence_boost': -0.2, 'complexity': 'high', 'risk': 'high'},
            'security_concern': {'confidence_boost': -0.3, 'complexity': 'high', 'risk': 'critical'},
            'general_inquiry': {'confidence_boost': 0.15, 'complexity': 'low', 'risk': 'low'}
        }
    
    async def execute(self, input_data: Dict[str, Any]) -> AgentResponse:
        """Execute advanced triage analysis"""
        
        request_text = input_data.get('query', input_data.get('support_request', ''))
        user_context = input_data.get('context', {})
        workflow_type = input_data.get('workflow_type', 'support_evaluation')
        
        if not request_text:
            raise ValueError("No request text provided for triage")
        
        # Multi-stage triage analysis
        analysis_results = await self._perform_comprehensive_analysis(request_text, user_context)
        
        # Generate routing recommendation
        routing = await self._generate_routing_recommendation(analysis_results, user_context)
        
        # Calculate confidence and risk scores
        confidence_score = await self._calculate_confidence_score(analysis_results, routing)
        risk_score = await self._calculate_risk_score(analysis_results, routing)
        
        # Store for learning
        await self._store_triage_decision(request_text, analysis_results, routing)
        
        result = {
            'category': analysis_results['primary_category'],
            'subcategory': analysis_results['subcategory'],
            'confidence_score': confidence_score,
            'risk_score': risk_score,
            'routing_recommendation': routing,
            'urgency_level': analysis_results['urgency'],
            'complexity_assessment': analysis_results['complexity'],
            'recommended_agent': routing['primary_agent'],
            'escalation_reason': routing.get('escalation_reason'),
            'analysis_details': analysis_results,
            'learning_confidence': await self._get_learning_confidence(analysis_results['primary_category'])
        }
        
        return AgentResponse(
            success=True,
            result=result,
            agent_type=self.agent_type,
            timestamp=self._get_timestamp(),
            metadata={'analysis_depth': 'comprehensive', 'reasoning_stages': 4}
        )
    
    async def _perform_comprehensive_analysis(self, request_text: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Perform deep analysis using multiple reasoning approaches"""
        
        # Stage 1: Fast categorization
        fast_analysis = await self._fast_categorization(request_text)
        
        # Stage 2: Deep semantic analysis
        semantic_analysis = await self._deep_semantic_analysis(request_text, user_context)
        
        # Stage 3: Context-aware reasoning
        contextual_analysis = await self._contextual_reasoning(request_text, user_context, fast_analysis)
        
        # Stage 4: Synthesis and validation
        final_analysis = await self._synthesize_analysis(fast_analysis, semantic_analysis, contextual_analysis)
        
        return final_analysis
    
    async def _fast_categorization(self, request_text: str) -> Dict[str, Any]:
        """Quick categorization using fast model"""
        
        prompt = f"""Analyze this support request and provide quick categorization:

Request: "{request_text}"

Provide JSON response with:
- primary_category: main category (password_reset, technical_issue, configuration, integration_issue, security_concern, general_inquiry)
- confidence: confidence in categorization (0.0-1.0)
- urgency: urgency level (low, medium, high, critical)
- keywords: key terms identified

Be concise and accurate."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.fast_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0]
            
            return json.loads(content)
            
        except Exception as e:
            logging.error(f"Fast categorization failed: {e}")
            return {
                'primary_category': 'general_inquiry',
                'confidence': 0.3,
                'urgency': 'medium',
                'keywords': request_text.split()[:5]
            }
    
    async def _deep_semantic_analysis(self, request_text: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Deep semantic analysis using advanced model"""
        
        context_str = json.dumps(user_context, indent=2) if user_context else "No context provided"
        
        prompt = f"""Perform deep semantic analysis of this support request:

Request: "{request_text}"
User Context: {context_str}

Analyze:
1. Intent and goal of the user
2. Technical complexity level
3. Emotional state indicators
4. Domain expertise required
5. Potential risks and impacts
6. Similar request patterns
7. Success probability for automation

Provide detailed JSON response with:
- intent: primary user intent
- complexity: technical complexity (1-10)
- emotional_state: detected emotional indicators
- expertise_required: domain expertise needed
- risk_factors: potential risks
- automation_feasibility: likelihood of successful automation (0.0-1.0)
- reasoning: detailed reasoning chain

Be thorough and analytical."""

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            if content.startswith('```json'):
                content = content.split('```json')[1].split('```')[0]
            
            return json.loads(content)
            
        except Exception as e:
            logging.error(f"Deep semantic analysis failed: {e}")
            return {
                'intent': 'seek_assistance',
                'complexity': 5,
                'emotional_state': 'neutral',
                'expertise_required': 'general',
                'risk_factors': ['moderate_complexity'],
                'automation_feasibility': 0.5,
                'reasoning': 'Analysis failed, using defaults'
            }
    
    async def _contextual_reasoning(self, request_text: str, user_context: Dict[str, Any], fast_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Context-aware reasoning and validation"""
        
        user_level = user_context.get('user_level', 'intermediate')
        system_context = user_context.get('system', 'unknown')
        priority = user_context.get('priority', 'medium')
        
        # Apply contextual adjustments
        complexity_modifier = {
            'beginner': +2,
            'intermediate': 0,
            'advanced': -1
        }.get(user_level, 0)
        
        risk_modifier = {
            'critical': +0.3,
            'high': +0.1,
            'medium': 0.0,
            'low': -0.1
        }.get(priority, 0.0)
        
        return {
            'complexity_adjusted': min(10, max(1, fast_analysis.get('complexity', 5) + complexity_modifier)),
            'risk_adjusted': max(0.0, min(1.0, risk_modifier)),
            'user_capability_match': self._assess_user_capability_match(fast_analysis['primary_category'], user_level),
            'contextual_confidence': self._calculate_contextual_confidence(fast_analysis, user_context)
        }
    
    async def _synthesize_analysis(self, fast: Dict[str, Any], semantic: Dict[str, Any], contextual: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize all analysis stages into final assessment"""
        
        return {
            'primary_category': fast['primary_category'],
            'subcategory': semantic.get('intent', 'general'),
            'confidence': (fast['confidence'] + contextual['contextual_confidence']) / 2,
            'urgency': fast['urgency'],
            'complexity': contextual['complexity_adjusted'],
            'risk_level': contextual['risk_adjusted'],
            'automation_feasibility': semantic.get('automation_feasibility', 0.5),
            'emotional_indicators': semantic.get('emotional_state', 'neutral'),
            'expertise_required': semantic.get('expertise_required', 'general'),
            'user_capability_match': contextual['user_capability_match'],
            'synthesis_confidence': min(fast['confidence'], semantic.get('automation_feasibility', 0.5))
        }
    
    async def _generate_routing_recommendation(self, analysis: Dict[str, Any], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate intelligent routing recommendation"""
        
        category = analysis['primary_category']
        complexity = analysis['complexity']
        automation_feasibility = analysis['automation_feasibility']
        
        # Determine primary agent
        if automation_feasibility > 0.7 and complexity <= 6:
            primary_agent = 'research'
            confidence_adjustment = 0.1
        elif category in ['password_reset', 'general_inquiry'] and complexity <= 4:
            primary_agent = 'research'
            confidence_adjustment = 0.2
        elif complexity > 8 or automation_feasibility < 0.3:
            primary_agent = 'human_expert'
            confidence_adjustment = -0.3
        else:
            primary_agent = 'research'
            confidence_adjustment = 0.0
        
        # Secondary routing options
        secondary_options = []
        if primary_agent == 'research' and complexity > 6:
            secondary_options.append('human_expert')
        
        routing = {
            'primary_agent': primary_agent,
            'secondary_options': secondary_options,
            'confidence_adjustment': confidence_adjustment,
            'routing_reasoning': f"Category: {category}, Complexity: {complexity}, Feasibility: {automation_feasibility:.2f}"
        }
        
        # Add escalation conditions
        if complexity > 8:
            routing['escalation_reason'] = 'High complexity requires human expertise'
        elif automation_feasibility < 0.3:
            routing['escalation_reason'] = 'Low automation feasibility'
        elif analysis.get('risk_level', 0) > 0.7:
            routing['escalation_reason'] = 'High risk requires human oversight'
        
        return routing
    
    async def _calculate_confidence_score(self, analysis: Dict[str, Any], routing: Dict[str, Any]) -> float:
        """Calculate overall confidence score"""
        
        base_confidence = analysis['synthesis_confidence']
        category_boost = self.triage_categories.get(analysis['primary_category'], {}).get('confidence_boost', 0.0)
        routing_adjustment = routing['confidence_adjustment']
        learning_factor = await self._get_learning_confidence(analysis['primary_category'])
        
        final_confidence = base_confidence + category_boost + routing_adjustment + learning_factor
        return max(0.0, min(1.0, final_confidence))
    
    async def _calculate_risk_score(self, analysis: Dict[str, Any], routing: Dict[str, Any]) -> float:
        """Calculate risk score"""
        
        base_risk = analysis.get('risk_level', 0.5)
        category_risk = self.triage_categories.get(analysis['primary_category'], {}).get('risk', 'medium')
        
        risk_values = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'critical': 0.95}
        category_risk_score = risk_values.get(category_risk, 0.5)
        
        complexity_risk = min(0.3, analysis['complexity'] / 10 * 0.3)
        
        return min(1.0, max(0.0, (base_risk + category_risk_score + complexity_risk) / 3))
    
    def _assess_user_capability_match(self, category: str, user_level: str) -> float:
        """Assess how well user capability matches request complexity"""
        
        category_complexity = {
            'password_reset': 1,
            'general_inquiry': 2,
            'configuration': 4,
            'technical_issue': 6,
            'integration_issue': 8,
            'security_concern': 9
        }
        
        user_capability = {
            'beginner': 3,
            'intermediate': 6,
            'advanced': 9
        }
        
        req_complexity = category_complexity.get(category, 5)
        user_cap = user_capability.get(user_level, 6)
        
        if user_cap >= req_complexity:
            return 1.0
        else:
            return user_cap / req_complexity
    
    def _calculate_contextual_confidence(self, fast_analysis: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """Calculate confidence based on context"""
        
        base = fast_analysis['confidence']
        
        # Adjust for user level
        user_level = user_context.get('user_level', 'intermediate')
        if user_level == 'advanced':
            base += 0.1
        elif user_level == 'beginner':
            base -= 0.1
        
        # Adjust for priority
        priority = user_context.get('priority', 'medium')
        if priority in ['critical', 'high']:
            base -= 0.05  # More conservative for high priority
        
        return max(0.0, min(1.0, base))
    
    async def _get_learning_confidence(self, category: str) -> float:
        """Get confidence adjustment based on learning history"""
        
        if not self.outcome_feedback.get(category):
            return 0.0
        
        recent_outcomes = self.outcome_feedback[category][-10:]  # Last 10 outcomes
        if not recent_outcomes:
            return 0.0
        
        success_rate = sum(1 for outcome in recent_outcomes if outcome.get('success', False)) / len(recent_outcomes)
        
        # Convert success rate to confidence adjustment
        if success_rate > 0.8:
            return 0.1
        elif success_rate < 0.5:
            return -0.1
        else:
            return 0.0
    
    async def _store_triage_decision(self, request_text: str, analysis: Dict[str, Any], routing: Dict[str, Any]):
        """Store triage decision for learning"""
        
        decision_record = {
            'timestamp': datetime.now().isoformat(),
            'request_hash': hash(request_text),
            'category': analysis['primary_category'],
            'routing': routing['primary_agent'],
            'confidence': analysis['synthesis_confidence'],
            'complexity': analysis['complexity'],
            'automation_feasibility': analysis['automation_feasibility']
        }
        
        self.routing_history.append(decision_record)
        
        # Keep only recent history
        if len(self.routing_history) > 500:
            self.routing_history = self.routing_history[-500:]
    
    def update_outcome_feedback(self, category: str, outcome: Dict[str, Any]):
        """Update learning from outcomes"""
        
        if category not in self.outcome_feedback:
            self.outcome_feedback[category] = []
        
        self.outcome_feedback[category].append({
            'timestamp': datetime.now().isoformat(),
            'success': outcome.get('success', False),
            'user_satisfaction': outcome.get('satisfaction', 0.5),
            'resolution_time': outcome.get('resolution_time', 0)
        })
        
        # Keep recent feedback
        if len(self.outcome_feedback[category]) > 50:
            self.outcome_feedback[category] = self.outcome_feedback[category][-50:]