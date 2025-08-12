A comprehensive Model Context Protocol (MCP) server that dynamically loads OpenAPI specifications and exposes REST APIs as tools for chatbot integration. Perfect for financial institutions and enterprises that need to provide conversational access to their APIs.
# OpenAPI MCP Server (Simplified Edition)

Minimal, LLM-ready bridge that:
- Auto-loads OpenAPI specs from `openapi_specs/` and converts each endpoint into a tool
- Provides HTTP introspection + execution endpoints under `/mcp/*`
- Offers a simple FastAPI chatbot proxy and a very small React chat UI (or minimal HTML UI at `/simple`)
- Includes an optional LLM planning endpoint (`/llm/agent`) and lightweight heuristic assistant (`/assistant/chat`)

This is a trimmed, cleaner version: legacy experimental scripts and duplicate server variants removed.

A comprehensive Model Context Protocol (MCP) server that dynamically loads OpenAPI specifications and exposes REST APIs as tools for chatbot integration. Perfect for financial institutions and enterprises that need to provide conversational access to their APIs.

## 🚀 Core Features

### Core
- Dynamic OpenAPI loading -> tools
- Tool execution over HTTP or MCP transport (stdio/http)
- Base URL override via `FORCE_BASE_URL` or `FORCE_BASE_URL_<SPEC>` (useful for mock server)
- Simple assistant: naive relevance scoring + inline arg parse (adds `status=pending` if you just say pending)
- LLM agent (OpenAI optional) for multi-step tool planning `/llm/agent`

### Included Demo Spec
Cash API (payments, transactions, summary) – extend by dropping more specs in `openapi_specs/`.

### Smart Features
- **Natural Language Processing**: Understand user intent and route to appropriate APIs
- **Contextual Responses**: Provide intelligent summaries and insights
- **Error Handling**: Comprehensive error management and recovery
- **Performance Optimization**: Connection pooling and request optimization

## 📋 Prerequisites

- Python 3.8+
- pip (Python package manager)
- Access to REST APIs (for production use)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd MCP_API
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import fastmcp, yaml, requests; print('✅ Dependencies installed successfully!')"
   ```

## 🚀 Quick Start

### One Command Demo

```powershell
python start_demo.py --dev --with-mock
```

Starts:
- Mock API (port 9001)
- MCP Server (port 8000, HTTP transport)
- Chatbot FastAPI (port 8080)
- (Optional) React dev UI if Node available

### Manual Startup

1. **Start the MCP Server:**
   ```bash
   python openapi_mcp_server.py
   ```

2. **Start the FastAPI Chatbot (in another terminal):**
   ```bash
   python chatbot_app.py
   ```

3. **Access the web interface:**
   - Open http://localhost:8080 in your browser
   - Start asking questions about your financial data!

### Test Endpoints

```bash
# Start servers
python openapi_mcp_server.py --transport http
python chatbot_app.py
```

### Add / Override Specs

```python
# Load cash management API
load_openapi_spec(
    spec_name="cash",
    yaml_path="api_specs/cash_api.yaml",
    base_url="https://api.company.com/cash/v1",
    auth_type="bearer",
    token="your_token_here"
)

