import os
import numpy as np
import logging
from openai import OpenAI
from PyPDF2 import PdfReader
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from app.core.user_context import UserContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticProcessor:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            logger.warning("OpenAI API key not found in environment variables")
        self.client = OpenAI(api_key=self.openai_api_key)
        self.embeddings_cache = {}
        self.user_context = UserContext()
    
    def compute_level_0_distances(self) -> Dict[Tuple[str, str], float]:
        """Compute semantic distances between top-level folders with user context."""
        try:
            distances = {}
            top_folders = self._get_top_level_folders()
            logger.info(f"Processing {len(top_folders)} top-level folders")
            
            # Add "Me" node at the center
            folder_embeddings = {"Me": self._get_user_embedding()}
            
            # Get embeddings for folders
            for folder in top_folders:
                embedding = self._get_folder_embedding(folder)
                if embedding is not None:
                    # Apply user preference weighting
                    user_weight = self.user_context.preferences["domains"].get(folder, 0.5)
                    weighted_embedding = embedding * user_weight
                    folder_embeddings[folder] = weighted_embedding
                else:
                    logger.warning(f"Could not generate embedding for folder: {folder}")
            
            # Compute distances including "Me" node
            all_nodes = ["Me"] + top_folders
            for i, node1 in enumerate(all_nodes):
                for node2 in all_nodes[i+1:]:
                    if node1 in folder_embeddings and node2 in folder_embeddings:
                        distance = self._compute_distance(
                            folder_embeddings[node1],
                            folder_embeddings[node2]
                        )
                        distances[(node1, node2)] = distance
            
            return distances
            
        except Exception as e:
            logger.error(f"Error computing level 0 distances: {str(e)}")
            return {}
    
    def _get_user_embedding(self) -> np.ndarray:
        """Generate embedding for user based on preferences and history."""
        user_summary = self._generate_user_summary()
        return self._get_text_embedding(user_summary)
    
    def _generate_user_summary(self) -> str:
        """Create a text summary of user's interests and expertise."""
        summary_parts = ["Personal knowledge profile"]
        
        # Add domain interests
        interests = sorted(
            self.user_context.preferences["domains"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        if interests:
            summary_parts.append("Primary interests: " + 
                               ", ".join(f"{domain}" for domain, _ in interests[:3]))
        
        # Add expertise levels
        expertise = self.user_context.preferences["expertise_levels"]
        if expertise:
            expert_domains = [d for d, level in expertise.items() if level > 0.7]
            if expert_domains:
                summary_parts.append("Expert in: " + ", ".join(expert_domains))
        
        return " ".join(summary_parts)
    
    def _get_top_level_folders(self) -> List[str]:
        """Get all top-level folders in the base path."""
        try:
            return [d for d in os.listdir(self.base_path) 
                    if os.path.isdir(os.path.join(self.base_path, d))
                    and not d.startswith('.')]
        except Exception as e:
            logger.error(f"Error getting top-level folders: {str(e)}")
            return []
    
    def _get_folder_embedding(self, folder_path: str) -> Optional[np.ndarray]:
        """Compute aggregate embedding for a folder based on its contents."""
        try:
            if folder_path in self.embeddings_cache:
                return self.embeddings_cache[folder_path]
                
            folder_summary = self._generate_folder_summary(folder_path)
            if not folder_summary:
                return None
                
            embedding = self._get_text_embedding(folder_summary)
            self.embeddings_cache[folder_path] = embedding
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding for {folder_path}: {str(e)}")
            return None
    
    def _generate_folder_summary(self, folder_path: str) -> str:
        """Generate a summary of folder contents for embedding."""
        try:
            content_summary = []
            full_path = os.path.join(self.base_path, folder_path)
            
            # Add folder name with domain context
            content_summary.append(f"Knowledge domain: {folder_path}")
            
            # Add subfolder names as subdomains
            subfolders = [
                d for d in os.listdir(full_path)
                if os.path.isdir(os.path.join(full_path, d))
                and not d.startswith('.')
            ]
            if subfolders:
                content_summary.append(f"Subdomains: {', '.join(subfolders)}")
            
            # Sample document titles for topic inference
            docs = []
            for root, _, files in os.walk(full_path):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        # Clean and format document names
                        doc_name = os.path.splitext(file)[0]
                        doc_name = doc_name.replace('_', ' ').replace('-', ' ')
                        docs.append(doc_name)
                    if len(docs) >= 5:  # Limit to 5 representative documents
                        break
            if docs:
                content_summary.append(f"Representative topics: {', '.join(docs)}")
            
            return ' '.join(content_summary)
            
        except Exception as e:
            logger.error(f"Error generating summary for {folder_path}: {str(e)}")
            return ""
    
    def _get_text_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding vector for text using OpenAI's API."""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text[:8191]  # API token limit
            )
            return np.array(response.data[0].embedding)
            
        except Exception as e:
            logger.error(f"Error getting embedding from OpenAI: {str(e)}")
            return None
    
    def _compute_distance(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute semantic distance between two embeddings."""
        try:
            similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
            return 1 - similarity
            
        except Exception as e:
            logger.error(f"Error computing distance: {str(e)}")
            return 1.0  # Maximum distance on error