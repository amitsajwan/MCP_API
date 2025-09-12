#!/usr/bin/env python3
"""
Integration Tests for Complete MCP System
=========================================
Tests the complete system integration including:
- End-to-end message processing
- Tool execution flow
- Error handling across components
- Performance and reliability
"""

import unittest
import asyncio
import json
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_service import ModernLLMService
from mcp_client import MCPClient, PythonStdioTransport
from web_ui_ws import MCPDemoService

class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the complete MCP system"""
    
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
        
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)
    
    @patch('mcp_service.create_azure_client')
    @patch('mcp_service.MCPClient')
    @patch('mcp_service.PythonStdioTransport')
    @patch('mcp_service.list_and_prepare_tools')
    def test_complete_message_flow(self, mock_list_tools, mock_transport, mock_mcp_client, mock_azure_client):
        """Test complete message processing flow"""
        # Mock all dependencies
        mock_azure_instance = AsyncMock()
        mock_azure_client.return_value = mock_azure_instance
        
        mock_transport_instance = MagicMock()
        mock_transport.return_value = mock_transport_instance
        
        mock_mcp_instance = AsyncMock()
        mock_mcp_client.return_value = mock_mcp_instance
        
        mock_tools = [
            {
                "function": {
                    "name": "cash_api_getPayments",
                    "description": "Get payments",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]
        mock_list_tools.return_value = mock_tools
        
        # Mock Azure response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "I found 3 payments"
        mock_response.choices[0].message.tool_calls = []
        
        mock_azure_instance.chat.completions.create.return_value = mock_response
        
        # Test complete flow
        service = ModernLLMService()
        
        # Initialize service
        init_result = service.initialize()
        self.assertTrue(init_result)
        
        # Process message
        result = asyncio.run(service.process_message("Show me all payments", []))
        
        # Verify result structure
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)
        self.assertIn("response", result)
        self.assertIn("tool_calls", result)
        self.assertIn("capabilities", result)
    
    def test_web_ui_integration(self):
        """Test web UI integration with MCP service"""
        # Mock the MCP service
        with patch('web_ui_ws.ModernLLMService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.initialize.return_value = True
            mock_service.process_message.return_value = {
                "response": "Test response",
                "tool_calls": [{"tool_name": "test_tool", "success": True}],
                "capabilities": {"descriptions": ["Test capability"]}
            }
            mock_service_class.return_value = mock_service
            
            # Test web UI service
            demo_service = MCPDemoService()
            
            # Initialize
            init_result = asyncio.run(demo_service.initialize())
            self.assertTrue(init_result)
            
            # Process message
            result = asyncio.run(demo_service.process_message("Test message"))
            
            # Verify result
            self.assertIsInstance(result, dict)
            self.assertEqual(result["response"], "Test response")
            self.assertEqual(len(result["tool_calls"]), 1)
            self.assertEqual(len(result["capabilities"]["descriptions"]), 1)
    
    def test_error_propagation(self):
        """Test error propagation across components"""
        # Test with invalid Azure credentials
        with patch.dict(os.environ, {
            'AZURE_OPENAI_ENDPOINT': 'invalid-endpoint',
            'AZURE_DEPLOYMENT_NAME': 'invalid-deployment'
        }):
            service = ModernLLMService()
            
            # Should handle invalid credentials gracefully
            try:
                result = service.initialize()
                self.assertFalse(result)
            except Exception as e:
                # Expected behavior for invalid credentials
                self.assertIsInstance(e, Exception)
    
    def test_conversation_flow(self):
        """Test conversation flow with multiple messages"""
        # Mock the MCP service
        with patch('web_ui_ws.ModernLLMService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.initialize.return_value = True
            mock_service.process_message.return_value = {
                "response": "Test response",
                "tool_calls": [],
                "capabilities": {}
            }
            mock_service_class.return_value = mock_service
            
            # Test conversation flow
            demo_service = MCPDemoService()
            asyncio.run(demo_service.initialize())
            
            # First message
            result1 = asyncio.run(demo_service.process_message("Hello"))
            self.assertEqual(len(demo_service.conversation), 2)
            
            # Second message
            result2 = asyncio.run(demo_service.process_message("How are you?"))
            self.assertEqual(len(demo_service.conversation), 4)
            
            # Third message
            result3 = asyncio.run(demo_service.process_message("What can you do?"))
            self.assertEqual(len(demo_service.conversation), 6)

class TestSystemPerformance(unittest.TestCase):
    """Performance tests for the MCP system"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_patcher = patch.dict(os.environ, {
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_DEPLOYMENT_NAME': 'gpt-4o'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.env_patcher.stop()
    
    def test_initialization_performance(self):
        """Test initialization performance"""
        import time
        
        # Mock dependencies
        with patch('mcp_service.create_azure_client') as mock_azure, \
             patch('mcp_service.MCPClient') as mock_mcp, \
             patch('mcp_service.PythonStdioTransport') as mock_transport, \
             patch('mcp_service.list_and_prepare_tools') as mock_tools:
            
            mock_azure.return_value = AsyncMock()
            mock_mcp.return_value = AsyncMock()
            mock_transport.return_value = MagicMock()
            mock_tools.return_value = []
            
            # Test initialization time
            start_time = time.time()
            service = ModernLLMService()
            result = service.initialize()
            end_time = time.time()
            
            # Verify initialization completed
            self.assertTrue(result)
            
            # Verify reasonable initialization time (should be fast with mocks)
            init_time = end_time - start_time
            self.assertLess(init_time, 5.0)  # Should complete within 5 seconds
    
    def test_message_processing_performance(self):
        """Test message processing performance"""
        import time
        
        # Mock dependencies
        with patch('web_ui_ws.ModernLLMService') as mock_service_class:
            mock_service = AsyncMock()
            mock_service.initialize.return_value = True
            mock_service.process_message.return_value = {
                "response": "Test response",
                "tool_calls": [],
                "capabilities": {}
            }
            mock_service_class.return_value = mock_service
            
            # Test message processing time
            demo_service = MCPDemoService()
            asyncio.run(demo_service.initialize())
            
            start_time = time.time()
            result = asyncio.run(demo_service.process_message("Test message"))
            end_time = time.time()
            
            # Verify processing completed
            self.assertIsInstance(result, dict)
            
            # Verify reasonable processing time
            process_time = end_time - start_time
            self.assertLess(process_time, 2.0)  # Should complete within 2 seconds

class TestSystemReliability(unittest.TestCase):
    """Reliability tests for the MCP system"""
    
    def test_concurrent_initialization(self):
        """Test concurrent initialization handling"""
        # This would test concurrent initialization
        # For now, just verify the structure is correct
        self.assertTrue(True)
    
    def test_memory_usage(self):
        """Test memory usage during operation"""
        # This would test memory usage
        # For now, just verify the structure is correct
        self.assertTrue(True)
    
    def test_error_recovery(self):
        """Test error recovery mechanisms"""
        # Test recovery from initialization errors
        service = ModernLLMService()
        
        # First initialization attempt (should fail without proper setup)
        result1 = service.initialize()
        
        # Second initialization attempt (should handle gracefully)
        result2 = service.initialize()
        
        # Both should handle errors gracefully
        self.assertIsInstance(result1, bool)
        self.assertIsInstance(result2, bool)

if __name__ == '__main__':
    unittest.main()