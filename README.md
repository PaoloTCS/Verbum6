# Verbum6 Knowledge Landscape

Interactive knowledge visualization and navigation using semantic tessellation.

## Overview
Verbum6 creates an intelligent interface for knowledge exploration using:
- Voronoi tessellation for spatial organization
- Semantic distances for knowledge relationships
- Adaptive user context for personalized navigation
- Document querying with OpenAI integration

## Features

### Document Navigation
- Interactive Voronoi tessellation interface
- Semantic-based document clustering
- Hierarchical navigation through knowledge domains

### Document Querying
When viewing a document, users can:
- Ask specific questions about document content
- Get page-specific answers with citations
- See relevant quotes from the text

Example response format:
```
Q: "What is an IPO?"
A: Found on page 12: "An Initial Public Offering (IPO) is the process of offering 
shares of a private corporation to the public in a new stock issuance."

Related quote: "The IPO process transforms a private company into a public company, 
enabling broader access to capital markets." (p.13)
```

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
- Flask (backend framework)
- D3.js (visualization)
- OpenAI API (document understanding)
- PyPDF2 (PDF processing with page tracking)