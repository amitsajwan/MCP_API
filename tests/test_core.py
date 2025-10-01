"""
Tests for core modules
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from core import CacheManager, UseCaseManager, BotManager, MCPToolsManager


class TestCacheManager:
    """Test CacheManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.cache_manager = CacheManager()
    
    def test_set_get_workflow_cache(self):
        """Test workflow cache set/get"""
        workflow_id = "test_workflow"
        data = {"test": "data"}
        
        self.cache_manager.set_workflow_cache(workflow_id, data)
        result = self.cache_manager.get_workflow_cache(workflow_id)
        
        assert result == data
    
    def test_set_get_user_cache(self):
        """Test user cache set/get"""
        user_id = "test_user"
        query = "test query"
        data = {"response": "test response"}
        
        self.cache_manager.set_user_cache(user_id, query, data)
        result = self.cache_manager.get_user_cache(user_id, query)
        
        assert result == data
    
    def test_set_get_use_case_cache(self):
        """Test use case cache set/get"""
        use_case_id = "test_case"
        parameters = {"param1": "value1"}
        result = {"success": True}
        
        self.cache_manager.set_use_case_cache(use_case_id, parameters, result)
        cached_result = self.cache_manager.get_use_case_cache(use_case_id, parameters)
        
        assert cached_result == result
    
    def test_clear_cache(self):
        """Test cache clearing"""
        self.cache_manager.set_workflow_cache("test", {"data": "test"})
        self.cache_manager.clear_cache("workflow")
        
        result = self.cache_manager.get_workflow_cache("test")
        assert result is None
    
    def test_cache_stats(self):
        """Test cache statistics"""
        self.cache_manager.set_workflow_cache("test1", {"data": "test1"})
        self.cache_manager.set_workflow_cache("test2", {"data": "test2"})
        
        stats = self.cache_manager.get_cache_stats()
        assert stats["workflow_cache_size"] == 2


class TestUseCaseManager:
    """Test UseCaseManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.use_case_manager = UseCaseManager()
    
    def test_get_all_use_cases(self):
        """Test getting all use cases"""
        use_cases = self.use_case_manager.get_all_use_cases()
        assert len(use_cases) > 0
    
    def test_get_use_case(self):
        """Test getting specific use case"""
        use_case = self.use_case_manager.get_use_case("1")
        assert use_case is not None
        assert use_case["id"] == "1"
    
    def test_get_categories(self):
        """Test getting categories"""
        categories = self.use_case_manager.get_categories()
        assert len(categories) > 0
    
    def test_search_use_cases(self):
        """Test searching use cases"""
        results = self.use_case_manager.search_use_cases("authentication")
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_execute_use_case(self):
        """Test use case execution"""
        parameters = {"user_id": "123", "account_id": "ACC-001"}
        result = await self.use_case_manager.execute_use_case("1", parameters)
        
        assert result["success"] is True
        assert "use_case" in result


class TestBotManager:
    """Test BotManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.bot_manager = BotManager()
    
    @pytest.mark.asyncio
    async def test_process_query(self):
        """Test query processing"""
        result = await self.bot_manager.process_query("test query")
        
        assert "response" in result
        assert "session_id" in result
    
    def test_get_conversation_history(self):
        """Test getting conversation history"""
        session_id = "test_session"
        history = self.bot_manager.get_conversation_history(session_id)
        assert isinstance(history, list)
    
    def test_clear_conversation(self):
        """Test clearing conversation"""
        session_id = "test_session"
        self.bot_manager.clear_conversation(session_id)
        # Should not raise exception
    
    def test_get_statistics(self):
        """Test getting statistics"""
        stats = self.bot_manager.get_all_statistics()
        assert "total_sessions" in stats
        assert "total_messages" in stats


class TestMCPToolsManager:
    """Test MCPToolsManager functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.tools_manager = MCPToolsManager()
    
    def test_get_all_tools(self):
        """Test getting all tools"""
        tools = self.tools_manager.get_all_tools()
        assert len(tools) > 0
    
    def test_get_tool(self):
        """Test getting specific tool"""
        tool = self.tools_manager.get_tool("login")
        assert tool is not None
        assert tool["name"] == "login"
    
    def test_get_categories(self):
        """Test getting categories"""
        categories = self.tools_manager.get_categories()
        assert len(categories) > 0
    
    def test_search_tools(self):
        """Test searching tools"""
        results = self.tools_manager.search_tools("login")
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_execute_tool(self):
        """Test tool execution"""
        parameters = {"username": "test", "password": "test"}
        result = await self.tools_manager.execute_tool("login", parameters)
        
        assert "tool" in result
        assert "success" in result
    
    def test_get_statistics(self):
        """Test getting statistics"""
        stats = self.tools_manager.get_tool_statistics()
        assert "total_executions" in stats


if __name__ == "__main__":
    pytest.main([__file__])
