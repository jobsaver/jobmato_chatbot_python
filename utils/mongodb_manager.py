import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
import json

logger = logging.getLogger(__name__)

class MongoDBManager:
    """Manages MongoDB operations for chat storage"""
    
    def __init__(self, mongodb_uri: str, database_name: str = 'admin', collection_name: str = 'mato_chats'):
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
            # Index on session_id for faster queries
            self.collection.create_index("session_id")
            # Index on timestamp for cleanup operations
            self.collection.create_index("timestamp")
            # Compound index for session queries
            self.collection.create_index([("session_id", 1), ("timestamp", -1)])
            logger.info("📊 MongoDB indexes created successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not create indexes: {str(e)}")
    
    async def store_message(self, session_id: str, user_message: str, assistant_message: str, 
                          message_type: str = 'chat', metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a chat message in MongoDB"""
        if not self.connected:
            logger.warning("MongoDB not connected, attempting to reconnect...")
            self._connect()
            if not self.connected:
                return False
        
        try:
            document = {
                'session_id': session_id,
                'user_message': user_message,
                'assistant_message': assistant_message,
                'message_type': message_type,
                'metadata': metadata or {},
                'timestamp': datetime.utcnow(),
                'created_at': datetime.utcnow().isoformat()
            }
            
            result = self.collection.insert_one(document)
            logger.info(f"💾 Message stored with ID: {result.inserted_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error storing message: {str(e)}")
            return False
    
    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get conversation history for a session"""
        if not self.connected:
            return []
        
        try:
            cursor = self.collection.find(
                {'session_id': session_id}
            ).sort('timestamp', -1).limit(limit)
            
            messages = list(cursor)
            # Reverse to get chronological order
            messages.reverse()
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error getting conversation history: {str(e)}")
            return []
    
    async def get_formatted_history(self, session_id: str, limit: int = 10) -> str:
        """Get formatted conversation history as string"""
        messages = await self.get_conversation_history(session_id, limit)
        
        if not messages:
            return ""
        
        formatted_history = []
        for msg in messages:
            formatted_history.append(f"User: {msg.get('user_message', '')}")
            formatted_history.append(f"Assistant: {msg.get('assistant_message', '')}")
        
        return "\n".join(formatted_history)
    
    async def clear_session_history(self, session_id: str) -> bool:
        """Clear all messages for a session"""
        if not self.connected:
            return False
        
        try:
            result = self.collection.delete_many({'session_id': session_id})
            logger.info(f"🗑️ Cleared {result.deleted_count} messages for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error clearing session: {str(e)}")
            return False
    
    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        if not self.connected:
            return {}
        
        try:
            pipeline = [
                {'$match': {'session_id': session_id}},
                {'$group': {
                    '_id': '$session_id',
                    'message_count': {'$sum': 1},
                    'first_message': {'$min': '$timestamp'},
                    'last_message': {'$max': '$timestamp'}
                }}
            ]
            
            result = list(self.collection.aggregate(pipeline))
            
            if result:
                stats = result[0]
                return {
                    'session_id': session_id,
                    'message_count': stats['message_count'],
                    'first_message': stats['first_message'].isoformat() if stats['first_message'] else None,
                    'last_message': stats['last_message'].isoformat() if stats['last_message'] else None,
                    'duration_minutes': (stats['last_message'] - stats['first_message']).total_seconds() / 60 if stats['first_message'] and stats['last_message'] else 0
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
            result = self.collection.delete_many({'timestamp': {'$lt': cutoff_date}})
            
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
                    {'user_message': {'$regex': query, '$options': 'i'}},
                    {'assistant_message': {'$regex': query, '$options': 'i'}}
                ]
            }
            
            if session_id:
                search_filter['session_id'] = session_id
            
            cursor = self.collection.find(search_filter).sort('timestamp', -1).limit(limit)
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