#!/usr/bin/env python3
"""
WebSocket Test Script for JobMato Chatbot
This script tests the enhanced WebSocket functionality.
"""

import socketio
import time
import json

def test_websocket():
    """Test the WebSocket connection and basic functionality"""
    print("🧪 Testing JobMato WebSocket Functionality")
    print("=" * 50)
    
    # Create SocketIO client
    sio = socketio.Client()
    
    # Test events
    @sio.event
    def connect():
        print("✅ Connected to WebSocket server")
    
    @sio.event
    def disconnect():
        print("❌ Disconnected from WebSocket server")
    
    @sio.on('auth_status')
    def on_auth_status(data):
        print(f"🔐 Auth status: {data}")
    
    @sio.on('session_status')
    def on_session_status(data):
        print(f"📋 Session status: {data}")
    
    @sio.on('receive_message')
    def on_receive_message(data):
        print(f"💬 Received message: {data.get('content', '')[:100]}...")
    
    @sio.on('error')
    def on_error(data):
        print(f"❌ Error: {data}")
    
    @sio.on('pong')
    def on_pong():
        print("🏓 Received pong")
    
    try:
        # Connect to the server
        print("🔌 Connecting to WebSocket server...")
        sio.connect('http://localhost:5003')
        
        # Test ping/pong
        print("🏓 Testing ping/pong...")
        sio.emit('ping')
        time.sleep(1)
        
        # Test authentication (without token - should fail gracefully)
        print("🔐 Testing authentication...")
        sio.emit('init_chat', {})
        time.sleep(2)
        
        # Test sending message (should fail without proper session)
        print("💬 Testing message sending...")
        sio.emit('send_message', {'message': 'Hello, test message'})
        time.sleep(2)
        
        # Test typing status
        print("⌨️ Testing typing status...")
        sio.emit('typing_status', {'isTyping': True})
        time.sleep(1)
        sio.emit('typing_status', {'isTyping': False})
        time.sleep(1)
        
        print("✅ WebSocket tests completed successfully!")
        
    except Exception as e:
        print(f"❌ WebSocket test failed: {str(e)}")
    
    finally:
        # Disconnect
        if sio.connected:
            sio.disconnect()
        print("🔌 Disconnected from WebSocket server")

def test_http_endpoints():
    """Test HTTP endpoints"""
    print("\n🌐 Testing HTTP Endpoints")
    print("=" * 30)
    
    import requests
    
    try:
        # Test main page
        response = requests.get('http://localhost:5003')
        if response.status_code == 200:
            print("✅ Main page accessible")
        else:
            print(f"❌ Main page failed: {response.status_code}")
        
        # Test webhook endpoint
        test_data = {
            'chatInput': 'Hello, test message',
            'sessionId': 'test_session',
            'token': 'test_token',
            'baseUrl': 'https://backend-v1.jobmato.com'
        }
        
        response = requests.post('http://localhost:5003/jobmato-assistant-test', 
                               json=test_data)
        if response.status_code == 200:
            print("✅ Webhook endpoint working")
        else:
            print(f"❌ Webhook endpoint failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ HTTP test failed: {str(e)}")

if __name__ == "__main__":
    test_websocket()
    test_http_endpoints()
    print("\n🎉 All tests completed!") 