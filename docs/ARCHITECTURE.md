# 🏗️ System Architecture

## Overview

Demo MCP System - Fully dynamic adaptive orchestration using FastMCP + OpenAPI integration.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                      STREAMLIT UI                               │
│  Home | MCP Tools | Use Cases | Bot Chat | Adaptive Query      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      CORE LAYER                                 │
│  • Adaptive Orchestrator (LLM-driven planning)                  │
│  • Cache Manager (Multi-level caching)                          │
│  • MCP Client Connector (MCP protocol communication)            │
│  • Bot Manager, Use Case Manager, Tools Manager                 │
└─────────────────────────────────────────────────────────────────┘
                              ↕ MCP Protocol (stdio)
┌─────────────────────────────────────────────────────────────────┐
│                     MCP SERVER (FastMCP)                        │
│  • Loads OpenAPI specs from openapi_specs/                      │
│  • Converts endpoints to MCP tools automatically                │
│  • Exposes tools via MCP protocol                               │
│  • Executes actual API calls                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   EXTERNAL SERVICES                             │
│  • Azure OpenAI (LLM + Embeddings)                              │
│  • Vector Store (FAISS)                                         │
│  • External APIs (via OpenAPI specs)                            │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. MCP Server (FastMCP)
- **File**: `mcp_server_fastmcp.py`
- **Responsibility**: Load OpenAPI specs, expose tools via MCP protocol
- **Uses**: FastMCP library from https://gofastmcp.com/integrations/openapi
- **Protocol**: MCP over stdio

### 2. MCP Client Connector
- **File**: `core/mcp_client_connector.py`
- **Responsibility**: Connect to MCP server, discover and execute tools
- **Protocol**: MCP stdio transport
- **Discovery**: Dynamic tool discovery via `list_tools()`

### 3. Adaptive Orchestrator
- **File**: `core/adaptive_orchestrator.py`
- **Responsibility**: LLM-driven query planning and execution
- **Features**: Dynamic tool selection, caching, Python code generation

### 4. Cache Manager
- **File**: `core/cache_manager.py`  
- **Responsibility**: Multi-level caching (Workflow, User, Use Case)
- **Strategy**: TTL-based, size-limited

### 5. External Services
- **Azure Client**: LLM and embedding generation
- **Vector Store**: Similarity search
- **Embedding Service**: Text-to-vector conversion

## Data Flow

```
User Query
    ↓
Adaptive Orchestrator
    ↓
MCP Client → list_tools() → MCP Server
    ↓
LLM analyzes query + discovered tools
    ↓
LLM creates execution plan
    ↓
MCP Client → call_tool() → MCP Server → External API
    ↓
Cache large results (>100KB)
    ↓
Generate summary for LLM
    ↓
LLM generates Python code
    ↓
Execute Python on cached data
    ↓
Return to user
```

## Module Structure

```
core/
├── adaptive_orchestrator.py    # LLM-driven orchestration
├── mcp_client_connector.py     # MCP protocol client
├── cache_manager.py            # Caching layer
├── bot_manager.py              # Bot interactions
├── use_case_manager.py         # Pre-defined workflows
└── mcp_tools_manager.py        # Tool utilities (for demo UI)

external/
├── azure_client.py             # Azure OpenAI integration
├── vector_store.py             # FAISS vector store
└── embedding_service.py        # Embedding generation

ui/
└── streamlit_app.py            # Streamlit interface

config/
└── settings.py                 # Configuration management
```

## Design Principles

1. **No Hardcoding** - Works with ANY OpenAPI spec
2. **LLM-Driven** - All decisions made by LLM
3. **MCP Protocol** - Standard MCP communication
4. **Dynamic Discovery** - Tools discovered at runtime
5. **Caching Strategy** - Large results cached, summaries to LLM
6. **Safe Execution** - Python code validated and sandboxed

---

**Version**: 2.0.0 (FastMCP + Dynamic Orchestration)
