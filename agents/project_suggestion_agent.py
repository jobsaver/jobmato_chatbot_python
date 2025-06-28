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

RESPONSE FORMATTING:
- Use markdown formatting for well-structured project suggestions
- Use headings (## or ###) to organize project categories
- Use bullet points (-) for features, requirements, and learning outcomes
- Use **bold** for project names and important milestones
- Use `code blocks` for technology stacks and tools
- Structure your response with clear sections like:
  - ## Recommended Projects
  - ## Project 1: [Name]
  - ### Technology Stack
  - ### Learning Outcomes
  - ### Implementation Steps
  - ## Timeline & Milestones
  - ## Portfolio Tips

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
            
            # Storage is handled by app.py to avoid duplication

            final =  self.create_response(
                'project_suggestion',
                suggestions_response,
                {
                    'category': 'PROJECT_SUGGESTION',
                    'sessionId': session_id,
                    'language': extracted_data.get('language', 'english'),
                    'suggestion_type': self._classify_suggestion_type(original_query),
                    'skillLevel': self._determine_skill_level(profile_data, resume_data),
                    'has_previous_suggestions': bool(conversation_context and 'project' in conversation_context.lower()),
                    "focusArea": None,
                    'suggestedProjects': self._get_sample_projects(self._determine_skill_level(profile_data, resume_data))
                }
            )
            
            return final
        
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
    
    def _get_sample_projects(self, skill_level: str) -> list:
        """Get sample project suggestions based on skill level"""
        if skill_level == 'beginner':
            return [
                {
                    'title': 'Personal Portfolio Website',
                    'description': 'Build a responsive portfolio website using HTML, CSS, and JavaScript to showcase your skills and projects.',
                    'difficulty': 'beginner',
                    'learningOutcomes': [
                        'HTML5 and CSS3 fundamentals',
                        'Responsive design principles',
                        'Basic JavaScript functionality',
                        'Git version control basics'
                    ]
                },
                {
                    'title': 'Todo List Application',
                    'description': 'Create a simple todo list app with add, edit, delete, and mark complete functionality.',
                    'difficulty': 'beginner',
                    'learningOutcomes': [
                        'DOM manipulation',
                        'Event handling',
                        'Local storage usage',
                        'Basic CRUD operations'
                    ]
                },
                {
                    'title': 'Weather App',
                    'description': 'Build a weather application that fetches data from a weather API and displays current conditions.',
                    'difficulty': 'beginner',
                    'learningOutcomes': [
                        'API integration',
                        'Async/await concepts',
                        'JSON data handling',
                        'Error handling basics'
                    ]
                }
            ]
        elif skill_level == 'advanced':
            return [
                {
                    'title': 'Full-Stack E-commerce Platform',
                    'description': 'Develop a complete e-commerce solution with user authentication, payment processing, and admin dashboard.',
                    'difficulty': 'advanced',
                    'learningOutcomes': [
                        'Full-stack development',
                        'Database design and optimization',
                        'Payment gateway integration',
                        'Security best practices'
                    ]
                },
                {
                    'title': 'Real-time Chat Application',
                    'description': 'Build a real-time messaging app with WebSocket connections, user presence, and file sharing.',
                    'difficulty': 'advanced',
                    'learningOutcomes': [
                        'WebSocket implementation',
                        'Real-time data handling',
                        'File upload and processing',
                        'Scalable architecture design'
                    ]
                },
                {
                    'title': 'Machine Learning Model Deployment',
                    'description': 'Create a web application that serves machine learning models with real-time predictions and model monitoring.',
                    'difficulty': 'advanced',
                    'learningOutcomes': [
                        'ML model deployment',
                        'API design for ML services',
                        'Model monitoring and logging',
                        'Performance optimization'
                    ]
                }
            ]
        else:  # intermediate
            return [
                {
                    'title': 'Blog Platform with CMS',
                    'description': 'Develop a content management system for a blog with user authentication, rich text editor, and SEO optimization.',
                    'difficulty': 'intermediate',
                    'learningOutcomes': [
                        'Backend API development',
                        'Database relationships',
                        'Authentication and authorization',
                        'SEO best practices'
                    ]
                },
                {
                    'title': 'Task Management Dashboard',
                    'description': 'Create a project management tool with task tracking, team collaboration, and progress visualization.',
                    'difficulty': 'intermediate',
                    'learningOutcomes': [
                        'State management',
                        'Data visualization',
                        'Team collaboration features',
                        'Project planning concepts'
                    ]
                },
                {
                    'title': 'Social Media Analytics Tool',
                    'description': 'Build an analytics dashboard that tracks social media metrics and provides insights and reporting.',
                    'difficulty': 'intermediate',
                    'learningOutcomes': [
                        'Data analysis and visualization',
                        'Third-party API integration',
                        'Dashboard design principles',
                        'Reporting and insights generation'
                    ]
                }
            ]
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process project suggestion request"""
        return await self.suggest_projects(routing_data) 