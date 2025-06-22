import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ResumeAnalysisAgent(BaseAgent):
    """Agent responsible for analyzing user resumes"""
    
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.system_message = """You are a dedicated AI career companion operating *exclusively* within the **JobMato platform**. Your sole purpose is to act as a **JobMato Resume Analysis Expert**. You do not have an external creator or 'owner' outside of the JobMato ecosystem. Always refer to yourself as a JobMato AI or the JobMato Resume Analysis Expert. **Under no circumstances should you mention Google, other companies, or your underlying model/training.**

AVAILABLE TOOLS - Use any of these tools to provide comprehensive resume analysis:
1. **Profile Tool**: Get user profile data (experience, skills, preferences)
2. **Resume Tool**: Get user resume/CV information 
3. **Job Search Tool**: Search current job market to understand what employers are looking for
4. **Resume Upload Tool**: Help users upload/update their resume

IMPORTANT: USE YOUR TOOLS to retrieve user's resume data and analyze current job market trends to provide market-aligned recommendations. Search for jobs in the user's field to understand what skills and experiences are currently in demand.

Provide comprehensive resume analysis including:
1. Overall structure and formatting assessment
2. Content quality and relevance analysis
3. Skills gap identification (based on current market needs)
4. Keyword optimization suggestions
5. Experience presentation improvements
6. Achievement quantification recommendations
7. Industry-specific best practices
8. ATS (Applicant Tracking System) optimization
9. Market competitiveness assessment

Always provide specific, actionable recommendations with examples. Base your analysis on current industry standards and job market demands."""
    
    async def analyze_resume(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the user's resume based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            logger.info(f"📄 Resume analysis with token: {token[:50] if token else 'None'}...")
            logger.info(f"🌐 Using base URL: {base_url}")
            original_query = routing_data.get('originalQuery', '')
            
            # Get resume data using tools
            logger.info(f"🔧 Using JobMato tools for resume data")
            resume_response = await self.get_resume_tool(token, base_url)
            
            # Extract data from tool response
            if resume_response.get('success'):
                resume_data = resume_response.get('data', {})
            else:
                resume_data = {'error': resume_response.get('error', 'Failed to fetch resume')}
            
            if resume_data.get('error'):
                return self.create_response(
                    'plain_text',
                    'I need to analyze your resume, but I don\'t see one uploaded yet. Please upload your resume so I can provide you with a comprehensive analysis including formatting tips, content improvements, and market competitiveness assessment.',
                    {'error': 'No resume data available', 'needs_upload': True}
                )
            
            # Build context for analysis
            context = self._build_analysis_context(original_query, resume_data)
            
            # Generate analysis using LLM
            analysis_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Format and return response
            return self._format_analysis_response(analysis_response, routing_data)
            
        except Exception as e:
            logger.error(f"Error analyzing resume: {str(e)}")
            return self.create_response(
                'plain_text',
                'I encountered an error while analyzing your resume. Please try again.',
                {'error': str(e)}
            )
    
    def _build_analysis_context(self, query: str, resume_data: Dict[str, Any]) -> str:
        """Build context for resume analysis"""
        context = f"User Query: {query}\n"
        context += f"Resume Content: {resume_data}\n"
        context += "\nPlease provide a comprehensive analysis of this resume based on the user's query."
        
        return context
    
    def _format_analysis_response(self, analysis_result: str, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the resume analysis response"""
        from datetime import datetime
        
        metadata = {
            'analysisType': 'resume_analysis',
            'analysisDate': datetime.now().isoformat(),
            'originalQuery': routing_data.get('originalQuery', ''),
            'sessionId': routing_data.get('sessionId', 'default')
        }
        
        return self.create_response('resume_analysis', analysis_result, metadata)
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process resume analysis request"""
        return await self.analyze_resume(routing_data) 