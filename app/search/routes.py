"""
Search functionality
"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from app.database.db import notes_collection
from app.utils.helpers import note_to_dict
from app.config.config import logger
from app.notes.models import increment_retrieval_count
from app.ai.factory import initialize_ai_components

# Get AI components
ai_components = initialize_ai_components()
embedding_retriever = ai_components.get('embedding_retriever')

# Create Blueprint
search_bp = Blueprint('search', __name__, url_prefix='/api/search')

@search_bp.route('', methods=['GET'])
def search():
    """Advanced search functionality"""
    query = request.args.get('q', '')
    vault_id = request.args.get('vault_id')
    
    # Build MongoDB query
    mongo_query = {}
    
    if vault_id:
        try:
            mongo_query['vault_id'] = ObjectId(vault_id)
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    # Add search terms
    if query:
        mongo_query['$or'] = [
            {'title': {'$regex': query, '$options': 'i'}},
            {'content': {'$regex': query, '$options': 'i'}},
            {'tags': {'$regex': query, '$options': 'i'}}
        ]
    
    # Perform search
    notes = list(notes_collection.find(mongo_query))
    return jsonify([note_to_dict(note) for note in notes])

@search_bp.route('/full-text', methods=['GET'])
def full_text_search():
    """Advanced full-text search with ranking"""
    query = request.args.get('q', '')
    vault_id = request.args.get('vault_id')
    limit = int(request.args.get('limit', 10))
    search_type = request.args.get('type', 'text')  # Options: 'text', 'semantic', 'hybrid'
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    # Build MongoDB query
    mongo_query = {}
    
    if vault_id:
        try:
            mongo_query['vault_id'] = ObjectId(vault_id)
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    # Text search results
    text_results = []
    if search_type in ['text', 'hybrid']:
        # Create text search query
        try:
            text_search_results = notes_collection.find(
                {'$text': {'$search': query}} if '$text' in notes_collection.index_information() else 
                {'$or': [
                    {'title': {'$regex': query, '$options': 'i'}},
                    {'content': {'$regex': query, '$options': 'i'}}
                ]}
            )
            
            text_results = [note_to_dict(note) for note in text_search_results]
            
            # Simple ranking based on exact matches in title and content
            for result in text_results:
                score = 0
                if query.lower() in result['title'].lower():
                    score += 5
                if query.lower() in result['content'].lower():
                    score += 1
                result['score'] = score
                result['search_type'] = 'text'
            
            # Sort by score
            text_results.sort(key=lambda x: x['score'], reverse=True)
        except Exception as e:
            logger.error(f"Error in text search: {str(e)}")
    
    # Semantic search results
    semantic_results = []
    if (search_type in ['semantic', 'hybrid'] and 
        embedding_retriever and 
        embedding_retriever.embedding_available):
        
        try:
            # Get semantic search results
            semantic_matches = embedding_retriever.search(query, k=limit)
            
            # Get documents from database
            for doc_id, similarity in semantic_matches:
                try:
                    doc = notes_collection.find_one({"_id": ObjectId(doc_id)})
                    if doc:
                        note_dict = note_to_dict(doc)
                        note_dict['score'] = float(similarity) * 5  # Scale to match text score range
                        note_dict['search_type'] = 'semantic'
                        semantic_results.append(note_dict)
                except Exception as e:
                    logger.error(f"Error retrieving semantic search result: {str(e)}")
        except Exception as e:
            logger.error(f"Error during semantic search: {str(e)}")
    
    # Combine results based on search type
    if search_type == 'text':
        results = text_results[:limit]
    elif search_type == 'semantic':
        results = semantic_results[:limit]
    else:  # hybrid
        # Combine results, ensuring no duplicates
        combined_results = {}
        
        # Add text results
        for result in text_results:
            result_id = result['_id']
            combined_results[result_id] = result
        
        # Add semantic results, boosting score if already in text results
        for result in semantic_results:
            result_id = result['_id']
            if result_id in combined_results:
                # If found in both searches, boost the score
                combined_results[result_id]['score'] += result['score']
                combined_results[result_id]['search_type'] = 'hybrid'
            else:
                combined_results[result_id] = result
        
        # Convert to list and sort
        results = list(combined_results.values())
        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:limit]
    
    # Update retrieval count for each note
    for result in results:
        try:
            increment_retrieval_count(result['_id'])
        except Exception as e:
            logger.error(f"Error updating retrieval count: {str(e)}")
    
    return jsonify(results)