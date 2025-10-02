"""
CRUD operations for AI Gatekeeper database
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_
import json
import uuid

from .models import (
    SupportTicket, Solution, SupportFeedback, KnowledgeBase,
    AgentPerformance, SwarmExecution, SupportRequestStatus
)
from .validators import InputValidator

class SupportTicketCRUD:
    """CRUD operations for support tickets"""
    
    @staticmethod
    def create_ticket(db: Session, message: str, user_context: Dict[str, Any], 
                     priority: str = 'medium') -> SupportTicket:
        """Create a new support ticket"""
        ticket = SupportTicket(
            message=message,
            user_context=user_context,
            priority=priority,
            status=SupportRequestStatus.NEW.value
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket
    
    @staticmethod
    def get_ticket(db: Session, ticket_id: Union[str, uuid.UUID]) -> Optional[SupportTicket]:
        """Get ticket by ID"""
        if isinstance(ticket_id, str):
            try:
                ticket_id = uuid.UUID(ticket_id)
            except ValueError:
                return None
        return db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    
    @staticmethod
    def update_ticket_status(db: Session, ticket_id: Union[str, uuid.UUID], status: str, 
                           confidence_score: float = None, risk_score: float = None,
                           triage_analysis: Dict[str, Any] = None) -> Optional[SupportTicket]:
        """Update ticket status and analysis"""
        if isinstance(ticket_id, str):
            ticket_id = uuid.UUID(ticket_id)
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if ticket:
            ticket.status = status
            ticket.updated_at = datetime.utcnow()
            
            if confidence_score is not None:
                ticket.confidence_score = confidence_score
            if risk_score is not None:
                ticket.risk_score = risk_score
            if triage_analysis is not None:
                ticket.triage_analysis = triage_analysis
            
            db.commit()
            db.refresh(ticket)
        return ticket
    
    @staticmethod
    def escalate_ticket(db: Session, ticket_id: Union[str, uuid.UUID], escalation_reason: str,
                       human_assignee: str = None) -> Optional[SupportTicket]:
        """Escalate ticket to human"""
        if isinstance(ticket_id, str):
            ticket_id = uuid.UUID(ticket_id)
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if ticket:
            ticket.status = SupportRequestStatus.ESCALATED.value
            ticket.escalation_reason = escalation_reason
            ticket.escalated_at = datetime.utcnow()
            ticket.human_assignee = human_assignee
            ticket.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(ticket)
        return ticket
    
    @staticmethod
    def resolve_ticket(db: Session, ticket_id: Union[str, uuid.UUID], solution_id: Union[str, uuid.UUID] = None) -> Optional[SupportTicket]:
        """Resolve ticket"""
        if isinstance(ticket_id, str):
            ticket_id = uuid.UUID(ticket_id)
        if isinstance(solution_id, str):
            solution_id = uuid.UUID(solution_id)
        ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
        if ticket:
            ticket.status = SupportRequestStatus.HUMAN_RESOLVED.value
            ticket.resolved_at = datetime.utcnow()
            ticket.updated_at = datetime.utcnow()
            
            if solution_id:
                ticket.solution_id = solution_id
            
            db.commit()
            db.refresh(ticket)
        return ticket
    
    @staticmethod
    def get_active_tickets(db: Session, limit: int = 100) -> List[SupportTicket]:
        """Get active tickets"""
        return db.query(SupportTicket).filter(
            SupportTicket.status.in_([
                SupportRequestStatus.NEW.value,
                SupportRequestStatus.AI_AUTO.value,
                SupportRequestStatus.ESCALATED.value
            ])
        ).order_by(desc(SupportTicket.created_at)).limit(limit).all()
    
    @staticmethod
    def get_tickets_by_status(db: Session, status: str, limit: int = 100) -> List[SupportTicket]:
        """Get tickets by status"""
        return db.query(SupportTicket).filter(
            SupportTicket.status == status
        ).order_by(desc(SupportTicket.created_at)).limit(limit).all()

class SolutionCRUD:
    """CRUD operations for solutions"""
    
    @staticmethod
    def create_solution(db: Session, title: str, content: str, solution_type: str,
                       steps: List[Dict] = None, category: str = None,
                       keywords: List[str] = None, agent_confidence: float = None) -> Solution:
        """Create a new solution"""
        solution = Solution(
            title=title,
            content=content,
            solution_type=solution_type,
            steps=steps,
            category=category,
            keywords=keywords,
            agent_confidence=agent_confidence
        )
        db.add(solution)
        db.commit()
        db.refresh(solution)
        return solution
    
    @staticmethod
    def get_solution(db: Session, solution_id: str) -> Optional[Solution]:
        """Get solution by ID"""
        return db.query(Solution).filter(Solution.id == solution_id).first()
    
    @staticmethod
    def update_solution_effectiveness(db: Session, solution_id: Union[str, uuid.UUID], 
                                    success: bool) -> Optional[Solution]:
        """Update solution effectiveness based on feedback"""
        if isinstance(solution_id, str):
            try:
                solution_id = uuid.UUID(solution_id)
            except ValueError:
                return None
        solution = db.query(Solution).filter(Solution.id == solution_id).first()
        if solution:
            solution.usage_count += 1
            
            # Update success rate using exponential moving average
            if solution.usage_count == 1:
                solution.success_rate = 1.0 if success else 0.0
            else:
                alpha = 0.1  # Learning rate
                new_success = 1.0 if success else 0.0
                solution.success_rate = (1 - alpha) * solution.success_rate + alpha * new_success
            
            solution.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(solution)
        return solution
    
    @staticmethod
    def search_solutions(db: Session, query: str, category: str = None,
                        limit: int = 10) -> List[Solution]:
        """
        Search solutions by content - SQL injection safe.

        Args:
            db: Database session
            query: Search query (will be validated)
            category: Optional category filter (will be validated)
            limit: Maximum results to return

        Returns:
            List of matching solutions

        Raises:
            ValueError: If query or category validation fails
        """
        # Validate and sanitize inputs
        validated_query = InputValidator.validate_search_query(query)
        validated_limit = InputValidator.validate_integer(
            limit, min_val=1, max_val=100, field_name="limit"
        )

        query_filter = db.query(Solution)

        # Validate category if provided
        if category:
            validated_category = InputValidator.validate_category(category)
            query_filter = query_filter.filter(Solution.category == validated_category)

        # Create safe search filter using parameterized queries
        search_filter = InputValidator.create_safe_search_filter(
            Solution,
            validated_query,
            ['content', 'title']
        )
        query_filter = query_filter.filter(search_filter)

        return query_filter.order_by(desc(Solution.success_rate)).limit(validated_limit).all()

class FeedbackCRUD:
    """CRUD operations for feedback"""
    
    @staticmethod
    def create_feedback(db: Session, ticket_id: Union[str, uuid.UUID], user_satisfaction: int,
                       solution_helpful: bool = None, comments: str = None,
                       issue_resolved: bool = None) -> SupportFeedback:
        """Create feedback for a ticket"""
        if isinstance(ticket_id, str):
            ticket_id = uuid.UUID(ticket_id)
        feedback = SupportFeedback(
            ticket_id=ticket_id,
            user_satisfaction=user_satisfaction,
            solution_helpful=solution_helpful,
            comments=comments,
            issue_resolved=issue_resolved
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        return feedback
    
    @staticmethod
    def get_feedback_by_ticket(db: Session, ticket_id: Union[str, uuid.UUID]) -> List[SupportFeedback]:
        """Get all feedback for a ticket"""
        if isinstance(ticket_id, str):
            ticket_id = uuid.UUID(ticket_id)
        return db.query(SupportFeedback).filter(
            SupportFeedback.ticket_id == ticket_id
        ).order_by(desc(SupportFeedback.created_at)).all()

class KnowledgeBaseCRUD:
    """CRUD operations for knowledge base"""
    
    @staticmethod
    def create_knowledge_item(db: Session, title: str, content: str, category: str,
                            keywords: List[str] = None, metadata: Dict[str, Any] = None,
                            embedding_vector: List[float] = None) -> KnowledgeBase:
        """Create a new knowledge base item"""
        kb_item = KnowledgeBase(
            title=title,
            content=content,
            category=category,
            keywords=keywords,
            metadata=metadata,
            embedding_vector=embedding_vector
        )
        db.add(kb_item)
        db.commit()
        db.refresh(kb_item)
        return kb_item
    
    @staticmethod
    def get_knowledge_by_category(db: Session, category: str, limit: int = 50) -> List[KnowledgeBase]:
        """Get knowledge items by category"""
        return db.query(KnowledgeBase).filter(
            KnowledgeBase.category == category
        ).order_by(desc(KnowledgeBase.effectiveness_score)).limit(limit).all()
    
    @staticmethod
    def search_knowledge(db: Session, query: str, category: str = None,
                        limit: int = 10) -> List[KnowledgeBase]:
        """
        Search knowledge base - SQL injection safe.

        Args:
            db: Database session
            query: Search query (will be validated)
            category: Optional category filter (will be validated)
            limit: Maximum results to return

        Returns:
            List of matching knowledge base items

        Raises:
            ValueError: If query or category validation fails
        """
        # Validate and sanitize inputs
        validated_query = InputValidator.validate_search_query(query)
        validated_limit = InputValidator.validate_integer(
            limit, min_val=1, max_val=100, field_name="limit"
        )

        query_filter = db.query(KnowledgeBase)

        # Validate category if provided
        if category:
            validated_category = InputValidator.validate_category(category)
            query_filter = query_filter.filter(KnowledgeBase.category == validated_category)

        # Create safe search filter using parameterized queries
        search_filter = InputValidator.create_safe_search_filter(
            KnowledgeBase,
            validated_query,
            ['content', 'title']
        )
        query_filter = query_filter.filter(search_filter)

        return query_filter.order_by(desc(KnowledgeBase.effectiveness_score)).limit(validated_limit).all()
    
    @staticmethod
    def update_knowledge_effectiveness(db: Session, kb_id: Union[str, uuid.UUID], effective: bool) -> Optional[KnowledgeBase]:
        """Update knowledge item effectiveness"""
        if isinstance(kb_id, str):
            try:
                kb_id = uuid.UUID(kb_id)
            except ValueError:
                return None
        kb_item = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
        if kb_item:
            kb_item.usage_count += 1
            
            # Update effectiveness score
            if kb_item.usage_count == 1:
                kb_item.effectiveness_score = 1.0 if effective else 0.0
            else:
                alpha = 0.1
                new_score = 1.0 if effective else 0.0
                kb_item.effectiveness_score = (1 - alpha) * kb_item.effectiveness_score + alpha * new_score
            
            kb_item.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(kb_item)
        return kb_item

class AgentPerformanceCRUD:
    """CRUD operations for agent performance"""
    
    @staticmethod
    def get_or_create_performance(db: Session, agent_type: str) -> AgentPerformance:
        """Get or create agent performance record"""
        performance = db.query(AgentPerformance).filter(
            AgentPerformance.agent_type == agent_type
        ).first()
        
        if not performance:
            performance = AgentPerformance(agent_type=agent_type)
            db.add(performance)
            db.commit()
            db.refresh(performance)
        
        return performance
    
    @staticmethod
    def update_performance(db: Session, agent_type: str, success: bool,
                         response_time: float, confidence_accuracy: float = None,
                         user_satisfaction: float = None) -> AgentPerformance:
        """Update agent performance metrics"""
        performance = AgentPerformanceCRUD.get_or_create_performance(db, agent_type)
        
        # Update execution counts
        performance.total_executions += 1
        if success:
            performance.successful_executions += 1
        else:
            performance.failed_executions += 1
        
        # Update success rate
        performance.success_rate = performance.successful_executions / performance.total_executions
        
        # Update average response time
        alpha = 0.1
        if performance.total_executions == 1:
            performance.avg_response_time = response_time
        else:
            performance.avg_response_time = (1 - alpha) * performance.avg_response_time + alpha * response_time
        
        # Update other metrics if provided
        if confidence_accuracy is not None:
            if performance.total_executions == 1:
                performance.confidence_accuracy = confidence_accuracy
            else:
                performance.confidence_accuracy = (1 - alpha) * performance.confidence_accuracy + alpha * confidence_accuracy
        
        if user_satisfaction is not None:
            if performance.total_executions == 1:
                performance.user_satisfaction = user_satisfaction
            else:
                performance.user_satisfaction = (1 - alpha) * performance.user_satisfaction + alpha * user_satisfaction
        
        performance.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(performance)
        return performance

class SwarmExecutionCRUD:
    """CRUD operations for swarm executions"""
    
    @staticmethod
    def create_swarm_execution(db: Session, ticket_id: Union[str, uuid.UUID], participating_agents: List[str],
                             individual_results: Dict[str, Any] = None,
                             consensus_reached: bool = False,
                             consensus_confidence: float = None) -> SwarmExecution:
        """Create swarm execution record"""
        if isinstance(ticket_id, str):
            ticket_id = uuid.UUID(ticket_id)
        swarm_exec = SwarmExecution(
            ticket_id=ticket_id,
            participating_agents=participating_agents,
            individual_results=individual_results,
            consensus_reached=consensus_reached,
            consensus_confidence=consensus_confidence
        )
        db.add(swarm_exec)
        db.commit()
        db.refresh(swarm_exec)
        return swarm_exec