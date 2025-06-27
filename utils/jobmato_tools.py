import logging
import requests
from typing import Dict, Any, List, Optional, Union
import json
from urllib.parse import urlencode
import os
import io
import time
import jwt
from datetime import datetime

logger = logging.getLogger(__name__)

class JobMatoTools:
    """Comprehensive tools for JobMato API operations"""
    
    def __init__(self, base_url: str = "https://backend-v1.jobmato.com"):
        self.base_url = base_url
        self.timeout = 45  # Increased timeout
        self.max_retries = 2  # Add retry mechanism
    
    def _extract_user_info(self, token: str) -> Dict[str, Any]:
        """Extract user information from JWT token for logging"""
        try:
            if not token:
                return {'user_id': 'anonymous', 'email': 'unknown'}
            
            # Decode without verification for logging purposes
            payload = jwt.decode(token, options={"verify_signature": False})
            return {
                'user_id': payload.get('id', 'unknown'),
                'email': payload.get('email', 'unknown'),
                'exp': payload.get('exp', 'unknown')
            }
        except Exception as e:
            logger.warning(f"⚠️ Could not decode token for logging: {str(e)}")
            return {'user_id': 'decode_error', 'email': 'unknown'}
    
    def _make_request(self, method: str, endpoint: str, token: str, 
                     params: Optional[Dict[str, Any]] = None, 
                     data: Optional[Dict[str, Any]] = None,
                     files: Optional[Dict[str, Any]] = None,
                     retry_count: int = 0) -> Dict[str, Any]:
        """Make HTTP request to JobMato API with detailed logging and retry mechanism"""
        
        # Extract user info for logging
        user_info = self._extract_user_info(token)
        request_id = f"{int(time.time() * 1000)}"  # Simple request ID
        
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {
                'Authorization': f'Bearer {token}',
                'Accept': 'application/json',
                'X-Request-ID': request_id  # Add request tracking
            }
            
            # Don't add Content-Type for file uploads
            if not files:
                headers['Content-Type'] = 'application/json'
            
            # Enhanced logging
            logger.info(f"🌐 API Request [{request_id}] - {method} {url}")
            logger.info(f"👤 User: {user_info['user_id']} ({user_info['email']})")
            logger.info(f"🔑 Token: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
            logger.info(f"🔄 Retry: {retry_count}/{self.max_retries}")
            
            if params:
                logger.info(f"📋 Parameters: {json.dumps(params, indent=2)}")
            if data and not files:
                logger.info(f"📄 Data: {json.dumps(data, indent=2) if isinstance(data, dict) else str(data)}")
            
            # Start timing
            start_time = time.time()
            
            # Make the request
            response = None
            if method.upper() == 'GET':
                logger.info(f"📤 Making GET request with timeout: {self.timeout}s")
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                
            elif method.upper() == 'POST':
                if files:
                    # Remove Content-Type for file uploads (let requests set it)
                    headers.pop('Content-Type', None)
                    logger.info(f"📁 Files being sent: {list(files.keys()) if files else 'None'}")
                    logger.info(f"📄 Form data: {data if data else 'None'}")
                    
                    # Debug the actual file content being sent
                    for key, file_info in files.items():
                        if isinstance(file_info, tuple) and len(file_info) >= 2:
                            filename, file_obj = file_info[0], file_info[1]
                            if hasattr(file_obj, 'getvalue'):
                                logger.info(f"📁 File '{key}': {filename}, size: {len(file_obj.getvalue())} bytes")
                            elif hasattr(file_obj, 'read'):
                                # Save current position
                                pos = file_obj.tell() if hasattr(file_obj, 'tell') else 0
                                file_obj.seek(0)
                                content = file_obj.read()
                                file_obj.seek(pos)  # Restore position
                                logger.info(f"📁 File '{key}': {filename}, size: {len(content)} bytes")
                    
                    logger.info(f"📤 Making POST request (file upload) with timeout: {self.timeout}s")
                    response = requests.post(url, headers=headers, files=files, data=data, timeout=self.timeout)
                else:
                    logger.info(f"📤 Making POST request (JSON) with timeout: {self.timeout}s")
                    response = requests.post(url, headers=headers, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Enhanced response logging
            logger.info(f"📡 Response [{request_id}] - Status: {response.status_code}")
            logger.info(f"⏱️ Response Time: {response_time:.2f}s")
            logger.info(f"📊 Response Size: {len(response.content)} bytes")
            logger.info(f"🔗 Response Headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    logger.info(f"✅ Request successful [{request_id}] - {response_time:.2f}s")
                    
                    # Log response structure (limited)
                    if isinstance(result, dict):
                        keys = list(result.keys())[:5]  # First 5 keys only
                        logger.info(f"📋 Response Keys: {keys}")
                        if 'data' in result and isinstance(result['data'], (list, dict)):
                            if isinstance(result['data'], list):
                                logger.info(f"📊 Response Data: Array with {len(result['data'])} items")
                            else:
                                data_keys = list(result['data'].keys())[:5]
                                logger.info(f"📊 Response Data Keys: {data_keys}")
                    
                    return {'success': True, 'data': result, 'response_time': response_time}
                except json.JSONDecodeError as je:
                    logger.warning(f"⚠️ JSON decode error [{request_id}]: {str(je)}")
                    logger.info(f"📄 Raw response: {response.text[:500]}...")
                    return {'success': True, 'data': {'message': 'Request successful'}, 'response_time': response_time}
            else:
                logger.error(f"❌ Request failed [{request_id}] - {response.status_code} in {response_time:.2f}s")
                logger.error(f"📄 Error response: {response.text[:1000]}...")
                return {
                    'success': False, 
                    'error': f"HTTP {response.status_code}: {response.reason}",
                    'details': response.text,
                    'response_time': response_time
                }
                
        except requests.exceptions.Timeout as te:
            response_time = time.time() - start_time if 'start_time' in locals() else self.timeout
            logger.error(f"⏰ Request timeout [{request_id}] after {response_time:.2f}s - {str(te)}")
            
            # Retry logic for timeouts
            if retry_count < self.max_retries:
                logger.info(f"🔄 Retrying request [{request_id}] ({retry_count + 1}/{self.max_retries})")
                time.sleep(1)  # Brief delay before retry
                return self._make_request(method, endpoint, token, params, data, files, retry_count + 1)
            else:
                logger.error(f"❌ Max retries exceeded for [{request_id}]")
                return {
                    'success': False, 
                    'error': f'Request timeout after {self.timeout}s (tried {self.max_retries + 1} times)',
                    'timeout': True,
                    'response_time': response_time
                }
        
        except requests.exceptions.ConnectionError as ce:
            response_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"🔌 Connection error [{request_id}] - {str(ce)}")
            
            # Retry logic for connection errors
            if retry_count < self.max_retries:
                logger.info(f"🔄 Retrying connection [{request_id}] ({retry_count + 1}/{self.max_retries})")
                time.sleep(2)  # Longer delay for connection issues
                return self._make_request(method, endpoint, token, params, data, files, retry_count + 1)
            else:
                return {
                    'success': False, 
                    'error': f'Connection failed: {str(ce)}',
                    'connection_error': True,
                    'response_time': response_time
                }
        
        except Exception as e:
            response_time = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"❌ Unexpected error [{request_id}] - {str(e)}")
            logger.error(f"🔍 Error type: {type(e).__name__}")
            return {
                'success': False, 
                'error': f'Unexpected error: {str(e)}',
                'error_type': type(e).__name__,
                'response_time': response_time
            }
    
    def search_jobs(self, token: str, **kwargs) -> Dict[str, Any]:
        """
        Search for jobs with comprehensive parameters
        
        Available parameters:
        - query: General search query
        - search: Additional search terms
        - job_title: Specific job title
        - company: Company name
        - locations: List or comma-separated string of locations
        - skills: List or comma-separated string of skills
        - industry: Industry filter
        - domain: Domain/field filter
        - job_type: full-time, part-time, internship, contract
        - work_mode: remote, on-site, hybrid
        - experience_min: Minimum years of experience
        - experience_max: Maximum years of experience
        - salary_min: Minimum salary
        - salary_max: Maximum salary
        - internship: Boolean for internship filter
        - limit: Number of results (default: 20)
        - page: Page number (default: 1)
        """
        
        # Build search parameters
        params = {}
        
        # Basic search parameters
        if kwargs.get('query'):
            params['query'] = kwargs['query']
        if kwargs.get('search'):
            params['search'] = kwargs['search']
        if kwargs.get('job_title'):
            params['job_title'] = kwargs['job_title']
        if kwargs.get('company'):
            params['company'] = kwargs['company']
        
        # Location handling
        locations = kwargs.get('locations')
        if locations:
            if isinstance(locations, list):
                params['locations'] = ','.join(locations)
            else:
                params['locations'] = str(locations)
        
        # Skills handling
        skills = kwargs.get('skills')
        if skills:
            if isinstance(skills, list):
                params['skills'] = ','.join(skills)
            else:
                params['skills'] = str(skills)
        
        # Filter parameters
        if kwargs.get('industry'):
            params['industry'] = kwargs['industry']
        if kwargs.get('domain'):
            params['domain'] = kwargs['domain']
        if kwargs.get('job_type'):
            params['job_type'] = kwargs['job_type']
        if kwargs.get('work_mode'):
            params['work_mode'] = kwargs['work_mode']
        
        # Experience parameters
        if kwargs.get('experience_min') is not None:
            params['experience_min'] = kwargs['experience_min']
        if kwargs.get('experience_max') is not None:
            params['experience_max'] = kwargs['experience_max']
        
        # Salary parameters
        if kwargs.get('salary_min') is not None:
            params['salary_min'] = kwargs['salary_min']
        if kwargs.get('salary_max') is not None:
            params['salary_max'] = kwargs['salary_max']
        
        # Special parameters
        if kwargs.get('internship') is not None:
            params['internship'] = str(kwargs['internship']).lower()
        
        # Pagination
        params['limit'] = kwargs.get('limit', 20)
        params['page'] = kwargs.get('page', 1)
        
        logger.info(f"🔍 Job search parameters: {params}")
        
        return self._make_request('GET', '/api/rag/jobs', token, params=params)
    
    def get_user_profile(self, token: str) -> Dict[str, Any]:
        """
        Get user profile information
        """
        logger.info("👤 Fetching user profile")
        result = self._make_request('GET', '/api/rag/profile', token)
        
        # Add detailed logging for profile data
        logger.info(f"👤 Profile API response success: {result.get('success', False)}")
        logger.info(f"👤 Profile API response time: {result.get('response_time', 0):.2f}s")
        
        if result.get('success'):
            data = result.get('data', {})
            logger.info(f"👤 Profile API data type: {type(data)}")
            logger.info(f"👤 Profile API data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if isinstance(data, dict):
                # Log the structure of the profile data
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        logger.info(f"👤 Profile data.{key}: {type(value)} with {len(value)} items")
                    else:
                        logger.info(f"👤 Profile data.{key}: {type(value)} = {str(value)[:100]}...")
        else:
            logger.error(f"❌ Profile API failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def get_user_resume(self, token: str) -> Dict[str, Any]:
        """
        Get user's latest resume information
        """
        logger.info("📄 Fetching user resume")
        result = self._make_request('GET', '/api/rag/resume', token)
        
        # Add detailed logging for resume data
        logger.info(f"📄 Resume API response success: {result.get('success', False)}")
        logger.info(f"📄 Resume API response time: {result.get('response_time', 0):.2f}s")
        
        if result.get('success'):
            data = result.get('data', {})
            logger.info(f"📄 Resume API data type: {type(data)}")
            logger.info(f"📄 Resume API data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if isinstance(data, dict):
                # Log the structure of the resume data
                for key, value in data.items():
                    if isinstance(value, (list, dict)):
                        logger.info(f"📄 Resume data.{key}: {type(value)} with {len(value)} items")
                    else:
                        logger.info(f"📄 Resume data.{key}: {type(value)} = {str(value)[:100]}...")
            
            # Check if we have actual resume content
            has_content = False
            if isinstance(data, dict):
                if data.get('data'):
                    has_content = True
                elif any(key in data for key in ['skills', 'experience', 'education', 'summary', 'content']):
                    has_content = True
            
            logger.info(f"📄 Resume has content: {has_content}")
        else:
            logger.error(f"❌ Resume API failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    def upload_resume(self, token: str, file_path: str) -> Dict[str, Any]:
        """
        Upload a resume file (PDF, DOC, DOCX)
        
        Args:
            token: JWT authentication token
            file_path: Path to the resume file
        """
        try:
            logger.info(f"📤 Uploading resume: {file_path}")
            
            with open(file_path, 'rb') as file:
                files = {'resume': file}
                return self._make_request('POST', '/api/resumes/upload', token, files=files)
                
        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            return {'success': False, 'error': f"File not found: {file_path}"}
        except Exception as e:
            logger.error(f"❌ Upload error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def upload_resume_content(self, token: str, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload resume from file content (for web uploads)
        
        Args:
            token: JWT authentication token
            file_content: File content as bytes
            filename: Original filename
        """
        try:
            logger.info(f"📤 Uploading resume content: {filename}")
            logger.info(f"📊 File size: {len(file_content)} bytes")
            logger.info(f"📝 File content type: {type(file_content)}")
            logger.info(f"📋 First 100 bytes: {file_content[:100] if len(file_content) > 100 else file_content}")
            
            # Create BytesIO object like Postman would do for form-data
            import io
            file_obj = io.BytesIO(file_content)
            file_obj.seek(0)
            
            # Ensure proper content type detection
            content_type = 'application/pdf'
            if filename.lower().endswith('.doc'):
                content_type = 'application/msword'
            elif filename.lower().endswith('.docx'):
                content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            
            # Format exactly like Postman form-data: (name, file_object, content_type)
            files = {'resume': (filename, file_obj, content_type)}
            logger.info(f"📋 Files prepared for upload: {list(files.keys())}")
            logger.info(f"📄 Content type: {content_type}")
            
            return self._make_request('POST', '/api/resumes/upload', token, files=files)
                
        except Exception as e:
            logger.error(f"❌ Upload error: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global instance for easy access
jobmato_tools = JobMatoTools()

class JobMatoToolsMixin:
    """Mixin class to add JobMato tools to agents"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tools = jobmato_tools
    
    async def search_jobs_tool(self, token: str, base_url: str = None, **search_params) -> Dict[str, Any]:
        """Search for jobs using the tools system"""
        # Always use JobMato backend URL for API calls, ignore base_url parameter
        # The base_url parameter is for WebSocket communication, not API calls
        return self.tools.search_jobs(token, **search_params)
    
    async def get_profile_tool(self, token: str, base_url: str = None) -> Dict[str, Any]:
        """Get user profile using the tools system"""
        # Always use JobMato backend URL for API calls, ignore base_url parameter
        return self.tools.get_user_profile(token)
    
    async def get_resume_tool(self, token: str, base_url: str = None) -> Dict[str, Any]:
        """Get user resume using the tools system"""
        # Always use JobMato backend URL for API calls, ignore base_url parameter
        return self.tools.get_user_resume(token)
    
    async def upload_resume_tool(self, token: str, file_path: str = None, 
                                file_content: bytes = None, filename: str = None,
                                base_url: str = None) -> Dict[str, Any]:
        """Upload resume using the tools system"""
        # Always use JobMato backend URL for API calls, ignore base_url parameter
        
        if file_path:
            return self.tools.upload_resume(token, file_path)
        elif file_content and filename:
            return self.tools.upload_resume_content(token, file_content, filename)
        else:
            return {'success': False, 'error': 'Either file_path or file_content+filename required'}

# Helper functions for easy access
def search_jobs(token: str, base_url: str = "https://backend-v1.jobmato.com", **kwargs) -> Dict[str, Any]:
    """Standalone function to search jobs"""
    tools = JobMatoTools(base_url)
    return tools.search_jobs(token, **kwargs)

def get_user_profile(token: str, base_url: str = "https://backend-v1.jobmato.com") -> Dict[str, Any]:
    """Standalone function to get user profile"""
    tools = JobMatoTools(base_url)
    return tools.get_user_profile(token)

def get_user_resume(token: str, base_url: str = "https://backend-v1.jobmato.com") -> Dict[str, Any]:
    """Standalone function to get user resume"""
    tools = JobMatoTools(base_url)
    return tools.get_user_resume(token)

def upload_resume(token: str, file_path: str, base_url: str = "https://backend-v1.jobmato.com") -> Dict[str, Any]:
    """Standalone function to upload resume"""
    tools = JobMatoTools(base_url)
    return tools.upload_resume(token, file_path) 