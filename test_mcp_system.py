"""
Comprehensive MCP System Tests - Model Context Protocol Testing
Tests MCP server, client, and web bridge functionality
"""

import asyncio
import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Import MCP components
from mcp_server import IntelligentOrchestrationMCPServer
from mcp_client import IntelligentOrchestrationMCPClient, MCPOrchestrationManager
from web_mcp_bridge import WebMCPBridge, WebMCPEndpoint


class TestMCPServer:
    """Test MCP server functionality"""
    
    @pytest.fixture
    async def mcp_server(self):
        """Create MCP server for testing"""
        with patch('semantic_state_manager.QdrantClient'), \
             patch('tool_manager.FastMCP'):
            server = IntelligentOrchestrationMCPServer()
            yield server
    
    @pytest.mark.asyncio
    async def test_server_initialization(self, mcp_server):
        """Test MCP server initialization"""
        assert mcp_server.server is not None
        assert mcp_server.semantic_state is not None
        assert mcp_server.tool_manager is not None
        assert len(mcp_server.active_executions) == 0
    
    @pytest.mark.asyncio
    async def test_list_tools(self, mcp_server):
        """Test listing available tools"""
        # Mock the list_tools handler
        tools_response = await mcp_server.server._handlers['list_tools']()
        
        tool_names = [tool.name for tool in tools_response]
        expected_tools = [
            "execute_query", "load_api_spec", "query_semantic_state",
            "get_execution_status", "list_available_tools", "get_system_stats"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_execute_query_tool(self, mcp_server):
        """Test execute query tool execution"""
        # Mock orchestrator
        mock_result = Mock()
        mock_result.success = True
        mock_result.final_answer = "Test answer"
        mock_result.total_iterations = 1
        mock_result.execution_time = 1.5
        mock_result.execution_steps = []
        
        with patch('adaptive_orchestrator.AdaptiveOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.execute_query = AsyncMock(return_value=mock_result)
            mock_orchestrator_class.return_value = mock_orchestrator
            
            # Execute tool
            result = await mcp_server._handle_execute_query({
                "query": "test query",
                "max_iterations": 5
            })
            
            assert len(result) == 1
            assert result[0].type == "text"
            
            # Parse result
            result_data = json.loads(result[0].text)
            assert result_data["success"] is True
            assert result_data["final_answer"] == "Test answer"
    
    @pytest.mark.asyncio
    async def test_load_api_spec_tool(self, mcp_server):
        """Test load API spec tool execution"""
        # Mock tool manager
        mcp_server.tool_manager.load_api_spec = AsyncMock(return_value=3)
        
        api_spec = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "1.0.0"},
            "paths": {}
        }
        
        result = await mcp_server._handle_load_api_spec({
            "api_spec": api_spec,
            "api_name": "test_api"
        })
        
        assert len(result) == 1
        result_data = json.loads(result[0].text)
        assert result_data["success"] is True
        assert result_data["tools_loaded"] == 3
    
    @pytest.mark.asyncio
    async def test_query_semantic_state_tool(self, mcp_server):
        """Test semantic state query tool execution"""
        # Mock semantic state manager
        mock_results = [
            {
                "id": "test-id",
                "score": 0.95,
                "data": {"test": "data"},
                "description": "Test state",
                "context_type": "execution_result"
            }
        ]
        mcp_server.semantic_state.query_relevant_state = AsyncMock(return_value=mock_results)
        
        result = await mcp_server._handle_query_semantic_state({
            "query": "test query",
            "limit": 5
        })
        
        assert len(result) == 1
        result_data = json.loads(result[0].text)
        assert result_data["results_count"] == 1
        assert len(result_data["results"]) == 1


