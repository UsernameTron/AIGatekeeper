"""
Support Request Processing Engine for AI Gatekeeper System
Leverages existing agent framework for intelligent support automation
"""

import sys
import os
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

# Add shared agents to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared_agents'))

from shared_agents.core.agent_factory import AgentBase, AgentResponse, AgentCapability
from shared_agents.config.shared_config import SharedConfig
from core.confidence_agent import ConfidenceAgent, ConfidenceResult
from core.advanced_agent_manager import AdvancedAgentManager


class SupportRequestPriority(Enum):
    """Priority levels for support requests."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SupportRequestStatus(Enum):
    """Status of support request processing."""
    RECEIVED = "received"
    EVALUATING = "evaluating"
    AUTOMATED_RESOLUTION = "automated_resolution"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class SupportRequest:
    """Support request data structure."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message: str = ""
    user_context: Dict[str, Any] = field(default_factory=dict)
    priority: SupportRequestPriority = SupportRequestPriority.MEDIUM
    status: SupportRequestStatus = SupportRequestStatus.RECEIVED
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    confidence_score: Optional[float] = None
    risk_score: Optional[float] = None
    resolution_path: Optional[str] = None
    assigned_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SupportRequestProcessor:
    """
    Main processor for support requests using existing agent framework.
    Integrates with TriageAgent, ResearchAgent, and other specialized agents.
    """
    
    def __init__(self, config: SharedConfig):
        """Initialize the support request processor."""
        self.config = config
        self.active_requests: Dict[str, SupportRequest] = {}
        self.processing_queue: List[str] = []
        
        # Configuration for AI Gatekeeper
        self.confidence_threshold = getattr(config, 'support_confidence_threshold', 0.8)
        self.risk_threshold = getattr(config, 'support_risk_threshold', 0.3)
        
        # Initialize agent connections (will be injected from existing system)
        self.agent_manager = None
        self.search_system = None
        self.confidence_agent = None
        self.advanced_agent_manager = None
        
    def set_agent_manager(self, agent_manager):
        """Set the agent manager from existing unified system."""
        self.agent_manager = agent_manager
        
    def set_search_system(self, search_system):
        """Set the search system for knowledge base operations."""
        self.search_system = search_system
    
    def set_confidence_agent(self, confidence_agent: ConfidenceAgent):
        """Set the confidence agent for advanced scoring."""
        self.confidence_agent = confidence_agent
    
    def set_advanced_agent_manager(self, advanced_agent_manager: AdvancedAgentManager):
        """Set the advanced agent manager with swarm intelligence."""
        self.advanced_agent_manager = advanced_agent_manager
    
    async def process_support_request(self, message: str, user_context: Dict[str, Any]) -> SupportRequest:
        """
        Process an incoming support request using existing agent framework.
        
        Args:
            message: The support request message
            user_context: Context about the user and environment
            
        Returns:
            SupportRequest with processing results
        """
        # Create new support request
        request = SupportRequest(
            message=message,
            user_context=user_context,
            priority=self._determine_priority(message, user_context),
            metadata={
                'source': 'ai_gatekeeper',
                'processing_started': datetime.now().isoformat()
            }
        )
        
        # Store request
        self.active_requests[request.id] = request
        self.processing_queue.append(request.id)
        
        try:
            # Step 1: Use TriageAgent for initial evaluation
            triage_result = await self._perform_triage_evaluation(request)
            
            # Step 2: Calculate confidence and risk scores
            request.confidence_score = triage_result.get('confidence_score', 0.0)
            request.risk_score = triage_result.get('risk_score', 0.5)
            
            # Step 3: Determine resolution path
            resolution_path = self._determine_resolution_path(request)
            request.resolution_path = resolution_path
            
            # Step 4: Execute resolution path
            if resolution_path == "automated_resolution":
                await self._handle_automated_resolution(request)
            else:
                await self._handle_escalation(request)
                
            request.status = SupportRequestStatus.RESOLVED
            request.updated_at = datetime.now()
            
        except Exception as e:
            request.status = SupportRequestStatus.ESCALATED
            request.metadata['error'] = str(e)
            request.updated_at = datetime.now()
            
        return request
    
    async def _perform_triage_evaluation(self, request: SupportRequest) -> Dict[str, Any]:
        """Use confidence agent for evaluation."""
        
        if not self.confidence_agent:
            # Fallback to original logic
            return await self._perform_original_triage_evaluation(request)
        
        # Use confidence agent
        confidence_result = await self.confidence_agent.score_confidence(
            request.message, 
            request.user_context
        )
        
        return {
            'confidence_score': confidence_result.confidence_score,
            'risk_score': self._calculate_risk_score_from_confidence(confidence_result),
            'confidence_analysis': confidence_result,
            'primary_matches': confidence_result.primary_matches,
            'reasoning': confidence_result.reasoning
        }
    
    async def _perform_original_triage_evaluation(self, request: SupportRequest) -> Dict[str, Any]:
        """
        Use existing TriageAgent to evaluate support request.
        
        Args:
            request: The support request to evaluate
            
        Returns:
            Dictionary with triage results
        """
        if not self.agent_manager:
            raise ValueError("Agent manager not initialized")
        
        # Prepare input for TriageAgent
        triage_input = {
            'support_request': request.message,
            'user_context': request.user_context,
            'workflow_type': 'support_evaluation',
            'request_id': request.id,
            'priority': request.priority.value
        }
        
        # Execute TriageAgent
        triage_response = await self.agent_manager.execute_agent('triage', triage_input)
        
        if not triage_response.success:
            raise Exception(f"Triage evaluation failed: {triage_response.error}")
        
        # Extract confidence and risk scores from triage response
        result = triage_response.result
        
        # Calculate confidence based on triage analysis
        confidence_score = self._calculate_confidence_score(result, request)
        
        # Calculate risk based on user context and request type
        risk_score = self._calculate_risk_score(result, request)
        
        return {
            'confidence_score': confidence_score,
            'risk_score': risk_score,
            'triage_analysis': result,
            'recommended_agent': result.get('recommended_agent'),
            'escalation_reason': result.get('escalation_reason')
        }
    
    def _calculate_confidence_score(self, triage_result: Dict[str, Any], request: SupportRequest) -> float:
        """
        Calculate confidence score for automated resolution.
        
        Args:
            triage_result: Results from TriageAgent
            request: The support request
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = 0.5
        
        # Boost confidence for common issues
        if self._is_common_issue(request.message):
            base_confidence += 0.3
        
        # Boost confidence for experienced users
        user_level = request.user_context.get('user_level', 'beginner')
        if user_level in ['intermediate', 'advanced']:
            base_confidence += 0.2
        
        # Reduce confidence for complex technical issues
        if self._is_complex_issue(request.message):
            base_confidence -= 0.4
        
        # Reduce confidence for critical system issues
        if request.priority == SupportRequestPriority.CRITICAL:
            base_confidence -= 0.3
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_risk_score(self, triage_result: Dict[str, Any], request: SupportRequest) -> float:
        """
        Calculate risk score for automated resolution.
        
        Args:
            triage_result: Results from TriageAgent
            request: The support request
            
        Returns:
            Risk score between 0.0 and 1.0
        """
        base_risk = 0.2
        
        # Increase risk for system-critical issues
        if 'system' in request.message.lower() or 'critical' in request.message.lower():
            base_risk += 0.4
        
        # Increase risk for data-related issues
        if any(keyword in request.message.lower() for keyword in ['data', 'database', 'backup', 'security']):
            base_risk += 0.3
        
        # Increase risk for novice users
        user_level = request.user_context.get('user_level', 'beginner')
        if user_level == 'beginner':
            base_risk += 0.2
        
        # Reduce risk for common, safe operations
        if self._is_safe_operation(request.message):
            base_risk -= 0.2
        
        return max(0.0, min(1.0, base_risk))
    
    def _calculate_risk_score_from_confidence(self, confidence_result: ConfidenceResult) -> float:
        """Calculate risk based on confidence factors"""
        base_risk = 1.0 - confidence_result.confidence_score
        
        # Adjust based on factors
        factors = confidence_result.factors
        
        # Higher risk for complex requests
        if factors.get('complexity', 1.0) < 0.7:
            base_risk += 0.2
        
        # Higher risk for unclear requests
        if factors.get('clarity', 1.0) < 0.5:
            base_risk += 0.1
        
        return min(1.0, base_risk)
    
    def _determine_resolution_path(self, request: SupportRequest) -> str:
        """
        Determine whether to provide automated resolution or escalate.
        
        Args:
            request: The support request
            
        Returns:
            Resolution path: 'automated_resolution' or 'escalation'
        """
        confidence = request.confidence_score or 0.0
        risk = request.risk_score or 1.0
        
        # High confidence and low risk -> automated resolution
        if confidence >= self.confidence_threshold and risk <= self.risk_threshold:
            return "automated_resolution"
        
        # Otherwise escalate to human
        return "escalation"
    
    async def _handle_automated_resolution(self, request: SupportRequest) -> None:
        """
        Handle automated resolution using ResearchAgent.
        
        Args:
            request: The support request to resolve
        """
        if not self.agent_manager:
            raise ValueError("Agent manager not initialized")
        
        # Use ResearchAgent to find solutions
        research_input = {
            'query': request.message,
            'context': request.user_context,
            'search_type': 'support_solutions',
            'request_id': request.id
        }
        
        research_response = await self.agent_manager.execute_agent('research', research_input)
        
        if research_response.success:
            request.status = SupportRequestStatus.AUTOMATED_RESOLUTION
            request.metadata['solution'] = research_response.result
            request.metadata['resolved_by'] = 'automated_system'
            request.assigned_agent = 'research'
        else:
            # Fallback to escalation if automated resolution fails
            await self._handle_escalation(request)
    
    async def _handle_escalation(self, request: SupportRequest) -> None:
        """
        Handle escalation to human expert.
        
        Args:
            request: The support request to escalate
        """
        request.status = SupportRequestStatus.ESCALATED
        request.metadata['escalation_reason'] = self._get_escalation_reason(request)
        request.metadata['escalated_at'] = datetime.now().isoformat()
        
        # Enrich context for human expert
        enriched_context = await self._enrich_context_for_human(request)
        request.metadata['enriched_context'] = enriched_context
    
    async def _enrich_context_for_human(self, request: SupportRequest) -> Dict[str, Any]:
        """
        Enrich context information for human expert.
        
        Args:
            request: The support request
            
        Returns:
            Enriched context dictionary
        """
        enriched = {
            'ai_analysis': {
                'confidence_score': request.confidence_score,
                'risk_score': request.risk_score,
                'priority': request.priority.value
            },
            'user_context': request.user_context,
            'similar_cases': [],
            'suggested_actions': []
        }
        
        # Use ResearchAgent to find similar cases
        if self.agent_manager:
            try:
                similar_cases_input = {
                    'query': f"similar issues: {request.message}",
                    'context': request.user_context,
                    'search_type': 'case_history',
                    'limit': 5
                }
                
                similar_response = await self.agent_manager.execute_agent('research', similar_cases_input)
                if similar_response.success:
                    enriched['similar_cases'] = similar_response.result
                    
            except Exception as e:
                enriched['similar_cases_error'] = str(e)
        
        return enriched
    
    def _determine_priority(self, message: str, user_context: Dict[str, Any]) -> SupportRequestPriority:
        """Determine priority based on message content and context."""
        message_lower = message.lower()
        
        # Critical keywords
        if any(keyword in message_lower for keyword in ['critical', 'emergency', 'down', 'outage', 'security breach']):
            return SupportRequestPriority.CRITICAL
        
        # High priority keywords
        if any(keyword in message_lower for keyword in ['urgent', 'asap', 'blocking', 'production']):
            return SupportRequestPriority.HIGH
        
        # Medium priority (default)
        return SupportRequestPriority.MEDIUM
    
    def _is_common_issue(self, message: str) -> bool:
        """Check if this is a common, well-documented issue."""
        common_patterns = [
            'how to', 'password reset', 'login', 'forgot password',
            'installation', 'setup', 'configuration', 'getting started'
        ]
        message_lower = message.lower()
        return any(pattern in message_lower for pattern in common_patterns)
    
    def _is_complex_issue(self, message: str) -> bool:
        """Check if this is a complex technical issue."""
        complex_patterns = [
            'integration', 'api', 'database', 'performance', 'custom',
            'development', 'programming', 'architecture', 'scaling'
        ]
        message_lower = message.lower()
        return any(pattern in message_lower for pattern in complex_patterns)
    
    def _is_safe_operation(self, message: str) -> bool:
        """Check if this is a safe operation with low risk."""
        safe_patterns = [
            'view', 'display', 'show', 'list', 'help', 'documentation',
            'tutorial', 'guide', 'example', 'demo'
        ]
        message_lower = message.lower()
        return any(pattern in message_lower for pattern in safe_patterns)
    
    def _get_escalation_reason(self, request: SupportRequest) -> str:
        """Get human-readable escalation reason."""
        confidence = request.confidence_score or 0.0
        risk = request.risk_score or 1.0
        
        if confidence < self.confidence_threshold:
            return f"Low confidence score ({confidence:.2f}) - requires human expertise"
        
        if risk > self.risk_threshold:
            return f"High risk score ({risk:.2f}) - requires human oversight"
        
        return "Complex issue requiring human intervention"
    
    def get_request_status(self, request_id: str) -> Optional[SupportRequest]:
        """Get the current status of a support request."""
        return self.active_requests.get(request_id)
    
    def get_active_requests(self) -> List[SupportRequest]:
        """Get all active support requests."""
        return list(self.active_requests.values())
    
    def cleanup_completed_requests(self, max_age_hours: int = 24) -> None:
        """Clean up completed requests older than specified age."""
        cutoff_time = datetime.now()
        cutoff_time = cutoff_time.replace(hour=cutoff_time.hour - max_age_hours)
        
        completed_ids = []
        for request_id, request in self.active_requests.items():
            if request.status in [SupportRequestStatus.RESOLVED, SupportRequestStatus.CLOSED]:
                if request.updated_at < cutoff_time:
                    completed_ids.append(request_id)
        
        for request_id in completed_ids:
            del self.active_requests[request_id]
            if request_id in self.processing_queue:
                self.processing_queue.remove(request_id)