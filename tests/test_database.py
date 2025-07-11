"""
Unit tests for database layer (models and CRUD operations)
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

from db.models import (
    SupportTicket, Solution, SupportFeedback, KnowledgeBase,
    AgentPerformance, SwarmExecution, SupportRequestStatus
)
from db.crud import (
    SupportTicketCRUD, SolutionCRUD, FeedbackCRUD, KnowledgeBaseCRUD,
    AgentPerformanceCRUD, SwarmExecutionCRUD
)

class TestSupportTicketModel:
    """Test SupportTicket model."""
    
    def test_create_support_ticket(self, test_db):
        """Test creating a support ticket."""
        ticket = SupportTicket(
            message="Test support request",
            user_context={"user_id": "test-user"},
            priority="high",
            status=SupportRequestStatus.NEW.value
        )
        
        test_db.add(ticket)
        test_db.commit()
        test_db.refresh(ticket)
        
        assert ticket.id is not None
        assert ticket.message == "Test support request"
        assert ticket.priority == "high"
        assert ticket.status == SupportRequestStatus.NEW.value
        assert ticket.created_at is not None
        assert ticket.updated_at is not None
    
    def test_ticket_relationships(self, test_db):
        """Test ticket relationships."""
        # Create solution
        solution = Solution(
            title="Test Solution",
            content="Test content",
            solution_type="automated"
        )
        test_db.add(solution)
        test_db.commit()
        
        # Create ticket with solution
        ticket = SupportTicket(
            message="Test request",
            user_context={"user_id": "test"},
            solution_id=solution.id
        )
        test_db.add(ticket)
        test_db.commit()
        
        # Test relationship
        assert ticket.solution == solution
        assert ticket in solution.tickets

class TestSupportTicketCRUD:
    """Test SupportTicketCRUD operations."""
    
    def test_create_ticket(self, test_db):
        """Test creating a ticket via CRUD."""
        ticket = SupportTicketCRUD.create_ticket(
            test_db,
            message="CRUD test ticket",
            user_context={"user_id": "crud-user"},
            priority="medium"
        )
        
        assert ticket.id is not None
        assert ticket.message == "CRUD test ticket"
        assert ticket.priority == "medium"
        assert ticket.status == SupportRequestStatus.NEW.value
    
    def test_get_ticket(self, test_db, sample_support_ticket):
        """Test getting a ticket by ID."""
        ticket = SupportTicketCRUD.get_ticket(test_db, str(sample_support_ticket.id))
        
        assert ticket is not None
        assert ticket.id == sample_support_ticket.id
        assert ticket.message == sample_support_ticket.message
    
    def test_get_nonexistent_ticket(self, test_db):
        """Test getting a non-existent ticket."""
        ticket = SupportTicketCRUD.get_ticket(test_db, "nonexistent-id")
        assert ticket is None
    
    def test_update_ticket_status(self, test_db, sample_support_ticket):
        """Test updating ticket status."""
        updated_ticket = SupportTicketCRUD.update_ticket_status(
            test_db,
            str(sample_support_ticket.id),
            SupportRequestStatus.AI_AUTO.value,
            confidence_score=0.9,
            risk_score=0.1
        )
        
        assert updated_ticket.status == SupportRequestStatus.AI_AUTO.value
        assert updated_ticket.confidence_score == 0.9
        assert updated_ticket.risk_score == 0.1
    
    def test_escalate_ticket(self, test_db, sample_support_ticket):
        """Test escalating a ticket."""
        escalated_ticket = SupportTicketCRUD.escalate_ticket(
            test_db,
            str(sample_support_ticket.id),
            "Complex technical issue",
            "john.doe@example.com"
        )
        
        assert escalated_ticket.status == SupportRequestStatus.ESCALATED.value
        assert escalated_ticket.escalation_reason == "Complex technical issue"
        assert escalated_ticket.human_assignee == "john.doe@example.com"
        assert escalated_ticket.escalated_at is not None
    
    def test_resolve_ticket(self, test_db, sample_support_ticket, sample_solution):
        """Test resolving a ticket."""
        resolved_ticket = SupportTicketCRUD.resolve_ticket(
            test_db,
            str(sample_support_ticket.id),
            str(sample_solution.id)
        )
        
        assert resolved_ticket.status == SupportRequestStatus.HUMAN_RESOLVED.value
        assert resolved_ticket.solution_id == sample_solution.id
        assert resolved_ticket.resolved_at is not None
    
    def test_get_active_tickets(self, test_db):
        """Test getting active tickets."""
        # Create tickets with different statuses
        ticket1 = SupportTicketCRUD.create_ticket(
            test_db, "Active ticket 1", {}, "medium"
        )
        ticket2 = SupportTicketCRUD.create_ticket(
            test_db, "Active ticket 2", {}, "high"
        )
        
        # Resolve one ticket
        SupportTicketCRUD.resolve_ticket(test_db, str(ticket2.id))
        
        active_tickets = SupportTicketCRUD.get_active_tickets(test_db)
        
        assert len(active_tickets) >= 1
        assert any(t.id == ticket1.id for t in active_tickets)
        assert not any(t.id == ticket2.id for t in active_tickets)

class TestSolutionCRUD:
    """Test SolutionCRUD operations."""
    
    def test_create_solution(self, test_db):
        """Test creating a solution."""
        solution = SolutionCRUD.create_solution(
            test_db,
            title="Test Solution",
            content="This is a test solution",
            solution_type="automated",
            steps=[{"step": 1, "description": "First step"}],
            category="technical",
            keywords=["test", "solution"],
            agent_confidence=0.85
        )
        
        assert solution.id is not None
        assert solution.title == "Test Solution"
        assert solution.content == "This is a test solution"
        assert solution.solution_type == "automated"
        assert solution.agent_confidence == 0.85
        assert solution.success_rate == 0.0  # Default
        assert solution.usage_count == 0  # Default
    
    def test_update_solution_effectiveness(self, test_db, sample_solution):
        """Test updating solution effectiveness."""
        # Store original values
        original_usage_count = sample_solution.usage_count
        original_success_rate = sample_solution.success_rate
        
        # Update with success
        updated_solution = SolutionCRUD.update_solution_effectiveness(
            test_db, str(sample_solution.id), True
        )
        
        assert updated_solution.usage_count == original_usage_count + 1
        assert updated_solution.success_rate >= original_success_rate
        
        # Update with failure
        updated_solution = SolutionCRUD.update_solution_effectiveness(
            test_db, str(sample_solution.id), False
        )
        
        assert updated_solution.usage_count == original_usage_count + 2
    
    def test_search_solutions(self, test_db):
        """Test searching solutions."""
        # Create test solutions
        solution1 = SolutionCRUD.create_solution(
            test_db,
            title="Password Reset",
            content="How to reset your password",
            solution_type="automated",
            category="authentication"
        )
        
        solution2 = SolutionCRUD.create_solution(
            test_db,
            title="Login Issues",
            content="Troubleshoot login problems",
            solution_type="automated",
            category="authentication"
        )
        
        # Search by content
        results = SolutionCRUD.search_solutions(test_db, "password")
        assert len(results) >= 1
        assert any(s.id == solution1.id for s in results)
        
        # Search by category
        results = SolutionCRUD.search_solutions(test_db, "login", "authentication")
        assert len(results) >= 1
        assert any(s.id == solution2.id for s in results)

class TestFeedbackCRUD:
    """Test FeedbackCRUD operations."""
    
    def test_create_feedback(self, test_db, sample_support_ticket):
        """Test creating feedback."""
        feedback = FeedbackCRUD.create_feedback(
            test_db,
            str(sample_support_ticket.id),
            user_satisfaction=5,
            solution_helpful=True,
            comments="Excellent solution!",
            issue_resolved=True
        )
        
        assert feedback.id is not None
        assert feedback.ticket_id == sample_support_ticket.id
        assert feedback.user_satisfaction == 5
        assert feedback.solution_helpful is True
        assert feedback.comments == "Excellent solution!"
        assert feedback.issue_resolved is True
    
    def test_get_feedback_by_ticket(self, test_db, sample_support_ticket):
        """Test getting feedback by ticket."""
        # Create multiple feedback entries
        feedback1 = FeedbackCRUD.create_feedback(
            test_db, str(sample_support_ticket.id), 4, True, "Good"
        )
        feedback2 = FeedbackCRUD.create_feedback(
            test_db, str(sample_support_ticket.id), 5, True, "Excellent"
        )
        
        feedback_list = FeedbackCRUD.get_feedback_by_ticket(
            test_db, str(sample_support_ticket.id)
        )
        
        assert len(feedback_list) >= 2
        feedback_ids = [f.id for f in feedback_list]
        assert feedback1.id in feedback_ids
        assert feedback2.id in feedback_ids

class TestKnowledgeBaseCRUD:
    """Test KnowledgeBaseCRUD operations."""
    
    def test_create_knowledge_item(self, test_db):
        """Test creating a knowledge base item."""
        kb_item = KnowledgeBaseCRUD.create_knowledge_item(
            test_db,
            title="Test Knowledge",
            content="This is test knowledge content",
            category="technical",
            keywords=["test", "knowledge"],
            metadata={"difficulty": "easy"},
            embedding_vector=[0.1, 0.2, 0.3]
        )
        
        assert kb_item.id is not None
        assert kb_item.title == "Test Knowledge"
        assert kb_item.content == "This is test knowledge content"
        assert kb_item.category == "technical"
        assert kb_item.keywords == ["test", "knowledge"]
        assert kb_item.metadata == {"difficulty": "easy"}
        assert kb_item.embedding_vector == [0.1, 0.2, 0.3]
    
    def test_get_knowledge_by_category(self, test_db):
        """Test getting knowledge by category."""
        # Create items in different categories
        item1 = KnowledgeBaseCRUD.create_knowledge_item(
            test_db, "Tech Item 1", "Content 1", "technical"
        )
        item2 = KnowledgeBaseCRUD.create_knowledge_item(
            test_db, "Tech Item 2", "Content 2", "technical"
        )
        item3 = KnowledgeBaseCRUD.create_knowledge_item(
            test_db, "User Item", "Content 3", "user_guide"
        )
        
        technical_items = KnowledgeBaseCRUD.get_knowledge_by_category(
            test_db, "technical"
        )
        
        assert len(technical_items) >= 2
        tech_ids = [item.id for item in technical_items]
        assert item1.id in tech_ids
        assert item2.id in tech_ids
        assert item3.id not in tech_ids
    
    def test_update_knowledge_effectiveness(self, test_db, sample_knowledge_base):
        """Test updating knowledge effectiveness."""
        # Store original values
        original_usage_count = sample_knowledge_base.usage_count
        original_effectiveness_score = sample_knowledge_base.effectiveness_score
        
        # Update with positive feedback
        updated_kb = KnowledgeBaseCRUD.update_knowledge_effectiveness(
            test_db, str(sample_knowledge_base.id), True
        )
        
        assert updated_kb.usage_count == original_usage_count + 1
        assert updated_kb.effectiveness_score >= original_effectiveness_score
        
        # Update with negative feedback
        updated_kb = KnowledgeBaseCRUD.update_knowledge_effectiveness(
            test_db, str(sample_knowledge_base.id), False
        )
        
        assert updated_kb.usage_count == original_usage_count + 2

class TestAgentPerformanceCRUD:
    """Test AgentPerformanceCRUD operations."""
    
    def test_get_or_create_performance(self, test_db):
        """Test getting or creating agent performance."""
        # Create new performance record
        performance = AgentPerformanceCRUD.get_or_create_performance(
            test_db, "test_agent"
        )
        
        assert performance.agent_type == "test_agent"
        assert performance.total_executions == 0
        assert performance.success_rate == 0.0
        
        # Get existing performance record
        performance2 = AgentPerformanceCRUD.get_or_create_performance(
            test_db, "test_agent"
        )
        
        assert performance.id == performance2.id
    
    def test_update_performance(self, test_db):
        """Test updating agent performance."""
        # Update with success
        performance = AgentPerformanceCRUD.update_performance(
            test_db,
            "test_agent",
            success=True,
            response_time=1.5,
            confidence_accuracy=0.85,
            user_satisfaction=4.5
        )
        
        assert performance.total_executions == 1
        assert performance.successful_executions == 1
        assert performance.success_rate == 1.0
        assert performance.avg_response_time == 1.5
        assert performance.confidence_accuracy == 0.85
        assert performance.user_satisfaction == 4.5
        
        # Update with failure
        performance = AgentPerformanceCRUD.update_performance(
            test_db,
            "test_agent",
            success=False,
            response_time=2.0
        )
        
        assert performance.total_executions == 2
        assert performance.successful_executions == 1
        assert performance.success_rate == 0.5

class TestSwarmExecutionCRUD:
    """Test SwarmExecutionCRUD operations."""
    
    def test_create_swarm_execution(self, test_db, sample_support_ticket):
        """Test creating swarm execution record."""
        swarm_exec = SwarmExecutionCRUD.create_swarm_execution(
            test_db,
            str(sample_support_ticket.id),
            ["triage", "confidence", "research"],
            {
                "triage": {"confidence": 0.8, "category": "technical"},
                "confidence": {"score": 0.85, "factors": {"clarity": 0.9}},
                "research": {"solutions": 3, "confidence": 0.7}
            },
            consensus_reached=True,
            consensus_confidence=0.8
        )
        
        assert swarm_exec.id is not None
        assert swarm_exec.ticket_id == sample_support_ticket.id
        assert swarm_exec.participating_agents == ["triage", "confidence", "research"]
        assert swarm_exec.consensus_reached is True
        assert swarm_exec.consensus_confidence == 0.8
        assert "triage" in swarm_exec.individual_results
        assert "confidence" in swarm_exec.individual_results
        assert "research" in swarm_exec.individual_results