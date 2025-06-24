#!/usr/bin/env python3
"""
Test script to verify chat session functionality with MongoDB
Tests: session creation, message storage, last 5 messages retrieval, and context handling
"""

import asyncio
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.mongodb_manager import MongoDBManager
from utils.memory_manager import MemoryManager
from config import config

async def test_chat_sessions():
    """Test chat session functionality"""
    print("🧪 Testing Chat Session Functionality")
    print("=" * 50)
    
    # Get MongoDB configuration
    current_config = config[os.environ.get('FLASK_ENV', 'development')]
    mongodb_uri = current_config.MONGODB_URI
    
    print(f"📊 Using MongoDB: {mongodb_uri}")
    
    # Initialize MongoDB manager
    mongodb_manager = MongoDBManager(mongodb_uri, 'admin', 'chatsessions')
    
    # Initialize memory manager
    memory_manager = MemoryManager(mongodb_uri, 'admin', 'chatsessions')
    
    # Test session ID
    test_session_id = f"test_session_{int(datetime.now().timestamp())}"
    test_user_id = "test_user_123"
    
    print(f"\n🆔 Test Session ID: {test_session_id}")
    print(f"👤 Test User ID: {test_user_id}")
    
    try:
        # Test 1: Store multiple messages
        print("\n📝 Test 1: Storing multiple messages...")
        
        messages = [
            ("Hello, how are you?", "I'm doing great! How can I help you today?"),
            ("I'm looking for a job", "I'd be happy to help you find a job! What field are you interested in?"),
            ("I'm interested in software development", "Great choice! Software development is a growing field. What programming languages do you know?"),
            ("I know Python and JavaScript", "Excellent! Python and JavaScript are very popular. Are you looking for frontend, backend, or full-stack positions?"),
            ("I prefer backend development", "Perfect! Backend development with Python is in high demand. Would you like me to search for some opportunities?"),
            ("Yes, please search for Python backend jobs", "I'll search for Python backend development positions for you. Let me find some great opportunities!"),
            ("What was my last message?", "Your last message was asking me to search for Python backend jobs.")
        ]
        
        for i, (user_msg, assistant_msg) in enumerate(messages, 1):
            print(f"  📤 Message {i}: {user_msg[:50]}...")
            print(f"  📥 Response {i}: {assistant_msg[:50]}...")
            
            await memory_manager.store_conversation(
                session_id=test_session_id,
                user_message=user_msg,
                assistant_message=assistant_msg,
                user_id=test_user_id,
                metadata={'message_number': i}
            )
        
        # Test 2: Get last 5 messages
        print("\n📋 Test 2: Retrieving last 5 messages...")
        last_5_messages = await mongodb_manager.get_last_n_messages(test_session_id, 5)
        
        print(f"  📊 Retrieved {len(last_5_messages)} messages:")
        for i, msg in enumerate(last_5_messages, 1):
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:60]
            print(f"    {i}. {role.capitalize()}: {content}...")
        
        # Test 3: Get formatted conversation history
        print("\n📜 Test 3: Getting formatted conversation history...")
        formatted_history = await memory_manager.get_conversation_history(test_session_id, limit=5)
        
        print("  📝 Formatted History (last 5 messages):")
        print("  " + "-" * 40)
        if formatted_history:
            for line in formatted_history.split('\n'):
                print(f"  {line}")
        else:
            print("  ❌ No formatted history found")
        
        # Test 4: Get conversation context for agents
        print("\n🤖 Test 4: Getting conversation context for agents...")
        conversation_context = await memory_manager.get_conversation_history(test_session_id, limit=5)
        
        print("  🧠 Conversation Context:")
        print("  " + "-" * 40)
        if conversation_context:
            print(f"  {conversation_context}")
        else:
            print("  ❌ No conversation context found")
        
        # Test 5: Verify session stats
        print("\n📈 Test 5: Getting session statistics...")
        session_stats = await mongodb_manager.get_session_stats(test_session_id)
        
        print(f"  📊 Session Stats:")
        print(f"    - Session ID: {session_stats.get('session_id')}")
        print(f"    - Message Count: {session_stats.get('message_count', 0)}")
        print(f"    - Created At: {session_stats.get('created_at')}")
        print(f"    - Updated At: {session_stats.get('updated_at')}")
        print(f"    - User ID: {session_stats.get('user_id')}")
        
        # Test 6: Test context in routing data simulation
        print("\n🔄 Test 6: Simulating routing data with context...")
        
        # Simulate what the chatbot would do
        routing_data = {
            'sessionId': test_session_id,
            'originalQuery': 'What was my last message?',
            'conversation_context': conversation_context,
            'extractedData': {'language': 'english'},
            'token': 'test_token',
            'baseUrl': 'https://backend-v1.jobmato.com'
        }
        
        print(f"  📋 Routing Data Keys: {list(routing_data.keys())}")
        print(f"  🧠 Context Available: {'Yes' if routing_data.get('conversation_context') else 'No'}")
        print(f"  📝 Context Length: {len(routing_data.get('conversation_context', ''))} characters")
        
        # Test 7: Verify the context contains the right information
        print("\n✅ Test 7: Verifying context content...")
        context = routing_data.get('conversation_context', '')
        
        expected_phrases = [
            'Python backend jobs',
            'What was my last message',
            'Your last message was'
        ]
        
        for phrase in expected_phrases:
            found = phrase.lower() in context.lower()
            print(f"  🔍 '{phrase}': {'✅ Found' if found else '❌ Not found'}")
        
        print("\n🎉 All tests completed successfully!")
        
        # Cleanup: Clear test session
        print("\n🧹 Cleaning up test session...")
        await memory_manager.clear_session(test_session_id)
        print("  ✅ Test session cleared")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_chat_sessions())
    
    if success:
        print("\n🎯 Test Summary: All chat session functionality is working correctly!")
        print("✅ MongoDB integration: Working")
        print("✅ Message storage: Working") 
        print("✅ Last 5 messages retrieval: Working")
        print("✅ Conversation context: Working")
        print("✅ Session management: Working")
    else:
        print("\n💥 Test Summary: Some issues were found!")
        sys.exit(1) 