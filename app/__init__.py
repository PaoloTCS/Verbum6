from flask import Flask
from flask_cors import CORS
from app.api.routes import api_bp
from dotenv import load_dotenv
import os

load_dotenv()

def create_app(env='development'):
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    CORS(app)
    
    # Point to InputDocs at root level
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-change-in-production'),
        UPLOAD_FOLDER=os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'InputDocs'
        ),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024,
        TEMPLATES_AUTO_RELOAD=True if env == 'development' else False
    )
    
    # Register blueprints
    app.register_blueprint(api_bp)
    
    return app