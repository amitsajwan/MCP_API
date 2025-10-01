"""
External services module for Demo MCP System
Handles Azure OpenAI, vector store, and embedding services
"""

from .azure_client import AzureClient
from .vector_store import VectorStore
from .embedding_service import EmbeddingService

__all__ = [
    'AzureClient',
    'VectorStore', 
    'EmbeddingService'
]
