#!/usr/bin/env python3
"""
Test runner for AI Gatekeeper System
Provides comprehensive test execution with coverage reporting
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def run_tests(test_type="all", verbose=False, coverage=False, specific_test=None):
    """
    Run tests for AI Gatekeeper System.
    
    Args:
        test_type: Type of tests to run (unit, integration, all)
        verbose: Enable verbose output
        coverage: Enable coverage reporting
        specific_test: Run specific test file or pattern
    """
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=auth",
            "--cov=core", 
            "--cov=db",
            "--cov=integrations",
            "--cov=knowledge",
            "--cov=monitoring",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Determine test paths
    test_paths = []
    if test_type == "unit":
        test_paths = [
            "tests/test_database.py",
            "tests/test_auth_middleware.py",
            "tests/test_confidence_agent.py"
        ]
    elif test_type == "integration":
        test_paths = [
            "tests/test_api_integration.py",
            "tests/test_advanced_agents_integration.py"
        ]
    elif test_type == "all":
        test_paths = ["tests/"]
    
    if specific_test:
        test_paths = [specific_test]
    
    cmd.extend(test_paths)
    
    # Add test discovery options
    cmd.extend([
        "--tb=short",
        "--strict-markers",
        "--disable-warnings"
    ])
    
    print(f"Running tests: {' '.join(cmd)}")
    print("=" * 80)
    
    # Run tests
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    if coverage and result.returncode == 0:
        print("\n" + "=" * 80)
        print("Coverage report generated in htmlcov/index.html")
    
    return result.returncode

def setup_test_environment():
    """Setup test environment variables."""
    test_env = {
        'ENVIRONMENT': 'testing',
        'DATABASE_URL': 'sqlite:///:memory:',
        'OPENAI_API_KEY': 'test-key',
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'ADMIN_API_KEY': 'test-admin-key',
        'CONFIDENCE_THRESHOLD': '0.8',
        'RISK_THRESHOLD': '0.3',
        'PYTHONPATH': os.getcwd()
    }
    
    for key, value in test_env.items():
        os.environ[key] = value

def install_test_dependencies():
    """Install test dependencies if not already installed."""
    try:
        import pytest
        import pytest_cov
        import pytest_mock
    except ImportError:
        print("Installing test dependencies...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "pytest", "pytest-cov", "pytest-mock", "pytest-asyncio"
        ])

def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="AI Gatekeeper Test Runner")
    parser.add_argument(
        "--type", 
        choices=["unit", "integration", "all"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Enable coverage reporting"
    )
    parser.add_argument(
        "--test", "-t",
        help="Run specific test file or pattern"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Setup test environment and install dependencies"
    )
    
    args = parser.parse_args()
    
    if args.setup:
        print("Setting up test environment...")
        install_test_dependencies()
        setup_test_environment()
        print("✅ Test environment setup complete")
        return 0
    
    # Setup environment
    setup_test_environment()
    
    # Run tests
    exit_code = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        specific_test=args.test
    )
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())