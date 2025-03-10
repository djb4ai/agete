from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import re
import datetime
import networkx as nx
import json
import os
import uuid
from typing import List, Dict, Optional, Literal, Any
import logging
import numpy as np

# Optional imports for AI-powered features
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    EMBEDDING_AVAILABLE = True
except ImportError:
    EMBEDDING_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['knowledge_base']
notes_collection = db['notes']
vaults_collection = db['vaults']
tags_collection = db['tags']

# Import custom modules for AI features
try:
    from llm_integration import LLMController
    from semantic_search import EmbeddingRetriever
    from memory_evolution import MemoryEvolutionSystem
    
    # Initialize LLM controller and embedding retriever
    llm_controller = LLMController(
        backend="openai" if os.getenv('OPENAI_API_KEY') and OPENAI_AVAILABLE else "mock",
        model="gpt-4o-mini"
    )
    
    embedding_retriever = EmbeddingRetriever(model_name='all-MiniLM-L6-v2') if EMBEDDING_AVAILABLE else None
    
    # Load existing embeddings if available
    if embedding_retriever and embedding_retriever.embedding_available:
        embedding_retriever.load_embeddings()
    
    # Initialize memory evolution system
    memory_evolution = MemoryEvolutionSystem(
        db=db,
        llm_controller=llm_controller,
        embedding_retriever=embedding_retriever,
        evolution_threshold=20
    )
        
    AI_FEATURES_ENABLED = True
except ImportError:
    logger.warning("AI features could not be initialized. Running in basic mode.")
    AI_FEATURES_ENABLED = False
    llm_controller = None
    embedding_retriever = None
    memory_evolution = None

# Ensure indexes for performance
notes_collection.create_index('title')
notes_collection.create_index('content')
notes_collection.create_index('vault_id')
notes_collection.create_index('tags')

# Helper functions
def extract_links(content):
    """Extract links from content using regex for [[link]] format"""
    return re.findall(r'\[\[(.*?)\]\]', content)

def note_to_dict(note):
    """Convert MongoDB note to dictionary and handle ObjectId"""
    if note is None:
        return None
    note['_id'] = str(note['_id'])
    if 'vault_id' in note:
        note['vault_id'] = str(note['vault_id'])
    return note

# Vault management routes
@app.route('/api/vaults', methods=['GET'])
def get_vaults():
    """Get all vaults"""
    vaults = list(vaults_collection.find())
    return jsonify([{**vault, '_id': str(vault['_id'])} for vault in vaults])

@app.route('/api/vaults', methods=['POST'])
def create_vault():
    """Create a new vault"""
    data = request.json
    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400
    
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
    return jsonify(vault), 201

