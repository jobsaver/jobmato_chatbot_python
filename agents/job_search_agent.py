import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent
from utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

class JobSearchAgent(BaseAgent):
    """Agent responsible for handling job search requests"""
    
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
        """Search for jobs based on the routing data"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            session_id = routing_data.get('sessionId', 'default')
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            logger.info(f"🔍 Job search with token: {token[:50] if token else 'None'}...")
            logger.info(f"🌐 Using base URL: {base_url}")
            
            # Get conversation context
            conversation_context = await self.get_conversation_context(session_id)
            
            # Get user profile and resume data for better job matching
            profile_data = await self.get_profile_data(token, base_url)
            resume_data = await self.get_resume_data(token, base_url)
            
            # Build search parameters from extracted data and user context
            search_params = self._build_search_params(extracted_data, profile_data, resume_data)
            
            # Search for jobs using the JobMato API
            job_search_result = await self.search_jobs_tool(token, base_url, **search_params)
            
            if not job_search_result.get('success'):
                return self._handle_search_failure(original_query, extracted_data.get('language', 'english'))
            
            jobs_data = job_search_result.get('data', {})
            jobs = jobs_data.get('jobs', [])
            
            if not jobs:
                return self._handle_no_jobs_found(original_query, search_params, extracted_data.get('language', 'english'))
            
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

            return {
                'type': 'job_card',
                'content': content,
                'metadata': {
                    'jobs': formatted_jobs,
                    'totalJobs': total_available,
                    'isFollowUp': False,
                    'hasMore': has_more,
                    'currentPage': 1,
                    'searchQuery': search_query,
                }
            }
            
        except Exception as e:
            logger.error(f"Error in job search: {str(e)}")
            return {
                'type': 'plain_text',
                'content': 'Sorry yaar, job search mein kuch technical issue ho gaya! 😅 Please try again, main help karunga.',
                'metadata': {'error': str(e), 'category': 'JOB_SEARCH'}
            }
    
    def format_job_for_response(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Format job data for response following the specified structure"""
        return {
            '_id': job.get('_id'),
            'job_id': job.get('job_id'),
            'job_title': job.get('job_title'),
            'company': job.get('company'),
            'locations': job.get('locations'),
            'location': job.get('locations', [])[0] if job.get('locations') else job.get('location'),
            'experience': job.get('experience'),
            'salary': job.get('salary'),
            'skills': job.get('skills'),
            'work_mode': job.get('work_mode'),
            'job_type': job.get('job_type'),
            'description': job.get('description'),
            'posted_date': job.get('posted_date'),
            'source_url': job.get('source_url'),
            'apply_url': job.get('apply_url'),
            'source_platform': job.get('source_platform'),
        }
    
    def _handle_search_failure(self, original_query: str, language: str = 'english') -> Dict[str, Any]:
        """Handle job search failure"""
        if language in ['hindi', 'hinglish']:
            content = f"Sorry yaar, '{original_query}' ke liye job search mein kuch technical issue ho gaya! 😅 Please try again with different keywords."
        else:
            content = f"Sorry, I encountered a technical issue while searching for '{original_query}'. Please try again with different keywords."
        
        return {
            'type': 'plain_text',
            'content': content,
            'metadata': {'error': 'search_failed', 'category': 'JOB_SEARCH'}
        }
    
    def _handle_no_jobs_found(self, original_query: str, search_params: Dict[str, Any], language: str = 'english') -> Dict[str, Any]:
        """Handle case when no jobs are found"""
        if language in ['hindi', 'hinglish']:
            content = f"'{original_query}' ke liye koi jobs nahi mili. Try using different keywords, removing specific requirements, or searching for broader terms like 'developer' or 'engineer'."
        else:
            content = f"No jobs found for '{original_query}'. Try using different keywords, removing specific requirements, or searching for broader terms like 'developer' or 'engineer'."
        
        return {
            'type': 'plain_text',
            'content': content,
            'metadata': {
                'error': 'no_jobs_found',
                'category': 'JOB_SEARCH',
                'searchParams': search_params,
                'suggestions': [
                    'Try broader keywords',
                    'Remove location restrictions',
                    'Check spelling',
                    'Use different job titles'
                ]
            }
        }
    
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
        
        # 🎓 Internship filter
        if extracted_data.get('internship') is not None:
            params['internship'] = extracted_data['internship']
            # If internship is true, set appropriate defaults
            if extracted_data['internship']:
                params['job_type'] = 'internship'
                params['experience_max'] = 1  # Max 1 year for internships
                logger.info(f"🎓 Detected internship search, setting job_type: internship, experience_max: 1")
        
        # 📄 Pagination parameters
        if extracted_data.get('limit'):
            params['limit'] = extracted_data['limit']
        if extracted_data.get('page'):
            params['page'] = extracted_data['page']
        
        logger.info(f"🔧 Built comprehensive search params: {params}")
        return params
    
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
            'blockchain': 'Solidity, Ethereum, Smart Contracts, Web3, JavaScript',
            'cybersecurity': 'Network Security, Penetration Testing, SIEM, Firewall, Linux',
            'qa': 'Selenium, TestNG, JUnit, Manual Testing, Automation, API Testing',
            'database': 'SQL, MongoDB, PostgreSQL, MySQL, Redis, Database Design',
            'system admin': 'Linux, Windows Server, Active Directory, Networking, PowerShell',
            # Internship-specific mappings
            'intern': 'Basic Programming, Problem Solving, Team Work, Communication',
            'internship': 'Basic Programming, Problem Solving, Team Work, Communication',
            'trainee': 'Basic Programming, Problem Solving, Team Work, Communication',
            'graduate': 'Basic Programming, Problem Solving, Team Work, Communication'
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
            import json
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
    
    async def search_jobs_follow_up(self, routing_data: Dict[str, Any], current_page: int = 1) -> Dict[str, Any]:
        """Handle follow-up job searches with pagination"""
        try:
            token = routing_data.get('token', '')
            base_url = routing_data.get('baseUrl', self.base_url)
            session_id = routing_data.get('sessionId', 'default')
            original_query = routing_data.get('originalQuery', '')
            extracted_data = routing_data.get('extractedData', {})
            
            # Update search parameters for pagination
            search_params = self._build_search_params(extracted_data, {}, {})
            search_params['page'] = current_page
            search_params['limit'] = 5  # Keep consistent with initial search limit
            
            # Search for jobs using the JobMato API
            job_search_result = await self.search_jobs_tool(token, base_url, **search_params)
            
            if not job_search_result.get('success'):
                return self._handle_search_failure(original_query, extracted_data.get('language', 'english'))
            
            jobs_data = job_search_result.get('data', {})
            jobs = jobs_data.get('jobs', [])
            
            if not jobs:
                return {
                    'type': 'plain_text',
                    'content': 'No more jobs found. Try adjusting your search criteria.',
                    'metadata': {'error': 'No more jobs', 'category': 'JOB_SEARCH'}
                }
            
            # Format jobs for response
            formatted_jobs = []
            for job in jobs:
                formatted_job = self.format_job_for_response(job)
                formatted_jobs.append(formatted_job)
            
            # Create dynamic message for follow-up
            total_jobs = len(formatted_jobs)
            search_query = routing_data.get('searchQuery') or routing_data.get('originalQuery', 'default search')
            
            content = f"Here are {total_jobs} more job opportunities that might interest you:"
            
            # Calculate if there are more jobs available
            total_available = jobs_data.get('total', 0)
            has_more = total_available > (current_page * 5)  # Check if more than current page * 5
            
            return {
                'type': 'job_card',
                'content': content,
                'metadata': {
                    'jobs': formatted_jobs,
                    'totalJobs': total_available,
                    'isFollowUp': True,
                    'hasMore': has_more,
                    'currentPage': current_page,
                    'searchQuery': search_query,
                }
            }
            
        except Exception as e:
            logger.error(f"Error in follow-up job search: {str(e)}")
            return {
                'type': 'plain_text',
                'content': 'Sorry, there was an error loading more jobs. Please try again.',
                'metadata': {'error': str(e), 'category': 'JOB_SEARCH'}
            } 