# Load securities trading API
load_openapi_spec(
    spec_name="securities",
    yaml_path="api_specs/securities_api.yaml",
    base_url="https://api.company.com/securities/v1",
    auth_type="basic",
    username="your_username",
    password="your_password"
)
```

### Heuristic Assistant

```python
# Natural language queries
result = intelligent_api_router("Show me pending payments")
result = intelligent_api_router("Get my portfolio overview")
result = intelligent_api_router("Check settlement status")
```

### LLM Planning (Optional)

Set an API key if you want OpenAI planning:
```powershell
$env:OPENAI_API_KEY = 'sk-...'
```
Call:
```powershell
Invoke-RestMethod -Uri http://localhost:8000/llm/agent -Method Post -ContentType 'application/json' -Body '{"message":"pending payments and summary","max_steps":2}'
```

```python
# Comprehensive financial summary
summary = get_financial_summary(
    date_range="last_7_days",
    include_pending=True,
    include_approved=True
)
```

## 📚 Specs

### Included APIs

| API | Description | Key Features |
|-----|-------------|--------------|
| **Cash Management** | Payment processing and cash flow | Payments, transactions, approvals |
| **Securities Trading** | Portfolio and trading management | Portfolio, trades, settlements |
| **CLS Settlement** | Settlement and clearing operations | Settlements, clearing, risk |
| **Mailbox** | Communication and notifications | Messages, alerts, notifications |

### Adding Specs

1. **Create OpenAPI YAML file**:
   ```yaml
   openapi: 3.0.3
   info:
     title: Your API Name
     description: API description
     version: 1.0.0
   servers:
     - url: https://your-api-url.com/v1
   paths:
     /your-endpoint:
       get:
         operationId: getYourData
         summary: Get your data
         # ... rest of your API spec
   ```

2. **Load the specification**:
   ```python
   load_openapi_spec(
       spec_name="your_api",
       yaml_path="path/to/your_api.yaml",
       base_url="https://your-api-url.com/v1",
       auth_type="your_auth_type"
   )
   ```

## 🔧 Core Tools

### Management Tools
- `load_openapi_spec`: Load and validate OpenAPI specifications
- `list_api_tools`: List all available API tools
- `execute_parallel_apis`: Execute multiple API calls in parallel

### Intelligent Tools
- `intelligent_api_router`: Route natural language queries to relevant APIs
- `get_financial_summary`: Get comprehensive financial summaries
- `check_payment_approvals`: Check payment approval status across systems

## 💬 Natural Language Examples

The system understands various natural language patterns:

### Payment Related
- "Show me pending payments"
- "Get payment approval status"
- "List all cash transactions"
- "Check payment ID 12345"

### Securities Related
- "Show my portfolio"
- "Get trading history"
- "Check settlement status"
- "List my positions"

### CLS Related
- "Show CLS settlements"
- "Get clearing status"
- "Check risk metrics"
- "List pending instructions"

### Mailbox Related
- "Show unread messages"
- "Get notifications"
- "List active alerts"
- "Check mailbox summary"

### Summary Queries
- "Give me a financial summary"
- "Summarize all activities"
- "Show pending approvals"
- "Get overview of all systems"

## 🔐 Authentication

### Supported Methods

1. **None**: No authentication required
2. **Basic**: Username/password authentication
3. **Bearer**: Token-based authentication
4. **OAuth2**: OAuth 2.0 authentication (basic support)

### Example Setup

```python
# Basic Auth
load_openapi_spec(
    spec_name="api_name",
    yaml_path="api_specs/api.yaml",
    base_url="https://api.company.com/v1",
    auth_type="basic",
    username="your_username",
    password="your_password"
)

# Bearer Token
load_openapi_spec(
    spec_name="api_name",
    yaml_path="api_specs/api.yaml",
    base_url="https://api.company.com/v1",
    auth_type="bearer",
    token="your_bearer_token"
)
```

## 🤖 Interaction Options
1. Minimal HTML: http://localhost:8080/simple
2. Simple React Chat (launch dev server in `frontend/`)
3. Programmatic: /mcp/tools, /mcp/tools/{tool}, /assistant/chat, /llm/agent

The project includes a modern web-based chatbot interface built with FastAPI that provides:

### Features
- **Real-time Chat Interface**: Beautiful, responsive web UI
- **Natural Language Processing**: Ask questions in plain English
- **Quick Actions**: Pre-defined buttons for common queries
- **Session Management**: Track conversation history
- **Real-time Status**: Monitor MCP server connection
- **WebSocket Support**: Real-time communication (optional)

### Web Interface
- **URL**: http://localhost:8080
- **API Documentation**: http://localhost:8080/docs
- **Real-time Status**: Shows MCP server connection status
- **Quick Actions**: One-click access to common queries

### Example Queries
Try these questions in the web interface:
- "Show me all pending payments that need approval"
- "What's my current portfolio value?"
- "Are there any CLS settlements pending?"
- "Do I have any unread messages?"
- "Give me a summary of all financial activities"

## 📖 Usage Examples

### Example 1: Web Interface

1. Start the demo:
   ```bash
   python start_demo.py
   ```

2. Open http://localhost:8080 in your browser

3. Start asking questions!

### Example 2: Programmatic Usage

```python
from mcp_client import ChatbotMCPClient

