# JobMato ChatBot

A sophisticated AI-powered chatbot system for JobMato, built with Flask and WebSocket support. The system features intelligent query classification, specialized agents, and comprehensive JobMato API integration.

## 🚀 Key Features

### Intelligent Agent System
- **Query Classifier**: Automatically categorizes user queries into appropriate agent types
- **Specialized Agents**: Each agent handles specific tasks but with **flexible tool access**
- **Real-time Communication**: WebSocket-based chat with typing indicators
- **Persistent Storage**: MongoDB integration for conversation history

### 🔧 Flexible Tool System - **ANY AGENT CAN USE ANY TOOL**

**IMPORTANT**: All agents have access to ALL JobMato tools and can use them intelligently based on user needs:

#### Available Tools for All Agents:
1. **Profile Tool**: Get user profile data (experience, skills, preferences)
2. **Resume Tool**: Get user resume/CV information 
3. **Job Search Tool**: Search jobs with comprehensive parameters
4. **Resume Upload Tool**: Help users upload/update their resume

#### Intelligent Tool Usage Examples:
- **General Chat Agent**: "How's the job market?" → Uses job search tool to show current opportunities
- **Career Advice Agent**: "Should I transition to data science?" → Uses profile + resume + job search tools for market-informed advice  
- **Profile Info Agent**: "What jobs match my skills?" → Uses profile + job search tools
- **Resume Analysis Agent**: "What skills am I missing?" → Uses resume + job search tools for market analysis
- **Project Suggestion Agent**: "What projects should I build?" → Uses profile + job search tools for market-relevant suggestions

### Agent Categories

1. **JOB_SEARCH**: Intelligent job searching with all available parameters
2. **RESUME_ANALYSIS**: Comprehensive resume analysis with market context
3. **CAREER_ADVICE**: Personalized career guidance with job market insights
4. **PROJECT_SUGGESTION**: Skill-building project recommendations 
5. **PROFILE_INFO**: User profile information and job matching
6. **GENERAL_CHAT**: Conversational AI with proactive tool usage
7. **RESUME_UPLOAD**: Resume file handling and processing

## 🛠 Technical Architecture

### Backend Components
- **Flask + SocketIO**: Real-time WebSocket communication
- **MongoDB**: Persistent conversation storage (`admin.mato_chats` collection)
- **Google Gemini**: LLM integration for intelligent responses
- **JobMato API**: Full integration with authentication

### Tool System Architecture
```python
# All agents inherit from BaseAgent which inherits from JobMatoToolsMixin
class BaseAgent(ABC, JobMatoToolsMixin):
    # Provides access to all JobMato tools
    
class CareerAdviceAgent(BaseAgent):
    # Can use any tool: profile, resume, job search, upload
    
class GeneralChatAgent(BaseAgent):
    # Can use any tool based on user query analysis
```

## 📋 Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   ```bash
   # .env file
   GEMINI_API_KEY=your_gemini_api_key
   MONGODB_CONNECTION_STRING=your_mongodb_connection
   JWT_SECRET=your_jwt_secret
   ```

3. **Run the Application**:
   ```bash
   python app.py
   ```
   Server runs on `http://localhost:5001`

## 🧪 Testing

### Run Complete Test Suite:
```bash
python test_chatbot.py
```

This tests both basic functionality and **flexible agent tool usage**, verifying that:
- Agents can intelligently select and use appropriate tools
- Job search tools work across different agent types
- Profile and resume tools provide context for all agents
- Market data informs recommendations across all categories

### Example Flexible Tool Usage:
```python
# General Chat asking about jobs → Uses job search tool
"How's the job market for Python developers?"

# Career Advice → Uses profile + resume + job search
"I want advice on transitioning to data science"

# Profile Info → Uses profile + job search for matching
"What jobs match my profile and skills?"
```

## 🌐 API Integration

### JobMato API Features:
- **Job Search**: All parameters (location, skills, salary, experience, work mode)
- **User Profile**: Complete profile data retrieval
- **Resume Management**: Upload, retrieve, and analyze resumes
- **JWT Authentication**: Secure API access

### MongoDB Integration:
- **Collection**: `admin.mato_chats`
- **Real-time Storage**: All conversations persisted
- **Session Management**: Multi-user session handling
- **Search Capabilities**: Full conversation search

## 💡 Key Benefits

1. **Intelligent Tool Selection**: Agents automatically choose appropriate tools based on query context
2. **Market-Informed Responses**: All agents can access current job market data
3. **Personalized Interactions**: Profile and resume data used across all agent types
4. **Comprehensive Coverage**: No query type is limited to a single tool set
5. **Real-time Experience**: WebSocket communication with persistent storage

## 🚀 Usage Examples

