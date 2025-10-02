"""
AI Gatekeeper Flask Routes
Integrates with existing Flask application to provide support workflow endpoints
"""

import json
import asyncio
import traceback
import time
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

# Import AI Gatekeeper components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.support_request_processor import SupportRequestProcessor, SupportRequest, SupportRequestStatus
from knowledge.solution_generator import KnowledgeBaseSolutionGenerator, SolutionType
from monitoring.metrics_system import metrics_collector, performance_tracker, track_execution
from auth.middleware import auth_required, optional_auth
from integrations.validators import RequestValidator, limit_content_length
from core.rate_limiter import limiter, get_rate_limit


# Create Blueprint for AI Gatekeeper routes
ai_gatekeeper_bp = Blueprint('ai_gatekeeper', __name__, url_prefix='/api/support')

# Global instances (will be initialized when routes are registered)
support_processor: Optional[SupportRequestProcessor] = None
solution_generator: Optional[KnowledgeBaseSolutionGenerator] = None


def register_ai_gatekeeper_routes(app):
    """
    Register AI Gatekeeper routes with the existing Flask application.
    
    Args:
        app: Flask application instance
    """
    global support_processor, solution_generator
    
    # Initialize AI Gatekeeper components with existing infrastructure
    try:
        from shared_agents.config.shared_config import SharedConfig
        
        # Create config (could also be loaded from app.config)
        config = SharedConfig()
        
        # Initialize support processor
        support_processor = SupportRequestProcessor(config)
        
        # Connect to existing agent manager and search system
        if hasattr(app, 'agent_manager'):
            support_processor.set_agent_manager(app.agent_manager)
        
        # Connect to advanced agent manager (swarm intelligence)
        if hasattr(app, 'advanced_agent_manager'):
            support_processor.set_advanced_agent_manager(app.advanced_agent_manager)
        
        if hasattr(app, 'search_system'):
            support_processor.set_search_system(app.search_system)
        
        # Initialize solution generator
        solution_generator = KnowledgeBaseSolutionGenerator(
            agent_manager=getattr(app, 'agent_manager', None),
            advanced_agent_manager=getattr(app, 'advanced_agent_manager', None),
            search_system=getattr(app, 'search_system', None)
        )
        
        print("✅ AI Gatekeeper components initialized successfully")
        
    except Exception as e:
        print(f"⚠️  AI Gatekeeper initialization failed: {e}")
    
    # Register the blueprint
    app.register_blueprint(ai_gatekeeper_bp)
    
    return app


