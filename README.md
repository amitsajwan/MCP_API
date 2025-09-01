# MCP API Project - WebSocket-based Real-time AI Assistant

A modern, real-time implementation of an MCP (Model Context Protocol) API project with WebSocket-based UI and enhanced AI reasoning:

- **MCP Server**: Pure tool provider (no LLM logic)
- **MCP Client**: LLM-based client with detailed reasoning and planning
- **Chatbot App**: Real-time WebSocket UI with live reasoning display
- **Mock Server**: Testing and development support

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket UI  │◄──►│  Chatbot App     │───▶│  MCP Client     │───▶│  MCP Server     │
│                 │    │  (Real-time)     │    │  (LLM Planning) │    │  (Tools Only)   │
│ - Real-time     │    │                  │    │                  │    │                  │
│ - Live Reasoning│    │ - WebSocket Mgmt │    │ - Tool Planning │    │ - OpenAPI Tools │
│ - Typing Ind.   │    │ - Auth Gateway   │    │ - Detailed Logic│    │ - Auth Handler   │
└─────────────────┘    └──────────────────┘    └──────────────────┘    └─────────────────┘
                                                                              │
                                                                              ▼
                                                                      ┌─────────────────┐
                                                                      │  REST APIs      │
                                                                      │                 │
                                                                      │ - Cash API      │
                                                                      │ - Securities    │
                                                                      │ - CLS           │
                                                                      │ - Mailbox       │
                                                                      └─────────────────┘
```

## ✨ Key Features

### 🔄 **Real-time WebSocket Communication**
- **Live chat interface** with instant responses
- **Typing indicators** showing when AI is thinking
- **Connection status** with automatic reconnection
- **Real-time reasoning display** showing AI's thought process

### 🧠 **Enhanced AI Reasoning**
- **Detailed planning** with step-by-step explanations
- **Tool-by-tool reasoning** showing why each tool is called
- **Execution status** with success/failure indicators
- **Human-readable summaries** with context and insights

### 🔐 **Azure AD Token Provider Support**
- **Secure authentication** using Azure AD tokens
- **No API keys needed** - uses Azure Identity
- **Automatic token refresh** handled by Azure
- **Role-based access** with Azure RBAC

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd MCP_API

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp config.env.example .env
# Edit .env with your Azure OpenAI credentials
```

### 2. Configure Environment

Edit `.env` file with your settings:

#### Option A: Azure AD Token Provider (Recommended)
```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure AD Token Provider Configuration
USE_AZURE_AD_TOKEN_PROVIDER=true
AZURE_AD_TOKEN_SCOPE=https://cognitiveservices.azure.com/.default

# WebSocket Configuration
WEBSOCKET_ENABLED=true
WEBSOCKET_PATH=/ws

# Authentication (Optional)
DEFAULT_USERNAME=your-username
DEFAULT_PASSWORD=your-password
DEFAULT_LOGIN_URL=http://api.company.com/login
```

#### Option B: API Key Authentication (Legacy)
```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_KEY=your-api-key-here

# Disable Azure AD Token Provider
USE_AZURE_AD_TOKEN_PROVIDER=false

# WebSocket Configuration
WEBSOCKET_ENABLED=true
WEBSOCKET_PATH=/ws

# Authentication (Optional)
DEFAULT_USERNAME=your-username
DEFAULT_PASSWORD=your-password
DEFAULT_LOGIN_URL=http://api.company.com/login
```

### 3. Azure AD Token Provider Setup

If using Azure AD Token Provider (recommended), ensure you have:

1. **Azure CLI installed and logged in**:
   ```bash
   az login
   ```

2. **Proper permissions** to access the Azure OpenAI resource:
   - Contributor or Cognitive Services User role on the Azure OpenAI resource
   - Or appropriate RBAC permissions

3. **Azure Identity package installed**:
   ```bash
   pip install azure-identity
   ```

### 4. Run the Application

#### Development Mode (Recommended)
```bash
# Start everything with mock APIs
python launcher.py --mode dev

# Start without mock APIs (use real APIs)
python launcher.py --mode dev --no-mock

# Start without frontend dev server
python launcher.py --mode dev --no-frontend
```

#### Production Mode
```bash
# Build frontend and start production servers
python launcher.py --mode prod
```

#### Manual Startup
```bash
# Terminal 1: Start MCP Server
python mcp_server.py

# Terminal 2: Start Chatbot App
python chatbot_app.py

# Terminal 3: Start Mock Server (optional)
python mock_server.py
```

## 📁 Project Structure

