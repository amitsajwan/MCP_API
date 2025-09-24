# Simplified FastMCP System

A clean, simple implementation using FastMCP's `from_openapi` capability to automatically generate tools from OpenAPI specifications.

## 🎯 Key Benefits

- **Simplified Architecture**: Uses FastMCP's built-in `from_openapi` method
- **Automatic Tool Generation**: No manual tool registration needed
- **Built-in Authentication**: Handles user login, API keys, and JSESSIONID
- **Clean Web UI**: Simple, responsive interface
- **One Flow**: Single, adaptive approach without complexity

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare OpenAPI Specifications

Place your OpenAPI YAML files in the `./openapi_specs/` directory:

```
openapi_specs/
├── cash_api.yaml
├── securities_api.yaml
├── mailbox_api.yaml
└── cls_api.yaml
```

### 3. Start the System

```bash
python start_simplified.py
```

This will start:
- FastMCP server (stdio mode)
- Web UI on http://localhost:5001

### 4. Access the Web Interface

Open http://localhost:5001 in your browser to:
- Set authentication credentials
- View available API tools
- Execute API calls
- Chat with the assistant

## 🔧 Configuration

### Environment Variables

Set these environment variables for automatic configuration:

```bash
export API_USERNAME="your_username"
export API_PASSWORD="your_password"
export API_KEY_NAME="X-API-Key"
export API_KEY_VALUE="your_api_key"
export LOGIN_URL="https://api.company.com/auth/login"
export FORCE_BASE_URL="https://api.company.com"
```

### Per-API Base URLs

Override base URLs for specific APIs:

```bash
export FORCE_BASE_URL_CASH_API="https://cash-api.company.com"
export FORCE_BASE_URL_SECURITIES_API="https://securities-api.company.com"
```

## 🏗️ Architecture

### Simplified Flow

```
Web UI (Port 5001)
    ↓
Simplified FastMCP Server
    ↓
FastMCP.from_openapi() → Auto-generates tools
    ↓
HTTP Client with Authentication
    ↓
Actual API Endpoints
```

### Key Components

1. **`simplified_fastmcp_server.py`**: Main server using FastMCP's `from_openapi`
2. **`simplified_web_ui.py`**: Clean web interface with WebSocket support
3. **`templates/simplified_chat.html`**: Responsive web UI template
4. **`start_simplified.py`**: Simple startup script

## 🔐 Authentication

The system supports multiple authentication methods:

### 1. Basic Authentication
- Username/password for login
- Automatic JSESSIONID extraction
- Session management across API calls

### 2. API Key Authentication
- Custom API key headers
- Per-request authentication

### 3. Combined Authentication
- Both basic auth and API keys
- Flexible configuration

## 📋 Available Tools

Tools are automatically generated from your OpenAPI specifications:

- **Cash API**: Payment management, approvals, transactions
- **Securities API**: Portfolio management, trading
- **Mailbox API**: Message handling, notifications
- **CLS API**: Settlement operations

## 🎨 Web UI Features

- **Real-time Chat**: WebSocket-based communication
- **Tool Browser**: View and execute available API tools
- **Credential Management**: Set authentication in the UI
- **Responsive Design**: Works on desktop and mobile
- **Status Indicators**: Connection and authentication status

## 🔄 Migration from Complex System

### What's Removed
- Complex modular service architecture
- Manual tool registration
- Custom MCP server implementation
- Multiple layers of abstraction

### What's Simplified
- Single FastMCP server using `from_openapi`
- Direct OpenAPI → Tools conversion
- Built-in authentication handling
- Clean, single-flow architecture

## 🛠️ Development

### Adding New APIs

1. Add OpenAPI YAML file to `./openapi_specs/`
2. Restart the system
3. Tools are automatically generated

### Customizing Authentication

Modify `_create_authenticated_client()` in `simplified_fastmcp_server.py`:

```python
async def _create_authenticated_client(self, spec_data, spec_name):
    # Custom authentication logic here
    pass
```

### Extending the Web UI

Modify `templates/simplified_chat.html` for UI changes or add new WebSocket handlers in `simplified_web_ui.py`.

## 🐛 Troubleshooting

### Common Issues

1. **No tools available**: Check OpenAPI YAML files in `./openapi_specs/`
2. **Authentication fails**: Verify credentials and login URL
3. **Connection errors**: Check base URLs and network connectivity
4. **Tool execution fails**: Verify API endpoints and parameters

### Logs

Check these log files:
- `simplified_fastmcp.log`: Server operations
- `simplified_web_ui.log`: Web UI operations

## 📚 FastMCP Documentation

For more information about FastMCP's `from_openapi` capability:
- [FastMCP Documentation](https://gofastmcp.com/integrations/openapi)
- [OpenAPI Integration Guide](https://gofastmcp.com/docs/openapi)

## 🎉 Benefits of This Approach

1. **90% Less Code**: Simplified from complex modular system
2. **Automatic Tool Generation**: No manual registration needed
3. **Built-in Authentication**: Handles sessions and API keys
4. **Single Flow**: One adaptive approach
5. **Easy Maintenance**: Clean, understandable code
6. **Fast Development**: Quick to add new APIs
7. **Production Ready**: Robust error handling and logging