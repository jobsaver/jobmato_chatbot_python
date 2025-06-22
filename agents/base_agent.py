import logging
import requests
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from utils.jobmato_tools import JobMatoToolsMixin

logger = logging.getLogger(__name__)

class BaseAgent(ABC, JobMatoToolsMixin):
    """Base class for all JobMato agents with integrated tools"""
    
    def __init__(self):
        super().__init__()
        self.base_url = "https://backend-v1.jobmato.com"
    
    async def call_api(self, endpoint: str, token: str, method: str = 'GET', 
                      params: Optional[Dict[str, Any]] = None, 
                      data: Optional[Dict[str, Any]] = None,
                      base_url: Optional[str] = None) -> Dict[str, Any]:
        """Make API calls to JobMato backend"""
        try:
            # Always use the JobMato backend URL for API calls
            # The base_url parameter is for WebSocket communication, not JobMato API calls
            api_base_url = self.base_url  # Always use https://backend-v1.jobmato.com
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
    
    def create_response(self, response_type: str, content: str, 
                       metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a standardized response format"""
        return {
            'type': response_type,
            'content': content,
            'metadata': metadata or {}
        } 