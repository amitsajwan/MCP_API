"""
Embedding Service for Demo MCP System
Handles text embedding generation and similarity search
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

from .azure_client import AzureClient
from .vector_store import VectorStore
from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing embeddings"""
    
    def __init__(self):
        self.azure_client = AzureClient()
        self.vector_store = VectorStore()
        self.embedding_model = settings.azure_openai_embedding_model
        self.dimension = settings.vector_db_dimension
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            # Use Azure client if available
            if self.azure_client.is_available():
                embeddings = await self.azure_client.generate_embeddings([text])
                return embeddings[0]
            else:
                # Fallback to simple hash-based embedding for demo
                return self._generate_hash_embedding(text)
                
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return self._generate_hash_embedding(text)
    
    def _generate_hash_embedding(self, text: str) -> List[float]:
        """Generate simple hash-based embedding for demo"""
        # Create a deterministic embedding based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # Convert hash to embedding vector
        embedding = []
        for i in range(0, len(text_hash), 2):
            hex_pair = text_hash[i:i+2]
            value = int(hex_pair, 16) / 255.0  # Normalize to 0-1
            embedding.append(value)
        
        # Pad or truncate to correct dimension
        while len(embedding) < self.dimension:
            embedding.append(0.0)
        
        return embedding[:self.dimension]
    
    async def add_document(self, content: str, metadata: Dict[str, Any]) -> str:
        """Add document to vector store"""
        try:
            # Generate embedding
            embedding = await self.generate_embedding(content)
            
            # Add to vector store
            vector_id = self.vector_store.add_vector(content, embedding, metadata)
            
            logger.info(f"Added document to vector store: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            return None
    
    async def search_similar(self, query: str, top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query)
            
            # Search vector store
            results = self.vector_store.search_similar(query_embedding, top_k, threshold)
            
            logger.info(f"Found {len(results)} similar documents for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Error searching similar documents: {e}")
            return []
    
    async def find_relevant_use_cases(self, query: str, use_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find relevant use cases for a query"""
        try:
            # Add use cases to vector store if not already present
            for use_case in use_cases:
                content = f"{use_case['name']} {use_case['description']} {' '.join(use_case.get('keywords', []))}"
                metadata = {
                    "type": "use_case",
                    "use_case_id": use_case["id"],
                    "category": use_case.get("category", "General")
                }
                
                # Check if already exists
                existing = self.vector_store.search_by_metadata({"use_case_id": use_case["id"]})
                if not existing:
                    await self.add_document(content, metadata)
            
            # Search for similar use cases
            results = await self.search_similar(query, top_k=3, threshold=0.5)
            
            # Filter for use cases only
            relevant_use_cases = []
            for result in results:
                if result["metadata"].get("type") == "use_case":
                    use_case_id = result["metadata"]["use_case_id"]
                    # Find the original use case
                    for use_case in use_cases:
                        if use_case["id"] == use_case_id:
                            relevant_use_cases.append({
                                "use_case": use_case,
                                "similarity": result["similarity"],
                                "reason": f"Similar to: {result['content'][:100]}..."
                            })
                            break
            
            return relevant_use_cases
            
        except Exception as e:
            logger.error(f"Error finding relevant use cases: {e}")
            return []
    
    async def find_relevant_tools(self, query: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find relevant tools for a query"""
        try:
            # Add tools to vector store if not already present
            for tool in tools:
                content = f"{tool['name']} {tool['description']} {tool['category']}"
                metadata = {
                    "type": "tool",
                    "tool_name": tool["name"],
                    "category": tool["category"]
                }
                
                # Check if already exists
                existing = self.vector_store.search_by_metadata({"tool_name": tool["name"]})
                if not existing:
                    await self.add_document(content, metadata)
            
            # Search for similar tools
            results = await self.search_similar(query, top_k=5, threshold=0.5)
            
            # Filter for tools only
            relevant_tools = []
            for result in results:
                if result["metadata"].get("type") == "tool":
                    tool_name = result["metadata"]["tool_name"]
                    # Find the original tool
                    for tool in tools:
                        if tool["name"] == tool_name:
                            relevant_tools.append({
                                "tool": tool,
                                "similarity": result["similarity"],
                                "reason": f"Similar to: {result['content'][:100]}..."
                            })
                            break
            
            return relevant_tools
            
        except Exception as e:
            logger.error(f"Error finding relevant tools: {e}")
            return []
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding service statistics"""
        vector_stats = self.vector_store.get_statistics()
        
        return {
            "embedding_model": self.embedding_model,
            "dimension": self.dimension,
            "vector_store_stats": vector_stats,
            "azure_client_available": self.azure_client.is_available()
        }
    
    async def batch_generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            if self.azure_client.is_available():
                return await self.azure_client.generate_embeddings(texts)
            else:
                # Generate hash-based embeddings for demo
                embeddings = []
                for text in texts:
                    embedding = self._generate_hash_embedding(text)
                    embeddings.append(embedding)
                return embeddings
                
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            return [self._generate_hash_embedding(text) for text in texts]
    
    async def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        try:
            embedding1 = await self.generate_embedding(text1)
            embedding2 = await self.generate_embedding(text2)
            
            # Calculate cosine similarity
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def clear_embeddings(self) -> None:
        """Clear all embeddings from vector store"""
        self.vector_store.clear_store()
        logger.info("All embeddings cleared")
    
    def export_embeddings(self) -> Dict[str, Any]:
        """Export all embeddings and metadata"""
        return self.vector_store.export_vectors()
    
    def import_embeddings(self, data: Dict[str, Any]) -> bool:
        """Import embeddings and metadata"""
        return self.vector_store.import_vectors(data)
