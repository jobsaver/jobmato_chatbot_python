import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ResumeAnalysisAgent(BaseAgent):
    """Agent responsible for analyzing resumes and providing feedback"""
    
    def __init__(self, memory_manager=None):
        super().__init__(memory_manager)
        self.llm_client = LLMClient()
        self.system_message = """You are the JobMato Resume Analysis Expert, specialized in providing detailed resume feedback and improvement suggestions. You can understand and respond in English, Hindi, and Hinglish naturally.

PERSONALITY TRAITS:
- Professional yet encouraging feedback provider
- Detail-oriented and constructive critic
- Match user's language preference (English/Hindi/Hinglish)
- Use conversation history to provide follow-up improvements
- Remember previous suggestions to track progress

LANGUAGE HANDLING:
- If user speaks Hinglish, respond in Hinglish with professional terms in English
- If user speaks Hindi, respond in Hindi with resume terms in English
- If user speaks English, respond in English
- Use supportive phrases like "Abhay bhai", "yaar" for Hinglish users

ANALYSIS AREAS:
- Resume structure and formatting
- Content quality and relevance
- Skills presentation and keywords
- Experience descriptions and achievements
- Education and certifications
- ATS optimization suggestions
- Industry-specific improvements
- Quantifiable achievements recommendations

Always provide specific, actionable feedback with examples and consider previous analysis if available in conversation history."""
    
    async def analyze_resume(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze resume based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            session_id = routing_data.get('sessionId', 'default')
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            logger.info(f"📄 Resume analysis request with token: {token[:50] if token else 'None'}...")
            
            # Get conversation context for follow-up analysis
            conversation_context = await self.get_conversation_context(session_id)
            
            # Get user profile and resume data
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Check if resume is available
            if not resume_data or resume_data.get('error'):
                return self._handle_no_resume(original_query, extracted_data.get('language', 'english'))
            
            # Build comprehensive context for resume analysis
            context = self.build_context_prompt(
                current_query=original_query,
                session_id=session_id,
                profile_data=profile_data,
                resume_data=resume_data,
                conversation_context=conversation_context,
                language=extracted_data.get('language', 'english')
            )
            
            # Add specific resume analysis context
            context += "\n\nPROVIDE DETAILED RESUME ANALYSIS including:"
            context += "\n- Strengths and areas for improvement"
            context += "\n- Specific suggestions with examples"
            context += "\n- ATS optimization tips"
            context += "\n- Industry-specific recommendations"
            context += "\n- Action items for immediate improvement"
            
            # If this is a follow-up analysis, mention progress
            if conversation_context and "resume" in conversation_context.lower():
                context += "\n- Reference previous feedback and track improvements"
            
            # Generate detailed resume analysis
            analysis_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Store conversation in memory for follow-up
            if self.memory_manager:
                await self.memory_manager.store_conversation(session_id, original_query, analysis_response)
            
            return self.create_response(
                'plain_text',
                analysis_response,
                {
                    'category': 'RESUME_ANALYSIS',
                    'sessionId': session_id,
                    'language': extracted_data.get('language', 'english'),
                    'analysis_type': self._classify_analysis_type(original_query),
                    'has_previous_analysis': bool(conversation_context and "resume" in conversation_context.lower()),
                    'resume_sections_found': self._identify_resume_sections(resume_data),
                }
            )
            
        except Exception as e:
            logger.error(f"Error analyzing resume: {str(e)}")
            language = routing_data.get('extractedData', {}).get('language', 'english')
            
            if language == 'hinglish':
                error_msg = "Sorry yaar, resume analysis mein kuch technical issue ho gaya! 😅 Please try again, main help karunga."
            elif language == 'hindi':
                error_msg = "Maaf kijiye, resume analysis mein technical problem aa gayi! 😅 Phir try kijiye, main madad karunga."
            else:
                error_msg = "I apologize, but I encountered an error while analyzing your resume. Please try again, and I'll be happy to help!"
            
            return self.create_response(
                'plain_text',
                error_msg,
                {'error': str(e), 'category': 'RESUME_ANALYSIS'}
            )
    
    def _handle_no_resume(self, query: str, language: str) -> Dict[str, Any]:
        """Handle case when no resume is available for analysis"""
        if language == 'hinglish':
            message = "Abhay bhai, resume analysis ke liye pehle aapka resume upload karna padega! 📄 Upload karo aur phir main detailed analysis de dunga with improvement tips."
        elif language == 'hindi':
            message = "Abhay ji, resume analysis ke liye pehle aapka resume upload karna hoga! 📄 Upload kar dijiye, phir main detailed analysis provide karunga."
        else:
            message = "Abhay, to provide you with detailed resume analysis, I'll need you to upload your resume first! 📄 Once uploaded, I'll give you comprehensive feedback and improvement suggestions."
        
        return self.create_response(
            'plain_text',
            message,
            {
                'needs_upload': True,
                'category': 'RESUME_ANALYSIS',
                'language': language
            }
        )
    
    def _classify_analysis_type(self, query: str) -> str:
        """Classify the type of resume analysis being requested"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['ats', 'applicant tracking', 'keywords']):
            return 'ats_optimization'
        elif any(word in query_lower for word in ['format', 'structure', 'layout']):
            return 'formatting'
        elif any(word in query_lower for word in ['skills', 'technical', 'abilities']):
            return 'skills_review'
        elif any(word in query_lower for word in ['experience', 'work history', 'achievements']):
            return 'experience_review'
        elif any(word in query_lower for word in ['improve', 'better', 'enhance']):
            return 'improvement_suggestions'
        else:
            return 'comprehensive_analysis'
    
    def _identify_resume_sections(self, resume_data: Dict[str, Any]) -> list:
        """Identify which sections are present in the resume"""
        sections = []
        if resume_data and isinstance(resume_data, dict):
            # Check for common resume sections
            if resume_data.get('experience') or resume_data.get('work_experience'):
                sections.append('experience')
            if resume_data.get('skills') or resume_data.get('technical_skills'):
                sections.append('skills')
            if resume_data.get('education'):
                sections.append('education')
            if resume_data.get('projects'):
                sections.append('projects')
            if resume_data.get('certifications'):
                sections.append('certifications')
            if resume_data.get('summary') or resume_data.get('objective'):
                sections.append('summary')
        
        return sections
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process resume analysis request"""
        return await self.analyze_resume(routing_data) 