# Initialize client
client = ChatbotMCPClient()

# Ask questions
result = client.ask_question("Show me pending payments")
print(result)

# Get financial summary
summary = client.get_financial_summary(date_range="this_month")
print(summary)
```

### Example 3: Basic Setup and Querying

```python
# Load APIs
load_openapi_spec("cash", "api_specs/cash_api.yaml", "https://api.company.com/cash/v1")
load_openapi_spec("securities", "api_specs/securities_api.yaml", "https://api.company.com/securities/v1")

# List available tools
tools = list_api_tools()
print(f"Available tools: {tools['count']}")

# Intelligent routing
result = intelligent_api_router("Show me pending payments")
print(result)
```

### Example 4: Financial Summary

```python
# Get comprehensive financial summary
summary = get_financial_summary(
    date_range="last_7_days",
    include_pending=True,
    include_approved=True
)
print(summary)
```

### Example 5: Parallel Execution

```python
# Execute multiple APIs in parallel
tool_calls = [
    {"tool_name": "cash_getPayments", "parameters": {"status": "pending"}},
    {"tool_name": "securities_getPortfolio", "parameters": {"account_id": "123"}},
    {"tool_name": "cls_getCLSSettlements", "parameters": {"status": "pending"}}
]

results = execute_parallel_apis(tool_calls)
print(results)
```

## 🏗️ Architecture (Slim)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Chatbot/LLM   │───▶│  OpenAPI MCP     │───▶│  REST APIs      │
│                 │    │  Server          │    │                 │
│ - Claude        │    │                  │    │ - Cash API      │
│ - ChatGPT       │    │ - Tool Registry  │    │ - Securities    │
│ - Custom        │    │ - Router         │    │ - CLS           │
└─────────────────┘    │ - Parallel Exec  │    │ - Mailbox       │
                       └──────────────────┘    └─────────────────┘
```

## 🔧 Configuration

### Server Configuration

```python
# In openapi_mcp_server.py
server = OpenAPIMCPServer()
server.run(
    transport="http",
    host="localhost",
    port=8000
)
```

### Logging Configuration

