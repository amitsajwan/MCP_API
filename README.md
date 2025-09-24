# Smart MCP System

A sophisticated MCP server with API relationship intelligence, automatic authentication handling, and intelligent response truncation.

## 🧠 Key Features

### 1. **JSESSIONID Authentication**
- Automatic login and JSESSIONID extraction
- Session management across all API calls
- Automatic re-authentication when needed

### 2. **API Key Support**
- Custom API key headers
- Per-request authentication
- Combined with JSESSIONID for maximum security

### 3. **Intelligent Response Truncation**
- Automatic truncation at MCP server level
- Configurable limit (default: 100 items)
- Proper JSON structure with truncation metadata
- Prevents huge responses that break the system

### 4. **API Relationship Intelligence**
- Understands dependencies between APIs
- Smart call ordering based on relationships
- Visual relationship mapping in the UI
- Call history tracking

### 5. **Multiple Tool Execution**
- Execute multiple tools with intelligent ordering
- Relationship-aware execution sequence
- Batch processing capabilities

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

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
```

### 4. Start the System

```bash
python start_smart.py
```

This will start:
- Smart MCP server (stdio mode)
- Web UI on http://localhost:5002

### 5. Access the Web Interface

Open http://localhost:5002 in your browser to:
- Set authentication credentials
- View available API tools
- Execute single or multiple API calls
- Monitor API relationships
- Track authentication status

## 🔧 Configuration

### Environment Variables

```bash
# Authentication
export API_USERNAME="your_username"
export API_PASSWORD="your_password"
export API_KEY_NAME="X-API-Key"
export API_KEY_VALUE="your_api_key"

# API Endpoints
export LOGIN_URL="https://api.company.com/auth/login"
export FORCE_BASE_URL="https://api.company.com"

# Response Truncation
export MAX_RESPONSE_ITEMS="100"
```

### Per-API Base URLs

Override base URLs for specific APIs:

```bash
export FORCE_BASE_URL_CASH_API="https://cash-api.company.com"
export FORCE_BASE_URL_SECURITIES_API="https://securities-api.company.com"
export FORCE_BASE_URL_MAILBOX_API="https://mailbox-api.company.com"
export FORCE_BASE_URL_CLS_API="https://cls-api.company.com"
```

## 🏗️ Architecture

### Smart Flow

```
Web UI (Port 5002)
    ↓
Smart MCP Server
    ↓
FastMCP.from_openapi() → Auto-generates tools
    ↓
HTTP Client with JSESSIONID + API Key
    ↓
Response Truncation (100 items max)
    ↓
Actual API Endpoints
```

### Key Components

1. **`smart_mcp_server.py`**: Main server with relationship intelligence
2. **`smart_web_ui.py`**: Advanced web interface with relationship visualization
3. **`templates/smart_chat.html`**: Rich web UI with multiple tool execution
4. **`start_smart.py`**: Intelligent startup script

## 🔐 Authentication Features

### JSESSIONID Management
- Automatic login using username/password
- JSESSIONID extraction from login response
- Session cookie management across all clients
- Automatic re-authentication when sessions expire

### API Key Support
- Custom header configuration
- Per-request API key injection
- Combined authentication (JSESSIONID + API Key)

### Authentication Status
- Real-time authentication status in UI
- Visual indicators for JSESSIONID and API Key
- Credential validation and feedback

## 📊 Response Truncation

### Intelligent Truncation
- Server-level truncation before sending to client
- Configurable item limits (default: 100)
- Preserves JSON structure
- Adds truncation metadata

### Truncation Features
- List responses: Limits to N items
- Object responses: Truncates list fields within objects
- Metadata: Includes total count, returned count, truncation note
- Visual warnings in UI when truncation occurs

### Example Truncated Response
```json
{
  "items": [...100 items...],
  "total_count": 500,
  "returned_count": 100,
  "truncated": true,
  "truncation_note": "Response limited to 100 items out of 500 total items"
}
```

## 🔗 API Relationship Intelligence

### Relationship Types
- **depends_on**: APIs that must be called first
- **calls_after**: APIs that should be called after others
- **uses_data_from**: APIs that consume data from others
- **provides_data_to**: APIs that provide data to others

### Smart Call Ordering
- Automatic dependency resolution
- Optimal execution sequence
- Relationship-aware tool execution
- Call history tracking

### Example Relationships
```python
'cash_api': {
    'depends_on': [],
    'calls_after': ['securities_api'],
    'uses_data_from': ['securities_api', 'cls_api'],
    'provides_data_to': ['cls_api']
}
```

## 🎨 Web UI Features

### Advanced Interface
- **Real-time Chat**: WebSocket-based communication
- **Tool Browser**: View and execute available API tools
- **Credential Management**: Set authentication in the UI
- **Relationship Visualization**: See API dependencies
- **Multiple Tool Execution**: Execute multiple tools with smart ordering
- **Authentication Status**: Real-time auth indicators
- **Response Truncation Warnings**: Visual feedback for truncated responses

### Smart Features
- **Intelligent Tool Selection**: Relationship-aware tool recommendations
- **Batch Execution**: Execute multiple tools with optimal ordering
- **Status Monitoring**: Real-time connection and authentication status
- **Error Handling**: Comprehensive error reporting and recovery

## 🛠️ Development

### Adding New APIs

1. Add OpenAPI YAML file to `./openapi_specs/`
2. Update relationship configuration in `smart_mcp_server.py`
3. Restart the system
4. Tools are automatically generated

### Customizing Relationships

Modify the `_load_api_relationships()` method in `smart_mcp_server.py`:

```python
self.api_relationships = {
    'your_api': {
        'depends_on': ['other_api'],
        'calls_after': ['another_api'],
        'uses_data_from': ['data_provider_api'],
        'provides_data_to': ['consumer_api']
    }
}
```

### Extending Truncation

Modify the `_truncate_response()` method for custom truncation logic:

```python
def _truncate_response(self, data: Any) -> TruncatedResponse:
    # Custom truncation logic here
    pass
