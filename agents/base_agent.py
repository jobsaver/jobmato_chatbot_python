import logging
import requests
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all JobMato agents"""
    
    def __init__(self):
        self.base_url = "https://backend-v1.jobmato.com"
    
    async def call_api(self, endpoint: str, token: str, method: str = 'GET', 
                      params: Optional[Dict[str, Any]] = None, 
                      data: Optional[Dict[str, Any]] = None,
                      base_url: Optional[str] = None) -> Dict[str, Any]:
        """Make API calls to JobMato backend"""
        try:
            url = f"{base_url or self.base_url}{endpoint}"
            headers = {'Authorization': f'Bearer {token}'}
            
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API call failed: {response.status_code} - {response.text}")
                return {'error': f"API call failed: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"Error calling API {endpoint}: {str(e)}")
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