"""
Integration tests for AI Gatekeeper API endpoints
"""

import pytest
import json
from unittest.mock import patch, Mock

class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_basic_health_check(self, client):
        """Test basic health check endpoint."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['service'] == 'AI Gatekeeper'
    
    def test_comprehensive_health_check(self, client):
        """Test comprehensive health check endpoint."""
        with patch('integrations.ai_gatekeeper_routes.perform_comprehensive_health_check') as mock_health:
            mock_health.return_value = {
                'components': {
                    'database': {'healthy': True, 'status': 'healthy'},
                    'vector_store': {'healthy': True, 'status': 'healthy'},
                    'support_processor': {'healthy': True, 'status': 'healthy'},
                    'openai_api': {'healthy': True, 'status': 'healthy'}
                },
                'summary': {
                    'total_components': 4,
                    'healthy_components': 4,
                    'degraded_components': 0,
                    'unhealthy_components': 0
                }
            }
            
            response = client.get('/api/support/health')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'healthy'
            assert data['summary']['total_components'] == 4
            assert data['summary']['healthy_components'] == 4

class TestAuthenticationEndpoints:
    """Test authentication endpoints."""
    
    def test_token_generation_success(self, client, mock_env_vars):
        """Test successful token generation."""
        response = client.post('/auth/token', json={
            'user_id': 'test-user',
            'email': 'test@example.com',
            'role': 'api_user',
            'admin_key': 'test-admin-key'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'token' in data
        assert data['user_id'] == 'test-user'
        assert data['email'] == 'test@example.com'
        assert data['role'] == 'api_user'
        assert data['expires_in'] == 24 * 3600
    
    def test_token_generation_invalid_admin_key(self, client, mock_env_vars):
        """Test token generation with invalid admin key."""
        response = client.post('/auth/token', json={
            'user_id': 'test-user',
            'email': 'test@example.com',
            'role': 'api_user',
            'admin_key': 'invalid-key'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Invalid admin key'
    
    def test_token_generation_missing_data(self, client, mock_env_vars):
        """Test token generation with missing data."""
        response = client.post('/auth/token', json={
            'user_id': 'test-user',
            'admin_key': 'test-admin-key'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'user_id and email are required' in data['error']

class TestSupportEvaluation:
    """Test support evaluation endpoints."""
    
    def test_evaluate_support_request_success(self, client, api_user_token, test_data_factory):
        """Test successful support request evaluation."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('integrations.ai_gatekeeper_routes.support_processor') as mock_processor:
            # Mock support processor response
            mock_ticket = Mock()
            mock_ticket.id = 'test-ticket-123'
            mock_ticket.confidence_score = 0.85
            mock_ticket.risk_score = 0.15
            mock_ticket.resolution_path = 'automated_resolution'
            mock_ticket.status.value = 'ai_auto'
            mock_ticket.metadata = {
                'solution': {
                    'title': 'Test Solution',
                    'summary': 'This is a test solution',
                    'estimated_time': '5 minutes'
                }
            }
            
            mock_processor.process_support_request.return_value = mock_ticket
            
            response = client.post('/api/support/evaluate', 
                                 headers=headers,
                                 json=test_data_factory.create_support_request_data())
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['action'] == 'automated_resolution'
            assert data['request_id'] == 'test-ticket-123'
            assert data['confidence'] == 0.85
            assert data['risk_score'] == 0.15
            assert 'solution' in data
    
    def test_evaluate_support_request_escalation(self, client, api_user_token, test_data_factory):
        """Test support request that gets escalated."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('integrations.ai_gatekeeper_routes.support_processor') as mock_processor:
            # Mock escalation response
            mock_ticket = Mock()
            mock_ticket.id = 'test-ticket-456'
            mock_ticket.confidence_score = 0.45
            mock_ticket.risk_score = 0.65
            mock_ticket.resolution_path = 'escalation'
            mock_ticket.status.value = 'escalated'
            mock_ticket.priority.value = 'high'
            mock_ticket.metadata = {
                'escalation_reason': 'Complex technical issue',
                'enriched_context': {'similar_cases': 2}
            }
            
            mock_processor.process_support_request.return_value = mock_ticket
            
            response = client.post('/api/support/evaluate', 
                                 headers=headers,
                                 json=test_data_factory.create_support_request_data())
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['action'] == 'escalate_to_human'
            assert data['request_id'] == 'test-ticket-456'
            assert data['analysis']['confidence_score'] == 0.45
            assert data['analysis']['risk_score'] == 0.65
    
    def test_evaluate_support_request_no_auth(self, client, test_data_factory):
        """Test support request evaluation without authentication."""
        response = client.post('/api/support/evaluate', 
                             json=test_data_factory.create_support_request_data())
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Authentication failed'
    
    def test_evaluate_support_request_invalid_data(self, client, api_user_token):
        """Test support request evaluation with invalid data."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        response = client.post('/api/support/evaluate', 
                             headers=headers,
                             json={'invalid': 'data'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Message is required'

class TestFeedbackEndpoints:
    """Test feedback endpoints."""
    
    def test_submit_feedback_success(self, client, api_user_token, test_data_factory):
        """Test successful feedback submission."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('integrations.ai_gatekeeper_routes.process_outcome_feedback') as mock_process:
            mock_process.return_value = {
                'feedback_id': 'feedback-123',
                'confidence_updates': {'solution_success_rate': 0.92},
                'learning_impact': 'high',
                'metrics_updated': True
            }
            
            response = client.post('/api/support/feedback',
                                 headers=headers,
                                 json=test_data_factory.create_feedback_data())
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'feedback_processed'
            assert data['feedback_id'] == 'feedback-123'
            assert data['learning_impact'] == 'high'
            assert 'confidence_updates' in data
    
    def test_submit_feedback_invalid_rating(self, client, api_user_token):
        """Test feedback submission with invalid rating."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        response = client.post('/api/support/feedback',
                             headers=headers,
                             json={
                                 'request_id': 'test-123',
                                 'rating': 6,  # Invalid rating
                                 'outcome': 'resolved'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'Rating must be an integer between 1 and 5' in data['error']
    
    def test_submit_feedback_missing_request_id(self, client, api_user_token):
        """Test feedback submission without request ID."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        response = client.post('/api/support/feedback',
                             headers=headers,
                             json={
                                 'rating': 4,
                                 'outcome': 'resolved'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'Request ID is required'

class TestHandoffEndpoints:
    """Test handoff endpoints."""
    
    def test_handoff_to_human_success(self, client, api_user_token, test_data_factory):
        """Test successful handoff to human."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('integrations.ai_gatekeeper_routes.process_human_handoff') as mock_handoff:
            mock_handoff.return_value = {
                'handoff_id': 'handoff-123',
                'assigned_to': 'Support Team',
                'estimated_response_time': '2 hours',
                'context_summary': {'ticket_summary': {'id': 'test-ticket'}},
                'handoff_timestamp': '2024-01-01T12:00:00Z',
                'escalation_type': 'technical',
                'priority': 'high'
            }
            
            response = client.post('/api/support/handoff',
                                 headers=headers,
                                 json=test_data_factory.create_handoff_data())
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'handoff_successful'
            assert data['handoff_id'] == 'handoff-123'
            assert data['assigned_to'] == 'Support Team'
            assert data['escalation_type'] == 'technical'
            assert data['priority'] == 'high'
    
    def test_handoff_invalid_priority(self, client, api_user_token):
        """Test handoff with invalid priority."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        response = client.post('/api/support/handoff',
                             headers=headers,
                             json={
                                 'ticket_id': 'test-ticket-123',
                                 'handoff_reason': 'Complex issue',
                                 'priority': 'invalid_priority'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'priority must be one of' in data['error']
    
    def test_handoff_missing_ticket_id(self, client, api_user_token):
        """Test handoff without ticket ID."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        response = client.post('/api/support/handoff',
                             headers=headers,
                             json={
                                 'handoff_reason': 'Complex issue',
                                 'priority': 'high'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['error'] == 'ticket_id is required'
    
    def test_get_handoff_status_success(self, client, api_user_token):
        """Test getting handoff status."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('integrations.ai_gatekeeper_routes.get_ticket_handoff_status') as mock_status:
            mock_status.return_value = {
                'ticket_id': 'test-ticket-123',
                'status': 'escalated',
                'escalated_at': '2024-01-01T12:00:00Z',
                'escalation_reason': 'Complex technical issue',
                'human_assignee': 'john.doe@example.com',
                'priority': 'high'
            }
            
            response = client.get('/api/support/handoff/test-ticket-123/status',
                                headers=headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['ticket_id'] == 'test-ticket-123'
            assert data['status'] == 'escalated'
            assert data['human_assignee'] == 'john.doe@example.com'
    
    def test_get_handoff_status_not_found(self, client, api_user_token):
        """Test getting handoff status for non-existent ticket."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('integrations.ai_gatekeeper_routes.get_ticket_handoff_status') as mock_status:
            mock_status.return_value = None
            
            response = client.get('/api/support/handoff/nonexistent/status',
                                headers=headers)
            
            assert response.status_code == 404
            data = response.get_json()
            assert data['error'] == 'Ticket not found or not handed off'

class TestMonitoringEndpoints:
    """Test monitoring endpoints."""
    
    def test_monitoring_health(self, client, api_user_token):
        """Test monitoring health endpoint."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        response = client.get('/api/monitoring/health', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'health' in data
        assert 'performance' in data
    
    def test_monitoring_metrics(self, client, api_user_token):
        """Test monitoring metrics endpoint."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        response = client.get('/api/monitoring/metrics', headers=headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'metrics' in data
        assert 'timestamp' in data
    
    def test_feedback_analytics(self, client, api_user_token):
        """Test feedback analytics endpoint."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('monitoring.metrics_system.metrics_collector') as mock_metrics:
            mock_metrics.get_metrics.return_value = {
                'points': [
                    {'value': 1, 'labels': {'outcome': 'resolved'}},
                    {'value': 1, 'labels': {'outcome': 'not_resolved'}}
                ]
            }
            
            response = client.get('/api/monitoring/feedback-analytics', headers=headers)
            
            assert response.status_code == 200
            data = response.get_json()
            assert 'feedback_analytics' in data
            assert 'total_feedback' in data['feedback_analytics']
            assert 'outcomes' in data['feedback_analytics']

class TestErrorHandling:
    """Test error handling across endpoints."""
    
    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['error'] == 'Endpoint not found'
        assert 'available_endpoints' in data
    
    def test_500_error_simulation(self, client, api_user_token):
        """Test 500 error handling."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        with patch('integrations.ai_gatekeeper_routes.support_processor') as mock_processor:
            mock_processor.process_support_request.side_effect = Exception("Database error")
            
            response = client.post('/api/support/evaluate',
                                 headers=headers,
                                 json={'message': 'Test request', 'context': {}})
            
            assert response.status_code == 500
            data = response.get_json()
            assert data['error'] == 'Internal server error'
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options('/api/support/evaluate')
        
        # CORS headers should be present
        assert 'Access-Control-Allow-Origin' in response.headers

class TestSlackIntegration:
    """Test Slack integration endpoints."""
    
    def test_slack_events_url_verification(self, client):
        """Test Slack URL verification challenge."""
        response = client.post('/slack/events', json={
            'type': 'url_verification',
            'challenge': 'test-challenge-123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['challenge'] == 'test-challenge-123'
    
    def test_slack_events_invalid_signature(self, client):
        """Test Slack events with invalid signature."""
        response = client.post('/slack/events', 
                             json={'type': 'event_callback'},
                             headers={
                                 'X-Slack-Request-Timestamp': str(int(time.time())),
                                 'X-Slack-Signature': 'invalid-signature'
                             })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['error'] == 'Invalid signature'

class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def test_admin_access_to_all_endpoints(self, client, admin_token):
        """Test admin can access all endpoints."""
        headers = {'Authorization': f'Bearer {admin_token}'}
        
        # Test access to monitoring endpoints (admin-only)
        response = client.get('/api/monitoring/health', headers=headers)
        assert response.status_code == 200
        
        # Test access to support endpoints
        response = client.get('/api/support/active-requests', headers=headers)
        assert response.status_code == 200
    
    def test_api_user_limited_access(self, client, api_user_token):
        """Test API user has limited access."""
        headers = {'Authorization': f'Bearer {api_user_token}'}
        
        # Should have access to basic support endpoints
        response = client.get('/api/support/active-requests', headers=headers)
        assert response.status_code == 200
        
        # Should have read access to monitoring
        response = client.get('/api/monitoring/health', headers=headers)
        assert response.status_code == 200