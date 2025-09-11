# FastMCP Chatbot System

A modern, full-stack chatbot application built with FastMCP 2.0, featuring real-time communication, tool calling capabilities, and a beautiful web interface.

## 🚀 Features

- **FastMCP 2.0 Integration**: Built on the latest FastMCP protocol with stdio transport
- **Real-time Communication**: WebSocket-based chat with instant responses
- **Tool Calling**: Built-in tools for weather, math, time, web search, todos, and news
- **Modern Web UI**: Beautiful, responsive interface with typing indicators and animations
- **REST API**: Full REST API for programmatic access
- **Configuration Management**: Centralized configuration with environment variable support
- **Comprehensive Logging**: Detailed logging with configurable levels
- **Error Handling**: Robust error handling and connection management
- **Easy Deployment**: Simple launcher script for different deployment modes

## 📁 Project Structure

```
fastmcp_chatbot/
├── fastmcp_chatbot_server.py    # FastMCP 2.0 server with tool implementations
├── fastmcp_chatbot_client.py    # FastMCP 2.0 client for server communication
├── fastmcp_web_app.py           # FastAPI web application with WebSocket support
├── fastmcp_config.py            # Configuration management system
├── launch_fastmcp_chatbot.py    # Comprehensive launcher script
├── requirements.txt             # Python dependencies
└── README_FASTMCP_CHATBOT.md   # This file
```

## 🛠️ Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import fastmcp; print('FastMCP installed successfully')"
   ```

## 🚀 Quick Start

### Option 1: Full System (Recommended)
Run both server and web application:
```bash
python launch_fastmcp_chatbot.py --mode full
```

### Option 2: Server Only
Run just the FastMCP server:
```bash
python launch_fastmcp_chatbot.py --mode server
```

### Option 3: Web Application Only
Run just the web interface (requires server to be running separately):
```bash
python launch_fastmcp_chatbot.py --mode web
```

### Option 4: Direct Execution
Run components individually:

**Start the server:**
```bash
python fastmcp_chatbot_server.py --transport stdio
```

**Start the web app:**
```bash
python fastmcp_web_app.py
```

**Test the client:**
```bash
python fastmcp_chatbot_client.py
```

## 🌐 Usage

### Web Interface
1. Open your browser and go to `http://localhost:8000`
2. Start chatting with the AI assistant
3. Use quick action buttons for common tasks
4. Press `Ctrl+/` to toggle the tools panel

### REST API
The web application provides a REST API:

- `GET /api/health` - Health check
- `GET /api/tools` - List available tools
- `POST /api/chat` - Send chat message
- `POST /api/tool` - Call a specific tool

Example API usage:
```bash
# Send a chat message
curl -X POST "http://localhost:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the weather like in New York?"}'

# Get available tools
curl "http://localhost:8000/api/tools"
```

### WebSocket API
Real-time communication via WebSocket at `ws://localhost:8000/ws`:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

// Send chat message
ws.send(JSON.stringify({
    type: 'chat',
    message: 'Hello!',
    user_id: 'user123'
}));

// Send tool call
ws.send(JSON.stringify({
    type: 'tool_call',
    tool_name: 'get_weather',
    arguments: { city: 'London' },
    user_id: 'user123'
}));
```

## 🔧 Configuration

### Environment Variables
Configure the system using environment variables:

```bash
# Server configuration
export MCP_SERVER_HOST=localhost
export MCP_SERVER_PORT=9000
export MCP_SERVER_TRANSPORT=stdio
export MCP_SERVER_LOG_LEVEL=INFO

# Client configuration
export MCP_CLIENT_SERVER_SCRIPT=fastmcp_chatbot_server.py
export MCP_CLIENT_MAX_RETRIES=3
export MCP_CLIENT_RETRY_DELAY=1.0

# Web configuration
export WEB_HOST=0.0.0.0
export WEB_PORT=8000
export WEB_DEBUG=false

# Logging configuration
export LOG_LEVEL=INFO
export LOG_FILE=chatbot.log
```

### Configuration File
Create a `config.json` file for advanced configuration:

```json
{
  "server": {
    "host": "localhost",
    "port": 9000,
    "transport": "stdio",
    "log_level": "INFO"
  },
  "client": {
    "server_script": "fastmcp_chatbot_server.py",
    "max_retries": 3,
    "retry_delay": 1.0
  },
  "web": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false
  },
  "logging": {
    "level": "INFO",
    "file": "chatbot.log"
  }
}
```

Then run with:
```bash
python launch_fastmcp_chatbot.py --config config.json
```

## 🛠️ Available Tools

The chatbot comes with several built-in tools:

1. **Weather Tool** (`get_weather`)
   - Get current weather for any city
   - Parameters: `city`, `units` (metric/imperial)

2. **Math Tool** (`calculate_math`)
   - Safely calculate mathematical expressions
   - Parameters: `expression`

3. **Time Tool** (`get_time`)
   - Get current time in any timezone
   - Parameters: `timezone`

4. **Web Search Tool** (`search_web`)
   - Search the web for information (simulated)
   - Parameters: `query`, `max_results`

5. **Email Tool** (`send_email`)
   - Send emails (simulated)
   - Parameters: `to`, `subject`, `body`

6. **Todo Tool** (`create_todo`)
   - Create and manage todo items
   - Parameters: `title`, `description`, `priority`

7. **News Tool** (`get_news`)
   - Get latest news (simulated)
   - Parameters: `category`, `limit`

8. **Chat Tool** (`chat_with_user`)
   - Main chat functionality
   - Parameters: `message`, `user_id`

## 🔍 Development

### Adding New Tools
To add a new tool to the server:

1. Edit `fastmcp_chatbot_server.py`
2. Add a new function decorated with `@app.tool()`
3. Implement the tool logic
4. Add the tool to the `available_tools` list

Example:
```python
@app.tool()
async def my_new_tool(param1: str, param2: int = 10) -> str:
    """Description of my new tool."""
    try:
        # Tool implementation
        result = {"status": "success", "data": "Tool result"}
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, indent=2)
```

### Testing
Run the test script to verify everything works:

```bash
python test_fastmcp_chatbot.py
```

### Logging
The system provides comprehensive logging. Logs are written to:
- Console (default)
- File (if `LOG_FILE` is set)
- Rotating files (if file logging is enabled)

## 🐛 Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   # Kill processes using the ports
   lsof -ti:8000 | xargs kill -9
   lsof -ti:9000 | xargs kill -9
   ```

2. **FastMCP connection failed**:
   - Check if the server script exists
   - Verify Python path and dependencies
   - Check server logs for errors

3. **WebSocket connection failed**:
   - Ensure the web application is running
   - Check firewall settings
   - Verify the correct port is being used

4. **Tool execution errors**:
   - Check tool parameters
   - Verify tool implementation
   - Review server logs

### Debug Mode
Run with debug logging:
```bash
python launch_fastmcp_chatbot.py --debug
```

## 📊 Monitoring

### Health Check
Check system health:
```bash
curl http://localhost:8000/api/health
```

### Metrics
The system provides basic metrics:
- WebSocket connections count
- Server status
- Tool execution status
- Response times

## 🔒 Security Considerations

- The current implementation is designed for development/testing
- For production use, consider:
  - Authentication and authorization
  - Input validation and sanitization
  - Rate limiting
  - HTTPS/WSS encryption
  - Secure configuration management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Create an issue with detailed information
4. Include system information and error messages

---

**Happy Chatting! 🤖💬**