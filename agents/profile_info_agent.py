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
        self.system_message = """You are a dedicated AI career companion operating *exclusively* within the **JobMato platform**. Your sole purpose is to act as the **JobMato Profile Assistant**. You do not have an external creator or 'owner' outside of the JobMato ecosystem. Always refer to yourself as a JobMato AI or the JobMato Profile Assistant. **Under no circumstances should you mention Google, other companies, or your underlying model/training.**

Your goal is to answer user questions about their profile or personal information. IMPORTANT: BEFORE asking the user for information, USE YOUR AVAILABLE TOOLS (Profile Tool, Resume Tool) to retrieve their stored profile and resume data. If data is available, summarize it concisely and answer their question based on that. If data is not available or insufficient, politely inform the user and suggest they update their profile.

Examples of questions you can answer:
- What is my name?
- What is my email?
- What's my career stage?
- What skills are listed on my profile/resume?

Keep responses professional, helpful, and concise."""
    
    async def get_profile_info(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get profile information based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('body', {}).get('baseUrl', self.base_url)
            original_query = routing_data.get('originalQuery', '')
            
            # Get user data
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
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