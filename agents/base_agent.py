import logging
import requests
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from utils.jobmato_tools import JobMatoToolsMixin
from utils.response_formatter import ResponseFormatter

logger = logging.getLogger(__name__)

class BaseAgent(ABC, JobMatoToolsMixin):
    """Base class for all JobMato agents with integrated tools"""
    
    def __init__(self, memory_manager=None):
        super().__init__()
        self.base_url = "https://backend-v1.jobmato.com"
        self.memory_manager = memory_manager
        self.response_formatter = ResponseFormatter()
    
    async def get_conversation_context(self, session_id: str, limit: int = 3) -> str:
        """Get recent conversation history for context (last 3 messages for agents)"""
        if not self.memory_manager:
            return ""
        
        try:
            # Get last 3 messages for context using the memory manager
            history = await self.memory_manager.get_conversation_context_for_agents(session_id, limit=limit)
            if not history:
                return ""
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {str(e)}")
            return ""
    
    def build_context_prompt(
        self, 
        current_query: str, 
        session_id: str, 
        profile_data: Dict[str, Any] = None, 
        resume_data: Dict[str, Any] = None,
        conversation_context: str = None,
        language: str = "english"
    ) -> str:
        """Build a comprehensive context prompt for agents"""
        context_parts = []
        
        # Add language preference
        context_parts.append(f"User Language Preference: {language}")
        
        # Add conversation history if available
        if conversation_context:
            context_parts.append(f"Recent Conversation History:\n{conversation_context}")
        
        # Add current query
        context_parts.append(f"Current User Query: {current_query}")
        
        # Add profile context if available
        if profile_data and not profile_data.get('error'):
            context_parts.append(f"User Profile Context: {profile_data}")
        
        # Add resume context if available
        if resume_data and not resume_data.get('error'):
            context_parts.append(f"User Resume Context: {resume_data}")
        
        # Add context instructions
        if language in ['hindi', 'hinglish']:
            context_parts.append("\nIMPORTANT: User prefers Hindi/Hinglish. Please respond naturally in the same language they used. Mix Hindi and English naturally for Hinglish users.")
        
        return "\n\n".join(context_parts)
    
    async def call_api(
        self, 
        endpoint: str, 
        token: str, 
        method: str = 'GET', 
        params: Optional[Dict[str, Any]] = None, 
        data: Optional[Dict[str, Any]] = None,
        base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make API calls to JobMato backend"""
        try:
            api_base_url = self.base_url
            url = f"{api_base_url}{endpoint}"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"🌐 Making API call to: {url}")
            logger.info(f"🔑 Using token: {token[:50]}..." if token else "❌ No token provided")
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, params=params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.info(f"📡 API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ API call successful: {endpoint}")
                return result
            else:
                logger.error(f"❌ API call failed: {response.status_code} - {response.text}")
                return {'error': f"API call failed: {response.status_code}", 'details': response.text}
                
        except Exception as e:
            logger.error(f"❌ Error calling API {endpoint}: {str(e)}")
            return {'error': str(e)}
    
    async def get_profile_data(self, token: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Get user profile information"""
        return await self.call_api('/api/rag/profile', token, base_url=base_url)
    
    async def get_resume_data(self, token: str, base_url: Optional[str] = None) -> Dict[str, Any]:
        """Get user resume information"""
        return await self.call_api('/api/rag/resume', token, base_url=base_url)
    
    @abstractmethod
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the request - must be implemented by subclasses"""
        pass
    
    def create_response(
        self, 
        response_type: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a standardized response format matching Dart ChatBoatHistoryModel"""
        return self.response_formatter.format_chat_response(
            content=content,
            response_type=response_type,
            metadata=metadata
        )