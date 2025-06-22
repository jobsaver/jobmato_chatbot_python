import logging
import os
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
    
    def _get_mock_response(self, prompt: str) -> str:
        """Generate mock responses for testing when API key is not available"""
        prompt_lower = prompt.lower()
        
        # Mock classification responses
        if "user query:" in prompt_lower and any(word in prompt_lower for word in ["job", "search", "engineer", "developer"]):
            return '''```json
{
  "category": "JOB_SEARCH",
  "confidence": 0.95,
  "extractedData": {
    "job_title": "software engineer",
    "location": "remote"
  },
  "searchQuery": "software engineer remote jobs"
}
```'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["resume", "cv"]):
            return '''```json
{
  "category": "RESUME_ANALYSIS",
  "confidence": 0.9,
  "extractedData": {},
  "searchQuery": ""
}
```'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["career", "advice"]):
            return '''```json
{
  "category": "CAREER_ADVICE",
  "confidence": 0.85,
  "extractedData": {},
  "searchQuery": ""
}
```'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["project", "suggestion"]):
            return '''```json
{
  "category": "PROJECT_SUGGESTION",
  "confidence": 0.8,
  "extractedData": {},
  "searchQuery": ""
}
```'''
        elif "user query:" in prompt_lower and any(word in prompt_lower for word in ["profile", "name", "info"]):
            return '''```json
{
  "category": "PROFILE_INFO",
  "confidence": 0.8,
  "extractedData": {},
  "searchQuery": ""
}
```'''
        else:
            # For non-classification queries, provide helpful mock responses
            if any(word in prompt_lower for word in ["job", "search", "engineer", "developer"]):
                return "I'd be happy to help you find software engineering jobs! Based on your query, I found several opportunities that might interest you. While I'm running in demo mode, in the full version I would search our extensive job database and provide personalized recommendations based on your profile and preferences."
            elif any(word in prompt_lower for word in ["resume", "cv", "analyze"]):
                return "I'd love to help analyze your resume! In demo mode, I can tell you that a strong resume typically includes:\n\n• Clear contact information\n• Professional summary\n• Relevant work experience with quantified achievements\n• Technical skills section\n• Education and certifications\n\nFor a full analysis, please ensure you've uploaded your resume and try again with a real API connection."
            elif any(word in prompt_lower for word in ["career", "advice"]):
                return "I'm here to provide career guidance! Based on current market trends, here are some general recommendations:\n\n• Focus on in-demand skills like data analysis, cloud computing, or AI/ML\n• Build a strong online presence (LinkedIn, GitHub)\n• Network within your industry\n• Consider continuous learning and certifications\n• Tailor your applications to specific roles\n\nFor personalized advice, I'd need to access your profile and understand your specific career goals."
            elif any(word in prompt_lower for word in ["project", "suggestion"]):
                return "Here are some great project ideas to build your skills:\n\n**For Beginners:**\n• Personal portfolio website\n• Todo list application\n• Weather app with API integration\n\n**Intermediate:**\n• E-commerce platform\n• Data visualization dashboard\n• Chat application with real-time features\n\n**Advanced:**\n• Machine learning prediction model\n• Microservices architecture project\n• Mobile app with backend integration\n\nChoose projects that align with your career goals and showcase the skills you want to develop!"
            else:
                return '''```json
{
  "category": "GENERAL_CHAT",
  "confidence": 0.7,
  "extractedData": {},
  "searchQuery": ""
}
```'''
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when LLM fails"""
        return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment, or contact support if the issue persists." 