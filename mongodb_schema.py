# mongodb_schema.py
from pymongo import MongoClient
import datetime
from bson.objectid import ObjectId

def setup_database(connection_string='mongodb://localhost:27017/'):
    """Set up the MongoDB database with proper collections and indexes"""
    client = MongoClient(connection_string)
    db = client['knowledge_base']
    
    # Create collections if they don't exist
    if 'notes' not in db.list_collection_names():
        db.create_collection('notes')
    
    if 'vaults' not in db.list_collection_names():
        db.create_collection('vaults')
    
    if 'tags' not in db.list_collection_names():
        db.create_collection('tags')
    
    # Set up indexes
    notes_collection = db['notes']
    notes_collection.create_index('title')
    notes_collection.create_index('content')
    notes_collection.create_index('vault_id')
    notes_collection.create_index('tags')
    
    # Set up text search index
    try:
        notes_collection.create_index([
            ('title', 'text'),
            ('content', 'text'),
            ('tags', 'text')
        ])
    except Exception as e:
        print(f"Warning: Could not create text index: {e}")
    
    # Set up schema validation
    db.command('collMod', 'notes', validator={
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['title', 'content', 'created_at', 'updated_at'],
            'properties': {
                'title': {
                    'bsonType': 'string',
                    'description': 'Title of the note'
                },
                'content': {
                    'bsonType': 'string',
                    'description': 'Content of the note'
                },
                'vault_id': {
                    'bsonType': ['objectId', 'null'],
                    'description': 'ID of the vault this note belongs to'
                },
                'tags': {
                    'bsonType': 'array',
                    'description': 'List of tags associated with the note'
                },
                'links': {
                    'bsonType': 'array',
                    'description': 'List of links extracted from the note content'
                },
                'created_at': {
                    'bsonType': 'date',
                    'description': 'Date when the note was created'
                },
                'updated_at': {
                    'bsonType': 'date',
                    'description': 'Date when the note was last updated'
                }
            }
        }
    })
    
    db.command('collMod', 'vaults', validator={
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['name', 'created_at', 'updated_at'],
            'properties': {
                'name': {
                    'bsonType': 'string',
                    'description': 'Name of the vault'
                },
                'description': {
                    'bsonType': 'string',
                    'description': 'Description of the vault'
                },
                'created_at': {
                    'bsonType': 'date',
                    'description': 'Date when the vault was created'
                },
                'updated_at': {
                    'bsonType': 'date',
                    'description': 'Date when the vault was last updated'
                }
            }
        }
    })
    
    db.command('collMod', 'tags', validator={
        '$jsonSchema': {
            'bsonType': 'object',
            'required': ['name', 'note_ids'],
            'properties': {
                'name': {
                    'bsonType': 'string',
                    'description': 'Tag name'
                },
                'note_ids': {
                    'bsonType': 'array',
                    'description': 'List of note IDs that have this tag'
                }
            }
        }
    })
    
    print("Database setup complete!")
    return db

# Sample data structures for reference

# Note document
sample_note = {
    '_id': ObjectId(),  # MongoDB generated ID
    'title': 'Sample Note',
    'content': 'This is a sample note with a [[link]] to another note.',
    'vault_id': ObjectId(),  # Reference to vault
    'tags': ['sample', 'example'],
    'links': ['link'],  # Extracted from content
    'created_at': datetime.datetime.now(),
    'updated_at': datetime.datetime.now(),
    # Enhanced fields from the AI-powered system
    'keywords': ['sample', 'note', 'link'],  # AI-extracted keywords
    'context': 'Documentation about note linking',  # Contextual description
    'importance_score': 1.0,  # Importance score (0.0-2.0)
    'retrieval_count': 0,  # Number of times this note has been retrieved
    'last_accessed': datetime.datetime.now().strftime("%Y%m%d%H%M")  # Last access timestamp
}

# Vault document
sample_vault = {
    '_id': ObjectId(),  # MongoDB generated ID
    'name': 'Sample Vault',
    'description': 'This is a sample vault for storing notes',
    'created_at': datetime.datetime.now(),
    'updated_at': datetime.datetime.now()
}

# Tag document
sample_tag = {
    '_id': ObjectId(),  # MongoDB generated ID
    'name': 'sample',
    'note_ids': [ObjectId()]  # References to notes with this tag
}

if __name__ == '__main__':
    # Run this script to initialize the database
    setup_database()