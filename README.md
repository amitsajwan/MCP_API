## OpenAPI MCP Server (Pure MCP, Client-Side LLM)

Proper MCP implementation that follows the real-world pattern:
- **MCP Server**: Pure tool provider (no LLM logic)
- **MCP Client**: LLM-based client that does planning and orchestration
- **UI**: Simple interface using the MCP client

Key points
- Auto-load OpenAPI specs from `openapi_specs/` and expose tools under `/mcp/*`
- **Automatic authentication** - set credentials once, auto-login on API calls
- **Client-side LLM planning** - MCP client handles tool orchestration
- **Pure MCP server** - no LLM logic, just tool provider
- Simple HTML UI at `/simple` (from `chatbot_app.py`)
- Clear logging for inbound requests and outbound API calls

Prerequisites
- Python 3.9+
- pip

Install
```powershell
pip install -r requirements.txt
```

Quick start
```powershell
# Optional: mock-only/demo
$env:FORCE_BASE_URL='http://localhost:9001'
python mock_api_server.py   # in a separate terminal (port 9001)

# MCP HTTP server
python openapi_mcp_server.py --transport http   # http://127.0.0.1:9000

# Chatbot UI/API
python chatbot_app.py                           # http://127.0.0.1:9080
```

Environment
- OPENAPI_DIR: directory of specs (default: ./openapi_specs)
- FORCE_BASE_URL or FORCE_BASE_URL_<SPEC>: override spec server URL
- MOCK_ALL=1: force all specs to mock base (default http://localhost:9001)
- AUTO_MOCK_FALLBACK=1: retry failed external calls against mock
- AZURE_OPENAI_ENDPOINT: required for LLM planning/summaries
- AZURE_OPENAI_DEPLOYMENT: optional (default: gpt-4)

Endpoints
- GET  /mcp/tools                     list tools
- GET  /mcp/tool_meta/{tool}          tool params
- POST /mcp/tools/{tool}              execute tool (body: {"arguments": {...}})
- GET  /mcp/prompts                   quick prompt suggestions
- POST /credentials                   set authentication credentials
- POST /login                        login using Basic Auth
- POST /assistant/chat                UI-friendly query execution with NL summary

Multi-step + simple chaining
- The agent may return multiple steps; they execute sequentially up to max_steps.
- You can reference prior results in later step arguments using placeholders like:
   {"accountId": "${cash_api_getCashSummary.accounts.0.id}"}

Logging
- Access logs for all HTTP endpoints
- Outbound API logs: method, URL, query/header keys, and a response preview

Troubleshooting
- Check /llm/status -> { provider: "openai", azure_openai_endpoint_present: true }
- If external endpoints fail, set FORCE_BASE_URL or use MOCK_ALL/AUTO_MOCK_FALLBACK

Notes
- Groq planning removed; Azure OpenAI-only to keep it simple and reliable.
- Older guides were removed to avoid duplication; this README is the source of truth.
 - Client-side planning and chaining is the default. Server is tools-only.

<!-- Parallel execution is not implemented in this edition; sequential multi-step only. -->

## 🏗️ Architecture (Proper MCP)

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   UI            │───▶│  MCP Client      │───▶│  MCP Server     │───▶│  REST APIs      │
│                 │    │  (LLM-based)     │    │  (Tools Only)   │    │                 │
│ - React/HTML    │    │                  │    │                 │    │ - Cash API      │
│ - User Input    │    │ - LLM Planning   │    │ - Tool Registry │    │ - Securities    │
│                 │    │ - Tool Execution │    │ - Auto Auth     │    │ - CLS           │
└─────────────────┘    └──────────────────┘    └─────────────────┘    │ - Mailbox       │
                                                                      └─────────────────┘
```

**Key Points:**
- **MCP Client** only calls MCP Server tools (never direct REST APIs)
- **MCP Server** embeds and exposes REST APIs as tools
- **REST APIs** are abstracted away from the client

## 🔄 Data Flow

1. **User Query** → "Show me pending payments"
2. **MCP Client** → LLM plans which MCP server tools to call
3. **MCP Client** → Calls `cash_api_getPayments` tool on MCP server
4. **MCP Server** → Executes tool, auto-authenticates with REST API
5. **MCP Server** → Returns result to MCP client
6. **MCP Client** → LLM generates natural language summary
7. **UI** → Displays result to user

**Important:** The MCP client never connects directly to REST APIs. All API interactions go through the MCP server's tool layer.

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
├── (guides removed)           # This README is the source of truth
├── api_specs/                 # Source OpenAPI specs (authoring)
├── openapi_specs/             # Loaded specs directory used by server
├── frontend/                  # React (Vite) UI source
└── tests/ (future)            # Placeholder for test suite
```

## 🔐 Authentication Flow

The new architecture uses **simple two-step authentication**:

1. **Set credentials**: Use `/credentials` endpoint or UI configuration
2. **Login**: Use `/login` endpoint to authenticate and get JSESSIONID
3. **Session management**: JSESSIONID is cached and reused
4. **Simple workflow**: Set credentials once, login when needed

### Example:
```bash
# Set credentials
curl -X POST http://localhost:9080/credentials \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass", "login_url": "http://api.company.com/login"}'

# Login to get JSESSIONID
curl -X POST http://localhost:9080/login \
  -H "Content-Type: application/json"

# Now use the assistant
curl -X POST http://localhost:9080/assistant/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me pending payments"}'
```

## 🚀 Getting Started

### Prerequisites
1. Copy `.env.example` to `.env` and configure your settings:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` file with your Azure OpenAI credentials and desired server configurations

### Quick Demo (All-in-One)
```bash
python start_demo.py
```

### Manual Startup (Step-by-Step)

#### 1. Start Mock API Server (Optional)
If you want to test with mock APIs instead of real ones:
```bash
python mock_api_server.py
```
- Uses `MOCK_API_HOST` and `MOCK_API_PORT` from `.env` (defaults: 127.0.0.1:9001)
- Set `FORCE_BASE_URL_CASH=http://localhost:9001` in `.env` to use mock APIs

#### 2. Start MCP Server
```bash
python openapi_mcp_server.py --transport http
```
- Uses `MCP_HOST` and `MCP_PORT` from `.env` (defaults: 127.0.0.1:9000)
- Loads OpenAPI specs from `OPENAPI_DIR` (default: ./openapi_specs)
- Exposes tools at `MCP_SERVER_ENDPOINT` (default: http://localhost:9000)

#### 3. Start Chatbot Application
```bash
python chatbot_app.py
```
- Uses `CHATBOT_HOST` and `CHATBOT_PORT` from `.env` (defaults: 0.0.0.0:9080)
- Connects to MCP server using `MCP_SERVER_ENDPOINT` from `.env`
- Access the web UI at: http://localhost:9080

### Configuration Notes
- **All server endpoints and ports are configured in `.env` file**
- **Base URLs for APIs (mock/real) are set via `FORCE_BASE_URL_*` variables**
- **MCP server endpoint is configured once in `MCP_SERVER_ENDPOINT`**
- Use `MOCK_ALL=true` to enable mock mode for all APIs

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
Removed legacy scripts and outdated guides; this README is the up-to-date reference.
– [API Specifications](openapi_specs/): OpenAPI specifications for included APIs

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

If you see only `Loading application…` at `http://localhost:9080`, you're viewing the backend placeholder. Run the dev UI separately:

### Dev Mode
```powershell
cd frontend
npm install   # first time
npm run dev
```
Open the Vite URL (default http://localhost:9517).

The UI will call the backend at http://localhost:9080 for:
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
Restart `python chatbot_app.py` and visit: http://localhost:9080/app/

### Change Backend URL
Edit `frontend/src/util/api.ts` BASE_URL.

### Common Symptoms
| Symptom | Cause | Fix |
|---------|-------|-----|
| Only placeholder text | Dev server not running | Run `npm run dev` and use port 9517 |
| 404 /src/main.tsx on 9080 | Expecting Vite assets from backend | Use 9517 or build & visit /app/ |
| Empty tool list | MCP server not on 9000 | Start `openapi_mcp_server.py --transport http` |
| CORS errors | Backend not restarted | Restart chatbot_app |

### Next Frontend Enhancements
- Credentials/login form
- WebSocket streaming chat
- Tool search & filtering
- LocalStorage persistence