class TestMCPClient:
    """Test MCP client functionality"""
    
    @pytest.fixture
    async def mcp_client(self):
        """Create MCP client for testing"""
        with patch('subprocess.Popen'), \
             patch('mcp.client.stdio.stdio_client') as mock_stdio_client:
            
            # Mock client session
            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.call_tool = AsyncMock()
            mock_session.list_tools = AsyncMock()
            mock_session.list_resources = AsyncMock()
            mock_session.read_resource = AsyncMock()
            
            mock_stdio_client.return_value = mock_session
            
            client = IntelligentOrchestrationMCPClient()
            client.session = mock_session
            client.connected = True
            
            yield client
    
    @pytest.mark.asyncio
    async def test_client_connection(self, mcp_client):
        """Test client connection"""
        # Mock successful connection
        mcp_client.session.list_tools.return_value = Mock(tools=[])
        mcp_client.session.list_resources.return_value = Mock(resources=[])
        
        success = await mcp_client.connect()
        
        assert success is True
        assert mcp_client.connected is True
        mcp_client.session.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_query(self, mcp_client):
        """Test query execution via client"""
        # Mock tool response
        mock_content = Mock()
        mock_content.text = json.dumps({
            "success": True,
            "final_answer": "Test answer",
            "total_iterations": 1
        })
        mock_result = Mock()
        mock_result.content = [mock_content]
        
        mcp_client.session.call_tool.return_value = mock_result
        
        result = await mcp_client.execute_query("test query")
        
        assert result["success"] is True
        assert result["final_answer"] == "Test answer"
        mcp_client.session.call_tool.assert_called_once_with(
            "execute_query",
            {"query": "test query", "max_iterations": 20}
        )
    
    @pytest.mark.asyncio
    async def test_load_api_spec(self, mcp_client):
        """Test API spec loading via client"""
        # Mock tool response
        mock_content = Mock()
        mock_content.text = json.dumps({
            "success": True,
            "tools_loaded": 3
        })
        mock_result = Mock()
        mock_result.content = [mock_content]
        
        mcp_client.session.call_tool.return_value = mock_result
        
        api_spec = {"openapi": "3.0.0", "info": {"title": "Test API"}}
        result = await mcp_client.load_api_spec(api_spec, "test_api")
        
        assert result["success"] is True
        assert result["tools_loaded"] == 3
    
    @pytest.mark.asyncio
    async def test_health_check(self, mcp_client):
        """Test client health check"""
        # Mock system stats
        mock_content = Mock()
        mock_content.text = json.dumps({
            "semantic_state": {"total_points": 10},
            "tools": {"total_tools": 5}
        })
        mock_result = Mock()
        mock_result.content = [mock_content]
        
        mcp_client.session.call_tool.return_value = mock_result
        
        health = await mcp_client.health_check()
        
        assert health["connected"] is True
        assert "system_stats" in health


