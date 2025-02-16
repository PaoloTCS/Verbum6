"""
app/api/routes.py
Routes for the Verbum6 application.
"""

from flask import Blueprint, jsonify, current_app, render_template, send_file, request, send_from_directory
import os
import fitz  # PyMuPDF for PDF processing
from app.core.document_processor import DocumentProcessor
from app.core.semantic_processor import SemanticProcessor
import logging

# Create blueprint with template folder specified
api_bp = Blueprint('api', __name__, template_folder='../templates', static_folder='../static')
logger = logging.getLogger(__name__)

@api_bp.route('/')
def index():
    """Serve the main visualization page."""
    return render_template('index.html')

@api_bp.route('/api/hierarchy')
def get_root_hierarchy():
    """Get the root hierarchy."""
    try:
        base_path = current_app.config['UPLOAD_FOLDER']
        logger.info(f"Building root hierarchy from: {base_path}")
        
        if not os.path.exists(base_path):
            logger.error(f"Upload folder not found: {base_path}")
            return jsonify({'error': 'Upload folder not found'}), 404
            
        hierarchy = build_hierarchy(base_path)
        if not hierarchy:
            logger.error("Failed to build hierarchy")
            return jsonify({'error': 'Failed to build hierarchy'}), 500
            
        return jsonify({'hierarchy': hierarchy})
    except Exception as e:
        logger.error(f"Error in get_root_hierarchy: {str(e)}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/hierarchy/<path:subpath>')
def get_hierarchy(subpath):
    """Get hierarchy for a specific path."""
    try:
        base_path = current_app.config['UPLOAD_FOLDER']
        full_path = os.path.join(base_path, subpath)
        
        logger.info(f"Requested hierarchy for: {subpath}")
        logger.info(f"Full path: {full_path}")
        
        if not os.path.exists(full_path):
            logger.error(f"Path not found: {full_path}")
            return jsonify({'error': 'Path not found'}), 404

        hierarchy = build_hierarchy(full_path)
        return jsonify({'hierarchy': hierarchy})

    except Exception as e:
        logger.error(f"Error getting hierarchy for {subpath}: {str(e)}")
        return jsonify({'error': str(e)}), 500

def build_hierarchy(path: str) -> dict:
    """Build hierarchy dictionary from directory structure."""
    try:
        logger.info(f"Building hierarchy for: {path}")
        
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            return None

        result = {
            'name': os.path.basename(path) or 'root',
            'type': 'directory',
            'children': []
        }

        items = sorted(os.listdir(path))
        logger.debug(f"Found items in {path}: {items}")

        for item in items:
            if item.startswith('.'):
                continue

            item_path = os.path.join(path, item)
            try:
                if os.path.isdir(item_path):
                    child = build_hierarchy(item_path)
                    if child:
                        result['children'].append(child)
                else:
                    if item.lower().endswith(('.pdf', '.txt')):
                        rel_path = os.path.relpath(item_path, current_app.config['UPLOAD_FOLDER'])
                        logger.debug(f"Adding document: {rel_path}")
                        result['children'].append({
                            'name': item,
                            'type': 'document',
                            'path': rel_path
                        })
            except Exception as e:
                logger.error(f"Error processing {item_path}: {str(e)}")
                continue

        return result

    except Exception as e:
        logger.error(f"Error building hierarchy for {path}: {str(e)}")
        return None

@api_bp.route('/api/documents')
def get_documents():
    """Get document relationships and positions for visualization."""
    try:
        processor = DocumentProcessor(current_app.config['UPLOAD_FOLDER'])
        relationships = processor.get_document_relationships()
        return jsonify(relationships)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/document/<path:filepath>')
def get_document(filepath):
    """Serve document content."""
    try:
        full_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filepath)
        
        if not os.path.exists(full_path):
            logger.error(f"Document not found: {full_path}")
            return jsonify({'error': 'Document not found'}), 404
            
        if filepath.lower().endswith('.pdf'):
            logger.info(f"Serving PDF file: {filepath}")
            return send_from_directory(
                current_app.config['UPLOAD_FOLDER'],
                filepath,
                mimetype='application/pdf',
                as_attachment=False
            )
        else:
            # For text-based documents
            logger.info(f"Serving text file: {filepath}")
            with open(full_path, 'r') as f:
                content = f.read()
            return jsonify({
                'content': content,
                'filename': os.path.basename(filepath)
            })
    except Exception as e:
        logger.error(f"Error serving document {filepath}: {str(e)}")
        return jsonify({'error': str(e)}), 500

from flask import jsonify, request
import asyncio

@api_bp.route('/api/document/query', methods=['POST'])
def query_document():
    """Process a query against a document."""
    try:
        data = request.get_json()
        if not data or 'path' not in data or 'query' not in data:
            logger.error("Missing required fields in query request")
            return jsonify({'error': 'Missing path or query'}), 400

        logger.info(f"Processing query for document: {data['path']}")
        doc_processor = DocumentProcessor(current_app.config['UPLOAD_FOLDER'])
        
        result = doc_processor.process_document_query(
            doc_path=data['path'],
            query=data['query']
        )
        
        if 'error' in result:
            logger.error(f"Query processing error: {result['error']}")
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in query_document: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Failed to process query',
            'details': str(e)
        }), 500

@api_bp.route('/api/semantic-distances/level-0')
def get_level_0_distances():
    """Get semantic distances between top-level folders."""
    try:
        processor = SemanticProcessor(current_app.config['UPLOAD_FOLDER'])
        distances = processor.compute_level_0_distances()
        
        # Convert distances to a format suitable for visualization
        distance_data = {
            'nodes': processor._get_top_level_folders(),
            'distances': {f"{k[0]}|{k[1]}": v for k, v in distances.items()}
        }
        return jsonify(distance_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500