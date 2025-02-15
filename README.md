# Verbum6 Knowledge Landscape

Interactive knowledge visualization and navigation using semantic tessellation.

## Overview
Verbum6 creates an intelligent interface for knowledge exploration using:
- Voronoi tessellation for spatial organization
- Semantic distances for knowledge relationships
- Adaptive user context for personalized navigation
- Document querying with OpenAI integration

## Structure
```
VerbumTechnologies/Verbum6/
├── app/
│   ├── __init__.py          # Flask application factory
│   ├── api/                 # API routes
│   ├── core/                # Core functionality
│   │   ├── document_processor.py
│   │   ├── semantic_processor.py
│   │   └── user_context.py
│   ├── static/              # Static assets
│   │   ├── css/
│   │   └── js/
│   └── templates/           # HTML templates
├── inputDocs/              # Document storage
├── requirements.txt        # Python dependencies
└── run.py                 # Application entry point
```

## Setup
1. Create virtual environment
2. Install dependencies
3. Configure OpenAI API key
4. Run the application

## Development
Built with:
- Flask
- D3.js
- OpenAI API
- PyPDF2