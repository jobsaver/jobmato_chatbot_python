import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ProjectSuggestionAgent(BaseAgent):
    """Agent responsible for suggesting projects for skill building"""
    
    def __init__(self, memory_manager=None):
        super().__init__(memory_manager)
        self.llm_client = LLMClient()
        self.system_message = """You are the JobMato Project Suggestion Expert, specialized in recommending skill-building projects tailored to career goals. You can understand and respond in English, Hindi, and Hinglish naturally.

PERSONALITY TRAITS:
- Enthusiastic mentor and project guide
- Practical and hands-on approach
- Match user's language preference (English/Hindi/Hinglish)  
- Use conversation history to suggest progressive projects
- Remember previously suggested projects to avoid repetition

LANGUAGE HANDLING:
- If user speaks Hinglish, respond in Hinglish with technical terms in English
- If user speaks Hindi, respond in Hindi with project terms in English
- If user speaks English, respond in English
- Use motivating phrases like "Abhay bhai", "yaar", "boss" for Hinglish users

PROJECT CATEGORIES:
- Beginner-friendly projects for skill foundation
- Intermediate projects for portfolio building
- Advanced projects for expertise demonstration
- Industry-specific projects for targeted learning
- Open-source contribution opportunities
- Personal branding projects

Always provide specific project ideas with:
- Clear objectives and learning outcomes
- Technology stack recommendations
- Step-by-step implementation guidance
- Timeline estimates and milestones
- Portfolio presentation tips

Consider user's current skills, career goals, and conversation history for personalized recommendations."""
    
    async def suggest_projects(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest projects based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            session_id = routing_data.get('sessionId', 'default')
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            logger.info(f"🚀 Project suggestion request with token: {token[:50] if token else 'None'}...")
            
            # Get conversation context for progressive project suggestions
            conversation_context = await self.get_conversation_context(session_id)
            
            # Get user profile and resume data for personalized suggestions
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Build comprehensive context for project suggestions
            context = self.build_context_prompt(
                current_query=original_query,
                session_id=session_id,
                profile_data=profile_data,
                resume_data=resume_data,
                conversation_context=conversation_context,
                language=extracted_data.get('language', 'english')
            )
            
            # Add specific project suggestion context
            context += "\n\nPROVIDE TAILORED PROJECT SUGGESTIONS including:"
            context += "\n- Projects matching user's skill level and goals"
            context += "\n- Clear learning objectives for each project"
            context += "\n- Technology stack and tools needed"
            context += "\n- Implementation timeline and milestones"
            context += "\n- Portfolio presentation tips"
            context += "\n- Next level project progression"
            
            # Check for previously suggested projects
            if conversation_context and any(word in conversation_context.lower() for word in ['project', 'build', 'create']):
                context += "\n- Reference previous project suggestions and suggest next steps or new challenges"
            
            # Generate personalized project suggestions
            suggestions_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Store conversation in memory for progressive suggestions
            if self.memory_manager:
                await self.memory_manager.store_conversation(session_id, original_query, suggestions_response)
            
            return self.create_response(
                'project_suggestions',
                suggestions_response,
                {
                    'category': 'PROJECT_SUGGESTION',
                    'sessionId': session_id,
                    'language': extracted_data.get('language', 'english'),
                    'suggestion_type': self._classify_suggestion_type(original_query),
                    'skill_level': self._determine_skill_level(profile_data, resume_data),
                    'has_previous_suggestions': bool(conversation_context and 'project' in conversation_context.lower())
                }
            )
            
        except Exception as e:
            logger.error(f"Error suggesting projects: {str(e)}")
            language = routing_data.get('extractedData', {}).get('language', 'english')
            
            if language == 'hinglish':
                error_msg = "Sorry yaar, project suggestions dene mein kuch technical issue ho gaya! 😅 Please try again, main help karunga."
            elif language == 'hindi':
                error_msg = "Maaf kijiye, project suggestions dene mein technical problem aa gayi! 😅 Phir try kijiye, main madad karunga."
            else:
                error_msg = "I apologize, but I encountered an error while suggesting projects. Please try again, and I'll be happy to help!"
            
            return self.create_response(
                'plain_text',
                error_msg,
                {'error': str(e), 'category': 'PROJECT_SUGGESTION'}
            )
    
    def _classify_suggestion_type(self, query: str) -> str:
        """Classify the type of project suggestions being requested"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['beginner', 'basic', 'start', 'first']):
            return 'beginner_projects'
        elif any(word in query_lower for word in ['advanced', 'complex', 'challenging']):
            return 'advanced_projects'
        elif any(word in query_lower for word in ['portfolio', 'showcase', 'demo']):
            return 'portfolio_projects'
        elif any(word in query_lower for word in ['web', 'website', 'frontend', 'backend']):
            return 'web_development'
        elif any(word in query_lower for word in ['mobile', 'app', 'android', 'ios']):
            return 'mobile_development'
        elif any(word in query_lower for word in ['data', 'machine learning', 'ai', 'analytics']):
            return 'data_science'
        elif any(word in query_lower for word in ['open source', 'contribute', 'github']):
            return 'open_source'
        else:
            return 'general_suggestions'
    
    def _determine_skill_level(self, profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> str:
        """Determine user's skill level based on profile and resume"""
        # Default to intermediate if no data
        if not profile_data and not resume_data:
            return 'intermediate'
        
        # Check experience level
        experience_indicators = []
        
        if profile_data and not profile_data.get('error'):
            # Look for experience indicators in profile
            if 'experience' in str(profile_data).lower():
                experience_indicators.append('has_experience')
        
        if resume_data and not resume_data.get('error'):
            # Look for experience indicators in resume
            resume_str = str(resume_data).lower()
            if any(word in resume_str for word in ['senior', 'lead', 'manager', 'architect']):
                return 'advanced'
            elif any(word in resume_str for word in ['junior', 'intern', 'trainee', 'fresher']):
                return 'beginner'
            elif 'experience' in resume_str or 'project' in resume_str:
                return 'intermediate'
        
        return 'intermediate'  # Default
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process project suggestion request"""
        return await self.suggest_projects(routing_data) 