"""
Database models for AI Gatekeeper System
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class SupportRequestStatus(Enum):
    NEW = "new"
    AI_AUTO = "ai_auto"
    ESCALATED = "escalated"
    HUMAN_RESOLVED = "human_resolved"
    CLOSED = "closed"

class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message = Column(Text, nullable=False)
    user_context = Column(JSON, nullable=True)
    priority = Column(String(20), nullable=False, default='medium')
    status = Column(String(20), nullable=False, default=SupportRequestStatus.NEW.value)
    
    # AI Analysis
    confidence_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    triage_analysis = Column(JSON, nullable=True)
    
    # Solution
    solution_id = Column(UUID(as_uuid=True), ForeignKey('solutions.id'), nullable=True)
    solution = relationship("Solution", back_populates="tickets")
    
    # Escalation
    escalation_reason = Column(Text, nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    human_assignee = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    feedback = relationship("SupportFeedback", back_populates="ticket")

class Solution(Base):
    __tablename__ = 'solutions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    solution_type = Column(String(50), nullable=False)
    
    # Structured solution data
    steps = Column(JSON, nullable=True)
    troubleshooting = Column(JSON, nullable=True)
    estimated_time = Column(String(50), nullable=True)
    difficulty_level = Column(String(20), nullable=True)
    
    # Effectiveness tracking
    success_rate = Column(Float, default=0.0)
    usage_count = Column(Integer, default=0)
    
    # Categorization
    category = Column(String(100), nullable=True)
    keywords = Column(JSON, nullable=True)
    
    # AI generation metadata
    agent_confidence = Column(Float, nullable=True)
    generation_method = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tickets = relationship("SupportTicket", back_populates="solution")

class SupportFeedback(Base):
    __tablename__ = 'support_feedback'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('support_tickets.id'), nullable=False)
    
    # Feedback details
    user_satisfaction = Column(Integer, nullable=False)  # 1-5 scale
    solution_helpful = Column(Boolean, nullable=True)
    resolution_time_acceptable = Column(Boolean, nullable=True)
    
    # Text feedback
    comments = Column(Text, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    
    # Outcome tracking
    issue_resolved = Column(Boolean, nullable=True)
    required_follow_up = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = relationship("SupportTicket", back_populates="feedback")

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_base'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    
    # Metadata
    keywords = Column(JSON, nullable=True)
    meta_data = Column(JSON, nullable=True)
    
    # Usage tracking
    usage_count = Column(Integer, default=0)
    effectiveness_score = Column(Float, default=0.0)
    
    # Vector embedding data
    embedding_vector = Column(JSON, nullable=True)  # Store as JSON for now
    embedding_model = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentPerformance(Base):
    __tablename__ = 'agent_performance'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_type = Column(String(100), nullable=False)
    
    # Performance metrics
    success_rate = Column(Float, default=0.0)
    avg_response_time = Column(Float, default=0.0)
    confidence_accuracy = Column(Float, default=0.0)
    user_satisfaction = Column(Float, default=0.0)
    
    # Execution counts
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    
    # Learning data
    confidence_weights = Column(JSON, nullable=True)
    learning_rate = Column(Float, default=0.1)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SwarmExecution(Base):
    __tablename__ = 'swarm_executions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('support_tickets.id'), nullable=False)
    
    # Swarm details
    participating_agents = Column(JSON, nullable=False)
    consensus_reached = Column(Boolean, default=False)
    consensus_confidence = Column(Float, nullable=True)
    
    # Results
    individual_results = Column(JSON, nullable=True)
    final_recommendation = Column(JSON, nullable=True)
    
    # Performance
    execution_time = Column(Float, nullable=True)
    success = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    ticket = relationship("SupportTicket")