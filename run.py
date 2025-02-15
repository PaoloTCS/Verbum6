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
"""

import os
from app import create_app

# Get environment configuration
env = os.getenv('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    # Development server configuration
    if env == 'development':
        app.run(debug=True, port=5001)
    else:
        app.run()