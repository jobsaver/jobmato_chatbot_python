import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
import json

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Manages MongoDB operations for chat session storage (chatsessions collection)"""
    
    def __init__(self, mongodb_uri: str, database_name: str = 'admin', collection_name: str = 'chatsessions'):
        self.mongodb_uri = mongodb_uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        self.connected = False
        self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB"""
        try:
            self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            # Test the connection
            self.client.admin.command('ismaster')
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            self.connected = True
            logger.info(f"✅ Connected to MongoDB: {self.database_name}.{self.collection_name}")
            
            # Create indexes for better performance
            self._create_indexes()
            
        except ConnectionFailure as e:
            logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ MongoDB connection error: {str(e)}")
            self.connected = False
    
    def _create_indexes(self):
        """Create necessary indexes"""
        try:
            # First, clean up any documents with null sessionId
            self.collection.delete_many({"sessionId": None})
            
            # Create indexes with sparse option to handle missing fields
            self.collection.create_index("sessionId", unique=True, sparse=True)
            self.collection.create_index("userId", sparse=True)
            self.collection.create_index("updatedAt", sparse=True)
            logger.info("📊 MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not create indexes: {str(e)}")
    
    async def upsert_message(self, session_id: str, user_id: str, message: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None, metadata: Optional[Dict[str, Any]] = None):
        """Upsert a message into the chat session's messages array"""
        if not self.connected:
            logger.warning("MongoDB not connected, attempting to reconnect...")
            self._connect()
            if not self.connected:
                return False
        
        try:
            now = datetime.utcnow()
            update_doc = {
                '$setOnInsert': {
                    'sessionId': session_id,
                    'userId': user_id,
                    'title': 'New Chat',
                    'createdAt': now,
                },
                '$set': {
                    'updatedAt': now,
                },
                '$push': {
                    'messages': message
                }
            }
            if user_profile:
                update_doc['$set']['userProfile'] = user_profile
            if metadata:
                update_doc['$set']['metadata'] = metadata
            self.collection.update_one(
                {'sessionId': session_id},
                update_doc,
                upsert=True
            )
            logger.info(f"💾 Message upserted for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error upserting message: {str(e)}")
            return False
    
    async def get_last_n_messages(self, session_id: str, n: int = 5) -> List[Dict[str, Any]]:
        """Get the last n messages for a session (chronological order)"""
        if not self.connected:
            logger.warning("MongoDB not connected, attempting to reconnect...")
            self._connect()
            if not self.connected:
                return []
        
        try:
            session = self.collection.find_one({'sessionId': session_id}, {'messages': 1})
            if session and 'messages' in session:
                return session['messages'][-n:]
            return []
            
        except Exception as e:
            logger.error(f"❌ Error getting last n messages: {str(e)}")
            return []
    
    async def get_formatted_history(self, session_id: str, limit: int = 5) -> str:
        """Get formatted conversation history as string (last n messages)"""
        messages = await self.get_last_n_messages(session_id, limit)
        
        if not messages:
            return ""
        
        formatted_history = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            formatted_history.append(f"{role.capitalize()}: {content}")
        
        return "\n".join(formatted_history)
    
    async def clear_session_history(self, session_id: str) -> bool:
        """Clear all messages for a session"""
        if not self.connected:
            logger.warning("MongoDB not connected, attempting to reconnect...")
            self._connect()
            if not self.connected:
                return False
        
        try:
            result = self.collection.update_one({'sessionId': session_id}, {'$set': {'messages': []}})
            logger.info(f"🗑️ Cleared messages for session {session_id}")
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"❌ Error clearing session: {str(e)}")
            return False
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        if not self.connected:
            logger.warning("MongoDB not connected, attempting to reconnect...")
            self._connect()
            if not self.connected:
                return {}
        
        try:
            session = self.collection.find_one({'sessionId': session_id})
            if session:
                return {
                    'session_id': session_id,
                    'message_count': len(session.get('messages', [])),
                    'created_at': session.get('createdAt'),
                    'updated_at': session.get('updatedAt'),
                    'user_id': session.get('userId'),
                    'title': session.get('title'),
                }
            else:
                return {'session_id': session_id, 'message_count': 0}
                
        except Exception as e:
            logger.error(f"❌ Error getting session stats: {str(e)}")
            return {}
    
    async def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """Clean up sessions older than specified days"""
        if not self.connected:
            return 0
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            result = self.collection.delete_many({'updatedAt': {'$lt': cutoff_date}})
            
            deleted_count = result.deleted_count
            logger.info(f"🧹 Cleaned up {deleted_count} old messages (older than {days_old} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {str(e)}")
            return 0
    
    async def search_messages(self, query: str, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search messages by text content"""
        if not self.connected:
            return []
        
        try:
            # Build search filter
            search_filter = {
                '$or': [
                    {'messages.content': {'$regex': query, '$options': 'i'}},
                ]
            }
            
            if session_id:
                search_filter['sessionId'] = session_id
            
            cursor = self.collection.find(search_filter).sort('updatedAt', DESCENDING).limit(limit)
            return list(cursor)
            
        except Exception as e:
            logger.error(f"❌ Error searching messages: {str(e)}")
            return []
    
    def close_connection(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("📴 MongoDB connection closed")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.close_connection() 