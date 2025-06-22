from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime
import json
import re
from typing import Dict, Any, Optional
import logging
import asyncio
import os
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

# Initialize SocketIO with CORS support
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

class JobMatoChatBot:
    def __init__(self):
        self.query_classifier = QueryClassifierAgent()
        self.job_search_agent = JobSearchAgent()
        self.career_advice_agent = CareerAdviceAgent()
        self.resume_analysis_agent = ResumeAnalysisAgent()
        self.project_suggestion_agent = ProjectSuggestionAgent()
        self.profile_info_agent = ProfileInfoAgent()
        # Initialize general chat agent with shared memory manager
        self.general_chat_agent = None  # Will be initialized after memory manager
        self.response_formatter = ResponseFormatter()
        
        # Initialize memory manager with MongoDB
        mongodb_uri = app.config.get('MONGODB_URI')
        database_name = app.config.get('MONGODB_DATABASE', 'admin')
        collection_name = app.config.get('MONGODB_COLLECTION', 'mato_chats')
        
        if mongodb_uri:
            self.memory_manager = MemoryManager(mongodb_uri, database_name, collection_name)
            logger.info("✅ Using MongoDB for chat persistence")
        else:
            self.memory_manager = MemoryManager()
            logger.warning("⚠️ Using in-memory storage (no persistence)")
        
        # Initialize general chat agent with shared memory manager
        self.general_chat_agent = GeneralChatAgent(self.memory_manager)
    
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
            'baseUrl': original_data.get('baseUrl', 'https://backend-v1.jobmato.com')
        }
        
        return routing_data
    
    async def process_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message through the workflow"""
        try:
            # Step 1: Classify the query
            classification_response = await self.query_classifier.classify_query(
                data.get('chatInput', ''), 
                data.get('token', ''),
                data.get('baseUrl', 'https://backend-v1.jobmato.com')
            )
            
            # Step 2: Parse classification
            routing_data = self.parse_classification(classification_response, data)
            
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
                'type': 'plain_text',
                'content': 'I apologize, but I encountered an error processing your request. Please try again.',
                'metadata': {
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
            }

# Initialize the chatbot
chatbot = JobMatoChatBot()

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"👤 Client connected: {request.sid}")
    emit('connected', {'status': 'connected', 'session_id': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"👋 Client disconnected: {request.sid}")

@socketio.on('join_session')
def handle_join_session(data):
    """Handle joining a chat session"""
    session_id = data.get('session_id', request.sid)
    join_room(session_id)
    logger.info(f"🏠 Client {request.sid} joined session: {session_id}")
    emit('session_joined', {'session_id': session_id}, room=session_id)

@socketio.on('leave_session')
def handle_leave_session(data):
    """Handle leaving a chat session"""
    session_id = data.get('session_id', request.sid)
    leave_room(session_id)
    logger.info(f"🚪 Client {request.sid} left session: {session_id}")

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle incoming chat messages via WebSocket"""
    try:
        logger.info(f"💬 Received WebSocket message: {data}")
        
        # Extract message data
        session_id = data.get('session_id', request.sid)
        user_message = data.get('message', '')
        token = data.get('token', '')
        base_url = data.get('baseUrl', 'https://backend-v1.jobmato.com')
        
        if not user_message.strip():
            emit('error', {'message': 'Empty message received'}, room=session_id)
            return
        
        # Join session room if not already joined
        join_room(session_id)
        
        # Emit typing indicator
        emit('typing_start', {}, room=session_id)
        
        # Prepare request data
        request_data = {
            'chatInput': user_message,
            'sessionId': session_id,
            'token': token,
            'baseUrl': base_url
        }
        
        # Process message asynchronously
        def process_async():
            try:
                response = asyncio.run(chatbot.process_message(request_data))
                
                # Stop typing indicator
                socketio.emit('typing_stop', {}, room=session_id)
                
                # Send response
                socketio.emit('chat_response', {
                    'response': response,
                    'session_id': session_id,
                    'timestamp': datetime.now().isoformat()
                }, room=session_id)
                
                logger.info(f"✅ Response sent to session: {session_id}")
                
            except Exception as e:
                logger.error(f"❌ Error processing WebSocket message: {str(e)}")
                socketio.emit('typing_stop', {}, room=session_id)
                socketio.emit('error', {
                    'message': 'Sorry, I encountered an error processing your message.',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }, room=session_id)
        
        # Run in background thread
        socketio.start_background_task(process_async)
        
    except Exception as e:
        logger.error(f"❌ WebSocket error: {str(e)}")
        emit('error', {'message': 'An unexpected error occurred', 'error': str(e)})

