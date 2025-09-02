# MCP Financial API System

A production-ready Model Context Protocol (MCP) system that provides LLM-powered access to financial APIs with intelligent tool calling and authentication management.

## 🚀 **Key Features**

- **49 Financial Tools**: Automatically loaded from OpenAPI specifications (Cash, CLS, Securities, Mailbox APIs)
- **Intelligent Tool Calling**: GPT-4 powered automatic tool selection and execution
- **HTTP MCP Server**: Production-ready server with REST endpoints and comprehensive error handling
- **Web Chat Interface**: Real-time chat interface with WebSocket support and authentication flow
- **Credential Management**: Secure local credential storage with `set_credentials` tool
- **Azure OpenAI Integration**: GPT-4 powered tool orchestration and natural language responses

## 🏗️ **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │◄──►│   MCP Client    │◄──►│   MCP Server    │
│  (FastAPI App)  │    │  (HTTP Client)  │    │ (HTTP Server)   │
│  Port 9099      │    │  - GPT-4 LLM    │    │  Port 9000      │
│                 │    │  - Tool Planning │    │                 │
│ - Chat UI       │    │  - Function Call │    │ - 49 API Tools  │
│ - WebSocket     │    │  - Auth Flow     │    │ - Credential Mgmt│
│ - Auth Forms    │    │  - HTTP Client   │    │ - OpenAPI Specs │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │  External APIs  │
                                                │                 │
                                                │ - Cash API      │
                                                │ - Securities    │
                                                │ - CLS API       │
                                                │ - Mailbox API   │
                                                └─────────────────┘
```

## 🛠️ **How It Works**

### **1. Intelligent Tool Selection**
The system uses GPT-4 to analyze user queries and automatically select appropriate tools:

```
User: "Can you help me set up my API credentials?"
↓
GPT-4 Analysis: Recognizes credential management need
↓
Tool Selection: Chooses `set_credentials` tool
↓
Execution: MCP Server stores credentials locally
↓
Response: "✅ Credentials stored successfully"
```

### **2. MCP Protocol Flow**
1. **User Input**: Chat message via web interface
2. **LLM Processing**: GPT-4 analyzes intent and plans tool usage
3. **Tool Execution**: HTTP calls to MCP Server endpoints
4. **Result Integration**: LLM formats results into natural language
5. **Response**: User receives comprehensive answer with context

### **3. Authentication Management**
- **Local Storage**: Credentials stored securely in MCP Server memory
- **Session Management**: Persistent authentication across tool calls
- **Flexible Auth**: Supports username/password and API key authentication
- **Environment Fallback**: Uses environment variables as defaults

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.8+
- Azure OpenAI API access (for LLM features)

### **1. Installation**

```bash
# Clone and setup
git clone <repository>
cd MCP_API
pip install -r requirements.txt
```

### **2. Configuration**

Copy and edit the environment file:
```bash
cp .env.example .env
```

Edit `.env` with your Azure OpenAI credentials:
```env
# Required: Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Optional: Default API Credentials (can be set via chat interface)
API_USERNAME=your-api-username
API_PASSWORD=your-api-password
API_KEY_NAME=your-api-key-name
API_KEY_VALUE=your-api-key-value
LOGIN_URL=https://api.company.com/login
```

### **3. Running the System**

**Option A: Manual Startup (Recommended)**
```bash
# Terminal 1: Start MCP Server
python mcp_server.py --transport http --port 9000

# Terminal 2: Start Web Interface
python chatbot_app.py
```

**Option B: Using Launcher**
```bash
# Start both servers
python launcher.py
```

### **4. Access the Application**

- **Web Chat Interface**: http://localhost:9099
- **MCP Server API Docs**: http://localhost:9000/docs
- **Health Check**: http://localhost:9000/health

## 💬 **Usage Examples**

### **Setting Up Credentials**
```
User: "Can you help me set up my API credentials?"
System: "I'll help you set up your API credentials. Please provide:
- Username: your-username
- Password: your-password
- API Key Name (optional): X-API-Key
- API Key Value (optional): your-api-key
- Login URL (optional): https://api.company.com/login"

[System automatically calls set_credentials tool]

