"""
Comprehensive test suite for Intelligent API Orchestration System
Tests semantic state management, tool integration, and orchestration
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from semantic_state_manager import SemanticStateManager
from tool_manager import ToolManager, ToolExecutionResult
from adaptive_orchestrator import AdaptiveOrchestrator, ExecutionStep


class TestSemanticStateManager:
    """Test semantic state management functionality"""
    
    @pytest.fixture
    async def state_manager(self):
        """Create state manager for testing"""
        # Mock Qdrant client for testing
        with patch('semantic_state_manager.QdrantClient') as mock_client:
            mock_client.return_value.get_collections.return_value = Mock(collections=[])
            mock_client.return_value.create_collection.return_value = None
            mock_client.return_value.upsert.return_value = None
            mock_client.return_value.search.return_value = []
            
            manager = SemanticStateManager()
            yield manager
    
    @pytest.mark.asyncio
    async def test_store_state(self, state_manager):
        """Test storing state with embeddings"""
        state_id = await state_manager.store_state(
            "User asked about account balance",
            {"balance": 1500.50},
            "api_result"
        )
        
        assert state_id is not None
        assert len(state_id) == 36  # UUID length
    
    @pytest.mark.asyncio
    async def test_query_relevant_state(self, state_manager):
        """Test querying relevant states"""
        # Mock search results
        mock_results = [
            Mock(
                id="test-id",
                score=0.95,
                payload={
                    "data": {"balance": 1500.50},
                    "description": "User asked about account balance",
                    "context_type": "api_result",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        ]
        
        with patch.object(state_manager.client, 'search', return_value=mock_results):
            results = await state_manager.query_relevant_state(
                "account balance information",
                limit=5
            )
            
            assert len(results) == 1
            assert results[0]["score"] == 0.95
            assert results[0]["data"]["balance"] == 1500.50
    
    @pytest.mark.asyncio
    async def test_get_execution_context(self, state_manager):
        """Test getting execution context"""
        with patch.object(state_manager, 'query_relevant_state', return_value=[]):
            context = await state_manager.get_execution_context("test query", 0)
            
            assert context["user_query"] == "test query"
            assert context["iteration"] == 0
            assert "past_executions" in context
            assert "api_results" in context
            assert "memory_context" in context


class TestToolManager:
    """Test tool management functionality"""
    
    @pytest.fixture
    async def tool_manager(self):
        """Create tool manager for testing"""
        mock_state_manager = AsyncMock()
        manager = ToolManager(mock_state_manager)
        yield manager
    
    @pytest.mark.asyncio
    async def test_load_api_spec(self, tool_manager):
        """Test loading API specification"""
        sample_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/test": {
                    "get": {
                        "summary": "Test endpoint",
                        "responses": {"200": {"description": "Success"}}
                    }
                }
            }
        }
        
        # Mock FastMCP
        with patch('tool_manager.FastMCP') as mock_fastmcp:
            mock_tool = Mock()
            mock_tool.name = "test_tool"
            mock_tool.description = "Test tool"
            mock_fastmcp.return_value.get_tools_for_route_map.return_value = [mock_tool]
            
            tools_loaded = await tool_manager.load_api_spec(sample_spec, "test_api")
            
            assert tools_loaded == 1
            assert "test_api_test_tool" in tool_manager.tools
    
    @pytest.mark.asyncio
    async def test_execute_tool(self, tool_manager):
        """Test tool execution"""
        # Mock tool
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.endpoint = "/test"
        mock_tool.method = "GET"
        mock_tool.base_url = "https://api.example.com"
        mock_tool.api_name = "test_api"
        
        tool_manager.tools["test_tool"] = mock_tool
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status.return_value = None
        
        with patch.object(tool_manager.http_client, 'request', return_value=mock_response):
            result = await tool_manager.execute_tool(
                tool_name="test_tool",
                params={"param1": "value1"}
            )
            
            assert result.success is True
            assert result.data == {"result": "success"}
            assert result.tool_name == "test_tool"
    
    def test_get_tool_context(self, tool_manager):
        """Test generating tool context for LLM"""
        # Mock tools
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool description"
        mock_tool.endpoint = "/test"
        mock_tool.method = "GET"
        mock_tool.api_name = "test_api"
        mock_tool.required_params = ["param1"]
        
        tool_manager.tools["test_tool"] = mock_tool
        
        context = tool_manager.get_tool_context()
        
        assert "Test Api API" in context
        assert "test_tool" in context
        assert "Test tool description" in context
        assert "GET /test" in context


class TestAdaptiveOrchestrator:
    """Test adaptive orchestration functionality"""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator for testing"""
        mock_state_manager = AsyncMock()
        mock_tool_manager = AsyncMock()
        
        orchestrator = AdaptiveOrchestrator(
            semantic_state_manager=mock_state_manager,
            tool_manager=mock_tool_manager,
            max_iterations=3
        )
        
        # Mock LLM responses
        orchestrator._get_openai_response = AsyncMock(return_value=json.dumps({
            "action": "complete",
            "reasoning": "Test reasoning",
            "final_answer": "Test answer"
        }))
        
        yield orchestrator
    
    @pytest.mark.asyncio
    async def test_execute_query(self, orchestrator):
        """Test query execution"""
        # Mock context
        mock_context = {
            "user_query": "test query",
            "iteration": 0,
            "past_executions": [],
            "api_results": [],
            "memory_context": [],
            "total_context_items": 0
        }
        
        orchestrator.semantic_state.get_execution_context = AsyncMock(return_value=mock_context)
        orchestrator.semantic_state.store_execution_step = AsyncMock()
        orchestrator.semantic_state.store_state = AsyncMock()
        
        result = await orchestrator.execute_query("test query")
        
        assert result.query == "test query"
        assert result.success is True
        assert result.final_answer == "Test answer"
        assert len(result.execution_steps) == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_streaming(self, orchestrator):
        """Test streaming execution"""
        # Mock context
        mock_context = {
            "user_query": "test query",
            "iteration": 0,
            "past_executions": [],
            "api_results": [],
            "memory_context": [],
            "total_context_items": 0
        }
        
        orchestrator.semantic_state.get_execution_context = AsyncMock(return_value=mock_context)
        orchestrator.semantic_state.store_execution_step = AsyncMock()
        
        updates = []
        async for update in orchestrator.execute_with_streaming("test query"):
            updates.append(update)
        
        assert len(updates) > 0
        assert updates[0]["type"] == "status"
        assert any(update["type"] == "completed" for update in updates)
    
    def test_parse_llm_response(self, orchestrator):
        """Test LLM response parsing"""
        # Test JSON response
        json_response = json.dumps({
            "action": "use_tool",
            "reasoning": "Need to get data",
            "tool_name": "test_tool",
            "params": {"param1": "value1"}
        })
        
        result = orchestrator._parse_llm_response(json_response)
        
        assert result["action"] == "use_tool"
        assert result["tool_name"] == "test_tool"
        assert result["params"]["param1"] == "value1"
        
        # Test fallback parsing
        text_response = "I need to complete this task by getting the data."
        result = orchestrator._parse_llm_response(text_response)
        
        assert result["action"] == "complete"
        assert "complete" in result["final_answer"]


