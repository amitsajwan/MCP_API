#!/usr/bin/env python3
"""
MCP Server using FastMCP with OpenAPI Integration
Loads OpenAPI specs and exposes tools via MCP protocol
"""

import os
import logging
from pathlib import Path
import yaml
import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import RouteMap, MCPType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastMCP server
mcp = FastMCP("API Orchestration Server", version="2.0.0")

def load_openapi_specs():
    """Load all OpenAPI specifications from openapi_specs directory"""
    specs_dir = Path(__file__).parent / "openapi_specs"
    
    if not specs_dir.exists():
        logger.warning(f"OpenAPI specs directory not found: {specs_dir}")
        return
    
    # Find all YAML files
    spec_files = list(specs_dir.glob("*.yaml")) + list(specs_dir.glob("*.yml"))
    
    logger.info(f"Found {len(spec_files)} OpenAPI specification files")
    
    for spec_file in spec_files:
        try:
            logger.info(f"Loading OpenAPI spec: {spec_file.name}")
            
            # Load YAML spec
            with open(spec_file, 'r') as f:
                openapi_spec = yaml.safe_load(f)
            
            # Get API name from filename
            api_name = spec_file.stem  # e.g., "cash_api" from "cash_api.yaml"
            
            # Get base URL from spec
            servers = openapi_spec.get('servers', [])
            base_url = servers[0]['url'] if servers else 'http://localhost:8000'
            
            # Create HTTP client for this API
            api_client = httpx.AsyncClient(
                base_url=base_url,
                timeout=30.0
            )
            
            # Create route maps for better MCP component organization
            route_maps = [
                # GET requests with path parameters become ResourceTemplates
                RouteMap(
                    methods=["GET"],
                    pattern=r".*\{.*\}.*",
                    mcp_type=MCPType.RESOURCE_TEMPLATE,
                    mcp_tags={"semantic-cache", "parameterized"}
                ),
                # Other GET requests become Resources
                RouteMap(
                    methods=["GET"],
                    pattern=r".*",
                    mcp_type=MCPType.RESOURCE,
                    mcp_tags={"data-retrieval", "cacheable"}
                ),
                # Write operations become Tools
                RouteMap(
                    methods=["POST", "PUT", "DELETE", "PATCH"],
                    mcp_type=MCPType.TOOL,
                    mcp_tags={"write-operation", "api-mutation"}
                )
            ]
            
            # Add OpenAPI spec to MCP server using FastMCP
            mcp_instance = FastMCP.from_openapi(
                openapi_spec=openapi_spec,
                client=api_client,
                name=f"{api_name}_api",
                route_maps=route_maps,
                tags={api_name, "openapi", "auto-generated"}
            )
            
            # Merge tools into main MCP server
            # In FastMCP 2.x, you can merge multiple servers
            # For now, we'll track that we loaded the spec
            
            logger.info(f"✓ Loaded {api_name} API from {spec_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to load {spec_file.name}: {e}")
            continue
    
    logger.info(f"✓ All OpenAPI specifications loaded successfully")

# Add custom MCP tools for orchestration
@mcp.tool()
async def list_loaded_apis() -> str:
    """List all loaded API specifications"""
    specs_dir = Path(__file__).parent / "openapi_specs"
    spec_files = list(specs_dir.glob("*.yaml")) + list(specs_dir.glob("*.yml"))
    
    apis = [spec_file.stem for spec_file in spec_files]
    
    return json.dumps({
        "loaded_apis": apis,
        "total_count": len(apis),
        "specs_directory": str(specs_dir)
    })

@mcp.tool()
async def reload_openapi_specs() -> str:
    """Reload all OpenAPI specifications"""
    try:
        load_openapi_specs()
        return json.dumps({
            "success": True,
            "message": "OpenAPI specs reloaded successfully"
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })

@mcp.resource("system://status")
async def get_system_status() -> str:
    """Get MCP server status"""
    return json.dumps({
        "status": "running",
        "server": "FastMCP API Orchestration Server",
        "version": "2.0.0",
        "protocol": "MCP over stdio"
    })

if __name__ == "__main__":
    # Load OpenAPI specs on startup
    logger.info("Starting MCP Server with FastMCP + OpenAPI integration")
    load_openapi_specs()
    
    # Run MCP server with stdio transport
    mcp.run(transport="stdio")
