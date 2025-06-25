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
            search_params = self._build_search_params(extracted_data, {}, {})
            
            # First attempt with original parameters
            logger.info(f"🔍 First attempt search params: {search_params}")
            job_search_result = await self.search_jobs_tool(token, base_url, **search_params)
            
            if not job_search_result.get('success'):
                return self._handle_search_failure(original_query, extracted_data.get('language', 'english'))
            
            jobs_data = job_search_result.get('data', {})
            jobs = jobs_data.get('jobs', [])
            
            # If no jobs found, try with broader filters
            if not jobs:
                logger.info("🔄 No jobs found, trying with broader filters...")
                broader_params = self._build_broader_search_params(extracted_data, search_params)
                logger.info(f"🔍 Broader search params: {broader_params}")
                
                broader_result = await self.search_jobs_tool(token, base_url, **broader_params)
                
                if broader_result.get('success'):
                    jobs_data = broader_result.get('data', {})
                    jobs = jobs_data.get('jobs', [])
                    
                    if jobs:
                        logger.info(f"✅ Found {len(jobs)} jobs with broader filters")
                        # Use broader params for the rest of the processing
                        search_params = broader_params
                    else:
                        logger.info("❌ No jobs found even with broader filters")
                        return self._handle_no_jobs_found(original_query, search_params, extracted_data.get('language', 'english'))
                else:
                    logger.info("❌ Broader search also failed")
                    return self._handle_search_failure(original_query, extracted_data.get('language', 'english'))
            
            # Format jobs for response (don't send raw data to AI)
            formatted_jobs = []
            for job in jobs:
                formatted_job = self.format_job_for_response(job)
                formatted_jobs.append(formatted_job)
            
            # Create dynamic 2-line message based on results
            total_jobs = len(formatted_jobs)
            search_query = routing_data.get('searchQuery') or routing_data.get('originalQuery', 'default search')
            
            if total_jobs == 1:
                content = f"Here's a job opportunity that matches your search for '{search_query}':"
            else:
                content = f"Here are {total_jobs} job opportunities that might interest you:"
            
            # Store conversation in memory (without raw job data)
            if self.memory_manager:
                await self.memory_manager.store_conversation(session_id, original_query, f"Found {total_jobs} jobs matching the search criteria")

            # Get total available jobs from API response
            total_available = jobs_data.get('total', total_jobs)
            has_more = total_available > 5  # Show load more if more than 5 jobs available

            # Store search context for follow-up searches
            search_context = {
                'skills': search_params.get('skills'),
                'location': extracted_data.get('location'),
                'query': extracted_data.get('query'),
                'internship': extracted_data.get('internship'),
                'experience_min': extracted_data.get('experience_min'),
                'experience_max': extracted_data.get('experience_max'),
                'job_title': extracted_data.get('job_title'),
                'original_query': original_query
            }
            
            # Store in memory manager for session persistence
            if self.memory_manager:
                try:
                    # Store search context for this session
                    session_id = routing_data.get('sessionId', 'default')
                    # We'll store this in the memory manager's session data
                    await self.memory_manager.store_conversation(
                        session_id, 
                        f"Search context: {original_query}", 
                        f"Search params: {json.dumps(search_context)}",
                        {'search_context': search_context}
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not store search context: {str(e)}")
            
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
    
    def _handle_search_failure(self, original_query: str, language: str = 'english') -> Dict[str, Any]:
        """Handle job search failure"""
        if language in ['hindi', 'hinglish']:
            content = f"Sorry yaar, '{original_query}' ke liye job search mein kuch technical issue ho gaya! 😅 Please try again with different keywords."
        else:
            content = f"Sorry, I encountered a technical issue while searching for '{original_query}'. Please try again with different keywords."
        
        return self.response_formatter.format_error_response(
            error_message=content,
            error_details='search_failed'
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
    
    def _build_search_params(self, extracted_data: Dict[str, Any], profile_data: Dict[str, Any], resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build comprehensive search parameters from extracted data using JobMato Tools"""
        params = {
            'limit': 5,  # Show only 5 jobs by default
            'page': 1
        }
        
        # 🔍 Basic search parameters
        if extracted_data.get('query'):
            params['query'] = extracted_data['query']
        if extracted_data.get('search'):
            params['search'] = extracted_data['search']
        if extracted_data.get('job_title'):
            params['job_title'] = extracted_data['job_title']
        if extracted_data.get('company'):
            params['company'] = extracted_data['company']
        
        # 📍 Location parameters
        if extracted_data.get('location'):
            params['locations'] = extracted_data['location']
        if extracted_data.get('locations'):
            params['locations'] = extracted_data['locations']
        
        # 🛠️ Skills and domain parameters - Enhanced with auto-skill detection
        skills = self._enhance_skills_from_job_title(extracted_data)
        if skills:
            params['skills'] = skills
            logger.info(f"🎯 Using enhanced skills: {skills}")
        elif extracted_data.get('skills'):
            params['skills'] = extracted_data['skills']
            logger.info(f"🎯 Using extracted skills: {extracted_data['skills']}")
            
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
        
        # 💰 Salary parameters
        if extracted_data.get('salary_min') is not None:
            params['salary_min'] = extracted_data['salary_min']
        if extracted_data.get('salary_max') is not None:
            params['salary_max'] = extracted_data['salary_max']
        
        # 🎓 Internship filter - IMPROVED LOGIC
        # Only set internship if explicitly requested AND user doesn't have substantial skills
        if extracted_data.get('internship') is not None:
            # Check if user has substantial technical skills that suggest they're beyond internship level
            has_substantial_skills = self._has_substantial_technical_skills(extracted_data, profile_data, resume_data)
            
            if extracted_data['internship'] and not has_substantial_skills:
                params['internship'] = True
                params['job_type'] = 'internship'
                params['experience_max'] = 1  # Max 1 year for internships
                logger.info(f"🎓 Detected internship search for entry-level user, setting job_type: internship")
            elif extracted_data['internship'] and has_substantial_skills:
                # User has substantial skills but requested internship - this might be for career transition
                params['internship'] = True
                params['job_type'] = 'internship'
                logger.info(f"🎓 User with substantial skills requested internship (possible career transition)")
            else:
                # Not an internship request - focus on full-time positions
                params['internship'] = False
                params['job_type'] = 'full-time'
                logger.info(f"💼 Focusing on full-time positions for user with substantial skills")
        else:
            # No explicit internship request - check if we should default to full-time based on skills
            has_substantial_skills = self._has_substantial_technical_skills(extracted_data, profile_data, resume_data)
            if has_substantial_skills:
                params['internship'] = False
                params['job_type'] = 'full-time'
                logger.info(f"💼 Defaulting to full-time positions for user with substantial skills")
        
        # 📄 Pagination parameters
        if extracted_data.get('limit'):
            params['limit'] = extracted_data['limit']
        if extracted_data.get('page'):
            params['page'] = extracted_data['page']
        
        logger.info(f"🔧 Built comprehensive search params: {params}")
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
        skills_text = extracted_data.get('skills', '').lower()
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
        query_text = extracted_data.get('query', '').lower()
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
    
    def _enhance_skills_from_job_title(self, extracted_data: Dict[str, Any]) -> str:
        """Enhance skills based on job title if skills are not explicitly provided"""
        job_title = extracted_data.get('job_title', '').lower()
        existing_skills = extracted_data.get('skills', '')
        is_internship = extracted_data.get('internship', False)
        
        # If skills are already provided, return them
        if existing_skills:
            return existing_skills
        
        # Auto-detect skills based on job title
        skill_mapping = {
            'android': 'Android, Java, Kotlin, Android Studio, XML, Gradle',
            'ios': 'iOS, Swift, Objective-C, Xcode, CocoaPods, Core Data',
            'react': 'React, JavaScript, TypeScript, HTML, CSS, Redux',
            'angular': 'Angular, TypeScript, HTML, CSS, RxJS, Angular CLI',
            'vue': 'Vue.js, JavaScript, HTML, CSS, Vuex, Vue Router',
            'node': 'Node.js, JavaScript, Express, MongoDB, REST API',
            'python': 'Python, Django, Flask, SQL, Git, REST API',
            'java': 'Java, Spring Boot, Maven, Hibernate, SQL, JUnit',
            'c#': 'C#, .NET, ASP.NET, SQL Server, Entity Framework',
            'php': 'PHP, Laravel, MySQL, WordPress, Composer',
            'data scientist': 'Python, R, SQL, Machine Learning, Statistics, Pandas',
            'data analyst': 'SQL, Python, Excel, Tableau, Power BI, Statistics',
            'machine learning': 'Python, TensorFlow, PyTorch, Scikit-learn, SQL, Statistics',
            'devops': 'Docker, Kubernetes, AWS, CI/CD, Linux, Jenkins',
            'cloud': 'AWS, Azure, GCP, Docker, Kubernetes, Terraform',
            'ui/ux': 'Figma, Adobe XD, Sketch, Prototyping, User Research, Wireframing',
            'product manager': 'Product Strategy, Agile, Scrum, Market Research, Analytics, JIRA',
            'project manager': 'Project Management, Agile, Scrum, JIRA, Risk Management',
            'sales': 'Sales, CRM, Communication, Negotiation, Lead Generation',
            'marketing': 'Digital Marketing, SEO, Social Media, Google Ads, Analytics',
            'content': 'Content Writing, SEO, Copywriting, Social Media, WordPress',
            'frontend': 'HTML, CSS, JavaScript, React, Angular, Vue.js',
            'backend': 'Python, Java, Node.js, SQL, REST API, Microservices',
            'full stack': 'JavaScript, Python, React, Node.js, SQL, Git',
            'mobile': 'React Native, Flutter, Android, iOS, JavaScript, Dart',
            'hr': 'HR Management, Recruitment, Employee Relations, Communication, MS Office, HRIS',
            'human resources': 'HR Management, Recruitment, Employee Relations, Communication, MS Office, HRIS',
            'recruitment': 'Recruitment, Sourcing, Interviewing, Communication, ATS, HR Management',
            'intern': 'Basic Programming, Problem Solving, Team Work, Communication, Learning Ability',
            'internship': 'Basic Programming, Problem Solving, Team Work, Communication, Learning Ability'
        }
        
        # Check for exact matches first
        for keyword, skills in skill_mapping.items():
            if keyword in job_title:
                logger.info(f"🎯 Auto-detected skills for '{job_title}': {skills}")
                return skills
        
        # Check for partial matches
        for keyword, skills in skill_mapping.items():
            if any(word in job_title for word in keyword.split()):
                logger.info(f"🎯 Auto-detected skills for '{job_title}': {skills}")
                return skills
        
        # If no specific skills found, return empty string
        logger.info(f"⚠️ No specific skills auto-detected for job title: {job_title}")
        return ""
    
    def _enhance_search_params(self, params: Dict[str, Any], routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance search parameters with intelligent defaults and optimizations"""
        
        # Auto-detect internship based on query keywords
        original_query = routing_data.get('originalQuery', '').lower()
        if any(keyword in original_query for keyword in ['intern', 'internship', 'trainee', 'graduate']):
            params['internship'] = True
            params['job_type'] = 'internship'
            params['experience_max'] = 1  # Max 1 year for internships
        
        # Auto-detect remote work preference
        if any(keyword in original_query for keyword in ['remote', 'work from home', 'wfh']):
            params['work_mode'] = 'remote'
        elif any(keyword in original_query for keyword in ['on-site', 'office', 'onsite']):
            params['work_mode'] = 'on-site'
        elif any(keyword in original_query for keyword in ['hybrid']):
            params['work_mode'] = 'hybrid'
        
        # Auto-detect experience level
        if any(keyword in original_query for keyword in ['junior', 'entry level', 'fresher', 'fresh graduate']):
            params['experience_min'] = 0
            params['experience_max'] = 2
        elif any(keyword in original_query for keyword in ['senior', 'lead', 'principal']):
            params['experience_min'] = 5
        elif any(keyword in original_query for keyword in ['mid level', 'intermediate']):
            params['experience_min'] = 2
            params['experience_max'] = 5
        
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
                        return parsed_params
               
                # If no JSON line found, try to parse the entire response
                if llm_response.strip().startswith('{') and llm_response.strip().endswith('}'):
                    parsed_params = json.loads(llm_response.strip())
                    logger.info(f"✅ Successfully parsed LLM parameters: {parsed_params}")
                    return parsed_params
                
            except json.JSONDecodeError as e:
                logger.warning(f"⚠️ Failed to parse LLM JSON response: {e}")
                logger.warning(f"⚠️ Raw response was: {llm_response}")
            
            # Fallback: basic keyword extraction
            return self._fallback_query_parsing(query)
            
        except Exception as e:
            logger.error(f"❌ Error in LLM query parsing: {str(e)}")
            return self._fallback_query_parsing(query)
    
    def _fallback_query_parsing(self, query: str) -> Dict[str, Any]:
        """Fallback method for basic query parsing if LLM fails"""
        params = {}
        query_lower = query.lower()
        
        # Remove common action words to focus on job-related terms
        cleaned_query = query_lower
        for action_word in ['suggest', 'find', 'show me', 'search for', 'look for', 'get me', 'give me']:
            cleaned_query = cleaned_query.replace(action_word, '').strip()
        
        # Basic job title extraction
        if 'android' in cleaned_query:
            params['job_title'] = 'Android Developer'
            params['skills'] = 'Android,Kotlin,Java'
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
        
        # Job type detection
        if 'intern' in cleaned_query:
            params['job_type'] = 'internship'
            params['experience_max'] = 1
        elif 'senior' in cleaned_query:
            params['experience_min'] = 5
        elif 'junior' in cleaned_query:
            params['experience_max'] = 2
        
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
            
            # Build search parameters for follow-up
            search_params = {
                'limit': 5,
                'page': page
            }
            
            # Add skills if available
            if extracted_data.get('skills'):
                search_params['skills'] = extracted_data['skills']
            
            # Add location if available
            if extracted_data.get('location'):
                search_params['location'] = extracted_data['location']
            
            # Add experience filters if available
            if extracted_data.get('experience_min') is not None:
                search_params['experience_min'] = extracted_data['experience_min']
            if extracted_data.get('experience_max') is not None:
                search_params['experience_max'] = extracted_data['experience_max']
            
            # Add internship filter if available
            if extracted_data.get('internship'):
                search_params['internship'] = True
                search_params['job_type'] = 'internship'
            
            # Add job title if available
            if extracted_data.get('job_title'):
                search_params['job_title'] = extracted_data['job_title']
            
            logger.info(f"🔄 Follow-up search params: {search_params}")
            
            # Perform the search
            jobs_response = await self.search_jobs_tool(
                skills=search_params.get('skills'),
                location=search_params.get('location'),
                job_title=search_params.get('job_title'),
                experience_min=search_params.get('experience_min'),
                experience_max=search_params.get('experience_max'),
                internship=search_params.get('internship'),
                limit=search_params['limit'],
                page=search_params['page']
            )
            
            if not jobs_response or not jobs_response.get('success'):
                return {
                    'type': 'plain_text',
                    'content': 'No more jobs found. Try adjusting your search criteria.',
                    'metadata': {'error': 'No more jobs'}
                }
            
            jobs = jobs_response.get('jobs', [])
            total_jobs = jobs_response.get('total', 0)
            
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
                formatted_job = {
                    'title': self._safe_extract(job, 'title'),
                    'company': self._safe_extract(job, 'company'),
                    'location': self._safe_extract(job, 'location'),
                    'job_type': self._safe_extract(job, 'job_type'),
                    'experience': self._safe_extract(job, 'experience'),
                    'skills': self._safe_extract(job, 'skills'),
                    'salary': self._safe_extract(job, 'salary'),
                    'apply_url': self._safe_extract(job, 'apply_url'),
                    'source': self._safe_extract(job, 'source')
                }
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
            
            # Store in memory
            if self.memory_manager:
                try:
                    await self.memory_manager.add_message(
                        session_id=routing_data.get('sessionId', 'default'),
                        message=f"Load more jobs request - Page {page}",
                        sender='user',
                        metadata={'page': page, 'total_pages': total_pages}
                    )
                    
                    await self.memory_manager.add_message(
                        session_id=routing_data.get('sessionId', 'default'),
                        message=message,
                        sender='assistant',
                        metadata={
                            'type': 'job_card',
                            'jobs_count': len(formatted_jobs),
                            'page': page,
                            'total_pages': total_pages,
                            'has_more': has_more
                        }
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Could not store follow-up search in memory: {str(e)}")
            
            return {
                'type': 'job_card',
                'content': message,
                'metadata': {
                    'jobs': formatted_jobs,
                    'totalJobs': total_jobs,
                    'currentPage': page,
                    'totalPages': total_pages,
                    'hasMore': has_more,
                    'searchContext': extracted_data
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in follow-up job search: {str(e)}")
            return {
                'type': 'plain_text',
                'content': 'Sorry, there was an error loading more jobs. Please try again.',
                'metadata': {'error': str(e)}
            }
    
    def _build_broader_search_params(self, extracted_data: Dict[str, Any], original_params: Dict[str, Any]) -> Dict[str, Any]:
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
            'limit': 5,
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
        
        if extracted_data.get('internship') is not None:
            if extracted_data['internship'] and not has_substantial_skills:
                # User explicitly requested internship and has entry-level skills
                essential_params['internship'] = True
                essential_params['job_type'] = 'internship'
                essential_params['experience_max'] = 1
                logger.info(f"🔄 Broader search: User requested internship with entry-level skills")
            elif extracted_data['internship'] and has_substantial_skills:
                # User requested internship but has substantial skills (career transition)
                essential_params['internship'] = True
                essential_params['job_type'] = 'internship'
                logger.info(f"🔄 Broader search: User with substantial skills requested internship")
            else:
                # Not an internship request - focus on full-time positions
                essential_params['internship'] = False
                essential_params['job_type'] = 'full-time'
                logger.info(f"🔄 Broader search: Focusing on full-time positions")
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