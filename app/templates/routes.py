"""
Template routes and controllers
"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from app.database.db import notes_collection, tags_collection
from app.utils.helpers import note_to_dict, extract_links
from app.config.config import logger
import datetime

# Create Blueprint
templates_bp = Blueprint('templates', __name__, url_prefix='/api/templates')

@templates_bp.route('', methods=['GET'])
def get_templates():
    """Get all template notes"""
    query = {'tags': 'template'}
    
    vault_id = request.args.get('vault_id')
    if vault_id:
        try:
            query['vault_id'] = ObjectId(vault_id)
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    templates = list(notes_collection.find(query))
    return jsonify([note_to_dict(template) for template in templates])

@templates_bp.route('/<template_id>/apply', methods=['POST'])
def apply_template(template_id):
    """Apply a template to create a new note"""
    data = request.json
    if not data or 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    
    try:
        template_object_id = ObjectId(template_id)
    except:
        return jsonify({'error': 'Invalid template ID'}), 400
    
    # Get template
    template = notes_collection.find_one({'_id': template_object_id, 'tags': 'template'})
    if not template:
        return jsonify({'error': 'Template not found'}), 404
    
    # Prepare new note from template
    new_note = {
        'title': data['title'],
        'content': template['content'],
        'tags': data.get('tags', []),
        'vault_id': ObjectId(data['vault_id']) if 'vault_id' in data and data['vault_id'] else None,
        'created_at': datetime.datetime.now(),
        'updated_at': datetime.datetime.now(),
        'retrieval_count': 0,
        'last_accessed': datetime.datetime.now().strftime("%Y%m%d%H%M")
    }
    
    # Extract links from content
    new_note['links'] = extract_links(new_note['content'])
    
    # Create note
    result = notes_collection.insert_one(new_note)
    new_note['_id'] = str(result.inserted_id)
    
    # Update tags
    for tag in new_note['tags']:
        tags_collection.update_one(
            {'name': tag},
            {'$set': {'name': tag}, '$addToSet': {'note_ids': result.inserted_id}},
            upsert=True
        )
    
    return jsonify(note_to_dict(new_note)), 201