```
MCP_API/
├── config.py              # Centralized configuration
├── mcp_server.py          # MCP Server (tools only)
├── mcp_client.py          # MCP Client (LLM planning + reasoning)
├── chatbot_app.py         # WebSocket UI and API gateway
├── mock_server.py         # Mock API server
├── launcher.py            # Unified launcher
├── config.env.example     # Environment template
├── requirements.txt       # Python dependencies
├── # MCP Financial API System

A production-ready Model Context Protocol (MCP) system that provides LLM-powered access to financial APIs with Anthropic Claude-style tool calling capabilities.

## 🚀 **Features**

- **49 Financial Tools**: Automatically loaded from OpenAPI specifications
- **LLM Tool Calling**: Anthropic Claude-style automatic tool selection and execution
- **HTTP MCP Server**: Production-ready server with proper REST endpoints
- **Web Interface**: Real-time chat interface with WebSocket support
- **Authentication Management**: Credential storage and login handling
- **Azure OpenAI Integration**: GPT-4 powered tool orchestration and planning

## 📋 **System Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │◄──►│   MCP Client    │◄──►│   MCP Server    │
│  (FastAPI App)  │    │  (HTTP Client)  │    │ (HTTP Server)   │
│  Port 9099      │    │                 │    │  Port 8081      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ **Quick Start**

### **Prerequisites**
- Python 3.8+
- Azure OpenAI API access (optional, for LLM features)

### **Installation**

1. **Clone and setup**:
```bash
git clone <repository>
cd MCP_API
pip install -r requirements.txt
```

2. **Configure environment** (copy `config.env.example` to `config.env`):
```env
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=your_deployment
```

### **Running the System**

1. **Start MCP Server**:
```bash
python mcp_server.py --transport http --port 8081
```

2. **Start Web Interface**:
```bash
python chatbot_app.py
```

3. **Access the application**:
   - Web UI: http://localhost:9099
   - API Documentation: http://localhost:8081/docs
   - Health Check: http://localhost:9099/health

## 📚 **API Documentation**

### **Web Interface Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web chat interface |
| `/health` | GET | Health check |
| `/api/tools` | GET | List available tools |
| `/credentials` | POST | Set API credentials |
| `/login` | POST | Perform authentication |
| `/chat` | POST | Send chat message |
| `/ws` | WebSocket | Real-time chat |

### **MCP Server Endpoints**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health status |
| `/docs` | GET | Interactive API documentation |
| `/tools` | GET | Available tools list |
| `/call_tool` | POST | Execute a specific tool |

## 🧠 **LLM Tool Calling**

The system implements Anthropic Claude-style tool calling:

### **How it works**:

1. **User Query**: "Can you help me set up my credentials?"
2. **LLM Analysis**: Recognizes need for credential management
3. **Tool Selection**: Chooses `set_credentials` tool automatically
4. **Execution**: System calls the tool via MCP protocol
5. **Response**: LLM integrates results into natural language

### **Example Usage**:

```python
from mcp_client import MCPClient

client = MCPClient(server_host="localhost", server_port=8081)
await client.connect()

# LLM automatically selects and calls appropriate tools
response = await client.chat_with_function_calling(
    "Show me information about cash management APIs"
)
print(response)  # Natural language response with tool results
```

## 🔧 **Available Tools**

The system automatically loads tools from OpenAPI specifications:

- **Cash APIs** (8 tools): Payment processing, account management
- **CLS APIs** (11 tools): Continuous Linked Settlement operations
- **Mailbox APIs** (19 tools): Message and notification handling
- **Securities APIs** (11 tools): Trading and portfolio management

## 📁 **Project Structure**

```
MCP_API/
├── mcp_server.py          # HTTP MCP server
├── mcp_client.py          # HTTP MCP client with LLM integration
├── chatbot_app.py         # FastAPI web interface
├── config.py              # Configuration management
├── launcher.py            # System launcher utility
├── simple_ui.html         # Web chat interface
├── requirements.txt       # Python dependencies
├── openapi_specs/         # API specifications
│   ├── cash_api.yaml
│   ├── cls_api.yaml
│   ├── mailbox_api.yaml
│   └── securities_api.yaml
└── README.md              # This file
```

## ⚙️ **Configuration**

### **Environment Variables**

| Variable | Description | Required |
|----------|-------------|----------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI service endpoint | No* |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | No* |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | No* |

*Required for LLM-powered tool calling features

### **Server Configuration**

- **MCP Server Port**: 8081 (configurable)
- **Web Interface Port**: 9099 (configurable)
- **Transport**: HTTP (production-ready)
- **Authentication**: API key and session-based

## 🔐 **Security**

- API credentials stored securely during session
- CORS protection enabled
- Input validation on all endpoints
- Proper error handling and logging

## 🚀 **Deployment**

### **Production Setup**

1. **Configure environment variables**
2. **Start MCP server** as a service:
```bash
python mcp_server.py --transport http --host 0.0.0.0 --port 8081
```

3. **Start web interface** with production WSGI:
```bash
uvicorn chatbot_app:app --host 0.0.0.0 --port 9099
```

### **Docker Support**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8081 9099

CMD ["python", "launcher.py"]
```

