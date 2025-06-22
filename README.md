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