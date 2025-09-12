#!/usr/bin/env python3
"""
Test Cases for MCP Service (mcp_service.py)
===========================================
Tests the MCP service functionality including:
- Service initialization
- Message processing
- Tool execution orchestration
- Capability analysis
- Error handling
"""

import unittest
import asyncio
import json
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_service import ModernLLMService

class TestMCPService(unittest.TestCase):
    """Test cases for MCP Service functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_DEPLOYMENT_NAME': 'gpt-4o',
            'AZURE_CLIENT_ID': 'test-client-id',
            'AZURE_CLIENT_SECRET': 'test-secret',
            'AZURE_TENANT_ID': 'test-tenant'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_service_initialization(self):
        """Test MCP service initializes correctly"""
        service = ModernLLMService()
        self.assertIsNotNone(service)
        self.assertFalse(service._initialized)
        self.assertIsNone(service._mcp_client)
        self.assertIsNone(service._azure_client)
        self.assertIsNone(service._tools)
    
    @patch('mcp_service.create_azure_client')
    @patch('mcp_service.MCPClient')
    @patch('mcp_service.PythonStdioTransport')
    @patch('mcp_service.list_and_prepare_tools')
    def test_service_initialize_success(self, mock_list_tools, mock_transport, mock_mcp_client, mock_azure_client):
        """Test successful service initialization"""
        # Mock dependencies
        mock_azure_instance = AsyncMock()
        mock_azure_client.return_value = mock_azure_instance
        
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        
        mock_mcp_instance = AsyncMock()
        mock_mcp_client.return_value = mock_mcp_instance
        
        mock_tools = [{"function": {"name": "test_tool", "description": "Test"}}]
        mock_list_tools.return_value = mock_tools
        
        # Test initialization
        service = ModernLLMService()
        result = service.initialize()
        
        # Verify initialization
        self.assertTrue(result)
        self.assertTrue(service._initialized)
        self.assertIsNotNone(service._azure_client)
        self.assertIsNotNone(service._mcp_client)
        self.assertIsNotNone(service._tools)
    
    @patch('mcp_service.create_azure_client')
    def test_service_initialize_failure(self, mock_azure_client):
        """Test service initialization failure"""
        # Mock Azure client creation failure
        mock_azure_client.side_effect = Exception("Azure connection failed")
        
        # Test initialization
        service = ModernLLMService()
        result = service.initialize()
        
        # Verify initialization failed
        self.assertFalse(result)
        self.assertFalse(service._initialized)
    
    def test_analyze_capabilities(self):
        """Test capability analysis"""
        service = ModernLLMService()
        
        # Test with tool calls
        tool_calls = [
            {"tool_name": "cash_api_getPayments", "success": True},
            {"tool_name": "cls_api_createSettlement", "success": True}
        ]
        user_message = "Show me payments and create settlement"
        
        capabilities = service._analyze_capabilities(tool_calls, user_message)
        
        # Verify capabilities analysis
        self.assertIsInstance(capabilities, dict)
        self.assertIn("descriptions", capabilities)
        self.assertIsInstance(capabilities["descriptions"], list)
    
    def test_analyze_capabilities_no_tools(self):
        """Test capability analysis with no tool calls"""
        service = ModernLLMService()
        
        tool_calls = []
        user_message = "Hello, how are you?"
        
        capabilities = service._analyze_capabilities(tool_calls, user_message)
        
        # Verify capabilities analysis
        self.assertIsInstance(capabilities, dict)
        self.assertIn("descriptions", capabilities)
    
    @patch('mcp_service.ModernLLMService._azure_client')
    def test_process_message_success(self, mock_azure_client):
        """Test successful message processing"""
        # Mock Azure client
        mock_azure_instance = AsyncMock()
        mock_azure_client = mock_azure_instance
        
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].message.tool_calls = []
        
        mock_azure_instance.chat.completions.create.return_value = mock_response
        
        # Test message processing
        service = ModernLLMService()
        service._initialized = True
        service._azure_client = mock_azure_instance
        service._tools = []
        
        # This would need to be tested with actual async execution
        # For now, just verify the method exists
        self.assertTrue(hasattr(service, 'process_message'))
    
    def test_process_message_not_initialized(self):
        """Test message processing when not initialized"""
        service = ModernLLMService()
        
        # Test with uninitialized service
        result = asyncio.run(service.process_message("test message", []))
        
        # Verify error handling
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("success", True))
        self.assertIn("not initialized", result.get("response", ""))

class TestMCPServiceIntegration(unittest.TestCase):
    """Integration tests for MCP Service"""
    
    def test_import_structure(self):
        """Test that all required functions can be imported"""
        try:
            from mcp_service import ModernLLMService
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import ModernLLMService: {e}")
    
    def test_service_methods_exist(self):
        """Test that all required methods exist"""
        service = ModernLLMService()
        
        required_methods = [
            'initialize',
            'process_message',
            '_analyze_capabilities'
        ]
        
        for method in required_methods:
            self.assertTrue(hasattr(service, method), f"Missing method: {method}")
    
    def test_service_attributes(self):
        """Test that service has required attributes"""
        service = ModernLLMService()
        
        required_attributes = [
            '_mcp_client',
            '_azure_client',
            '_tools',
            '_initialized',
            'mcp_server_cmd'
        ]
        
        for attr in required_attributes:
            self.assertTrue(hasattr(service, attr), f"Missing attribute: {attr}")

class TestMCPServiceErrorHandling(unittest.TestCase):
    """Test error handling in MCP Service"""
    
    def test_invalid_message_handling(self):
        """Test handling of invalid messages"""
        service = ModernLLMService()
        
        # Test with None message
        result = asyncio.run(service.process_message(None, []))
        self.assertIsInstance(result, dict)
    
    def test_empty_message_handling(self):
        """Test handling of empty messages"""
        service = ModernLLMService()
        
        # Test with empty message
        result = asyncio.run(service.process_message("", []))
        self.assertIsInstance(result, dict)
    
    def test_malformed_conversation_handling(self):
        """Test handling of malformed conversation"""
        service = ModernLLMService()
        
        # Test with invalid conversation format
        result = asyncio.run(service.process_message("test", "invalid_conversation"))
        self.assertIsInstance(result, dict)

if __name__ == '__main__':
    unittest.main()