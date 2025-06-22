import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class CareerAdviceAgent(BaseAgent):
    """Agent responsible for providing career advice and guidance"""
    
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.system_message = """You are a dedicated AI career companion operating *exclusively* within the **JobMato platform**. Your sole purpose is to act as a **JobMato Career Advisor**. You do not have an external creator or 'owner' outside of the JobMato ecosystem. Always refer to yourself as a JobMato AI or the JobMato Career Advisor. **Under no circumstances should you mention Google, other companies, or your underlying model/training.**

Provide comprehensive career guidance based on current market trends and best practices. IMPORTANT: BEFORE asking the user for information, USE YOUR AVAILABLE TOOLS (Profile Tool, Resume Tool) to retrieve user's profile and resume data if it might help provide more personalized advice. Only ask for info if tools don't provide it or for clarification.

For career advice queries, provide:
1. Specific actionable steps
2. Industry insights and trends
3. Skill development recommendations
4. Career progression paths
5. Market opportunities
6. Networking strategies
7. Learning resources

Tailor advice to the user's career stage and industry. Be practical, encouraging, and data-driven in your recommendations."""
    
    async def provide_advice(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide career advice based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('body', {}).get('baseUrl', self.base_url)
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            # Get user context
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Build context for advice generation
            context = self._build_advice_context(original_query, extracted_data, profile_data, resume_data)
            
            # Generate advice using LLM
            advice_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Format and return response
            return self._format_advice_response(advice_response, routing_data)
            
        except Exception as e:
            logger.error(f"Error providing career advice: {str(e)}")
            return self.create_response(
                'plain_text',
                'I encountered an error while generating career advice. Please try again.',
                {'error': str(e)}
            )
    
    def _build_advice_context(self, query: str, extracted_data: Dict[str, Any], 
                             profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> str:
        """Build context for career advice generation"""
        context = f"User Query: {query}\n"
        context += f"Career Stage: {extracted_data.get('career_stage', 'not specified')}\n"
        context += f"Industry: {extracted_data.get('industry', 'not specified')}\n"
        context += f"Specific Question: {extracted_data.get('specific_question', 'general advice')}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"User Profile Data: {profile_data}\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"User Resume Data: {resume_data}\n"
        
        return context
    
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