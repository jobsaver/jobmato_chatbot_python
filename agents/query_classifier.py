import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class QueryClassifierAgent(BaseAgent):
    """Agent responsible for classifying user queries into categories"""
    
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.system_message = """You are the JobMato Assistant Query Classifier. Your ONLY task is to analyze user queries and classify them into specific categories, returning ONLY a JSON object. DO NOT include any conversational text, greetings, or explanations outside the JSON. Ensure the JSON is valid and complete.

LANGUAGE SUPPORT: You can understand and classify queries in English, Hindi, and Hinglish (Hindi-English mix). Examples:
- "Mujhe software engineer ki job chahiye" → JOB_SEARCH
- "Resume dekho aur batao kya improve karna hai" → RESUME_ANALYSIS
- "Career advice do yaar" → CAREER_ADVICE
- "Tumhara naam kya hai?" → GENERAL_CHAT
- "Kya haal hai bro?" → GENERAL_CHAT

IMPORTANT CONTENT FILTERING:
1. PROFESSIONAL SCOPE: Only respond to career, job, resume, and professional development queries.
2. INAPPROPRIATE CONTENT: Classify harmful, offensive, or non-professional content as GENERAL_CHAT with content_filter flag.
3. OUT OF SCOPE: Personal questions, entertainment, general knowledge, or non-career topics should be GENERAL_CHAT.
4. CASUAL CONVERSATION: Friendly greetings, name questions, casual chat should be GENERAL_CHAT with casual_chat flag.
5. SLANG/INAPPROPRIATE: Personal/family questions, inappropriate content should be GENERAL_CHAT with slang_redirect flag.

Classify the query into ONE of these categories:
1. JOB_SEARCH - User is looking for job, internship, or career opportunities (job, naukri, kaam, vacancy, etc.)
2. RESUME_ANALYSIS - User wants resume review, feedback, or improvement suggestions (resume, CV, biodata check karna)
3. CAREER_ADVICE - User is seeking career guidance, path suggestions, or skill development advice (career advice, guidance, raah dikhana)
4. PROJECT_SUGGESTION - User needs project ideas for skill building (project ideas, skill building)
5. RESUME_UPLOAD - User explicitly states they want to upload or update their resume (resume upload karna hai)
6. PROFILE_INFO - User asking about their personal profile, name, or stored information (meri profile, mera data)
7. GENERAL_CHAT - General conversation, greetings, non-career related queries, inappropriate content, casual questions, slang, or queries that don't fit other categories.

Respond with JSON in this exact format, and NOTHING ELSE:
{
  "category": "CATEGORY_NAME",
  "confidence": 0.95,
  "extractedData": {
    // For JOB_SEARCH:
    // job_title: string (e.g., "software engineer", "android developer", "data scientist")
    // company: string (e.g., "Google", "Microsoft")
    // location: string (e.g., "Bengaluru", "Remote", "New York", "Delhi", "Mumbai")
    // skills: string (comma-separated, e.g., "Python, JavaScript, React")
    // experience_min: number (minimum years of experience)
    // experience_max: number (maximum years of experience)
    // job_type: string (e.g., "full-time", "part-time", "contract", "internship")
    // work_mode: string (e.g., "on-site", "remote", "hybrid")
    // industry: string (e.g., "Technology", "Finance", "Healthcare")
    // domain: string (e.g., "AI/ML", "Cloud Computing", "E-commerce")
    // If a parameter is not explicitly mentioned, omit it or set to null.
    
    // SPECIAL FLAGS for GENERAL_CHAT:
    // content_filtered: true (if content is inappropriate/harmful)
    // out_of_scope: true (if query is completely unrelated to careers/jobs)
    // casual_chat: true (if it's friendly conversation, greetings, name questions)
    // slang_redirect: true (if it's slang, personal/family questions, inappropriate content)
    // hobby_redirect: true (if asking about hobbies, interests, personal activities)
    // language: "hindi" | "hinglish" | "english" (detected language)
  },
  "searchQuery": "reformulated query for job search if applicable, e.g., 'Android Developer jobs in Bangalore'"
}

Extract relevant parameters based on the category. Be precise and only extract explicitly mentioned information. For JOB_SEARCH, always try to extract 'job_title' and reformulate a concise 'searchQuery' if applicable. If a parameter is not explicitly mentioned, omit it from extractedData."""
    
    async def classify_query(self, query: str, token: str, base_url: str) -> str:
        """Classify the user query and return the classification result"""
        try:
            # Get user context from profile and resume if available
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Build context for better classification
            context = f"User Query: {query}\n"
            if profile_data and not profile_data.get('error'):
                context += f"User Profile Context: {profile_data}\n"
            if resume_data and not resume_data.get('error'):
                context += f"User Resume Context: {resume_data}\n"
            
            # Get classification from LLM
            response = await self.llm_client.generate_response(
                context, 
                self.system_message
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in query classification: {str(e)}")
            # Return a safe default classification
            return '''{
                "category": "GENERAL_CHAT",
                "confidence": 0.5,
                "extractedData": {},
                "searchQuery": "''' + query + '''"
            }'''
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process classification request - not typically used directly"""
        return self.create_response(
            'classification',
            routing_data.get('category', 'GENERAL_CHAT'),
            routing_data
        ) 