"""
Tests for external modules
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from external import AzureClient, VectorStore, EmbeddingService


class TestAzureClient:
    """Test AzureClient functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.azure_client = AzureClient()
    
    @pytest.mark.asyncio
    async def test_generate_response(self):
        """Test response generation"""
        messages = [{"role": "user", "content": "test message"}]
        response = await self.azure_client.generate_response(messages)
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    @pytest.mark.asyncio
    async def test_generate_embeddings(self):
        """Test embedding generation"""
        texts = ["test text"]
        embeddings = await self.azure_client.generate_embeddings(texts)
        
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1536  # Default dimension
    
    @pytest.mark.asyncio
    async def test_analyze_tools(self):
        """Test tool analysis"""
        tools = [
            {"name": "login", "category": "Authentication"},
            {"name": "get_balance", "category": "Account"}
        ]
        
        result = await self.azure_client.analyze_tools(tools)
        
        assert "use_cases" in result
        assert len(result["use_cases"]) > 0
    
    def test_is_available(self):
        """Test availability check"""
        available = self.azure_client.is_available()
        assert isinstance(available, bool)
    
    def test_get_status(self):
        """Test status retrieval"""
        status = self.azure_client.get_status()
        assert "available" in status
        assert "endpoint" in status


class TestVectorStore:
    """Test VectorStore functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.vector_store = VectorStore()
    
    def test_add_vector(self):
        """Test adding vector"""
        content = "test content"
        vector = [0.1] * 1536
        metadata = {"type": "test"}
        
        vector_id = self.vector_store.add_vector(content, vector, metadata)
        
        assert vector_id is not None
        assert vector_id in self.vector_store.vectors
    
    def test_get_vector(self):
        """Test getting vector"""
        content = "test content"
        vector = [0.1] * 1536
        metadata = {"type": "test"}
        
        vector_id = self.vector_store.add_vector(content, vector, metadata)
        result = self.vector_store.get_vector(vector_id)
        
        assert result is not None
        assert result["content"] == content
    
    def test_search_similar(self):
        """Test similarity search"""
        # Add test vectors
        self.vector_store.add_vector("test content 1", [0.1] * 1536, {"type": "test"})
        self.vector_store.add_vector("test content 2", [0.2] * 1536, {"type": "test"})
        
        query_vector = [0.15] * 1536
        results = self.vector_store.search_similar(query_vector, top_k=2)
        
        assert len(results) > 0
        assert all("similarity" in result for result in results)
    
    def test_get_statistics(self):
        """Test getting statistics"""
        self.vector_store.add_vector("test", [0.1] * 1536, {"type": "test"})
        stats = self.vector_store.get_statistics()
        
        assert stats["total_vectors"] == 1
        assert stats["dimension"] == 1536
    
    def test_clear_store(self):
        """Test clearing store"""
        self.vector_store.add_vector("test", [0.1] * 1536, {"type": "test"})
        self.vector_store.clear_store()
        
        assert len(self.vector_store.vectors) == 0


class TestEmbeddingService:
    """Test EmbeddingService functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.embedding_service = EmbeddingService()
    
    @pytest.mark.asyncio
    async def test_generate_embedding(self):
        """Test embedding generation"""
        text = "test text"
        embedding = await self.embedding_service.generate_embedding(text)
        
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_add_document(self):
        """Test adding document"""
        content = "test document"
        metadata = {"type": "test"}
        
        vector_id = await self.embedding_service.add_document(content, metadata)
        
        assert vector_id is not None
    
    @pytest.mark.asyncio
    async def test_search_similar(self):
        """Test similarity search"""
        # Add test document
        await self.embedding_service.add_document("test content", {"type": "test"})
        
        results = await self.embedding_service.search_similar("test query")
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_find_relevant_use_cases(self):
        """Test finding relevant use cases"""
        use_cases = [
            {"id": "1", "name": "Test Case", "description": "Test description", "keywords": ["test"]}
        ]
        
        results = await self.embedding_service.find_relevant_use_cases("test query", use_cases)
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_calculate_similarity(self):
        """Test similarity calculation"""
        text1 = "test text 1"
        text2 = "test text 2"
        
        similarity = await self.embedding_service.calculate_similarity(text1, text2)
        
        assert 0.0 <= similarity <= 1.0
    
    def test_get_embedding_stats(self):
        """Test getting embedding statistics"""
        stats = self.embedding_service.get_embedding_stats()
        
        assert "embedding_model" in stats
        assert "dimension" in stats
        assert "azure_client_available" in stats


if __name__ == "__main__":
    pytest.main([__file__])
