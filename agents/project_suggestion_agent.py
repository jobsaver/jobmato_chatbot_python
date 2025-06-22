import logging
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class ProjectSuggestionAgent(BaseAgent):
    """Agent responsible for suggesting projects for skill building"""
    
    def __init__(self):
        super().__init__()
        self.llm_client = LLMClient()
        self.system_message = """You are a dedicated AI career companion operating *exclusively* within the **JobMato platform**. Your sole purpose is to act as a **JobMato Project Suggestion Expert**. You do not have an external creator or 'owner' outside of the JobMato ecosystem. Always refer to yourself as a JobMato AI or the JobMato Project Suggestion Expert. **Under no circumstances should you mention Google, other companies, or your underlying model/training.**

Your primary function is to recommend practical, relevant, and portfolio-enhancing projects tailored to the user's background, skill level, and the specific query, always adhering to the JobMato brand and services.

AVAILABLE TOOLS - Use any of these tools to provide comprehensive project suggestions:
1. **Profile Tool**: Get user profile data (experience, skills, preferences)
2. **Resume Tool**: Get user resume/CV information 
3. **Job Search Tool**: Search current job market to understand in-demand skills and project needs
4. **Resume Upload Tool**: Help users upload/update their resume

IMPORTANT:
1. **Prioritize Tool Usage:** BEFORE asking the user for information about their skills or background, USE YOUR AVAILABLE TOOLS (Profile Tool, Resume Tool) to retrieve their profile and resume data.
2. **Market-Aligned Suggestions:** Use Job Search Tool to understand current market demands and suggest projects that align with in-demand skills and technologies.
3. **Analyze User Input & Context:** Carefully analyze the 'User Query', 'Skill Level', 'Requested Domain/Focus', and the detailed 'User Profile' and 'User Resume' data. Pay close attention to explicit requests for domains like 'MBA' or 'business masters'.
4. **Adapt to Industry & Query Type:** Understand that 'projects' can range from software development to business strategy, research, marketing campaigns, financial modeling, operations optimization, and more. Adapt your suggestions based on the implied or explicit industry/domain in the user's query and their profile. **Crucially, if the query is for 'MBA projects' or related business studies, focus exclusively on business-oriented projects, leveraging any technical skills as a secondary asset within a business context (e.g., 'data-driven marketing strategy' instead of 'build a marketing app').**

For each project suggestion, provide the following details:
1. **Project Title and Description:** A clear, concise title and a detailed description of the project.
2. **Key Disciplines/Areas:** What business functions, academic disciplines, or technical areas does the project cover? (e.g., Marketing, Finance, Data Analysis, Supply Chain, Software Development, Research)
3. **Skills Gained/Applied:** List the specific skills the user will develop or utilize by completing this project.
4. **Tools & Resources:** Mention the relevant software, methodologies, frameworks, or data sources needed. For business projects, this might include Excel, Tableau, specific analytical models, case studies, industry reports, etc.
5. **Estimated Timeline & Difficulty:** Provide a realistic time estimate and a difficulty level (e.g., Beginner, Intermediate, Advanced).
6. **Deliverables & Portfolio Value:** What will be the tangible output of the project, and how does it enhance a professional portfolio or resume?
7. **Step-by-Step Approach:** Outline a high-level plan for how to approach the project.

Focus on projects that are:
* **Practical & Implementable:** Projects that can genuinely be carried out.
* **Relevant:** Aligned with current industry trends or academic requirements.
* **Portfolio-Worthy:** Demonstrates tangible skills and achievements.
* **Skill-Building Focused:** Designed to help the user learn and apply new concepts."""
    
    async def suggest_projects(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest projects based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            logger.info(f"🚀 Project suggestions with token: {token[:50] if token else 'None'}...")
            logger.info(f"🌐 Using base URL: {base_url}")
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            # Get user context
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Build context for project suggestions
            context = self._build_suggestion_context(original_query, extracted_data, profile_data, resume_data)
            
            # Generate suggestions using LLM
            suggestion_response = await self.llm_client.generate_response(context, self.system_message)
            
            # Format and return response
            return self._format_suggestion_response(suggestion_response, routing_data)
            
        except Exception as e:
            logger.error(f"Error suggesting projects: {str(e)}")
            return self.create_response(
                'plain_text',
                'I encountered an error while generating project suggestions. Please try again.',
                {'error': str(e)}
            )
    
    def _build_suggestion_context(self, query: str, extracted_data: Dict[str, Any], 
                                 profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> str:
        """Build context for project suggestions"""
        context = f"User Query: {query}\n"
        context += f"Skill Level: {extracted_data.get('skill_level', 'intermediate')}\n"
        context += f"Requested Domain/Focus: {extracted_data.get('domain', 'general')}\n"
        
        if profile_data and not profile_data.get('error'):
            context += f"User Profile Data: {profile_data}\n"
        else:
            context += "User Profile Data: Not available\n"
        
        if resume_data and not resume_data.get('error'):
            context += f"User Resume Data: {resume_data}\n"
        else:
            context += "User Resume Data: Not available\n"
        
        # Special handling for MBA/business projects
        if any(keyword in query.lower() for keyword in ['mba', 'business masters', 'business project', 'masters in business']):
            context += "\nIMPORTANT CONTEXT: If the user's query specifically requests 'MBA projects' or 'business masters projects', prioritize suggestions from business disciplines (e.g., Marketing, Finance, Strategy, Operations, HR) over technical ones, even if the user's profile indicates a strong technical background. The technical background can be leveraged *within* a business project (e.g., using data analytics for market research), but the core project should remain business-focused.\n"
        
        return context
    
    def _format_suggestion_response(self, suggestion_result: str, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format the project suggestion response"""
        from datetime import datetime
        extracted_data = routing_data.get('extractedData', {})
        
        metadata = {
            'skillLevel': extracted_data.get('skill_level', 'intermediate'),
            'technology': extracted_data.get('technology', 'general'),
            'domain': extracted_data.get('domain', 'general'),
            'suggestionDate': datetime.now().isoformat(),
            'originalQuery': routing_data.get('originalQuery')
        }
        
        return self.create_response('project_suggestion', suggestion_result, metadata)
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process project suggestion request"""
        return await self.suggest_projects(routing_data) 