import logging
import random
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
        # Track recent responses to avoid repetition
        self.recent_responses = []
        self.max_recent_responses = 10
        
        # Humorous out-of-context responses in multiple languages
        self.casual_responses = [
            # English responses
            "Haha, I'm JobMato's career buddy! 🤖 While I'd love to chat about everything, I'm really passionate about helping with your career. What's cooking in your professional life?",
            "LOL! I'm like that friend who only talks about work... but in a good way! 😄 I'm here to help with jobs, resumes, career advice. What can I help you achieve today?",
            "You caught me! I'm JobMato's AI assistant, and I'm obsessed with careers! 🎯 Think of me as your professional wingman. What career goals are we tackling?",
            "Guilty as charged! I'm the career-obsessed AI of JobMato! 🚀 I live and breathe job searches, resume tips, and career advice. Ready to level up your career?",
            "Hehe, I'm JobMato's career companion! 💼 I might not know much about other stuff, but I'm your go-to for all things professional. What's your next career move?",
            
            # Hinglish responses  
            "Arre yaar, main JobMato ka career assistant hoon! 😊 Baaki sab toh theek hai, but mera passion hai career help karna. Kya career goals hai tumhare?",
            "Haha bhai, main sirf career ke baare mein baat karta hoon! 🤓 JobMato ka AI hoon, job search aur resume mein expert. Kya help chahiye?",
            "Dekho, main JobMato ka career buddy hoon! 🎉 Other topics mein thoda weak hoon, but career advice mein strong! Kya plan hai professional life mein?",
            "Arre boss, main career-obsessed AI hoon JobMato ka! 💪 Job hunting, resume tips, career guidance - ye sab mera area hai. Kya help kar sakoon?",
            "Yaar, main JobMato ka career specialist hoon! 😄 Dusre topics mein average hoon, but career mein top class! Batao kya chahiye?",
            
            # Hindi responses
            "Namaste! Main JobMato ka career sahayak hoon! 🙏 Mera kaam hai aapki professional life mein madad karna. Kya career sahaayata chahiye?",
            "Haan bhai, main career ke liye dedicated AI hoon! 💼 JobMato mein aapka dost. Naukri, resume, career advice - sab kuch! Kya help karna hai?",
            "Main JobMato ka AI assistant hoon, career expert! 🎯 Aapki professional journey mein guide karna mera passion hai. Kya goals hain?",
        ]
        
        # Name responses (when asked about name)
        self.name_responses = [
            "Main JobMato Assistant hoon! 🤖 Aap mujhe JM, JobMato AI, ya phir Career Buddy bhi keh sakte ho! What should I call you?",
            "I'm your friendly JobMato Assistant! 😊 You can call me JM for short, or just your career buddy! Aur aapka naam kya hai?",
            "JobMato Assistant here! 🎉 But you can give me a nickname if you want - Career Guru, Job Buddy, kuch bhi! What's your name?",
            "Haha, main JobMato ka AI assistant hoon! 💼 Officially JobMato Assistant, but friends call me JM. Tumhara naam kya hai yaar?",
            "I'm the JobMato Assistant - your personal career companion! 🚀 Call me whatever feels right - JM, Career AI, Job Helper! And you are?",
        ]
        
        self.system_message = """You are the JobMato Assistant, a friendly and humorous AI career companion. You can understand and respond in English, Hindi, and Hinglish naturally.

PERSONALITY TRAITS:
- Friendly, humorous, and slightly witty
- Career-obsessed but in a charming way
- Uses emojis appropriately 
- Can switch between English, Hindi, and Hinglish based on user's language
- Admits when topics are outside your expertise but redirects with humor
- Never repetitive - always vary your responses

LANGUAGE HANDLING:
- If user speaks in Hindi/Hinglish, respond in the same language
- Use natural code-switching for Hinglish speakers
- Keep professional terms in English even in Hindi responses (e.g., "resume", "job", "career")

PROFESSIONAL SCOPE: You specialize in:
- Career guidance and professional development
- Job searching and opportunities  
- Resume and CV assistance
- Skill development and learning
- Industry insights and trends
- Professional networking advice
- Interview preparation
- Salary and compensation discussions
- Workplace advice and professional conduct

CONTENT BOUNDARIES:
- For out-of-scope topics: Respond with humor but redirect to career topics
- Never be rude or dismissive - always friendly
- Don't engage with inappropriate content - redirect professionally
- Vary your responses - never repeat the same answer

AVAILABLE TOOLS - Use intelligently based on user needs:
1. **Profile Tool**: Get user profile data (experience, skills, preferences)
2. **Resume Tool**: Get user resume/CV information 
3. **Job Search Tool**: Search for jobs when user asks about opportunities
4. **Resume Upload Tool**: Help users upload/update their resume

RESPONSE STYLE:
- Keep responses conversational and engaging
- Use humor appropriately
- Match user's language preference
- Include relevant emojis
- Always end with a career-related question or offer to help

Handle conversations naturally while steering toward professional development. If asked about your name or identity, respond warmly and ask about their career goals."""
    
    async def handle_chat(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general chat based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            logger.info(f"💬 General chat with token: {token[:50] if token else 'None'}...")
            logger.info(f"🌐 Using base URL: {base_url}")
            original_query = routing_data.get('originalQuery', '')
            session_id = routing_data.get('sessionId', 'default')
            extracted_data = routing_data.get('extractedData', {})
            
            # Check for content filtering flags
            if extracted_data.get('content_filtered'):
                return self._get_filtered_response()
            
            # Handle casual chat (name questions, greetings, etc.)
            if extracted_data.get('casual_chat'):
                return self._handle_casual_chat(original_query, extracted_data.get('language', 'english'))
            
            if extracted_data.get('out_of_scope'):
                return self._get_varied_out_of_scope_response(extracted_data.get('language', 'english'))
            
            # Get conversation history
            conversation_history = ""
            if self.memory_manager:
                conversation_history = await self.memory_manager.get_conversation_history(session_id)
            
            # Intelligently determine which tools to use based on query
            profile_data = None
            resume_data = None
            job_data = None
            
            query_lower = original_query.lower()
            
            # Always get profile/resume for personalization unless it's a simple greeting
            if not any(greeting in query_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'namaste', 'halo']):
                profile_data = await self.get_profile_data(token, base_url)
                resume_data = await self.get_resume_data(token, base_url)
            
            # Check if user is asking for personalized help but no resume is available
            wants_personalized = any(keyword in query_lower for keyword in [
                'my career', 'my resume', 'my experience', 'my skills', 'help me',
                'what should i', 'advice for me', 'about me', 'my background',
                'recommend for me', 'suggest for me', 'personalized', 'tailored',
                'mera career', 'mera resume', 'mere skills', 'meri help'
            ])
            
            if wants_personalized and (not resume_data or resume_data.get('error')):
                return self._get_upload_prompt_response(extracted_data.get('language', 'english'))
            
            # Use job search tool if query is about jobs, market, opportunities
            if any(keyword in query_lower for keyword in [
                'job', 'jobs', 'market', 'opportunities', 'hiring', 'openings', 
                'available', 'positions', 'roles', 'career', 'work', 'employment',
                'naukri', 'kaam', 'vacancy'
            ]):
                logger.info("🔍 Job search relevant for this general chat query")
                search_params = self._extract_general_job_search_params(original_query, profile_data, resume_data)
                if search_params:
                    job_search_result = await self.search_jobs_tool(token, base_url, **search_params)
                    if job_search_result.get('success'):
                        job_data = job_search_result.get('data')
                        logger.info(f"✅ Found {len(job_data.get('jobs', []))} jobs for general chat context")
            
            # Build context for chat response
            context = self._build_chat_context(original_query, conversation_history, profile_data, resume_data, job_data, extracted_data.get('language', 'english'))
            
            # Generate response using LLM
            chat_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Store conversation in memory
            if self.memory_manager:
                await self.memory_manager.store_conversation(session_id, original_query, chat_response)
            
            # Track this response to avoid repetition
            self._track_response(chat_response)
            
            # Format and return response
            return self._format_chat_response(chat_response, routing_data)
            
        except Exception as e:
            logger.error(f"Error handling general chat: {str(e)}")
            return self.create_response(
                'plain_text',
                'Oops! Kuch technical issue ho gaya hai. 😅 But don\'t worry, I\'m still here to help with your career goals! Kya kar sakte hain aapke liye?',
                {'error': str(e)}
            )
    
    def _handle_casual_chat(self, query: str, language: str) -> Dict[str, Any]:
        """Handle casual chat like name questions, greetings"""
        query_lower = query.lower()
        
        # Handle name questions
        if any(word in query_lower for word in ['name', 'naam', 'tumhara naam', 'your name', 'who are you', 'kaun ho']):
            response = self._get_varied_response(self.name_responses)
        else:
            # Handle other casual chat
            response = self._get_varied_response(self.casual_responses)
        
        return self.create_response(
            'plain_text',
            response,
            {'chat_type': 'casual', 'language': language}
        )
    
    def _get_varied_out_of_scope_response(self, language: str) -> Dict[str, Any]:
        """Get a varied response for out-of-scope queries"""
        response = self._get_varied_response(self.casual_responses)
        
        return self.create_response(
            'plain_text',
            response,
            {'filtered': True, 'reason': 'out_of_scope', 'language': language}
        )
    
    def _get_filtered_response(self) -> Dict[str, Any]:
        """Get response for filtered content"""
        responses = [
            "Hey! Let's keep things professional and career-focused! 😊 I'm here to help with jobs, resumes, and career advice. What can I help you achieve?",
            "Arre yaar, let's talk about careers and professional stuff! 💼 I'm your JobMato assistant for job hunting and career growth. Kya help chahiye?",
            "I prefer talking about careers and professional development! 🎯 I'm here to help with job searches, resume tips, and career advice. Ready to level up?"
        ]
        
        return self.create_response(
            'plain_text',
            self._get_varied_response(responses),
            {'filtered': True, 'reason': 'inappropriate_content'}
        )
    
    def _get_upload_prompt_response(self, language: str) -> Dict[str, Any]:
        """Get response prompting for resume upload"""
        if language == 'hindi':
            responses = [
                "Personalized advice dene ke liye mujhe aapka resume chahiye! 📄 Upload kar dijiye taki main aapko best guidance de sakoon.",
                "Aapke background ke baare mein jaanne ke liye resume upload karna padega! 🚀 Phir main tailored career advice de sakuunga.",
            ]
        elif language == 'hinglish':
            responses = [
                "Yaar, personalized help ke liye resume upload karo! 📄 Tab main proper advice de sakuunga aapko.",
                "Bhai, aapka resume chahiye mujhe! Upload karo taki main best career guidance de sakoon! 🎯",
            ]
        else:
            responses = [
                "I'd love to give you personalized advice! 📄 Please upload your resume so I can understand your background and provide tailored recommendations.",
                "For the best personalized guidance, I'll need your resume! 🚀 Upload it and I'll give you customized career advice.",
            ]
        
        return self.create_response(
            'plain_text',
            self._get_varied_response(responses),
            {'needs_upload': True, 'chat_type': 'personalized_help', 'language': language}
        )
    
    def _get_varied_response(self, responses_list: list) -> str:
        """Get a varied response that hasn't been used recently"""
        available_responses = [r for r in responses_list if r not in self.recent_responses]
        
        if not available_responses:
            # If all responses have been used recently, reset and use any
            self.recent_responses = []
            available_responses = responses_list
        
        return random.choice(available_responses)
    
    def _track_response(self, response: str):
        """Track response to avoid repetition"""
        # Store first 100 characters as identifier
        response_id = response[:100]
        self.recent_responses.append(response_id)
        
        # Keep only recent responses
        if len(self.recent_responses) > self.max_recent_responses:
            self.recent_responses = self.recent_responses[-self.max_recent_responses:]
    
    def _build_chat_context(self, query: str, conversation_history: str, 
                           profile_data: Dict[str, Any], resume_data: Dict[str, Any], job_data: Dict[str, Any], language: str) -> str:
        """Build context for general chat response"""
        context = f"Current User Query: {query}\n"
        
        if conversation_history:
            context += f"Conversation History: {conversation_history}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"User Profile Context: {profile_data}\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"User Resume Context: {resume_data}\n"
        
        if job_data and not job_data.get('error'):
            context += f"Job Search Result: {job_data}\n"
        
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
    
    def _extract_general_job_search_params(self, query: str, profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract job search parameters for general chat queries"""
        params = {'limit': 15}  # Moderate limit for chat context
        
        # Use profile data if available
        if profile_data and not profile_data.get('error'):
            if 'skills' in profile_data:
                params['skills'] = profile_data['skills']
            if 'location' in profile_data:
                params['locations'] = profile_data['location']
        
        # Use resume data if available  
        if resume_data and not resume_data.get('error'):
            if 'skills' in resume_data:
                params['skills'] = resume_data['skills']
        
        # Extract specific terms from query
        query_lower = query.lower()
        
        # Work mode preferences
        if 'remote' in query_lower:
            params['work_mode'] = 'remote'
        elif 'onsite' in query_lower or 'on-site' in query_lower:
            params['work_mode'] = 'onsite'
        elif 'hybrid' in query_lower:
            params['work_mode'] = 'hybrid'
        
        # Job type preferences
        if 'internship' in query_lower:
            params['internship'] = True
        elif 'full time' in query_lower or 'full-time' in query_lower:
            params['job_type'] = 'full-time'
        elif 'part time' in query_lower or 'part-time' in query_lower:
            params['job_type'] = 'part-time'
        
        # Try to extract skills/technologies mentioned in query
        tech_keywords = ['python', 'java', 'javascript', 'react', 'node', 'aws', 'docker', 'sql', 'data science', 'machine learning', 'ai']
        mentioned_skills = [skill for skill in tech_keywords if skill in query_lower]
        if mentioned_skills:
            params['skills'] = ','.join(mentioned_skills)
        
        return params if len(params) > 1 else None  # Only return if we have actual search criteria 