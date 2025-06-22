#!/usr/bin/env python3
"""
Test script for JobMato ChatBot
"""

import requests
import json
import time

# Test configuration
BASE_URL = "http://localhost:5001"  # Updated to use current port
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjY4NDcxMDBlYTQxN2IwMGEyMGYzZjA1MSIsImVtYWlsIjoiaGFja3lhYmhheUBnbWFpbC5jb20iLCJpYXQiOjE3NTA1Nzk4MDYsImV4cCI6MTc1MTE4NDYwNn0.5cMF3TDItaJt7JPONtHEF3lAe-qgL8Q8ujwMagC1fVo"

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
            "token": JWT_TOKEN,  # Use real token
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
    print(f"\n💡 To test the web interface, visit: {BASE_URL}")

def test_flexible_agent_tools():
    """Test that agents can use any tool based on user query needs"""
    
    test_cases = [
        {
            "description": "General chat asking about job market - should use job search tool",
            "query": "How's the job market for Python developers?",
            "expected_category": "GENERAL_CHAT"
        },
        {
            "description": "Career advice about transitioning - should use profile + job search tools", 
            "query": "I want career advice on transitioning to data science",
            "expected_category": "CAREER_ADVICE"
        },
        {
            "description": "Profile info asking about matching jobs - should use profile + job search",
            "query": "What jobs match my profile and skills?", 
            "expected_category": "PROFILE_INFO"
        },
        {
            "description": "Resume analysis with market context - should use resume + job search",
            "query": "Analyze my resume and tell me what skills are missing for current market",
            "expected_category": "RESUME_ANALYSIS"
        },
        {
            "description": "Project suggestions based on market trends - should use profile + job search",
            "query": "Suggest projects that will help me get hired in the current market",
            "expected_category": "PROJECT_SUGGESTION"
        }
    ]
    
    print("🧪 Testing Flexible Agent Tool Usage")
    print("=" * 60)
    
    session_id = f"test_flexible_{int(time.time())}"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"Query: {test_case['query']}")
        
        try:
            payload = {
                "user_input": test_case['query'],
                "token": JWT_TOKEN,
                "user_id": "test_user_123",
                "session_id": session_id
            }
            
            response = requests.post(
                f"{BASE_URL}/jobmato-assistant-test",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Category: {result.get('category', 'Unknown')}")
                print(f"✅ Response received (length: {len(result.get('response', ''))} chars)")
                
                # Check if response indicates tool usage
                response_text = result.get('response', '').lower()
                tool_indicators = ['found', 'jobs', 'profile', 'resume', 'search', 'skills', 'market']
                used_tools = [indicator for indicator in tool_indicators if indicator in response_text]
                if used_tools:
                    print(f"🔧 Tools likely used: {', '.join(used_tools)}")
                
            else:
                print(f"❌ HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        time.sleep(1)  # Small delay between requests
    
    print("\n" + "=" * 60)
    print("✨ Flexible tool usage test completed!")

if __name__ == "__main__":
    print("🚀 JobMato ChatBot Test Suite")
    print(f"🌐 Testing against: {BASE_URL}")
    print(f"🔑 Using token: {JWT_TOKEN[:50]}...")
    print()
    
    # Run basic functionality test
    test_chatbot()
    
    print("\n" + "🔄" * 20)
    
    # Run flexible tool usage test
    test_flexible_agent_tools() 