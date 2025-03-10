"""OpenAPI specification for the Knowledge Base API"""

from flask_restx import Api

def configure_api(app):
    """Configure the API with complete OpenAPI documentation"""
    
    # Create API with metadata
    api = Api(
        app, 
        version='1.0.0',
        title='AI-Enhanced Knowledge Base API',
        description='A comprehensive API for an Obsidian-like knowledge management system with AI capabilities.',
        doc='/api/docs',
        default='Knowledge Base',
        default_label='Knowledge Base Operations'
    )
    
    # Create namespaces for API organization
    vaults_ns = api.namespace('vaults', description='Vault operations', path='/api/vaults')
    notes_ns = api.namespace('notes', description='Note operations', path='/api/notes')
    tags_ns = api.namespace('tags', description='Tag operations', path='/api/tags')
    search_ns = api.namespace('search', description='Search operations', path='/api/search')
    graph_ns = api.namespace('graph', description='Knowledge graph operations', path='/api/graph')
    templates_ns = api.namespace('templates', description='Template operations', path='/api/templates')
    daily_ns = api.namespace('daily', description='Daily note operations', path='/api/daily-note')
    tools_ns = api.namespace('tools', description='Tool operations', path='/tools')
    execute_ns = api.namespace('execute', description='Tool execution', path='/execute')
    discover_ns = api.namespace('discover', description='Tool discovery', path='/discover')
    
    # Return all namespaces for use in routes
    return {
        'api': api,
        'vaults_ns': vaults_ns,
        'notes_ns': notes_ns,
        'tags_ns': tags_ns,
        'search_ns': search_ns,
        'graph_ns': graph_ns,
        'templates_ns': templates_ns,
        'daily_ns': daily_ns,
        'tools_ns': tools_ns,
        'execute_ns': execute_ns,
        'discover_ns': discover_ns
    } 