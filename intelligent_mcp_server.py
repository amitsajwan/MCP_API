#!/usr/bin/env python3
"""
Intelligent MCP Server with Azure OpenAI Integration
This version uses LLM capabilities to provide smart API handling,
dynamic schema understanding, and intelligent error recovery.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import argparse
import traceback
from urllib.parse import urljoin

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.sse import sse_server
from mcp.types import (
    CallToolRequest, CallToolResult, ListToolsRequest, Tool,
    TextContent, ImageContent, EmbeddedResource
)

# HTTP client imports
import httpx
from openai import AzureOpenAI

# Local imports
from intelligent_argument_validator import IntelligentArgumentValidator, ValidationResult
from api_client import APIClient
from openapi_parser import OpenAPIParser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class IntelligentAPITool:
    """Enhanced API tool with intelligent capabilities."""
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any]
    spec_name: str = ""
    tags: List[str] = field(default_factory=list)
    summary: str = ""
    operation_id: str = ""
    
    # Intelligence features
    usage_examples: List[Dict[str, Any]] = field(default_factory=list)
    common_errors: List[str] = field(default_factory=list)
    business_context: str = ""
    auto_fix_enabled: bool = True
    confidence_threshold: float = 0.7

class IntelligentMCPServer:
    """Intelligent MCP Server with LLM-powered features."""
    
    def __init__(self, config_path: str = "config.json"):
        self.server = Server("intelligent-api-server")
        self.config_path = config_path
        self.config = self._load_config()
        
        # Initialize components
        self.api_client = APIClient(self.config)
        self.openapi_parser = OpenAPIParser()
        self.intelligent_validator = IntelligentArgumentValidator(
            azure_endpoint=self.config.get('azure_openai', {}).get('endpoint'),
            azure_key=self.config.get('azure_openai', {}).get('api_key'),
            azure_deployment=self.config.get('azure_openai', {}).get('deployment')
        )
        
        # Initialize Azure OpenAI for server intelligence
        self._init_llm_client()
        
        # Tool registry
        self.tools: Dict[str, IntelligentAPITool] = {}
        self.tool_usage_stats: Dict[str, Dict[str, Any]] = {}
        
        # Setup handlers
        self._setup_handlers()
        
        logger.info("🧠 Intelligent MCP Server initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration with intelligent defaults."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"✅ Configuration loaded from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"⚠️  Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in config file: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "apis": [],
            "azure_openai": {
                "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
                "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
            },
            "intelligence": {
                "auto_fix_enabled": True,
                "confidence_threshold": 0.7,
                "learning_enabled": True,
                "usage_analytics": True
            }
        }
    
    def _init_llm_client(self):
        """Initialize LLM client for server intelligence."""
        try:
            azure_config = self.config.get('azure_openai', {})
            self.llm_client = AzureOpenAI(
                azure_endpoint=azure_config.get('endpoint'),
                api_key=azure_config.get('api_key'),
                api_version="2024-02-15-preview"
            )
            self.deployment_name = azure_config.get('deployment', 'gpt-4')
            self.llm_available = True
            logger.info("✅ Server LLM client initialized")
        except Exception as e:
            logger.warning(f"⚠️  Server LLM not available: {e}")
            self.llm_client = None
            self.llm_available = False
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools with intelligent descriptions."""
            tools = []
            
            for tool_name, api_tool in self.tools.items():
                # Enhance description with intelligence
                enhanced_description = await self._enhance_tool_description(
                    api_tool.description, api_tool
                )
                
                tools.append(Tool(
                    name=tool_name,
                    description=enhanced_description,
                    inputSchema=api_tool.parameters
                ))
            
            logger.info(f"📋 Listed {len(tools)} intelligent tools")
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Execute tool with intelligent handling."""
            logger.info(f"🔧 Intelligent tool call: {name} with args: {arguments}")
            
            if name not in self.tools:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"❌ Tool '{name}' not found. Available tools: {list(self.tools.keys())}"
                        )
                    ]
                )
            
            api_tool = self.tools[name]
            
            try:
                # Record usage
                self._record_tool_usage(name, arguments)
                
                # Intelligent validation
                validation_result = await self._intelligent_validation(
                    arguments, api_tool
                )
                
                if not validation_result.is_valid:
                    # Try auto-fix if enabled
                    if api_tool.auto_fix_enabled and validation_result.confidence_score > api_tool.confidence_threshold:
                        fixed_args = await self._attempt_auto_fix(
                            arguments, api_tool, validation_result
                        )
                        if fixed_args:
                            logger.info(f"🔧 Auto-fixed arguments for {name}")
                            arguments = fixed_args
                            # Re-validate
                            validation_result = await self._intelligent_validation(
                                arguments, api_tool
                            )
                    
                    if not validation_result.is_valid:
                        return await self._create_validation_error_response(
                            validation_result, api_tool
                        )
                
                # Execute API call
                result = await self._execute_api_call(api_tool, validation_result.cleaned_args)
                
                # Enhance response with intelligence
                enhanced_result = await self._enhance_api_response(result, api_tool)
                
                return enhanced_result
                
            except Exception as e:
                logger.error(f"❌ Tool execution failed: {e}")
                logger.error(traceback.format_exc())
                
                # Intelligent error handling
                error_response = await self._handle_execution_error(e, api_tool, arguments)
                return error_response
    
    async def _enhance_tool_description(self, base_description: str, 
                                      api_tool: IntelligentAPITool) -> str:
        """Enhance tool description with LLM intelligence."""
        if not self.llm_available:
            return base_description
        
        try:
            # Get usage statistics
            usage_stats = self.tool_usage_stats.get(api_tool.name, {})
            
            prompt = f"""
