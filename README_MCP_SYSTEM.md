# MCP Chatbot System

A complete Model Context Protocol (MCP) system that provides a chatbot interface connected to financial APIs through proper MCP client-server architecture.

## Architecture

```
chatbot_app (WebSocket UI) 
    ↓
mcp_client_proper_working (MCP Client with stdio transport)
    ↓
mcp_server (MCP Server with OpenAPI tools)
    ↓
Financial APIs (Cash, Securities, Mailbox, etc.)
```

## Components

### 1. MCP Server (`mcp_server.py`)
- Implements proper MCP protocol with stdio transport
- Loads OpenAPI specifications and exposes them as MCP tools
- Handles authentication and API calls
- Supports both stdio and HTTP transports

### 2. MCP Client (`mcp_client_proper_working.py`)
- Proper MCP client using stdio transport
- Connects to MCP server and executes tools
- Provides intelligent tool planning and execution
- Returns structured results

### 3. Chatbot App (`chatbot_app.py`)
- FastAPI web application with WebSocket support
- Provides web UI for chatting
- Uses MCP client to process user queries
- Real-time communication via WebSocket

### 4. System Launcher (`stdio_launcher.py`)
- Starts the complete system
- Manages MCP server and chatbot app processes
- Provides system monitoring and graceful shutdown

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Complete System
```bash
python stdio_launcher.py
```

This will start:
- MCP Server (stdio transport)
- Chatbot App (http://localhost:8000)

### 3. Access the Chatbot
Open your browser and go to: http://localhost:8000

### 4. Start Chatting
The chatbot can help you with:
- Authentication setup
- Payment queries
- Cash summaries
- Financial data retrieval

## Manual Testing

### Test the System
```bash
python test_mcp_system.py
```

### Test MCP Client Directly
```bash
python mcp_client_proper_working.py
```

### Test MCP Server
```bash
python mcp_server.py --transport stdio
```

## Configuration

### Environment Variables
Set these for authentication:
```bash
export API_USERNAME="your_username"
export API_PASSWORD="your_password"
export API_KEY_NAME="X-API-Key"
export API_KEY_VALUE="your_api_key"
export LOGIN_URL="https://your-api.com/auth/login"
```

### OpenAPI Specifications
Place your OpenAPI spec files in the `openapi_specs/` directory:
- `cash_api.yaml`
- `securities_api.yaml`
- `mailbox_api.yaml`
- `cls_api.yaml`

## Usage Examples

### Authentication
```
User: "I need to login"
Bot: Uses set_credentials and perform_login tools
```

### Payment Queries
```
User: "Show me pending payments"
Bot: Uses cash_api_getPayments tool with status=pending
```

### Cash Summary
```
User: "What's my cash balance?"
Bot: Uses cash_api_getCashSummary tool
```

## System Architecture Details

### MCP Protocol Flow
1. **Chatbot App** receives user message via WebSocket
2. **MCP Client** processes query and plans tool calls
3. **MCP Server** executes tools via stdio transport
4. **API Calls** are made to financial services
5. **Results** flow back through the chain
6. **Response** is sent to user via WebSocket

### Tool Execution
- Tools are automatically discovered from OpenAPI specs
- Parameters are validated against schemas
- Authentication is handled transparently
- Results are formatted and summarized

## Troubleshooting

### Common Issues

1. **MCP Server won't start**
   - Check if OpenAPI specs exist in `openapi_specs/`
   - Verify Python dependencies are installed
   - Check logs for specific error messages

2. **Chatbot can't connect to MCP Server**
   - Ensure MCP server is running
   - Check stdio transport is working
   - Verify no port conflicts

3. **API calls fail**
   - Set proper environment variables for authentication
   - Check API endpoints are accessible
   - Verify credentials are correct

### Logs
- MCP Server: Check console output for stdio transport
- Chatbot App: Check console output for WebSocket connections
- System Launcher: Monitors both processes

## Development

### Adding New Tools
1. Add OpenAPI spec to `openapi_specs/`
2. Restart MCP server
3. Tools are automatically available

### Customizing the Chatbot
- Modify `chatbot_app.py` for UI changes
- Update `mcp_client_proper_working.py` for query processing
- Extend tool planning logic in `_simple_plan()` method

### Testing
- Use `test_mcp_system.py` for system validation
- Test individual components separately
- Check logs for debugging information

## Security Notes

- Credentials are stored in environment variables
- API keys are handled securely
- WebSocket connections use CORS protection
- All API calls use HTTPS (when configured)

## Support

For issues or questions:
1. Check the logs for error messages
2. Run the test suite to identify problems
3. Verify all components are properly installed
4. Check network connectivity to APIs