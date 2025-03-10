"""
Daily note routes and controllers
"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from app.database.db import notes_collection, tags_collection
from app.utils.helpers import note_to_dict
from app.config.config import logger
import datetime

# Create Blueprint
daily_bp = Blueprint('daily', __name__, url_prefix='/api/daily-note')

@daily_bp.route('', methods=['GET', 'POST'])
def daily_note():
    """Get or create a daily note"""
    date_str = request.args.get('date')
    vault_id = request.args.get('vault_id')
    
    # Parse date or use today
    try:
        if date_str:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = datetime.datetime.now().date()
    except:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    # Format date for title and query
    date_formatted = date.strftime('%Y-%m-%d')
    title = f"Daily Note: {date_formatted}"
    
    # Build query
    query = {'title': title}
    if vault_id:
        try:
            query['vault_id'] = ObjectId(vault_id)
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    # Check if note exists
    note = notes_collection.find_one(query)
    
    if request.method == 'GET':
        if note:
            return jsonify(note_to_dict(note))
        else:
            return jsonify({'exists': False, 'title': title}), 404
    
    # POST method - create if doesn't exist
    if note:
        return jsonify({'error': 'Daily note already exists', 'note': note_to_dict(note)}), 409
    
    # Create new daily note
    new_note = {
        'title': title,
        'content': f"# {title}\n\n",
        'tags': ['daily-note'],
        'created_at': datetime.datetime.now(),
        'updated_at': datetime.datetime.now(),
        'links': [],
        'retrieval_count': 0,
        'last_accessed': datetime.datetime.now().strftime("%Y%m%d%H%M")
    }
    
    if vault_id:
        try:
            new_note['vault_id'] = ObjectId(vault_id)
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    result = notes_collection.insert_one(new_note)
    new_note['_id'] = str(result.inserted_id)
    
    # Update tags
    tags_collection.update_one(
        {'name': 'daily-note'},
        {'$set': {'name': 'daily-note'}, '$addToSet': {'note_ids': result.inserted_id}},
        upsert=True
    )
    
    return jsonify(new_note), 201