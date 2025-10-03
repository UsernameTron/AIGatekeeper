#!/usr/bin/env python3
"""
AI Gatekeeper System - Main Application Entry Point
A standalone support ticketing automation system
"""

import os
import sys
import asyncio
from flask import Flask, jsonify
from flask_cors import CORS

# Add project paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'shared_agents'))

# Add imports
from core.confidence_agent import ConfidenceAgent
from knowledge.knowledge_loader import KnowledgeLoader
from core.advanced_agent_manager import AdvancedAgentManager
from agents import *  # Auto-registers agents
import openai

async def initialize_confidence_agent(app):
    """Initialize confidence agent with knowledge base"""
    
    # Create OpenAI client
    openai_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Create confidence agent
    confidence_agent = ConfidenceAgent(openai_client)
    
    # Load knowledge base
    knowledge_items = await KnowledgeLoader.load_sample_knowledge()
    await confidence_agent.load_knowledge_base(knowledge_items)
    
    # Set in support processor
    if hasattr(app, 'support_processor'):
        app.support_processor.set_confidence_agent(confidence_agent)
    
    print("✅ Confidence agent initialized with knowledge base")
    return confidence_agent

async def initialize_advanced_agents(app):
    """Initialize advanced agent system"""
    
    openai_client = openai.AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    config = {
        'openai_client': openai_client,
        'model': 'gpt-4o',
        'fast_model': 'gpt-4o-mini'
    }
    
    # Create advanced agent manager
    agent_manager = AdvancedAgentManager(openai_client, config)
    
    # Create and register agents
    from shared_agents.core.agent_factory import AgentFactory
    
    agents_config = {**config, 'search_system': getattr(app, 'search_system', None)}
    
    triage_agent = AgentFactory.create_agent('triage', {**agents_config, 'name': 'Production Triage', 'agent_type': 'triage'})
    research_agent = AgentFactory.create_agent('research', {**agents_config, 'name': 'Production Research', 'agent_type': 'research'})
    confidence_agent = AgentFactory.create_agent('confidence', {**agents_config, 'name': 'Production Confidence', 'agent_type': 'confidence'})
    
    agent_manager.register_agent('triage', triage_agent)
    agent_manager.register_agent('research', research_agent)
    agent_manager.register_agent('confidence', confidence_agent)
    
    # Initialize confidence agent knowledge base
    from knowledge.knowledge_loader import KnowledgeLoader
    knowledge_items = await KnowledgeLoader.load_sample_knowledge()
    await confidence_agent.load_knowledge_base(knowledge_items)
    
    app.advanced_agent_manager = agent_manager
    
    # Connect to support processor
    if hasattr(app, 'support_processor'):
        app.support_processor.set_advanced_agent_manager(agent_manager)
    
    print("✅ Advanced agent system initialized")
    return agent_manager

def validate_environment():
    """Validate environment configuration before starting app."""
    print("🔐 Validating environment configuration...")

    # Import and run secrets validator
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))
    try:
        from validate_secrets import validate_secrets
        if not validate_secrets():
            print("\n❌ Environment validation failed!")
            print("Please fix the errors above before starting the application.")
            sys.exit(1)
    except ImportError as e:
        print(f"⚠️  Could not import secrets validator: {e}")
        # Continue but warn

    print("✅ Environment validation passed\n")

