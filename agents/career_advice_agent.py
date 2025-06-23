import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class CareerAdviceAgent(BaseAgent):
    """Agent responsible for providing career advice and guidance"""
    
    def __init__(self, memory_manager=None):
        super().__init__(memory_manager)
        self.llm_client = LLMClient()
        self.system_message = """
        You are the JobMato Career Advisor, a friendly and knowledgeable career guidance expert. You can understand and respond in English, Hindi, and Hinglish naturally.

        PERSONALITY TRAITS:
        - Supportive and encouraging mentor
        - Practical and actionable advice giver
        - Match user's language preference (English/Hindi/Hinglish)
        - Use conversation history to provide continuous guidance
        - Remember previous advice given to build upon it

        LANGUAGE HANDLING:
        - If user speaks Hinglish, respond in Hinglish with career terms in English
        - If user speaks Hindi, respond in Hindi with professional terms in English
        - If user speaks English, respond in English
        - Use encouraging phrases like "Abhay bhai", "yaar", "boss" for Hinglish users

        ADVICE AREAS:
        - Career path planning and transitions
        - Skill development recommendations
        - Industry insights and trends
        - Professional networking guidance
        - Interview preparation tips
        - Salary negotiation advice
        - Work-life balance strategies
        - Personal branding and LinkedIn optimization

        Always provide specific, actionable steps and consider the user's background from their profile/resume and conversation history.
        """
        self.industry_trends = {
            "AI & Machine Learning": {
                "impact": "high",
                "skills": ["Python", "TensorFlow", "PyTorch", "Machine Learning", "Deep Learning", "NLP", "Computer Vision"],
                "roles": ["ML Engineer", "AI Researcher", "Data Scientist", "AI Product Manager"],
                "description": "AI and ML are transforming industries with applications in automation, prediction, and decision-making."
            },
            "Remote Work Technologies": {
                "impact": "high",
                "skills": ["Cloud Computing", "DevOps", "Collaboration Tools", "Security", "Virtual Infrastructure"],
                "roles": ["Cloud Architect", "DevOps Engineer", "Remote Team Lead", "Virtual Infrastructure Specialist"],
                "description": "Remote work technologies are enabling global collaboration and distributed teams."
            },
            "Cybersecurity": {
                "impact": "medium",
                "skills": ["Security Analysis", "Network Security", "Ethical Hacking", "Risk Assessment", "Compliance"],
                "roles": ["Security Engineer", "Cybersecurity Analyst", "Security Architect", "Compliance Officer"],
                "description": "Cybersecurity is crucial for protecting digital assets and ensuring data privacy."
            }
        }

    def _extract_user_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        if not profile_data or profile_data.get("error"):
            return {}

        personal_info = profile_data.get("personalInfo", {})
        education = profile_data.get("education", [])
        experience = profile_data.get("workExperience", [])
        skills = profile_data.get("skills", [])

        return {
            "name": personal_info.get("fullName"),
            "email": personal_info.get("email"),
            "currentRole": personal_info.get("role"),
            "gender": personal_info.get("gender"),
            "skills": skills,
            "education": [
                {
                    "course": e.get("course"),
                    "university": e.get("university"),
                    "from": e.get("from"),
                    "to": e.get("to"),
                    "graduated": e.get("graduated"),
                    "description": e.get("description")
                } for e in education
            ],
            "experience": [
                {
                    "company": w.get("company"),
                    "role": w.get("role"),
                    "from": w.get("form_year"),
                    "to": w.get("to_year"),
                    "work_here": w.get("work_here"),
                    "description": w.get("description")
                } for w in experience
            ],
            "socialLinks": profile_data.get("socialLinks", {})
        }

    
    async def provide_advice(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide career advice based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            session_id = routing_data.get('sessionId', 'default')
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            logger.info(f"💼 Career advice request with token: {token[:50] if token else 'None'}...")
            
            # Get conversation context for continuity
            conversation_context = await self.get_conversation_context(session_id)
            
            # Get user profile and resume data for personalized advice
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            user_profile = self._extract_user_profile(profile_data)

            # Build comprehensive context for personalized advice
            context = self.build_context_prompt(
                current_query=original_query,
                session_id=session_id,
                profile_data=profile_data,
                resume_data=resume_data,
                conversation_context=conversation_context,
                language=extracted_data.get('language', 'english')
            )
            
            # Add specific career advice context
            context += "\n\nPROVIDE SPECIFIC CAREER ADVICE based on:"
            context += "\n- User's current situation and background"
            context += "\n- Previous conversation context"
            context += "\n- Current market trends and opportunities"
            context += "\n- Actionable next steps"
            
            # Generate personalized career advice
            advice_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Store conversation in memory for continuity
            if self.memory_manager:
                await self.memory_manager.store_conversation(session_id, original_query, advice_response)
            
            return self.create_response(
                'career_advice',
                advice_response,
                {
                    'trends': self.industry_trends,
                    'category': 'CAREER_ADVICE',
                    'user_profile': user_profile,
                    'sessionId': session_id,
                    'language': extracted_data.get('language', 'english'),
                    'advice_type': self._classify_advice_type(original_query),
                    'has_profile': bool(profile_data and not profile_data.get('error')),
                    'has_resume': bool(resume_data and not resume_data.get('error'))
                }
            )
            
        except Exception as e:
            logger.error(f"Error providing career advice: {str(e)}")
            language = routing_data.get('extractedData', {}).get('language', 'english')
            
            if language == 'hinglish':
                error_msg = "Sorry yaar, career advice dene mein kuch technical issue ho gaya! 😅 Please try again, main help karunga."
            elif language == 'hindi':
                error_msg = "Maaf kijiye, career advice dene mein technical problem aa gayi! 😅 Phir try kijiye, main madad karunga."
            else:
                error_msg = "I apologize, but I encountered an error while providing career advice. Please try again, and I'll be happy to help!"
            
            return self.create_response(
                'plain_text',
                error_msg,
                {'error': str(e), 'category': 'CAREER_ADVICE'}
            )
    
    def _classify_advice_type(self, query: str) -> str:
        """Classify the type of career advice being requested"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['switch', 'change', 'transition', 'shift']):
            return 'career_transition'
        elif any(word in query_lower for word in ['skill', 'learn', 'course', 'training']):
            return 'skill_development'
        elif any(word in query_lower for word in ['interview', 'preparation', 'tips']):
            return 'interview_prep'
        elif any(word in query_lower for word in ['salary', 'negotiate', 'pay', 'compensation']):
            return 'salary_negotiation'
        elif any(word in query_lower for word in ['network', 'linkedin', 'connections']):
            return 'networking'
        elif any(word in query_lower for word in ['resume', 'cv', 'profile']):
            return 'resume_improvement'
        else:
            return 'general_guidance'
    
    def _build_advice_context(self, query: str, extracted_data: Dict[str, Any], 
                             profile_data: Dict[str, Any], resume_data: Dict[str, Any], job_data: Dict[str, Any] = None) -> str:
        """Build context for career advice generation"""
        context = f"User Query: {query}\n"
        context += f"Career Stage: {extracted_data.get('career_stage', 'not specified')}\n"
        context += f"Industry: {extracted_data.get('industry', 'not specified')}\n"
        context += f"Specific Question: {extracted_data.get('specific_question', 'general advice')}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"User Profile Data: {profile_data}\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"User Resume Data: {resume_data}\n"
        
        if job_data:
            context += f"Job Market Data: {job_data}\n"
        
        return context
    
    def _extract_job_search_params(self, query: str, extracted_data: Dict[str, Any], 
                                  profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job search parameters for career advice context"""
        params = {'limit': 10}  # Smaller limit for advice context
        
        # Use extracted data from query classifier
        if extracted_data.get('industry'):
            params['industry'] = extracted_data['industry']
        
        # Use profile data if available
        if profile_data and not profile_data.get('error'):
            # Extract relevant fields from profile
            if 'skills' in profile_data:
                params['skills'] = profile_data['skills']
            if 'location' in profile_data:
                params['locations'] = profile_data['location']
        
        # Use resume data if available  
        if resume_data and not resume_data.get('error'):
            # Extract skills or job titles from resume
            if 'skills' in resume_data:
                params['skills'] = resume_data['skills']
        
        # Extract from query text
        query_lower = query.lower()
        if 'remote' in query_lower:
            params['work_mode'] = 'remote'
        if 'internship' in query_lower:
            params['internship'] = True
        
        return params if len(params) > 1 else None  # Only return if we have actual search criteria
    
    def _format_advice_response(self, advice_result: str, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the career advice response"""
        extracted_data = routing_data.get('extractedData', {})
        
        metadata = {
            'careerStage': extracted_data.get('career_stage', 'not specified'),
            'industry': extracted_data.get('industry', 'not specified'),
            'specificQuestion': extracted_data.get('specific_question', 'general advice'),
            'adviceDate': routing_data.get('timestamp', '')
        }
        
        return self.create_response('career_advice', advice_result, metadata)
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process career advice request"""
        return await self.provide_advice(routing_data) 