System: "✅ Credentials stored successfully! You can now use the financial APIs."
```

### **Querying Financial Data**
```
User: "Show me information about cash management APIs"
System: [Analyzes query, selects appropriate cash API tools, executes calls]
"Here's information about the available cash management APIs..."
```

### **Authentication Flow**
```
User: "Please log me in to the system"
System: [Uses stored credentials, calls perform_login tool]
"✅ Successfully authenticated! You now have access to all API endpoints."
```

## 📁 **Project Structure**

```
MCP_API/
├── mcp_server.py          # HTTP MCP Server (Port 9000)
├── mcp_client.py          # MCP Client with GPT-4 integration
├── chatbot_app.py         # Web interface (Port 9099)
├── config.py              # Configuration management
├── launcher.py            # Unified startup script
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
├── openapi_specs/         # API specifications
│   ├── cash_api.yaml      # Cash management APIs (8 tools)
│   ├── cls_api.yaml       # CLS APIs (11 tools)
│   ├── mailbox_api.yaml   # Mailbox APIs (19 tools)
│   └── securities_api.yaml # Securities APIs (11 tools)
└── simple_ui.html         # Basic HTML interface
```

## 📚 **API Documentation**

### **Web Interface (Port 9099)**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web chat interface |
| `/health` | GET | Health check |
| `/api/tools` | GET | List available tools |
| `/credentials` | POST | Set API credentials |
| `/login` | POST | Perform authentication |
| `/chat` | POST | Send chat message |
| `/ws` | WebSocket | Real-time chat |

### **MCP Server (Port 9000)**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health status |
| `/docs` | GET | Interactive API documentation |
| `/tools` | GET | Available tools list |
| `/call_tool` | POST | Execute a specific tool |

## 🔧 **Available Tools**

The system automatically loads 49 tools from OpenAPI specifications:

- **Cash APIs** (8 tools): Payment processing, account management
- **CLS APIs** (11 tools): Continuous Linked Settlement operations  
- **Mailbox APIs** (19 tools): Message and notification handling
- **Securities APIs** (11 tools): Trading and portfolio management

## ⚙️ **Configuration**

### **Environment Variables**

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | Yes* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Yes* |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | Yes* |

*Required for LLM-powered intelligent tool calling

### **Server Configuration**

- **MCP Server Port**: 9000 (HTTP transport)
- **Web Interface Port**: 9099 (FastAPI + WebSocket)
- **Transport**: HTTP (production-ready)
- **Authentication**: Credential management via `set_credentials` tool

## 🔐 **Security Features**

- Secure credential storage during session
- CORS protection enabled
- Input validation on all endpoints
- Comprehensive error handling and logging
- Authentication flow integration

## 🐛 **Troubleshooting**

### **Common Issues**

1. **Connection Failed**: Ensure MCP server is running on port 9000
2. **No Tools Loaded**: Check OpenAPI specs in `openapi_specs/` directory
3. **LLM Not Working**: Verify Azure OpenAI configuration in `.env`
4. **Port Conflicts**: Modify ports in `config.py`

### **System Status**

- **MCP Server Health**: http://localhost:9000/health
- **Web Interface Health**: http://localhost:9099/health
- **API Documentation**: http://localhost:9000/docs

---

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Add tests for new functionality
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Submit pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 **Support**

For issues and questions:
- Check system logs for error details
- Verify Azure OpenAI configuration
- Ensure all dependencies are installed
- Verify port availability (9000, 9099)
- Review OpenAPI specifications in `openapi_specs/`

---

**Built with Model Context Protocol (MCP) - Enabling intelligent LLM-tool integration** 🚀

### Human-readable Summaries

The AI generates comprehensive, conversational responses:

```
Based on your request for pending payments, here's what I found:

You have 2 pending payments that need attention:

1. **Rent Payment** - $1,500.00
   - Account: Main Checking Account
   - Due: In 5 days
   - Recipient: Landlord LLC

2. **Utility Bill** - $250.00
   - Account: Main Checking Account  
   - Due: In 3 days
   - Recipient: City Utilities

Total pending: $1,750.00

Your Main Checking Account has a balance of $15,420.50, so you have sufficient funds to cover these payments. I recommend scheduling these payments soon to avoid any late fees.
```

## 🛠️ Development

### Adding New APIs

1. Add OpenAPI specification to `openapi_specs/`
2. Restart MCP server
3. Tools are automatically registered

### Customizing Configuration

Edit `.env` file or set environment variables:

```bash
# Override API base URLs
export FORCE_BASE_URL_CASH=http://localhost:9001
export FORCE_BASE_URL_SECURITIES=http://api.company.com

# Enable mock mode
export MOCK_ALL=true

# Set log level
export LOG_LEVEL=DEBUG

# WebSocket settings
export WEBSOCKET_PING_INTERVAL=60
export WEBSOCKET_PING_TIMEOUT=20
```

### Testing

```bash
# Check configuration
python launcher.py --check-only

# Test with mock APIs
python launcher.py --mode dev

# Test with real APIs
python launcher.py --mode dev --no-mock

# Test WebSocket connection
# Open browser to http://localhost:9080 and start chatting
```

## 🐛 Troubleshooting

### Common Issues

1. **Configuration Errors**
   ```bash
   # Check configuration
   python launcher.py --check-only
   ```

2. **Missing Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Azure AD Authentication Issues**
   ```bash
   # Check Azure CLI login
   az account show
   
   # Check permissions
   az role assignment list --assignee $(az account show --query user.name -o tsv)
   ```

4. **WebSocket Connection Issues**
   - Check if WebSocket is enabled in config
   - Verify firewall settings
   - Check browser console for connection errors

5. **Port Conflicts**
   - Edit `.env` file to change ports
   - Check if ports are already in use

6. **Authentication Issues**
   - Verify credentials in web UI
   - Check login URL configuration
   - Review server logs

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python launcher.py --mode dev
```

## 📚 API Documentation

### WebSocket API

The WebSocket endpoint (`/ws`) supports real-time communication:

**Client to Server Messages:**
```json
{
  "type": "message",
  "content": "Show me pending payments"
}
```

**Server to Client Messages:**
```json
{
  "type": "typing_start"
}
```
```json
{
  "type": "message",
  "content": "Here's what I found...",
  "reasoning": "I analyzed your request...",
  "plan": [
    {
      "tool_name": "cash_api_get_accounts",
      "reason": "I need to get account information first..."
    }
  ]
}
```

### REST API Endpoints

- `GET /` - WebSocket-based chat UI
- `GET /status` - Application status
- `GET /tools` - List available tools
- `POST /credentials` - Set authentication
- `POST /login` - Perform login
- `POST /assistant/chat` - Legacy REST chat endpoint

### MCP Server Endpoints

- `GET /mcp/tools` - List available tools
- `GET /mcp/tool_meta/{tool}` - Get tool metadata
- `POST /mcp/tools/{tool}` - Execute tool
- `POST /credentials` - Set authentication
- `POST /login` - Perform login

### Mock API Endpoints

- `GET /accounts` - List accounts
- `GET /payments` - List payments
- `GET /securities` - List securities
- `GET /messages` - List messages
- `POST /login` - Mock login

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:

1. Check the troubleshooting section
2. Review the configuration guide
3. Check server logs for errors
4. Open an issue on GitHub