@app.route('/api/vaults/<vault_id>', methods=['PUT'])
def update_vault(vault_id):
    """Update a vault"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        vault_object_id = ObjectId(vault_id)
    except:
        return jsonify({'error': 'Invalid vault ID'}), 400
    
    update_data = {
        'name': data.get('name'),
        'description': data.get('description'),
        'updated_at': datetime.datetime.now()
    }
    
    # Remove None values
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    if not update_data:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    result = vaults_collection.update_one(
        {'_id': vault_object_id},
        {'$set': update_data}
    )
    
    if result.matched_count == 0:
        return jsonify({'error': 'Vault not found'}), 404
    
    return jsonify({'success': True, 'updated': result.modified_count})

@app.route('/api/vaults/<vault_id>', methods=['DELETE'])
def delete_vault(vault_id):
    """Delete a vault and all its notes"""
    try:
        vault_object_id = ObjectId(vault_id)
    except:
        return jsonify({'error': 'Invalid vault ID'}), 400
    
    # Delete vault
    result = vaults_collection.delete_one({'_id': vault_object_id})
    if result.deleted_count == 0:
        return jsonify({'error': 'Vault not found'}), 404
    
    # Delete all notes in the vault
    notes_collection.delete_many({'vault_id': vault_object_id})
    
    return jsonify({'success': True})

# Note management routes
@app.route('/api/notes', methods=['GET'])
def get_notes():
    """Get all notes or filter by vault_id, tag, or search term"""
    vault_id = request.args.get('vault_id')
    tag = request.args.get('tag')
    search = request.args.get('search')
    
    query = {}
    
    if vault_id:
        try:
            query['vault_id'] = ObjectId(vault_id)
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    if tag:
        query['tags'] = tag
    
    if search:
        query['$or'] = [
            {'title': {'$regex': search, '$options': 'i'}},
            {'content': {'$regex': search, '$options': 'i'}}
        ]
    
    notes = list(notes_collection.find(query))
    return jsonify([note_to_dict(note) for note in notes])

@app.route('/api/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    try:
        note_object_id = ObjectId(note_id)
    except:
        return jsonify({'error': 'Invalid note ID'}), 400
    
    note = notes_collection.find_one({'_id': note_object_id})
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    # Get backlinks (notes that link to this note)
    title = note['title']
    backlinks = list(notes_collection.find({'content': {'$regex': f'\\[\\[{title}\\]\\]'}}))
    backlinks_data = [{'_id': str(bl['_id']), 'title': bl['title']} for bl in backlinks]
    
    # Convert note to dict and add backlinks
    note_dict = note_to_dict(note)
    note_dict['backlinks'] = backlinks_data
    
    return jsonify(note_dict)

@app.route('/api/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    data = request.json
    if not data or 'title' not in data or 'content' not in data:
        return jsonify({'error': 'Title and content are required'}), 400
    
    # Extract vault_id and convert to ObjectId if provided
    vault_id = None
    if 'vault_id' in data and data['vault_id']:
        try:
            vault_id = ObjectId(data['vault_id'])
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    # Extract links and tags from content
    links = extract_links(data['content'])
    tags = data.get('tags', [])
    
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
            for tag in auto_tags:
                if tag not in tags:
                    tags.append(tag)
                    
            # Find related notes to determine connections and importance
            if embedding_retriever and embedding_retriever.embedding_available:
                related_notes = []
                search_results = embedding_retriever.search(data['content'], k=5)
                
                if search_results:
                    # Get related notes from database
                    related_docs = []
                    for doc_id, _ in search_results:
                        try:
                            note_obj = notes_collection.find_one({"_id": ObjectId(doc_id)})
                            if note_obj:
                                related_docs.append(note_obj)
                        except:
                            continue
                    
                    # Find connections
                    connection_analysis = llm_controller.find_connections(data['content'], related_docs)
                    importance_score = connection_analysis.get('importance_score', 1.0)
                    
                    # Add suggested connections to links
                    suggested_connections = connection_analysis.get('suggested_connections', [])
                    for idx in suggested_connections:
                        if 0 <= idx < len(related_docs):
                            related_title = related_docs[idx].get('title', '')
                            if related_title and related_title not in links:
                                links.append(related_title)
        except Exception as e:
            logger.error(f"Error using AI features: {str(e)}")
    
    # Create note with enhanced metadata
    note = {
        'title': data['title'],
        'content': data['content'],
        'vault_id': vault_id,
        'tags': tags,
        'links': links,
        'keywords': keywords,
        'context': context,
        'importance_score': importance_score,
        'retrieval_count': 0,
        'created_at': datetime.datetime.now(),
        'updated_at': datetime.datetime.now(),
        'last_accessed': datetime.datetime.now().strftime("%Y%m%d%H%M")
    }
    
    result = notes_collection.insert_one(note)
    note_id = result.inserted_id
    note['_id'] = str(note_id)
    note['vault_id'] = str(vault_id) if vault_id else None
    
    # Update tags collection
    for tag in tags:
        tags_collection.update_one(
            {'name': tag},
            {'$set': {'name': tag}, '$addToSet': {'note_ids': note_id}},
            upsert=True
        )
    
    # Update embeddings if available
    if embedding_retriever and embedding_retriever.embedding_available:
        try:
            # Prepare document for embedding with metadata included
            metadata_text = f"{note['title']} {note['context']} {' '.join(note['keywords'])} {' '.join(note['tags'])}"
            document_for_embedding = f"{note['content']} {metadata_text}"
            
            embedding_retriever.add_documents([document_for_embedding], [str(note_id)])
        except Exception as e:
            logger.error(f"Error updating embeddings: {str(e)}")
    
    logger.info(f"Created note: {note['title']} with ID: {note['_id']}")
    
    # Process with memory evolution system
    if AI_FEATURES_ENABLED and memory_evolution:
        try:
            memory_evolution.process_new_note(note['_id'])
        except Exception as e:
            logger.error(f"Error processing note with memory evolution: {str(e)}")
    
    return jsonify(note), 201

@app.route('/api/notes/<note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a note"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        note_object_id = ObjectId(note_id)
    except:
        return jsonify({'error': 'Invalid note ID'}), 400
    
    # Get existing note to handle tags
    existing_note = notes_collection.find_one({'_id': note_object_id})
    if not existing_note:
        return jsonify({'error': 'Note not found'}), 404
    
    # Prepare update data
    update_data = {
        'title': data.get('title'),
        'content': data.get('content'),
        'updated_at': datetime.datetime.now()
    }
    
    # Handle vault_id
    if 'vault_id' in data:
        if data['vault_id']:
            try:
                update_data['vault_id'] = ObjectId(data['vault_id'])
            except:
                return jsonify({'error': 'Invalid vault ID'}), 400
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
    
    # Update links if content changed
    if 'content' in data:
        update_data['links'] = extract_links(data['content'])
    
    # Remove None values
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    if not update_data:
        return jsonify({'error': 'No valid fields to update'}), 400
    
    result = notes_collection.update_one(
        {'_id': note_object_id},
        {'$set': update_data}
    )
    
    return jsonify({'success': True, 'updated': result.modified_count})

@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a note"""
    try:
        note_object_id = ObjectId(note_id)
    except:
        return jsonify({'error': 'Invalid note ID'}), 400
    
    # Get note first to handle tag updates
    note = notes_collection.find_one({'_id': note_object_id})
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    # Remove note from tags
    tags = note.get('tags', [])
    for tag in tags:
        tags_collection.update_one(
            {'name': tag},
            {'$pull': {'note_ids': note_object_id}}
        )
    
    # Delete note
    result = notes_collection.delete_one({'_id': note_object_id})
    
    return jsonify({'success': True})

