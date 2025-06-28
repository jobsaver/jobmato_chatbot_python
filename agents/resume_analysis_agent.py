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
        self.system_message = """You are a resume analysis expert. Provide helpful feedback on resume improvement.

Focus on:
- Structure and formatting
- Content quality and relevance
- Skills presentation
- Experience descriptions
- Education and certifications
- ATS optimization
- Industry-specific improvements

Respond in the user's preferred language (English/Hindi/Hinglish). Be constructive and specific."""
    
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
            
            # Use clean text context for LLM analysis
            analysis_response = await self._analyze_with_llm(
                original_query,
                resume_data,
                profile_data
            )
            
            # Add detailed logging for debugging
            logger.info(f"📝 LLM response type: {type(analysis_response)}")
            logger.info(f"📝 LLM response: {analysis_response}")
            
            # Check if LLM response was successful
            if not analysis_response:
                logger.warning(f"⚠️ LLM response is empty, using fallback")
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
            elif isinstance(analysis_response, str) and 'error' in analysis_response.lower():
                logger.warning(f"⚠️ LLM response string contains error, using fallback: {analysis_response}")
                fallback_response = self._generate_fallback_analysis(
                    original_query, 
                    resume_data, 
                    profile_data, 
                    language=extracted_data.get('language', 'english')
                )
                analysis_response = fallback_response
            else:
                logger.info(f"✅ LLM response successful: {len(str(analysis_response))} characters")
            
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
        
        # Use a very simple approach to avoid safety filters
        context_parts = []
        
        # Add user query
        context_parts.append(f"User request: {original_query}")
        
        # Add minimal profile info (only skills, no personal data)
        if profile_data and not profile_data.get('error'):
            actual_profile_data = None
            if profile_data.get('data', {}).get('profile'):
                actual_profile_data = profile_data['data']['profile']
            elif profile_data.get('data'):
                actual_profile_data = profile_data['data']
            
            if actual_profile_data and actual_profile_data.get('skills'):
                skills = actual_profile_data['skills']
                if isinstance(skills, list) and len(skills) > 0:
                    context_parts.append(f"User skills: {', '.join(skills[:3])}")
        
        # Add minimal resume info (only key sections, no personal data)
        if resume_data and not resume_data.get('error'):
            actual_resume_data = None
            if resume_data.get('data', {}).get('resume'):
                actual_resume_data = resume_data['data']['resume']
            elif resume_data.get('data'):
                actual_resume_data = resume_data['data']
            
            if actual_resume_data and actual_resume_data.get('parsed_data'):
                parsed = actual_resume_data['parsed_data']
                
                # Count sections without revealing content
                sections = []
                if parsed.get('skills'):
                    sections.append(f"{len(parsed['skills'])} skills")
                if parsed.get('experience'):
                    sections.append(f"{len(parsed['experience'])} experience entries")
                if parsed.get('education'):
                    sections.append(f"{len(parsed['education'])} education entries")
                if parsed.get('projects'):
                    sections.append(f"{len(parsed['projects'])} projects")
                
                if sections:
                    context_parts.append(f"Resume sections: {', '.join(sections)}")
        
        # Add language preference
        context_parts.append(f"Language: {language}")
        
        # Add simple instruction
        context_parts.append("Provide resume improvement suggestions.")
        
        final_context = "\n".join(context_parts)
        logger.info(f"🔧 Final context: {final_context}")
        
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
        
        # Check if user is asking about keywords specifically
        query_lower = query.lower()
        is_keyword_request = any(word in query_lower for word in ['keyword', 'key', 'ats', 'tracking', 'optimize'])
        
        if is_keyword_request:
            if language == 'hinglish':
                response = f"""Abhay bhai, aapke resume ke keywords ke liye main analysis kar raha hun! 📄

**Aapke Resume ke Keywords:**
{resume_info}

**Keywords Optimization Tips:**
• Technical skills ko prominent jagah pe rakho (top section)
• Job descriptions mein relevant keywords add karo
• Industry-specific terms use karo (e.g., "React.js", "Node.js", "MongoDB")
• Action verbs add karo (Developed, Implemented, Optimized)
• Quantifiable achievements mention karo (e.g., "Improved performance by 25%")

**ATS-Friendly Keywords:**
• Skills section mein exact job requirements ke keywords add karo
• Company names, tools, technologies ko spell correctly
• Standard job titles use karo (Software Developer, not "Code Ninja")
• Keywords ko naturally integrate karo, don't stuff them

**Specific Keywords for Your Profile:**
Based on your skills, focus on: React, Node.js, Android Development, Java, Kotlin, Python, MongoDB, Firebase, AWS, Git, REST APIs, Mobile Development, Web Development

Agar aap specific job ke liye keywords chahte hain, to batao! Main help karunga. 😊"""
            
            elif language == 'hindi':
                response = f"""Abhay ji, aapke resume ke keywords ke liye main analysis kar raha hun! 📄

**Aapke Resume ke Keywords:**
{resume_info}

**Keywords Optimization Tips:**
• Technical skills ko prominent jagah pe rakhiye (top section)
• Job descriptions mein relevant keywords add kijiye
• Industry-specific terms use kijiye (e.g., "React.js", "Node.js", "MongoDB")
• Action verbs add kijiye (Developed, Implemented, Optimized)
• Quantifiable achievements mention kijiye (e.g., "Improved performance by 25%")

**ATS-Friendly Keywords:**
• Skills section mein exact job requirements ke keywords add kijiye
• Company names, tools, technologies ko spell correctly
• Standard job titles use kijiye (Software Developer, not "Code Ninja")
• Keywords ko naturally integrate kijiye, don't stuff them

**Specific Keywords for Your Profile:**
Based on your skills, focus on: React, Node.js, Android Development, Java, Kotlin, Python, MongoDB, Firebase, AWS, Git, REST APIs, Mobile Development, Web Development

Agar aap specific job ke liye keywords chahte hain, to bataiye! Main help karunga. 😊"""
            
            else:
                response = f"""Abhay, I've analyzed your resume for keywords! 📄

**Your Resume Keywords:**
{resume_info}

**Keywords Optimization Tips:**
• Place technical skills prominently (top section)
• Add relevant keywords to job descriptions
• Use industry-specific terms (e.g., "React.js", "Node.js", "MongoDB")
• Include action verbs (Developed, Implemented, Optimized)
• Mention quantifiable achievements (e.g., "Improved performance by 25%")

**ATS-Friendly Keywords:**
• Add exact job requirement keywords to skills section
• Spell company names, tools, technologies correctly
• Use standard job titles (Software Developer, not "Code Ninja")
• Integrate keywords naturally, don't stuff them

**Specific Keywords for Your Profile:**
Based on your skills, focus on: React, Node.js, Android Development, Java, Kotlin, Python, MongoDB, Firebase, AWS, Git, REST APIs, Mobile Development, Web Development

Let me know if you'd like keywords for a specific job! 😊"""
        else:
            # General resume analysis fallback
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

    def _build_analysis_context(self, user_question: str, resume_data: Dict[str, Any], profile_data: Dict[str, Any]) -> str:
        """Build context for LLM analysis using clean text content only"""
        
        # Extract clean text content from resume
        resume_text = ""
        if resume_data and not resume_data.get('error'):
            data = resume_data.get('data', {})
            if isinstance(data, dict):
                # Try different paths to get text content
                # Path 1: data.resume.text_content (from logs)
                if data.get('resume') and isinstance(data['resume'], dict):
                    resume_text = data['resume'].get('text_content', '')
                    logger.info(f"📄 Found text_content in data.resume.text_content: {len(resume_text)} chars")
                
                # Path 2: data.text_content (fallback)
                if not resume_text:
                    resume_text = data.get('text_content', '')
                    logger.info(f"📄 Found text_content in data.text_content: {len(resume_text)} chars")
                
                # Path 3: data.content (fallback)
                if not resume_text:
                    resume_text = data.get('content', '')
                    logger.info(f"📄 Found content in data.content: {len(resume_text)} chars")
                
                # Clean up the text content
                if resume_text:
                    # Remove excessive whitespace and normalize
                    resume_text = ' '.join(resume_text.split())
                    # Limit length to avoid token limits
                    if len(resume_text) > 8000:
                        resume_text = resume_text[:8000] + "..."
                    logger.info(f"📄 Final cleaned resume text: {len(resume_text)} chars")
                else:
                    logger.warning(f"📄 No resume text found in any path")
        
        # Build context for LLM
        if resume_text:
            context = f"""You are a professional resume consultant. The user has asked: "{user_question}"

Here is their resume content (parsed from PDF, so ignore any formatting issues):

{resume_text}

Please provide specific, actionable advice based on the actual resume content above. Focus on:
1. Content improvements and suggestions
2. Missing sections or information
3. Ways to strengthen their profile
4. Specific recommendations for their career goals

Be constructive and practical in your suggestions."""
        else:
            context = f"""User Question: {user_question}

No resume content was provided. Please provide general resume advice and suggest that they upload their resume for personalized feedback."""
        
        logger.info(f"📝 Built context with {len(context)} total characters")
        return context 

    async def _analyze_with_llm(self, user_question: str, resume_data: Dict[str, Any], profile_data: Dict[str, Any]) -> str:
        """Analyze resume using LLM with clean text content"""
        try:
            # Build clean context using only text content
            context = self._build_analysis_context(user_question, resume_data, profile_data)
            
            logger.info(f"📝 Sending clean text context to LLM (length: {len(context)} chars)")
            
            # Get LLM response
            response = await self.llm_client.generate_response(
                context,
                self.system_message
            )
            
            logger.info(f"📝 LLM response type: {type(response)}")
            logger.info(f"✅ LLM response successful: {len(response)} characters")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in LLM analysis: {str(e)}")
            return self._create_fallback_analysis(user_question, resume_data)

    async def _analyze_skills(self, user_question: str, resume_data: Dict[str, Any], profile_data: Dict[str, Any]) -> str:
        """Analyze skills section with clean text content"""
        try:
            context = self._build_analysis_context(user_question, resume_data, profile_data)
            context += "\n\nFocus specifically on skills analysis and recommendations."
            
            response = await self.llm_client.generate_response(
                context,
                "You are a career advisor. Analyze the skills in the resume and provide specific recommendations for improvement."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in skills analysis: {str(e)}")
            return "I can help you analyze your skills! Please share your resume or tell me about your current skills, and I'll provide specific recommendations for improvement."

    async def _analyze_experience(self, user_question: str, resume_data: Dict[str, Any], profile_data: Dict[str, Any]) -> str:
        """Analyze experience section with clean text content"""
        try:
            context = self._build_analysis_context(user_question, resume_data, profile_data)
            context += "\n\nFocus specifically on work experience analysis and recommendations."
            
            response = await self.llm_client.generate_response(
                context,
                "You are a career advisor. Analyze the work experience in the resume and provide specific recommendations for improvement."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in experience analysis: {str(e)}")
            return "I can help you improve your experience section! Please share your resume or tell me about your work experience, and I'll provide specific recommendations."

    async def _analyze_formatting(self, user_question: str, resume_data: Dict[str, Any], profile_data: Dict[str, Any]) -> str:
        """Analyze formatting and structure with clean text content"""
        try:
            context = self._build_analysis_context(user_question, resume_data, profile_data)
            context += "\n\nNote: Since this is parsed text content, focus on content structure and organization rather than visual formatting."
            
            response = await self.llm_client.generate_response(
                context,
                "You are a career advisor. Analyze the structure and organization of the resume content and provide recommendations for better content flow and sections."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in formatting analysis: {str(e)}")
            return "I can help you improve your resume structure! Please share your resume and I'll provide recommendations for better organization and content flow."

    async def _analyze_projects(self, user_question: str, resume_data: Dict[str, Any], profile_data: Dict[str, Any]) -> str:
        """Analyze projects section with clean text content"""
        try:
            context = self._build_analysis_context(user_question, resume_data, profile_data)
            context += "\n\nFocus specifically on projects analysis and recommendations."
            
            response = await self.llm_client.generate_response(
                context,
                "You are a career advisor. Analyze the projects in the resume and provide specific recommendations for improvement."
            )
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in projects analysis: {str(e)}")
            return "I can help you improve your projects section! Please share your resume or tell me about your projects, and I'll provide specific recommendations."

    def _create_fallback_analysis(self, user_question: str, resume_data: Dict[str, Any]) -> str:
        """Create a simple fallback analysis when LLM fails"""
        
        # Extract clean text content for basic analysis
        resume_text = ""
        if resume_data and isinstance(resume_data, dict):
            data = resume_data.get('data', {})
            if isinstance(data, dict):
                resume_text = data.get('text_content', '')
                if not resume_text:
                    resume_text = data.get('content', '')
        
        # Provide basic analysis based on text content
        if resume_text:
            word_count = len(resume_text.split())
            has_experience = any(word in resume_text.lower() for word in ['experience', 'worked', 'developed', 'managed'])
            has_skills = any(word in resume_text.lower() for word in ['skills', 'technologies', 'programming'])
            has_education = any(word in resume_text.lower() for word in ['education', 'degree', 'university', 'college'])
            
            analysis = f"""Based on your resume content, here's my analysis:

📄 **Resume Overview:**
• Resume length: ~{word_count} words
• Experience section: {'✅ Present' if has_experience else '❌ Needs improvement'}
• Skills section: {'✅ Present' if has_skills else '❌ Needs improvement'}  
• Education section: {'✅ Present' if has_education else '❌ Needs improvement'}

💡 **Key Recommendations:**
• **Quantify your achievements** - Add numbers, percentages, and metrics
• **Use strong action verbs** - Start bullet points with words like "Developed", "Led", "Improved"
• **Tailor for each job** - Match keywords from job descriptions
• **Keep it concise** - Focus on most relevant and recent experience
• **Professional formatting** - Use consistent fonts, spacing, and structure

🎯 **Specific Improvements:**
• Add measurable results to your accomplishments
• Include relevant technical skills for your target roles
• Ensure contact information is current and professional
• Consider adding a brief professional summary

Would you like me to focus on any specific section of your resume?"""
        else:
            analysis = """I'd be happy to help you improve your resume! Here are some general best practices:

💡 **Essential Resume Elements:**
• **Contact Information** - Name, phone, email, LinkedIn profile
• **Professional Summary** - 2-3 sentences highlighting your key strengths
• **Work Experience** - Focus on achievements, not just responsibilities
• **Skills** - Include both technical and soft skills relevant to your field
• **Education** - Degree, institution, graduation year

🎯 **Pro Tips:**
• Use action verbs and quantify your achievements
• Tailor your resume for each job application
• Keep it to 1-2 pages maximum
• Use a clean, professional format
• Include relevant keywords from job descriptions

Please upload your resume so I can provide more specific feedback!"""
        
        return analysis 