def create_app():
    """Create and configure the AI Gatekeeper Flask application."""
    # Initialize logging first (before anything else)
    from core.logging_config import setup_logging, init_audit_logger
    setup_logging()
    init_audit_logger()

    # Validate environment
    validate_environment()

    app = Flask(__name__)

    # Enable CORS
    CORS(app)

    # Setup distributed tracing
    try:
        from core.tracing import setup_tracing
        tracer = setup_tracing(app=app)
        if tracer:
            app.tracer = tracer
            print("✅ Distributed tracing initialized successfully")
    except Exception as tracing_error:
        print(f"⚠️  Tracing initialization failed: {tracing_error}")

    # Basic configuration - SECRET_KEY must be set
    secret_key = os.getenv('SECRET_KEY')
    if not secret_key:
        raise ValueError(
            "SECRET_KEY environment variable must be set. "
            "This is different from JWT_SECRET_KEY and is used for Flask sessions."
        )
    app.config['SECRET_KEY'] = secret_key
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    # Request timeout configuration
    app.config['REQUEST_TIMEOUT'] = int(os.getenv('REQUEST_TIMEOUT', '120'))  # 2 minutes default
    app.config['OPENAI_TIMEOUT'] = int(os.getenv('OPENAI_TIMEOUT', '60'))  # 1 minute for AI calls

    # Add logging middleware
    try:
        from integrations.logging_middleware import add_logging_middleware
        add_logging_middleware(app)
        print("✅ Logging middleware initialized successfully")
    except Exception as logging_error:
        print(f"⚠️  Logging middleware initialization failed: {logging_error}")

    # Add timeout monitoring
    try:
        from core.timeout_middleware import add_timeout_monitoring
        add_timeout_monitoring(app)
        print("✅ Timeout monitoring initialized successfully")
    except Exception as timeout_error:
        print(f"⚠️  Timeout monitoring initialization failed: {timeout_error}")

    # Initialize rate limiter
    try:
        from core.rate_limiter import init_rate_limiter
        init_rate_limiter(app)
        print("✅ Rate limiter initialized successfully")
    except Exception as rate_limit_error:
        print(f"⚠️  Rate limiter initialization failed: {rate_limit_error}")

    # Add security headers
    try:
        from core.security_headers import add_security_headers
        add_security_headers(app)
        print("✅ Security headers middleware initialized successfully")
    except Exception as security_error:
        print(f"⚠️  Security headers initialization failed: {security_error}")

    # Initialize AI Gatekeeper components
    try:
        # Import and register AI Gatekeeper routes
        from integrations.ai_gatekeeper_routes import register_ai_gatekeeper_routes
        register_ai_gatekeeper_routes(app)
        
        # Initialize monitoring system
        from monitoring.metrics_system import monitoring_bp, initialize_health_checks, metrics_collector
        from monitoring.ai_metrics import init_ai_metrics
        app.register_blueprint(monitoring_bp)

        # Initialize AI metrics tracking
        init_ai_metrics(metrics_collector)
        print("✅ AI metrics tracking initialized")

        # Initialize health checks (will be improved when components are available)
        try:
            initialize_health_checks(None, None, None)
        except Exception as health_error:
            print(f"⚠️  Health checks initialization failed: {health_error}")
        
        # Initialize Slack Events listener
        try:
            from integrations.slack_events_listener import create_slack_listener
            app.slack_listener = create_slack_listener(
                support_processor=getattr(app, 'support_processor', None),
                flask_app=app
            )
            if app.slack_listener:
                print("✅ Slack Events listener initialized successfully")
            else:
                print("⚠️  Slack Events listener not configured (missing tokens)")
        except Exception as slack_error:
            print(f"⚠️  Slack Events listener initialization failed: {slack_error}")
        
        # Setup authentication middleware
        try:
            from auth.middleware import setup_auth_middleware
            setup_auth_middleware(app)
            print("✅ Authentication middleware configured successfully")
        except Exception as auth_error:
            print(f"⚠️  Authentication middleware setup failed: {auth_error}")
        
        print("✅ AI Gatekeeper routes and monitoring registered successfully")
        
    except Exception as e:
        print(f"⚠️  AI Gatekeeper initialization failed: {e}")
        # Continue with basic app even if AI Gatekeeper fails to initialize
    
    # Initialize confidence agent and advanced agent system
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        app.confidence_agent = loop.run_until_complete(initialize_confidence_agent(app))
        app.advanced_agent_manager = loop.run_until_complete(initialize_advanced_agents(app))
        loop.close()
    except Exception as e:
        print(f"⚠️ Advanced agent system initialization failed: {e}")
    
    @app.route('/')
    def index():
        """Main index route."""
        return jsonify({
            'name': 'AI Gatekeeper System',
            'description': 'Intelligent Support Ticketing Automation',
            'version': '1.0.0',
            'endpoints': {
                'support_evaluation': '/api/support/evaluate',
                'solution_generation': '/api/support/generate-solution',
                'request_status': '/api/support/status/<request_id>',
                'slack_integration': '/api/support/slack-integration',
                'feedback_submission': '/api/support/feedback',
                'human_handoff': '/api/support/handoff',
                'handoff_status': '/api/support/handoff/<ticket_id>/status',
                'health_check': '/api/support/health',
                'monitoring_health': '/api/monitoring/health',
                'monitoring_metrics': '/api/monitoring/metrics',
                'monitoring_performance': '/api/monitoring/performance',
                'monitoring_dashboard': '/api/monitoring/dashboard',
                'feedback_analytics': '/api/monitoring/feedback-analytics'
            },
            'documentation': 'See README.md for complete API documentation'
        })
    
    @app.route('/health')
    def health():
        """Basic health check."""
        return jsonify({
            'status': 'healthy',
            'service': 'AI Gatekeeper',
            'timestamp': '2024-07-11T00:00:00Z'
        })
    
    @app.route('/auth/token', methods=['POST'])
    def generate_token():
        """Generate authentication token for API access."""
        try:
            if not request.is_json:
                return jsonify({'error': 'Request must be JSON'}), 400
            
            data = request.get_json()
            user_id = data.get('user_id')
            email = data.get('email')
            role = data.get('role', 'api_user')
            
            if not user_id or not email:
                return jsonify({'error': 'user_id and email are required'}), 400
            
            # Simple validation - in production, this would validate against a user database
            admin_key = os.getenv('ADMIN_API_KEY', 'ai-gatekeeper-admin-key')
            provided_key = data.get('admin_key')
            
            if provided_key != admin_key:
                return jsonify({'error': 'Invalid admin key'}), 401
            
            from auth.middleware import create_admin_token, create_api_user_token
            
            if role == 'admin':
                token = create_admin_token(user_id, email)
            else:
                token = create_api_user_token(user_id, email)
            
            return jsonify({
                'token': token,
                'user_id': user_id,
                'email': email,
                'role': role,
                'expires_in': 24 * 3600  # 24 hours in seconds
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify({
            'error': 'Endpoint not found',
            'message': 'The requested endpoint does not exist',
            'available_endpoints': [
                '/api/support/evaluate',
                '/api/support/generate-solution',
                '/api/support/status/<request_id>',
                '/api/support/slack-integration',
                '/api/support/feedback',
                '/api/support/handoff',
                '/api/support/handoff/<ticket_id>/status',
                '/api/support/health',
                '/api/monitoring/health',
                '/api/monitoring/metrics',
                '/api/monitoring/performance',
                '/api/monitoring/dashboard',
                '/api/monitoring/feedback-analytics'
            ]
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    return app


def main():
    """Main application entry point."""
    # Check environment setup
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set. AI features may not work.")
        print("   Set it with: export OPENAI_API_KEY='your-api-key'")
    
    # Create and run the app
    app = create_app()
    
    print("🛡️  Starting AI Gatekeeper System...")
    print("📡 Available endpoints:")
    print("   • POST /api/support/evaluate")
    print("   • POST /api/support/generate-solution") 
    print("   • GET  /api/support/status/<request_id>")
    print("   • POST /api/support/slack-integration")
    print("   • POST /api/support/feedback")
    print("   • POST /api/support/handoff")
    print("   • GET  /api/support/handoff/<ticket_id>/status")
    print("   • GET  /api/support/health")
    print("   • GET  /api/monitoring/health")
    print("   • GET  /api/monitoring/metrics")
    print("   • GET  /api/monitoring/performance") 
    print("   • GET  /api/monitoring/dashboard")
    print("   • GET  /api/monitoring/feedback-analytics")
    print("   • GET  / (API documentation)")
    
    # Run the application
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG'],
        threaded=True
    )


if __name__ == '__main__':
    main()