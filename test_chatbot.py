#!/usr/bin/env python3
"""
Test script for JobMato ChatBot
"""

import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_MESSAGES = [
    "Hello! What can you help me with?",
    "Find me software engineer jobs in San Francisco",
    "Can you analyze my resume?",
    "I need career advice for transitioning to data science",
    "Suggest some Python projects for beginners",
    "What's my profile information?",
]

def test_chatbot():
    """Test the chatbot with various message types"""
    print("🎯 Testing JobMato ChatBot")
    print("=" * 50)
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print("❌ Server returned unexpected status code:", response.status_code)
            return
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start the application first:")
        print("   python app.py")
        return
    
    session_id = f"test_session_{int(time.time())}"
    
    for i, message in enumerate(TEST_MESSAGES, 1):
        print(f"\n{i}. Testing: '{message}'")
        print("-" * 30)
        
        # Prepare request data
        request_data = {
            "chatInput": message,
            "sessionId": session_id,
            "token": "demo_token",
            "baseUrl": "https://backend-v1.jobmato.com"
        }
        
        try:
            # Send request
            response = requests.post(
                f"{BASE_URL}/jobmato-assistant-test",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Response Type: {result.get('type', 'unknown')}")
                print(f"📝 Content: {result.get('content', '')[:100]}...")
                
                if result.get('metadata'):
                    print(f"📊 Metadata: {json.dumps(result['metadata'], indent=2)[:200]}...")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {str(e)}")
        
        # Small delay between requests
        time.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("🎉 Test completed!")
    print("\n💡 To test the web interface, visit: http://localhost:5000")

if __name__ == "__main__":
    test_chatbot() 