"""
Semantic State Manager - Core innovation for intelligent API orchestration
Stores and retrieves execution state, API results, and context as searchable embeddings
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)


class SemanticStateManager:
    """
    Maintains all state as searchable embeddings using vector similarity
    Enables natural language queries for past interactions and data
    """
    
    def __init__(self, 
                 vector_db_url: str = "http://localhost:6333",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 collection_name: str = "semantic_state"):
        """
        Initialize semantic state manager
        
        Args:
            vector_db_url: Qdrant server URL
            embedding_model: Sentence transformer model name
            collection_name: Vector collection name
        """
        self.client = QdrantClient(url=vector_db_url)
        self.embedding_model = SentenceTransformer(embedding_model)
        self.collection_name = collection_name
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension
        
        # Initialize collection if it doesn't exist
        asyncio.create_task(self._initialize_collection())
    
    async def _initialize_collection(self):
        """Initialize Qdrant collection for semantic state storage"""
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to initialize collection: {e}")
    
    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            embedding = self.embedding_model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * self.embedding_dim
    
    async def store_state(self, 
                         state_description: str,
                         data: Dict[str, Any],
                         context_type: str = "execution",
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store any state as semantic embedding
        
        Args:
            state_description: Natural language description of the state
            data: Actual data to store
            context_type: Type of context (execution, result, memory, etc.)
            metadata: Additional metadata
            
        Returns:
            Unique ID of the stored state
        """
        try:
            state_id = str(uuid.uuid4())
            timestamp = datetime.utcnow().isoformat()
            
            # Create payload
            payload = {
                "id": state_id,
                "timestamp": timestamp,
                "context_type": context_type,
                "description": state_description,
                "data": data,
                **(metadata or {})
            }
            
            # Generate embedding from description + context
            embedding_text = f"{context_type}: {state_description}"
            embedding = self._embed(embedding_text)
            
            # Store in vector database
            point = PointStruct(
                id=state_id,
                vector=embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.debug(f"Stored state: {state_id} - {context_type}")
            return state_id
            
        except Exception as e:
            logger.error(f"Failed to store state: {e}")
            raise
    
    async def query_relevant_state(self, 
                                  query: str,
                                  context_types: Optional[List[str]] = None,
                                  limit: int = 5,
                                  score_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Retrieve semantically similar states using natural language query
        
        Args:
            query: Natural language query for relevant states
            context_types: Filter by specific context types
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of relevant states with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self._embed(query)
            
            # Build filter
            filter_conditions = None
            if context_types:
                filter_conditions = {
                    "must": [
                        {"key": "context_type", "match": {"any": context_types}}
                    ]
                }
            
            # Search vector database
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=filter_conditions,
                limit=limit,
                score_threshold=score_threshold
            )
            
            # Format results
            results = []
            for point in search_result:
                results.append({
                    "id": point.id,
                    "score": point.score,
                    "data": point.payload.get("data", {}),
                    "description": point.payload.get("description", ""),
                    "context_type": point.payload.get("context_type", ""),
                    "timestamp": point.payload.get("timestamp", ""),
                    "metadata": {k: v for k, v in point.payload.items() 
                               if k not in ["id", "data", "description", "context_type", "timestamp"]}
                })
            
            logger.debug(f"Found {len(results)} relevant states for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query relevant state: {e}")
            return []
    
    async def get_execution_context(self, 
                                  user_query: str,
                                  iteration: int = 0) -> Dict[str, Any]:
        """
        Get comprehensive execution context for LLM decision making
        
        Args:
            user_query: Current user query
            iteration: Current iteration number
            
        Returns:
            Structured context for LLM
        """
        try:
            # Query for relevant past executions
            execution_query = f"query: {user_query} iteration: {iteration}"
            past_executions = await self.query_relevant_state(
                execution_query,
                context_types=["execution_result", "execution_state"],
                limit=3
            )
            
            # Query for relevant API results
            api_query = f"API results for {user_query}"
            api_results = await self.query_relevant_state(
                api_query,
                context_types=["api_result"],
                limit=5
            )
            
            # Query for relevant memory/context
            memory_query = f"context memory {user_query}"
            memory_context = await self.query_relevant_state(
                memory_query,
                context_types=["memory", "context"],
                limit=3
            )
            
            return {
                "user_query": user_query,
                "iteration": iteration,
                "past_executions": past_executions,
                "api_results": api_results,
                "memory_context": memory_context,
                "total_context_items": len(past_executions) + len(api_results) + len(memory_context)
            }
            
        except Exception as e:
            logger.error(f"Failed to get execution context: {e}")
            return {
                "user_query": user_query,
                "iteration": iteration,
                "past_executions": [],
                "api_results": [],
                "memory_context": [],
                "total_context_items": 0
            }
    
    async def store_api_result(self, 
                              api_name: str,
                              endpoint: str,
                              result: Dict[str, Any],
                              query_context: str) -> str:
        """
        Store API result with semantic context for future reuse
        
        Args:
            api_name: Name of the API
            endpoint: API endpoint used
            result: API response data
            query_context: Context that led to this API call
            
        Returns:
            ID of stored result
        """
        description = f"API result from {api_name} {endpoint} for {query_context}"
        
        return await self.store_state(
            state_description=description,
            data={
                "api_name": api_name,
                "endpoint": endpoint,
                "result": result,
                "query_context": query_context
            },
            context_type="api_result",
            metadata={
                "api_name": api_name,
                "endpoint": endpoint,
                "result_size": len(str(result))
            }
        )
    
    async def store_execution_step(self,
                                  action: str,
                                  tool_name: str,
                                  params: Dict[str, Any],
                                  result: Dict[str, Any],
                                  query_context: str,
                                  iteration: int) -> str:
        """
        Store execution step for future reference
        
        Args:
            action: Action taken
            tool_name: Tool used
            params: Parameters passed
            result: Result obtained
            query_context: Original query context
            iteration: Iteration number
            
        Returns:
            ID of stored execution step
        """
        description = f"Executed {action} using {tool_name} for {query_context} iteration {iteration}"
        
        return await self.store_state(
            state_description=description,
            data={
                "action": action,
                "tool_name": tool_name,
                "params": params,
                "result": result,
                "query_context": query_context,
                "iteration": iteration
            },
            context_type="execution_result",
            metadata={
                "tool_name": tool_name,
                "action": action,
                "iteration": iteration
            }
        )
    
    async def clear_old_states(self, days_old: int = 30):
        """Clear states older than specified days"""
        try:
            # This would require implementing a time-based filter
            # For now, we'll keep all states
            logger.info(f"State cleanup not implemented - keeping all states")
        except Exception as e:
            logger.error(f"Failed to clear old states: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored states"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            # Get sample of recent states
            recent_states = await self.query_relevant_state(
                "recent execution",
                limit=10
            )
            
            context_types = {}
            for state in recent_states:
                context_type = state.get("context_type", "unknown")
                context_types[context_type] = context_types.get(context_type, 0) + 1
            
            return {
                "total_points": collection_info.points_count,
                "collection_status": collection_info.status,
                "context_types": context_types,
                "recent_activity": len(recent_states)
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}


# Example usage and testing
async def main():
    """Test the semantic state manager"""
    manager = SemanticStateManager()
    
    # Store some test states
    await manager.store_state(
        "User asked about account balance",
        {"balance": 1500.50, "currency": "USD"},
        "api_result"
    )
    
    await manager.store_state(
        "Executed account lookup for user",
        {"tool": "account_api", "status": "success"},
        "execution_result"
    )
    
    # Query relevant states
    results = await manager.query_relevant_state("account balance information")
    print(f"Found {len(results)} relevant results")
    for result in results:
        print(f"- {result['description']} (score: {result['score']:.3f})")


if __name__ == "__main__":
    asyncio.run(main())