# 📁 Examples

This directory contains example code demonstrating how to use the MCP API system components.

## Available Examples

### 🤖 Intelligent API Analysis Example

**File**: `intelligent_analysis_example.py`

**Description**: Demonstrates the `IntelligentAPIAnalyzer` capabilities including:
- MCP tool discovery and analysis
- Dependency mapping between tools
- Cache opportunity identification
- Intelligent use case generation
- Vector database integration
- Query analysis and matching

**Usage**:
```bash
cd examples
python intelligent_analysis_example.py
```

**Features Demonstrated**:
- ✅ MCP protocol integration
- ✅ Tool metadata extraction
- ✅ Dependency analysis
- ✅ Cache strategy optimization
- ✅ Use case generation
- ✅ Vector database storage
- ✅ Query matching

## Running Examples

### Prerequisites
1. Ensure all dependencies are installed:
   ```bash
   pip install -r ../requirements.txt
   ```

2. Make sure the MCP server is available:
   ```bash
   # The example will start the MCP server automatically
   python intelligent_analysis_example.py
   ```

### Example Output
The intelligent analysis example will show:
- Tool discovery and metadata extraction
- Dependency mapping results
- Cache opportunity analysis
- Generated use cases
- Vector database statistics
- Query matching demonstrations

## Integration with Main System

These examples show how to integrate the analysis components with your main application:

```python
# Initialize analyzer
analyzer = IntelligentAPIAnalyzer(
    mcp_client_connector=mcp_client,
    vector_store=vector_store,
    cache_manager=cache_manager
)

# Analyze and generate use cases
analysis = await analyzer.analyze_and_generate_use_cases()

# Use for query resolution
query_analysis = await analyzer.get_analysis_for_query(user_query)
```

## Next Steps

1. **Run the example** to see the analyzer in action
2. **Integrate with your adaptive orchestrator** for enhanced query processing
3. **Customize use case generation** for your specific APIs
4. **Extend cache strategies** based on your performance requirements

---

**For more information, see the [Dependency Analysis Documentation](../docs/DEPENDENCY_ANALYSIS.md)**
