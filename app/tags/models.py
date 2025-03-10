"""
Tag model and operations
"""
from typing import Dict, Any, List
from app.database.db import tags_collection
from app.config.config import logger

def find_all_tags() -> List[Dict[str, Any]]:
    """Get all tags and their counts"""
    tags = list(tags_collection.find())
    
    result = []
    for tag in tags:
        tag['_id'] = str(tag['_id'])
        tag['count'] = len(tag.get('note_ids', []))
        tag['note_ids'] = [str(note_id) for note_id in tag.get('note_ids', [])]
        result.append(tag)
    
    return result

def find_tag_by_name(tag_name: str) -> Dict[str, Any]:
    """Find a tag by name"""
    tag = tags_collection.find_one({'name': tag_name})
    if tag:
        tag['_id'] = str(tag['_id'])
        tag['count'] = len(tag.get('note_ids', []))
        tag['note_ids'] = [str(note_id) for note_id in tag.get('note_ids', [])]
        return tag
    return {'name': tag_name, 'count': 0, 'note_ids': []}