```

## 🐛 Troubleshooting

### Common Issues

1. **No tools available**: Check OpenAPI YAML files in `./openapi_specs/`
2. **Authentication fails**: Verify credentials and login URL
3. **Connection errors**: Check base URLs and network connectivity
4. **Tool execution fails**: Verify API endpoints and parameters
5. **Truncation issues**: Check `MAX_RESPONSE_ITEMS` setting

### Logs

Check these log files:
- `smart_mcp.log`: Server operations and relationships
- `smart_web_ui.log`: Web UI operations

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python start_smart.py
```

## 📚 API Examples

### Single Tool Execution
```javascript
socket.emit('execute_tool', {
    tool_name: 'getPayments',
    arguments: { status: 'pending', amount_min: 1000 }
});
```

### Multiple Tool Execution
```javascript
socket.emit('execute_multiple_tools', {
    tool_requests: [
        { tool_name: 'getSecurities', arguments: {} },
        { tool_name: 'getPayments', arguments: { status: 'pending' } },
        { tool_name: 'processSettlement', arguments: {} }
    ]
});
```

### Credential Setting
```javascript
socket.emit('set_credentials', {
    username: 'your_user',
    password: 'your_pass',
    api_key_name: 'X-API-Key',
    api_key_value: 'your_key'
});
```

## 🎉 Benefits

1. **90% Less Complexity**: Simplified from complex modular system
2. **Automatic Authentication**: JSESSIONID and API key handling
3. **Intelligent Truncation**: Prevents huge responses
4. **Relationship Intelligence**: Smart API call ordering
5. **Production Ready**: Robust error handling and logging
6. **Easy Maintenance**: Clean, understandable code
7. **Fast Development**: Quick to add new APIs
8. **Real-time Monitoring**: Live status and relationship tracking

## 🔄 Migration from Legacy Systems

### What's Improved
- **Authentication**: Automatic JSESSIONID management
- **Response Handling**: Intelligent truncation
- **API Intelligence**: Relationship understanding
- **UI/UX**: Advanced web interface
- **Performance**: Optimized call ordering

### Migration Steps
1. **Backup OpenAPI specs** (they're still needed)
2. **Set environment variables** (same format)
3. **Use the smart system** instead of legacy
4. **Remove legacy files** (no longer needed)

## 📈 Performance

### Optimizations
- **Smart Call Ordering**: Reduces API call dependencies
- **Response Truncation**: Prevents memory issues
- **Connection Pooling**: Efficient HTTP client management
- **Caching**: Relationship and tool caching

### Monitoring
- **Call History**: Track API usage patterns
- **Performance Metrics**: Response times and success rates
- **Relationship Analysis**: Optimize call sequences

## 🚀 Future Enhancements

- **LLM Integration**: Natural language to API calls
- **Advanced Analytics**: Usage patterns and optimization
- **Custom Relationship Rules**: User-defined API relationships
- **Performance Optimization**: Advanced caching and batching
- **Security Enhancements**: OAuth2 and advanced authentication