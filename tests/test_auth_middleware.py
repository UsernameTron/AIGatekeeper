"""
Unit tests for authentication middleware
"""

import pytest
import time
import jwt
from unittest.mock import patch, Mock
from flask import Flask, g

from auth.middleware import (
    JWTManager, BearerTokenManager, authenticate_request, authorize_request,
    auth_required, optional_auth, require_role, AuthenticationError, AuthorizationError
)

class TestJWTManager:
    """Test JWT Manager functionality."""
    
    def test_jwt_manager_initialization(self):
        """Test JWT manager initialization."""
        jwt_manager = JWTManager(secret_key='test-secret', token_expiry_hours=12)
        
        assert jwt_manager.secret_key == 'test-secret'
        assert jwt_manager.algorithm == 'HS256'
        assert jwt_manager.token_expiry_hours == 12
        assert 'admin' in jwt_manager.roles
        assert 'manage' in jwt_manager.roles['admin']
    
    def test_generate_token(self, jwt_manager):
        """Test JWT token generation."""
        token = jwt_manager.generate_token(
            user_id='test-user',
            email='test@example.com',
            role='admin'
        )
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify
        payload = jwt.decode(token, jwt_manager.secret_key, algorithms=['HS256'])
        assert payload['user_id'] == 'test-user'
        assert payload['email'] == 'test@example.com'
        assert payload['role'] == 'admin'
        assert payload['iss'] == 'ai-gatekeeper'
        assert 'permissions' in payload
        assert 'iat' in payload
        assert 'exp' in payload
    
    def test_decode_valid_token(self, jwt_manager):
        """Test decoding valid JWT token."""
        token = jwt_manager.generate_token(
            user_id='test-user',
            email='test@example.com',
            role='api_user'
        )
        
        payload = jwt_manager.decode_token(token)
        
        assert payload['user_id'] == 'test-user'
        assert payload['email'] == 'test@example.com'
        assert payload['role'] == 'api_user'
        assert payload['permissions'] == ['read', 'write']
    
    def test_decode_expired_token(self, jwt_manager):
        """Test decoding expired JWT token."""
        # Create token with past expiry
        expired_payload = {
            'user_id': 'test-user',
            'email': 'test@example.com',
            'role': 'api_user',
            'exp': time.time() - 3600,  # Expired 1 hour ago
            'iat': time.time() - 7200,  # Issued 2 hours ago
            'iss': 'ai-gatekeeper'
        }
        
        expired_token = jwt.encode(expired_payload, jwt_manager.secret_key, algorithm='HS256')
        
        with pytest.raises(AuthenticationError, match="Token has expired"):
            jwt_manager.decode_token(expired_token)
    
    def test_decode_invalid_token(self, jwt_manager):
        """Test decoding invalid JWT token."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(AuthenticationError, match="Invalid token"):
            jwt_manager.decode_token(invalid_token)
    
    def test_validate_permissions(self, jwt_manager):
        """Test permission validation."""
        # Admin permissions
        admin_perms = ['read', 'write', 'delete', 'manage']
        assert jwt_manager.validate_permissions(admin_perms, ['read']) is True
        assert jwt_manager.validate_permissions(admin_perms, ['write']) is True
        assert jwt_manager.validate_permissions(admin_perms, ['delete']) is True
        assert jwt_manager.validate_permissions(admin_perms, ['manage']) is True
        
        # API user permissions
        api_perms = ['read', 'write']
        assert jwt_manager.validate_permissions(api_perms, ['read']) is True
        assert jwt_manager.validate_permissions(api_perms, ['write']) is True
        assert jwt_manager.validate_permissions(api_perms, ['delete']) is False
        assert jwt_manager.validate_permissions(api_perms, ['manage']) is False
        
        # Viewer permissions
        viewer_perms = ['read']
        assert jwt_manager.validate_permissions(viewer_perms, ['read']) is True
        assert jwt_manager.validate_permissions(viewer_perms, ['write']) is False
    
    def test_get_endpoint_permissions(self, jwt_manager):
        """Test getting endpoint permissions."""
        # Exact match
        perms = jwt_manager.get_endpoint_permissions('POST', '/api/support/evaluate')
        assert perms == ['write']
        
        # Wildcard match
        perms = jwt_manager.get_endpoint_permissions('GET', '/api/support/status/123')
        assert perms == ['read']
        
        # Default API permissions
        perms = jwt_manager.get_endpoint_permissions('GET', '/api/custom/endpoint')
        assert perms == ['read']
        
        perms = jwt_manager.get_endpoint_permissions('POST', '/api/custom/endpoint')
        assert perms == ['write']
        
        perms = jwt_manager.get_endpoint_permissions('DELETE', '/api/custom/endpoint')
        assert perms == ['delete']
        
        # Non-API endpoints
        perms = jwt_manager.get_endpoint_permissions('GET', '/health')
        assert perms == []

class TestBearerTokenManager:
    """Test Bearer Token Manager functionality."""
    
    def test_bearer_token_manager_initialization(self):
        """Test bearer token manager initialization."""
        with patch.dict('os.environ', {
            'API_KEY_TEST': 'test-key-123:admin',
            'API_KEY_USER': 'user-key-456:api_user'
        }):
            manager = BearerTokenManager()
            
            assert 'test-key-123' in manager.api_keys
            assert 'user-key-456' in manager.api_keys
            assert manager.api_keys['test-key-123']['role'] == 'admin'
            assert manager.api_keys['user-key-456']['role'] == 'api_user'
    
    def test_validate_token_success(self):
        """Test successful token validation."""
        with patch.dict('os.environ', {
            'API_KEY_TEST': 'valid-key:admin'
        }):
            manager = BearerTokenManager()
            
            token_info = manager.validate_token('valid-key')
            
            assert token_info is not None
            assert token_info['role'] == 'admin'
            assert token_info['name'] == 'TEST'
            assert 'manage' in token_info['permissions']
    
    def test_validate_token_invalid(self):
        """Test invalid token validation."""
        with patch.dict('os.environ', {
            'API_KEY_TEST': 'valid-key:admin'
        }):
            manager = BearerTokenManager()
            
            token_info = manager.validate_token('invalid-key')
            
            assert token_info is None

class TestAuthenticationDecorators:
    """Test authentication decorators."""
    
    def test_auth_required_decorator_success(self):
        """Test auth_required decorator with valid token."""
        app = Flask(__name__)
        
        @app.route('/protected')
        @auth_required
        def protected_route():
            return {'message': 'success', 'user': g.user['email']}
        
        with app.test_client() as client:
            with patch('auth.middleware.authenticate_request') as mock_auth:
                with patch('auth.middleware.authorize_request') as mock_authz:
                    mock_auth.return_value = {
                        'user_id': 'test-user',
                        'email': 'test@example.com',
                        'role': 'admin',
                        'permissions': ['read', 'write', 'manage']
                    }
                    mock_authz.return_value = True
                    
                    response = client.get('/protected')
                    
                    assert response.status_code == 200
                    data = response.get_json()
                    assert data['message'] == 'success'
                    assert data['user'] == 'test@example.com'
    
    def test_auth_required_decorator_auth_failure(self):
        """Test auth_required decorator with authentication failure."""
        app = Flask(__name__)
        
        @app.route('/protected')
        @auth_required
        def protected_route():
            return {'message': 'success'}
        
        with app.test_client() as client:
            with patch('auth.middleware.authenticate_request') as mock_auth:
                mock_auth.side_effect = AuthenticationError("Invalid token")
                
                response = client.get('/protected')
                
                assert response.status_code == 401
                data = response.get_json()
                assert data['error'] == 'Authentication failed'
                assert data['message'] == 'Invalid token'
    
    def test_auth_required_decorator_authz_failure(self):
        """Test auth_required decorator with authorization failure."""
        app = Flask(__name__)
        
        @app.route('/protected')
        @auth_required
        def protected_route():
            return {'message': 'success'}
        
        with app.test_client() as client:
            with patch('auth.middleware.authenticate_request') as mock_auth:
                with patch('auth.middleware.authorize_request') as mock_authz:
                    mock_auth.return_value = {
                        'user_id': 'test-user',
                        'email': 'test@example.com',
                        'role': 'viewer',
                        'permissions': ['read']
                    }
                    mock_authz.side_effect = AuthorizationError("Insufficient permissions")
                    
                    response = client.get('/protected')
                    
                    assert response.status_code == 403
                    data = response.get_json()
                    assert data['error'] == 'Authorization failed'
                    assert data['message'] == 'Insufficient permissions'
    
    def test_optional_auth_decorator_with_auth(self):
        """Test optional_auth decorator with valid authentication."""
        app = Flask(__name__)
        
        @app.route('/public')
        @optional_auth
        def public_route():
            if g.user:
                return {'message': f'Hello {g.user["email"]}'}
            else:
                return {'message': 'Hello anonymous'}
        
        with app.test_client() as client:
            with patch('auth.middleware.authenticate_request') as mock_auth:
                mock_auth.return_value = {
                    'user_id': 'test-user',
                    'email': 'test@example.com',
                    'role': 'api_user',
                    'permissions': ['read', 'write']
                }
                
                response = client.get('/public')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['message'] == 'Hello test@example.com'
    
    def test_optional_auth_decorator_without_auth(self):
        """Test optional_auth decorator without authentication."""
        app = Flask(__name__)
        
        @app.route('/public')
        @optional_auth
        def public_route():
            if g.user:
                return {'message': f'Hello {g.user["email"]}'}
            else:
                return {'message': 'Hello anonymous'}
        
        with app.test_client() as client:
            with patch('auth.middleware.authenticate_request') as mock_auth:
                mock_auth.side_effect = AuthenticationError("No token")
                
                response = client.get('/public')
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['message'] == 'Hello anonymous'
    
    def test_require_role_decorator_success(self):
        """Test require_role decorator with correct role."""
        app = Flask(__name__)
        
        @app.route('/admin')
        @auth_required
        @require_role(['admin'])
        def admin_route():
            return {'message': 'Admin access granted'}
        
        with app.test_client() as client:
            with patch('auth.middleware.authenticate_request') as mock_auth:
                with patch('auth.middleware.authorize_request') as mock_authz:
                    mock_auth.return_value = {
                        'user_id': 'admin-user',
                        'email': 'admin@example.com',
                        'role': 'admin',
                        'permissions': ['read', 'write', 'manage']
                    }
                    mock_authz.return_value = True
                    
                    with app.test_request_context('/admin'):
                        # Set up g.user as auth_required would
                        g.user = mock_auth.return_value
                        
                        response = client.get('/admin')
                        
                        assert response.status_code == 200
                        data = response.get_json()
                        assert data['message'] == 'Admin access granted'
    
    def test_require_role_decorator_failure(self):
        """Test require_role decorator with incorrect role."""
        app = Flask(__name__)
        
        @app.route('/admin')
        @auth_required
        @require_role(['admin'])
        def admin_route():
            return {'message': 'Admin access granted'}
        
        with app.test_client() as client:
            with patch('auth.middleware.authenticate_request') as mock_auth:
                with patch('auth.middleware.authorize_request') as mock_authz:
                    mock_auth.return_value = {
                        'user_id': 'regular-user',
                        'email': 'user@example.com',
                        'role': 'api_user',
                        'permissions': ['read', 'write']
                    }
                    mock_authz.return_value = True
                    
                    with app.test_request_context('/admin'):
                        # Set up g.user as auth_required would
                        g.user = mock_auth.return_value
                        
                        response = client.get('/admin')
                        
                        assert response.status_code == 403
                        data = response.get_json()
                        assert data['error'] == 'Insufficient role'

class TestAuthenticationFunctions:
    """Test authentication helper functions."""
    
    def test_authenticate_request_jwt_success(self):
        """Test successful JWT authentication."""
        mock_request = Mock()
        mock_request.headers = {'Authorization': 'Bearer valid-jwt-token'}
        
        with patch('auth.middleware.request', mock_request):
            with patch('auth.middleware.jwt_manager.decode_token') as mock_decode:
                mock_decode.return_value = {
                    'user_id': 'test-user',
                    'email': 'test@example.com',
                    'role': 'admin',
                    'permissions': ['read', 'write', 'manage']
                }
                
                user_info = authenticate_request()
                
                assert user_info['user_id'] == 'test-user'
                assert user_info['email'] == 'test@example.com'
                assert user_info['role'] == 'admin'
                assert user_info['token_type'] == 'jwt'
    
    def test_authenticate_request_bearer_success(self):
        """Test successful Bearer token authentication."""
        mock_request = Mock()
        mock_request.headers = {'Authorization': 'Bearer valid-bearer-token'}
        
        with patch('auth.middleware.request', mock_request):
            with patch('auth.middleware.jwt_manager.decode_token') as mock_jwt:
                with patch('auth.middleware.bearer_token_manager.validate_token') as mock_bearer:
                    mock_jwt.side_effect = AuthenticationError("Invalid JWT")
                    mock_bearer.return_value = {
                        'name': 'API_USER',
                        'role': 'api_user',
                        'permissions': ['read', 'write']
                    }
                    
                    user_info = authenticate_request()
                    
                    assert user_info['user_id'] == 'API_USER'
                    assert user_info['role'] == 'api_user'
                    assert user_info['token_type'] == 'bearer'
    
    def test_authenticate_request_no_token(self):
        """Test authentication without token."""
        mock_request = Mock()
        mock_request.headers = {}
        
        with patch('auth.middleware.request', mock_request):
            with pytest.raises(AuthenticationError, match="No authentication token provided"):
                authenticate_request()
    
    def test_authenticate_request_invalid_token(self):
        """Test authentication with invalid token."""
        mock_request = Mock()
        mock_request.headers = {'Authorization': 'Bearer invalid-token'}
        
        with patch('auth.middleware.request', mock_request):
            with patch('auth.middleware.jwt_manager.decode_token') as mock_jwt:
                with patch('auth.middleware.bearer_token_manager.validate_token') as mock_bearer:
                    mock_jwt.side_effect = AuthenticationError("Invalid JWT")
                    mock_bearer.return_value = None
                    
                    with pytest.raises(AuthenticationError, match="Invalid authentication token"):
                        authenticate_request()
    
    def test_authorize_request_success(self):
        """Test successful authorization."""
        user_info = {
            'permissions': ['read', 'write'],
            'role': 'api_user'
        }
        
        with patch('auth.middleware.jwt_manager.get_endpoint_permissions') as mock_perms:
            with patch('auth.middleware.jwt_manager.validate_permissions') as mock_validate:
                mock_perms.return_value = ['write']
                mock_validate.return_value = True
                
                result = authorize_request(user_info, 'POST', '/api/support/evaluate')
                
                assert result is True
    
    def test_authorize_request_failure(self):
        """Test authorization failure."""
        user_info = {
            'permissions': ['read'],
            'role': 'viewer'
        }
        
        with patch('auth.middleware.jwt_manager.get_endpoint_permissions') as mock_perms:
            with patch('auth.middleware.jwt_manager.validate_permissions') as mock_validate:
                mock_perms.return_value = ['write']
                mock_validate.return_value = False
                
                with pytest.raises(AuthorizationError, match="Insufficient permissions"):
                    authorize_request(user_info, 'POST', '/api/support/evaluate')
    
    def test_authorize_request_no_permissions_required(self):
        """Test authorization when no permissions required."""
        user_info = {
            'permissions': ['read'],
            'role': 'viewer'
        }
        
        with patch('auth.middleware.jwt_manager.get_endpoint_permissions') as mock_perms:
            mock_perms.return_value = []
            
            result = authorize_request(user_info, 'GET', '/health')
            
            assert result is True