### Multi-Tool Career Advice:
```
User: "I'm a Python developer, should I learn React?"
Agent: Uses profile tool → job search tool → provides market-informed advice
```

### Cross-Agent Job Search:
```
User: "Tell me about myself and current opportunities"
Profile Agent: Uses profile tool → job search tool → provides comprehensive overview
```

### Market-Aware Project Suggestions:
```
User: "What projects should I build to get hired?"
Project Agent: Uses profile tool → job search tool → suggests market-relevant projects
```

The system ensures that **every agent can provide comprehensive, tool-enhanced responses** regardless of the initial query classification, making the chatbot more intelligent and helpful for users.

## 🚀 Production Deployment

### Option 1: Local/Server Deployment

#### Quick Setup & Run:
```bash
# Clone repository and navigate to project
cd jobmato_chatbot

# Setup and run locally
chmod +x deploy_local.sh
./deploy_local.sh setup    # Install dependencies
./deploy_local.sh dev      # Start in development mode
# OR
./deploy_local.sh prod     # Start in production mode

# Management commands
./deploy_local.sh status   # Check application status
./deploy_local.sh restart  # Restart the application
./deploy_local.sh logs     # View and follow logs
./deploy_local.sh stop     # Stop the application
```

#### Production Server Deployment:
```bash
# For production server deployment (requires root)
chmod +x start_jobmato.sh
sudo ./start_jobmato.sh setup    # Complete production setup
sudo ./start_jobmato.sh start    # Start application

# Management (with systemd service)
sudo systemctl start jobmato-chatbot
sudo systemctl stop jobmato-chatbot
sudo systemctl restart jobmato-chatbot
sudo systemctl status jobmato-chatbot
```

#### Environment Variables:
```bash
# Set custom port and host
PORT=8080 HOST=0.0.0.0 ./deploy_local.sh prod

# Production environment file
cp env.example .env
# Edit .env with your configuration:
# - MONGODB_URI
# - GEMINI_API_KEY
# - Other settings
```

### Option 2: Docker Deployment

#### Quick Docker Setup:
```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f jobmato-chatbot

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

#### Manual Docker Build:
```bash
# Build image
docker build -t jobmato-chatbot .

# Run container
docker run -d \
  --name jobmato-chatbot \
  -p 5000:5000 \
  -e MONGODB_URI="your_mongodb_uri" \
  -e GEMINI_API_KEY="your_api_key" \
  jobmato-chatbot
```

### Option 3: Cloud Deployment

#### Heroku:
```bash
# Install Heroku CLI and login
heroku create jobmato-chatbot

# Set environment variables
heroku config:set MONGODB_URI="your_mongodb_uri"
heroku config:set GEMINI_API_KEY="your_api_key"

# Deploy
git push heroku main
```

#### AWS/Google Cloud/Azure:
- Use the provided Dockerfile for container deployment
- Configure environment variables in your cloud platform
- Set up load balancer and auto-scaling as needed

## 🔧 Production Configuration

### Environment Variables:
- `MONGODB_URI`: MongoDB connection string
- `GEMINI_API_KEY`: Google Gemini API key
- `PORT`: Application port (default: 5000)
- `HOST`: Bind host (default: 0.0.0.0)
- `FLASK_ENV`: production/development
- `DEBUG`: true/false

### Monitoring & Logs:
- **Local deployment**: Logs in `./logs/` directory
- **Production deployment**: Logs in `/var/log/jobmato_chatbot/`
- **Docker**: Use `docker logs jobmato-chatbot`

### Auto-Restart Features:
- **Systemd service**: Automatic restart on failure
- **Docker**: `restart: unless-stopped` policy
- **Cron monitoring**: For non-root deployments
- **Health checks**: Built-in health monitoring

### Performance Optimization:
- **Gunicorn**: Production WSGI server with eventlet workers
- **Connection pooling**: MongoDB connection optimization
- **Rate limiting**: Configurable request throttling
- **Caching**: Memory management for better performance

### Security:
- **Non-root user**: Application runs as dedicated user
- **Environment isolation**: Virtual environment separation
- **Secure headers**: Production security headers
- **HTTPS support**: SSL/TLS configuration ready

## 🛠 Maintenance Commands

```bash
# Check application status
./deploy_local.sh status
# OR
sudo systemctl status jobmato-chatbot

# View real-time logs
./deploy_local.sh logs
# OR
sudo journalctl -u jobmato-chatbot -f

# Restart after configuration changes
./deploy_local.sh restart
# OR
sudo systemctl restart jobmato-chatbot

