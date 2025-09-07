#!/usr/bin/env python3
"""
API Diagnostics Script
Helps diagnose external API connection and authentication issues
"""

import os
import sys
import json
import requests
import logging
from typing import Dict, Any, Optional
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_diagnostics")

class APIDiagnostics:
    """Diagnostic tools for API troubleshooting."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MCP-API-Diagnostics/1.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def test_mcp_server(self) -> Dict[str, Any]:
        """Test MCP server connectivity and tools."""
        results = {}
        
        try:
            # Test health endpoint
            response = self.session.get("http://localhost:9000/health", timeout=10)
            results['health'] = {
                'status': response.status_code,
                'data': response.json() if response.status_code == 200 else response.text
            }
        except Exception as e:
            results['health'] = {'error': str(e)}
        
        try:
            # Test tools endpoint
            response = self.session.get("http://localhost:9000/tools", timeout=10)
            if response.status_code == 200:
                tools_data = response.json()
                results['tools'] = {
                    'status': 200,
                    'count': len(tools_data.get('tools', [])),
                    'tools': [t.get('name') for t in tools_data.get('tools', [])[:10]]
                }
            else:
                results['tools'] = {'status': response.status_code, 'error': response.text}
        except Exception as e:
            results['tools'] = {'error': str(e)}
        
        return results
    
    def test_authentication(self, username: str = None, password: str = None) -> Dict[str, Any]:
        """Test authentication with MCP server."""
        results = {}
        
        # Use environment variables if not provided
        username = username or os.getenv('DEFAULT_USERNAME')
        password = password or os.getenv('DEFAULT_PASSWORD')
        
        if not username or not password:
            return {'error': 'No credentials provided. Set DEFAULT_USERNAME and DEFAULT_PASSWORD'}
        
        try:
            # Test set_credentials
            payload = {
                'name': 'set_credentials',
                'arguments': {
                    'username': username,
                    'password': password
                }
            }
            
            response = self.session.post("http://localhost:9000/call_tool", json=payload, timeout=10)
            results['set_credentials'] = {
                'status': response.status_code,
                'data': response.json() if response.status_code == 200 else response.text
            }
            
            # Test perform_login
            if response.status_code == 200:
                payload = {
                    'name': 'perform_login',
                    'arguments': {}
                }
                
                response = self.session.post("http://localhost:9000/call_tool", json=payload, timeout=10)
                results['perform_login'] = {
                    'status': response.status_code,
                    'data': response.json() if response.status_code == 200 else response.text
                }
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def test_sample_api_call(self, tool_name: str = None) -> Dict[str, Any]:
        """Test a sample API call to diagnose external API issues."""
        results = {}
        
        try:
            # Get available tools first
            response = self.session.get("http://localhost:9000/tools", timeout=10)
            if response.status_code != 200:
                return {'error': 'Cannot retrieve tools list'}
            
            tools_data = response.json()
            tools = tools_data.get('tools', [])
            
            if not tools:
                return {'error': 'No tools available'}
            
            # Use provided tool or first available tool
            if tool_name:
                tool = next((t for t in tools if t.get('name') == tool_name), None)
                if not tool:
                    return {'error': f'Tool {tool_name} not found'}
            else:
                tool = tools[0]
            
            tool_name = tool.get('name')
            logger.info(f"Testing tool: {tool_name}")
            
            # Prepare minimal arguments
            schema = tool.get('inputSchema', {})
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            arguments = {}
            for param in required:
                if param in properties:
                    param_type = properties[param].get('type', 'string')
                    if param_type == 'string':
                        arguments[param] = 'test'
                    elif param_type == 'integer':
                        arguments[param] = 1
                    elif param_type == 'boolean':
                        arguments[param] = True
            
            # Make the call
            payload = {
                'name': tool_name,
                'arguments': arguments
            }
            
            logger.info(f"Calling {tool_name} with arguments: {arguments}")
            response = self.session.post("http://localhost:9000/call_tool", json=payload, timeout=30)
            
            results = {
                'tool_name': tool_name,
                'status': response.status_code,
                'arguments': arguments
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    results['data'] = data
                    # Check for API errors in the response
                    if isinstance(data, dict) and data.get('status') == 'error':
                        results['api_error'] = data.get('message')
                        results['error_details'] = data.get('error_details', {})
                except:
                    results['data'] = response.text
            else:
                results['error'] = response.text
            
        except Exception as e:
            results['error'] = str(e)
        
        return results
    
    def check_network_connectivity(self) -> Dict[str, Any]:
        """Check basic network connectivity to common endpoints."""
        results = {}
        
        endpoints = [
            'https://httpbin.org/get',
            'https://api.github.com',
            'https://jsonplaceholder.typicode.com/posts/1'
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(endpoint, timeout=10)
                results[endpoint] = {
                    'status': response.status_code,
                    'success': response.status_code == 200
                }
            except Exception as e:
                results[endpoint] = {
                    'error': str(e),
                    'success': False
                }
        
        return results
    
    def analyze_openapi_specs(self) -> Dict[str, Any]:
        """Analyze OpenAPI specifications for potential issues."""
        results = {}
        
        try:
            import yaml
            from pathlib import Path
            
            openapi_dir = Path('./openapi_specs')
            if not openapi_dir.exists():
                return {'error': 'OpenAPI specs directory not found'}
            
            specs = {}
            for spec_file in openapi_dir.glob('*.yaml'):
                try:
                    with open(spec_file, 'r') as f:
                        spec_data = yaml.safe_load(f)
                    
                    spec_name = spec_file.stem
                    servers = spec_data.get('servers', [])
                    paths = spec_data.get('paths', {})
                    
                    specs[spec_name] = {
                        'file': str(spec_file),
                        'servers': servers,
                        'path_count': len(paths),
                        'has_info': 'info' in spec_data,
                        'has_components': 'components' in spec_data
                    }
                    
                except Exception as e:
                    specs[spec_file.name] = {'error': str(e)}
            
            results['specs'] = specs
            results['total_specs'] = len(specs)
            
        except Exception as e:
            results['error'] = str(e)
        
        return results

def print_section(title: str, data: Dict[str, Any]):
    """Print a diagnostic section."""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")
    print(json.dumps(data, indent=2, default=str))

def main():
    """Run complete diagnostic suite."""
    print("🚀 MCP API System Diagnostics")
    print("="*60)
    
    diagnostics = APIDiagnostics()
    
    # Test MCP Server
    print_section("MCP Server Status", diagnostics.test_mcp_server())
    
    # Test Network Connectivity
    print_section("Network Connectivity", diagnostics.check_network_connectivity())
    
    # Analyze OpenAPI Specs
    print_section("OpenAPI Specifications", diagnostics.analyze_openapi_specs())
    
    # Test Authentication
    print("\n" + "="*60)
    print("🔐 Testing Authentication")
    print("="*60)
    
    username = input("Enter username (or press Enter to use DEFAULT_USERNAME): ").strip()
    password = input("Enter password (or press Enter to use DEFAULT_PASSWORD): ").strip()
    
    if not username:
        username = None
    if not password:
        password = None
    
    auth_results = diagnostics.test_authentication(username, password)
    print(json.dumps(auth_results, indent=2, default=str))
    
    # Test Sample API Call
    print("\n" + "="*60)
    print("🧪 Testing Sample API Call")
    print("="*60)
    
    tool_name = input("Enter tool name to test (or press Enter for auto-select): ").strip()
    if not tool_name:
        tool_name = None
    
    api_results = diagnostics.test_sample_api_call(tool_name)
    print(json.dumps(api_results, indent=2, default=str))
    
    # Summary
    print("\n" + "="*60)
    print("📋 Diagnostic Summary")
    print("="*60)
    
    # Check for common issues
    issues = []
    recommendations = []
    
    if 'error' in auth_results:
        issues.append("❌ Authentication failed")
        recommendations.append("💡 Check DEFAULT_USERNAME and DEFAULT_PASSWORD environment variables")
    
    if 'error' in api_results:
        issues.append("❌ API call failed")
        recommendations.append("💡 Check external API server status and network connectivity")
        if 'error_details' in api_results:
            recommendations.append("💡 Review error_details for specific API issues")
    
    if issues:
        print("\n🚨 Issues Found:")
        for issue in issues:
            print(f"  {issue}")
        
        print("\n💡 Recommendations:")
        for rec in recommendations:
            print(f"  {rec}")
    else:
        print("✅ No major issues detected")
    
    print("\n📖 For more help, check the README.md troubleshooting section")

if __name__ == "__main__":
    main()
