"""
run.py

Entry point for the Verbum6 Knowledge Landscape application.
This script initializes and runs the Flask application with the correct configuration
based on the environment (development, testing, or production).

Usage:
    python run.py

Environment Variables:
    FLASK_ENV: The environment to run in (development, testing, production)
    OPENAI_API_KEY: API key for OpenAI integration (optional for basic functionality)
    PORT: Port number to run the application on (default: 5001)
"""

import os
import sys
import logging
from app import create_app

# Configure basic logging with timestamp
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_port():
    """Get and validate port number from environment."""
    try:
        port = int(os.getenv('PORT', 5001))
        if not (1024 <= port <= 65535):
            logger.warning(f"Port {port} out of range, using default 5001")
            return 5001
        return port
    except ValueError:
        logger.error("Invalid PORT environment variable")
        return 5001

def get_environment():
    """Get and validate environment configuration."""
    env = os.getenv('FLASK_ENV', 'development')
    valid_environments = ['development', 'testing', 'production']
    if env not in valid_environments:
        logger.warning(f"Invalid environment '{env}' specified, defaulting to development")
        return 'development'
    return env

def configure_app(app, env, port):
    """Configure and run the Flask application."""
    # Log startup information
    logger.info(f"Starting Verbum6 in {env} mode on port {port}")
    
    # Set common configuration
    app.config['ENV'] = env
    app.config['PORT'] = port
    
    # Configure server based on environment
    debug_mode = env == 'development'
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=debug_mode,
            use_reloader=debug_mode
        )
    except OSError as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        env = get_environment()
        port = get_port()
        
        # Create and configure the application instance
        app = create_app(env)
        configure_app(app, env, port)
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)