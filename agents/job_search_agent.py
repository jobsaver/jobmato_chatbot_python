import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class JobSearchAgent(BaseAgent):
    """Agent responsible for handling job search requests"""
    
    async def search_jobs(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for jobs based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('body', {}).get('baseUrl', self.base_url)
            extracted_data = routing_data.get('extractedData', {})
            
            # Build search parameters
            search_params = self._build_search_params(extracted_data)
            
            # Call job search API
            job_data = await self.call_api(
                '/api/rag/jobs',
                token,
                method='GET',
                params=search_params,
                base_url=base_url
            )
            
            # Format the response
            return self._format_job_response(job_data, routing_data)
            
        except Exception as e:
            logger.error(f"Error in job search: {str(e)}")
            return self.create_response(
                'plain_text',
                'I encountered an error while searching for jobs. Please try again.',
                {'error': str(e)}
            )
    
    def _build_search_params(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build search parameters from extracted data"""
        params = {
            'limit': 10,
            'page': 1
        }
        
        # Map extracted data to API parameters
        if extracted_data.get('job_title'):
            params['job_title'] = extracted_data['job_title']
        if extracted_data.get('company'):
            params['company'] = extracted_data['company']
        if extracted_data.get('location'):
            params['locations'] = extracted_data['location']
        if extracted_data.get('skills'):
            params['skills'] = extracted_data['skills']
        if extracted_data.get('industry'):
            params['industry'] = extracted_data['industry']
        if extracted_data.get('domain'):
            params['domain'] = extracted_data['domain']
        if extracted_data.get('job_type'):
            params['job_type'] = extracted_data['job_type']
        if extracted_data.get('work_mode'):
            params['work_mode'] = extracted_data['work_mode']
        if extracted_data.get('experience_min'):
            params['experience_min'] = extracted_data['experience_min']
        if extracted_data.get('experience_max'):
            params['experience_max'] = extracted_data['experience_max']
        
        return params
    
    def _format_job_response(self, job_data: Dict[str, Any], routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format job search response"""
        if job_data.get('error'):
            return self.create_response(
                'plain_text',
                'I encountered an error while searching for jobs. Please try again.',
                {'error': job_data['error']}
            )
        
        jobs = job_data.get('jobs', [])
        if isinstance(jobs, list):
            formatted_jobs = [self._format_single_job(job) for job in jobs]
        else:
            formatted_jobs = []
        
        content = f"Found {len(formatted_jobs)} job opportunities matching your search:" if formatted_jobs else "No jobs found matching your criteria. Try adjusting your search parameters."
        
        metadata = {
            'jobs': formatted_jobs,
            'totalJobs': job_data.get('total', len(formatted_jobs)),
            'hasMore': (job_data.get('total', len(formatted_jobs))) > len(formatted_jobs),
            'currentPage': job_data.get('page', 1),
            'searchQuery': routing_data.get('searchQuery') or routing_data.get('originalQuery'),
            'searchParams': routing_data.get('extractedData', {})
        }
        
        return self.create_response('job_card', content, metadata)
    
    def _format_single_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Format a single job entry following the improved format"""
        return {
            'id': job.get('_id') or job.get('job_id'),
            'title': job.get('job_title') or job.get('title'),
            'company': job.get('company', {}).get('name') if isinstance(job.get('company'), dict) else job.get('company') or "Company not specified",
            'location': ', '.join(job.get('locations', [])) if isinstance(job.get('locations'), list) else job.get('location') or "Location not specified",
            'salary': job.get('salary') or "Salary not disclosed",
            'experience': job.get('experience') or "Experience not specified",
            'skills': job.get('skills')[:5] if isinstance(job.get('skills'), list) else [],
            'workMode': job.get('work_mode') or "Not specified",
            'jobType': job.get('job_type') or "Full-time",
            'description': job.get('description', {}).get('text') if isinstance(job.get('description'), dict) else job.get('description') or "",
            'postedDate': job.get('created_at') or job.get('posted_date'),
            'url': job.get('job_url') or job.get('url'),
            # Legacy fields for backward compatibility
            '_id': job.get('_id') or job.get('job_id'),
            'job_id': job.get('job_id') or job.get('id'),
            'job_title': job.get('job_title') or job.get('title'),
            'locations': job.get('locations') or ([job.get('location')] if job.get('location') else []),
            'work_mode': job.get('work_mode') or job.get('remote_type'),
            'job_type': job.get('job_type') or job.get('employment_type'),
            'posted_date': job.get('posted_date') or job.get('date_posted'),
            'source_url': job.get('source_url') or job.get('job_url'),
            'apply_url': job.get('apply_url') or job.get('application_url'),
            'source_platform': job.get('source_platform') or job.get('platform')
        }
    
    async def process_request(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process job search request"""
        return await self.search_jobs(routing_data) 