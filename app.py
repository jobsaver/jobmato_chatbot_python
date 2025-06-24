from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from datetime import datetime
import json
import re
from typing import Dict, Any, Optional
import logging
import asyncio
import os
import redis
import jwt
from functools import wraps
from config import config
from agents.query_classifier import QueryClassifierAgent
from agents.job_search_agent import JobSearchAgent
from agents.career_advice_agent import CareerAdviceAgent
from agents.resume_analysis_agent import ResumeAnalysisAgent
from agents.project_suggestion_agent import ProjectSuggestionAgent
from agents.profile_info_agent import ProfileInfoAgent
from agents.general_chat_agent import GeneralChatAgent
from utils.response_formatter import ResponseFormatter
from utils.memory_manager import MemoryManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(config[os.environ.get('FLASK_ENV', 'development')])

# Get configuration
current_config = config[os.environ.get('FLASK_ENV', 'development')]

# Initialize SocketIO with enhanced configuration
socketio = SocketIO(
    app, 
    cors_allowed_origins="*", 
    async_mode='threading',
    connect_timeout=current_config.SOCKETIO_CONNECT_TIMEOUT,
    transports=['websocket', 'polling']
)

# Redis connection for session management
redis_client = None
try:
    redis_url = current_config.REDIS_URL
    redis_ssl = current_config.REDIS_SSL
    
    # Configure Redis connection with SSL support for online services
    if redis_ssl:
        # For online Redis services with SSL
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            ssl=True,
            ssl_cert_reqs=None,  # Don't verify SSL certificate
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=False,
            health_check_interval=0  # Disable health check to avoid recursion
        )
    else:
        # For local Redis or non-SSL connections
        redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=False,
            health_check_interval=0  # Disable health check to avoid recursion
        )
    
    # Test the connection
    redis_client.ping()
    logger.info("✅ Redis connected successfully")
    
except Exception as e:
    logger.warning(f"⚠️ Redis not available: {str(e)}")
    logger.info("🔄 Falling back to in-memory session storage")
    redis_client = None

# Global session tracking
connected_users = {}  # socket_id -> user_id
active_sessions = {}  # socket_id -> session_id
user_sessions = {}    # user_id -> set of session_ids
user_data_store = {}  # socket_id -> user_data

def ws_authenticate(callback):
    """WebSocket authentication middleware"""
    try:
        token = request.args.get('token') or request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            callback(Exception(current_config.ERROR_CODES['AUTH_FAILED']))
            return
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            user_id = payload.get('id')
            if not user_id:
                raise Exception("Invalid token payload")
            # Store user data in global dictionary
            user_data_store[request.sid] = {
                'id': user_id,
                'email': payload.get('email'),
                'token': token
            }
            logger.info(f"✅ Authenticated user {user_id} for socket {request.sid}")
            callback(None)
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Invalid JWT token for socket {request.sid}: {str(e)}")
            callback(Exception(current_config.ERROR_CODES['INVALID_TOKEN']))
    except Exception as e:
        logger.error(f"❌ Authentication error for socket {request.sid}: {str(e)}")
        callback(e)

def get_user_id():
    """Get user ID from global storage"""
    return user_data_store.get(request.sid, {}).get('id')

def get_user_data():
    """Get full user data from global storage"""
    return user_data_store.get(request.sid, {})

def store_user_session(user_id: str, socket_id: str):
    if not redis_client:
        return
    try:
        redis_client.hset(f"user_sessions:{user_id}", "socketId", socket_id)
        redis_client.hset(f"user_sessions:{user_id}", "connectedAt", datetime.now().isoformat())
        redis_client.expire(f"user_sessions:{user_id}", current_config.SESSION_TIMEOUT_HOURS * 3600)
        redis_client.set(f"socket_user:{socket_id}", user_id, current_config.SESSION_TIMEOUT_HOURS * 3600)
        logger.info(f"💾 Stored user session in Redis: {user_id} -> {socket_id}")
    except Exception as e:
        logger.error(f"❌ Failed to store user session in Redis: {str(e)}")

def get_user_session_from_redis(user_id: str) -> Optional[str]:
    if not redis_client:
        return None
    try:
        return redis_client.hget(f"user_sessions:{user_id}", "socketId")
    except Exception as e:
        logger.error(f"❌ Failed to get user session from Redis: {str(e)}")
        return None

def broadcast_to_user(user_id: str, event: str, data: dict):
    try:
        socket_id = get_user_session_from_redis(user_id)
        if socket_id:
            socketio.emit(event, data, room=socket_id)
        else:
            socketio.emit(event, data, room=user_id)
    except Exception as e:
        logger.error(f"❌ Error broadcasting to user {user_id}: {str(e)}")

