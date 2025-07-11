#!/usr/bin/env python3
"""
Simple test to verify basic functionality
"""

def test_basic_import():
    """Test that basic imports work"""
    import sys
    import os
    
    # Add project path
    sys.path.insert(0, os.path.dirname(__file__))
    
    # Test imports
    from core.confidence_agent import ConfidenceAgent
    from core.support_request_processor import SupportRequestProcessor
    
    assert ConfidenceAgent is not None
    assert SupportRequestProcessor is not None
    print("✅ Basic imports successful")

if __name__ == "__main__":
    test_basic_import()