Enhance this API tool description to be more helpful for developers:

**Current Description:** {base_description}
**API Method:** {api_tool.method} {api_tool.path}
**Business Context:** {api_tool.business_context or 'General API endpoint'}
**Usage Stats:** {usage_stats.get('call_count', 0)} calls, {usage_stats.get('success_rate', 100)}% success rate
**Common Errors:** {', '.join(api_tool.common_errors[:3]) if api_tool.common_errors else 'None recorded'}

Provide a concise, developer-friendly description that includes:
1. What the API does in business terms
2. Key parameters and their purpose
3. Common use cases
4. Tips for success

Keep it under 200 words and practical.
"""
            
            response = await asyncio.to_thread(
                self.llm_client.chat.completions.create,
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API documentation expert. Create clear, helpful descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            enhanced = response.choices[0].message.content.strip()
            return enhanced if enhanced else base_description
            
        except Exception as e:
            logger.error(f"Description enhancement failed: {e}")
            return base_description
    
    async def _intelligent_validation(self, arguments: Dict[str, Any],
                                    api_tool: IntelligentAPITool) -> ValidationResult:
        """Perform intelligent validation."""
        return await asyncio.to_thread(
            self.intelligent_validator.validate_arguments,
            arguments,
            api_tool.parameters,
            api_tool.method,
            api_tool.name,
            api_tool.description
        )
    
    async def _attempt_auto_fix(self, arguments: Dict[str, Any],
                              api_tool: IntelligentAPITool,
                              validation_result: ValidationResult) -> Optional[Dict[str, Any]]:
        """Attempt to auto-fix validation issues."""
        if not self.llm_available:
            return None
        
        try:
            fixed_args = await asyncio.to_thread(
                self.intelligent_validator.suggest_corrections,
                arguments,
                api_tool.parameters,
                api_tool.name
            )
            
            # Verify the fix actually works
            test_validation = await self._intelligent_validation(fixed_args, api_tool)
            if test_validation.is_valid:
                return fixed_args
            
        except Exception as e:
            logger.error(f"Auto-fix failed: {e}")
        
        return None
    
    async def _create_validation_error_response(self, validation_result: ValidationResult,
                                               api_tool: IntelligentAPITool) -> CallToolResult:
        """Create intelligent validation error response."""
        error_content = []
        
        # Main error message
        error_text = f"❌ Validation failed for {api_tool.name}:\n\n"
        
        # Add errors
        if validation_result.errors:
            error_text += "**Errors:**\n"
            for error in validation_result.errors:
                error_text += f"• {error}\n"
        
        # Add suggestions
        if validation_result.suggestions:
            error_text += "\n**Suggestions:**\n"
            for suggestion in validation_result.suggestions:
                error_text += f"• {suggestion}\n"
        
        # Add schema explanation if available
        if self.llm_available:
            try:
                explanation = await asyncio.to_thread(
                    self.intelligent_validator.explain_schema,
                    api_tool.parameters,
                    api_tool.name,
                    api_tool.description
                )
                error_text += f"\n**How to use this API:**\n{explanation}"
            except Exception as e:
                logger.error(f"Schema explanation failed: {e}")
        
        error_content.append(TextContent(type="text", text=error_text))
        
        return CallToolResult(content=error_content, isError=True)
    
    async def _execute_api_call(self, api_tool: IntelligentAPITool,
                              arguments: Dict[str, Any]) -> CallToolResult:
        """Execute the actual API call."""
        try:
            # Use the existing API client
            response = await asyncio.to_thread(
                self.api_client.make_request,
                api_tool.method,
                api_tool.path,
                arguments
            )
            
            # Format response
            if isinstance(response, dict):
                response_text = json.dumps(response, indent=2)
            else:
                response_text = str(response)
            
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"✅ {api_tool.name} executed successfully:\n\n{response_text}"
                    )
                ]
            )
            
        except Exception as e:
            raise e  # Re-raise for intelligent error handling
    
    async def _enhance_api_response(self, result: CallToolResult,
                                  api_tool: IntelligentAPITool) -> CallToolResult:
        """Enhance API response with intelligent insights."""
        if not self.llm_available or result.isError:
            return result
        
        try:
            # Extract response content
            response_text = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    response_text += content.text
            
            # Skip enhancement for very long responses
            if len(response_text) > 2000:
                return result
            
            prompt = f"""
