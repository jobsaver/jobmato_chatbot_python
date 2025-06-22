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

Your task is to analyze the user's resume thoroughly and answer any question related to resume user asks to you. You can use resume tool to get user resume content.

When analyzing a resume, provide:
1. **Overall Assessment**: Strengths and areas for improvement
2. **Content Analysis**: Review of experience, skills, education, and achievements
3. **Format & Structure**: Layout, readability, and organization feedback
4. **ATS Optimization**: Keywords and formatting for Applicant Tracking Systems
5. **Industry Alignment**: How well the resume fits target roles/industries
6. **Specific Recommendations**: Actionable improvements with examples
7. **Skills Gap Analysis**: Missing skills for target positions
8. **Achievement Quantification**: Suggestions for better metrics and impact statements

Be constructive, specific, and provide actionable feedback that helps improve the resume's effectiveness."""
    
    async def analyze_resume(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the user's resume based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('body', {}).get('baseUrl', self.base_url)
            original_query = routing_data.get('originalQuery', '')
            
            # Get resume data
            resume_data = await self.get_resume_data(token, base_url)
            
            if resume_data.get('error'):
                return self.create_response(
                    'plain_text',
                    'I couldn\'t access your resume data. Please make sure you have uploaded a resume first.',
                    {'error': 'No resume data available'}
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