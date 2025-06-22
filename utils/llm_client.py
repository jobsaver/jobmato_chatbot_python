import logging
import os
import random
from typing import Dict, Any, Optional
import google.generativeai as genai
from datetime import datetime

logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with language models (using Google Gemini)"""
    
    def __init__(self):
        # Configure Gemini API
        api_key = "AIzaSyCOisI31bZxs1j6WProcu1khBht29tnV4I"
        if not api_key:
            logger.warning("GOOGLE_API_KEY not found in environment variables. Using mock responses.")
            self.mock_mode = True
        else:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
            self.mock_mode = False
        
        # Mock responses for different languages and scenarios
        self.mock_responses = {
            'casual_english': [
                "Haha, I'm JobMato's career buddy! 🤖 While I'd love to chat about everything, I'm really passionate about helping with your career. What's cooking in your professional life?",
                "LOL! I'm like that friend who only talks about work... but in a good way! 😄 I'm here to help with jobs, resumes, career advice. What can I help you achieve today?",
                "You caught me! I'm JobMato's AI assistant, and I'm obsessed with careers! 🎯 Think of me as your professional wingman. What career goals are we tackling?",
            ],
            'casual_hinglish': [
                "Arre yaar, main JobMato ka career assistant hoon! 😊 Baaki sab toh theek hai, but mera passion hai career help karna. Kya career goals hai tumhare?",
                "Haha bhai, main sirf career ke baare mein baat karta hoon! 🤓 JobMato ka AI hoon, job search aur resume mein expert. Kya help chahiye?",
                "Dekho, main JobMato ka career buddy hoon! 🎉 Other topics mein thoda weak hoon, but career advice mein strong! Kya plan hai professional life mein?",
            ],
            'casual_hindi': [
                "Namaste! Main JobMato ka career sahayak hoon! 🙏 Mera kaam hai aapki professional life mein madad karna. Kya career sahaayata chahiye?",
                "Haan bhai, main career ke liye dedicated AI hoon! 💼 JobMato mein aapka dost. Naukri, resume, career advice - sab kuch! Kya help karna hai?",
                "Main JobMato ka AI assistant hoon, career expert! 🎯 Aapki professional journey mein guide karna mera passion hai. Kya goals hain?",
            ],
            'name_responses': [
                "Main JobMato Assistant hoon! 🤖 Aap mujhe JM, JobMato AI, ya phir Career Buddy bhi keh sakte ho! What should I call you?",
                "I'm your friendly JobMato Assistant! 😊 You can call me JM for short, or just your career buddy! Aur aapka naam kya hai?",
                "JobMato Assistant here! 🎉 But you can give me a nickname if you want - Career Guru, Job Buddy, kuch bhi! What's your name?",
            ]
        }
    
    async def generate_response(self, prompt: str, system_message: str = "") -> str:
        """Generate a response using the language model"""
        try:
            if self.mock_mode:
                return self._get_mock_response(prompt)
            
            # Combine system message and prompt
            full_prompt = f"{system_message}\n\nUser: {prompt}\n\nAssistant:"
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            if response.text:
                return response.text.strip()
            else:
                logger.error("Empty response from language model")
                return "I apologize, but I couldn't generate a proper response. Please try again."
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return self._get_fallback_response()
    
    def _detect_language(self, text: str) -> str:
        """Detect if text is in Hindi, Hinglish, or English"""
        text_lower = text.lower()
        
        # Hindi words
        hindi_words = ['naam', 'kya', 'hai', 'hoon', 'main', 'tumhara', 'mera', 'aap', 'tum', 'kaun', 'kaise', 'kahan', 'kyun']
        # Hinglish indicators
        hinglish_words = ['yaar', 'bhai', 'boss', 'dekho', 'arre', 'batao', 'chahiye', 'karo', 'haal', 'bro']
        
        hindi_count = sum(1 for word in hindi_words if word in text_lower)
        hinglish_count = sum(1 for word in hinglish_words if word in text_lower)
        
        if hindi_count > hinglish_count and hindi_count > 0:
            return 'hindi'
        elif hinglish_count > 0:
            return 'hinglish'
        else:
            return 'english'
    
    def _get_mock_response(self, prompt: str) -> str:
        """Generate mock responses for testing when API key is not available"""
        prompt_lower = prompt.lower()
        
        # Mock classification responses
        if "user query:" in prompt_lower and any(word in prompt_lower for word in ["job", "search", "engineer", "developer", "naukri", "kaam"]):
            # Detect language for classification
            language = self._detect_language(prompt)
            return f'''{{
  "category": "JOB_SEARCH",
  "confidence": 0.95,
  "extractedData": {{
    "job_title": "software engineer",
    "location": "remote",
    "language": "{language}"
  }},
  "searchQuery": "software engineer remote jobs"
}}'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["resume", "cv", "biodata"]):
            language = self._detect_language(prompt)
            return f'''{{
  "category": "RESUME_ANALYSIS",
  "confidence": 0.9,
  "extractedData": {{
    "language": "{language}"
  }},
  "searchQuery": ""
}}'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["career", "advice", "raah", "guidance"]):
            language = self._detect_language(prompt)
            return f'''{{
  "category": "CAREER_ADVICE",
  "confidence": 0.85,
  "extractedData": {{
    "language": "{language}"
  }},
  "searchQuery": ""
}}'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["project", "suggestion"]):
            language = self._detect_language(prompt)
            return f'''{{
  "category": "PROJECT_SUGGESTION",
  "confidence": 0.8,
  "extractedData": {{
    "language": "{language}"
  }},
  "searchQuery": ""
}}'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["profile", "name", "info", "naam", "kaun"]):
            language = self._detect_language(prompt)
            return f'''{{
  "category": "PROFILE_INFO",
  "confidence": 0.8,
  "extractedData": {{
    "language": "{language}"
  }},
  "searchQuery": ""
}}'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["naam", "name", "tumhara naam", "your name", "who are you", "kaun ho"]):
            language = self._detect_language(prompt)
            return f'''{{
  "category": "GENERAL_CHAT",
  "confidence": 0.9,
  "extractedData": {{
    "casual_chat": true,
    "language": "{language}"
  }},
  "searchQuery": ""
}}'''
        else:
            # For non-classification queries, provide contextual mock responses
            language = self._detect_language(prompt)
            
            # Handle name questions
            if any(word in prompt_lower for word in ["naam", "name", "tumhara naam", "your name", "who are you", "kaun ho"]):
                return random.choice(self.mock_responses['name_responses'])
            
            # Handle casual chat based on language
            if language == 'hindi':
                return random.choice(self.mock_responses['casual_hindi'])
            elif language == 'hinglish':
                return random.choice(self.mock_responses['casual_hinglish'])
            else:
                # Handle different types of English queries
                if any(word in prompt_lower for word in ["job", "search", "engineer", "developer"]):
                    return "I'd be happy to help you find software engineering jobs! 🚀 Based on your query, I found several opportunities that might interest you. While I'm running in demo mode, in the full version I would search our extensive job database and provide personalized recommendations based on your profile and preferences. What specific role are you looking for?"
                elif any(word in prompt_lower for word in ["resume", "cv", "analyze"]):
                    return "I'd love to help analyze your resume! 📄 In demo mode, I can tell you that a strong resume typically includes:\n\n• Clear contact information\n• Professional summary\n• Relevant work experience with quantified achievements\n• Technical skills section\n• Education and certifications\n\nFor a full analysis, please ensure you've uploaded your resume and try again with a real API connection."
                elif any(word in prompt_lower for word in ["career", "advice"]):
                    return "I'm here to provide career guidance! 💼 Based on current market trends, here are some general recommendations:\n\n• Focus on in-demand skills like data analysis, cloud computing, or AI/ML\n• Build a strong online presence (LinkedIn, GitHub)\n• Network within your industry\n• Consider continuous learning and certifications\n• Tailor your applications to specific roles\n\nFor personalized advice, I'd need to access your profile and understand your specific career goals. What's your current situation?"
                elif any(word in prompt_lower for word in ["project", "suggestion"]):
                    return "Here are some great project ideas to build your skills! 🎯\n\n**For Beginners:**\n• Personal portfolio website\n• Todo list application\n• Weather app with API integration\n\n**Intermediate:**\n• E-commerce platform\n• Data visualization dashboard\n• Chat application with real-time features\n\n**Advanced:**\n• Machine learning prediction model\n• Microservices architecture project\n• Mobile app with backend integration\n\nChoose projects that align with your career goals and showcase the skills you want to develop!"
                else:
                    return random.choice(self.mock_responses['casual_english'])
            
            # Default classification for unrecognized queries
            return f'''{{
  "category": "GENERAL_CHAT",
  "confidence": 0.7,
  "extractedData": {{
    "language": "{language}"
  }},
  "searchQuery": ""
}}'''
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when LLM fails"""
        fallback_responses = [
            "Oops! Technical issue ho gaya hai. 😅 But don't worry, I'm still here to help with your career goals! Kya kar sakte hain aapke liye?",
            "Sorry yaar, kuch technical problem hai! 🤖 But I'm ready to help with jobs, resume, career advice. What do you need?",
            "I apologize, but I'm experiencing technical difficulties. Please try again in a moment, or let me know how I can help with your career! 💼"
        ]
        return random.choice(fallback_responses) 