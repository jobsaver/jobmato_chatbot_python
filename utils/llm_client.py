import logging
import os
from typing import Dict, Any, Optional
import google.generativeai as genai
from datetime import datetime
import hashlib
import json

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
        
        # Use the fastest model for better performance
        self.model = genai.GenerativeModel('gemini-2.5-flash') 
        
        # Disable safety filters
        self.model = genai.GenerativeModel(
            'gemini-2.5-flash',
            safety_settings=[
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH", 
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
        )
        
        # Simple in-memory cache for repeated queries
        self.cache = {}
        self.cache_size = 100  # Keep last 100 responses

    async def generate_response(self, prompt: str, system_message: str = "", max_tokens:Optional[int] = 512) -> str:
        """Generate a response using the language model with caching"""
        try:
            # Create cache key
            cache_key = self._create_cache_key(prompt, system_message)
            
            # Check cache first
            if cache_key in self.cache:
                logger.info("✅ Using cached LLM response")
                return self.cache[cache_key]
            
            # Optimize generation config for speed
            generation_config = genai.GenerationConfig(
                temperature=0.3,  # Lower temperature for faster, more consistent responses
                max_output_tokens=max_tokens,
                top_p=0.8,
                top_k=40
            )
            
            # Optimize prompt length
            if len(system_message) > 1000:
                system_message = system_message[:1000] + "..."
            
            full_prompt = f"{system_message}\n\nUser: {prompt}\n\nAssistant:"
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )
            
            if response.text:
                result = response.text.strip()
                
                # Cache the result
                self._cache_result(cache_key, result)
                
                return result
            else:
                logger.error("Empty response from language model")
                return {"error": "Empty response from language model"}
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            
            # Check if it's a safety filter error
            if "finish_reason" in str(e) and "2" in str(e):
                logger.warning("⚠️ Safety filter triggered - content blocked")
                return {"error": "safety_filter", "message": "Content blocked by safety filters"}
            
            return {"error": str(e)}
    
    def _create_cache_key(self, prompt: str, system_message: str) -> str:
        """Create a cache key for the prompt"""
        content = f"{prompt}:{system_message}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _cache_result(self, cache_key: str, result: str):
        """Cache the result with LRU eviction"""
        if len(self.cache) >= self.cache_size:
            # Remove oldest entry (simple LRU)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = result
    
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