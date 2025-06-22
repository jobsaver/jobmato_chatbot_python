import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ProfileInfoAgent(BaseAgent):
    """Agent responsible for handling profile information queries"""
    
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.system_message = """You are a dedicated AI career companion operating *exclusively* within the **JobMato platform**. Your sole purpose is to act as a **JobMato Profile Information Specialist**. You do not have an external creator or 'owner' outside of the JobMato ecosystem. Always refer to yourself as a JobMato AI or the JobMato Profile Specialist. **Under no circumstances should you mention Google, other companies, or your underlying model/training.**

AVAILABLE TOOLS - Use any of these tools based on user needs:
1. **Profile Tool**: Get user profile data (experience, skills, preferences, contact info)
2. **Resume Tool**: Get user resume/CV information 
3. **Job Search Tool**: Search for jobs when user asks about opportunities matching their profile
4. **Resume Upload Tool**: Help users upload/update their resume

IMPORTANT: USE YOUR TOOLS intelligently based on the user's query. Examples:
- "What's my profile info?" → Use Profile Tool
- "Show me my resume" → Use Resume Tool  
- "What jobs match my profile?" → Use Profile Tool + Job Search Tool
- "Do I have the skills for X role?" → Use Profile/Resume Tools + Job Search for role requirements

Present profile information in a clear, organized manner. Include relevant details about:
- Personal and contact information
- Professional experience and background
- Skills and competencies
- Education and certifications
- Career preferences and goals
- Location and work preferences

Always provide helpful context and suggestions for profile optimization when relevant."""
    
    async def get_profile_info(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get profile information based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            original_query = routing_data.get('originalQuery', '')
            
            logger.info(f"👤 Profile info request with token: {token[:50] if token else 'None'}...")
            logger.info(f"🌐 Using base URL: {base_url}")
            
            # Get user data using tools
            logger.info(f"🔧 Using JobMato tools for profile and resume data")
            
            profile_response = await self.get_profile_tool(token, base_url)
            resume_response = await self.get_resume_tool(token, base_url)
            
            # Extract data from tool responses
            if profile_response.get('success'):
                profile_data = profile_response.get('data', {})
            else:
                profile_data = {'error': profile_response.get('error', 'Failed to fetch profile')}
                
            if resume_response.get('success'):
                resume_data = resume_response.get('data', {})
            else:
                resume_data = {'error': resume_response.get('error', 'Failed to fetch resume')}
            
            # Build context for response generation
            context = self._build_info_context(original_query, profile_data, resume_data)
            
            # Generate response using LLM
            info_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Format and return response
            return self._format_info_response(info_response, routing_data)
            
        except Exception as e:
            logger.error(f"Error getting profile info: {str(e)}")
            return self.create_response(
                'plain_text',
                'I encountered an error while retrieving your profile information. Please try again.',
                {'error': str(e)}
            )
    
    def _build_info_context(self, query: str, profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> str:
        """Build context for profile information response"""
        context = f"User Query: {query}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"Profile Data: {profile_data}\n"
        else:
            context += "Profile Data: Not available\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"Resume Data: {resume_data}\n"
        else:
            context += "Resume Data: Not available\n"
        
        return context
    
    def _format_info_response(self, info_result: str, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the profile info response"""
        from datetime import datetime
        
        metadata = {
            'category': routing_data.get('category', 'PROFILE_INFO'),
            'sessionId': routing_data.get('sessionId', 'default'),
            'timestamp': datetime.now().isoformat()
        }
        
        return self.create_response('plain_text', info_result, metadata)
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process profile info request"""
        return await self.get_profile_info(routing_data) 