def broadcast_typing_status(user_id: str, is_typing: bool):
    try:
        logger.info(f"📝 Broadcasting typing status for user {user_id}: {is_typing}")
        broadcast_to_user(user_id, current_config.SOCKET_EVENTS['typing_status'], {
            'isTyping': is_typing,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Error broadcasting typing status: {str(e)}")

def handle_error(error_type: str, error: Exception, session_id: str = None):
    logger.error(f"❌ {error_type}: {str(error)}")
    error_message = str(error) if isinstance(error, Exception) else "An error occurred"
    error_code = current_config.ERROR_CODES.get(error_type.upper(), error_type.upper())
    emit(current_config.SOCKET_EVENTS['error'], {
        'type': error_type,
        'code': error_code,
        'message': error_message,
        'sessionId': session_id,
        'timestamp': datetime.now().isoformat()
    }, room=request.sid)
    emit(error_type, {
        'error': True,
        'message': error_message,
        'code': error_code
    }, room=request.sid)

class JobMatoChatBot:
    def __init__(self):
        # Initialize memory manager first
        mongodb_uri = current_config.MONGODB_URI
        database_name = current_config.MONGODB_DATABASE
        collection_name = current_config.MONGODB_COLLECTION
        
        if mongodb_uri:
            self.memory_manager = MemoryManager(mongodb_uri, database_name, collection_name)
            logger.info("✅ Using MongoDB for chat persistence")
        else:
            self.memory_manager = MemoryManager()
            logger.warning("⚠️ Using in-memory storage (no persistence)")
        
        # Initialize all agents with memory manager
        self.query_classifier = QueryClassifierAgent()
        self.job_search_agent = JobSearchAgent(self.memory_manager)
        self.career_advice_agent = CareerAdviceAgent(self.memory_manager)
        self.resume_analysis_agent = ResumeAnalysisAgent(self.memory_manager)
        self.project_suggestion_agent = ProjectSuggestionAgent(self.memory_manager)
        self.profile_info_agent = ProfileInfoAgent(self.memory_manager)
        self.general_chat_agent = GeneralChatAgent(self.memory_manager)
        self.response_formatter = ResponseFormatter()
    
    def parse_classification(self, raw_response: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and clean the classification response from the LLM"""
        logger.info(f'Raw response from Query Classifier Agent: {raw_response}')
        
        cleaned_response = raw_response.strip()
        
        # Remove markdown code block wrappers
        json_block_regex = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(json_block_regex, cleaned_response)
        if match and match.group(1):
            cleaned_response = match.group(1).strip()
            logger.info(f'Cleaned response (extracted from markdown block): {cleaned_response}')
        else:
            logger.info('No markdown block found, proceeding with basic trim and brace search.')
        
        classification = None
        parse_error = None
        
        try:
            # Try parsing the cleaned response directly
            classification = json.loads(cleaned_response)
            logger.info(f'Successfully parsed directly: {classification}')
        except json.JSONDecodeError as direct_parse_error:
            parse_error = str(direct_parse_error)
            logger.info(f'Direct parsing failed, attempting brace isolation: {parse_error}')
            
            # Try to find JSON object structure within the string
            json_start_index = cleaned_response.find('{')
            json_end_index = cleaned_response.rfind('}')
            
            if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                json_string = cleaned_response[json_start_index:json_end_index + 1]
                try:
                    classification = json.loads(json_string)
                    logger.info(f'Successfully parsed from brace isolation: {classification}')
                except json.JSONDecodeError as brace_parse_error:
                    parse_error = str(brace_parse_error)
                    logger.error(f'JSON parsing failed even with brace isolation: {parse_error}')
            else:
                parse_error = 'No valid JSON object structure (braces) found.'
        
        # If classification failed, return default
        if not classification or not classification.get('category'):
            return {
                'category': 'GENERAL_CHAT',
                'confidence': 0.5,
                'extractedData': {},
                'originalQuery': original_data.get('chatInput', ''),
                'body': original_data,
                'token': original_data.get('token', ''),
                'sessionId': original_data.get('sessionId', 'default'),
                'error': f'Classification parsing failed. Original LLM response was: "{raw_response}". Error: {parse_error or "Unknown parsing error."}'
            }
        
        # Ensure extractedData is always an object
        classification['extractedData'] = classification.get('extractedData') or {}
        
        # Build routing data
        routing_data = {
            'category': classification['category'],
            'confidence': classification.get('confidence', 0.8),
            'extractedData': classification['extractedData'],
            'searchQuery': classification.get('searchQuery') or original_data.get('chatInput', ''),
            'originalQuery': original_data.get('chatInput', ''),
            'body': original_data,
            'token': original_data.get('token', ''),
            'sessionId': original_data.get('sessionId', 'default'),
            'baseUrl': original_data.get('baseUrl', current_config.JOBMATO_API_BASE_URL)
        }
        
        return routing_data
    
    async def process_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message through the workflow"""
        try:
            # Get conversation context first (last 5 messages)
            session_id = data.get('sessionId', '')
            conversation_context = ""
            if session_id and self.memory_manager:
                conversation_context = await self.memory_manager.get_conversation_history(session_id, limit=5)
            
            # Step 1: Classify the query
            classification_response = await self.query_classifier.classify_query(
                data.get('chatInput', ''), 
                data.get('token', ''),
                data.get('baseUrl', current_config.JOBMATO_API_BASE_URL)
            )
            
            # Step 2: Parse classification
            routing_data = self.parse_classification(classification_response, data)
            
            # Add conversation context to routing data
            routing_data['conversation_context'] = conversation_context
            
            # Step 3: Route to appropriate agent
            category = routing_data['category']
            
            if category == 'JOB_SEARCH':
                response = await self.job_search_agent.search_jobs(routing_data)
            elif category == 'CAREER_ADVICE':
                response = await self.career_advice_agent.provide_advice(routing_data)
            elif category == 'RESUME_ANALYSIS':
                response = await self.resume_analysis_agent.analyze_resume(routing_data)
            elif category == 'PROJECT_SUGGESTION':
                response = await self.project_suggestion_agent.suggest_projects(routing_data)
            elif category == 'PROFILE_INFO':
                response = await self.profile_info_agent.get_profile_info(routing_data)
            elif category == 'GENERAL_CHAT':
                response = await self.general_chat_agent.handle_chat(routing_data)
            else:
                # Default to general chat
                response = await self.general_chat_agent.handle_chat(routing_data)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                'type': current_config.RESPONSE_TYPES['plain_text'],
                'content': 'I apologize, but I encountered an error processing your request. Please try again.',
                'metadata': {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            }

# Initialize the chatbot
chatbot = JobMatoChatBot()

# WebSocket event handlers with enhanced functionality
@socketio.on(current_config.SOCKET_EVENTS['connect'])
def handle_connect(auth=None):
    logger.info(f"👤 Client connected: {request.sid}")
    ws_authenticate(lambda err: handle_auth_result(err))

def handle_auth_result(error):
    if error:
        logger.error(f"❌ Authentication failed for socket {request.sid}: {str(error)}")
        emit('auth_error', {
            'message': str(error),
            'code': current_config.ERROR_CODES['AUTH_FAILED']
        }, room=request.sid)
        disconnect()
    else:
        user_id = get_user_id()
        if user_id:
            store_user_session(user_id, request.sid)
            connected_users[request.sid] = user_id
            emit(current_config.SOCKET_EVENTS['auth_status'], {
                'authenticated': True,
                'userId': user_id,
                'socketId': request.sid
            }, room=request.sid)
            emit('available_agents', {
                'availableAgents': list(current_config.AGENT_TYPES.keys()),
                'message': 'These agent types are available for your queries'
            }, room=request.sid)
            logger.info(f"✅ User {user_id} authenticated successfully")
        else:
            logger.error(f"❌ No user ID found for authenticated socket {request.sid}")

def disconnect_unauthorized():
    import time
    time.sleep(5)
    if not get_user_id():
        disconnect()

@socketio.on(current_config.SOCKET_EVENTS['disconnect'])
def handle_disconnect():
    user_id = get_user_id()
    session_id = active_sessions.get(request.sid)
    logger.info(f"👋 Client disconnected: {request.sid}")
    if user_id and redis_client:
        try:
            redis_client.hdel(f"user_sessions:{user_id}", "socketId")
            redis_client.delete(f"socket_user:{request.sid}")
            logger.info(f"🧹 Cleaned up Redis session data for user: {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to clean up Redis session data: {str(e)}")
    connected_users.pop(request.sid, None)
    active_sessions.pop(request.sid, None)
    user_data_store.pop(request.sid, None)  # Clean up user data

@socketio.on(current_config.SOCKET_EVENTS['init_chat'])
def handle_init_chat(data=None):
    """Initialize a new chat session or load existing with enhanced error handling"""
    try:
        user_id = get_user_id()
        if not user_id:
            raise Exception("User not authenticated")
        
        logger.info(f"🔄 Initializing chat for user {user_id}")
        
        session_id = data.get('sessionId') if data else None
        
        if session_id:
            # Validate session ID format
            if not isinstance(session_id, str) or not session_id.strip():
                raise Exception("Invalid session ID format")
            
            # Check Redis for session validation
            if redis_client:
                try:
                    cached_session = redis_client.get(f"chat_session:{session_id}")
                    if cached_session:
                        session_data = json.loads(cached_session)
                        if session_data.get('userId') != user_id:
                            raise Exception("Invalid session ID")
                except Exception as redis_error:
                    logger.warn(f"⚠️ Redis session check failed: {str(redis_error)}")
        else:
            # Create new session
            session_id = f"session_{user_id}_{int(datetime.now().timestamp())}"
            
            # Cache session in Redis
            if redis_client:
                try:
                    session_data = {
                        'userId': user_id,
                        'sessionId': session_id,
                        'createdAt': datetime.now().isoformat()
                    }
                    redis_client.setex(f"chat_session:{session_id}", current_config.SESSION_TIMEOUT_HOURS * 3600, json.dumps(session_data))
                except Exception as redis_error:
                    logger.warn(f"⚠️ Failed to cache session in Redis: {str(redis_error)}")
            
            # Add to user sessions
            if user_id not in user_sessions:
                user_sessions[user_id] = set()
            user_sessions[user_id].add(session_id)
        
        # Update socket mappings
        active_sessions[request.sid] = session_id
        join_room(user_id)
        
        logger.info(f"✅ Session {session_id} initialized for user {user_id}")
        
        # Send success response
        response = {
            'connected': True,
            'sessionId': session_id,
            'userId': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        emit(current_config.SOCKET_EVENTS['session_status'], response, room=request.sid)
        emit('init_response', response, room=request.sid)
        
    except Exception as e:
        logger.error(f"❌ Init chat error: {str(e)}")
        error_response = {
            'connected': False,
            'error': str(e) if isinstance(e, Exception) else "Failed to initialize chat",
            'timestamp': datetime.now().isoformat()
        }
        
        emit(current_config.SOCKET_EVENTS['session_status'], error_response, room=request.sid)
        handle_error('init_error', e)

@socketio.on(current_config.SOCKET_EVENTS['send_message'])
def handle_send_message(data):
    """Handle incoming chat messages with enhanced error handling and recovery"""
    try:
        user_id = get_user_id()
        session_id = active_sessions.get(request.sid)
        
        logger.info(f"💬 Processing message: '{data.get('message', '')}' for session {session_id}, user {user_id}")
        
        if not user_id or not session_id:
            # Try to recover the session
            if user_id:
                # Try Redis recovery
                if redis_client:
                    redis_session_id = redis_client.get(f"last_session:{user_id}")
                    if redis_session_id:
                        logger.info(f"🔄 Attempting session recovery from Redis: {redis_session_id}")
                        handle_init_chat({'sessionId': redis_session_id})
                        # Retry sending message after session recovery
                        if data.get('message'):
                            socketio.start_background_task(lambda: retry_send_message(request, data))
            return
        
        message = data.get('message', '')
        if not message or not isinstance(message, str):
            raise Exception("Invalid message format")
        
        # Check if this is a load more request
        if message.lower().strip() in ['load more', 'load more jobs', 'more jobs', 'next page']:
            # Handle as load more request instead of new search
            logger.info(f"🔄 Detected load more request: {message}")
            
            # Get current page from session
            current_page = 1  # Default to page 1
            if redis_client:
                try:
                    last_page = redis_client.get(f"last_page:{session_id}")
                    if last_page:
                        current_page = int(last_page) + 1
                except Exception as e:
                    logger.warning(f"⚠️ Could not get last page: {str(e)}")
            
            # Emit load more event
            socketio.emit('load_more_jobs', {
                'page': current_page,
                'searchQuery': 'load more request'
            }, room=request.sid)
            return
        
        # Check message length
        if len(message) > current_config.MAX_MESSAGE_LENGTH:
            raise Exception(f"Message too long. Maximum length is {current_config.MAX_MESSAGE_LENGTH} characters.")
        
        # Store last active session in Redis
        if redis_client:
            redis_client.setex(f"last_session:{user_id}", current_config.SESSION_TIMEOUT_HOURS * 3600, session_id)
        
        # Don't emit typing for very short follow-up queries
        is_short_query = len(message) <= 15
        if not is_short_query:
            broadcast_typing_status(user_id, True)
        
        logger.info(f"🤖 Calling chatbot service for session {session_id}")
        
        # Process message
        request_data = {
            'chatInput': message,
            'sessionId': session_id,
            'token': get_user_data().get('token', ''),
            'baseUrl': current_config.JOBMATO_API_BASE_URL
        }
        
        response = asyncio.run(chatbot.process_message(request_data))
        
        # Always stop typing indicator
        broadcast_typing_status(user_id, False)
        
        if not response:
            raise Exception("No response received from chatbot")
        
        if not response.get('content'):
            raise Exception("Empty response content received from chatbot")
        
        # Cache response for potential replay
        if redis_client:
            try:
                redis_client.setex(f"last_response:{session_id}", 3600, json.dumps(response))
            except Exception as e:
                logger.warn(f"⚠️ Failed to cache response: {str(e)}")
        
        # Route based on response type
        if response.get('type') == 'career_advice':
            handle_career_response(request, response)
        else:
            handle_agent_response(request, response)
        
        # Update session activity
        active_sessions[request.sid] = session_id
        
    except Exception as e:
        logger.error(f"❌ Error in handle_send_message: {str(e)}")
        
        # Always stop typing indicator on error
        user_id = get_user_id()
        if user_id:
            broadcast_typing_status(user_id, False)
        
        # Send user-friendly error message
        emit(current_config.SOCKET_EVENTS['receive_message'], {
            'content': "I'm sorry, I encountered an issue processing your request. Please try again or start a new session if the problem persists.",
            'type': current_config.RESPONSE_TYPES['plain_text'],
            'metadata': {
                'error': True,
                'errorType': 'processing_error'
            }
        }, room=request.sid)

def retry_send_message(socket, data):
    """Retry sending message after session recovery"""
    import time
    time.sleep(0.5)
    handle_send_message(data)

@socketio.on(current_config.SOCKET_EVENTS['typing_status'])
def handle_typing_status(data):
    """Handle typing status with broadcasting to all user sockets"""
    try:
        user_id = get_user_id()
        if user_id:
            is_typing = data.get('isTyping', False)
            broadcast_typing_status(user_id, is_typing)
    except Exception as e:
        logger.error(f"❌ Error handling typing status: {str(e)}")

@socketio.on('get_chat_history')
def handle_get_chat_history():
    """Handle request for chat history"""
    try:
        session_id = active_sessions.get(request.sid)
        if not session_id:
            raise Exception("No active session")
        
        history = asyncio.run(chatbot.memory_manager.get_all_messages(session_id))
        emit(current_config.SOCKET_EVENTS['chat_history'], {'messages': history}, room=request.sid)
    except Exception as e:
        handle_error('history_error', e)

@socketio.on('get_user_sessions')
def handle_get_user_sessions():
    """Handle request for user's chat sessions"""
    try:
        user_id = get_user_id()
        if not user_id:
            raise Exception("User not authenticated")
        
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        emit('user_sessions', {'sessions': sessions}, room=request.sid)
    except Exception as e:
        handle_error('sessions_error', e)

@socketio.on('load_session')
def handle_load_session(data):
    """Handle request to load a specific session"""
    try:
        user_id = get_user_id()
        session_id = data.get('sessionId')
        
        if not user_id:
            raise Exception("User not authenticated")
        
        if not session_id:
            raise Exception("Session ID required")
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            raise Exception("Session not found or access denied")
        
        # Load session messages
        messages = asyncio.run(chatbot.memory_manager.get_all_messages(session_id))
        
        # Update active session
        active_sessions[request.sid] = session_id
        
        emit('session_loaded', {
            'sessionId': session_id,
            'messages': messages,
            'timestamp': datetime.now().isoformat()
        }, room=request.sid)
        
    except Exception as e:
        handle_error('load_session_error', e)

@socketio.on('delete_session')
def handle_delete_session(data):
    """Handle request to delete a session"""
    try:
        user_id = get_user_id()
        session_id = data.get('sessionId')
        
        if not user_id:
            raise Exception("User not authenticated")
        
        if not session_id:
            raise Exception("Session ID required")
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            raise Exception("Session not found or access denied")
        
        # Delete session
        success = asyncio.run(chatbot.memory_manager.delete_session(session_id))
        
        if success:
            emit('session_deleted', {
                'sessionId': session_id,
                'message': 'Session deleted successfully'
            }, room=request.sid)
        else:
            raise Exception("Failed to delete session")
        
    except Exception as e:
        handle_error('delete_session_error', e)

@socketio.on('update_session_title')
def handle_update_session_title(data):
    """Handle request to update session title"""
    try:
        user_id = get_user_id()
        session_id = data.get('sessionId')
        title = data.get('title')
        
        if not user_id:
            raise Exception("User not authenticated")
        
        if not session_id or not title:
            raise Exception("Session ID and title required")
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            raise Exception("Session not found or access denied")
        
        # Update title
        success = asyncio.run(chatbot.memory_manager.update_session_title(session_id, title))
        
        if success:
            emit('session_title_updated', {
                'sessionId': session_id,
                'title': title,
                'message': 'Session title updated successfully'
            }, room=request.sid)
        else:
            raise Exception("Failed to update session title")
        
    except Exception as e:
        handle_error('update_title_error', e)

@socketio.on(current_config.SOCKET_EVENTS['ping'])
def handle_ping():
    """Connection health check"""
    try:
        emit(current_config.SOCKET_EVENTS['pong'], room=request.sid)
        logger.debug(f"🏓 Ping-pong with client: {request.sid}")
    except Exception as e:
        logger.error(f"❌ Error handling ping: {str(e)}")

@socketio.on('load_more_jobs')
def handle_load_more_jobs(data):
    """Handle request to load more jobs (pagination)"""
    try:
        user_id = get_user_id()
        session_id = active_sessions.get(request.sid)
        
        if not user_id or not session_id:
            raise Exception("User not authenticated or session not initialized")
        
        # Get pagination parameters
        current_page = data.get('page', 1)
        search_query = data.get('searchQuery', '')
        
        logger.info(f"📄 Loading more jobs for user {user_id}, page {current_page}, query: {search_query}")
        
        # Get the last job search context from Redis
        extracted_data = {}
        if redis_client:
            try:
                # Try to get the last search context from Redis
                last_search_context = redis_client.get(f"last_search_context:{session_id}")
                if last_search_context:
                    extracted_data = json.loads(last_search_context)
                    logger.info(f"🔄 Retrieved search context from Redis: {extracted_data}")
                else:
                    logger.warning(f"⚠️ No search context found in Redis for session {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Could not retrieve search context from Redis: {str(e)}")
        
        # If no search context found, we can't do a proper follow-up search
        if not extracted_data:
            emit(current_config.SOCKET_EVENTS['receive_message'], {
                'content': 'Unable to load more jobs. Please perform a new search first.',
                'type': 'plain_text',
                'metadata': {'error': 'No search context'}
            }, room=request.sid)
            return
        
        # Prepare routing data for follow-up search
        routing_data = {
            'token': get_user_data().get('token', ''),
            'baseUrl': current_config.JOBMATO_API_BASE_URL,
            'sessionId': session_id,
            'originalQuery': extracted_data.get('original_query', search_query),
            'searchQuery': extracted_data.get('original_query', search_query),
            'extractedData': extracted_data
        }
        
        logger.info(f"🔄 Follow-up search routing data: {routing_data}")
        
        # Call follow-up job search
        response = asyncio.run(chatbot.job_search_agent.search_jobs_follow_up(routing_data, current_page))
        
        if response:
            handle_agent_response(request, response)
        else:
            emit(current_config.SOCKET_EVENTS['receive_message'], {
                'content': 'No more jobs found. Try adjusting your search criteria.',
                'type': 'plain_text',
                'metadata': {'error': 'No more jobs'}
            }, room=request.sid)
    except Exception as e:
        logger.error(f"❌ Error loading more jobs: {str(e)}")
        emit(current_config.SOCKET_EVENTS['receive_message'], {
            'content': 'Sorry, there was an error loading more jobs. Please try again.',
            'type': 'plain_text',
            'metadata': {'error': str(e)}
        }, room=request.sid)

def handle_career_response(socket, response):
    """Handle career advice responses"""
    if not response or not response.get('content'):
        handle_error('response_error', Exception("Invalid career response"))
        return
    
    logger.info("🎯 Processing career response:", {
        'type': response.get('type'),
        'hasContent': bool(response.get('content')),
        'metadata': response.get('metadata')
    })
    
    # Format career suggestions if available
    suggestions = response.get('metadata', {}).get('suggestions', [])
    formatted_response = format_career_suggestions(suggestions) if suggestions else response.get('content')
    
    emit(current_config.SOCKET_EVENTS['receive_message'], {
        'content': formatted_response,
        'type': 'career_advice',
        'metadata': response.get('metadata', {})
    }, room=request.sid)

def handle_agent_response(socket, response):
    """Handle agent responses with enhanced job card support"""
    if not response or not response.get('content'):
        handle_error('response_error', Exception("Invalid response from agent"))
        return
    
    content = response.get('content')
    response_type = response.get('type', 'plain_text')
    metadata = response.get('metadata', {})
    
    # Enhanced job card handling
    if response_type == 'job_card' and metadata.get('jobs'):
        session_id = active_sessions.get(request.sid)
        if session_id and redis_client:
            try:
                # Cache jobs and metadata for session replay
                redis_client.setex(f"job_agent:jobs:{session_id}", 3600, json.dumps(metadata.get('jobs')))
                redis_client.setex(f"job_agent:metadata:{session_id}", 3600, json.dumps(metadata))
                
                # Store search context for follow-up searches
                if metadata.get('searchContext'):
                    redis_client.setex(f"last_search_context:{session_id}", 3600, json.dumps(metadata['searchContext']))
                    logger.info(f"💾 Stored search context for session {session_id}")
            except Exception as e:
                logger.warn(f"⚠️ Failed to cache job data: {str(e)}")
    
    # Always emit through receive_message with consistent format
    emit(current_config.SOCKET_EVENTS['receive_message'], {
        'content': content,
        'type': response_type,
        'metadata': {
            **metadata,
            # For job cards, ensure jobs array is always present
            **({'jobs': metadata.get('jobs', []), 'totalJobs': metadata.get('totalJobs', len(metadata.get('jobs', [])))} if response_type == 'job_card' else {})
        }
    }, room=request.sid)

def format_career_suggestions(suggestions):
    """Format career suggestions for display"""
    if not suggestions:
        return "I don't have any specific career suggestions at the moment."
    
    formatted = "Here are some career suggestions for you:\n\n"
    for i, suggestion in enumerate(suggestions[:5], 1):  # Limit to 5 suggestions
        formatted += f"{i}. {suggestion}\n"
    
    return formatted

def broadcast_resume_upload_success(user_id: str):
    """Broadcast resume upload success message to user"""
    try:
        message = {
            'content': """🎉 **Resume uploaded successfully!** 

Your resume has been processed and is now ready for analysis. Here's what you can do now:

## 📋 Available Resume Analysis Options:

### 🔍 **General Analysis**
- Ask: *"Analyze my resume"* or *"Give me feedback on my resume"*
- Get comprehensive feedback on content, structure, and improvements

### 🎯 **ATS Optimization** 
- Ask: *"Make my resume ATS-friendly"* or *"ATS optimization"*
- Get specific tips to pass Applicant Tracking Systems

### 💼 **Job-Specific Analysis**
- Ask: *"How does my resume match [job title]?"*
- Get targeted feedback for specific roles

### 🚀 **Skills Analysis**
- Ask: *"What skills should I add?"* or *"Skill gap analysis"*
- Identify missing skills for your career goals

### 📈 **Industry Insights**
- Ask: *"Industry trends for my field"*
- Get market insights and recommendations

**Ready to get started?** Just type any of the questions above, or ask me anything specific about your resume!""",
            'type': 'resume_upload_success',
            'metadata': {
                'uploadSuccess': True,
                'availableOptions': [
                    'General Resume Analysis',
                    'ATS Optimization',
                    'Job-Specific Analysis',
                    'Skills Gap Analysis',
                    'Industry Insights'
                ],
                'nextSteps': [
                    'Ask for general analysis',
                    'Request ATS optimization',
                    'Compare with specific job',
                    'Analyze skill gaps',
                    'Get industry insights'
                ]
            }
        }
        
        broadcast_to_user(user_id, current_config.SOCKET_EVENTS['receive_message'], message)
        logger.info(f"📤 Sent resume upload success message to user: {user_id}")
    except Exception as e:
        logger.error(f"❌ Error broadcasting resume upload success: {str(e)}")

# Legacy event handlers for backward compatibility
@socketio.on('chat_message')
def handle_chat_message_legacy(data):
    """Legacy chat message handler for backward compatibility"""
    # Convert to new format
    new_data = {
        'message': data.get('message', ''),
        'sessionId': data.get('session_id', request.sid),
        'token': data.get('token', ''),
        'baseUrl': data.get('baseUrl', 'https://backend-v1.jobmato.com')
    }
    handle_send_message(new_data)

@socketio.on('join_session')
def handle_join_session(data):
    """Legacy session join handler"""
    session_id = data.get('session_id', request.sid)
    join_room(session_id)
    logger.info(f"🏠 Client {request.sid} joined session: {session_id}")
    emit('session_joined', {'session_id': session_id}, room=session_id)

@socketio.on('leave_session')
def handle_leave_session(data):
    """Legacy session leave handler"""
    session_id = data.get('session_id', request.sid)
    leave_room(session_id)
    logger.info(f"🚪 Client {request.sid} left session: {session_id}")

@socketio.on('get_session_history')
def handle_get_session_history_legacy(data):
    """Legacy session history handler"""
    handle_get_chat_history()

@socketio.on('clear_session')
def handle_clear_session(data):
    """Handle request to clear session history"""
    try:
        session_id = data.get('session_id', request.sid)
        
        def clear_session_async():
            try:
                success = asyncio.run(chatbot.memory_manager.clear_session(session_id))
                
                if success:
                    emit(current_config.SOCKET_EVENTS['session_cleared'], {
                        'message': 'Session history cleared successfully',
                        'session_id': session_id
                    }, room=session_id)
                else:
                    emit(current_config.SOCKET_EVENTS['error'], {
                        'message': 'Failed to clear session history',
                        'session_id': session_id
                    }, room=session_id)
                
            except Exception as e:
                logger.error(f"❌ Error clearing session: {str(e)}")
                emit(current_config.SOCKET_EVENTS['error'], {
                    'message': 'Error clearing session',
                    'error': str(e)
                }, room=session_id)
        
        socketio.start_background_task(clear_session_async)
        
    except Exception as e:
        logger.error(f"❌ Error handling clear session: {str(e)}")
        emit(current_config.SOCKET_EVENTS['error'], {'message': 'Error processing clear request', 'error': str(e)})

@app.route('/')
def index():
    """Serve the chat interface"""
    return render_template('chat.html')

@app.route('/jobmato-assistant-test', methods=['POST'])
def main_webhook():
    """Main webhook endpoint for processing chat messages"""
    try:
        data = request.get_json()
        logger.info(f"Received request: {data}")
        
        # Run async function in sync context
        response = asyncio.run(chatbot.process_message(data))
        
        logger.info(f"Sending response: {response}")
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in main webhook: {str(e)}")
        return jsonify({
            'type': current_config.RESPONSE_TYPES['plain_text'],
            'content': 'Sorry, I encountered an error. Please try again.',
            'metadata': {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        }), 500

@app.route('/resume-upload', methods=['POST'])
def resume_upload_webhook():
    """Webhook endpoint for resume uploads"""
    try:
        # Handle file upload
        if 'resume' not in request.files:
            return jsonify({
                'type': current_config.RESPONSE_TYPES['plain_text'],
                'content': 'No resume file provided. Please upload a PDF file.',
                'metadata': {
                    'uploadSuccess': False,
                    'error': 'No file provided',
                    'uploadDate': datetime.now().isoformat()
                }
            }), 400
        
        file = request.files['resume']
        token = request.form.get('token', '')
        base_url = request.form.get('baseUrl', current_config.JOBMATO_API_BASE_URL)
        
        # Forward to resume upload API
        import requests
        files = {'resume': (file.filename, file.stream, file.content_type)}
        headers = {'Authorization': f'Bearer {token}'}
        
        upload_response = requests.post(
            f'{base_url}/api/rag/resume/upload',
            files=files,
            headers=headers
        )
        
        if upload_response.status_code == 200:
            upload_result = upload_response.json()
            
            # Extract user ID from token for broadcasting
            try:
                payload = jwt.decode(token, options={"verify_signature": False})
                user_id = payload.get('id')
                if user_id:
                    # Broadcast resume upload success
                    broadcast_resume_upload_success(user_id)
            except Exception as e:
                logger.warning(f"⚠️ Could not extract user ID for broadcasting: {str(e)}")
            
            return jsonify({
                'type': current_config.RESPONSE_TYPES['plain_text'],
                'content': 'Resume uploaded successfully! I can now provide detailed analysis and personalized job recommendations based on your resume.',
                'metadata': {
                    'uploadSuccess': True,
                    'resumeId': upload_result.get('resumeId') or upload_result.get('id'),
                    'uploadDate': datetime.now().isoformat(),
                    'nextActions': [
                        'Ask for resume analysis',
                        'Search for relevant jobs',
                        'Get career advice'
                    ]
                }
            })
        else:
            return jsonify({
                'type': current_config.RESPONSE_TYPES['plain_text'],
                'content': 'Resume upload failed. Please ensure you\'re uploading a valid PDF file and try again.',
                'metadata': {
                    'uploadSuccess': False,
                    'error': upload_response.text,
                    'uploadDate': datetime.now().isoformat()
                }
            }), 400
            
    except Exception as e:
        logger.error(f"Error in resume upload: {str(e)}")
        return jsonify({
            'type': current_config.RESPONSE_TYPES['plain_text'],
            'content': 'Resume upload failed due to an unexpected error. Please try again.',
            'metadata': {
                'uploadSuccess': False,
                'error': str(e),
                'uploadDate': datetime.now().isoformat()
            }
        }), 500

@app.route('/upload-resume', methods=['POST'])
def upload_resume_ui():
    """UI-specific endpoint for resume uploads with FormData"""
    try:
        # Check if file is present
        if 'resume' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No resume file provided'
            }), 400
        
        file = request.files['resume']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'No file selected'
            }), 400
        
        # Get form data
        token = request.form.get('token', '')
        session_id = request.form.get('session_id', 'default')
        
        # Validate file type
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in current_config.ALLOWED_EXTENSIONS:
            return jsonify({
                'success': False,
                'error': f'Only {", ".join(current_config.ALLOWED_EXTENSIONS)} files are allowed'
            }), 400
        
        # Validate file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > current_config.MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'File size must be less than {current_config.MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400
        
        logger.info(f"📤 Uploading resume: {file.filename} ({file_size} bytes) for session: {session_id}")
        
        # Use resume upload tool from any agent (they all inherit from JobMatoToolsMixin)
        try:
            # Create a temporary file-like object to pass to the tool
            file_content = file.read()
            file.seek(0)  # Reset for potential future use
            
            # Use the upload tool
            upload_result = asyncio.run(
                chatbot.job_search_agent.upload_resume_tool(
                    file_content=file_content,
                    filename=file.filename,
                    token=token
                )
            )
            
            if upload_result.get('success'):
                logger.info(f"✅ Resume uploaded successfully for session: {session_id}")
                
                # Store upload info in memory manager if available
                if hasattr(chatbot, 'memory_manager') and chatbot.memory_manager:
                    try:
                        asyncio.run(chatbot.memory_manager.add_message(
                            session_id=session_id,
                            message=f"Resume '{file.filename}' uploaded successfully",
                            sender='system',
                            metadata={
                                'event_type': 'resume_upload',
                                'filename': file.filename,
                                'upload_id': upload_result.get('upload_id'),
                                'timestamp': datetime.now().isoformat()
                            }
                        ))
                    except Exception as e:
                        logger.warning(f"⚠️ Could not store upload event in memory: {str(e)}")
                
                # Extract user ID from token for broadcasting
                try:
                    payload = jwt.decode(token, options={"verify_signature": False})
                    user_id = payload.get('id')
                    if user_id:
                        # Broadcast resume upload success
                        broadcast_resume_upload_success(user_id)
                except Exception as e:
                    logger.warning(f"⚠️ Could not extract user ID for broadcasting: {str(e)}")
                
                return jsonify({
                    'success': True,
                    'message': 'Resume uploaded successfully!',
                    'upload_id': upload_result.get('upload_id'),
                    'filename': file.filename
                })
            else:
                error_msg = upload_result.get('error', 'Upload failed')
                logger.error(f"❌ Resume upload failed: {error_msg}")
                return jsonify({
                    'success': False,
                    'error': error_msg
                }), 400
                
        except Exception as tool_error:
            logger.error(f"❌ Resume upload tool error: {str(tool_error)}")
            return jsonify({
                'success': False,
                'error': f'Upload processing failed: {str(tool_error)}'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Error in UI resume upload: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred during upload'
        }), 500

# REST API endpoints for chat history management
@app.route('/api/chat/sessions', methods=['GET'])
def get_user_sessions_api():
    """Get all chat sessions for the authenticated user"""
    try:
        # Extract user ID from token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get('id')
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get sessions from memory manager
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        
        return jsonify({
            'success': True,
            'sessions': sessions,
            'count': len(sessions)
        })
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"❌ Error getting user sessions: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chat/sessions/<session_id>', methods=['GET'])
def get_session_messages_api(session_id):
    """Get all messages for a specific session"""
    try:
        # Extract user ID from token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get('id')
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get session messages
        messages = asyncio.run(chatbot.memory_manager.get_all_messages(session_id))
        
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'messages': messages,
            'count': len(messages)
        })
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"❌ Error getting session messages: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chat/sessions/<session_id>', methods=['DELETE'])
def delete_session_api(session_id):
    """Delete a specific session"""
    try:
        # Extract user ID from token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get('id')
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Delete session
        success = asyncio.run(chatbot.memory_manager.delete_session(session_id))
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Session deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete session'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"❌ Error deleting session: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chat/sessions/<session_id>/title', methods=['PUT'])
def update_session_title_api(session_id):
    """Update the title of a session"""
    try:
        # Extract user ID from token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get('id')
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Get title from request body
        data = request.get_json()
        title = data.get('title')
        
        if not title:
            return jsonify({'error': 'Title is required'}), 400
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Update title
        success = asyncio.run(chatbot.memory_manager.update_session_title(session_id, title))
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Session title updated successfully',
                'title': title
            })
        else:
            return jsonify({'error': 'Failed to update session title'}), 500
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"❌ Error updating session title: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chat/sessions/<session_id>/clear', methods=['POST'])
def clear_session_messages_api(session_id):
    """Clear all messages from a session"""
    try:
        # Extract user ID from token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get('id')
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Clear session messages
        asyncio.run(chatbot.memory_manager.clear_session(session_id))
        
        return jsonify({
            'success': True,
            'message': 'Session messages cleared successfully'
        })
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"❌ Error clearing session messages: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/chat/sessions/<session_id>/context', methods=['GET'])
def get_session_context_api(session_id):
    """Get conversation context for agents (last 3 messages)"""
    try:
        # Extract user ID from token
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header required'}), 401
        
        token = auth_header.replace('Bearer ', '')
        payload = jwt.decode(token, options={"verify_signature": False})
        user_id = payload.get('id')
        
        if not user_id:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Validate session belongs to user
        sessions = asyncio.run(chatbot.memory_manager.get_user_sessions(user_id))
        session_exists = any(s['sessionId'] == session_id for s in sessions)
        
        if not session_exists:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get conversation context for agents
        context = asyncio.run(chatbot.memory_manager.get_conversation_context_for_agents(session_id, limit=3))
        
        return jsonify({
            'success': True,
            'sessionId': session_id,
            'context': context
        })
        
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401
    except Exception as e:
        logger.error(f"❌ Error getting session context: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Use SocketIO's run method instead of Flask's run method
    # Use configuration for port and host
    socketio.run(
        app, 
        debug=current_config.DEBUG, 
        host=current_config.HOST, 
        port=current_config.PORT
    )