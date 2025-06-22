import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from .mongodb_manager import MongoDBManager

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages conversation memory and history with MongoDB persistence"""
    
    def __init__(self, mongodb_uri: str = None, database_name: str = 'admin', collection_name: str = 'mato_chats'):
        # MongoDB storage for persistent conversation history
        if mongodb_uri:
            self.mongodb_manager = MongoDBManager(mongodb_uri, database_name, collection_name)
            self.use_mongodb = True
        else:
            self.mongodb_manager = None
            self.use_mongodb = False
            # Fallback to in-memory storage
            self.conversations = {}
        
        self.max_history_length = 10  # Keep last 10 exchanges
        self.session_timeout = timedelta(hours=24)  # 24-hour session timeout
    
    async def get_conversation_history(self, session_id: str) -> str:
        """Get conversation history for a session"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                # Use MongoDB for persistent storage
                return await self.mongodb_manager.get_formatted_history(session_id, self.max_history_length)
            else:
                # Fallback to in-memory storage
                if session_id not in self.conversations:
                    return ""
                
                session_data = self.conversations[session_id]
                
                # Check if session has expired
                last_activity = datetime.fromisoformat(session_data.get('last_activity', ''))
                if datetime.now() - last_activity > self.session_timeout:
                    # Session expired, clear it
                    del self.conversations[session_id]
                    return ""
                
                # Format conversation history
                history = session_data.get('history', [])
                formatted_history = []
                
                for exchange in history[-self.max_history_length:]:
                    formatted_history.append(f"User: {exchange['user']}")
                    formatted_history.append(f"Assistant: {exchange['assistant']}")
                
                return "\n".join(formatted_history)
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return ""
    
    async def store_conversation(self, session_id: str, user_message: str, assistant_message: str, metadata: Dict[str, Any] = None):
        """Store a conversation exchange"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                # Store in MongoDB
                await self.mongodb_manager.store_message(
                    session_id, 
                    user_message, 
                    assistant_message, 
                    'chat',
                    metadata
                )
            else:
                # Fallback to in-memory storage
                if session_id not in self.conversations:
                    self.conversations[session_id] = {
                        'history': [],
                        'created_at': datetime.now().isoformat(),
                        'last_activity': datetime.now().isoformat()
                    }
                
                # Add new exchange
                exchange = {
                    'user': user_message,
                    'assistant': assistant_message,
                    'timestamp': datetime.now().isoformat(),
                    'metadata': metadata or {}
                }
                
                self.conversations[session_id]['history'].append(exchange)
                self.conversations[session_id]['last_activity'] = datetime.now().isoformat()
                
                # Keep only the most recent exchanges
                if len(self.conversations[session_id]['history']) > self.max_history_length:
                    self.conversations[session_id]['history'] = \
                        self.conversations[session_id]['history'][-self.max_history_length:]
            
        except Exception as e:
            logger.error(f"Error storing conversation: {str(e)}")
    
    async def clear_session(self, session_id: str):
        """Clear conversation history for a session"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                await self.mongodb_manager.clear_session_history(session_id)
            else:
                if session_id in self.conversations:
                    del self.conversations[session_id]
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get session information"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                return await self.mongodb_manager.get_session_stats(session_id)
            else:
                if session_id not in self.conversations:
                    return {}
                
                session_data = self.conversations[session_id]
                return {
                    'session_id': session_id,
                    'created_at': session_data.get('created_at'),
                    'last_activity': session_data.get('last_activity'),
                    'message_count': len(session_data.get('history', []))
                }
            
        except Exception as e:
            logger.error(f"Error getting session info: {str(e)}")
            return {} 