@socketio.on('get_session_history')
def handle_get_session_history(data):
    """Handle request for session history"""
    try:
        session_id = data.get('session_id', request.sid)
        limit = data.get('limit', 10)
        
        def get_history_async():
            try:
                history = asyncio.run(chatbot.memory_manager.get_conversation_history(session_id))
                session_info = asyncio.run(chatbot.memory_manager.get_session_info(session_id))
                
                socketio.emit('session_history', {
                    'history': history,
                    'session_info': session_info,
                    'session_id': session_id
                }, room=session_id)
                
            except Exception as e:
                logger.error(f"❌ Error getting session history: {str(e)}")
                socketio.emit('error', {
                    'message': 'Error retrieving session history',
                    'error': str(e)
                }, room=session_id)
        
        socketio.start_background_task(get_history_async)
        
    except Exception as e:
        logger.error(f"❌ Error handling history request: {str(e)}")
        emit('error', {'message': 'Error processing history request', 'error': str(e)})

@socketio.on('clear_session')
def handle_clear_session(data):
    """Handle request to clear session history"""
    try:
        session_id = data.get('session_id', request.sid)
        
        def clear_session_async():
            try:
                success = asyncio.run(chatbot.memory_manager.clear_session(session_id))
                
                if success:
                    socketio.emit('session_cleared', {
                        'message': 'Session history cleared successfully',
                        'session_id': session_id
                    }, room=session_id)
                else:
                    socketio.emit('error', {
                        'message': 'Failed to clear session history',
                        'session_id': session_id
                    }, room=session_id)
                
            except Exception as e:
                logger.error(f"❌ Error clearing session: {str(e)}")
                socketio.emit('error', {
                    'message': 'Error clearing session',
                    'error': str(e)
                }, room=session_id)
        
        socketio.start_background_task(clear_session_async)
        
    except Exception as e:
        logger.error(f"❌ Error handling clear session: {str(e)}")
        emit('error', {'message': 'Error processing clear request', 'error': str(e)})

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
            'type': 'plain_text',
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
                'type': 'plain_text',
                'content': 'No resume file provided. Please upload a PDF file.',
                'metadata': {
                    'uploadSuccess': False,
                    'error': 'No file provided',
                    'uploadDate': datetime.now().isoformat()
                }
            }), 400
        
        file = request.files['resume']
        token = request.form.get('token', '')
        base_url = request.form.get('baseUrl', 'https://backend-v1.jobmato.com')
        
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
            return jsonify({
                'type': 'plain_text',
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
                'type': 'plain_text',
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
            'type': 'plain_text',
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
        allowed_extensions = {'.pdf', '.doc', '.docx'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': 'Only PDF and Word documents are allowed'
            }), 400
        
        # Validate file size (10MB limit)
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Reset to beginning
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            return jsonify({
                'success': False,
                'error': 'File size must be less than 10MB'
            }), 400
        
        logger.info(f"📤 Uploading resume: {file.filename} ({file_size} bytes) for session: {session_id}")
        
        # Use resume upload tool from any agent (they all inherit from JobMatoToolsMixin)
        try:
            # Create a temporary file-like object to pass to the tool
            file_content = file.read()
            file.seek(0)  # Reset for potential future use
            
            # Use the upload tool
            upload_result = asyncio.run(
                chatbot.job_search_agent.upload_resume(
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

if __name__ == '__main__':
    # Use SocketIO's run method instead of Flask's run method
    # Port 5001 to avoid conflicts with macOS AirPlay Receiver on port 5000
    port = int(os.environ.get('PORT', 5001))
    socketio.run(app, debug=True, host='0.0.0.0', port=port) 