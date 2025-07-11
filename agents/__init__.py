"""
Agent Registration and Factory Setup
"""

import sys
import os

# Add shared agents to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared_agents'))

from shared_agents.core.agent_factory import AgentFactory
from .triage_agent import AdvancedTriageAgent
from .research_agent import AdvancedResearchAgent
from .confidence_agent import EnhancedConfidenceAgent

def register_all_agents():
    """Register all advanced agents with the factory"""
    
    # Register Triage Agent
    AgentFactory.register_agent(
        agent_type="triage",
        agent_class=AdvancedTriageAgent,
        input_type="dict"
    )
    
    # Register Research Agent
    AgentFactory.register_agent(
        agent_type="research", 
        agent_class=AdvancedResearchAgent,
        input_type="dict"
    )
    
    # Register Confidence Agent
    AgentFactory.register_agent(
        agent_type="confidence",
        agent_class=EnhancedConfidenceAgent, 
        input_type="dict"
    )
    
    print("✅ All advanced agents registered successfully")

# Auto-register when imported
register_all_agents()