"""
Core application module
"""
from flask import Flask, render_template
from flask_cors import CORS
from app.database.db import ensure_indexes
from app.config.config import DEBUG

def create_app():
    """Initialize the Flask application"""
    # Create Flask app
    app = Flask(__name__, template_folder='../templates')
    CORS(app)
    
    # Ensure MongoDB indexes
    text_index_created = ensure_indexes()
    
    # Register blueprints
    from app.notes.routes import notes_bp
    from app.vaults.routes import vaults_bp
    from app.tags.routes import tags_bp
    from app.search.routes import search_bp
    from app.graph.routes import graph_bp
    from app.templates.routes import templates_bp
    from app.daily.routes import daily_bp
    
    app.register_blueprint(notes_bp)
    app.register_blueprint(vaults_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(graph_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(daily_bp)
    
    # Main route - home page
    @app.route('/')
    def index():
        return render_template('index.html')
    
    return app