import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

class ResponseFormatter:
    """Utility class for formatting responses to match Dart ChatBoatHistoryModel"""
    
    def format_chat_response(
        self, 
        content: str, 
        response_type: str = 'plain_text',
        metadata: Dict[str, Any] = None,
        role: str = 'assistant'
    ) -> Dict[str, Any]:
        """Format response to match Dart ChatBoatHistoryModel structure"""
        
        # Map response types to Dart MessageType enum values
        type_mapping = {
            'plain_text': 'plain_text',
            'markdown': 'markdown', 
            'job_card': 'job_card',
            'resume_analysis': 'resume_analysis',
            'career_advice': 'career_advice',
            'project_suggestion': 'project_suggestion',
            'resume_upload_required': 'resume_upload_required',
            'resume_upload_success': 'resume_upload_success'
        }
        
        message_type = type_mapping.get(response_type, 'plain_text')
        
        # Create metadata structure matching Dart model
        formatted_metadata = {
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z",
            **(metadata or {})
        }
        
        return {
            'role': role,
            'content': content.strip(),
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z",
            'type': message_type,
            'id': str(uuid.uuid4()),
            'metadata': formatted_metadata
        }
    
    def format_job_response(self, jobs: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format job search response"""
        if not jobs:
            content = "No jobs found matching your criteria. Try adjusting your search parameters."
        else:
            content = f"Found {len(jobs)} job opportunities matching your search:"
        
        # Format jobs to match Dart Job model structure
        formatted_jobs = []
        for job in jobs:
            formatted_job = self._format_single_job(job)
            formatted_jobs.append(formatted_job)
        
        job_metadata = {
            'agent': 'job_search',
            'intent': 'job_search',
            'confidence': metadata.get('confidence', 0.9),
            'jobs': formatted_jobs,
            'totalJobs': metadata.get('total', len(jobs)),
            'hasMore': metadata.get('hasMore', False),
            'currentPage': metadata.get('page', 1),
            'searchParams': metadata.get('searchParams', {}),
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
        }
        
        return self.format_chat_response(
            content=content,
            response_type='job_card',
            metadata=job_metadata
        )
    
    def format_career_advice_response(self, advice: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format career advice response"""
        career_metadata = {
            'agent': 'career_advice',
            'intent': 'career_advice',
            'confidence': metadata.get('confidence', 0.9),
            'careerStage': metadata.get('careerStage', 'not specified'),
            'industry': metadata.get('industry', 'not specified'),
            'specificQuestion': metadata.get('specificQuestion', 'general advice'),
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
        }
        
        return self.format_chat_response(
            content=advice,
            response_type='career_advice',
            metadata=career_metadata
        )
    
    def format_resume_analysis_response(self, analysis: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format resume analysis response"""
        resume_metadata = {
            'agent': 'resume_analysis',
            'intent': 'resume_analysis',
            'confidence': metadata.get('confidence', 0.9),
            'analysisType': 'resume_analysis',
            'originalQuery': metadata.get('originalQuery', ''),
            'sessionId': metadata.get('sessionId', 'default'),
            'hasResume': metadata.get('hasResume', True),
            'uploadRequired': metadata.get('uploadRequired', False),
            'allowReupload': metadata.get('allowReupload', True),
            'generalResumeReply': metadata.get('generalResumeReply', False),
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
        }
        
        return self.format_chat_response(
            content=analysis,
            response_type='resume_analysis',
            metadata=resume_metadata
        )
    
    def format_project_suggestion_response(self, suggestions: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Format project suggestion response"""
        project_metadata = {
            'agent': 'project_suggestion',
            'intent': 'project_suggestion',
            'confidence': metadata.get('confidence', 0.9),
            'skillLevel': metadata.get('skillLevel', 'intermediate'),
            'technology': metadata.get('technology', 'general'),
            'domain': metadata.get('domain', 'general'),
            'originalQuery': metadata.get('originalQuery', ''),
            'suggestedProjects': metadata.get('suggestedProjects', []),
            'learningPath': metadata.get('learningPath', []),
            'technologyStack': metadata.get('technologyStack', {}),
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
        }
        
        return self.format_chat_response(
            content=suggestions,
            response_type='project_suggestion',
            metadata=project_metadata
        )
    
    def format_plain_text_response(self, content: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format plain text response"""
        plain_metadata = {
            'agent': 'general_chat',
            'intent': 'general_chat',
            'confidence': metadata.get('confidence', 0.9) if metadata else 0.9,
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z",
            **(metadata or {})
        }
        
        return self.format_chat_response(
            content=content,
            response_type='plain_text',
            metadata=plain_metadata
        )
    
    def format_error_response(self, error_message: str, error_details: str = None) -> Dict[str, Any]:
        """Format error response"""
        error_metadata = {
            'agent': 'error_handler',
            'intent': 'error',
            'confidence': 1.0,
            'error': True,
            'errorDetails': error_details,
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z"
        }
        
        return self.format_chat_response(
            content=error_message,
            response_type='plain_text',
            metadata=error_metadata
        )
    
    def format_resume_upload_required_response(self, message: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format resume upload required response"""
        upload_metadata = {
            'agent': 'resume_analysis',
            'intent': 'resume_upload_required',
            'confidence': 1.0,
            'hasResume': False,
            'uploadRequired': True,
            'allowReupload': True,
            'generalResumeReply': False,
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z",
            **(metadata or {})
        }
        
        return self.format_chat_response(
            content=message,
            response_type='resume_upload_required',
            metadata=upload_metadata
        )
    
    def format_resume_upload_success_response(self, message: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format resume upload success response"""
        upload_success_metadata = {
            'agent': 'resume_analysis',
            'intent': 'resume_upload_success',
            'confidence': 1.0,
            'hasResume': True,
            'uploadRequired': False,
            'allowReupload': True,
            'generalResumeReply': False,
            'uploadSuccess': True,
            'timestamp': datetime.now(timezone.utc).isoformat() + "Z",
            **(metadata or {})
        }
        
        return self.format_chat_response(
            content=message,
            response_type='resume_upload_success',
            metadata=upload_success_metadata
        )
    
    def _format_single_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single job to match Dart Job model structure"""
        def safe_get_string(value, default=""):
            """Safely extract string value from potentially complex objects"""
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                return value.get('name', value.get('title', value.get('display_name', default)))
            elif isinstance(value, list):
                return ', '.join([safe_get_string(item) for item in value])
            elif value is None:
                return default
            else:
                return str(value)
        
        def safe_get_list(value, default=None):
            """Safely extract list value"""
            if isinstance(value, list):
                return value
            elif isinstance(value, str):
                return [value]
            elif value is None:
                return default or []
            else:
                return [str(value)]
        
        # Format company information
        company_info = None
        if job.get('company'):
            if isinstance(job['company'], dict):
                company_info = {
                    'name': job['company'].get('name', ''),
                    'url': job['company'].get('url', ''),
                    'logo': job['company'].get('logo', ''),
                    'size': job['company'].get('size', ''),
                    'sector': job['company'].get('sector', '')
                }
            else:
                company_info = {
                    'name': safe_get_string(job['company']),
                    'url': '',
                    'logo': '',
                    'size': '',
                    'sector': ''
                }
        
        # Format experience information
        experience_info = None
        if job.get('experience'):
            if isinstance(job['experience'], dict):
                experience_info = {
                    'minYears': job['experience'].get('min', job['experience'].get('min_years')),
                    'maxYears': job['experience'].get('max', job['experience'].get('max_years'))
                }
            else:
                experience_info = {
                    'minYears': None,
                    'maxYears': None
                }
        
        # Format salary information
        salary_info = None
        if job.get('salary'):
            if isinstance(job['salary'], dict):
                salary_info = {
                    'currency': job['salary'].get('currency', ''),
                    'tenure': job['salary'].get('tenure', ''),
                    'min': job['salary'].get('min', ''),
                    'max': job['salary'].get('max', ''),
                    'display': job['salary'].get('display', '')
                }
            else:
                salary_info = {
                    'currency': '',
                    'tenure': '',
                    'min': safe_get_string(job['salary']),
                    'max': '',
                    'display': safe_get_string(job['salary'])
                }
        
        return {
            'id': job.get('_id', ''),
            'jobId': job.get('job_id', ''),
            'jobTitle': safe_get_string(job.get('job_title'), 'Job Title'),
            'company': company_info,
            'locations': safe_get_list(job.get('locations')),
            'location': safe_get_string(job.get('locations', [])[0] if job.get('locations') else job.get('location'), 'Location'),
            'experience': experience_info,
            'salary': salary_info,
            'skills': safe_get_list(job.get('skills')),
            'workMode': safe_get_string(job.get('work_mode'), 'Work Mode'),
            'jobType': safe_get_string(job.get('job_type'), 'Job Type'),
            'description': safe_get_string(job.get('description'), 'Description'),
            'postedDate': job.get('posted_date'),
            'sourceUrl': safe_get_string(job.get('source_url'), ''),
            'applyUrl': job.get('apply_url', ''),
            'sourcePlatform': safe_get_string(job.get('source_platform'), '')
        } 