```python
# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚨 Error Handling

The system includes comprehensive error handling:

- **OpenAPI Validation**: Validates specifications before loading
- **API Call Errors**: Returns detailed error information
- **Authentication Errors**: Handles auth failures gracefully
- **Network Errors**: Manages connection issues

## ⚡ Performance

- **Parallel Execution**: Up to 5 parallel API calls by default
- **Connection Pooling**: Reuses HTTP connections
- **Caching**: Session-based caching for authentication
- **Timeout Handling**: Configurable request timeouts

## 🔒 Security Considerations

1. **Token Management**: Store tokens securely, not in code
2. **API Access**: Use least privilege principle for API access
3. **Network Security**: Use HTTPS for all API communications
4. **Input Validation**: Validate all user inputs before API calls

## 📁 Key Files
```
openapi_mcp_server.py   # Core server + FastAPI introspection
chatbot_app.py          # Chat/assistant proxy + simple UI route (/simple)
llm_mcp_bridge.py       # LLM agent & route helpers
mock_api_server.py      # Local mock cash API
start_demo.py           # Unified launcher
frontend/               # Minimal React SimpleChatApp (optional)
openapi_specs/          # Drop your OpenAPI YAML/JSON specs here
```

```
MCP_API/
├── openapi_mcp_server.py      # MCP server (OpenAPI -> tools)
├── chatbot_app.py             # FastAPI API + proxy + serves frontend build
├── fastmcp_client.py          # HTTP client used by chatbot
├── start_demo.py              # Convenience launcher
├── requirements.txt           # Python dependencies
├── README.md                  # Documentation
├── setup_guide.md             # Setup guide
├── api_specs/                 # Source OpenAPI specs (authoring)
├── openapi_specs/             # Loaded specs directory used by server
├── frontend/                  # React (Vite) UI source
└── tests/ (future)            # Placeholder for test suite
```

## 🧪 Quick Smoke

### Quick Demo
```bash
python start_demo.py
```

### Individual Testing
```bash
python openapi_mcp_server.py --transport http
python chatbot_app.py
```

### Manual Testing
1. Start MCP server: `python openapi_mcp_server.py --transport http`
2. Start chatbot: `python chatbot_app.py`
3. Open http://localhost:8080
4. Use the React UI (dev: http://localhost:5173 or http://localhost:5174) or call /chat

## 🐛 Troubleshooting

### Common Issues

1. **OpenAPI Validation Errors**
   - Ensure your YAML file is valid OpenAPI 3.0.3
   - Check for syntax errors in the specification

2. **Authentication Failures**
   - Verify credentials are correct
   - Check if the API requires different auth method

3. **Network Issues**
   - Verify API endpoints are accessible
   - Check firewall/proxy settings

4. **Tool Not Found Errors**
   - Ensure API specification is loaded
   - Check tool names in the generated tools list

### Debug Mode

Enable debug logging:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 📚 Notes
Removed legacy scripts: `mcp_client.py`, `mcp_server*.py`, `openapi.py`, demos.

- [Setup Guide](setup_guide.md): Comprehensive setup and usage guide
<!-- Legacy example script removed during cleanup -->
- [API Specifications](api_specs/): OpenAPI specifications for included APIs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the troubleshooting section
2. Review the setup guide
3. Use start_demo.py or direct scripts
4. Check server logs for errors

## 🔮 Roadmap (Lean)

- [ ] Enhanced NLP for better query understanding
- [ ] Response caching for improved performance
- [ ] Webhook support for real-time updates
- [ ] Advanced authentication methods
- [ ] Metrics and monitoring dashboard
- [ ] GraphQL support
- [ ] Rate limiting and throttling
- [ ] Multi-tenant support

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/fastmcp/fastmcp)
- OpenAPI 3.0.3 specification support
- Financial API patterns and best practices

---

## 🖥️ Simple React UI
We replaced the complex console with a minimal chat (`SimpleChatApp`). Switch back by editing `frontend/src/main.tsx` to render the old `App` component if still desired.

If you see only `Loading application…` at `http://localhost:8080`, you're viewing the backend placeholder. Run the dev UI separately:

### Dev Mode
```powershell
cd frontend
npm install   # first time
npm run dev
```
Open the Vite URL (default http://localhost:5173).

The UI will call the backend at http://localhost:8080 for:
- /status
- /tools
- /quick_actions
- /tool_meta/{tool_name}
- /run_tool
- /chat

### Production Build (Served by Backend)
```powershell
cd frontend
npm run build
```
Restart `python chatbot_app.py` and visit: http://localhost:8080/app/

### Change Backend URL
Edit `frontend/src/util/api.ts` BASE_URL.

### Common Symptoms
| Symptom | Cause | Fix |
|---------|-------|-----|
| Only placeholder text | Dev server not running | Run `npm run dev` and use port 5173 |
| 404 /src/main.tsx on 8080 | Expecting Vite assets from backend | Use 5173 or build & visit /app/ |
| Empty tool list | MCP server not on 8000 | Start `openapi_mcp_server.py --transport http` |
| CORS errors | Backend not restarted | Restart chatbot_app |

### Next Frontend Enhancements
- Credentials/login form
- WebSocket streaming chat
- Tool search & filtering
- LocalStorage persistence