class TestMCPOrchestrationManager:
    """Test high-level MCP orchestration manager"""
    
    @pytest.fixture
    async def orchestration_manager(self):
        """Create orchestration manager for testing"""
        with patch('mcp_client.IntelligentOrchestrationMCPClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            mock_client.execute_query = AsyncMock()
            mock_client.load_api_spec = AsyncMock()
            mock_client.query_semantic_state = AsyncMock()
            mock_client.health_check = AsyncMock()
            
            mock_client_class.return_value = mock_client
            
            manager = MCPOrchestrationManager()
            manager.client = mock_client
            
            yield manager
    
    @pytest.mark.asyncio
    async def test_context_manager(self, orchestration_manager):
        """Test async context manager functionality"""
        async with orchestration_manager as manager:
            assert manager is not None
            manager.client.connect.assert_called_once()
        
        manager.client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ask_method(self, orchestration_manager):
        """Test ask method"""
        # Mock query execution
        mock_result = {
            "success": True,
            "final_answer": "Test answer"
        }
        orchestration_manager.client.execute_query.return_value = mock_result
        
        answer = await orchestration_manager.ask("test question")
        
        assert answer == "Test answer"
        orchestration_manager.client.execute_query.assert_called_once_with("test question")
    
    @pytest.mark.asyncio
    async def test_add_api_method(self, orchestration_manager):
        """Test add API method"""
        # Mock API loading
        mock_result = {
            "success": True,
            "tools_loaded": 3
        }
        orchestration_manager.client.load_api_spec.return_value = mock_result
        
        api_spec = {"openapi": "3.0.0"}
        success = await orchestration_manager.add_api(api_spec, "test_api")
        
        assert success is True
        orchestration_manager.client.load_api_spec.assert_called_once_with(api_spec, "test_api")


class TestWebMCPBridge:
    """Test Web MCP bridge functionality"""
    
    @pytest.fixture
    async def web_bridge(self):
        """Create web MCP bridge for testing"""
        with patch('mcp_client.IntelligentOrchestrationMCPClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect = AsyncMock(return_value=True)
            mock_client.disconnect = AsyncMock()
            mock_client.connected = True
            mock_client.execute_query = AsyncMock()
            mock_client.load_api_spec = AsyncMock()
            mock_client.query_semantic_state = AsyncMock()
            mock_client.list_available_tools = AsyncMock()
            mock_client.get_system_stats = AsyncMock()
            mock_client.health_check = AsyncMock()
            
            mock_client_class.return_value = mock_client
            
            bridge = WebMCPBridge()
            bridge.mcp_client = mock_client
            
            yield bridge
    
    @pytest.fixture
    async def mock_websocket(self):
        """Create mock WebSocket for testing"""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_json = AsyncMock()
        websocket.receive_json = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, web_bridge, mock_websocket):
        """Test WebSocket connection"""
        client_id = "test-client"
        
        await web_bridge.connect_websocket(mock_websocket, client_id)
        
        assert client_id in web_bridge.active_connections
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_execute_query(self, web_bridge, mock_websocket):
        """Test execute query message handling"""
        client_id = "test-client"
        
        # Mock query execution result
        mock_result = {
            "success": True,
            "final_answer": "Test answer"
        }
        web_bridge.mcp_client.execute_query.return_value = mock_result
        
        message = {
            "type": "mcp_execute_query",
            "query": "test query",
            "max_iterations": 10
        }
        
        await web_bridge.handle_message(mock_websocket, client_id, message)
        
        # Should send execution started and completed messages
        assert mock_websocket.send_json.call_count >= 2
        web_bridge.mcp_client.execute_query.assert_called_once_with("test query", 10)
    
    @pytest.mark.asyncio
    async def test_handle_load_api(self, web_bridge, mock_websocket):
        """Test load API message handling"""
        client_id = "test-client"
        
        # Mock API loading result
        mock_result = {
            "success": True,
            "tools_loaded": 3
        }
        web_bridge.mcp_client.load_api_spec.return_value = mock_result
        
        message = {
            "type": "mcp_load_api",
            "api_spec": {"openapi": "3.0.0"},
            "api_name": "test_api"
        }
        
        await web_bridge.handle_message(mock_websocket, client_id, message)
        
        mock_websocket.send_json.assert_called()
        web_bridge.mcp_client.load_api_spec.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_query_state(self, web_bridge, mock_websocket):
        """Test semantic state query message handling"""
        client_id = "test-client"
        
        # Mock semantic query result
        mock_result = {
            "query": "test query",
            "results_count": 2,
            "results": []
        }
        web_bridge.mcp_client.query_semantic_state.return_value = mock_result
        
        message = {
            "type": "mcp_query_state",
            "query": "test query",
            "limit": 5
        }
        
        await web_bridge.handle_message(mock_websocket, client_id, message)
        
        mock_websocket.send_json.assert_called()
        web_bridge.mcp_client.query_semantic_state.assert_called_once_with("test query", None, 5)


class TestMCPIntegration:
    """Integration tests for MCP components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_mcp_communication(self):
        """Test complete MCP communication flow"""
        # This would test the full MCP protocol flow
        # For now, we'll test the components work together
        
        with patch('semantic_state_manager.QdrantClient'), \
             patch('tool_manager.FastMCP'), \
             patch('subprocess.Popen'), \
             patch('mcp.client.stdio.stdio_client'):
            
            # Test that all components can be instantiated together
            server = IntelligentOrchestrationMCPServer()
            client = IntelligentOrchestrationMCPClient()
            bridge = WebMCPBridge()
            
            assert server is not None
            assert client is not None
            assert bridge is not None
    
    @pytest.mark.asyncio
    async def test_mcp_orchestration_manager_integration(self):
        """Test MCP orchestration manager integration"""
        with patch('mcp_client.IntelligentOrchestrationMCPClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            mock_client.execute_query = AsyncMock(return_value={
                "success": True,
                "final_answer": "Integration test answer"
            })
            
            mock_client_class.return_value = mock_client
            
            async with MCPOrchestrationManager() as manager:
                answer = await manager.ask("Integration test question")
                assert "Integration test answer" in answer


# Performance tests for MCP
class TestMCPPerformance:
    """Performance tests for MCP components"""
    
    @pytest.mark.asyncio
    async def test_concurrent_mcp_requests(self):
        """Test handling concurrent MCP requests"""
        with patch('mcp_client.IntelligentOrchestrationMCPClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect = AsyncMock()
            mock_client.disconnect = AsyncMock()
            mock_client.execute_query = AsyncMock(return_value={
                "success": True,
                "final_answer": "Concurrent test answer"
            })
            
            mock_client_class.return_value = mock_client
            
            async with MCPOrchestrationManager() as manager:
                # Run multiple concurrent requests
                tasks = [
                    manager.ask(f"Concurrent test question {i}")
                    for i in range(5)
                ]
                
                results = await asyncio.gather(*tasks)
                
                assert len(results) == 5
                assert all("Concurrent test answer" in result for result in results)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])