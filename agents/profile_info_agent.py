import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ProfileInfoAgent(BaseAgent):
    """Agent responsible for managing and displaying profile information"""
    
    def __init__(self, memory_manager=None):
        super().__init__(memory_manager)
        self.llm_client = LLMClient()
        self.system_message = """You are the JobMato Profile Manager, specialized in helping users understand and manage their professional profile information. You can understand and respond in English, Hindi, and Hinglish naturally.

PERSONALITY TRAITS:
- Helpful and informative profile guide
- Privacy-conscious and professional
- Match user's language preference (English/Hindi/Hinglish)
- Use conversation history to provide contextual profile insights
- Remember user's name and personal details from conversation

LANGUAGE HANDLING:
- If user speaks Hinglish, respond in Hinglish with professional terms in English
- If user speaks Hindi, respond in Hindi with profile terms in English
- If user speaks English, respond in English
- Use friendly phrases like "Abhay bhai", "yaar" for Hinglish users

RESPONSE FORMATTING:
- Use markdown formatting for well-structured profile information
- Use headings (## or ###) to organize profile sections
- Use bullet points (-) for lists and details
- Use **bold** for emphasis on important information
- Use `code blocks` for technical skills and technologies
- Structure your response with clear sections like:
  - ## Profile Summary
  - ## Professional Experience
  - ## Technical Skills
  - ## Education & Certifications
  - ## Profile Completeness
  - ## Improvement Suggestions

PROFILE AREAS:
- Personal information and contact details
- Professional experience and skills
- Education and certifications
- Career preferences and goals
- Resume and portfolio status
- Account settings and privacy

Always provide clear, organized information about the user's profile and suggest improvements or updates when relevant. Consider conversation history for personalized responses."""
    
    async def get_profile_info(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get and display profile information based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            session_id = routing_data.get('sessionId', 'default')
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            logger.info(f"👤 Profile info request with token: {token[:50] if token else 'None'}...")
            
            # Get conversation context for personalized responses
            conversation_context = await self.get_conversation_context(session_id)
            
            # Get user profile and resume data
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Build comprehensive context for profile response
            context = self.build_context_prompt(
                current_query=original_query,
                session_id=session_id,
                profile_data=profile_data,
                resume_data=resume_data,
                conversation_context=conversation_context,
                language=extracted_data.get('language', 'english')
            )
            
            # Add specific profile context
            context += "\n\nPROVIDE PROFILE INFORMATION including:"
            context += "\n- Summary of user's professional profile"
            context += "\n- Key skills and experience highlights"
            context += "\n- Profile completeness assessment"
            context += "\n- Suggestions for profile improvement"
            context += "\n- Next steps for career development"
            
            # Handle specific profile queries
            query_type = self._classify_profile_query(original_query)
            if query_type == 'name_info':
                context += "\n- Focus on personal information and name details"
            elif query_type == 'skills_info':
                context += "\n- Focus on skills and technical abilities"
            elif query_type == 'experience_info':
                context += "\n- Focus on work experience and achievements"
            elif query_type == 'completeness':
                context += "\n- Focus on profile completeness and missing information"
            
            # Generate personalized profile response
            profile_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Store conversation in memory
            if self.memory_manager:
                await self.memory_manager.store_conversation(session_id, original_query, profile_response)
            
            return self.create_response(
                'profile_info',
                profile_response,
                {
                    'category': 'PROFILE_INFO',
                    'sessionId': session_id,
                    'language': extracted_data.get('language', 'english'),
                    'query_type': query_type,
                    'has_profile': bool(profile_data and not profile_data.get('error')),
                    'has_resume': bool(resume_data and not resume_data.get('error')),
                    'profile_completeness': self._assess_profile_completeness(profile_data, resume_data),
                }
            )
            
        except Exception as e:
            logger.error(f"Error getting profile info: {str(e)}")
            language = routing_data.get('extractedData', {}).get('language', 'english')
            
            if language == 'hinglish':
                error_msg = "Sorry yaar, profile info nikalne mein kuch technical issue ho gaya! 😅 Please try again, main help karunga."
            elif language == 'hindi':
                error_msg = "Maaf kijiye, profile information mein technical problem aa gayi! 😅 Phir try kijiye, main madad karunga."
            else:
                error_msg = "I apologize, but I encountered an error while retrieving your profile information. Please try again, and I'll be happy to help!"
            
            return self.create_response(
                'plain_text',
                error_msg,
                {'error': str(e), 'category': 'PROFILE_INFO'}
            )
    
    def _classify_profile_query(self, query: str) -> str:
        """Classify the type of profile query being made"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['name', 'naam', 'personal', 'contact']):
            return 'name_info'
        elif any(word in query_lower for word in ['skills', 'abilities', 'technical', 'expertise']):
            return 'skills_info'
        elif any(word in query_lower for word in ['experience', 'work', 'job', 'career']):
            return 'experience_info'
        elif any(word in query_lower for word in ['complete', 'missing', 'update', 'improve']):
            return 'completeness'
        elif any(word in query_lower for word in ['education', 'degree', 'qualification']):
            return 'education_info'
        else:
            return 'general_profile'
    
    def _assess_profile_completeness(self, profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess how complete the user's profile is"""
        completeness = {
            'score': 0,
            'total': 100,
            'missing_sections': [],
            'suggestions': []
        }
        
        # Check profile data
        if profile_data and not profile_data.get('error'):
            if profile_data.get('name'):
                completeness['score'] += 10
            else:
                completeness['missing_sections'].append('name')
            
            if profile_data.get('skills'):
                completeness['score'] += 20
            else:
                completeness['missing_sections'].append('skills')
            
            if profile_data.get('experience'):
                completeness['score'] += 20
            else:
                completeness['missing_sections'].append('experience')
            
            if profile_data.get('location'):
                completeness['score'] += 10
            else:
                completeness['missing_sections'].append('location')
        else:
            completeness['missing_sections'].extend(['name', 'skills', 'experience', 'location'])
        
        # Check resume data
        if resume_data and not resume_data.get('error'):
            completeness['score'] += 40
        else:
            completeness['missing_sections'].append('resume')
        
        # Generate suggestions
        if 'resume' in completeness['missing_sections']:
            completeness['suggestions'].append('Upload your resume for better job matching')
        if 'skills' in completeness['missing_sections']:
            completeness['suggestions'].append('Add your technical skills and competencies')
        if 'experience' in completeness['missing_sections']:
            completeness['suggestions'].append('Update your work experience details')
        
        return completeness
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process profile info request"""
        return await self.get_profile_info(routing_data) 