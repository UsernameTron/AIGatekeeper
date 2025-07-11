"""
Advanced Agent Manager with Swarm Intelligence and Self-Learning
"""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import numpy as np
from collections import defaultdict, deque

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared_agents'))

from shared_agents.core.agent_factory import AgentBase, AgentResponse, AgentCapability

@dataclass
class AgentInteraction:
    source_agent: str
    target_agent: str
    interaction_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    success: bool
    response_time: float

@dataclass
class AgentPerformanceMetrics:
    agent_id: str
    success_rate: float
    avg_response_time: float
    confidence_accuracy: float
    user_satisfaction: float
    learning_rate: float

class SwarmCoordinator:
    """Coordinates agent swarm with collective intelligence"""
    
    def __init__(self):
        self.agent_interactions: List[AgentInteraction] = []
        self.agent_performance: Dict[str, AgentPerformanceMetrics] = {}
        self.collective_memory: Dict[str, Any] = {}
        self.consensus_threshold = 0.75
        
    async def coordinate_multi_agent_task(self, task: Dict[str, Any], agents: List[str]) -> Dict[str, Any]:
        """Coordinate multiple agents for complex task resolution"""
        
        results = {}
        consensus_data = []
        
        # Execute task across multiple agents
        for agent_id in agents:
            try:
                agent_result = await self._execute_agent_task(agent_id, task)
                results[agent_id] = agent_result
                
                if agent_result.success:
                    consensus_data.append({
                        'agent': agent_id,
                        'confidence': getattr(agent_result, 'confidence', 0.5),
                        'result': agent_result.result
                    })
                    
            except Exception as e:
                logging.error(f"Agent {agent_id} failed: {e}")
        
        # Calculate consensus
        consensus = await self._calculate_consensus(consensus_data)
        
        # Store collective learning
        await self._update_collective_memory(task, results, consensus)
        
        return {
            'individual_results': results,
            'consensus': consensus,
            'confidence': consensus.get('confidence', 0.0),
            'recommendation': consensus.get('recommendation')
        }
    
    async def _execute_agent_task(self, agent_id: str, task: Dict[str, Any]) -> AgentResponse:
        """Execute task on specific agent"""
        # This would be implemented by the actual agent manager
        # For now, return a mock response
        return AgentResponse(
            success=True,
            result={'mock_result': f'Agent {agent_id} processed task'},
            agent_type=agent_id,
            timestamp=datetime.now().isoformat()
        )
    
    async def _calculate_consensus(self, agent_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate consensus from multiple agent results"""
        
        if not agent_results:
            return {'confidence': 0.0, 'recommendation': 'insufficient_data'}
        
        # Weight results by agent performance and confidence
        weighted_confidences = []
        recommendations = defaultdict(float)
        
        for result in agent_results:
            agent_id = result['agent']
            confidence = result['confidence']
            
            # Get agent performance weight
            perf_metrics = self.agent_performance.get(agent_id)
            weight = perf_metrics.success_rate if perf_metrics else 0.5
            
            weighted_confidences.append(confidence * weight)
            
            # Aggregate recommendations
            if isinstance(result['result'], dict):
                rec = result['result'].get('recommendation', 'process')
                recommendations[rec] += weight
        
        # Calculate consensus confidence
        consensus_confidence = np.mean(weighted_confidences) if weighted_confidences else 0.0
        
        # Select best recommendation
        best_recommendation = max(recommendations.items(), key=lambda x: x[1])[0] if recommendations else 'escalate'
        
        return {
            'confidence': consensus_confidence,
            'recommendation': best_recommendation,
            'agent_count': len(agent_results),
            'consensus_strength': max(recommendations.values()) / sum(recommendations.values()) if recommendations else 0.0
        }
    
    async def _update_collective_memory(self, task: Dict[str, Any], results: Dict[str, Any], consensus: Dict[str, Any]):
        """Update collective memory with task results"""
        
        task_hash = hash(str(task))
        
        self.collective_memory[task_hash] = {
            'timestamp': datetime.now().isoformat(),
            'task': task,
            'results': results,
            'consensus': consensus,
            'success': consensus.get('confidence', 0.0) > self.consensus_threshold
        }
        
        # Keep only recent memory
        if len(self.collective_memory) > 1000:
            # Remove oldest entries
            sorted_memory = sorted(self.collective_memory.items(), key=lambda x: x[1]['timestamp'])
            self.collective_memory = dict(sorted_memory[-1000:])

class AdvancedAgentManager:
    """Manages advanced AI agents with learning and coordination"""
    
    def __init__(self, openai_client, config: Dict[str, Any]):
        self.openai_client = openai_client
        self.config = config
        self.agents: Dict[str, AgentBase] = {}
        self.swarm_coordinator = SwarmCoordinator()
        self.learning_data = defaultdict(list)
        
    def register_agent(self, agent_id: str, agent: AgentBase):
        """Register agent with manager"""
        self.agents[agent_id] = agent
        logging.info(f"Registered agent: {agent_id}")
    
    async def execute_agent(self, agent_type: str, input_data: Dict[str, Any]) -> AgentResponse:
        """Execute specific agent with learning tracking"""
        
        if agent_type not in self.agents:
            raise ValueError(f"Agent {agent_type} not registered")
        
        agent = self.agents[agent_type]
        start_time = time.time()
        
        try:
            # Execute agent
            response = await agent.execute(input_data)
            execution_time = time.time() - start_time
            
            # Track learning data
            await self._track_execution(agent_type, input_data, response, execution_time)
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_response = AgentResponse(
                success=False,
                result=None,
                agent_type=agent_type,
                timestamp=datetime.now().isoformat(),
                execution_time=execution_time,
                error=str(e)
            )
            
            await self._track_execution(agent_type, input_data, error_response, execution_time)
            return error_response
    
    async def execute_swarm_task(self, task: Dict[str, Any], agent_types: List[str]) -> Dict[str, Any]:
        """Execute task using swarm intelligence"""
        
        # Override the coordinator's execute method to use actual agents
        original_execute = self.swarm_coordinator._execute_agent_task
        
        async def execute_with_real_agents(agent_id: str, task: Dict[str, Any]) -> AgentResponse:
            if agent_id in self.agents:
                return await self.execute_agent(agent_id, task)
            else:
                return AgentResponse(
                    success=False,
                    result=None,
                    agent_type=agent_id,
                    timestamp=datetime.now().isoformat(),
                    error=f"Agent {agent_id} not found"
                )
        
        self.swarm_coordinator._execute_agent_task = execute_with_real_agents
        
        try:
            return await self.swarm_coordinator.coordinate_multi_agent_task(task, agent_types)
        finally:
            # Restore original method
            self.swarm_coordinator._execute_agent_task = original_execute
    
    async def _track_execution(self, agent_type: str, input_data: Dict[str, Any], 
                             response: AgentResponse, execution_time: float):
        """Track execution for learning"""
        
        learning_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_type': agent_type,
            'input_hash': hash(str(input_data)),
            'success': response.success,
            'execution_time': execution_time,
            'confidence': getattr(response, 'confidence', None)
        }
        
        self.learning_data[agent_type].append(learning_entry)
        
        # Keep only recent data
        if len(self.learning_data[agent_type]) > 1000:
            self.learning_data[agent_type] = self.learning_data[agent_type][-1000:]
    
    def get_agent_performance(self, agent_type: str) -> Dict[str, float]:
        """Get performance metrics for an agent"""
        
        if agent_type not in self.learning_data:
            return {'success_rate': 0.0, 'avg_response_time': 0.0, 'execution_count': 0}
        
        data = self.learning_data[agent_type]
        
        if not data:
            return {'success_rate': 0.0, 'avg_response_time': 0.0, 'execution_count': 0}
        
        success_count = sum(1 for entry in data if entry['success'])
        total_count = len(data)
        total_time = sum(entry['execution_time'] for entry in data)
        
        return {
            'success_rate': success_count / total_count,
            'avg_response_time': total_time / total_count,
            'execution_count': total_count
        }
    
    def get_all_performance_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for all agents"""
        
        metrics = {}
        for agent_type in self.agents.keys():
            metrics[agent_type] = self.get_agent_performance(agent_type)
        
        return metrics
    
    async def optimize_agent_selection(self, task_type: str, context: Dict[str, Any]) -> str:
        """Select optimal agent based on performance history"""
        
        # Get performance metrics for all agents
        all_metrics = self.get_all_performance_metrics()
        
        # Score agents based on success rate and response time
        agent_scores = {}
        
        for agent_type, metrics in all_metrics.items():
            if metrics['execution_count'] > 0:
                # Score based on success rate (70%) and response time (30%)
                success_score = metrics['success_rate'] * 0.7
                time_score = (1.0 / (1.0 + metrics['avg_response_time'])) * 0.3
                agent_scores[agent_type] = success_score + time_score
            else:
                # Default score for agents without history
                agent_scores[agent_type] = 0.5
        
        # Select agent with highest score
        if agent_scores:
            best_agent = max(agent_scores.items(), key=lambda x: x[1])[0]
            return best_agent
        
        # Fallback to first available agent
        return list(self.agents.keys())[0] if self.agents else None
    
    async def learn_from_feedback(self, agent_type: str, task: Dict[str, Any], 
                                feedback: Dict[str, Any]):
        """Learn from user feedback"""
        
        if agent_type not in self.learning_data:
            self.learning_data[agent_type] = []
        
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_type': agent_type,
            'task_hash': hash(str(task)),
            'user_satisfaction': feedback.get('satisfaction', 0.5),
            'feedback_type': feedback.get('type', 'general'),
            'comments': feedback.get('comments', ''),
            'success': feedback.get('success', False)
        }
        
        self.learning_data[agent_type].append(feedback_entry)
        
        # Update swarm coordinator performance metrics
        if agent_type not in self.swarm_coordinator.agent_performance:
            self.swarm_coordinator.agent_performance[agent_type] = AgentPerformanceMetrics(
                agent_id=agent_type,
                success_rate=0.5,
                avg_response_time=1.0,
                confidence_accuracy=0.5,
                user_satisfaction=0.5,
                learning_rate=0.1
            )
        
        # Update metrics with feedback
        metrics = self.swarm_coordinator.agent_performance[agent_type]
        learning_rate = metrics.learning_rate
        
        # Update satisfaction with exponential moving average
        new_satisfaction = feedback.get('satisfaction', 0.5)
        metrics.user_satisfaction = (1 - learning_rate) * metrics.user_satisfaction + learning_rate * new_satisfaction
        
        # Update success rate
        success = 1.0 if feedback.get('success', False) else 0.0
        metrics.success_rate = (1 - learning_rate) * metrics.success_rate + learning_rate * success
        
        logging.info(f"Updated learning metrics for agent {agent_type}: satisfaction={metrics.user_satisfaction:.3f}, success_rate={metrics.success_rate:.3f}")
    
    def get_swarm_intelligence_insights(self) -> Dict[str, Any]:
        """Get insights from swarm intelligence"""
        
        insights = {
            'total_agents': len(self.agents),
            'total_interactions': len(self.swarm_coordinator.agent_interactions),
            'collective_memory_size': len(self.swarm_coordinator.collective_memory),
            'agent_performance': {}
        }
        
        # Add performance insights
        for agent_type, metrics in self.swarm_coordinator.agent_performance.items():
            insights['agent_performance'][agent_type] = {
                'success_rate': metrics.success_rate,
                'avg_response_time': metrics.avg_response_time,
                'user_satisfaction': metrics.user_satisfaction,
                'learning_rate': metrics.learning_rate
            }
        
        # Add collective insights
        successful_tasks = sum(1 for memory in self.swarm_coordinator.collective_memory.values() 
                             if memory.get('success', False))
        total_tasks = len(self.swarm_coordinator.collective_memory)
        
        insights['collective_intelligence'] = {
            'successful_tasks': successful_tasks,
            'total_tasks': total_tasks,
            'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0.0,
            'consensus_threshold': self.swarm_coordinator.consensus_threshold
        }
        
        return insights