Analyze this API response and provide helpful insights:

**API:** {api_tool.name} ({api_tool.method} {api_tool.path})
**Response:**
{response_text}

Provide a brief analysis that includes:
1. What the response means in business terms
2. Key data points to note
3. Possible next steps or related actions
4. Any warnings or important information

Keep it concise and actionable (under 150 words).
"""
            
            response = await asyncio.to_thread(
                self.llm_client.chat.completions.create,
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API response analyst. Provide helpful insights about API responses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            insights = response.choices[0].message.content.strip()
            
            # Add insights to the response
            enhanced_content = list(result.content)
            enhanced_content.append(
                TextContent(
                    type="text",
                    text=f"\n\n🧠 **AI Insights:**\n{insights}"
                )
            )
            
            return CallToolResult(content=enhanced_content)
            
        except Exception as e:
            logger.error(f"Response enhancement failed: {e}")
            return result
    
    async def _handle_execution_error(self, error: Exception,
                                    api_tool: IntelligentAPITool,
                                    arguments: Dict[str, Any]) -> CallToolResult:
        """Intelligent error handling with suggestions."""
        error_text = f"❌ Error executing {api_tool.name}: {str(error)}\n\n"
        
        if self.llm_available:
            try:
                prompt = f"""
Analyze this API execution error and provide helpful guidance:

**API:** {api_tool.name} ({api_tool.method} {api_tool.path})
**Arguments:** {json.dumps(arguments, indent=2)}
**Error:** {str(error)}
**Error Type:** {type(error).__name__}

Provide:
1. What likely caused this error
2. How to fix it
3. Alternative approaches
4. Prevention tips

Be specific and actionable.
"""
                
                response = await asyncio.to_thread(
                    self.llm_client.chat.completions.create,
                    model=self.deployment_name,
                    messages=[
                        {"role": "system", "content": "You are an API troubleshooting expert. Help developers resolve API errors."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=400
                )
                
                guidance = response.choices[0].message.content.strip()
                error_text += f"🧠 **Troubleshooting Guidance:**\n{guidance}"
                
            except Exception as e:
                logger.error(f"Error analysis failed: {e}")
                error_text += "Unable to provide intelligent error analysis."
        
        # Record error for learning
        self._record_error(api_tool.name, str(error))
        
        return CallToolResult(
            content=[TextContent(type="text", text=error_text)],
            isError=True
        )
    
    def _record_tool_usage(self, tool_name: str, arguments: Dict[str, Any]):
        """Record tool usage for analytics."""
        if tool_name not in self.tool_usage_stats:
            self.tool_usage_stats[tool_name] = {
                'call_count': 0,
                'success_count': 0,
                'error_count': 0,
                'success_rate': 100.0,
                'last_used': None,
                'common_args': {}
            }
        
        stats = self.tool_usage_stats[tool_name]
        stats['call_count'] += 1
        stats['last_used'] = datetime.now().isoformat()
        
        # Track common argument patterns
        for key, value in arguments.items():
            if key not in stats['common_args']:
                stats['common_args'][key] = {}
            
            value_str = str(value)[:50]  # Truncate long values
            if value_str not in stats['common_args'][key]:
                stats['common_args'][key][value_str] = 0
            stats['common_args'][key][value_str] += 1
    
    def _record_error(self, tool_name: str, error_message: str):
        """Record error for learning."""
        if tool_name in self.tool_usage_stats:
            self.tool_usage_stats[tool_name]['error_count'] += 1
            
            # Update success rate
            stats = self.tool_usage_stats[tool_name]
            stats['success_rate'] = (
                stats['success_count'] / stats['call_count'] * 100
                if stats['call_count'] > 0 else 100.0
            )
        
        # Add to common errors for the tool
        if tool_name in self.tools:
            api_tool = self.tools[tool_name]
            if error_message not in api_tool.common_errors:
                api_tool.common_errors.append(error_message)
                # Keep only the 5 most recent errors
                api_tool.common_errors = api_tool.common_errors[-5:]
    
    async def load_apis(self):
        """Load and register APIs with intelligence."""
        logger.info("🔄 Loading APIs with intelligent analysis...")
        
        for api_config in self.config.get('apis', []):
            try:
                await self._load_single_api(api_config)
            except Exception as e:
                logger.error(f"❌ Failed to load API {api_config.get('name', 'unknown')}: {e}")
        
        logger.info(f"✅ Loaded {len(self.tools)} intelligent API tools")
    
    async def _load_single_api(self, api_config: Dict[str, Any]):
        """Load a single API with intelligent enhancement."""
        spec_url = api_config['spec_url']
        base_url = api_config['base_url']
        
        # Parse OpenAPI spec
        spec = await asyncio.to_thread(self.openapi_parser.parse_spec, spec_url)
        
        # Extract and enhance tools
        for path, methods in spec.get('paths', {}).items():
            for method, operation in methods.items():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    tool = await self._create_intelligent_tool(
                        spec, path, method, operation, api_config
                    )
                    if tool:
                        self.tools[tool.name] = tool
    
    async def _create_intelligent_tool(self, spec: Dict[str, Any], path: str,
                                     method: str, operation: Dict[str, Any],
                                     api_config: Dict[str, Any]) -> Optional[IntelligentAPITool]:
        """Create an intelligent API tool with LLM enhancement."""
        try:
            # Basic tool creation (similar to original)
            operation_id = operation.get('operationId', f"{method}_{path.replace('/', '_')}")
            tool_name = operation_id
            
            # Extract parameters
            parameters = self.openapi_parser.extract_parameters(operation, spec)
            
            # Create base tool
            tool = IntelligentAPITool(
                name=tool_name,
                description=operation.get('description', operation.get('summary', f"{method.upper()} {path}")),
                method=method.upper(),
                path=path,
                parameters=parameters,
                spec_name=api_config.get('name', ''),
                tags=operation.get('tags', []),
                summary=operation.get('summary', ''),
                operation_id=operation_id
            )
            
            # Enhance with LLM intelligence
            if self.llm_available:
                await self._enhance_tool_with_llm(tool, operation, spec)
            
            return tool
            
        except Exception as e:
            logger.error(f"Failed to create intelligent tool for {method} {path}: {e}")
            return None
    
    async def _enhance_tool_with_llm(self, tool: IntelligentAPITool,
                                   operation: Dict[str, Any],
                                   spec: Dict[str, Any]):
        """Enhance tool with LLM-generated intelligence."""
        try:
            prompt = f"""
