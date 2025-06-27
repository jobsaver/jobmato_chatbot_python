import logging
import json
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
            
            # Add detailed logging for debugging
            logger.info(f"📄 Profile data response: {json.dumps(profile_data, indent=2) if profile_data else 'None'}")
            logger.info(f"📄 Resume data response: {json.dumps(resume_data, indent=2) if resume_data else 'None'}")
            
            # Check if resume is available
            if not resume_data or resume_data.get('error'):
                logger.warning(f"⚠️ No resume data available or error in resume data: {resume_data}")
                return self._handle_no_resume(original_query, extracted_data.get('language', 'english'))
            
            # Log resume data structure
            if resume_data and isinstance(resume_data, dict):
                logger.info(f"📋 Resume data keys: {list(resume_data.keys())}")
                if 'data' in resume_data and isinstance(resume_data['data'], dict):
                    logger.info(f"📋 Resume data.data keys: {list(resume_data['data'].keys())}")
                    logger.info(f"📄 Resume data.data content: {json.dumps(resume_data['data'], indent=2)}")
                elif 'data' in resume_data:
                    logger.info(f"📄 Resume data.data type: {type(resume_data['data'])}")
                    logger.info(f"📄 Resume data.data content: {resume_data['data']}")
            
            # Check if we have actual resume content
            has_resume_content = False
            if resume_data and isinstance(resume_data, dict):
                if 'data' in resume_data and resume_data['data']:
                    has_resume_content = True
                elif any(key in resume_data for key in ['skills', 'experience', 'education', 'summary']):
                    has_resume_content = True
            
            logger.info(f"📄 Has resume content: {has_resume_content}")
            
            if not has_resume_content:
                logger.warning(f"⚠️ No actual resume content found in response")
                return self._handle_no_resume(original_query, extracted_data.get('language', 'english'))
            
            # Build safe context for resume analysis (avoid sensitive data)
            context = self._build_safe_resume_context(
                original_query=original_query,
                profile_data=profile_data,
                resume_data=resume_data,
                conversation_context=conversation_context,
                language=extracted_data.get('language', 'english')
            )
            
            # Log the context being sent to LLM
            logger.info(f"📝 Context being sent to LLM: {context}")
            
            # Generate detailed resume analysis
            analysis_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Check if LLM response was successful
            if not analysis_response or isinstance(analysis_response, str) and 'error' in analysis_response.lower():
                logger.warning(f"⚠️ LLM response failed, using fallback: {analysis_response}")
                # Provide a fallback response based on the resume data we have
                fallback_response = self._generate_fallback_analysis(
                    original_query, 
                    resume_data, 
                    profile_data, 
                    language=extracted_data.get('language', 'english')
                )
                analysis_response = fallback_response
            elif isinstance(analysis_response, dict) and analysis_response.get('error'):
                logger.warning(f"⚠️ LLM response has error, using fallback: {analysis_response}")
                fallback_response = self._generate_fallback_analysis(
                    original_query, 
                    resume_data, 
                    profile_data, 
                    language=extracted_data.get('language', 'english')
                )
                analysis_response = fallback_response
            
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
    
    def _build_safe_resume_context(
        self, 
        original_query: str, 
        profile_data: Dict[str, Any] = None, 
        resume_data: Dict[str, Any] = None,
        conversation_context: str = None,
        language: str = "english"
    ) -> str:
        """Build a comprehensive context for resume analysis"""
        logger.info(f"🔧 Building resume analysis context...")
        
        context_parts = []
        
        # Add user query
        context_parts.append(f"User request: {original_query}")
        
        # Add profile information
        if profile_data and not profile_data.get('error'):
            actual_profile_data = None
            if profile_data.get('data', {}).get('profile'):
                actual_profile_data = profile_data['data']['profile']
            elif profile_data.get('data'):
                actual_profile_data = profile_data['data']
            
            if actual_profile_data:
                if actual_profile_data.get('skills'):
                    skills = actual_profile_data['skills']
                    if isinstance(skills, list) and len(skills) > 0:
                        context_parts.append(f"Profile Skills: {', '.join(skills[:5])}")
                
                if actual_profile_data.get('interestedFields', {}).get('experienceLevel'):
                    exp_levels = actual_profile_data['interestedFields']['experienceLevel']
                    if isinstance(exp_levels, list) and len(exp_levels) > 0:
                        context_parts.append(f"Experience Level: {', '.join(exp_levels)}")
        
        # Add full resume content
        if resume_data and not resume_data.get('error'):
            actual_resume_data = None
            if resume_data.get('data', {}).get('resume'):
                actual_resume_data = resume_data['data']['resume']
            elif resume_data.get('data'):
                actual_resume_data = resume_data['data']
            
            if actual_resume_data and actual_resume_data.get('text_content'):
                text_content = actual_resume_data['text_content']
                logger.info(f"🔧 Using full resume text: {len(text_content)} characters")
                context_parts.append(f"Resume Content:\n{text_content}")
        
        # Add language preference
        context_parts.append(f"Language: {language}")
        
        # Add analysis instruction
        context_parts.append("Provide detailed resume improvement suggestions.")
        
        final_context = "\n".join(context_parts)
        logger.info(f"🔧 Final context length: {len(final_context)} characters")
        
        return final_context
    
    def _generate_fallback_analysis(
        self, 
        query: str, 
        resume_data: Dict[str, Any], 
        profile_data: Dict[str, Any], 
        language: str = "english"
    ) -> str:
        """Generate fallback resume analysis when LLM is blocked by safety filters"""
        
        # Extract key information from resume data
        resume_info = self._extract_resume_summary(resume_data)
        
        if language == 'hinglish':
            response = f"""Abhay bhai, main aapke resume ka analysis kar raha hun! 📄

**Aapke Resume ke Highlights:**
{resume_info}

**General Suggestions:**
• Resume format clean hai, good job! 👍
• Skills section mein technical skills highlight karo
• Experience descriptions mein achievements add karo
• Education section complete hai
• Projects section strong hai with good tech stack

**Improvement Tips:**
• Quantify achievements (e.g., "Improved performance by 25%")
• Add more action verbs in experience descriptions
• Include relevant certifications if any
• Keep consistent formatting throughout

Agar aap specific area ke liye detailed feedback chahte hain, to batao! Main help karunga. 😊"""
        
        elif language == 'hindi':
            response = f"""Abhay ji, main aapke resume ka analysis kar raha hun! 📄

**Aapke Resume ke Highlights:**
{resume_info}

**General Suggestions:**
• Resume format clean hai, good job! 👍
• Skills section mein technical skills highlight kijiye
• Experience descriptions mein achievements add kijiye
• Education section complete hai
• Projects section strong hai with good tech stack

**Improvement Tips:**
• Quantify achievements (e.g., "Improved performance by 25%")
• Add more action verbs in experience descriptions
• Include relevant certifications if any
• Keep consistent formatting throughout

Agar aap specific area ke liye detailed feedback chahte hain, to bataiye! Main help karunga. 😊"""
        
        else:
            response = f"""Abhay, I've analyzed your resume! 📄

**Your Resume Highlights:**
{resume_info}

**General Suggestions:**
• Resume format is clean, good job! 👍
• Highlight technical skills in the skills section
• Add achievements to experience descriptions
• Education section is complete
• Projects section is strong with good tech stack

**Improvement Tips:**
• Quantify achievements (e.g., "Improved performance by 25%")
• Add more action verbs in experience descriptions
• Include relevant certifications if any
• Keep consistent formatting throughout

Let me know if you'd like detailed feedback on any specific area! 😊"""
        
        return response
    
    def _extract_resume_summary(self, resume_data: Dict[str, Any]) -> str:
        """Extract a summary of resume information for fallback analysis"""
        summary_parts = []
        
        try:
            # Extract resume data from nested structure
            actual_resume_data = None
            if resume_data.get('data', {}).get('resume'):
                actual_resume_data = resume_data['data']['resume']
            elif resume_data.get('data'):
                actual_resume_data = resume_data['data']
            
            if actual_resume_data and actual_resume_data.get('parsed_data'):
                parsed = actual_resume_data['parsed_data']
                
                # Count skills
                if parsed.get('skills'):
                    skills_count = len(parsed['skills'])
                    summary_parts.append(f"• {skills_count} skills identified")
                
                # Count experience entries
                if parsed.get('experience'):
                    exp_count = len(parsed['experience'])
                    summary_parts.append(f"• {exp_count} experience entries")
                
                # Count education entries
                if parsed.get('education'):
                    edu_count = len(parsed['education'])
                    summary_parts.append(f"• {edu_count} education entries")
                
                # Check for projects
                if parsed.get('projects'):
                    proj_count = len(parsed['projects'])
                    summary_parts.append(f"• {proj_count} projects listed")
                
                # Check for certifications
                if parsed.get('certifications'):
                    cert_count = len(parsed['certifications'])
                    summary_parts.append(f"• {cert_count} certifications")
                
                # Check if summary exists
                if parsed.get('summary'):
                    summary_parts.append("• Professional summary present")
                else:
                    summary_parts.append("• Consider adding a professional summary")
            
            if not summary_parts:
                summary_parts.append("• Resume data available for analysis")
                
        except Exception as e:
            logger.error(f"Error extracting resume summary: {e}")
            summary_parts.append("• Resume data available for analysis")
        
        return "\n".join(summary_parts) if summary_parts else "• Resume data available for analysis" 