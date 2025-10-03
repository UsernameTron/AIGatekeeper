#!/usr/bin/env python3
"""
Test runner that properly sets up environment before running tests
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
    print(f"✅ Loaded environment from {env_file}")
else:
    print(f"⚠️  No .env file found at {env_file}")

# Verify critical env vars are set
required_vars = ['JWT_SECRET_KEY', 'SECRET_KEY', 'OPENAI_API_KEY']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"❌ Missing required environment variables: {missing_vars}")
    print("   Please create a .env file from .env.example")
    sys.exit(1)

print("✅ All required environment variables are set")
print()

# Now run pytest
import pytest

exit_code = pytest.main([
    'tests/test_end_to_end.py',
    '-v',
    '--tb=short',
    '--color=yes',
    '-p', 'no:warnings'
])

sys.exit(exit_code)
