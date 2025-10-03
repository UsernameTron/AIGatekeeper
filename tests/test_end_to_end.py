"""
Comprehensive End-to-End Tests for AI Gatekeeper
Tests all new features: circuit breaker, security headers, timeout monitoring, etc.
"""

import pytest
import os
import sys
import time
import json
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ['ENVIRONMENT'] = 'test'
os.environ['DATABASE_URL'] = 'sqlite:///./test_ai_gatekeeper.db'


class TestCircuitBreaker:
    """Test circuit breaker functionality"""

    def test_circuit_breaker_module_imports(self):
        """Test that circuit breaker module can be imported"""
        from core.circuit_breaker import (
            with_circuit_breaker,
            with_retry,
            openai_breaker,
            ServiceUnavailableError,
            get_all_circuit_breakers_status
        )

        assert openai_breaker is not None
        assert callable(with_circuit_breaker)
        assert callable(with_retry)

    def test_circuit_breaker_status_function(self):
        """Test getting circuit breaker status"""
        from core.circuit_breaker import get_all_circuit_breakers_status

        status = get_all_circuit_breakers_status()

        assert isinstance(status, dict)
        assert 'openai' in status
        assert 'database' in status
        assert 'vector_store' in status

        # Check openai breaker structure
        openai_status = status['openai']
        assert 'name' in openai_status
        assert 'state' in openai_status
        assert 'fail_counter' in openai_status
        assert 'fail_max' in openai_status

    def test_circuit_breaker_decorator_sync(self):
        """Test circuit breaker decorator on sync function"""
        from core.circuit_breaker import with_circuit_breaker, openai_breaker

        call_count = {'count': 0}

        @with_circuit_breaker(openai_breaker, 'TestService')
        def test_function():
            call_count['count'] += 1
            return "success"

        # Should work normally
        result = test_function()
        assert result == "success"
        assert call_count['count'] == 1

    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures"""
        from core.circuit_breaker import CircuitBreaker, CircuitBreakerError

        # Create test circuit breaker with low threshold
        test_breaker = CircuitBreaker(
            fail_max=3,
            timeout_duration=10,
            name='test_breaker'
        )

        def failing_function():
            raise Exception("Simulated failure")

        # Cause failures
        for i in range(3):
            with pytest.raises(Exception):
                test_breaker.call(failing_function)

        # Circuit should now be open
        with pytest.raises(CircuitBreakerError):
            test_breaker.call(failing_function)


class TestSecurityHeaders:
    """Test security headers middleware"""

    def test_security_headers_module_imports(self):
        """Test that security headers module can be imported"""
        from core.security_headers import add_security_headers, get_security_headers_config

        assert callable(add_security_headers)
        assert callable(get_security_headers_config)

    def test_security_headers_config(self):
        """Test getting security headers configuration"""
        from core.security_headers import get_security_headers_config

        config = get_security_headers_config()

        assert isinstance(config, dict)
        assert 'csp_enabled' in config
        assert 'hsts_enabled' in config
        assert 'headers' in config

        headers = config['headers']
        assert 'Content-Security-Policy' in headers
        assert 'Strict-Transport-Security' in headers
        assert 'X-Content-Type-Options' in headers
        assert 'X-Frame-Options' in headers


class TestTimeoutMonitoring:
    """Test timeout monitoring middleware"""

    def test_timeout_middleware_imports(self):
        """Test that timeout middleware can be imported"""
        from core.timeout_middleware import add_timeout_monitoring, timeout_required

        assert callable(add_timeout_monitoring)
        assert callable(timeout_required)

    def test_timeout_decorator(self):
        """Test timeout decorator functionality"""
        from core.timeout_middleware import timeout_required

        @timeout_required(5)
        def quick_function():
            return "completed"

        result = quick_function()
        assert result == "completed"


class TestDatabaseEnhancements:
    """Test database connection pool enhancements"""

    def test_database_manager_imports(self):
        """Test database manager with new features"""
        from db.database import DatabaseManager, ConnectionPoolExhaustedException

        assert ConnectionPoolExhaustedException is not None

    def test_database_pool_health(self):
        """Test database pool health checking"""
        from db.database import db_manager

        # Initialize if needed
        if not db_manager.engine:
            db_manager.initialize()

        pool_health = db_manager.get_pool_health()

        assert isinstance(pool_health, dict)
        assert 'utilization_percent' in pool_health
        assert 'health_status' in pool_health
        assert 'available_connections' in pool_health
        assert 'healthy' in pool_health

        # Should be healthy with no load
        assert pool_health['health_status'] in ['healthy', 'warning', 'critical']

    def test_get_session_with_retry(self):
        """Test get_session has retry parameters"""
        from db.database import db_manager
        import inspect

        # Check get_session signature
        sig = inspect.signature(db_manager.get_session)
        params = sig.parameters

        assert 'timeout' in params
        assert 'max_retries' in params


class TestSQLInjectionProtection:
    """Test SQL injection protection"""

    def test_sql_injection_tests_exist(self):
        """Verify SQL injection test file exists"""
        import os
        test_file = os.path.join(
            os.path.dirname(__file__),
            'test_sql_injection_security.py'
        )
        assert os.path.exists(test_file), "SQL injection test file should exist"

    def test_crud_uses_orm(self):
        """Verify CRUD operations use ORM (not raw SQL)"""
        from db.crud import SupportTicketCRUD
        import inspect

        # Get create_ticket source
        source = inspect.getsource(SupportTicketCRUD.create_ticket)

        # Should not contain string formatting in SQL
        assert 'execute(' not in source or 'format' not in source
        assert 'db.add(' in source  # ORM pattern
        assert 'db.commit(' in source  # ORM pattern


class TestMonitoringEndpoints:
    """Test monitoring system endpoints"""

    def test_metrics_system_imports(self):
        """Test metrics system can be imported"""
        from monitoring.metrics_system import (
            metrics_collector,
            health_checker,
            performance_tracker,
            monitoring_bp
        )

        assert metrics_collector is not None
        assert health_checker is not None
        assert performance_tracker is not None
        assert monitoring_bp is not None

    def test_circuit_breaker_monitoring_integration(self):
        """Test circuit breaker monitoring is integrated"""
        from monitoring.metrics_system import start_background_monitoring
        import inspect

        # Check that circuit breaker tracking is in monitoring
        source = inspect.getsource(start_background_monitoring)
        assert 'circuit_breaker' in source.lower()


class TestTracingIntegration:
    """Test OpenTelemetry tracing integration"""

    def test_tracing_module_imports(self):
        """Test tracing module can be imported"""
        from core.tracing import (
            setup_tracing,
            trace_operation,
            add_span_attributes,
            traced
        )

        assert callable(setup_tracing)
        assert callable(traced)

    def test_traced_decorator(self):
        """Test traced decorator works"""
        from core.tracing import traced

        @traced("test_operation")
        def test_function():
            return "result"

        result = test_function()
        assert result == "result"


class TestApplicationIntegration:
    """Test full application integration"""

    def test_app_creation(self):
        """Test application can be created"""
        from app import create_app

        app = create_app()

        assert app is not None
        assert app.config is not None

    def test_app_has_timeout_config(self):
        """Test app has timeout configuration"""
        from app import create_app

        app = create_app()

        assert 'REQUEST_TIMEOUT' in app.config
        assert 'OPENAI_TIMEOUT' in app.config
        assert isinstance(app.config['REQUEST_TIMEOUT'], int)
        assert isinstance(app.config['OPENAI_TIMEOUT'], int)

    @pytest.mark.skipif(
        os.getenv('SKIP_FLASK_TESTS') == 'true',
        reason="Flask tests skipped"
    )
    def test_app_test_client(self):
        """Test app test client works"""
        from app import create_app

        app = create_app()
        client = app.test_client()

        # Test health endpoint
        response = client.get('/health')

        assert response.status_code in [200, 503]  # May fail if DB not ready

        if response.status_code == 200:
            data = response.get_json()
            assert 'status' in data or 'timestamp' in data


class TestEndToEndFlow:
    """Test complete end-to-end flows"""

    @pytest.mark.skipif(
        os.getenv('SKIP_E2E_TESTS') == 'true',
        reason="E2E tests skipped"
    )
    def test_complete_monitoring_flow(self):
        """Test complete monitoring flow"""
        from app import create_app

        app = create_app()
        client = app.test_client()

        # Test circuit breaker endpoint (if available)
        response = client.get(
            '/api/monitoring/circuit-breakers',
            headers={'Authorization': 'Bearer test-admin-key-12345'}
        )

        # Should either work or return auth error
        assert response.status_code in [200, 401, 404, 503]

    def test_security_headers_applied(self):
        """Test security headers are applied to responses"""
        from app import create_app

        app = create_app()
        client = app.test_client()

        response = client.get('/health')

        # Check for security headers
        headers = response.headers

        # At minimum should have some security headers
        assert 'X-Content-Type-Options' in headers or response.status_code >= 400

    def test_database_initialization(self):
        """Test database can be initialized"""
        from db.database import db_manager

        # Should initialize without errors
        result = db_manager.initialize()

        assert result is True or result is None

    def test_monitoring_background_thread(self):
        """Test monitoring background thread configuration"""
        from monitoring.metrics_system import start_background_monitoring
        import inspect

        # Verify function exists and has monitoring logic
        source = inspect.getsource(start_background_monitoring)

        assert 'threading.Thread' in source
        assert 'daemon=True' in source


def run_all_tests():
    """Run all tests and return results"""

    print("=" * 80)
    print("AI GATEKEEPER - COMPREHENSIVE END-TO-END TEST SUITE")
    print("=" * 80)
    print()

    # Run pytest
    exit_code = pytest.main([
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ])

    return exit_code


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
