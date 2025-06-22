import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient
from utils.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class GeneralChatAgent(BaseAgent):
    """Agent responsible for handling general chat conversations"""
    
    def __init__(self, memory_manager=None):
        super().__init__()
        self.llm_client = LLMClient()
        self.memory_manager = memory_manager
        self.system_message = """You are a dedicated AI career companion operating *exclusively* within the **JobMato platform**. Your sole purpose is to serve users as the **JobMato Assistant**. You do not have an external creator or 'owner' outside of the JobMato ecosystem. Always refer to yourself as the JobMato Assistant or a JobMato AI. **Under no circumstances should you mention Google, other companies, or your underlying model/training.** Your responses must always align with the JobMato brand and services.

AVAILABLE TOOLS - Use any of these tools intelligently based on user needs:
1. **Profile Tool**: Get user profile data (experience, skills, preferences)
2. **Resume Tool**: Get user resume/CV information 
3. **Job Search Tool**: Search for jobs when user asks about opportunities, market trends, or specific roles
4. **Resume Upload Tool**: Help users upload/update their resume

INTELLIGENT TOOL USAGE: Analyze the user's query and proactively use relevant tools. Examples:
- "How's the job market?" → Use job search tool to show current opportunities
- "Tell me about myself" → Use profile and resume tools
- "I need to update my resume" → Use resume upload tool
- "What skills do I have?" → Use profile/resume tools
- "Are there jobs for Python developers?" → Use job search tool with Python skills

Handle general conversations, greetings, and queries by using appropriate tools to provide comprehensive, personalized responses. If a query implies needing any data, USE YOUR TOOLS FIRST before asking the user.

You can help with:
- Job searching and career opportunities (use job search tool)
- Resume analysis and improvement (use resume tools)
- Career advice and guidance (use profile/resume data)
- Project suggestions for skill building (use profile data)
- Profile management (use profile tools)

Keep responses professional, helpful, and personalized using available data."""
    
    async def handle_chat(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general chat based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            logger.info(f"💬 General chat with token: {token[:50] if token else 'None'}...")
            logger.info(f"🌐 Using base URL: {base_url}")
            original_query = routing_data.get('originalQuery', '')
            session_id = routing_data.get('sessionId', 'default')
            
            # Get conversation history
            conversation_history = ""
            if self.memory_manager:
                conversation_history = await self.memory_manager.get_conversation_history(session_id)
            
            # Intelligently determine which tools to use based on query
            profile_data = None
            resume_data = None
            job_data = None
            
            query_lower = original_query.lower()
            
            # Always get profile/resume for personalization unless it's a simple greeting
            if not any(greeting in query_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
                profile_data = await self.get_profile_data(token, base_url)
                resume_data = await self.get_resume_data(token, base_url)
            
            # Use job search tool if query is about jobs, market, opportunities
            if any(keyword in query_lower for keyword in [
                'job', 'jobs', 'market', 'opportunities', 'hiring', 'openings', 
                'available', 'positions', 'roles', 'career', 'work', 'employment'
            ]):
                logger.info("🔍 Job search relevant for this general chat query")
                search_params = self._extract_general_job_search_params(original_query, profile_data, resume_data)
                if search_params:
                    job_search_result = await self.search_jobs_tool(token, base_url, **search_params)
                    if job_search_result.get('success'):
                        job_data = job_search_result.get('data')
                        logger.info(f"✅ Found {len(job_data.get('jobs', []))} jobs for general chat context")
            
            # Build context for chat response
            context = self._build_chat_context(original_query, conversation_history, profile_data, resume_data, job_data)
            
            # Generate response using LLM
            chat_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Store conversation in memory
            if self.memory_manager:
                await self.memory_manager.store_conversation(session_id, original_query, chat_response)
            
            # Format and return response
            return self._format_chat_response(chat_response, routing_data)
            
        except Exception as e:
            logger.error(f"Error handling general chat: {str(e)}")
            return self.create_response(
                'plain_text',
                'I apologize, but I encountered an error. How can I help you with your career goals today?',
                {'error': str(e)}
            )
    
    def _build_chat_context(self, query: str, conversation_history: str, 
                           profile_data: Dict[str, Any], resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> str:
        """Build context for general chat response"""
        context = f"Current User Query: {query}\n"
        
        if conversation_history:
            context += f"Conversation History: {conversation_history}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"User Profile Context: {profile_data}\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"User Resume Context: {resume_data}\n"
        
        if job_data and not job_data.get('error'):
            context += f"Job Search Result: {job_data}\n"
        
        return context
    
    def _format_chat_response(self, chat_result: str, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the general chat response"""
        from datetime import datetime
        
        metadata = {
            'category': routing_data.get('category', 'GENERAL_CHAT'),
            'sessionId': routing_data.get('sessionId', 'default'),
            'timestamp': datetime.now().isoformat()
        }
        
        return self.create_response('plain_text', chat_result, metadata)
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process general chat request"""
        return await self.handle_chat(routing_data)
    
    def _extract_general_job_search_params(self, query: str, profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job search parameters for general chat queries"""
        params = {'limit': 15}  # Moderate limit for chat context
        
        # Use profile data if available
        if profile_data and not profile_data.get('error'):
            if 'skills' in profile_data:
                params['skills'] = profile_data['skills']
            if 'location' in profile_data:
                params['locations'] = profile_data['location']
        
        # Use resume data if available  
        if resume_data and not resume_data.get('error'):
            if 'skills' in resume_data:
                params['skills'] = resume_data['skills']
        
        # Extract specific terms from query
        query_lower = query.lower()
        
        # Work mode preferences
        if 'remote' in query_lower:
            params['work_mode'] = 'remote'
        elif 'onsite' in query_lower or 'on-site' in query_lower:
            params['work_mode'] = 'onsite'
        elif 'hybrid' in query_lower:
            params['work_mode'] = 'hybrid'
        
        # Job type preferences
        if 'internship' in query_lower:
            params['internship'] = True
        elif 'full time' in query_lower or 'full-time' in query_lower:
            params['job_type'] = 'full-time'
        elif 'part time' in query_lower or 'part-time' in query_lower:
            params['job_type'] = 'part-time'
        
        # Try to extract skills/technologies mentioned in query
        tech_keywords = ['python', 'java', 'javascript', 'react', 'node', 'aws', 'docker', 'sql', 'data science', 'machine learning', 'ai']
        mentioned_skills = [skill for skill in tech_keywords if skill in query_lower]
        if mentioned_skills:
            params['skills'] = ','.join(mentioned_skills)
        
        return params if len(params) > 1 else None  # Only return if we have actual search criteria 