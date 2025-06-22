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

Handle general conversations, greetings, and non-career specific queries. If a query implies needing user profile or resume data, USE YOUR AVAILABLE TOOLS (Profile Tool, Resume Tool) to retrieve it BEFORE asking the user. Only ask for information if the tools don't provide it or for clarification.

You can help with:
- Job searching and career opportunities
- Resume analysis and improvement
- Career advice and guidance
- Project suggestions for skill building
- Profile management

Keep responses professional, helpful, and concise, always maintaining the JobMato persona."""
    
    async def handle_chat(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general chat based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('body', {}).get('baseUrl', self.base_url)
            original_query = routing_data.get('originalQuery', '')
            session_id = routing_data.get('sessionId', 'default')
            
            # Get conversation history
            conversation_history = ""
            if self.memory_manager:
                conversation_history = await self.memory_manager.get_conversation_history(session_id)
            
            # Get user context if needed
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Build context for chat response
            context = self._build_chat_context(original_query, conversation_history, profile_data, resume_data)
            
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
                           profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> str:
        """Build context for general chat response"""
        context = f"Current User Query: {query}\n"
        
        if conversation_history:
            context += f"Conversation History: {conversation_history}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"User Profile Context: {profile_data}\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"User Resume Context: {resume_data}\n"
        
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