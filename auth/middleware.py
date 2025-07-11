"""
Authentication middleware for AI Gatekeeper Flask routes
Provides JWT and Bearer token authentication with role-based access control
"""

import os
import jwt
import time
import logging
from functools import wraps
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from flask import request, jsonify, current_app, g

class AuthenticationError(Exception):
    """Custom exception for authentication errors."""
    pass

class AuthorizationError(Exception):
    """Custom exception for authorization errors."""
    pass

class JWTManager:
    """JWT token manager for AI Gatekeeper authentication."""
    
    def __init__(self, secret_key: str = None, algorithm: str = 'HS256', 
                 token_expiry_hours: int = 24):
        """
        Initialize JWT manager.
        
        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default: HS256)
            token_expiry_hours: Token expiry in hours (default: 24)
        """
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'ai-gatekeeper-secret')
        self.algorithm = algorithm
        self.token_expiry_hours = token_expiry_hours
        
        # Configure roles and permissions
        self.roles = {
            'admin': ['read', 'write', 'delete', 'manage'],
            'operator': ['read', 'write'],
            'viewer': ['read'],
            'api_user': ['read', 'write']
        }
        
        # Protected endpoints and their required permissions
        self.endpoint_permissions = {
            'POST:/api/support/evaluate': ['write'],
            'POST:/api/support/generate-solution': ['write'],
            'POST:/api/support/feedback': ['write'],
            'POST:/api/support/handoff': ['write'],
            'GET:/api/support/status/*': ['read'],
            'GET:/api/support/handoff/*/status': ['read'],
            'GET:/api/support/active-requests': ['read'],
            'DELETE:/api/support/*': ['delete'],
            'GET:/api/monitoring/*': ['read'],
            'POST:/api/monitoring/*': ['manage'],
            'PUT:/api/monitoring/*': ['manage'],
            'DELETE:/api/monitoring/*': ['manage']
        }
    
    def generate_token(self, user_id: str, email: str, role: str = 'api_user', 
                      custom_claims: Dict[str, Any] = None) -> str:
        """
        Generate JWT token for user.
        
        Args:
            user_id: User ID
            email: User email
            role: User role (default: api_user)
            custom_claims: Additional claims to include
            
        Returns:
            JWT token string
        """
        now = datetime.utcnow()
        expiry = now + timedelta(hours=self.token_expiry_hours)
        
        payload = {
            'user_id': user_id,
            'email': email,
            'role': role,
            'permissions': self.roles.get(role, []),
            'iat': now.timestamp(),
            'exp': expiry.timestamp(),
            'iss': 'ai-gatekeeper'
        }
        
        # Add custom claims
        if custom_claims:
            payload.update(custom_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token.
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload dictionary
            
        Raises:
            AuthenticationError: If token is invalid
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired
            if payload.get('exp', 0) < time.time():
                raise AuthenticationError("Token has expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def validate_permissions(self, user_permissions: List[str], required_permissions: List[str]) -> bool:
        """
        Validate user permissions against required permissions.
        
        Args:
            user_permissions: User's permissions
            required_permissions: Required permissions
            
        Returns:
            True if user has required permissions
        """
        # Admin role has all permissions
        if 'manage' in user_permissions:
            return True
        
        # Check if user has any of the required permissions
        return any(perm in user_permissions for perm in required_permissions)
    
    def get_endpoint_permissions(self, method: str, path: str) -> List[str]:
        """
        Get required permissions for endpoint.
        
        Args:
            method: HTTP method
            path: Request path
            
        Returns:
            List of required permissions
        """
        # Exact match
        endpoint_key = f"{method}:{path}"
        if endpoint_key in self.endpoint_permissions:
            return self.endpoint_permissions[endpoint_key]
        
        # Wildcard match
        for pattern, permissions in self.endpoint_permissions.items():
            if pattern.endswith('*'):
                pattern_base = pattern[:-1]  # Remove '*'
                if endpoint_key.startswith(pattern_base):
                    return permissions
        
        # Default permissions for API endpoints
        if path.startswith('/api/'):
            if method in ['GET', 'HEAD']:
                return ['read']
            elif method in ['POST', 'PUT', 'PATCH']:
                return ['write']
            elif method == 'DELETE':
                return ['delete']
        
        return []  # No permissions required for non-API endpoints

class BearerTokenManager:
    """Bearer token manager for simple API key authentication."""
    
    def __init__(self):
        """Initialize bearer token manager."""
        self.api_keys = self._load_api_keys()
    
    def _load_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """Load API keys from environment or configuration."""
        api_keys = {}
        
        # Load from environment variables
        # Format: API_KEY_<NAME>=<key>:<role>
        for key, value in os.environ.items():
            if key.startswith('API_KEY_'):
                name = key[8:]  # Remove 'API_KEY_' prefix
                if ':' in value:
                    api_key, role = value.split(':', 1)
                    api_keys[api_key] = {
                        'name': name,
                        'role': role,
                        'permissions': JWTManager().roles.get(role, [])
                    }
        
        # Default admin key if none configured
        if not api_keys:
            default_key = os.getenv('DEFAULT_API_KEY', 'ai-gatekeeper-default-key')
            api_keys[default_key] = {
                'name': 'DEFAULT_ADMIN',
                'role': 'admin',
                'permissions': ['read', 'write', 'delete', 'manage']
            }
        
        return api_keys
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate bearer token.
        
        Args:
            token: Bearer token
            
        Returns:
            Token info if valid, None otherwise
        """
        return self.api_keys.get(token)

# Global authentication managers
jwt_manager = JWTManager()
bearer_token_manager = BearerTokenManager()

def extract_token_from_request() -> Optional[str]:
    """Extract token from request headers."""
    auth_header = request.headers.get('Authorization', '')
    
    if auth_header.startswith('Bearer '):
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    return None

def authenticate_request() -> Dict[str, Any]:
    """
    Authenticate request using JWT or Bearer token.
    
    Returns:
        User info dictionary
        
    Raises:
        AuthenticationError: If authentication fails
    """
    token = extract_token_from_request()
    
    if not token:
        raise AuthenticationError("No authentication token provided")
    
    # Try JWT first
    try:
        payload = jwt_manager.decode_token(token)
        return {
            'user_id': payload.get('user_id'),
            'email': payload.get('email'),
            'role': payload.get('role'),
            'permissions': payload.get('permissions', []),
            'token_type': 'jwt'
        }
    except AuthenticationError:
        pass
    
    # Try Bearer token
    token_info = bearer_token_manager.validate_token(token)
    if token_info:
        return {
            'user_id': token_info['name'],
            'email': None,
            'role': token_info['role'],
            'permissions': token_info['permissions'],
            'token_type': 'bearer'
        }
    
    raise AuthenticationError("Invalid authentication token")

def authorize_request(user_info: Dict[str, Any], method: str, path: str) -> bool:
    """
    Authorize request based on user permissions.
    
    Args:
        user_info: User info from authentication
        method: HTTP method
        path: Request path
        
    Returns:
        True if authorized
        
    Raises:
        AuthorizationError: If authorization fails
    """
    required_permissions = jwt_manager.get_endpoint_permissions(method, path)
    
    if not required_permissions:
        return True  # No permissions required
    
    user_permissions = user_info.get('permissions', [])
    
    if not jwt_manager.validate_permissions(user_permissions, required_permissions):
        raise AuthorizationError(f"Insufficient permissions. Required: {required_permissions}")
    
    return True

def auth_required(f: Callable) -> Callable:
    """
    Decorator to require authentication for Flask routes.
    
    Usage:
        @app.route('/api/protected')
        @auth_required
        def protected_route():
            return jsonify({'user': g.user})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Authenticate request
            user_info = authenticate_request()
            
            # Authorize request
            authorize_request(user_info, request.method, request.path)
            
            # Store user info in Flask g object
            g.user = user_info
            
            return f(*args, **kwargs)
            
        except AuthenticationError as e:
            return jsonify({
                'error': 'Authentication failed',
                'message': str(e)
            }), 401
        except AuthorizationError as e:
            return jsonify({
                'error': 'Authorization failed',
                'message': str(e)
            }), 403
        except Exception as e:
            current_app.logger.error(f"Authentication error: {e}")
            return jsonify({
                'error': 'Internal authentication error'
            }), 500
    
    return decorated_function

def optional_auth(f: Callable) -> Callable:
    """
    Decorator for optional authentication.
    Sets g.user if token is valid, otherwise continues without authentication.
    
    Usage:
        @app.route('/api/public')
        @optional_auth
        def public_route():
            if g.user:
                return jsonify({'message': f'Hello {g.user["email"]}'})
            else:
                return jsonify({'message': 'Hello anonymous'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Try to authenticate
            user_info = authenticate_request()
            g.user = user_info
        except (AuthenticationError, AuthorizationError):
            # Continue without authentication
            g.user = None
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_role(roles: List[str]) -> Callable:
    """
    Decorator to require specific roles.
    
    Args:
        roles: List of allowed roles
        
    Usage:
        @app.route('/api/admin')
        @auth_required
        @require_role(['admin'])
        def admin_route():
            return jsonify({'message': 'Admin access'})
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'user') or not g.user:
                return jsonify({
                    'error': 'Authentication required'
                }), 401
            
            user_role = g.user.get('role')
            if user_role not in roles:
                return jsonify({
                    'error': 'Insufficient role',
                    'message': f'Required roles: {roles}, user role: {user_role}'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def setup_auth_middleware(app):
    """
    Setup authentication middleware for Flask app.
    
    Args:
        app: Flask application
    """
    # Add authentication to AI Gatekeeper routes
    protected_blueprints = ['ai_gatekeeper', 'monitoring']
    
    @app.before_request
    def before_request():
        # Skip authentication for certain paths
        skip_paths = ['/health', '/slack/events', '/']
        
        if request.path in skip_paths:
            return
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return
        
        # Check if request is for a protected blueprint
        if any(request.path.startswith(f'/api/{bp}') for bp in protected_blueprints):
            try:
                # Authenticate request
                user_info = authenticate_request()
                
                # Authorize request
                authorize_request(user_info, request.method, request.path)
                
                # Store user info
                g.user = user_info
                
            except AuthenticationError as e:
                return jsonify({
                    'error': 'Authentication failed',
                    'message': str(e)
                }), 401
            except AuthorizationError as e:
                return jsonify({
                    'error': 'Authorization failed',
                    'message': str(e)
                }), 403
            except Exception as e:
                current_app.logger.error(f"Authentication error: {e}")
                return jsonify({
                    'error': 'Internal authentication error'
                }), 500
    
    # Add authentication info to responses
    @app.after_request
    def after_request(response):
        if hasattr(g, 'user') and g.user:
            response.headers['X-User-Role'] = g.user.get('role', 'unknown')
        return response
    
    logging.info("Authentication middleware configured")

def create_admin_token(user_id: str = "admin", email: str = "admin@ai-gatekeeper.com") -> str:
    """
    Create admin token for testing/setup.
    
    Args:
        user_id: Admin user ID
        email: Admin email
        
    Returns:
        JWT token string
    """
    return jwt_manager.generate_token(user_id, email, role='admin')

def create_api_user_token(user_id: str, email: str) -> str:
    """
    Create API user token.
    
    Args:
        user_id: User ID
        email: User email
        
    Returns:
        JWT token string
    """
    return jwt_manager.generate_token(user_id, email, role='api_user')

# CLI utility functions
def print_sample_tokens():
    """Print sample tokens for testing."""
    print("=== AI Gatekeeper Authentication Tokens ===")
    
    admin_token = create_admin_token()
    print(f"Admin Token: {admin_token}")
    
    api_token = create_api_user_token("api_user", "api@example.com")
    print(f"API User Token: {api_token}")
    
    print("\n=== Usage Examples ===")
    print(f"curl -H 'Authorization: Bearer {admin_token}' http://localhost:5000/api/support/evaluate")
    print(f"curl -H 'Authorization: Bearer {api_token}' http://localhost:5000/api/support/feedback")

if __name__ == "__main__":
    print_sample_tokens()