# Update application
git pull
./deploy_local.sh restart
# OR
docker-compose up -d --build
```

# JobMato Chatbot - Enhanced WebSocket Implementation

A Python Flask-based chatbot with enhanced WebSocket functionality, JWT authentication, Redis session management, and real-time communication features.

## 🚀 Features

### Enhanced WebSocket Implementation
- **JWT Authentication**: Secure WebSocket connections with JWT token validation
- **Redis Session Management**: Scalable session storage with online Redis support
- **Real-time Communication**: Typing indicators, connection health monitoring
- **Resume Upload Integration**: Real-time notifications for resume uploads
- **Error Handling**: Comprehensive error handling and recovery mechanisms
- **Connection Health**: Ping/pong monitoring for connection stability

### Chatbot Capabilities
- **Multi-Agent Architecture**: Specialized agents for different query types
- **Job Search**: Intelligent job matching and recommendations
- **Resume Analysis**: ATS optimization and content analysis
- **Career Advice**: Personalized career guidance
- **Project Suggestions**: Relevant project recommendations
- **General Chat**: Conversational AI capabilities

## 📋 Configuration

### Centralized Configuration
All configuration is centralized in `config.py` with the following structure:

```python
# Main configuration classes
- Config: Base configuration with all settings
- DevelopmentConfig: Development environment settings
- ProductionConfig: Production environment settings  
- TestingConfig: Testing environment settings
```

### Key Configuration Sections
- **Flask Configuration**: Debug mode, secret keys
- **API Configuration**: Google Gemini, JobMato API endpoints
- **Database Configuration**: MongoDB and Redis settings
- **WebSocket Configuration**: Timeouts, events, connection settings
- **Security Configuration**: JWT settings, rate limiting
- **File Upload Configuration**: Size limits, allowed extensions
- **Agent Configuration**: Timeouts, retry settings

### Environment Variables (Optional Overrides)
You can override any configuration setting using environment variables:

```bash
# Copy the example environment file
cp env.example .env

# Edit .env with your settings
GEMINI_API_KEY=your_api_key_here
REDIS_URL=your_redis_url_here
JWT_SECRET=your_jwt_secret_here
```

## 🛠️ Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Redis (Optional but Recommended)
The application supports both local and online Redis services:

#### Option A: Online Redis (Recommended)
1. Choose a Redis service:
   - **Redis Cloud**: https://redis.com/try-free/
   - **Upstash**: https://upstash.com/
   - **Railway**: https://railway.app/
   - **Render**: https://render.com/

2. Get your Redis URL and update configuration:
```python
# In config.py or via environment variable
REDIS_URL = "redis://username:password@host:port"
REDIS_SSL = True
```

#### Option B: Local Redis
```bash
# Install Redis locally
brew install redis  # macOS
sudo apt-get install redis-server  # Ubuntu

# Start Redis
redis-server
```

### 3. Configure MongoDB (Optional)
For chat persistence, set up MongoDB:
```bash
# Install MongoDB
brew install mongodb-community  # macOS
sudo apt-get install mongodb  # Ubuntu

# Start MongoDB
mongod
```

### 4. Set Required API Keys
```bash
# Google Gemini API (Required)
export GEMINI_API_KEY="your_gemini_api_key_here"

# JWT Secret (Optional but recommended)
export JWT_SECRET="your_jwt_secret_here"
```

### 5. Run the Application
```bash
# Development mode
python app.py

# Or with specific environment
FLASK_ENV=production python app.py
```

## 🔌 WebSocket Usage

### Connection with Authentication
```javascript
// Connect with JWT token
const socket = io('http://localhost:5003', {
  query: { token: 'your_jwt_token_here' }
});

// Or with Authorization header
const socket = io('http://localhost:5003', {
  extraHeaders: {
    'Authorization': 'Bearer your_jwt_token_here'
  }
});
```

### Event Handlers
```javascript
// Connection events
socket.on('connect', () => {
  console.log('Connected to WebSocket');
});

socket.on('auth_status', (data) => {
  console.log('Authentication status:', data);
});

// Chat events
socket.on('session_status', (data) => {
  console.log('Session status:', data);
});

socket.on('receive_message', (data) => {
  console.log('Received message:', data);
});

// Typing indicators
socket.on('typing_status', (data) => {
  console.log('Typing status:', data);
});

// Error handling
socket.on('error', (data) => {
  console.error('WebSocket error:', data);
});
```

### Sending Messages
```javascript
// Initialize chat session
socket.emit('init_chat', { sessionId: 'optional_session_id' });

// Send message
socket.emit('send_message', { message: 'Hello, how can you help me?' });

// Typing indicator
socket.emit('typing_status', { isTyping: true });

// Health check
socket.emit('ping');
```

## 📡 HTTP Endpoints

### Main Webhook
```bash
POST /jobmato-assistant-test
Content-Type: application/json

{
  "chatInput": "Hello",
  "sessionId": "session_123",
  "token": "jwt_token_here"
}
```

### Resume Upload
```bash
POST /upload-resume
Content-Type: multipart/form-data

