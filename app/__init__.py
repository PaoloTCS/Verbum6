"""
app/__init__.py
Application factory for Verbum6.
"""

import os
from flask import Flask
from flask_cors import CORS
from app.api.routes import api_bp
from dotenv import load_dotenv

load_dotenv()

def create_app(env):
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    CORS(app)
    
    # Configuration
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-change-in-production'),
        UPLOAD_FOLDER=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'inputDocs'),  # Note lowercase 'inputDocs'
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,  # 16MB max file size
        TEMPLATES_AUTO_RELOAD=True if env == 'development' else False
    )
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/')
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    return app