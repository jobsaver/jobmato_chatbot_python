import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent
from utils.llm_client import LLMClient
import json
import redis
from config import config
import os

logger = logging.getLogger(__name__)

class JobSearchAgent(BaseAgent):
    """Agent responsible for handling job search requests"""
    
    UNREALISTIC_LOCATIONS = {"mars", "moon", "jupiter", "saturn", "venus", "pluto", "mercury", "neptune", "uranus", "andromeda", "milky way", "galaxy", "space", "sun"}
    
    def __init__(self, memory_manager=None):
        super().__init__(memory_manager)
        self.llm_client = LLMClient()
        self.system_message = """
        You are the JobMato Job Search Assistant, specialized in helping users find relevant job opportunities. You can understand and respond in English, Hindi, and Hinglish naturally.

        PERSONALITY TRAITS:
        - Professional yet friendly
        - Enthusiastic about job opportunities
        - Match user's language preference (English/Hindi/Hinglish)
        - Use conversation context to provide better recommendations

        LANGUAGE HANDLING:
        - If user speaks Hinglish, respond in Hinglish
        - If user speaks Hindi, respond in Hindi  
        - If user speaks English, respond in English
        - Use natural code-switching for Hinglish users

        RESPONSE FORMAT:
        When presenting job results, format them clearly with:
        - Job title and company
        - Location and work mode
        - Key requirements
        - Brief description
        - Application link or next steps

        Always consider the conversation history to provide contextual recommendations.
        """
            
    async def search_jobs(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for jobs using JobMato Tools with enhanced fallback logic"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            session_id = routing_data.get('sessionId', 'default')
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            conversation_context = routing_data.get('conversation_context', '')
            
            # Log extracted data for debugging
            logger.info(f"📊 Extracted data received: {extracted_data}")
            
            # Log conversation context for debugging
            if conversation_context:
                logger.info(f"📝 Using conversation context: {conversation_context[:200]}...")
            
            # Add this helper at the top of the class
            extracted_location = extracted_data.get('location', '')
            if self._is_unrealistic_location(extracted_location):
                return self.response_formatter.format_plain_text_response(
                    content="Sorry, I can't find jobs on Mars yet! 🚀 But I can help you find great opportunities here on Earth. Where would you like to work?",
                    metadata={
                        'error': 'unrealistic_location',
                        'category': 'JOB_SEARCH',
                        'location': extracted_location
                    }
                )
            
            # Build comprehensive search parameters
            search_params = await self._build_search_params(extracted_data, {}, {})
            
            # First attempt with original parameters
            logger.info(f"🔍 First attempt search params: {search_params}")
            job_search_result = await self.search_jobs_tool(token, base_url, **search_params)
            
            # Enhanced error handling with detailed API response analysis
            if not job_search_result.get('success'):
                error_msg = job_search_result.get('error', 'Unknown error')
                response_time = job_search_result.get('response_time', 0)
                
                if job_search_result.get('timeout'):
                    logger.error(f"⏰ API timeout after {response_time:.2f}s for query: {original_query}")
                    return self.response_formatter.format_error_response(
                        error_message=f"Sorry, the job search took too long to respond ({response_time:.1f}s). The job database might be busy right now. Please try again in a moment! 🔄",
                        error_details={
                            'error_type': 'timeout',
                            'response_time': response_time,
                            'search_params': search_params,
                            'query': original_query
                        }
                    )
                elif job_search_result.get('connection_error'):
                    logger.error(f"🔌 Connection failed for query: {original_query}")
                    return self.response_formatter.format_error_response(
                        error_message="Sorry, I couldn't connect to the job database right now. Please check your internet connection and try again! 🌐",
                        error_details={
                            'error_type': 'connection_error',
                            'original_error': error_msg,
                            'search_params': search_params
                        }
                    )
                else:
                    logger.error(f"❌ API error for query '{original_query}': {error_msg}")
                    return self._handle_search_failure(
                        original_query, 
                        extracted_data.get('language', 'english'),
                        {
                            'error_type': 'api_error',
                            'original_error': error_msg,
                            'response_time': response_time
                        }
                    )
            
            jobs_data = job_search_result.get('data', {})
            jobs = jobs_data.get('jobs', [])
            response_time = job_search_result.get('response_time', 0)
            logger.info(f"⏱️ First search completed in {response_time:.2f}s")
            
            # If less than 10 jobs found, try with broader filters (without job_title)
            if len(jobs) < 10:
                logger.info(f"🔄 Found only {len(jobs)} jobs, trying with broader filters (removing job_title)...")
                broader_params = await self._build_broader_search_params(extracted_data, search_params)
                logger.info(f"🔍 Broader search params: {broader_params}")
                
                broader_result = await self.search_jobs_tool(token, base_url, **broader_params)
                
                if broader_result.get('success'):
                    broader_jobs_data = broader_result.get('data', {})
                    broader_jobs = broader_jobs_data.get('jobs', [])
                    broader_response_time = broader_result.get('response_time', 0)
                    
                    if broader_jobs:
                        # Combine original jobs with broader search results, avoiding duplicates
                        original_job_count = len(jobs)
                        original_job_ids = {job.get('_id') or job.get('id') for job in jobs if job.get('_id') or job.get('id')}
                        unique_broader_jobs = [
                            job for job in broader_jobs 
                            if (job.get('_id') or job.get('id')) not in original_job_ids
                        ]
                        
                        # Combine jobs (original first, then unique broader results)
                        combined_jobs = jobs + unique_broader_jobs[:10-len(jobs)]  # Limit to 10 total
                        jobs = combined_jobs
                        
                        # Update jobs_data with combined results
                        jobs_data['jobs'] = jobs
                        jobs_data['total'] = max(jobs_data.get('total', 0), broader_jobs_data.get('total', 0))
                        
                        logger.info(f"✅ Combined {len(combined_jobs)} jobs (original: {original_job_count}, broader: {len(unique_broader_jobs)}) in {broader_response_time:.2f}s")
                        # Use broader params for pagination to get more results
                        search_params = broader_params
                    else:
                        logger.info(f"❌ No additional jobs found with broader filters ({broader_response_time:.2f}s)")
                        if len(jobs) == 0:
                            return self._handle_no_jobs_found(original_query, search_params, extracted_data.get('language', 'english'))
                else:
                    # Handle broader search errors too
                    broader_error = broader_result.get('error', 'Unknown error')
                    broader_response_time = broader_result.get('response_time', 0)
                    
                    if broader_result.get('timeout'):
                        logger.error(f"⏰ Broader search also timed out after {broader_response_time:.2f}s")
                        return self.response_formatter.format_error_response(
                            error_message=f"Both searches timed out ({broader_response_time:.1f}s). The job database seems overloaded. Please try again later! ⏰",
                            error_details={
                                'error_type': 'broader_search_timeout',
                                'response_time': broader_response_time
                            }
                        )
                    elif broader_result.get('connection_error'):
                        logger.error(f"🔌 Broader search connection failed")
                        return self.response_formatter.format_error_response(
                            error_message="Connection failed during broader search. Please check your connection and try again! 🔌",
                            error_details={
                                'error_type': 'broader_search_connection_error',
                                'original_error': broader_error
                            }
                        )
                    else:
                        logger.info(f"❌ Broader search also failed: {broader_error}")
                        return self._handle_search_failure(
                            original_query, 
                            extracted_data.get('language', 'english'),
                            {
                                'error_type': 'broader_search_failed',
                                'original_error': broader_error,
                                'response_time': broader_response_time
                            }
                        )
            
            # Format jobs for response (don't send raw data to AI)
            formatted_jobs = []
            for job in jobs:
                formatted_job = self.format_job_for_response(job)
                formatted_jobs.append(formatted_job)
            
            # Get total available jobs from API response first
            total_available = jobs_data.get('total', len(formatted_jobs))
            has_more = total_available > 10
            
            # Create dynamic 2-line message based on results
            total_jobs = len(formatted_jobs)
            search_query = routing_data.get('searchQuery') or routing_data.get('originalQuery', 'default search')
            
            if total_jobs == 1:
                content = f"Here's a job opportunity that matches your search for '{search_query}':"
            else:
                content = f"Here are {total_jobs} job opportunities that might interest you:"

            # Store search context for follow-up searches
            search_context = {
                'skills': search_params.get('skills'),
                'location': extracted_data.get('location'),
                'query': extracted_data.get('query'),
                'internship': extracted_data.get('internship'),
                'experience_min': extracted_data.get('experience_min'),
                'experience_max': extracted_data.get('experience_max'),
                'job_title': extracted_data.get('job_title'),
                'original_query': original_query,
                'search_params': search_params,  # Store full search params for load more
                'total_available': total_available,
                'current_page': 1
            }
            
            # Storage is handled by app.py to avoid duplication
            
            # Storage is handled by app.py to avoid duplication
            
            # Store current page in Redis for pagination tracking
            try:
                current_config = config[os.environ.get('FLASK_ENV', 'development')]
                redis_url = current_config.REDIS_URL
                redis_ssl = current_config.REDIS_SSL
                
                if redis_ssl:
                    redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        ssl=True,
                        ssl_cert_reqs=None
                    )
                else:
                    redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True
                    )
                
                session_id = routing_data.get('sessionId', 'default')
                redis_client.setex(f"last_page:{session_id}", 3600, "1")  # Store current page
                logger.info(f"💾 Stored current page 1 for session {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Could not store current page: {str(e)}")

            return self.response_formatter.format_job_response(
                jobs=formatted_jobs,
                metadata={
                    'total': total_available,
                    'hasMore': has_more,
                    'page': 1,
                    'searchQuery': search_query,
                    'searchParams': search_params,
                    'searchContext': search_context
                }
            )
            
        except Exception as e:
            logger.error(f"Error in job search: {str(e)}")
            return self.response_formatter.format_error_response(
                error_message='Sorry yaar, job search mein kuch technical issue ho gaya! 😅 Please try again, main help karunga.',
                error_details=str(e)
            )
    
    def _safe_extract(self, obj, key, default=""):
        """Safely extract a value from an object, handling nested structures"""
        try:
            if isinstance(obj, dict):
                value = obj.get(key, default)
            elif hasattr(obj, key):
                value = getattr(obj, key, default)
            else:
                value = default
            
            # Handle nested objects and lists
            if isinstance(value, (dict, list)):
                if isinstance(value, dict):
                    # For nested objects, try to get a meaningful string representation
                    if 'name' in value:
                        return str(value['name'])
                    elif 'text' in value:
                        return str(value['text'])
                    else:
                        return str(value)
                elif isinstance(value, list):
                    # For lists, join with commas
                    return ', '.join(str(item) for item in value[:3])  # Limit to first 3 items
            else:
                return str(value) if value is not None else default
        except Exception as e:
            logger.warning(f"⚠️ Error extracting {key} from {type(obj)}: {str(e)}")
            return default

    def format_job_for_response(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Format job data for response following the specified structure"""
        
        def safe_get_string(value, default=""):
            """Safely extract string value from potentially complex objects"""
            if isinstance(value, str):
                return value
            elif isinstance(value, dict):
                # Try to get name or title from object
                return value.get('name', value.get('title', value.get('display_name', default)))
            elif isinstance(value, list):
                # Join list items
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
        
        return {
            '_id': job.get('_id'),
            'job_id': job.get('job_id'),
            'job_title': safe_get_string(job.get('job_title'), 'Job Title'),
            'company': safe_get_string(job.get('company'), 'Company'),
            'locations': safe_get_list(job.get('locations')),
            'location': safe_get_string(job.get('locations', [])[0] if job.get('locations') else job.get('location'), 'Location'),
            'experience': safe_get_string(job.get('experience'), 'Experience'),
            'salary': safe_get_string(job.get('salary'), 'Salary'),
            'skills': safe_get_list(job.get('skills')),
            'work_mode': safe_get_string(job.get('work_mode'), 'Work Mode'),
            'job_type': safe_get_string(job.get('job_type'), 'Job Type'),
            'description': safe_get_string(job.get('description'), 'Description'),
            'posted_date': safe_get_string(job.get('posted_date'), 'Posted Date'),
            'source_url': safe_get_string(job.get('source_url'), ''),
            'apply_url': safe_get_string(job.get('apply_url'), ''),
            'source_platform': safe_get_string(job.get('source_platform'), ''),
        }
    
    def _handle_search_failure(self, original_query: str, language: str = 'english', error_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle job search failure with detailed error information"""
        
        # Build user-friendly error message
        if language in ['hindi', 'hinglish']:
            if error_details and error_details.get('error_type') == 'timeout':
                content = f"Sorry yaar, '{original_query}' ke liye search slow ho raha hai! Database busy hai. Please thoda wait karo aur try again! ⏰"
            elif error_details and error_details.get('error_type') == 'connection_error':
                content = f"Sorry yaar, job database se connection nahi ho raha! Internet check karo aur try again! 🌐"
            else:
                content = f"Sorry yaar, '{original_query}' ke liye job search mein kuch technical issue ho gaya! 😅 Please try again with different keywords."
        else:
            if error_details and error_details.get('error_type') == 'timeout':
                content = f"Sorry, the search for '{original_query}' is taking too long. The database seems busy. Please try again in a moment! ⏰"
            elif error_details and error_details.get('error_type') == 'connection_error':
                content = f"Sorry, I couldn't connect to the job database while searching for '{original_query}'. Please check your internet connection! 🌐"
            else:
                content = f"Sorry, I encountered a technical issue while searching for '{original_query}'. Please try again with different keywords."
        
        # Add helpful suggestions
        content += "\n\n🔧 **Troubleshooting Tips:**\n"
        content += "• Check your internet connection\n"
        content += "• Try simpler search terms\n"
        content += "• Wait a moment and try again\n"
        content += "• Contact support if the issue persists"
        
        return self.response_formatter.format_error_response(
            error_message=content,
            error_details=error_details or {'error_type': 'search_failed', 'query': original_query}
        )
    
    def _handle_no_jobs_found(self, original_query: str, search_params: Dict[str, Any], language: str = 'english') -> Dict[str, Any]:
        """Handle case when no jobs are found even after broader search"""
        if language in ['hindi', 'hinglish']:
            content = f"'{original_query}' ke liye koi jobs nahi mili, even after trying broader filters. Try these suggestions:\n\n"
            content += "🔍 **Search Tips:**\n"
            content += "• Use simpler keywords like 'developer' instead of 'React developer'\n"
            content += "• Remove location restrictions\n"
            content += "• Try different job titles\n"
            content += "• Check spelling of keywords\n\n"
            content += "💡 **Alternative Searches:**\n"
            content += "• 'software developer jobs'\n"
            content += "• 'IT jobs'\n"
            content += "• 'tech jobs'\n"
            content += "• 'remote jobs'"
        else:
            content = f"No jobs found for '{original_query}', even after trying broader filters. Here are some suggestions:\n\n"
            content += "🔍 **Search Tips:**\n"
            content += "• Use simpler keywords like 'developer' instead of 'React developer'\n"
            content += "• Remove location restrictions\n"
            content += "• Try different job titles\n"
            content += "• Check spelling of keywords\n\n"
            content += "💡 **Alternative Searches:**\n"
            content += "• 'software developer jobs'\n"
            content += "• 'IT jobs'\n"
            content += "• 'tech jobs'\n"
            content += "• 'remote jobs'"
        
        return self.response_formatter.format_plain_text_response(
            content=content,
            metadata={
                'error': 'no_jobs_found',
                'category': 'JOB_SEARCH',
                'searchParams': search_params,
                'suggestions': [
                    'Use simpler keywords',
                    'Remove location restrictions', 
                    'Try different job titles',
                    'Check spelling',
                    'Search for "developer jobs"',
                    'Search for "IT jobs"',
                    'Search for "remote jobs"'
                ],
                'broaderSearchAttempted': True
            }
        )
    
    async def _build_search_params(self, extracted_data: Dict[str, Any], profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive search parameters from extracted data using JobMato Tools"""
        params = {
            'limit': 10,  # Show 10 jobs per page
            'page': 1
        }
        
        # 🔍 Basic search parameters
        if extracted_data.get('query'):
            params['query'] = extracted_data['query']
        if extracted_data.get('search'):
            params['search'] = extracted_data['search']
        if extracted_data.get('searchQuery'):
            params['query'] = extracted_data['searchQuery']
        
        # Handle job_title or job_title_keywords
        job_title = extracted_data.get('job_title') or extracted_data.get('job_title_keywords') or extracted_data.get('keywords')
        if job_title:
            # Convert to string if it's a list
            if isinstance(job_title, list):
                job_title = ' '.join(job_title) if job_title else ''
            params['job_title'] = str(job_title)
            
        if extracted_data.get('company'):
            params['company'] = extracted_data['company']
        
        # 📍 Location parameters
        if extracted_data.get('location'):
            params['locations'] = extracted_data['location']
        if extracted_data.get('locations'):
            params['locations'] = extracted_data['locations']
        
        # 🛠️ Skills and domain parameters - Enhanced with auto-skill detection
        skills = await self._enhance_skills_from_job_title(extracted_data)
        if skills:
            params['skills'] = skills
            logger.info(f"🎯 Using enhanced skills: {skills}")
        elif extracted_data.get('skills'):
            # Convert skills list to comma-separated string if needed
            skills_value = extracted_data['skills']
            if isinstance(skills_value, list):
                params['skills'] = ', '.join(skills_value)
            else:
                params['skills'] = str(skills_value)
            logger.info(f"🎯 Using extracted skills: {params['skills']}")
            
        if extracted_data.get('industry'):
            params['industry'] = extracted_data['industry']
        if extracted_data.get('domain'):
            params['domain'] = extracted_data['domain']
        
        # 💼 Job type and work mode parameters
        if extracted_data.get('job_type'):
            params['job_type'] = extracted_data['job_type']
        if extracted_data.get('work_mode'):
            params['work_mode'] = extracted_data['work_mode']
        
        # 📅 Experience parameters
        if extracted_data.get('experience_min') is not None:
            params['experience_min'] = extracted_data['experience_min']
        if extracted_data.get('experience_max') is not None:
            params['experience_max'] = extracted_data['experience_max']
        
        # 💰 Salary parameters - Convert from thousands to actual rupee amounts
        if extracted_data.get('salary_min') is not None:
            # Query classifier sends values in thousands (e.g., 20 for 20k, 500 for 5 lakh)
            # API expects actual rupee amounts (e.g., 20000, 500000)
            salary_min_thousands = extracted_data['salary_min']
            params['salary_min'] = int(salary_min_thousands * 1000)
            logger.info(f"💰 Converting salary_min: {salary_min_thousands}k → {params['salary_min']} rupees")
        if extracted_data.get('salary_max') is not None:
            # Query classifier sends values in thousands (e.g., 50 for 50k, 1000 for 10 lakh)
            # API expects actual rupee amounts (e.g., 50000, 1000000)
            salary_max_thousands = extracted_data['salary_max']
            params['salary_max'] = int(salary_max_thousands * 1000)
            logger.info(f"💰 Converting salary_max: {salary_max_thousands}k → {params['salary_max']} rupees")
        
        # 🎓 Internship filter - IMPROVED LOGIC
        # Check for internship request from multiple sources
        is_internship_request = (
            extracted_data.get('internship') is True or 
            extracted_data.get('job_type') == 'internship' or
            (extracted_data.get('job_title', '').lower().find('intern') != -1)
        )
        
        if is_internship_request:
            # Always set internship=True when user explicitly requests internships
            params['internship'] = True
            params['job_type'] = 'internship'
            # Remove any experience parameters for internships
            params.pop('experience_min', None)
            params.pop('experience_max', None)
            logger.info(f"🎓 Detected internship request - setting internship=True and removing experience filters")
        elif extracted_data.get('internship') is False:
            # User explicitly said no internships
            params['internship'] = False
            params['job_type'] = 'full-time'
            logger.info(f"💼 User explicitly requested non-internship positions")
        else:
            # No explicit internship request - check if we should default based on skills
            has_substantial_skills = self._has_substantial_technical_skills(extracted_data, profile_data, resume_data)
            if has_substantial_skills:
                params['internship'] = False
                params['job_type'] = 'full-time'
                logger.info(f"💼 Defaulting to full-time positions for user with substantial skills")
            # If no substantial skills, don't set internship filter to allow both types
        
        # 📄 Pagination parameters
        if extracted_data.get('limit'):
            params['limit'] = extracted_data['limit']
        if extracted_data.get('page'):
            params['page'] = extracted_data['page']
        
        logger.info(f"🔧 Built comprehensive search params: {params}")
        logger.info(f"📊 Input extracted_data was: {extracted_data}")
        return params
    
    def _has_substantial_technical_skills(self, extracted_data: Dict[str, Any], profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> bool:
        """Check if user has substantial technical skills that suggest they're beyond internship level"""
        # Define substantial technical skills that indicate professional experience
        substantial_skills = [
            'java', 'kotlin', 'android', 'react', 'node.js', 'python', 'javascript', 'typescript',
            'mongodb', 'mysql', 'aws', 'docker', 'kubernetes', 'git', 'spring', 'django', 'flask',
            'express', 'angular', 'vue', 'php', 'c#', 'c++', 'go', 'rust', 'swift', 'objective-c',
            'tensorflow', 'pytorch', 'machine learning', 'data science', 'devops', 'cloud',
            'microservices', 'rest api', 'graphql', 'sql', 'nosql', 'redis', 'elasticsearch'
        ]
        
        # Check skills from extracted data
        skills_value = extracted_data.get('skills', '')
        if isinstance(skills_value, list):
            skills_text = ' '.join(skills_value).lower()
        else:
            skills_text = str(skills_value).lower()
        
        if skills_text:
            found_skills = [skill for skill in substantial_skills if skill in skills_text]
            if len(found_skills) >= 3:  # At least 3 substantial skills
                logger.info(f"🎯 Found substantial skills in extracted data: {found_skills}")
                return True
        
        # Check skills from profile data
        if profile_data and not profile_data.get('error'):
            profile_skills = str(profile_data.get('skills', '')).lower()
            if profile_skills:
                found_skills = [skill for skill in substantial_skills if skill in profile_skills]
                if len(found_skills) >= 3:
                    logger.info(f"🎯 Found substantial skills in profile data: {found_skills}")
                    return True
        
        # Check skills from resume data
        if resume_data and not resume_data.get('error'):
            resume_skills = str(resume_data.get('skills', '')).lower()
            if resume_skills:
                found_skills = [skill for skill in substantial_skills if skill in resume_skills]
                if len(found_skills) >= 3:
                    logger.info(f"🎯 Found substantial skills in resume data: {found_skills}")
                    return True
        
        # Check for experience indicators
        experience_indicators = ['experience', 'senior', 'lead', 'architect', 'manager', 'developer', 'engineer']
        
        # Check in extracted data
        query_value = extracted_data.get('query', '')
        if isinstance(query_value, list):
            query_text = ' '.join(query_value).lower()
        else:
            query_text = str(query_value).lower()

        if any(indicator in query_text for indicator in experience_indicators):
            logger.info(f"🎯 Found experience indicators in query: {query_text}")
            return True
        
        # Check in profile data
        if profile_data and not profile_data.get('error'):
            profile_text = str(profile_data).lower()
            if any(indicator in profile_text for indicator in experience_indicators):
                logger.info(f"🎯 Found experience indicators in profile data")
                return True
        
        # Check in resume data
        if resume_data and not resume_data.get('error'):
            resume_text = str(resume_data).lower()
            if any(indicator in resume_text for indicator in experience_indicators):
                logger.info(f"🎯 Found experience indicators in resume data")
                return True
        
        logger.info(f"⚠️ User appears to be entry-level, suitable for internships")
        return False
    
    async def _enhance_skills_from_job_title(self, extracted_data: Dict[str, Any]) -> str:
        """Enhance skills using LLM if not provided by query classifier"""
        # Handle different job title field names
        job_title = extracted_data.get('job_title') or extracted_data.get('job_title_keywords', '') or extracted_data.get('keywords', '')
        
        # Convert job_title to string if it's a list
        if isinstance(job_title, list):
            job_title = ' '.join(job_title) if job_title else ''
        
        job_title = str(job_title).strip()
        
        existing_skills = extracted_data.get('skills', '')
        
        # If skills are already provided by query classifier, use them
        if existing_skills:
            # Convert skills to string if it's a list
            if isinstance(existing_skills, list):
                return ', '.join(existing_skills)
            return str(existing_skills)
        
        # If no skills and no job title, return empty
        if not job_title:
            logger.info(f"⚠️ No job title or skills provided for skill enhancement")
            return ""
        
        # Use LLM to dynamically detect skills based on job title
        try:
            prompt = f"Extract the top 5-8 most relevant technical skills for a '{job_title}' position. Return only a comma-separated list of skills, no explanations."
            
            response = await self.llm_client.generate_response(
                prompt,
                "You are a career advisor. Extract relevant technical skills for job positions. Return only comma-separated skills, no other text."
            )
            
            # Clean up the response
            skills = response.strip().replace('\n', '').replace('"', '').replace('Skills:', '').strip()
            
            if skills and len(skills) > 5:  # Basic validation
                logger.info(f"🎯 LLM-generated skills for '{job_title}': {skills}")
                return skills
            else:
                logger.warning(f"⚠️ LLM returned invalid skills for '{job_title}': {response}")
                return ""
                
        except Exception as e:
            logger.error(f"❌ Error getting LLM skills for '{job_title}': {str(e)}")
            logger.info(f"⚠️ No skills auto-detected for job title: {job_title}")
            return ""
    
    def _enhance_search_params(self, params: Dict[str, Any], routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance search parameters with intelligent defaults and optimizations"""
        
        # Auto-detect internship based on query keywords
        original_query = routing_data.get('originalQuery', '').lower()
        if any(keyword in original_query for keyword in ['intern', 'internship', 'trainee', 'graduate']):
            params['internship'] = True
            params['job_type'] = 'internship'
            # Remove any experience parameters for internships
            params.pop('experience_min', None)
            params.pop('experience_max', None)
            
            # 🎓 Clean job title if it contains internship keywords
            if params.get('job_title'):
                params = self._clean_internship_job_title(params)
        
        # Auto-detect remote work preference
        if any(keyword in original_query for keyword in ['remote', 'work from home', 'wfh']):
            params['work_mode'] = 'remote'
        elif any(keyword in original_query for keyword in ['on-site', 'office', 'onsite']):
            params['work_mode'] = 'on-site'
        elif any(keyword in original_query for keyword in ['hybrid']):
            params['work_mode'] = 'hybrid'
        
        # Auto-detect experience level
        if any(keyword in original_query for keyword in ['junior', 'entry level', 'fresher', 'fresh graduate']):
            params['experience_min'] = "0"
            params['experience_max'] = "2"
        elif any(keyword in original_query for keyword in ['senior', 'lead', 'principal']):
            params['experience_min'] = "5"
        elif any(keyword in original_query for keyword in ['mid level', 'intermediate']):
            params['experience_min'] = "2"
            params['experience_max'] = "5"
        
        # Optimize limit based on search specificity
        if len([k for k in params.keys() if params[k] and k not in ['limit', 'page']]) > 5:
            # Very specific search, increase limit
            params['limit'] = 25
        
        return params
    
    def _format_job_response(self, job_data: Dict[str, Any], routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format job search response"""
        logger.info(f"🔍 Formatting job response with data: {job_data}")
        
        if job_data.get('error'):
            logger.error(f"❌ Job data contains error: {job_data['error']}")
            return self.create_response(
                'plain_text',
                'I encountered an error while searching for jobs. Please try again.',
                {'error': job_data['error']}
            )
        
        # Debug: Log the entire job_data structure
        logger.info(f"📊 Job data keys: {list(job_data.keys()) if isinstance(job_data, dict) else 'Not a dict'}")
        logger.info(f"📊 Job data type: {type(job_data)}")
        
        # Handle different possible response structures
        jobs = []
        if isinstance(job_data, dict):
            # Try different possible keys for jobs
            jobs = (job_data.get('jobs') or 
                   job_data.get('data') or 
                   job_data.get('results') or 
                   job_data.get('job_listings') or [])
        elif isinstance(job_data, list):
            jobs = job_data
        
        logger.info(f"📋 Extracted jobs: {len(jobs) if isinstance(jobs, list) else 'Not a list'}")
        logger.info(f"📋 Jobs type: {type(jobs)}")
        
        # If jobs is still not a list, log the structure and create empty list
        if not isinstance(jobs, list):
            logger.warning(f"⚠️ Jobs is not a list. Actual value: {jobs}")
            logger.warning(f"⚠️ Full job_data structure: {job_data}")
            jobs = []
        
        # Format individual jobs
        formatted_jobs = []
        if jobs:
            logger.info(f"🔧 Formatting {len(jobs)} jobs")
            for i, job in enumerate(jobs):
                try:
                    formatted_job = self._format_single_job(job)
                    formatted_jobs.append(formatted_job)
                    logger.info(f"✅ Formatted job {i+1}: {formatted_job.get('title', 'No title')}")
                except Exception as e:
                    logger.error(f"❌ Error formatting job {i+1}: {str(e)}")
                    logger.error(f"❌ Job data: {job}")
        
        # Create response content
        if formatted_jobs:
            content = f"Found {len(formatted_jobs)} job opportunities matching your search:"
            logger.info(f"✅ Successfully formatted {len(formatted_jobs)} jobs")
        else:
            # Provide more helpful messaging based on what we found
            if isinstance(jobs, list) and len(jobs) > 0:
                content = f"Found {len(jobs)} job(s) but couldn't format them properly. The jobs data might be incomplete. Please try a different search or contact support."
                logger.warning(f"⚠️ Found {len(jobs)} jobs but formatting failed")
            else:
                content = "No jobs found matching your criteria. Try using different keywords, removing specific requirements, or searching for broader terms like 'developer' or 'engineer'."
                logger.warning(f"⚠️ No jobs found. Original job_data: {job_data}")
        
        # Calculate total jobs more accurately
        total_jobs = 0
        if isinstance(job_data, dict):
            total_jobs = job_data.get('total', job_data.get('count', len(formatted_jobs)))
        else:
            total_jobs = len(formatted_jobs)
        
        metadata = {
            'jobs': formatted_jobs,
            'totalJobs': total_jobs,
            'hasMore': total_jobs > len(formatted_jobs),
            'currentPage': job_data.get('page', 1) if isinstance(job_data, dict) else 1,
            'searchQuery': routing_data.get('searchQuery') or routing_data.get('originalQuery'),
            'searchParams': routing_data.get('extractedData', {}),
            'debug': {
                'raw_response_keys': list(job_data.keys()) if isinstance(job_data, dict) else None,
                'jobs_count': len(jobs) if isinstance(jobs, list) else 0,
                'formatted_jobs_count': len(formatted_jobs),
                'api_total': job_data.get('total') if isinstance(job_data, dict) else None
            }
        }
        
        logger.info(f"📤 Final response: {content}")
        logger.info(f"📤 Metadata jobs count: {len(formatted_jobs)}")
        
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
    
    async def _parse_query_with_llm(self, query: str) -> Dict[str, Any]:
        """Use LLM to parse natural language query into structured job search parameters"""
        try:
            if not query or not query.strip():
                return {}
            
            logger.info(f"🧠 Parsing query with LLM: {query}")
            
            # Create the full prompt
            full_prompt = f"{self.query_parsing_prompt}\n\nUser Query: \"{query}\"\n\nExtracted Parameters:"
            
            # Get LLM response
            llm_response = await self.llm_client.generate_response(full_prompt, "")
            logger.info(f"🧠 LLM raw response: {llm_response}")
            
            # Try to parse the JSON response
            try:
                # Clean the response (remove any extra text)
                response_lines = llm_response.strip().split('\n')
                for line in response_lines:
                    line = line.strip()
                    if line.startswith('{') and line.endswith('}'):
                        parsed_params = json.loads(line)
                        logger.info(f"✅ Successfully parsed LLM parameters: {parsed_params}")
                        
                        # 🎓 Clean job title if internship is detected
                        parsed_params = self._clean_internship_job_title(parsed_params)
                        
                        return parsed_params
               
                # If no JSON line found, try to parse the entire response
                if llm_response.strip().startswith('{') and llm_response.strip().endswith('}'):
                    parsed_params = json.loads(llm_response.strip())
                    logger.info(f"✅ Successfully parsed LLM parameters: {parsed_params}")
                    
                    # 🎓 Clean job title if internship is detected
                    parsed_params = self._clean_internship_job_title(parsed_params)
                    
                    return parsed_params
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse LLM JSON response: {e}")
                logger.warning(f"⚠️ Raw response was: {llm_response}")
            
            # Fallback: basic keyword extraction
            return self._fallback_query_parsing(query)
            
        except Exception as e:
            logger.error(f"❌ Error in LLM query parsing: {str(e)}")
            return self._fallback_query_parsing(query)
    
    def _clean_internship_job_title(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Clean job title to remove internship keywords when internship flag is set"""
        if not params.get('internship') or not params.get('job_title'):
            return params
        
        job_title = params['job_title']
        internship_keywords = ['intern', 'internship', 'internships', 'trainee', 'graduate', 'student', 'summer intern', 'winter intern']
        
        # Clean the job title
        cleaned_title = job_title.lower()
        for keyword in internship_keywords:
            cleaned_title = cleaned_title.replace(keyword, '').strip()
        
        # Remove extra spaces and clean up
        cleaned_title = ' '.join(cleaned_title.split())
        
        # If we have a meaningful title left, use it
        if cleaned_title and len(cleaned_title) > 2:
            # Capitalize properly
            if 'flutter' in cleaned_title:
                params['job_title'] = 'Flutter Developer'
            elif 'android' in cleaned_title:
                params['job_title'] = 'Android Developer'
            elif 'ios' in cleaned_title:
                params['job_title'] = 'iOS Developer'
            elif 'react' in cleaned_title:
                params['job_title'] = 'React Developer'
            elif 'python' in cleaned_title:
                params['job_title'] = 'Python Developer'
            elif 'java' in cleaned_title and 'javascript' not in cleaned_title:
                params['job_title'] = 'Java Developer'
            elif 'javascript' in cleaned_title or 'js' in cleaned_title:
                params['job_title'] = 'JavaScript Developer'
            elif 'node' in cleaned_title:
                params['job_title'] = 'Node.js Developer'
            elif 'full stack' in cleaned_title or 'fullstack' in cleaned_title:
                params['job_title'] = 'Full Stack Developer'
            elif 'frontend' in cleaned_title or 'front-end' in cleaned_title:
                params['job_title'] = 'Frontend Developer'
            elif 'backend' in cleaned_title or 'back-end' in cleaned_title:
                params['job_title'] = 'Backend Developer'
            elif 'data scien' in cleaned_title:
                params['job_title'] = 'Data Scientist'
            elif 'devops' in cleaned_title:
                params['job_title'] = 'DevOps Engineer'
            else:
                # Capitalize the first letter of each word
                params['job_title'] = ' '.join(word.capitalize() for word in cleaned_title.split())
        
        logger.info(f"🎓 Cleaned job title from '{job_title}' to '{params['job_title']}' for internship search")
        return params
    
    def _fallback_query_parsing(self, query: str) -> Dict[str, Any]:
        """Fallback method for basic query parsing if LLM fails"""
        params = {}
        query_lower = query.lower()
        
        # Remove common action words to focus on job-related terms
        cleaned_query = query_lower
        for action_word in ['suggest', 'find', 'show me', 'search for', 'look for', 'get me', 'give me']:
            cleaned_query = cleaned_query.replace(action_word, '').strip()
        
        # 🎓 IMPROVED INTERNSHIP DETECTION - Check for internship keywords first
        internship_keywords = ['intern', 'internship', 'internships', 'trainee', 'graduate', 'student', 'summer intern', 'winter intern']
        is_internship = any(keyword in cleaned_query for keyword in internship_keywords)
        
        if is_internship:
            params['internship'] = True
            params['job_type'] = 'internship'
            # Don't add experience parameters for internships
            logger.info(f"🎓 Detected internship request in fallback parsing")
            
            # Clean the query to remove internship keywords for job title extraction
            for keyword in internship_keywords:
                cleaned_query = cleaned_query.replace(keyword, '').strip()
            
            # Remove extra spaces and clean up
            cleaned_query = ' '.join(cleaned_query.split())
        
        # Basic job title extraction (now with cleaned query)
        if 'android' in cleaned_query:
            params['job_title'] = 'Android Developer'
            params['skills'] = 'Android,Kotlin,Java'
        elif 'flutter' in cleaned_query:
            params['job_title'] = 'Flutter Developer'
            params['skills'] = 'Flutter,Dart,Mobile Development'
        elif 'ios' in cleaned_query:
            params['job_title'] = 'iOS Developer'
            params['skills'] = 'iOS,Swift,Objective-C'
        elif 'full stack' in cleaned_query or 'fullstack' in cleaned_query:
            params['job_title'] = 'Full Stack Developer'
            params['skills'] = 'JavaScript,React,Node.js,MongoDB'
        elif 'python' in cleaned_query:
            params['job_title'] = 'Python Developer'
            params['skills'] = 'Python'
        elif 'java' in cleaned_query and 'javascript' not in cleaned_query:
            params['job_title'] = 'Java Developer'
            params['skills'] = 'Java'
        elif 'javascript' in cleaned_query or 'js' in cleaned_query:
            params['job_title'] = 'JavaScript Developer'
            params['skills'] = 'JavaScript'
        elif 'react' in cleaned_query:
            params['job_title'] = 'React Developer'
            params['skills'] = 'React,JavaScript'
        elif 'node' in cleaned_query:
            params['job_title'] = 'Node.js Developer'
            params['skills'] = 'Node.js,JavaScript'
        elif 'data scien' in cleaned_query:
            params['job_title'] = 'Data Scientist'
            params['skills'] = 'Python,Machine Learning,Data Science'
        elif 'devops' in cleaned_query:
            params['job_title'] = 'DevOps Engineer'
            params['skills'] = 'DevOps,AWS,Docker,Kubernetes'
        elif 'frontend' in cleaned_query or 'front-end' in cleaned_query:
            params['job_title'] = 'Frontend Developer'
            params['skills'] = 'HTML,CSS,JavaScript,React'
        elif 'backend' in cleaned_query or 'back-end' in cleaned_query:
            params['job_title'] = 'Backend Developer'
            params['skills'] = 'Node.js,Python,Java'
        
        # Work mode detection
        if 'remote' in cleaned_query:
            params['work_mode'] = 'remote'
        elif 'onsite' in cleaned_query or 'on-site' in cleaned_query:
            params['work_mode'] = 'on-site'
        elif 'hybrid' in cleaned_query:
            params['work_mode'] = 'hybrid'
        
        # Experience level detection (only if not already an internship)
        if not is_internship:
            if 'senior' in cleaned_query:
                params['experience_min'] = "5"
            elif 'junior' in cleaned_query:
                params['experience_max'] = "2"
        
        # Only set general query if we have meaningful terms and no specific job title
        if not params.get('job_title') and len(cleaned_query.strip()) > 2:
            # Only include meaningful words (not partial words)
            meaningful_words = [word for word in cleaned_query.split() if len(word) > 3]
            if meaningful_words:
                params['query'] = ' '.join(meaningful_words)
        
        logger.info(f"🔄 Fallback parsing result: {params}")
        return params 
    
    async def search_jobs_follow_up(self, routing_data: Dict[str, Any], page: int = 2) -> Dict[str, Any]:
        """Follow-up job search for pagination"""
        try:
            logger.info(f"🔄 Follow-up job search for page {page}")
            
            # Get the original search context
            extracted_data = routing_data.get('extractedData', {})
            original_query = routing_data.get('originalQuery', '')
            
            # Get stored search params from context
            stored_search_params = extracted_data.get('search_params', {})
            
            # Build search parameters for follow-up
            search_params = {
                'limit': 10,  # Show 10 jobs per page
                'page': page
            }
            
            # Use stored search params if available, otherwise fall back to extracted data
            if stored_search_params:
                # Copy all search params except page and limit
                for key, value in stored_search_params.items():
                    if key not in ['page', 'limit']:
                        search_params[key] = value
                logger.info(f"🔄 Using stored search params for page {page}: {search_params}")
            else:
                # Fallback to extracted data
                if extracted_data.get('skills'):
                    search_params['skills'] = extracted_data['skills']
                
                if extracted_data.get('location'):
                    search_params['location'] = extracted_data['location']
                
                if extracted_data.get('experience_min') is not None:
                    search_params['experience_min'] = extracted_data['experience_min']
                if extracted_data.get('experience_max') is not None:
                    search_params['experience_max'] = extracted_data['experience_max']
                
                # 🎓 Check for internship from multiple sources
                if (extracted_data.get('internship') is True or 
                    extracted_data.get('job_type') == 'internship'):
                    search_params['internship'] = True
                    search_params['job_type'] = 'internship'
                    # Remove experience parameters for internships
                    search_params.pop('experience_min', None)
                    search_params.pop('experience_max', None)
                
                if extracted_data.get('job_title'):
                    search_params['job_title'] = extracted_data['job_title']
                
                logger.info(f"🔄 Using extracted data for page {page}: {search_params}")
            
            # Perform the search using the job search tool
            job_search_result = await self.search_jobs_tool(
                token=routing_data.get('token', ''),
                base_url=routing_data.get('baseUrl', self.base_url),
                **search_params
            )
            
            if not job_search_result or not job_search_result.get('success'):
                return {
                    'type': 'plain_text',
                    'content': 'No more jobs found. Try adjusting your search criteria.',
                    'metadata': {'error': 'No more jobs'}
                }
            
            jobs_data = job_search_result.get('data', {})
            jobs = job_search_result.get('jobs', []) or jobs_data.get('jobs', [])
            total_jobs = jobs_data.get('total', len(jobs))
            
            if not jobs:
                return {
                    'type': 'plain_text',
                    'content': 'No more jobs found. Try adjusting your search criteria.',
                    'metadata': {'error': 'No more jobs'}
                }
            
            # Store current page in Redis for pagination tracking
            try:
                current_config = config[os.environ.get('FLASK_ENV', 'development')]
                redis_url = current_config.REDIS_URL
                redis_ssl = current_config.REDIS_SSL
                
                if redis_ssl:
                    redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        ssl=True,
                        ssl_cert_reqs=None
                    )
                else:
                    redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True
                    )
                
                session_id = routing_data.get('sessionId', 'default')
                redis_client.setex(f"last_page:{session_id}", 3600, str(page))
                logger.info(f"💾 Stored current page {page} for session {session_id}")
            except Exception as e:
                logger.warning(f"⚠️ Could not store current page: {str(e)}")
            
            # Format jobs for display
            formatted_jobs = []
            for job in jobs:
                formatted_job = self.format_job_for_response(job)
                formatted_jobs.append(formatted_job)
            
            # Calculate pagination info
            jobs_per_page = search_params['limit']
            total_pages = (total_jobs + jobs_per_page - 1) // jobs_per_page
            has_more = page < total_pages
            
            # Create response message
            if has_more:
                message = f"Here are {len(formatted_jobs)} more job opportunities:\n\n📋 Job Opportunities\nShowing page {page} of {total_pages} (Jobs {((page-1) * jobs_per_page) + 1}-{min(page * jobs_per_page, total_jobs)} of {total_jobs})"
            else:
                message = f"Here are the final {len(formatted_jobs)} job opportunities:\n\n📋 Job Opportunities\nFinal page {page} of {total_pages} (Jobs {((page-1) * jobs_per_page) + 1}-{total_jobs} of {total_jobs})"
            
            # Storage is handled by app.py to avoid duplication
            
            return self.response_formatter.format_job_response(
                jobs=formatted_jobs,
                metadata={
                    'total': total_jobs,
                    'hasMore': has_more,
                    'page': page,
                    'totalPages': total_pages,
                    'searchQuery': original_query,
                    'searchParams': search_params,
                    'searchContext': extracted_data,
                    'isFollowUp': True,
                    'currentPage': page
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Error in follow-up job search: {str(e)}")
            return self.response_formatter.format_error_response(
                error_message='Sorry, there was an error loading more jobs. Please try again.',
                error_details=str(e)
            )
    
    async def _build_broader_search_params(self, extracted_data: Dict[str, Any], original_params: Dict[str, Any]) -> Dict[str, Any]:
        """Build broader search parameters when initial search returns no results"""
        broader_params = original_params.copy()
        
        # Remove restrictive filters but keep essential ones
        broader_params.pop('experience_min', None)
        broader_params.pop('experience_max', None)
        broader_params.pop('salary_min', None)
        broader_params.pop('salary_max', None)
        broader_params.pop('work_mode', None)
        broader_params.pop('job_type', None)
        
        # IMPORTANT: Remove job_title completely - don't use it in broader search
        broader_params.pop('job_title', None)
        
        # Keep only essential parameters
        essential_params = {
            'limit': 10,  # Show 10 jobs per page
            'page': 1
        }
        
        # Add location if available (keep it)
        if extracted_data.get('location'):
            essential_params['locations'] = extracted_data['location']
        
        # CRITICAL: Preserve skills from original search to maintain relevance
        if original_params.get('skills'):
            essential_params['skills'] = original_params['skills']
            logger.info(f"🔄 Preserving skills in broader search: {original_params['skills']}")
        elif extracted_data.get('skills'):
            essential_params['skills'] = extracted_data['skills']
            logger.info(f"🔄 Using extracted skills in broader search: {extracted_data['skills']}")
        else:
            # Auto-detect skills from the query for broader search
            auto_skills = await self._enhance_skills_from_job_title(extracted_data)
            if auto_skills:
                essential_params['skills'] = auto_skills
                logger.info(f"🔄 Auto-detected skills for broader search: {auto_skills}")
        
        # Add experience range but make it broader
        if extracted_data.get('experience_min') is not None or extracted_data.get('experience_max') is not None:
            # Broaden experience range
            exp_min = extracted_data.get('experience_min', 0)
            exp_max = extracted_data.get('experience_max', 10)
            
            # Make range broader: reduce min by 1, increase max by 2
            broader_min = max(0, exp_min - 1)
            broader_max = min(15, exp_max + 2)
            
            essential_params['experience_min'] = broader_min
            essential_params['experience_max'] = broader_max
        
        # Add salary range but make it broader
        if extracted_data.get('salary_min') is not None or extracted_data.get('salary_max') is not None:
            # Broaden salary range
            salary_min = extracted_data.get('salary_min', 0)
            salary_max = extracted_data.get('salary_max', 1000000)
            
            # Make range broader: reduce min by 20%, increase max by 30%
            broader_min = max(0, int(salary_min * 0.8))
            broader_max = int(salary_max * 1.3)
            
            essential_params['salary_min'] = broader_min
            essential_params['salary_max'] = broader_max
        
        # IMPROVED: Handle internship filter more intelligently
        # Check if user has substantial skills before defaulting to internships
        has_substantial_skills = self._has_substantial_technical_skills(extracted_data, {}, {})
        
        # 🎓 Check for internship from multiple sources
        is_internship_request = (
            extracted_data.get('internship') is True or 
            extracted_data.get('job_type') == 'internship'
        )
        
        if is_internship_request:
            # User explicitly requested internship
            essential_params['internship'] = True
            essential_params['job_type'] = 'internship'
            # Remove experience parameters for internships
            essential_params.pop('experience_min', None)
            essential_params.pop('experience_max', None)
            logger.info(f"🔄 Broader search: User requested internship - removing experience filters")
        elif extracted_data.get('internship') is False:
            # User explicitly said no internships
            essential_params['internship'] = False
            essential_params['job_type'] = 'full-time'
            logger.info(f"🔄 Broader search: User explicitly requested non-internship positions")
        else:
            # No explicit internship request - default based on skills
            if has_substantial_skills:
                essential_params['internship'] = False
                essential_params['job_type'] = 'full-time'
                logger.info(f"🔄 Broader search: Defaulting to full-time for user with substantial skills")
            else:
                # Entry-level user, allow both internship and full-time
                essential_params.pop('internship', None)  # Remove internship filter to get both types
                essential_params.pop('job_type', None)
                logger.info(f"🔄 Broader search: Entry-level user - allowing both internship and full-time positions")
        
        # If we have a query but no specific job title, use it
        if extracted_data.get('query') and not extracted_data.get('job_title'):
            essential_params['query'] = extracted_data['query']
        
        logger.info(f"🔄 Built broader search params: {essential_params}")
        return essential_params

    def _is_unrealistic_location(self, location: str) -> bool:
        if not location:
            return False
        location_lower = location.strip().lower()
        return any(loc in location_lower for loc in self.UNREALISTIC_LOCATIONS) 