@ai_gatekeeper_bp.route('/evaluate', methods=['POST'])
@auth_required
@limiter.limit(get_rate_limit('ai_processing'))
@limit_content_length(100000)  # 100KB max
@track_execution('support_request_evaluation')
def evaluate_support_request():
    """
    Main AI Gatekeeper endpoint for evaluating support requests.

    Expected JSON payload:
    {
        "message": "Support request description",
        "context": {
            "user_level": "beginner|intermediate|advanced",
            "system": "System information",
            "priority": "low|medium|high|critical"
        }
    }
    """
    start_time = time.time()
    try:
        # Validate request
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()

        # Apply comprehensive validation
        try:
            data = RequestValidator.validate_support_request(data)
        except ValueError as e:
            return jsonify({'error': 'Validation failed', 'details': str(e)}), 400

        # Extract validated fields
        message = data.get('message', '').strip()
        user_context = data.get('context', {})
        
        # Ensure support processor is available
        if not support_processor:
            return jsonify({'error': 'AI Gatekeeper not properly initialized'}), 503
        
        # Process support request asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            support_request = loop.run_until_complete(
                support_processor.process_support_request(message, user_context)
            )
        finally:
            loop.close()
        
        # Track metrics
        duration = time.time() - start_time
        is_automated = support_request.resolution_path == "automated_resolution"
        
        performance_tracker.track_request(
            request_type="evaluation",
            success=True,
            duration=duration,
            confidence=support_request.confidence_score,
            risk=support_request.risk_score
        )
        
        if not is_automated:
            escalation_reason = support_request.metadata.get('escalation_reason', 'unknown')
            performance_tracker.track_escalation(escalation_reason)
        
        # Format response based on resolution path
        if support_request.resolution_path == "automated_resolution":
            # Successful automated resolution
            solution_data = support_request.metadata.get('solution', {})
            
            response = {
                'action': 'automated_resolution',
                'request_id': support_request.id,
                'solution': solution_data,
                'confidence': support_request.confidence_score,
                'risk_score': support_request.risk_score,
                'estimated_time': solution_data.get('estimated_time', 'Unknown'),
                'status': support_request.status.value,
                'message': 'Solution generated successfully'
            }
        
        else:
            # Escalation to human expert
            enriched_context = support_request.metadata.get('enriched_context', {})
            
            response = {
                'action': 'escalate_to_human',
                'request_id': support_request.id,
                'analysis': {
                    'confidence_score': support_request.confidence_score,
                    'risk_score': support_request.risk_score,
                    'priority': support_request.priority.value,
                    'escalation_reason': support_request.metadata.get('escalation_reason')
                },
                'enriched_context': enriched_context,
                'status': support_request.status.value,
                'message': 'Request escalated to human expert'
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        # Track error metrics
        duration = time.time() - start_time
        performance_tracker.track_request(
            request_type="evaluation",
            success=False,
            duration=duration
        )
        
        error_details = {
            'error': 'Internal server error',
            'details': str(e),
            'type': type(e).__name__
        }
        
        # Log the full traceback for debugging
        current_app.logger.error(f"AI Gatekeeper evaluation error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


@ai_gatekeeper_bp.route('/generate-solution', methods=['POST'])
@auth_required
@limiter.limit(get_rate_limit('ai_processing'))
@limit_content_length(100000)
@track_execution('solution_generation')
def generate_solution():
    """
    Generate a detailed solution for a specific issue.
    
    Expected JSON payload:
    {
        "issue_description": "Detailed issue description",
        "context": {
            "user_level": "beginner|intermediate|advanced",
            "system": "System information"
        },
        "solution_type": "step_by_step|troubleshooting|configuration|documentation"
    }
    """
    start_time = time.time()
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        
        # Extract required fields
        issue_description = data.get('issue_description', '').strip()
        if not issue_description:
            return jsonify({'error': 'Issue description is required'}), 400
        
        user_context = data.get('context', {})
        solution_type_str = data.get('solution_type')
        
        # Parse solution type
        solution_type = None
        if solution_type_str:
            try:
                solution_type = SolutionType(solution_type_str)
            except ValueError:
                return jsonify({'error': f'Invalid solution type: {solution_type_str}'}), 400
        
        # Ensure solution generator is available
        if not solution_generator:
            return jsonify({'error': 'Solution generator not properly initialized'}), 503
        
        # Generate solution asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            generated_solution = loop.run_until_complete(
                solution_generator.generate_solution(
                    issue_description, 
                    user_context, 
                    solution_type
                )
            )
        finally:
            loop.close()
        
        # Format solution for response
        solution_response = {
            'solution_id': generated_solution.id,
            'title': generated_solution.title,
            'summary': generated_solution.summary,
            'solution_type': generated_solution.solution_type.value,
            'complexity': generated_solution.complexity.value,
            'estimated_time': generated_solution.estimated_time,
            'confidence_score': generated_solution.confidence_score,
            'success_rate': generated_solution.success_rate,
            'steps': [
                {
                    'step_number': step.step_number,
                    'title': step.title,
                    'description': step.description,
                    'commands': step.commands,
                    'expected_result': step.expected_result,
                    'troubleshooting': step.troubleshooting,
                    'risk_level': step.risk_level
                }
                for step in generated_solution.steps
            ],
            'prerequisites': generated_solution.prerequisites,
            'warnings': generated_solution.warnings,
            'related_docs': generated_solution.related_docs,
            'generated_at': generated_solution.generated_at.isoformat(),
            'metadata': generated_solution.metadata
        }
        
        return jsonify(solution_response), 200
        
    except Exception as e:
        error_details = {
            'error': 'Solution generation failed',
            'details': str(e),
            'type': type(e).__name__
        }
        
        current_app.logger.error(f"Solution generation error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


@ai_gatekeeper_bp.route('/status/<request_id>', methods=['GET'])
@auth_required
@limiter.limit(get_rate_limit('status'))
def get_request_status(request_id: str):
    """
    Get the current status of a support request.
    
    Args:
        request_id: The ID of the support request
    """
    try:
        if not support_processor:
            return jsonify({'error': 'AI Gatekeeper not properly initialized'}), 503
        
        support_request = support_processor.get_request_status(request_id)
        
        if not support_request:
            return jsonify({'error': 'Request not found'}), 404
        
        status_response = {
            'request_id': support_request.id,
            'status': support_request.status.value,
            'priority': support_request.priority.value,
            'message': support_request.message[:100] + '...' if len(support_request.message) > 100 else support_request.message,
            'confidence_score': support_request.confidence_score,
            'risk_score': support_request.risk_score,
            'resolution_path': support_request.resolution_path,
            'assigned_agent': support_request.assigned_agent,
            'created_at': support_request.created_at.isoformat(),
            'updated_at': support_request.updated_at.isoformat(),
            'metadata': support_request.metadata
        }
        
        return jsonify(status_response), 200
        
    except Exception as e:
        error_details = {
            'error': 'Status retrieval failed',
            'details': str(e)
        }
        
        current_app.logger.error(f"Status retrieval error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


@ai_gatekeeper_bp.route('/active-requests', methods=['GET'])
@auth_required
def get_active_requests():
    """
    Get all active support requests.
    """
    try:
        if not support_processor:
            return jsonify({'error': 'AI Gatekeeper not properly initialized'}), 503
        
        active_requests = support_processor.get_active_requests()
        
        requests_response = {
            'total_requests': len(active_requests),
            'requests': [
                {
                    'request_id': req.id,
                    'status': req.status.value,
                    'priority': req.priority.value,
                    'message_preview': req.message[:100] + '...' if len(req.message) > 100 else req.message,
                    'confidence_score': req.confidence_score,
                    'risk_score': req.risk_score,
                    'resolution_path': req.resolution_path,
                    'created_at': req.created_at.isoformat(),
                    'updated_at': req.updated_at.isoformat()
                }
                for req in active_requests
            ]
        }
        
        return jsonify(requests_response), 200
        
    except Exception as e:
        error_details = {
            'error': 'Active requests retrieval failed',
            'details': str(e)
        }
        
        current_app.logger.error(f"Active requests retrieval error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


@ai_gatekeeper_bp.route('/slack-integration', methods=['POST'])
def slack_integration():
    """
    Handle Slack integration for AI Gatekeeper.
    
    Expected JSON payload:
    {
        "channel": "Channel ID",
        "user": "User ID", 
        "message": "Support request message",
        "context": {
            "user_level": "beginner|intermediate|advanced"
        }
    }
    """
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        
        # Extract Slack-specific fields
        channel = data.get('channel')
        user = data.get('user')
        message = data.get('message', '').strip()
        context = data.get('context', {})
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Add Slack context
        context.update({
            'source': 'slack',
            'channel': channel,
            'user': user,
            'timestamp': datetime.now().isoformat()
        })
        
        # Process through main evaluation endpoint
        if not support_processor:
            return jsonify({'error': 'AI Gatekeeper not properly initialized'}), 503
        
        # Process support request
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            support_request = loop.run_until_complete(
                support_processor.process_support_request(message, context)
            )
        finally:
            loop.close()
        
        # Format response for Slack
        if support_request.resolution_path == "automated_resolution":
            solution_data = support_request.metadata.get('solution', {})
            
            # Format solution for Slack message
            slack_message = format_solution_for_slack(solution_data, support_request.confidence_score)
            
            response = {
                'action': 'send_slack_message',
                'channel': channel,
                'message': slack_message,
                'request_id': support_request.id,
                'message_type': 'automated_solution'
            }
        
        else:
            # Format escalation message for Slack
            escalation_message = format_escalation_for_slack(support_request)
            
            response = {
                'action': 'send_slack_message',
                'channel': channel,
                'message': escalation_message,
                'request_id': support_request.id,
                'message_type': 'escalation',
                'escalation_data': {
                    'priority': support_request.priority.value,
                    'confidence_score': support_request.confidence_score,
                    'risk_score': support_request.risk_score
                }
            }
        
        return jsonify(response), 200
        
    except Exception as e:
        error_details = {
            'error': 'Slack integration failed',
            'details': str(e)
        }
        
        current_app.logger.error(f"Slack integration error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


@ai_gatekeeper_bp.route('/feedback', methods=['POST'])
@auth_required
@limiter.limit(get_rate_limit('feedback'))
@limit_content_length(50000)  # 50KB max
@track_execution('feedback_submission')
def submit_feedback():
    """
    Enhanced feedback submission with database persistence and confidence weight updates.

    Expected JSON payload:
    {
        "request_id": "Request ID",
        "solution_id": "Solution ID (optional)",
        "rating": 1-5,
        "feedback": "Text feedback",
        "outcome": "resolved|not_resolved|partially_resolved",
        "confidence_accuracy": 0.0-1.0 (optional),
        "solution_helpful": true/false (optional)
    }
    """
    start_time = time.time()
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()

        # Apply comprehensive validation
        try:
            data = RequestValidator.validate_feedback(data)
        except ValueError as e:
            return jsonify({'error': 'Validation failed', 'details': str(e)}), 400

        # Extract validated fields
        request_id = data.get('request_id')
        solution_id = data.get('solution_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback', '')
        outcome = data.get('outcome')
        confidence_accuracy = data.get('confidence_accuracy')
        solution_helpful = data.get('solution_helpful')
        
        if not request_id:
            return jsonify({'error': 'Request ID is required'}), 400
        
        if rating is not None and (not isinstance(rating, int) or rating < 1 or rating > 5):
            return jsonify({'error': 'Rating must be an integer between 1 and 5'}), 400
        
        if confidence_accuracy is not None and (not isinstance(confidence_accuracy, (int, float)) or confidence_accuracy < 0 or confidence_accuracy > 1):
            return jsonify({'error': 'Confidence accuracy must be between 0.0 and 1.0'}), 400
        
        # Process feedback with database persistence and learning
        feedback_result = process_outcome_feedback(
            request_id=request_id,
            solution_id=solution_id,
            rating=rating,
            feedback_text=feedback_text,
            outcome=outcome,
            confidence_accuracy=confidence_accuracy,
            solution_helpful=solution_helpful
        )
        
        # Track metrics
        duration = time.time() - start_time
        performance_tracker.track_feedback(
            outcome=outcome,
            rating=rating,
            confidence_accuracy=confidence_accuracy,
            processing_time=duration
        )
        
        response = {
            'status': 'feedback_processed',
            'message': 'Thank you for your feedback - system learning updated',
            'feedback_id': feedback_result['feedback_id'],
            'confidence_updates': feedback_result.get('confidence_updates', {}),
            'learning_impact': feedback_result.get('learning_impact', 'moderate')
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        # Track error metrics
        duration = time.time() - start_time
        performance_tracker.track_request(
            request_type="feedback",
            success=False,
            duration=duration
        )
        
        error_details = {
            'error': 'Feedback submission failed',
            'details': str(e),
            'type': type(e).__name__
        }
        
        current_app.logger.error(f"Feedback submission error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


def process_outcome_feedback(request_id: str, solution_id: str = None, rating: int = None, 
                           feedback_text: str = '', outcome: str = None, 
                           confidence_accuracy: float = None, solution_helpful: bool = None) -> Dict[str, Any]:
    """
    Process feedback with database persistence and confidence weight updates.
    
    Args:
        request_id: The support request ID
        solution_id: Optional solution ID
        rating: User rating (1-5)
        feedback_text: Text feedback
        outcome: Resolution outcome
        confidence_accuracy: How accurate the AI confidence was
        solution_helpful: Whether the solution was helpful
    
    Returns:
        Dictionary with feedback processing results
    """
    from db import get_db_session
    from db.crud import FeedbackCRUD, SupportTicketCRUD, SolutionCRUD, AgentPerformanceCRUD
    
    db_session = get_db_session()
    
    try:
        # 1. Store feedback in database
        issue_resolved = outcome == 'resolved'
        
        feedback_record = FeedbackCRUD.create_feedback(
            db_session,
            ticket_id=request_id,
            user_satisfaction=rating,
            solution_helpful=solution_helpful,
            comments=feedback_text,
            issue_resolved=issue_resolved
        )
        
        # 2. Update solution effectiveness if solution_id provided
        confidence_updates = {}
        if solution_id:
            solution_success = outcome == 'resolved'
            updated_solution = SolutionCRUD.update_solution_effectiveness(
                db_session, solution_id, solution_success
            )
            if updated_solution:
                confidence_updates['solution_success_rate'] = updated_solution.success_rate
                confidence_updates['solution_usage_count'] = updated_solution.usage_count
        
        # 3. Update agent performance metrics
        ticket = SupportTicketCRUD.get_ticket(db_session, request_id)
        if ticket:
            # Update confidence agent performance
            if confidence_accuracy is not None:
                AgentPerformanceCRUD.update_performance(
                    db_session,
                    agent_type='confidence',
                    success=outcome == 'resolved',
                    response_time=1.0,  # Placeholder - would track actual response time
                    confidence_accuracy=confidence_accuracy,
                    user_satisfaction=rating / 5.0 if rating else None
                )
                confidence_updates['confidence_agent_accuracy'] = confidence_accuracy
            
            # Update triage agent performance
            if ticket.triage_analysis:
                triage_success = outcome == 'resolved'
                AgentPerformanceCRUD.update_performance(
                    db_session,
                    agent_type='triage',
                    success=triage_success,
                    response_time=1.0,  # Placeholder
                    user_satisfaction=rating / 5.0 if rating else None
                )
        
        # 4. Update knowledge base effectiveness
        if ticket and ticket.triage_analysis:
            kb_items = ticket.triage_analysis.get('knowledge_base_items', [])
            for kb_item in kb_items:
                if isinstance(kb_item, dict) and 'id' in kb_item:
                    from db.crud import KnowledgeBaseCRUD
                    KnowledgeBaseCRUD.update_knowledge_effectiveness(
                        db_session, kb_item['id'], outcome == 'resolved'
                    )
        
        # 5. Calculate learning impact
        learning_impact = 'low'
        if confidence_accuracy is not None:
            accuracy_delta = abs(confidence_accuracy - 0.5)  # How far from random
            if accuracy_delta > 0.3:
                learning_impact = 'high'
            elif accuracy_delta > 0.15:
                learning_impact = 'moderate'
        
        # Enhanced learning impact based on outcome
        if outcome == 'resolved' and rating and rating >= 4:
            learning_impact = 'high'
        elif outcome == 'not_resolved' and rating and rating <= 2:
            learning_impact = 'high'
        
        db_session.commit()
        
        return {
            'feedback_id': str(feedback_record.id),
            'confidence_updates': confidence_updates,
            'learning_impact': learning_impact,
            'metrics_updated': True
        }
        
    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Feedback processing error: {e}")
        raise
    finally:
        db_session.close()


def format_solution_for_slack(solution_data: Dict[str, Any], confidence_score: float) -> str:
    """Format solution data for Slack message."""
    title = solution_data.get('title', 'Solution')
    summary = solution_data.get('summary', 'Generated solution')
    steps = solution_data.get('steps', [])
    
    message = f"🤖 *AI Support Resolution*\n\n"
    message += f"**{title}**\n\n"
    message += f"{summary}\n\n"
    
    if steps:
        message += "*Steps to resolve:*\n"
        for i, step in enumerate(steps[:5], 1):  # Limit to 5 steps for Slack
            if isinstance(step, dict):
                step_title = step.get('title', f'Step {i}')
                step_desc = step.get('description', '')
            else:
                step_title = f'Step {i}'
                step_desc = str(step)
            
            message += f"{i}. {step_title}: {step_desc}\n"
        
        if len(steps) > 5:
            message += f"... and {len(steps) - 5} more steps\n"
    
    message += f"\n**Confidence**: {confidence_score:.0%}\n"
    message += f"**Estimated Time**: {solution_data.get('estimated_time', 'Unknown')}\n\n"
    message += "Need more help? Reply to this message or escalate to human support."
    
    return message


def format_escalation_for_slack(support_request: SupportRequest) -> str:
    """Format escalation data for Slack message."""
    message = f"👨‍💻 *Escalated to Human Expert*\n\n"
    message += f"**Issue**: {support_request.message[:200]}...\n\n" if len(support_request.message) > 200 else f"**Issue**: {support_request.message}\n\n"
    message += f"**Priority**: {support_request.priority.value.upper()}\n"
    message += f"**Request ID**: {support_request.id}\n\n"
    
    escalation_reason = support_request.metadata.get('escalation_reason', 'Requires human expertise')
    message += f"**Escalation Reason**: {escalation_reason}\n\n"
    
    message += "You'll be contacted shortly. Context has been shared with the support team."
    
    return message


@ai_gatekeeper_bp.route('/health', methods=['GET'])
@optional_auth
@limiter.limit(get_rate_limit('health'))
def health_check():
    """Enhanced health check endpoint for AI Gatekeeper system."""
    try:
        # Perform comprehensive health checks
        health_results = perform_comprehensive_health_check()
        
        # Determine overall status
        component_statuses = list(health_results['components'].values())
        critical_components = ['database', 'vector_store', 'support_processor']
        
        # Check critical components
        critical_healthy = all(
            health_results['components'].get(comp, {}).get('healthy', False) 
            for comp in critical_components
        )
        
        # Determine overall health
        if critical_healthy:
            if all(comp.get('healthy', False) for comp in component_statuses):
                overall_status = 'healthy'
                status_code = 200
            else:
                overall_status = 'degraded'
                status_code = 200  # Degraded but operational
        else:
            overall_status = 'unhealthy'
            status_code = 503
        
        health_results['status'] = overall_status
        health_results['timestamp'] = datetime.now().isoformat()
        
        return jsonify(health_results), status_code
        
    except Exception as e:
        health_status = {
            'status': 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'error_type': type(e).__name__
        }
        
        current_app.logger.error(f"Health check failed: {traceback.format_exc()}")
        return jsonify(health_status), 503


def perform_comprehensive_health_check() -> Dict[str, Any]:
    """Perform comprehensive health checks for all system components."""
    health_results = {
        'components': {},
        'summary': {
            'total_components': 0,
            'healthy_components': 0,
            'degraded_components': 0,
            'unhealthy_components': 0
        }
    }
    
    # Check database
    health_results['components']['database'] = check_database_health()
    
    # Check vector store
    health_results['components']['vector_store'] = check_vector_store_health()
    
    # Check support processor
    health_results['components']['support_processor'] = check_support_processor_health()
    
    # Check solution generator
    health_results['components']['solution_generator'] = check_solution_generator_health()
    
    # Check agent managers
    health_results['components']['agent_manager'] = check_agent_manager_health()
    health_results['components']['advanced_agent_manager'] = check_advanced_agent_manager_health()
    
    # Check OpenAI API
    health_results['components']['openai_api'] = check_openai_api_health()
    
    # Check Slack integration
    health_results['components']['slack_integration'] = check_slack_integration_health()
    
    # Calculate summary statistics
    component_checks = health_results['components']
    health_results['summary']['total_components'] = len(component_checks)
    
    for component_name, component_health in component_checks.items():
        if component_health.get('healthy', False):
            health_results['summary']['healthy_components'] += 1
        elif component_health.get('status') == 'degraded':
            health_results['summary']['degraded_components'] += 1
        else:
            health_results['summary']['unhealthy_components'] += 1
    
    return health_results


def check_database_health() -> Dict[str, Any]:
    """Check database connectivity and health."""
    try:
        from db.database import db_manager
        
        start_time = time.time()
        is_healthy = db_manager.health_check()
        response_time = time.time() - start_time
        
        if is_healthy:
            return {
                'healthy': True,
                'status': 'healthy',
                'response_time_ms': round(response_time * 1000, 2),
                'message': 'Database connection successful'
            }
        else:
            return {
                'healthy': False,
                'status': 'unhealthy',
                'response_time_ms': round(response_time * 1000, 2),
                'error': 'Database connection failed'
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


def check_vector_store_health() -> Dict[str, Any]:
    """Check vector store connectivity and health."""
    try:
        from db.vector_store import get_vector_store
        
        start_time = time.time()
        vector_store = get_vector_store()
        
        if vector_store:
            is_healthy = vector_store.health_check()
            response_time = time.time() - start_time
            
            if is_healthy:
                return {
                    'healthy': True,
                    'status': 'healthy',
                    'response_time_ms': round(response_time * 1000, 2),
                    'message': 'Vector store connection successful'
                }
            else:
                return {
                    'healthy': False,
                    'status': 'unhealthy',
                    'response_time_ms': round(response_time * 1000, 2),
                    'error': 'Vector store connection failed'
                }
        else:
            return {
                'healthy': False,
                'status': 'unhealthy',
                'error': 'Vector store not initialized'
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


def check_support_processor_health() -> Dict[str, Any]:
    """Check support processor health."""
    try:
        if support_processor:
            return {
                'healthy': True,
                'status': 'healthy',
                'message': 'Support processor initialized',
                'active_requests': len(support_processor.active_requests),
                'confidence_threshold': support_processor.confidence_threshold,
                'risk_threshold': support_processor.risk_threshold
            }
        else:
            return {
                'healthy': False,
                'status': 'unhealthy',
                'error': 'Support processor not initialized'
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


def check_solution_generator_health() -> Dict[str, Any]:
    """Check solution generator health."""
    try:
        if solution_generator:
            return {
                'healthy': True,
                'status': 'healthy',
                'message': 'Solution generator initialized'
            }
        else:
            return {
                'healthy': False,
                'status': 'degraded',
                'error': 'Solution generator not initialized'
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


def check_agent_manager_health() -> Dict[str, Any]:
    """Check agent manager health."""
    try:
        if support_processor and support_processor.agent_manager:
            return {
                'healthy': True,
                'status': 'healthy',
                'message': 'Agent manager initialized'
            }
        else:
            return {
                'healthy': False,
                'status': 'degraded',
                'error': 'Agent manager not initialized'
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


def check_advanced_agent_manager_health() -> Dict[str, Any]:
    """Check advanced agent manager health."""
    try:
        if support_processor and support_processor.advanced_agent_manager:
            return {
                'healthy': True,
                'status': 'healthy',
                'message': 'Advanced agent manager initialized'
            }
        else:
            return {
                'healthy': False,
                'status': 'degraded',
                'error': 'Advanced agent manager not initialized'
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


def check_openai_api_health() -> Dict[str, Any]:
    """Check OpenAI API connectivity."""
    try:
        import openai
        import os
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {
                'healthy': False,
                'status': 'unhealthy',
                'error': 'OpenAI API key not configured'
            }
        
        # Simple API test - try to list models
        start_time = time.time()
        try:
            client = openai.OpenAI(api_key=api_key)
            models = client.models.list()
            response_time = time.time() - start_time
            
            return {
                'healthy': True,
                'status': 'healthy',
                'response_time_ms': round(response_time * 1000, 2),
                'message': 'OpenAI API connection successful',
                'models_available': len(models.data) if models else 0
            }
        except Exception as api_error:
            response_time = time.time() - start_time
            return {
                'healthy': False,
                'status': 'unhealthy',
                'response_time_ms': round(response_time * 1000, 2),
                'error': str(api_error),
                'error_type': type(api_error).__name__
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


def check_slack_integration_health() -> Dict[str, Any]:
    """Check Slack integration health."""
    try:
        import os
        
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if not slack_token:
            return {
                'healthy': False,
                'status': 'degraded',
                'error': 'Slack bot token not configured',
                'message': 'Slack integration disabled'
            }
        
        # Simple validation - check token format
        if slack_token.startswith('xoxb-'):
            return {
                'healthy': True,
                'status': 'healthy',
                'message': 'Slack bot token configured',
                'note': 'Token validation requires network call'
            }
        else:
            return {
                'healthy': False,
                'status': 'degraded',
                'error': 'Invalid Slack bot token format',
                'message': 'Expected format: xoxb-...'
            }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'unhealthy',
            'error': str(e),
            'error_type': type(e).__name__
        }


@ai_gatekeeper_bp.route('/handoff', methods=['POST'])
@auth_required
@limiter.limit(get_rate_limit('ai_processing'))
@limit_content_length(100000)
@track_execution('human_handoff')
def handoff_to_human():
    """
    Handoff support ticket to human expert with comprehensive context.
    
    Expected JSON payload:
    {
        "ticket_id": "UUID of the support ticket",
        "handoff_reason": "Reason for human handoff",
        "priority": "low|medium|high|critical",
        "human_assignee": "Optional: specific human to assign to",
        "context_notes": "Additional context for human expert",
        "escalation_type": "technical|customer_service|specialist"
    }
    """
    start_time = time.time()
    try:
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
        
        data = request.get_json()
        
        # Extract required fields
        ticket_id = data.get('ticket_id')
        handoff_reason = data.get('handoff_reason', 'Manual handoff requested')
        priority = data.get('priority', 'medium')
        human_assignee = data.get('human_assignee')
        context_notes = data.get('context_notes', '')
        escalation_type = data.get('escalation_type', 'technical')
        
        if not ticket_id:
            return jsonify({'error': 'ticket_id is required'}), 400
        
        # Validate priority
        valid_priorities = ['low', 'medium', 'high', 'critical']
        if priority not in valid_priorities:
            return jsonify({'error': f'priority must be one of: {valid_priorities}'}), 400
        
        # Validate escalation type
        valid_escalation_types = ['technical', 'customer_service', 'specialist', 'billing', 'security']
        if escalation_type not in valid_escalation_types:
            return jsonify({'error': f'escalation_type must be one of: {valid_escalation_types}'}), 400
        
        # Process handoff with comprehensive context
        handoff_result = process_human_handoff(
            ticket_id=ticket_id,
            handoff_reason=handoff_reason,
            priority=priority,
            human_assignee=human_assignee,
            context_notes=context_notes,
            escalation_type=escalation_type
        )
        
        # Track metrics
        duration = time.time() - start_time
        performance_tracker.track_escalation(f"{escalation_type}_handoff")
        performance_tracker.track_request(
            request_type="handoff",
            success=True,
            duration=duration
        )
        
        response = {
            'status': 'handoff_successful',
            'message': 'Ticket successfully handed off to human expert',
            'handoff_id': handoff_result['handoff_id'],
            'ticket_id': ticket_id,
            'assigned_to': handoff_result.get('assigned_to', 'Unassigned'),
            'escalation_type': escalation_type,
            'priority': priority,
            'estimated_response_time': handoff_result.get('estimated_response_time', 'Within 2 hours'),
            'context_summary': handoff_result.get('context_summary', {}),
            'handoff_timestamp': handoff_result.get('handoff_timestamp')
        }
        
        return jsonify(response), 200
        
    except ValueError as e:
        # Handle validation errors
        error_details = {
            'error': 'Invalid request data',
            'details': str(e)
        }
        return jsonify(error_details), 400
        
    except Exception as e:
        # Track error metrics
        duration = time.time() - start_time
        performance_tracker.track_request(
            request_type="handoff",
            success=False,
            duration=duration
        )
        
        error_details = {
            'error': 'Human handoff failed',
            'details': str(e),
            'type': type(e).__name__
        }
        
        current_app.logger.error(f"Human handoff error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


@ai_gatekeeper_bp.route('/handoff/<ticket_id>/status', methods=['GET'])
@auth_required
def get_handoff_status(ticket_id: str):
    """
    Get the current status of a human handoff.
    
    Args:
        ticket_id: The ID of the support ticket
    """
    try:
        handoff_status = get_ticket_handoff_status(ticket_id)
        
        if not handoff_status:
            return jsonify({'error': 'Ticket not found or not handed off'}), 404
        
        return jsonify(handoff_status), 200
        
    except Exception as e:
        error_details = {
            'error': 'Failed to retrieve handoff status',
            'details': str(e)
        }
        
        current_app.logger.error(f"Handoff status retrieval error: {traceback.format_exc()}")
        
        return jsonify(error_details), 500


def process_human_handoff(ticket_id: str, handoff_reason: str, priority: str = 'medium',
                         human_assignee: str = None, context_notes: str = '', 
                         escalation_type: str = 'technical') -> Dict[str, Any]:
    """
    Process human handoff with comprehensive context and database updates.
    
    Args:
        ticket_id: The support ticket ID
        handoff_reason: Reason for handoff
        priority: Priority level
        human_assignee: Optional specific human assignee
        context_notes: Additional context notes
        escalation_type: Type of escalation
    
    Returns:
        Dictionary with handoff processing results
    """
    from db import get_db_session
    from db.crud import SupportTicketCRUD
    
    db_session = get_db_session()
    
    try:
        # Get the ticket
        ticket = SupportTicketCRUD.get_ticket(db_session, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Check if ticket is already closed
        if ticket.status == SupportRequestStatus.CLOSED.value:
            raise ValueError(f"Ticket {ticket_id} is already closed")
        
        # Generate comprehensive context for human expert
        context_summary = generate_handoff_context(ticket, context_notes, escalation_type)
        
        # Update ticket with handoff information
        enhanced_reason = f"[{escalation_type.upper()}] {handoff_reason}"
        if context_notes:
            enhanced_reason += f" | Notes: {context_notes}"
        
        escalated_ticket = SupportTicketCRUD.escalate_ticket(
            db_session,
            ticket_id=ticket_id,
            escalation_reason=enhanced_reason,
            human_assignee=human_assignee
        )
        
        # Update priority if provided
        if priority != 'medium':
            escalated_ticket.priority = priority
            db_session.commit()
        
        # Estimate response time based on priority and escalation type
        response_time = estimate_response_time(priority, escalation_type)
        
        # Create handoff record
        handoff_timestamp = datetime.now().isoformat()
        handoff_id = f"handoff_{ticket_id}_{int(datetime.now().timestamp())}"
        
        return {
            'handoff_id': handoff_id,
            'assigned_to': human_assignee or 'Support Team',
            'estimated_response_time': response_time,
            'context_summary': context_summary,
            'handoff_timestamp': handoff_timestamp,
            'escalation_type': escalation_type,
            'priority': priority
        }
        
    except Exception as e:
        db_session.rollback()
        current_app.logger.error(f"Handoff processing error: {e}")
        raise
    finally:
        db_session.close()


def generate_handoff_context(ticket: 'SupportTicket', context_notes: str, escalation_type: str) -> Dict[str, Any]:
    """Generate comprehensive context for human expert."""
    context = {
        'ticket_summary': {
            'id': str(ticket.id),
            'message': ticket.message,
            'priority': ticket.priority,
            'status': ticket.status,
            'created_at': ticket.created_at.isoformat(),
            'user_context': ticket.user_context
        },
        'ai_analysis': {
            'confidence_score': ticket.confidence_score,
            'risk_score': ticket.risk_score,
            'triage_analysis': ticket.triage_analysis
        },
        'escalation_context': {
            'escalation_type': escalation_type,
            'context_notes': context_notes,
            'escalation_reason': ticket.escalation_reason
        },
        'solution_attempts': [],
        'feedback_history': []
    }
    
    # Add solution information if available
    if ticket.solution:
        context['solution_attempts'].append({
            'title': ticket.solution.title,
            'content': ticket.solution.content[:200] + '...' if len(ticket.solution.content) > 200 else ticket.solution.content,
            'success_rate': ticket.solution.success_rate,
            'solution_type': ticket.solution.solution_type
        })
    
    # Add feedback if available
    if ticket.feedback:
        context['feedback_history'] = [
            {
                'rating': fb.user_satisfaction,
                'helpful': fb.solution_helpful,
                'comments': fb.comments,
                'created_at': fb.created_at.isoformat()
            }
            for fb in ticket.feedback[-3:]  # Last 3 feedback entries
        ]
    
    return context


def estimate_response_time(priority: str, escalation_type: str) -> str:
    """Estimate response time based on priority and escalation type."""
    base_times = {
        'critical': 30,    # 30 minutes
        'high': 120,       # 2 hours
        'medium': 480,     # 8 hours
        'low': 1440        # 24 hours
    }
    
    multipliers = {
        'security': 0.5,        # Security issues are urgent
        'billing': 1.0,         # Standard response
        'technical': 1.0,       # Standard response
        'customer_service': 1.2, # Slightly longer for complex service issues
        'specialist': 1.5       # Longer for specialist consultation
    }
    
    base_minutes = base_times.get(priority, 480)
    multiplier = multipliers.get(escalation_type, 1.0)
    estimated_minutes = int(base_minutes * multiplier)
    
    if estimated_minutes < 60:
        return f"{estimated_minutes} minutes"
    elif estimated_minutes < 1440:
        hours = estimated_minutes // 60
        return f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        days = estimated_minutes // 1440
        return f"{days} day{'s' if days > 1 else ''}"


def get_ticket_handoff_status(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Get handoff status for a ticket."""
    from db import get_db_session
    from db.crud import SupportTicketCRUD
    
    db_session = get_db_session()
    
    try:
        ticket = SupportTicketCRUD.get_ticket(db_session, ticket_id)
        if not ticket:
            return None
        
        if ticket.status != SupportRequestStatus.ESCALATED.value:
            return {
                'ticket_id': ticket_id,
                'status': 'not_escalated',
                'message': 'Ticket has not been escalated to human expert'
            }
        
        return {
            'ticket_id': ticket_id,
            'status': 'escalated',
            'escalated_at': ticket.escalated_at.isoformat() if ticket.escalated_at else None,
            'escalation_reason': ticket.escalation_reason,
            'human_assignee': ticket.human_assignee,
            'priority': ticket.priority,
            'last_updated': ticket.updated_at.isoformat()
        }
        
    except Exception as e:
        current_app.logger.error(f"Handoff status retrieval error: {e}")
        return None
    finally:
        db_session.close()