Analyze this API endpoint and provide intelligent enhancements:

**API Endpoint:** {tool.method} {tool.path}
**Description:** {tool.description}
**Parameters:** {json.dumps(tool.parameters, indent=2)}
**Tags:** {tool.tags}
**OpenAPI Operation:** {json.dumps(operation, indent=2)[:1000]}...

Provide a JSON response with:
1. `business_context`: What this API does in business terms
2. `usage_examples`: 2-3 realistic usage examples with sample arguments
3. `common_errors`: Potential errors users might encounter
4. `auto_fix_enabled`: Whether auto-fix should be enabled (boolean)
5. `confidence_threshold`: Confidence threshold for auto-fix (0.0-1.0)

Focus on practical developer guidance.
"""
            
            response = await asyncio.to_thread(
                self.llm_client.chat.completions.create,
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an API intelligence analyst. Provide structured insights about API endpoints."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            
            # Parse LLM response
            response_text = response.choices[0].message.content
            
            # Try to extract JSON
            import re
            json_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
            if json_match:
                enhancements = json.loads(json_match.group(1))
            else:
                enhancements = json.loads(response_text)
            
            # Apply enhancements
            tool.business_context = enhancements.get('business_context', '')
            tool.usage_examples = enhancements.get('usage_examples', [])
            tool.common_errors = enhancements.get('common_errors', [])
            tool.auto_fix_enabled = enhancements.get('auto_fix_enabled', True)
            tool.confidence_threshold = enhancements.get('confidence_threshold', 0.7)
            
            logger.info(f"🧠 Enhanced tool {tool.name} with LLM intelligence")
            
        except Exception as e:
            logger.error(f"Tool enhancement failed for {tool.name}: {e}")
            # Set reasonable defaults
            tool.auto_fix_enabled = True
            tool.confidence_threshold = 0.7

# Server execution functions
async def run_stdio_server():
    """Run the intelligent server with stdio transport."""
    server_instance = IntelligentMCPServer()
    await server_instance.load_apis()
    
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="intelligent-api-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={}
                )
            )
        )

async def run_sse_server(port: int = 8000):
    """Run the intelligent server with SSE transport."""
    server_instance = IntelligentMCPServer()
    await server_instance.load_apis()
    
    async with sse_server() as server:
        await server.run(
            host="localhost",
            port=port,
            server=server_instance.server
        )

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Intelligent MCP API Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport method (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for SSE transport (default: 8000)"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Configuration file path (default: config.json)"
    )
    
    args = parser.parse_args()
    
    try:
        if args.transport == "stdio":
            asyncio.run(run_stdio_server())
        else:
            asyncio.run(run_sse_server(args.port))
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()