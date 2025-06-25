import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration"""
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']
    
    # Google Gemini API configuration
    GOOGLE_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY')
    
    # JobMato API configuration
    JOBMATO_API_BASE_URL = os.environ.get('JOBMATO_API_BASE_URL', 'https://backend-v1.jobmato.com')
    
    # MongoDB configuration
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb+srv://doadmin:064CU93w5RlQvz18@db-postgresql-blr1--main-db-009faed0.mongo.ondigitalocean.com')
    MONGODB_DATABASE = 'admin'
    MONGODB_COLLECTION = 'chatsessions'
    
    # Redis configuration for WebSocket session management
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://143.244.135.42')
    REDIS_DB = int(os.environ.get('REDIS_DB', '0'))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', 'SgYEtc6WAOgalgLviUDHFV1Yskt')
    REDIS_SSL = os.environ.get('REDIS_SSL', 'False').lower() in ['true', '1', 'yes']
    
    # Session configuration
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', '24'))
    MAX_CONVERSATION_HISTORY = int(os.environ.get('MAX_CONVERSATION_HISTORY', '10'))
    
    # WebSocket configuration
    SOCKETIO_CONNECT_TIMEOUT = int(os.environ.get('SOCKETIO_CONNECT_TIMEOUT', '60000'))
    SOCKETIO_PING_TIMEOUT = int(os.environ.get('SOCKETIO_PING_TIMEOUT', '60000'))
    SOCKETIO_PING_INTERVAL = int(os.environ.get('SOCKETIO_PING_INTERVAL', '25000'))
    
    # Server configuration
    PORT = int(os.environ.get('PORT', '5003'))
    HOST = os.environ.get('HOST', '0.0.0.0')
    
    # JWT configuration
    JWT_SECRET = os.environ.get('JWT_SECRET') or 'your_jwt_secret_here'
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRATION_HOURS = 24
    
    # Rate limiting configuration
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', '100'))
    RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW', '3600'))
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # File upload configuration
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {'.pdf', '.doc', '.docx'}
    
    # Chat configuration
    MAX_MESSAGE_LENGTH = 1000
    TYPING_TIMEOUT_SECONDS = 30
    
    # Agent configuration
    AGENT_TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3
    
 
    # WebSocket Events Configuration
    SOCKET_EVENTS = {
        'connect': 'connect',
        'disconnect': 'disconnect',
        'init_chat': 'init_chat',
        'send_message': 'send_message',
        'receive_message': 'receive_message',
        'typing_status': 'typing_status',
        'ping': 'ping',
        'pong': 'pong',
        'auth_status': 'auth_status',
        'session_status': 'session_status',
        'error': 'error',
        'chat_history': 'chat_history',
        'clear_session': 'clear_session',
        'load_more_jobs': 'load_more_jobs'
    }
    
    # Agent Types Configuration
    AGENT_TYPES = {
        'job_search': 'Job Search Agent',
        'resume': 'Resume Analysis Agent',
        'career_advice': 'Career Advice Agent',
        'project': 'Project Suggestion Agent',
        'general': 'General Chat Agent',
        'profile': 'Profile Info Agent'
    }
    
    # Response Types Configuration
    RESPONSE_TYPES = {
        'plain_text': 'Plain Text Response',
        'job_card': 'Job Card Response',
        'job_search': 'Job Search Response',
        'career_advice': 'Career Advice Response',
        'resume_analysis': 'Resume Analysis Response',
        'project_suggestion': 'Project Suggestion Response',
        'profile_info': 'Profile Info Response',
        'general_chat': 'General Chat Response',
        'resume_upload_success': 'Resume Upload Success',
        'resume_upload_required': 'Resume Upload Required',
        'error': 'Error Response'
    }
    
    # Error Codes Configuration
    ERROR_CODES = {
        'AUTH_FAILED': 'Authentication failed',
        'INVALID_TOKEN': 'Invalid JWT token',
        'SESSION_NOT_FOUND': 'Session not found',
        'MESSAGE_ERROR': 'Message processing error',
        'REDIS_ERROR': 'Redis connection error',
        'AGENT_ERROR': 'Agent processing error'
    }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    REDIS_SSL = False
    REDIS_URL = 'redis://143.244.135.42'
    MONGODB_COLLECTION = 'chatsessions'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'
    REDIS_SSL = False
    REDIS_URL = 'redis://143.244.135.42'
    # Production Redis URL should be set via environment variable
    MONGODB_COLLECTION = 'chatsessions'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    REDIS_URL = 'redis://143.244.135.42'
    REDIS_SSL = False
    MONGODB_COLLECTION = 'chatsessions'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 