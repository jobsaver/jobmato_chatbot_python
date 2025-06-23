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
            logger.error("GOOGLE_API_KEY not found in environment variables.")
            raise ValueError("Google API key is required")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')
    
    async def generate_response(self, prompt: str, system_message: str = "", max_tokens:Optional[int] = 512) -> str:
        """Generate a response using the language model"""
        try:
            # Combine system message and prompt
            generation_config = genai.GenerationConfig(
                max_output_tokens=max_tokens
            )
            full_prompt = f"{system_message}\n\nUser: {prompt}\n\nAssistant:"
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
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
    
    def _get_fallback_response(self) -> str:
        """Get a fallback response when LLM fails"""
        return "I apologize, but I'm experiencing technical difficulties. Please try again in a moment, or let me know how I can help with your career! 💼" 