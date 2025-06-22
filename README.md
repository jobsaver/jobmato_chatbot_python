# JobMato ChatBot

A sophisticated AI-powered career companion built with Python Flask and Google Gemini. The JobMato ChatBot provides intelligent career assistance including job search, resume analysis, career advice, and project suggestions.

## Features

- **Real-time WebSocket Communication**: Instant messaging with typing indicators and session management
- **MongoDB Persistence**: Chat history stored in MongoDB (`admin.mato_chats` collection) for data persistence
- **Job Search**: Intelligent job matching based on user queries with improved job card formatting
- **Resume Analysis**: Comprehensive resume review and improvement suggestions  
- **Career Advice**: Personalized career guidance and industry insights
- **Project Suggestions**: Tailored project recommendations for skill building
- **Profile Management**: User profile information retrieval and management
- **General Chat**: Natural conversation with persistent memory management
- **Resume Upload**: Support for resume file uploads and processing
- **Session History**: Persistent conversation history with search and cleanup capabilities

## Installation

1. Clone the repository
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables in `.env` file:
   ```
   # MongoDB Configuration
   MONGODB_URI=mongodb+srv://your-connection-string/admin
   
   # Google Gemini API Key
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # JobMato API
   JOBMATO_API_BASE_URL=https://backend-v1.jobmato.com
   
   # Flask Configuration
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   ```
6. Run the application: `python app.py`

**Note**: The application now uses WebSocket for real-time communication and MongoDB for persistent chat storage in the `admin.mato_chats` collection. The server runs on port 5001 by default to avoid conflicts with macOS AirPlay Receiver.

## Usage

Visit `http://localhost:5001` to access the modern chat interface with real-time WebSocket communication.

### Communication Methods

**WebSocket Events** (Real-time, recommended):
- `chat_message` - Send chat messages
- `chat_response` - Receive assistant responses
- `typing_start/stop` - Typing indicators
- `session_joined` - Session management
- `get_session_history` - Retrieve chat history
- `clear_session` - Clear session history

**REST API Endpoints** (Legacy support):
- `POST /jobmato-assistant-test` - Main chat endpoint
- `POST /resume-upload` - Resume upload endpoint

### Example Queries

- "Find me Python developer jobs in remote"
- "Can you review my resume?"
- "I need career advice for transitioning to data science"
- "Suggest some projects for learning machine learning"
- "What's my current profile information?"

## Architecture

The chatbot follows a modular agent-based architecture with:
- **Query Classifier Agent**: Routes queries to appropriate specialized agents
- **Specialized Agents**: Job Search, Resume Analysis, Career Advice, Project Suggestions, Profile Info, General Chat
- **LLM Client**: Google Gemini integration with fallback mock responses
- **MongoDB Manager**: Persistent chat storage in `admin.mato_chats` collection
- **Memory Manager**: Session management with MongoDB or in-memory fallback
- **WebSocket Handler**: Real-time communication with typing indicators
- **Response Formatter**: Consistent output formatting across all agents

### Key Improvements
- **Real-time Communication**: WebSocket support for instant messaging
- **Data Persistence**: MongoDB integration for chat history storage
- **Enhanced Job Formatting**: Improved job card display with better field mapping
- **Session Management**: Persistent sessions with history retrieval and cleanup
- **Scalable Architecture**: Background task processing for non-blocking responses

## License

MIT License 