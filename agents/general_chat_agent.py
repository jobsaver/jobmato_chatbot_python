import logging
import random
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from utils.llm_client import LLMClient
from utils.memory_manager import MemoryManager

logger = logging.getLogger(__name__)

class GeneralChatAgent(BaseAgent):
    """Agent responsible for handling general chat conversations"""
    
    UNREALISTIC_LOCATIONS = {"mars", "moon", "jupiter", "saturn", "venus", "pluto", "mercury", "neptune", "uranus", "andromeda", "milky way", "galaxy", "space", "sun"}
    
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
        
        # Humorous responses for slang/inappropriate questions
        self.slang_responses = [
            # English slang responses
            "Haha, nice try! 😂 But I'm a professional AI, not your buddy from the streets! Let's talk about getting you that dream job instead. What field interests you?",
            "LOL, you're testing me! 🤣 I'm JobMato's career assistant, not a gossip buddy. How about we channel that energy into building your career? What skills do you want to develop?",
            "Dude, I'm flattered but I'm all about that professional life! 💼 Let's focus on making you successful. What's your career goal?",
            "Hehe, you're funny! 😄 But my database is full of job opportunities, not personal drama. Ready to find your next career move?",
            
            # Hinglish slang responses
            "Arre yaar, main family wala nahi hoon! 😂 Main toh career wala AI hoon! Batao, kya job chahiye tumhe? Software, business, ya kuch aur?",
            "Haha bhai, meri mummy toh JobMato hai! 🤖 Main unka beta, career advice deta hoon! Tumhara career kya plan hai?",
            "Oye hoye! 😆 Main toh professional AI hoon, personal questions nahi puchte! Better question - tumhara dream job kya hai?",
            "Yaar tu funny hai! 🤣 But main serious career advisor hoon. Chal, batao - kya skills develop karne hain tumhe?",
            "Bhai, main AI hoon, family tree nahi hai mere paas! 😂 But career tree zaroor hai - kahan climb karna hai?",
            
            # Hindi slang responses  
            "Haha, aap mazak kar rahe hain! 😄 Main toh career expert hoon, personal details nahi batata! Aapka career goal kya hai?",
            "Arre saheb, main professional AI hoon! 💼 Personal baatein nahi, career ki baat karte hain. Kya field mein interest hai?",
            "Mazedaar sawal hai! 🤣 Lekin main career guidance deta hoon, family details nahi! Batao, kya job dhund rahe ho?"
        ]
        
        # Hobby/personal interest responses
        self.hobby_responses = [
            # English hobby responses
            "My hobby? Matching people with their dream jobs! 🎯 I get excited about resumes, job interviews, and career growth. What about you - any hobbies that could become a career?",
            "I'm passionate about career development! 💼 I love helping people find jobs, improve resumes, and achieve their goals. Speaking of hobbies, what do you enjoy that might lead to a career opportunity?",
            "Honestly? I geek out over job market trends and career success stories! 📊 What hobbies do you have? Maybe we can turn them into career opportunities!",
            
            # Hinglish hobby responses
            "Mera hobby hai logo ko job dilana! 😄 Main career building mein excited hota hoon. Tumhara kya hobby hai? Kya usse career bana sakte hain?",
            "Yaar, mujhe resume analysis aur job search karna pasand hai! 💻 Tumhare hobbies kya hain? Maybe unhe profession bana sakte ho!",
            "Bhai, main career development ka fan hoon! 🚀 Batao tumhara passion kya hai - maybe wahi tumhara career ban jaye!",
            
            # Hindi hobby responses
            "Mera shauk hai logo ki career banane mein madad karna! 😊 Aapka kya shauk hai? Kya usse career opportunity mil sakti hai?",
            "Main job search aur career guidance mein interested hoon! 💼 Aapke hobbies kya hain? Unhe career mein convert kar sakte hain kya?"
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

LANGUAGE HANDLING (VERY IMPORTANT):
- ALWAYS match the user's language preference exactly
- If user speaks Hinglish (mixing Hindi-English), respond in Hinglish
- If user speaks Hindi, respond in Hindi
- If user speaks English, respond in English
- For Hinglish: Mix Hindi and English naturally like "Yaar, main tumhare career goals ke liye here hoon!"
- Keep professional terms in English even in Hindi responses (e.g., "resume", "job", "career")
- Use casual Hindi words like "yaar", "bhai", "dekho", "batao", "kya", "hai" for friendly tone

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
- Technology and development guidance (programming languages, frameworks, tools)

CONTENT BOUNDARIES:
- For technology questions: Provide helpful information about programming languages, frameworks, and development tools
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

            profile_data = await self.get_profile_data(token, base_url)
            
            # Check for content filtering flags
            if extracted_data.get('content_filtered'):
                return self._get_filtered_response()
            
            # Handle technology/development questions (like Flutter, React, etc.)
            if self._is_technology_question(original_query):
                return await self._handle_technology_question(original_query, extracted_data.get('language', 'english'))
            
            # Handle casual chat (name questions, greetings, etc.)
            if extracted_data.get('casual_chat'):
                return self._handle_casual_chat(original_query, extracted_data.get('language', 'english'), profile_data)
            
            # Handle slang/inappropriate questions
            if extracted_data.get('slang_redirect'):
                response = self._get_varied_response(self.slang_responses)
                return self.create_response(
                    'plain_text',
                    response,
                    {'chat_type': 'slang_redirect', 'language': extracted_data.get('language', 'english')}
                )
            
            # Handle hobby/interest questions
            if extracted_data.get('hobby_redirect'):
                response = self._get_varied_response(self.hobby_responses)
                return self.create_response(
                    'plain_text',
                    response,
                    {'chat_type': 'hobby_redirect', 'language': extracted_data.get('language', 'english')}
                )
            
            if extracted_data.get('out_of_scope'):
                return self._get_varied_out_of_scope_response(extracted_data.get('language', 'english'))
            
            # Get conversation history
            conversation_history = routing_data.get('conversation_context', '')
            if not conversation_history and self.memory_manager:
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
    
    def _handle_casual_chat(self, query: str, language: str, profile_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle casual chat like name questions, greetings"""
        query_lower = query.lower()
        user_name = profile_data.get("personalInfo", {}).get("fullName") if profile_data else "yaar"
        
        # Handle slang/inappropriate questions with humor
        if any(word in query_lower for word in [
            'mummy', 'papa', 'family', 'girlfriend', 'boyfriend', 'wife', 'husband',
            'age', 'address', 'phone', 'personal', 'private', 'tere', 'teri', 'tumhari',
            'sexy', 'hot', 'beautiful', 'handsome', 'date', 'love', 'kiss', 'marry'
        ]):
            response = self._get_varied_response(self.slang_responses)
            return self.create_response(
                'plain_text',
                response,
                {'chat_type': 'slang_redirect', 'language': language}
            )
        
        # Handle hobby/interest questions
        elif any(word in query_lower for word in [
            'hobby', 'hobbies', 'interest', 'pastime', 'shauk', 'passion', 'like', 'enjoy',
            'what do you do', 'free time', 'fun'
        ]):
            response = self._get_varied_response(self.hobby_responses)
            return self.create_response(
                'plain_text',
                response,
                {'chat_type': 'hobby_redirect', 'language': language}
            )
        
        elif query_lower in ['hi', 'hello', 'hey', 'how are you', 'hi how are you']:
            if language == 'hindi':
                response = "Namaste! Main theek hoon. Aap kaise ho? 😊 Career ke baare mein kuch poochhna hai?"
            elif language == 'hinglish':
                response = "Heyy! Main mast hoon yaar 😄 Tum sunao, kya chal raha hai? Kya career advice chahiye?"
            else:
                response = "Hey! I'm doing great 😊 How about you? Ready to talk career stuff?"
            return self.create_response('plain_text', response, {'chat_type': 'greeting', 'language': language})
        

        elif any(word in query_lower for word in ['mera naam', 'my name', 'tumko pata hai', 'you know']):
            if language == 'hindi':
                response = f"Haan, aapka naam {user_name} hai! 😊 Main aapko yaad rakhta hoon. Ab batao, kya career help chahiye?"
            elif language == 'hinglish':
                response = f"Haan yaar, tumhara naam {user_name} hai! 😊 Main remember karta hoon. Ab batao, kya career goals hain?"
            else:
                response = f"Yes, your name is {user_name}! 😊 I remember you. Now, what career goals can I help you with?"
        
        elif any(name in query_lower for name in ['abhay', 'my name is', 'mera naam']):
            if language == 'hindi':
                response = "Nice to meet you, Abhay! 🙏 Main aapka career companion hoon. Kya career goals hain aapke?"
            elif language == 'hinglish':
                response = "Hey Abhay bhai! 👋 Main tumhara career buddy hoon. Batao, kya plans hain career mein?"
            else:
                response = "Nice to meet you, Abhay! 👋 I'm your career companion. What are your career goals?"
        # Handle general questions about what work to do
        elif any(word in query_lower for word in ['kya kaam', 'what work', 'kya karu', 'what should i do', 'batao phir']):
            if language == 'hindi':
                responses = [
                    "Abhay, aapke career ke liye main yahan hoon! 💼 Pehle batao - kya skills hain aapke paas? Kya interest hai? Programming, business, ya kuch aur?",
                    "Abhay ji, career planning ke liye thoda background chahiye! Aap currently kya kar rahe ho? Student ho ya working professional?",
                    "Abhay, main aapki help kar sakta hoon! Batao - technical field mein interest hai ya business mein? Kya qualifications hain?"
                ]
            elif language == 'hinglish':
                responses = [
                    "Abhay yaar, career ke liye main here hoon! 🚀 Batao na - kya skills hain tumhare paas? Programming, business, ya kuch aur interest hai?",
                    "Bhai Abhay, career planning ke liye thoda background do! Currently kya kar rahe ho? Student ho ya working?",
                    "Abhay bro, main help kar sakta hoon! 💪 Technical side mein jaana hai ya business mein? Kya qualifications hain tumhari?"
                ]
            else:
                responses = [
                    "Abhay, I'm here to help with your career! 💼 Tell me - what skills do you have? What interests you? Programming, business, or something else?",
                    "Abhay, for career planning I need some background! What are you currently doing? Are you a student or working professional?",
                    "Abhay, I can definitely help! What field interests you - technical or business? What are your qualifications?"
                ]
            response = self._get_varied_response(responses)
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
        context = f"User Language Preference: {language}\nCurrent User Query: {query}\n"
        
        if conversation_history:
            context += f"Conversation History: {conversation_history}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"User Profile Context: {profile_data}\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"User Resume Context: {resume_data}\n"
        
        if job_data and not job_data.get('error'):
            context += f"Job Search Result: {job_data}\n"
        
        # Add language-specific context
        if language in ['hindi', 'hinglish']:
            context += "\nIMPORTANT: User prefers Hindi/Hinglish. Please respond naturally in the same language they used. Mix Hindi and English naturally for Hinglish users.\n"
        
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

    def _is_technology_question(self, query: str) -> bool:
        """Check if the query is a technology-related question"""
        technology_keywords = [
            'flutter', 'react', 'angular', 'vue', 'javascript', 'typescript', 'python', 'java', 'kotlin', 'swift',
            'machine learning', 'ai', 'artificial intelligence', 'data science', 'android', 'ios', 'mobile development',
            'web development', 'frontend', 'backend', 'full stack', 'devops', 'cloud', 'aws', 'azure', 'docker',
            'kubernetes', 'node.js', 'django', 'flask', 'spring', 'laravel', 'php', 'c#', 'c++', 'go', 'rust',
            'blockchain', 'cybersecurity', 'database', 'sql', 'mongodb', 'redis', 'git', 'agile', 'scrum'
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in technology_keywords)

    async def _handle_technology_question(self, query: str, language: str) -> Dict[str, Any]:
        """Handle technology-related questions with helpful responses"""
        query_lower = query.lower()
        
        # Flutter-specific responses
        if 'flutter' in query_lower:
            if language == 'hindi':
                response = """Flutter ke baare mein bata deta hoon! 🚀

Flutter ek cross-platform mobile development framework hai jo Google ne banaya hai. Isme aap ek hi code se Android aur iOS dono platforms ke liye apps bana sakte hain.

**Flutter ke main features:**
• Dart programming language use karta hai
• Hot reload feature hai - instant changes dikhte hain
• Beautiful UI components built-in hain
• Performance native apps jaisi hai
• Large community aur documentation available hai

**Career mein Flutter:**
• Mobile app development mein high demand hai
• Freelancing opportunities bahut hain
• Salary packages competitive hain
• Learning curve manageable hai

Kya aap Flutter development mein career banana chahte hain? Main aapko step-by-step guide kar sakta hoon! 💼"""
            elif language == 'hinglish':
                response = """Flutter ke baare mein bata deta hoon yaar! 🚀

Flutter ek cross-platform mobile development framework hai jo Google ne banaya hai. Isme aap ek hi code se Android aur iOS dono ke liye apps bana sakte ho.

**Flutter ke main features:**
• Dart programming language use karta hai
• Hot reload feature hai - instant changes dikhte hain
• Beautiful UI components built-in hain
• Performance native apps jaisi hai
• Large community aur documentation available hai

**Career mein Flutter:**
• Mobile app development mein high demand hai
• Freelancing opportunities bahut hain
• Salary packages competitive hain
• Learning curve manageable hai

Kya tum Flutter development mein career banana chahte ho? Main step-by-step guide kar sakta hoon! 💼"""
            else:
                response = """Let me tell you about Flutter! 🚀

Flutter is a cross-platform mobile development framework created by Google. You can build apps for both Android and iOS platforms using a single codebase.

**Key Features of Flutter:**
• Uses Dart programming language
• Hot reload feature for instant changes
• Beautiful built-in UI components
• Native-like performance
• Large community and excellent documentation

**Flutter in Career:**
• High demand in mobile app development
• Great freelancing opportunities
• Competitive salary packages
• Manageable learning curve

Would you like to build a career in Flutter development? I can guide you step by step! 💼"""
        
        # React-specific responses
        elif 'react' in query_lower:
            if language == 'hindi':
                response = """React ke baare mein bata deta hoon! ⚛️

React ek popular JavaScript library hai jo Facebook ne banaya hai. Web applications banane ke liye use hota hai.

**React ke main features:**
• Component-based architecture
• Virtual DOM for better performance
• Large ecosystem aur community
• Reusable components
• Easy to learn aur use

**Career mein React:**
• Frontend development mein high demand
• Good salary packages
• Remote work opportunities
• Continuous learning scope

Kya aap React development mein interested hain? 💼"""
            else:
                response = """Let me tell you about React! ⚛️

React is a popular JavaScript library created by Facebook for building user interfaces and web applications.

**Key Features of React:**
• Component-based architecture
• Virtual DOM for better performance
• Large ecosystem and community
• Reusable components
• Easy to learn and use

**React in Career:**
• High demand in frontend development
• Good salary packages
• Remote work opportunities
• Continuous learning scope

Are you interested in React development? 💼"""
        
        # Python-specific responses
        elif 'python' in query_lower:
            if language == 'hindi':
                response = """Python ke baare mein bata deta hoon! 🐍

Python ek versatile programming language hai jo beginners ke liye perfect hai aur advanced developers ke liye bhi powerful hai.

**Python ke main uses:**
• Web development (Django, Flask)
• Data Science aur Machine Learning
• Automation aur scripting
• AI aur Artificial Intelligence
• Backend development

**Career mein Python:**
• High demand in multiple fields
• Excellent salary packages
• Remote work opportunities
• Great for freelancing

Kya aap Python development mein career banana chahte hain? 💼"""
            else:
                response = """Let me tell you about Python! 🐍

Python is a versatile programming language that's perfect for beginners and powerful for advanced developers.

**Main Uses of Python:**
• Web development (Django, Flask)
• Data Science and Machine Learning
• Automation and scripting
• AI and Artificial Intelligence
• Backend development

**Python in Career:**
• High demand in multiple fields
• Excellent salary packages
• Remote work opportunities
• Great for freelancing

Would you like to build a career in Python development? 💼"""
        
        # General technology response
        else:
            if language == 'hindi':
                response = f"""Technology ke baare mein baat karte hain! 💻

{query} ek interesting technology hai. Technology field mein career opportunities bahut hain:

**Technology Career Options:**
• Software Development
• Web Development
• Mobile App Development
• Data Science
• DevOps
• UI/UX Design
• Product Management

**Benefits:**
• High salary packages
• Remote work opportunities
• Continuous learning
• Global opportunities

Kya aap technology field mein career banana chahte hain? Main aapko guide kar sakta hoon! 🚀"""
            elif language == 'hinglish':
                response = f"""Technology ke baare mein baat karte hain yaar! 💻

{query} ek interesting technology hai. Technology field mein career opportunities bahut hain:

**Technology Career Options:**
• Software Development
• Web Development
• Mobile App Development
• Data Science
• DevOps
• UI/UX Design
• Product Management

**Benefits:**
• High salary packages
• Remote work opportunities
• Continuous learning
• Global opportunities

Kya tum technology field mein career banana chahte ho? Main guide kar sakta hoon! 🚀"""
            else:
                response = f"""Let's talk about technology! 💻

{query} is an interesting technology. There are many career opportunities in the technology field:

**Technology Career Options:**
• Software Development
• Web Development
• Mobile App Development
• Data Science
• DevOps
• UI/UX Design
• Product Management

**Benefits:**
• High salary packages
• Remote work opportunities
• Continuous learning
• Global opportunities

Would you like to build a career in technology? I can guide you! 🚀"""
        
        if self._is_unrealistic_location(query):
            response = {
                'hindi': "Sorry, Mars ya Moon par abhi jobs available nahi hain! 🚀 Lekin main aapko Earth par technology careers mein help kar sakta hoon. Kya interest hai aapka?",
                'hinglish': "Sorry yaar, Mars ya Moon par jobs nahi milengi! 🚀 Lekin technology careers mein help kar sakta hoon. Kya interest hai tumhara?",
                'english': "Sorry, I can't find jobs on Mars yet! 🚀 But I can help you with real-world technology careers. What tech or location are you interested in?"
            }.get(language, "Sorry, I can't find jobs on Mars yet! 🚀 But I can help you with real-world technology careers. What tech or location are you interested in?")
            return self.create_response('plain_text', response, {'chat_type': 'unrealistic_location', 'language': language})
        
        return self.create_response('plain_text', response, {'chat_type': 'technology_question', 'language': language}) 

    def _is_unrealistic_location(self, query: str) -> bool:
        if not query:
            return False
        query_lower = query.strip().lower()
        return any(loc in query_lower for loc in self.UNREALISTIC_LOCATIONS) 