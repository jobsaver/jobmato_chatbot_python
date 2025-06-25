import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from .mongodb_manager import MongoDBManager

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages conversation memory and history with MongoDB persistence (chatsessions model)"""
    
    def __init__(self, mongodb_uri: str = None, database_name: str = 'admin', collection_name: str = 'chatsessions'):
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

    async def get_last_n_messages(self, session_id: str, n: int = 5) -> list:
        """Get the last n messages for a session (for chat context)"""
        if self.use_mongodb and self.mongodb_manager:
            return await self.mongodb_manager.get_last_n_messages(session_id, n)
        else:
            if session_id not in self.conversations:
                return []
            history = self.conversations[session_id].get('history', [])
            return history[-n:]

    async def get_all_messages(self, session_id: str) -> list:
        """Get all messages for a session"""
        if self.use_mongodb and self.mongodb_manager:
            return await self.mongodb_manager.get_all_messages(session_id)
        else:
            if session_id not in self.conversations:
                return []
            return self.conversations[session_id].get('history', [])

    async def get_user_sessions(self, user_id: str, limit: int = 20) -> list:
        """Get all sessions for a user"""
        if self.use_mongodb and self.mongodb_manager:
            return await self.mongodb_manager.get_user_sessions(user_id, limit)
        else:
            # Fallback for in-memory storage
            sessions = []
            for session_id, session_data in self.conversations.items():
                if session_data.get('user_id') == user_id:
                    sessions.append({
                        'sessionId': session_id,
                        'title': session_data.get('title', 'New Chat'),
                        'createdAt': session_data.get('created_at'),
                        'updatedAt': session_data.get('last_activity'),
                        'messageCount': len(session_data.get('history', []))
                    })
            # Sort by last activity
            sessions.sort(key=lambda x: x['updatedAt'], reverse=True)
            return sessions[:limit]

    async def get_conversation_history(self, session_id: str, limit: int = 5) -> str:
        """Get conversation history for a session (last 5 messages)"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                # Use MongoDB for persistent storage, last 5 messages
                messages = await self.mongodb_manager.get_last_n_messages(session_id, limit)
                if not messages:
                    return ""
                
                formatted_history = []
                for msg in messages:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    formatted_history.append(f"{role.capitalize()}: {content}")
                
                return "\n".join(formatted_history)
            else:
                # Fallback to in-memory storage
                if session_id not in self.conversations:
                    return ""
                session_data = self.conversations[session_id]
                last_5 = session_data.get('history', [])[-limit:]
                formatted_history = []
                for msg in last_5:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    formatted_history.append(f"{role.capitalize()}: {content}")
                return "\n".join(formatted_history)
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return ""

    async def get_conversation_context_for_agents(self, session_id: str, limit: int = 3) -> str:
        """Get conversation context specifically formatted for agents (last 3 messages)"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                return await self.mongodb_manager.get_conversation_context_for_agents(session_id, limit)
            else:
                # Fallback to in-memory storage
                if session_id not in self.conversations:
                    return ""
                session_data = self.conversations[session_id]
                last_3 = session_data.get('history', [])[-limit:]
                formatted_history = []
                for msg in last_3:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')
                    # Truncate very long messages to keep context manageable
                    if len(content) > 200:
                        content = content[:200] + "..."
                    formatted_history.append(f"{role.capitalize()}: {content}")
                return "\n".join(formatted_history)
        except Exception as e:
            logger.error(f"Error getting conversation context for agents: {str(e)}")
            return ""

    async def store_conversation(self, session_id: str, user_message: str, assistant_message: str, metadata: Dict[str, Any] = None, user_id: str = None, user_profile: Dict[str, Any] = None):
        """Store a conversation exchange as a message in the chat session"""
        try:
            now = datetime.utcnow()
            if self.use_mongodb and self.mongodb_manager:
                # Store as a message in the chat session's messages array
                # Store user message
                user_msg = {
                    'role': 'user',
                    'content': user_message,
                    'timestamp': now,
                    'type': 'plain_text',
                    'metadata': metadata or {}
                }
                await self.mongodb_manager.upsert_message(
                    session_id=session_id,
                    user_id=user_id or 'unknown',
                    message=user_msg,
                    user_profile=user_profile,
                    metadata=metadata
                )
                # Store assistant message
                assistant_msg = {
                    'role': 'assistant',
                    'content': assistant_message,
                    'timestamp': now,
                    'type': 'plain_text',
                    'metadata': metadata or {}
                }
                await self.mongodb_manager.upsert_message(
                    session_id=session_id,
                    user_id=user_id or 'unknown',
                    message=assistant_msg,
                    user_profile=user_profile,
                    metadata=metadata
                )
            else:
                # Fallback to in-memory storage
                if session_id not in self.conversations:
                    self.conversations[session_id] = {
                        'history': [],
                        'created_at': datetime.now().isoformat(),
                        'last_activity': datetime.now().isoformat(),
                        'user_id': user_id or 'unknown'
                    }
                # Add user and assistant messages
                self.conversations[session_id]['history'].append({
                    'role': 'user',
                    'content': user_message,
                    'timestamp': now.isoformat(),
                    'type': 'plain_text',
                    'metadata': metadata or {}
                })
                self.conversations[session_id]['history'].append({
                    'role': 'assistant',
                    'content': assistant_message,
                    'timestamp': now.isoformat(),
                    'type': 'plain_text',
                    'metadata': metadata or {}
                })
                self.conversations[session_id]['last_activity'] = datetime.now().isoformat()
                # Keep only the most recent exchanges
                if len(self.conversations[session_id]['history']) > self.max_history_length:
                    self.conversations[session_id]['history'] = \
                        self.conversations[session_id]['history'][-self.max_history_length:]
        except Exception as e:
            logger.error(f"Error storing conversation: {str(e)}")

    async def update_session_title(self, session_id: str, title: str) -> bool:
        """Update the title of a session"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                return await self.mongodb_manager.update_session_title(session_id, title)
            else:
                # Fallback to in-memory storage
                if session_id in self.conversations:
                    self.conversations[session_id]['title'] = title
                    return True
                return False
        except Exception as e:
            logger.error(f"Error updating session title: {str(e)}")
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                return await self.mongodb_manager.delete_session(session_id)
            else:
                # Fallback to in-memory storage
                if session_id in self.conversations:
                    del self.conversations[session_id]
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting session: {str(e)}")
            return False

    async def clear_session(self, session_id: str):
        """Clear conversation history for a session"""
        try:
            if self.use_mongodb and self.mongodb_manager:
                await self.mongodb_manager.clear_session_history(session_id)
            else:
                if session_id in self.conversations:
                    self.conversations[session_id]['history'] = []
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
                    'message_count': len(session_data.get('history', [])),
                    'title': session_data.get('title', 'New Chat')
                }
        except Exception as e:
            logger.error(f"Error getting session info: {str(e)}")
            return {} 