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
import tiktoken
import time
import numpy as np
from collections import defaultdict

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
    
    def __init__(self, base_path: str):
        """
        Initialize the document processor.
        
        Args:
            base_path (str): Path to the root documents directory
        """
        self.base_path = base_path
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.encoding = tiktoken.encoding_for_model("gpt-4")
        self.max_tokens = 2000  # Reduced from previous value
        self.min_pause = 1.0    # Minimum pause between API calls
        self.chapter_markers = ["Chapter", "Section", "Part", "Unit", "Module"]
        self._query_cache = {}
        self.logger = logging.getLogger(__name__)

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
        return self._process_directory(self.base_path)
    
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
                path=str(path.relative_to(self.base_path)),
                children=[]
            )
            
            for item in path.iterdir():
                if item.is_dir():
                    child_node = self._process_directory(item)
                    folder.children.append(child_node)
                elif item.suffix.lower() == '.pdf':
                    doc_node = DocumentNode(
                        name=item.name,
                        path=str(item.relative_to(self.base_path)),
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

    def chunk_document(self, pages_text: Dict[int, str]) -> List[Dict[str, Any]]:
        """Split document into digestible chunks while preserving page context."""
        chunks = []
        current_chunk = []
        current_tokens = 0
        current_pages = []

        for page_num, text in pages_text.items():
            page_tokens = self.encoding.encode(text)
            if current_tokens + len(page_tokens) > self.max_tokens:
                if current_chunk:
                    chunks.append({
                        'text': ' '.join(current_chunk),
                        'pages': current_pages
                    })
                current_chunk = [text]
                current_tokens = len(page_tokens)
                current_pages = [page_num]
            else:
                current_chunk.append(text)
                current_tokens += len(page_tokens)
                current_pages.append(page_num)

        if current_chunk:
            chunks.append({
                'text': ' '.join(current_chunk),
                'pages': current_pages
            })

        return chunks

    def detect_chapters(self, pdf: PdfReader) -> List[Dict[str, Any]]:
        """Detect logical document subdivisions."""
        chapters = []
        current_chapter = {
            'title': 'Introduction',
            'start_page': 1,
            'text': [],
            'toc_level': 0
        }
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            
            # Look for chapter markers
            lines = text.split('\n')
            for line in lines:
                if any(marker in line for marker in self.chapter_markers):
                    if current_chapter['text']:
                        chapters.append(current_chapter)
                        current_chapter = {
                            'title': line.strip(),
                            'start_page': page_num,
                            'text': [],
                            'toc_level': 1
                        }
                    break
            
            current_chapter['text'].append(text)
        
        # Add final chapter
        if current_chapter['text']:
            chapters.append(current_chapter)
        
        return chapters

    def extract_text_from_pdf(self, full_path: str) -> str:
        """Extract text from PDF file."""
        doc = fitz.open(full_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text

    def process_document_query(self, doc_path: str, query: str) -> Dict[str, Any]:
        """Process a query against a PDF document."""
        try:
            full_path = os.path.join(self.base_path, doc_path)
            self.logger.info(f"Processing query for: {doc_path}")
            
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"Document not found: {full_path}")

            # Extract text
            pdf_doc = fitz.open(full_path)
            text = self._extract_general_context(pdf_doc)
            
            # Process with OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": f"Based on this text:\n{text}\n\nAnswer this question: {query}"}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return {
                "answer": response.choices[0].message.content,
                "source_document": os.path.basename(doc_path),
                "pages_processed": pdf_doc.page_count
            }

        except Exception as e:
            self.logger.error(f"Query processing error: {str(e)}", exc_info=True)
            return {
                "error": "Failed to process query",
                "details": str(e)
            }

    def _extract_timing_context(self, pdf: PdfReader) -> str:
        """Extract context specifically related to timing and schedules."""
        relevant_text = []
        timing_keywords = ['schedule', 'timeline', 'date', 'when', 'plan', 'month', 'year', 'quarter']
        
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in timing_keywords):
                    relevant_text.append(line)
        
        return '\n'.join(relevant_text)[:4000]  # Stay within token limits

    def is_relevant_to_query(self, text: str, query: str) -> bool:
        """Check if chapter content is relevant to query."""
        # Get embeddings for query and text
        try:
            query_emb = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            ).data[0].embedding

            text_preview = text[:1000]  # Use start of chapter
            text_emb = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text_preview
            ).data[0].embedding

            # Calculate similarity
            similarity = np.dot(query_emb, text_emb)
            return similarity > 0.7  # Adjust threshold as needed
            
        except Exception as e:
            logger.warning(f"Error checking relevance: {e}")
            return True  # Process chapter if check fails

    def combine_chapter_responses(self, responses: List[Dict[str, Any]], doc_path: str) -> Dict[str, Any]:
        """Combine responses from different chapters."""
        combined_text = ["### Summary\n"]
        
        for resp in responses:
            combined_text.append(f"\n### From {resp['chapter']} (p.{resp['start_page']})")
            combined_text.append(resp['content'])

        return {
            "answer": '\n'.join(combined_text),
            "source_document": doc_path,
            "chapters_processed": [r['chapter'] for r in responses]
        }

    def get_system_prompt(self) -> str:
        return """
        When answering:
        1. Start with a brief summary
        2. Format citations as (p.X)
        3. Use block quotes for important passages:
           > Relevant quote here (p.X)
        4. Structure with headers:
           ### Main Points
           ### Details
           ### Related Concepts
        5. Bold key terms using **term**
        6. Use --- for section breaks
        7. Keep responses focused and concise
        """

    def _get_system_prompt(self) -> str:
        """Get system prompt for document query processing."""
        return """
        As a document analysis assistant, format your responses using Markdown:

        1. Start with a brief summary under "### Summary"
        2. Include relevant quotes using blockquotes:
           > "Exact quote from document" (p.X)
        3. Structure your response with headers:
           ### Summary
           ### Key Points
           ### Supporting Evidence
           ### Related Topics
        4. Use **bold** for key terms
        5. Use --- for section breaks
        6. List citations at the end under "### Sources"
        7. Keep responses focused and evidence-based
        8. Include page numbers for all citations (p.X)
        """

    def combine_responses(self, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine chunked responses into a coherent answer."""
        combined_text = ["### Summary\n"]
        seen_content = set()
        
        for resp in responses:
            # Remove duplicates and combine unique insights
            lines = resp['content'].split('\n')
            for line in lines:
                if line not in seen_content:
                    seen_content.add(line)
                    combined_text.append(line)

        return {
            "answer": '\n'.join(combined_text),
            "source_document": doc_path,
            "processed_pages": sorted(set(
                page for resp in responses for page in resp['pages']
            ))
        }

    def _extract_general_context(self, pdf_doc: fitz.Document) -> str:
        """Extract general context from first few pages."""
        try:
            context = []
            # Get text from first 2 pages or TOC
            for i in range(min(2, pdf_doc.page_count)):
                page = pdf_doc[i]
                text = page.get_text()
                if text:
                    context.append(text)
            return "\n".join(context)
        except Exception as e:
            logger.error(f"Error extracting general context: {str(e)}")
            return ""

    def _process_chapter(self, text: str, query: str) -> Optional[Dict[str, Any]]:
        """Process a single chapter with OpenAI."""
        try:
            messages = [
                {"role": "system", "content": "You are analyzing a document chapter."},
                {"role": "user", "content": f"Based on this text:\n{text}\n\nAnswer this question: {query}"}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return {
                "content": response.choices[0].message.content,
                "relevant": True if "not relevant" not in response.choices[0].message.content.lower() else False
            }
        except Exception as e:
            logger.error(f"Error processing chapter: {str(e)}")
            return None