class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_orchestration(self):
        """Test complete end-to-end orchestration"""
        # Mock all external dependencies
        with patch('semantic_state_manager.QdrantClient'), \
             patch('adaptive_orchestrator.openai.AsyncOpenAI'), \
             patch('tool_manager.FastMCP'):
            
            # Initialize components
            state_manager = SemanticStateManager()
            tool_manager = ToolManager(state_manager)
            orchestrator = AdaptiveOrchestrator(
                semantic_state_manager=state_manager,
                tool_manager=tool_manager
            )
            
            # Mock LLM to return completion
            orchestrator._get_openai_response = AsyncMock(return_value=json.dumps({
                "action": "complete",
                "reasoning": "Integration test",
                "final_answer": "Integration test completed successfully"
            }))
            
            # Execute test query
            result = await orchestrator.execute_query("Integration test query")
            
            assert result.success is True
            assert "Integration test completed successfully" in result.final_answer


# Performance tests
class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self):
        """Test handling multiple concurrent executions"""
        with patch('semantic_state_manager.QdrantClient'), \
             patch('adaptive_orchestrator.openai.AsyncOpenAI'):
            
            state_manager = SemanticStateManager()
            tool_manager = ToolManager(state_manager)
            orchestrator = AdaptiveOrchestrator(
                semantic_state_manager=state_manager,
                tool_manager=tool_manager
            )
            
            # Mock LLM responses
            orchestrator._get_openai_response = AsyncMock(return_value=json.dumps({
                "action": "complete",
                "reasoning": "Concurrent test",
                "final_answer": "Concurrent test completed"
            }))
            
            # Run multiple concurrent executions
            tasks = [
                orchestrator.execute_query(f"Concurrent test query {i}")
                for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 5
            assert all(result.success for result in results)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])