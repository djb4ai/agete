"""
Vault model and operations
"""
import datetime
from bson.objectid import ObjectId
from typing import Dict, Any, List, Optional
from app.database.db import vaults_collection, notes_collection
from app.config.config import logger

def find_all_vaults() -> List[Dict[str, Any]]:
    """Get all vaults"""
    vaults = list(vaults_collection.find())
    return [{**vault, '_id': str(vault['_id'])} for vault in vaults]

def find_vault_by_id(vault_id: str) -> Optional[Dict[str, Any]]:
    """Find a vault by ID"""
    try:
        vault_object_id = ObjectId(vault_id)
        vault = vaults_collection.find_one({'_id': vault_object_id})
        if vault:
            vault['_id'] = str(vault['_id'])
            return vault
        return None
    except Exception as e:
        logger.error(f"Error finding vault by ID: {str(e)}")
        return None

def create_vault(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new vault"""
    vault = {
        'name': data['name'],
        'description': data.get('description', ''),
        'created_at': datetime.datetime.now(),
        'updated_at': datetime.datetime.now()
    }
    
    # Store in MongoDB
    result = vaults_collection.insert_one(vault)
    vault['_id'] = str(result.inserted_id)
    
    logger.info(f"Created vault: {vault['name']} with ID: {vault['_id']}")
    return vault

def update_vault(vault_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a vault"""
    try:
        vault_object_id = ObjectId(vault_id)
    except:
        logger.error("Invalid vault ID")
        return {'success': False, 'error': 'Invalid vault ID'}
    
    update_data = {}
    
    if 'name' in data:
        update_data['name'] = data['name']
        
    if 'description' in data:
        update_data['description'] = data['description']
    
    update_data['updated_at'] = datetime.datetime.now()
    
    if not update_data or (len(update_data) == 1 and 'updated_at' in update_data):
        return {'success': False, 'error': 'No valid fields to update'}
    
    result = vaults_collection.update_one(
        {'_id': vault_object_id},
        {'$set': update_data}
    )
    
    if result.matched_count == 0:
        return {'success': False, 'error': 'Vault not found'}
    
    return {'success': True, 'updated': result.modified_count}

def delete_vault(vault_id: str) -> Dict[str, Any]:
    """Delete a vault and all its notes"""
    try:
        vault_object_id = ObjectId(vault_id)
    except:
        logger.error("Invalid vault ID")
        return {'success': False, 'error': 'Invalid vault ID'}
    
    # Delete vault
    result = vaults_collection.delete_one({'_id': vault_object_id})
    if result.deleted_count == 0:
        return {'success': False, 'error': 'Vault not found'}
    
    # Delete all notes in the vault
    notes_collection.delete_many({'vault_id': vault_object_id})
    
    return {'success': True}