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

def create_app():
    """Create and configure the AI Gatekeeper Flask application."""
    app = Flask(__name__)
    
    # Enable CORS
    CORS(app)
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ai-gatekeeper-dev-key')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Initialize AI Gatekeeper components
    try:
        # Import and register AI Gatekeeper routes
        from integrations.ai_gatekeeper_routes import register_ai_gatekeeper_routes
        register_ai_gatekeeper_routes(app)
        
        # Initialize monitoring system
        from monitoring.metrics_system import monitoring_bp, initialize_health_checks
        app.register_blueprint(monitoring_bp)
        
        # Initialize health checks (will be improved when components are available)
        try:
            initialize_health_checks(None, None, None)
        except Exception as health_error:
            print(f"⚠️  Health checks initialization failed: {health_error}")
        
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
                'health_check': '/api/support/health',
                'monitoring_health': '/api/monitoring/health',
                'monitoring_metrics': '/api/monitoring/metrics',
                'monitoring_performance': '/api/monitoring/performance',
                'monitoring_dashboard': '/api/monitoring/dashboard'
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
                '/api/support/health',
                '/api/monitoring/health',
                '/api/monitoring/metrics',
                '/api/monitoring/performance',
                '/api/monitoring/dashboard'
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
    print("   • GET  /api/support/health")
    print("   • GET  /api/monitoring/health")
    print("   • GET  /api/monitoring/metrics")
    print("   • GET  /api/monitoring/performance") 
    print("   • GET  /api/monitoring/dashboard")
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