#!/usr/bin/env python3
"""
Integration test script for confidence agent with AI Gatekeeper system
"""

import requests
import json
import time
import os

def test_confidence_integration():
    """Test confidence agent integration with the full system"""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Confidence Agent Integration")
    print("=" * 50)
    
    # Test requests with expected confidence levels
    test_cases = [
        {
            'name': 'High Confidence - Password Reset',
            'request': {
                'message': 'I forgot my password and need to reset it',
                'context': {'user_level': 'beginner'}
            },
            'expected_confidence': 0.7
        },
        {
            'name': 'Medium Confidence - Application Issue',
            'request': {
                'message': 'My application keeps crashing when I try to save files',
                'context': {'user_level': 'intermediate'}
            },
            'expected_confidence': 0.5
        },
        {
            'name': 'Low Confidence - Complex Technical',
            'request': {
                'message': 'I need help with complex API integration using OAuth2 and custom middleware',
                'context': {'user_level': 'advanced'}
            },
            'expected_confidence': 0.4
        }
    ]
    
    for test_case in test_cases:
        print(f"\n📋 {test_case['name']}")
        print("-" * 30)
        
        try:
            # Send request
            response = requests.post(
                f"{base_url}/api/support/evaluate",
                json=test_case['request'],
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                confidence = result.get('confidence', 0.0)
                action = result.get('action', 'unknown')
                
                print(f"✅ Request processed successfully")
                print(f"📊 Confidence: {confidence:.3f}")
                print(f"🎯 Action: {action}")
                print(f"📈 Expected: {test_case['expected_confidence']:.3f}")
                
                # Validate confidence is reasonable
                if confidence >= test_case['expected_confidence'] * 0.7:
                    print("✅ Confidence level appropriate")
                else:
                    print("⚠️ Confidence lower than expected")
                
                # Show reasoning if available
                if 'analysis' in result:
                    analysis = result['analysis']
                    if 'reasoning' in analysis:
                        print(f"💭 Reasoning: {analysis['reasoning'][:100]}...")
                
            else:
                print(f"❌ Request failed: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"💥 Test failed: {e}")
        
        time.sleep(1)  # Brief pause between tests
    
    print(f"\n🎯 Integration Test Complete")

if __name__ == "__main__":
    test_confidence_integration()