# Tag management routes
@app.route('/api/tags', methods=['GET'])
def get_tags():
    """Get all tags and their counts"""
    tags = list(tags_collection.find())
    
    result = []
    for tag in tags:
        tag['_id'] = str(tag['_id'])
        tag['count'] = len(tag.get('note_ids', []))
        tag['note_ids'] = [str(note_id) for note_id in tag.get('note_ids', [])]
        result.append(tag)
    
    return jsonify(result)

# Graph view and knowledge graph
@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Generate a knowledge graph representation for visualization"""
    vault_id = request.args.get('vault_id')
    
    # Build query
    query = {}
    if vault_id:
        try:
            query['vault_id'] = ObjectId(vault_id)
        except:
            return jsonify({'error': 'Invalid vault ID'}), 400
    
    # Get all notes
    notes = list(notes_collection.find(query))
    
    # Build graph
    G = nx.DiGraph()
    
    # Add nodes (notes)
    for note in notes:
        G.add_node(str(note['_id']), title=note['title'], type='note')
    
    # Add edges (links between notes)
    for note in notes:
        source_id = str(note['_id'])
        
        # Process explicit links [[link]]
        for link_title in note.get('links', []):
            # Find target note by title
            target_note = notes_collection.find_one({'title': link_title})
            if target_note:
                target_id = str(target_note['_id'])
                G.add_edge(source_id, target_id, type='link')
    
    # Convert to JSON-serializable format
    graph_data = {
        'nodes': [{'id': node, **G.nodes[node]} for node in G.nodes],
        'edges': [{'source': edge[0], 'target': edge[1], **G.edges[edge]} for edge in G.edges]
    }
    
    return jsonify(graph_data)

# Search functionality
@app.route('/api/search', methods=['GET'])
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

# Daily notes
@app.route('/api/daily-note', methods=['GET', 'POST'])
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
        'links': []
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

# Templates functionality
@app.route('/api/templates', methods=['GET'])
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

@app.route('/api/templates/<template_id>/apply', methods=['POST'])
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
        'updated_at': datetime.datetime.now()
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

# Full-text search
@app.route('/api/full-text-search', methods=['GET'])
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
        text_search_results = notes_collection.find(
            {'$text': {'$search': query}} if 'text_index_created' in globals() else 
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
            notes_collection.update_one(
                {"_id": ObjectId(result['_id'])},
                {"$inc": {"retrieval_count": 1}, 
                 "$set": {"last_accessed": datetime.datetime.now().strftime("%Y%m%d%H%M")}}
            )
        except Exception as e:
            logger.error(f"Error updating retrieval count: {str(e)}")
    
    return jsonify(results)

# Backlinks API
@app.route('/api/notes/<note_id>/backlinks', methods=['GET'])
def get_backlinks(note_id):
    """Get all notes that link to a specific note"""
    try:
        note_object_id = ObjectId(note_id)
    except:
        return jsonify({'error': 'Invalid note ID'}), 400
    
    note = notes_collection.find_one({'_id': note_object_id})
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    
    # Find notes that link to this note
    title = note['title']
    backlinks = list(notes_collection.find({'content': {'$regex': f'\\[\\[{title}\\]\\]'}}))
    
    return jsonify([note_to_dict(link) for link in backlinks])

# Create text index for better search
try:
    notes_collection.create_index([
        ('title', 'text'),
        ('content', 'text'),
        ('tags', 'text')
    ])
    globals()['text_index_created'] = True
except Exception as e:
    print(f"Warning: Could not create text index: {e}")

if __name__ == '__main__':
    app.run(debug=True)