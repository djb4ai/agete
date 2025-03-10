"""
Common utility functions
"""
import re
from bson.objectid import ObjectId
from typing import Dict, Any, Optional, List

def extract_links(content: str) -> List[str]:
    """Extract links from content using regex for [[link]] format"""
    return re.findall(r'\[\[(.*?)\]\]', content)

def note_to_dict(note: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Convert MongoDB note to dictionary and handle ObjectId"""
    if note is None:
        return None
    result = dict(note)
    result['_id'] = str(note['_id'])
    if 'vault_id' in note and note['vault_id'] is not None:
        result['vault_id'] = str(note['vault_id'])
    return result