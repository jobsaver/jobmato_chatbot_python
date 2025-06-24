#!/usr/bin/env python3
"""
Test script to verify .env file loading
"""

import os
from dotenv import load_dotenv

print("🔍 Testing .env file loading...")

# Test 1: Check if .env file exists
if os.path.exists('.env'):
    print("✅ .env file exists")
else:
    print("❌ .env file not found")

# Test 2: Load .env file
load_dotenv()
print("✅ load_dotenv() called")

# Test 3: Check some environment variables
env_vars = [
    'FLASK_ENV',
    'FLASK_DEBUG', 
    'GEMINI_API_KEY',
    'JOBMATO_API_BASE_URL',
    'MONGODB_URI',
    'REDIS_URL',
    'PORT',
    'HOST'
]

print("\n📋 Environment Variables:")
for var in env_vars:
    value = os.environ.get(var)
    if value:
        # Mask sensitive values
        if 'API_KEY' in var or 'SECRET' in var:
            display_value = value[:10] + "..." if len(value) > 10 else "***"
        else:
            display_value = value
        print(f"  {var}: {display_value}")
    else:
        print(f"  {var}: ❌ Not set")

# Test 4: Import and test config
print("\n🔧 Testing config.py import...")
try:
    from config import config
    current_config = config[os.environ.get('FLASK_ENV', 'development')]
    print("✅ config.py imported successfully")
    
    print(f"  FLASK_ENV: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"  DEBUG: {current_config.DEBUG}")
    print(f"  PORT: {current_config.PORT}")
    print(f"  HOST: {current_config.HOST}")
    print(f"  JOBMATO_API_BASE_URL: {current_config.JOBMATO_API_BASE_URL}")
    
except Exception as e:
    print(f"❌ Error importing config: {str(e)}")

print("\n✅ Environment loading test completed!") 