## 🐛 **Troubleshooting**

### **Common Issues**

1. **Connection Failed**: Ensure MCP server is running on correct port
2. **No Tools Loaded**: Check OpenAPI specs in `openapi_specs/` directory
3. **LLM Not Working**: Verify Azure OpenAI configuration
4. **Port Conflicts**: Change ports in configuration

### **Logging**

Set log level in environment:
```bash
export LOG_LEVEL=DEBUG
```

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📄 **License**

This project is licensed under the MIT License.

## 🆘 **Support**

For issues and questions:
- Check logs for error details
- Verify configuration settings
- Ensure all dependencies are installed
- Check port availability

---

**Built with Model Context Protocol (MCP) - The future of LLM-tool integration**
├── openapi_specs/        # OpenAPI specifications
│   ├── cash_api.yaml
│   ├── securities_api.yaml
│   ├── cls_api.yaml
│   └── mailbox_api.yaml
└── frontend/             # React frontend (optional)
```

## 🔧 Configuration

All configuration is centralized in `config.py` and loaded from environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_HOST` | MCP server host | `127.0.0.1` |
| `MCP_PORT` | MCP server port | `9000` |
| `CHATBOT_HOST` | Chatbot host | `0.0.0.0` |
| `CHATBOT_PORT` | Chatbot port | `9080` |
| `WEBSOCKET_ENABLED` | Enable WebSocket | `true` |
| `WEBSOCKET_PATH` | WebSocket path | `/ws` |
| `MOCK_API_HOST` | Mock API host | `127.0.0.1` |
| `MOCK_API_PORT` | Mock API port | `9001` |
| `OPENAPI_DIR` | OpenAPI specs directory | `./openapi_specs` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Required |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment | `gpt-4` |
| `USE_AZURE_AD_TOKEN_PROVIDER` | Use Azure AD auth | `true` |
| `AZURE_AD_TOKEN_SCOPE` | Azure AD token scope | `https://cognitiveservices.azure.com/.default` |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key | Required (if not using Azure AD) |

## 🔐 Authentication

### Azure AD Token Provider (Recommended)

The system supports Azure AD token provider authentication, which is more secure and follows Azure best practices:

1. **No API keys needed** - Uses Azure AD tokens
2. **Automatic token refresh** - Handled by Azure Identity
3. **Role-based access** - Uses Azure RBAC permissions
4. **Multiple auth methods** - Supports managed identity, service principal, etc.

### API Key Authentication (Legacy)

For backward compatibility, the system also supports traditional API key authentication:

1. **Set API key** in environment variables
2. **Disable Azure AD** by setting `USE_AZURE_AD_TOKEN_PROVIDER=false`

### Application Authentication

The system supports two-step authentication for the financial APIs:

1. **Set Credentials**: Use the web UI or API endpoint
2. **Login**: Automatic login when needed

### API Endpoints

```bash
# Set credentials
curl -X POST http://localhost:9080/credentials \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'

# Login
curl -X POST http://localhost:9080/login

# Chat (REST endpoint for backward compatibility)
curl -X POST http://localhost:9080/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me pending payments"}'
```

## 🌐 Access URLs

After starting the application:

- **Real-time Chat UI**: http://localhost:9080
- **WebSocket Endpoint**: ws://localhost:9080/ws
- **Frontend Dev**: http://localhost:9517 (dev mode)
- **Built UI**: http://localhost:9080/app/ (prod mode)
- **Mock API**: http://localhost:9001
- **MCP Server**: http://localhost:9000

## 🧠 AI Reasoning Features

### Real-time Reasoning Display

The WebSocket UI shows the AI's reasoning process in real-time:

1. **Planning Phase**: Shows which tools will be called and why
2. **Execution Phase**: Displays real-time status of each tool execution
3. **Summary Phase**: Provides comprehensive results with context

### Enhanced Planning

The AI now provides detailed reasoning for each tool call:

```
🤔 Reasoning:
I analyzed your request: "Show me pending payments"
I planned to execute 2 tool(s) to gather the necessary information:

1. cash_api_get_accounts
   Reason: I need to get account information first to understand which accounts are available
   Status: ✅ Success
   Data: Found 3 accounts: Main Checking, Savings, Investment

2. cash_api_get_payments
   Reason: Then I'll check pending payments for these accounts to show what's due
   Status: ✅ Success
   Data: Found 2 pending payments totaling $1,750.00

Execution Summary: 2/2 tools succeeded.
All tools executed successfully, providing complete information for your query.
```

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
