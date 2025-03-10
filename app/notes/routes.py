"""
Note routes and controllers
"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from app.notes.models import (
    find_note_by_id, find_notes_by_vault, find_notes_by_tag, 
    find_notes_by_search, create_note, update_note, delete_note,
    find_backlinks, increment_retrieval_count
)
from app.utils.helpers import note_to_dict
from app.config.config import logger
from app.ai.factory import initialize_ai_components

# Initialize AI components
ai_components = initialize_ai_components()
llm_controller = ai_components.get('llm_controller')
embedding_retriever = ai_components.get('embedding_retriever')
memory_evolution = ai_components.get('memory_evolution')
AI_FEATURES_ENABLED = ai_components.get('ai_features_enabled', False)

# Create Blueprint
notes_bp = Blueprint('notes', __name__, url_prefix='/api/notes')

@notes_bp.route('', methods=['GET'])
def get_notes():
    """Get all notes or filter by vault_id, tag, or search term"""
    vault_id = request.args.get('vault_id')
    tag = request.args.get('tag')
    search = request.args.get('search')
    
    if tag:
        notes = find_notes_by_tag(tag)
    elif search:
        notes = find_notes_by_search(search, vault_id)
    else:
        notes = find_notes_by_vault(vault_id)
    
    return jsonify(notes)

@notes_bp.route('/<note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = find_note_by_id(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    # Get backlinks (notes that link to this note)
    title = note['title']
    backlinks = find_backlinks(title)
    backlinks_data = [{'_id': bl['_id'], 'title': bl['title']} for bl in backlinks]
    
    # Convert note to dict and add backlinks
    note_dict = note_to_dict(note)
    note_dict['backlinks'] = backlinks_data
    
    return jsonify(note_dict)

@notes_bp.route('', methods=['POST'])
def create_new_note():
    """Create a new note"""
    data = request.json
    if not data or 'title' not in data or 'content' not in data:
        return jsonify({'error': 'Title and content are required'}), 400
    
    # Use AI to enhance note metadata if available
    keywords = []
    context = "General"
    importance_score = 1.0
    auto_tags = []
    
    if AI_FEATURES_ENABLED and llm_controller:
        try:
            # Analyze content with LLM
            analysis = llm_controller.analyze_content(data['content'])
            keywords = analysis.get('keywords', [])
            context = analysis.get('context', 'General')
            auto_tags = analysis.get('tags', [])
            
            # Merge user-provided tags with AI-generated tags
            if 'tags' not in data:
                data['tags'] = []
                
            for tag in auto_tags:
                if tag not in data['tags']:
                    data['tags'].append(tag)
                    
            # Find related notes to determine connections and importance
            if embedding_retriever and embedding_retriever.embedding_available:
                related_notes = []
                search_results = embedding_retriever.search(data['content'], k=5)
                
                if search_results:
                    # Get related notes from database
                    related_docs = []
                    for doc_id, _ in search_results:
                        try:
                            note_obj = find_note_by_id(doc_id)
                            if note_obj:
                                related_docs.append(note_obj)
                        except:
                            continue
                    
                    # Find connections
                    connection_analysis = llm_controller.find_connections(data['content'], related_docs)
                    importance_score = connection_analysis.get('importance_score', 1.0)
        except Exception as e:
            logger.error(f"Error using AI features: {str(e)}")
    
    # Add enhanced metadata to note data
    data['keywords'] = keywords
    data['context'] = context
    data['importance_score'] = importance_score
    
    # Create the note
    note = create_note(data)
    
    # Update embeddings if available
    if embedding_retriever and embedding_retriever.embedding_available:
        try:
            # Prepare document for embedding with metadata included
            metadata_text = f"{note['title']} {note['context']} {' '.join(note['keywords'])} {' '.join(note['tags'])}"
            document_for_embedding = f"{note['content']} {metadata_text}"
            
            embedding_retriever.add_documents([document_for_embedding], [note['_id']])
        except Exception as e:
            logger.error(f"Error updating embeddings: {str(e)}")
    
    # Process with memory evolution system
    if AI_FEATURES_ENABLED and memory_evolution:
        try:
            memory_evolution.process_new_note(note['_id'])
        except Exception as e:
            logger.error(f"Error processing note with memory evolution: {str(e)}")
    
    return jsonify(note), 201

@notes_bp.route('/<note_id>', methods=['PUT'])
def update_existing_note(note_id):
    """Update a note"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    result = update_note(note_id, data)
    
    if 'error' in result:
        return jsonify(result), 400 if 'Invalid' in result['error'] else 404
    
    return jsonify(result)

@notes_bp.route('/<note_id>', methods=['DELETE'])
def delete_existing_note(note_id):
    """Delete a note"""
    result = delete_note(note_id)
    
    if 'error' in result:
        return jsonify(result), 400 if 'Invalid' in result['error'] else 404
    
    return jsonify(result)

@notes_bp.route('/<note_id>/backlinks', methods=['GET'])
def get_note_backlinks(note_id):
    """Get all notes that link to a specific note"""
    note = find_note_by_id(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    # Find notes that link to this note
    title = note['title']
    backlinks = find_backlinks(title)
    
    return jsonify(backlinks)