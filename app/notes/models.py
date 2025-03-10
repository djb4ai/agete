"""
Note model and operations
"""
import datetime
from bson.objectid import ObjectId
from typing import Dict, Any, List, Optional
from app.database.db import notes_collection, tags_collection
from app.utils.helpers import extract_links, note_to_dict
from app.config.config import logger

def find_note_by_id(note_id: str) -> Optional[Dict[str, Any]]:
    """Find a note by ID"""
    try:
        note_object_id = ObjectId(note_id)
        note = notes_collection.find_one({'_id': note_object_id})
        return note
    except Exception as e:
        logger.error(f"Error finding note by ID: {str(e)}")
        return None

def find_notes_by_vault(vault_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Find notes by vault ID"""
    query = {}
    
    if vault_id:
        try:
            query['vault_id'] = ObjectId(vault_id)
        except:
            logger.error("Invalid vault ID")
            return []
    
    notes = list(notes_collection.find(query))
    return [note_to_dict(note) for note in notes]

def find_notes_by_tag(tag: str) -> List[Dict[str, Any]]:
    """Find notes by tag"""
    query = {'tags': tag}
    notes = list(notes_collection.find(query))
    return [note_to_dict(note) for note in notes]

def find_notes_by_search(search: str, vault_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Find notes by search term"""
    query = {}
    
    if vault_id:
        try:
            query['vault_id'] = ObjectId(vault_id)
        except:
            logger.error("Invalid vault ID")
            return []
    
    if search:
        query['$or'] = [
            {'title': {'$regex': search, '$options': 'i'}},
            {'content': {'$regex': search, '$options': 'i'}}
        ]
    
    notes = list(notes_collection.find(query))
    return [note_to_dict(note) for note in notes]

def create_note(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new note"""
    # Extract vault_id and convert to ObjectId if provided
    vault_id = None
    if 'vault_id' in data and data['vault_id']:
        try:
            vault_id = ObjectId(data['vault_id'])
        except:
            logger.error("Invalid vault ID")
    
    # Extract links and tags from content
    links = extract_links(data['content'])
    tags = data.get('tags', [])
    
    # Create note with basic metadata
    note = {
        'title': data['title'],
        'content': data['content'],
        'vault_id': vault_id,
        'tags': tags,
        'links': links,
        'created_at': datetime.datetime.now(),
        'updated_at': datetime.datetime.now(),
        'last_accessed': datetime.datetime.now().strftime("%Y%m%d%H%M"),
        'retrieval_count': 0,
        'keywords': data.get('keywords', []),
        'context': data.get('context', 'General'),
        'importance_score': data.get('importance_score', 1.0)
    }
    
    # Store note
    result = notes_collection.insert_one(note)
    note_id = result.inserted_id
    
    # Update tags collection
    for tag in tags:
        tags_collection.update_one(
            {'name': tag},
            {'$set': {'name': tag}, '$addToSet': {'note_ids': note_id}},
            upsert=True
        )
    
    # Return the created note
    note['_id'] = str(note_id)
    note['vault_id'] = str(vault_id) if vault_id else None
    
    return note

def update_note(note_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a note"""
    try:
        note_object_id = ObjectId(note_id)
    except:
        logger.error("Invalid note ID")
        return {'success': False, 'error': 'Invalid note ID'}
    
    # Get existing note to handle tags
    existing_note = notes_collection.find_one({'_id': note_object_id})
    if not existing_note:
        return {'success': False, 'error': 'Note not found'}
    
    # Prepare update data
    update_data = {
        'updated_at': datetime.datetime.now()
    }
    
    # Update fields if provided
    if 'title' in data:
        update_data['title'] = data['title']
        
    if 'content' in data:
        update_data['content'] = data['content']
        update_data['links'] = extract_links(data['content'])
    
    # Handle vault_id
    if 'vault_id' in data:
        if data['vault_id']:
            try:
                update_data['vault_id'] = ObjectId(data['vault_id'])
            except:
                logger.error("Invalid vault ID")
                return {'success': False, 'error': 'Invalid vault ID'}
        else:
            update_data['vault_id'] = None
    
    # Handle tags
    if 'tags' in data:
        update_data['tags'] = data['tags']
        
        # Remove note from old tags that are no longer used
        old_tags = set(existing_note.get('tags', []))
        new_tags = set(data['tags'])
        
        # Tags to remove
        for tag in old_tags - new_tags:
            tags_collection.update_one(
                {'name': tag},
                {'$pull': {'note_ids': note_object_id}}
            )
        
        # Tags to add
        for tag in new_tags - old_tags:
            tags_collection.update_one(
                {'name': tag},
                {'$set': {'name': tag}, '$addToSet': {'note_ids': note_object_id}},
                upsert=True
            )
    
    # Update other fields if provided
    if 'keywords' in data:
        update_data['keywords'] = data['keywords']
    
    if 'context' in data:
        update_data['context'] = data['context']
    
    if 'importance_score' in data:
        update_data['importance_score'] = data['importance_score']
    
    # Update the note
    result = notes_collection.update_one(
        {'_id': note_object_id},
        {'$set': update_data}
    )
    
    return {
        'success': True, 
        'updated': result.modified_count
    }

def delete_note(note_id: str) -> Dict[str, Any]:
    """Delete a note"""
    try:
        note_object_id = ObjectId(note_id)
    except:
        logger.error("Invalid note ID")
        return {'success': False, 'error': 'Invalid note ID'}
    
    # Get note first to handle tag updates
    note = notes_collection.find_one({'_id': note_object_id})
    if not note:
        return {'success': False, 'error': 'Note not found'}
    
    # Remove note from tags
    tags = note.get('tags', [])
    for tag in tags:
        tags_collection.update_one(
            {'name': tag},
            {'$pull': {'note_ids': note_object_id}}
        )
    
    # Delete note
    result = notes_collection.delete_one({'_id': note_object_id})
    
    return {'success': True, 'deleted': result.deleted_count}

def find_backlinks(note_title: str) -> List[Dict[str, Any]]:
    """Find notes that link to a note with the given title"""
    backlinks = list(notes_collection.find({'content': {'$regex': f'\\[\\[{note_title}\\]\\]'}}))
    return [note_to_dict(link) for link in backlinks]

def increment_retrieval_count(note_id: str) -> None:
    """Increment the retrieval count for a note"""
    try:
        notes_collection.update_one(
            {"_id": ObjectId(note_id)},
            {"$inc": {"retrieval_count": 1}, 
             "$set": {"last_accessed": datetime.datetime.now().strftime("%Y%m%d%H%M")}}
        )
    except Exception as e:
        logger.error(f"Error updating retrieval count: {str(e)}")