Form data:
- resume: file
- token: jwt_token_here
- session_id: session_123
```

## 🔧 Configuration Options

### Redis Configuration
```python
# In config.py
REDIS_URL = "redis://localhost:6379"  # Local Redis
REDIS_SSL = False

# For online Redis
REDIS_URL = "redis://username:password@host:port"
REDIS_SSL = True
```

### WebSocket Configuration
```python
# Connection timeouts
SOCKETIO_CONNECT_TIMEOUT = 60000  # 60 seconds
SOCKETIO_PING_TIMEOUT = 60000     # 60 seconds
SOCKETIO_PING_INTERVAL = 25000    # 25 seconds

# Session management
SESSION_TIMEOUT_HOURS = 24
MAX_CONVERSATION_HISTORY = 10
```

### Security Configuration
```python
# JWT settings
JWT_SECRET = "your_jwt_secret_here"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 3600
```

## 🧪 Testing

### WebSocket Testing
```bash
# Run the test script
python test_websocket.py
```

### Manual Testing
1. Start the application
2. Open browser to `http://localhost:5003`
3. Use browser console to test WebSocket connections
4. Monitor server logs for connection events

## 🚨 Troubleshooting

### Common Issues

#### Redis Connection Failed
```
⚠️ Redis not available: Connection refused
🔄 Falling back to in-memory session storage
```
**Solution**: 
- Check Redis server is running
- Verify Redis URL in configuration
- For online Redis, ensure SSL is enabled

#### JWT Authentication Failed
```
❌ Authentication failed for socket: No token provided
```
**Solution**:
- Ensure JWT token is provided in connection
- Verify token format and validity
- Check JWT secret configuration

#### WebSocket Connection Failed
```
❌ WebSocket connection failed
```
**Solution**:
- Check server is running on correct port
- Verify CORS settings
- Ensure client is using correct WebSocket URL

### Debug Mode
Enable debug logging:
```python
# In config.py
LOG_LEVEL = 'DEBUG'
DEBUG = True
```

### Health Checks
```bash
# Test HTTP endpoints
curl http://localhost:5003/

# Test WebSocket (using wscat)
npm install -g wscat
wscat -c "ws://localhost:5003/socket.io/?EIO=4&transport=websocket"
```

## 📊 Monitoring

### Connection Monitoring
- Real-time connection status
- User session tracking
- Redis health monitoring
- Error rate tracking

### Performance Metrics
- Message processing time
- Redis operation latency
- WebSocket connection stability
- Memory usage

## 🔒 Security Features

- JWT token validation
- Session-based authentication
- Rate limiting protection
- Input validation and sanitization
- Secure file upload handling
- CORS configuration

## 🚀 Production Deployment

### Environment Setup
```bash
# Set production environment
export FLASK_ENV=production

# Configure production Redis
export REDIS_URL="redis://prod-redis-url"
export REDIS_SSL=true

# Set secure JWT secret
export JWT_SECRET="secure_jwt_secret_here"
```

### Docker Deployment
```bash
# Build and run with Docker
docker build -t jobmato-chatbot .
docker run -p 5003:5003 jobmato-chatbot
```

### Scaling Considerations
- Use Redis cluster for high availability
- Implement load balancing for WebSocket connections
- Monitor memory usage and connection limits
- Set up proper logging and monitoring

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the configuration documentation

---

## ✅ Current Status

**Enhanced WebSocket Implementation Complete!**

### 🎯 What's Working:
- ✅ **Enhanced WebSocket server** running on port 5003
- ✅ **JWT authentication middleware** implemented
- ✅ **Redis integration** with online service support
- ✅ **Session management** with persistence
- ✅ **Error handling** and recovery mechanisms
- ✅ **Typing indicators** and real-time communication
- ✅ **Resume upload** with WebSocket broadcasting
- ✅ **HTTP endpoints** working correctly
- ✅ **MongoDB integration** for conversation storage
- ✅ **Comprehensive logging** and debugging

### 🌐 Online Redis Setup:
- ✅ **Setup script** for online Redis services
- ✅ **SSL support** for cloud Redis
- ✅ **Fallback to in-memory** storage if Redis unavailable
- ✅ **Multiple Redis providers** supported (Redis Cloud, Upstash, Railway, Render)

### 📋 Next Steps:
1. **Set up online Redis**: Run `python setup_online_redis.py`
2. **Configure environment**: Edit `.env` with your API keys
3. **Test WebSocket**: Use the chat interface at `http://localhost:5003`
4. **Deploy to production**: Use the provided deployment scripts

**Note**: This enhanced WebSocket implementation provides enterprise-level functionality with proper authentication, session management, and error handling. It's designed to scale and handle production workloads efficiently. 