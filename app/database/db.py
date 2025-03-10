"""
Database initialization and common operations
"""
from pymongo import MongoClient
from app.config.config import MONGO_URI, MONGO_DB_NAME, logger

# Initialize MongoDB connection
client = MongoClient(MONGO_URI)
db = client[MONGO_DB_NAME]
notes_collection = db['notes']
vaults_collection = db['vaults']
tags_collection = db['tags']

# Ensure indexes for performance
def ensure_indexes():
    """Create necessary indexes on collections"""
    notes_collection.create_index('title')
    notes_collection.create_index('content')
    notes_collection.create_index('vault_id')
    notes_collection.create_index('tags')
    
    # Create text index for better search
    try:
        notes_collection.create_index([
            ('title', 'text'),
            ('content', 'text'),
            ('tags', 'text')
        ])
        return True
    except Exception as e:
        logger.error(f"Could not create text index: {e}")
        return False