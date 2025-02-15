"""
app/core/document_processor.py
Core document processing functionality for Verbum6.

This module handles:
1. Directory traversal and hierarchy building
2. PDF text extraction and processing
3. Document relationship analysis
4. Semantic distance calculations

The hierarchy is built recursively, with each level (folders and documents)
being processed to extract relevant information for visualization.
"""

import os
import logging
from typing import Dict, List, Optional, Any
import fitz  # PyMuPDF
from dataclasses import dataclass
from pathlib import Path
import openai
from PyPDF2 import PdfReader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DocumentNode:
    """Represents a document (PDF) in the hierarchy."""
    name: str
    path: str
    content_preview: str = ""
    semantic_vector: Optional[List[float]] = None

@dataclass
class FolderNode:
    """Represents a folder in the hierarchy."""
    name: str
    path: str
    children: List[Any] = None
    semantic_center: Optional[List[float]] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

class DocumentProcessor:
    """Handles document processing and hierarchy building."""
    
    def __init__(self, root_path: str):
        """
        Initialize the document processor.
        
        Args:
            root_path (str): Path to the root documents directory
        """
        self.root_path = Path(root_path)
        self.base_path = root_path
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            self.client = openai.OpenAI(api_key=self.openai_api_key)
        
    def extract_text_preview(self, pdf_path: str, max_chars: int = 1000) -> str:
        """
        Extract a text preview from a PDF file.
        
        Args:
            pdf_path (str): Path to the PDF file
            max_chars (int): Maximum number of characters to extract
            
        Returns:
            str: Extracted text preview
        """
        try:
            with fitz.open(pdf_path) as doc:
                text = ""
                for page in doc:
                    text += page.get_text()
                    if len(text) > max_chars:
                        break
                return text[:max_chars]
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def build_hierarchy(self) -> FolderNode:
        """
        Build the complete document hierarchy.
        
        Returns:
            FolderNode: Root node of the document hierarchy
        """
        return self._process_directory(self.root_path)
    
    def _process_directory(self, path: Path) -> FolderNode:
        """
        Recursively process a directory to build the hierarchy.
        
        Args:
            path (Path): Directory path to process
            
        Returns:
            FolderNode: Node representing the processed directory
        """
        try:
            folder = FolderNode(
                name=path.name,
                path=str(path.relative_to(self.root_path.parent)),
                children=[]
            )
            
            for item in path.iterdir():
                if item.is_dir():
                    child_node = self._process_directory(item)
                    folder.children.append(child_node)
                elif item.suffix.lower() == '.pdf':
                    doc_node = DocumentNode(
                        name=item.name,
                        path=str(item.relative_to(self.root_path.parent)),
                        content_preview=self.extract_text_preview(str(item))
                    )
                    folder.children.append(doc_node)
            
            return folder
            
        except Exception as e:
            logger.error(f"Error processing directory {path}: {e}")
            return FolderNode(name=path.name, path=str(path))
            
    def get_document_relationships(self) -> Dict[str, Any]:
        """
        Get document relationships for visualization.
        
        Returns:
            Dict[str, Any]: Document relationships and hierarchy data
        """
        hierarchy = self.build_hierarchy()
        return {
            'status': 'success',
            'hierarchy': self._convert_to_dict(hierarchy)
        }
    
    def _convert_to_dict(self, node: Any) -> Dict[str, Any]:
        """
        Convert a node (folder or document) to a dictionary representation.
        
        Args:
            node (Union[FolderNode, DocumentNode]): Node to convert
            
        Returns:
            Dict[str, Any]: Dictionary representation of the node
        """
        if isinstance(node, DocumentNode):
            return {
                'type': 'document',
                'name': node.name,
                'path': node.path
            }
        elif isinstance(node, FolderNode):
            return {
                'type': 'folder',
                'name': node.name,
                'path': node.path,
                'children': [self._convert_to_dict(child) for child in node.children]
            }
        return {}

    def get_top_level_folders(self):
        """Get all top-level folders in InputDocs."""
        return [d for d in os.listdir(self.base_path) 
                if os.path.isdir(os.path.join(self.base_path, d))
                and not d.startswith('.')]

    def get_folder_contents(self, folder_path):
        """Get contents of a folder with hierarchical structure."""
        full_path = os.path.join(self.base_path, folder_path)
        contents = []
        
        try:
            for item in sorted(os.listdir(full_path)):
                if item.startswith('.'):
                    continue
                    
                item_path = os.path.join(full_path, item)
                rel_path = os.path.join(folder_path, item)
                
                if os.path.isdir(item_path):
                    contents.append({
                        "name": item,
                        "type": "folder",
                        "path": rel_path,
                        "children": self.get_folder_contents(rel_path)
                    })
                else:
                    contents.append({
                        "name": item,
                        "type": "document",
                        "path": rel_path
                    })
            
            return contents
            
        except Exception as e:
            print(f"Error processing {folder_path}: {str(e)}")
            return []

    def process_document_query(self, doc_path: str, query: str) -> str:
        """Process a query about a specific document."""
        if not self.openai_api_key:
            return "OpenAI API key not configured"

        try:
            # Extract text from PDF
            full_path = os.path.join(self.base_path, doc_path)
            pdf = PdfReader(full_path)
            text = ""
            for page in pdf.pages:
                text += page.extract_text()

            # Create OpenAI query with context using new client
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant explaining concepts from documents."},
                    {"role": "user", "content": f"Based on this document content:\n\n{text[:4000]}...\n\nQuestion: {query}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error processing query: {str(e)}"