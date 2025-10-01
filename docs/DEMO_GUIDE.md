# 🎯 Demo System Guide

## Quick Start

```bash
# Install dependencies
pip install streamlit fastmcp httpx pyyaml numpy pydantic

# Run Streamlit UI
streamlit run ui/streamlit_app.py

# Access at http://localhost:8501
```

## Pages

### 1. Home
- System overview and statistics
- Quick navigation

### 2. MCP Tools
- Execute individual tools
- View tool parameters
- See execution results

### 3. Use Cases
- Pre-defined workflows with 3-4 tools
- Documentation and flowcharts
- Execute with parameters

### 4. Bot Chat
- Natural language queries
- Context-aware responses
- Use case recommendations

### 5. Adaptive Query ⭐ **NEW**
- Fully dynamic query processing
- Intelligent tool orchestration
- Large result caching
- Python aggregation on cached data
- Works with ANY OpenAPI spec

### 6. Cache Management
- View cache statistics
- Clear cache by type
- Monitor performance

### 7. System Status
- Azure OpenAI status
- Vector store statistics
- Performance metrics

## Demo Scenarios

### Adaptive Query Demo
1. Go to **Adaptive Query** page
2. Enter: "Show me total balance across all accounts"
3. Click **Execute Adaptive Query**
4. Watch the system:
   - Discover tools via MCP
   - Create execution plan
   - Execute tools
   - Cache large results
   - Generate Python aggregation code
   - Process cached data
   - Return results

### Tool Execution Demo
1. Go to **MCP Tools** page
2. Select a tool
3. Enter parameters
4. Execute and see results

### Use Case Demo
1. Go to **Use Cases** page
2. Select "Account Balance Inquiry"
3. View documentation and flowchart
4. Execute the workflow

---

**Complete working demo system!**
