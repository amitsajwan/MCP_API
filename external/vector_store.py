"""
Vector Store for Demo MCP System
Handles vector similarity search and storage
"""

import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

from config.settings import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for similarity search and caching"""
    
    def __init__(self):
        self.vectors: Dict[str, np.ndarray] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.collection_name = settings.vector_db_collection_name
        self.dimension = settings.vector_db_dimension
        self.max_vectors = 10000  # Limit for demo
        
    def _generate_vector_id(self, content: str, metadata: Dict[str, Any]) -> str:
        """Generate unique vector ID"""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        metadata_hash = hashlib.md5(json.dumps(metadata, sort_keys=True).encode()).hexdigest()[:8]
        return f"{content_hash}_{metadata_hash}"
    
    def add_vector(self, content: str, vector: List[float], metadata: Dict[str, Any]) -> str:
        """Add vector to store"""
        if len(self.vectors) >= self.max_vectors:
            # Remove oldest vector
            oldest_id = min(self.vectors.keys(), key=lambda k: self.metadata[k]["timestamp"])
            self.remove_vector(oldest_id)
        
        vector_id = self._generate_vector_id(content, metadata)
        
        # Convert to numpy array
        vector_array = np.array(vector, dtype=np.float32)
        
        # Ensure correct dimension
        if len(vector_array) != self.dimension:
            logger.warning(f"Vector dimension mismatch: expected {self.dimension}, got {len(vector_array)}")
            # Pad or truncate to correct dimension
            if len(vector_array) < self.dimension:
                vector_array = np.pad(vector_array, (0, self.dimension - len(vector_array)))
            else:
                vector_array = vector_array[:self.dimension]
        
        self.vectors[vector_id] = vector_array
        self.metadata[vector_id] = {
            "content": content,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
            "dimension": len(vector_array)
        }
        
        logger.info(f"Added vector {vector_id} to store")
        return vector_id
    
    def remove_vector(self, vector_id: str) -> bool:
        """Remove vector from store"""
        if vector_id in self.vectors:
            del self.vectors[vector_id]
            del self.metadata[vector_id]
            logger.info(f"Removed vector {vector_id} from store")
            return True
        return False
    
    def search_similar(self, query_vector: List[float], top_k: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        if not self.vectors:
            return []
        
        # Convert query vector to numpy array
        query_array = np.array(query_vector, dtype=np.float32)
        
        # Ensure correct dimension
        if len(query_array) != self.dimension:
            logger.warning(f"Query vector dimension mismatch: expected {self.dimension}, got {len(query_array)}")
            if len(query_array) < self.dimension:
                query_array = np.pad(query_array, (0, self.dimension - len(query_array)))
            else:
                query_array = query_array[:self.dimension]
        
        # Calculate similarities
        similarities = []
        for vector_id, stored_vector in self.vectors.items():
            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_array, stored_vector)
            if similarity >= threshold:
                similarities.append({
                    "vector_id": vector_id,
                    "similarity": float(similarity),
                    "content": self.metadata[vector_id]["content"],
                    "metadata": self.metadata[vector_id]["metadata"]
                })
        
        # Sort by similarity and return top_k
        similarities.sort(key=lambda x: x["similarity"], reverse=True)
        return similarities[:top_k]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_vector(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """Get vector by ID"""
        if vector_id in self.vectors:
            return {
                "vector_id": vector_id,
                "vector": self.vectors[vector_id].tolist(),
                "content": self.metadata[vector_id]["content"],
                "metadata": self.metadata[vector_id]["metadata"],
                "timestamp": self.metadata[vector_id]["timestamp"]
            }
        return None
    
    def get_all_vectors(self) -> List[Dict[str, Any]]:
        """Get all vectors"""
        return [self.get_vector(vector_id) for vector_id in self.vectors.keys()]
    
    def search_by_metadata(self, metadata_filter: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search vectors by metadata"""
        results = []
        
        for vector_id, meta in self.metadata.items():
            match = True
            for key, value in metadata_filter.items():
                if key not in meta["metadata"] or meta["metadata"][key] != value:
                    match = False
                    break
            
            if match:
                results.append(self.get_vector(vector_id))
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        if not self.vectors:
            return {
                "total_vectors": 0,
                "dimension": self.dimension,
                "collection_name": self.collection_name,
                "max_vectors": self.max_vectors
            }
        
        # Calculate average similarity between vectors
        similarities = []
        vector_list = list(self.vectors.values())
        
        for i in range(len(vector_list)):
            for j in range(i + 1, len(vector_list)):
                similarity = self._cosine_similarity(vector_list[i], vector_list[j])
                similarities.append(similarity)
        
        avg_similarity = np.mean(similarities) if similarities else 0.0
        
        return {
            "total_vectors": len(self.vectors),
            "dimension": self.dimension,
            "collection_name": self.collection_name,
            "max_vectors": self.max_vectors,
            "average_similarity": float(avg_similarity),
            "memory_usage_mb": len(self.vectors) * self.dimension * 4 / (1024 * 1024)  # 4 bytes per float32
        }
    
    def clear_store(self) -> None:
        """Clear all vectors from store"""
        self.vectors.clear()
        self.metadata.clear()
        logger.info("Vector store cleared")
    
    def export_vectors(self) -> Dict[str, Any]:
        """Export all vectors and metadata"""
        return {
            "vectors": {k: v.tolist() for k, v in self.vectors.items()},
            "metadata": self.metadata,
            "collection_name": self.collection_name,
            "dimension": self.dimension,
            "export_timestamp": datetime.now().isoformat()
        }
    
    def import_vectors(self, data: Dict[str, Any]) -> bool:
        """Import vectors and metadata"""
        try:
            self.vectors = {k: np.array(v, dtype=np.float32) for k, v in data["vectors"].items()}
            self.metadata = data["metadata"]
            logger.info(f"Imported {len(self.vectors)} vectors")
            return True
        except Exception as e:
            logger.error(f"Failed to import vectors: {e}")
            return False
    
    def cleanup_expired(self, max_age_hours: int = 24) -> int:
        """Clean up expired vectors"""
        current_time = datetime.now()
        expired_count = 0
        
        expired_vectors = []
        for vector_id, meta in self.metadata.items():
            vector_time = datetime.fromisoformat(meta["timestamp"])
            age_hours = (current_time - vector_time).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                expired_vectors.append(vector_id)
        
        for vector_id in expired_vectors:
            self.remove_vector(vector_id)
            expired_count += 1
        
        logger.info(f"Cleaned up {expired_count} expired vectors")
        return expired_count
