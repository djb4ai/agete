"""
Knowledge graph routes and controllers
"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
import networkx as nx
from app.database.db import notes_collection
from app.config.config import logger

# Create Blueprint
graph_bp = Blueprint('graph', __name__, url_prefix='/api/graph')

@graph_bp.route('', methods=['GET'])
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