import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """Utility class for formatting responses"""
    
    def format_job_response(self, jobs: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format job search response"""
        if not jobs:
            content = "No jobs found matching your criteria. Try adjusting your search parameters."
        else:
            content = f"Found {len(jobs)} job opportunities matching your search:"
        
        return {
            'type': 'job_card',
            'content': content,
            'metadata': {
                'jobs': jobs,
                'totalJobs': metadata.get('total', len(jobs)),
                'hasMore': metadata.get('hasMore', False),
                'currentPage': metadata.get('page', 1),
                'searchQuery': metadata.get('searchQuery', ''),
                'searchParams': metadata.get('searchParams', {})
            }
        }
    
    def format_career_advice_response(self, advice: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format career advice response"""
        return {
            'type': 'career_advice',
            'content': advice,
            'metadata': {
                'careerStage': metadata.get('careerStage', 'not specified'),
                'industry': metadata.get('industry', 'not specified'),
                'specificQuestion': metadata.get('specificQuestion', 'general advice'),
                'adviceDate': datetime.now().isoformat()
            }
        }
    
    def format_resume_analysis_response(self, analysis: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format resume analysis response"""
        return {
            'type': 'resume_analysis',
            'content': analysis,
            'metadata': {
                'analysisType': 'resume_analysis',
                'analysisDate': datetime.now().isoformat(),
                'originalQuery': metadata.get('originalQuery', ''),
                'sessionId': metadata.get('sessionId', 'default')
            }
        }
    
    def format_project_suggestion_response(self, suggestions: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format project suggestion response"""
        return {
            'type': 'project_suggestion',
            'content': suggestions,
            'metadata': {
                'skillLevel': metadata.get('skillLevel', 'intermediate'),
                'technology': metadata.get('technology', 'general'),
                'domain': metadata.get('domain', 'general'),
                'suggestionDate': datetime.now().isoformat(),
                'originalQuery': metadata.get('originalQuery', '')
            }
        }
    
    def format_plain_text_response(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format plain text response"""
        return {
            'type': 'plain_text',
            'content': content,
            'metadata': metadata or {
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def format_error_response(self, error_message: str, error_details: str = None) -> Dict[str, Any]:
        """Format error response"""
        return {
            'type': 'plain_text',
            'content': error_message,
            'metadata': {
                'error': True,
                'errorDetails': error_details,
                'timestamp': datetime.now().isoformat()
            }
        } 