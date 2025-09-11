# Modern LLM Tool Capabilities Demo

## 🚀 **End-to-End Demonstration of Advanced LLM Tool Usage**

This project showcases the cutting-edge capabilities of modern LLMs when working with tools, demonstrating how they can intelligently select, chain, and adapt tool usage in complex scenarios.

## 🎯 **Modern LLM Capabilities Demonstrated**

### 1. **Intelligent Tool Selection** 🧠
- LLM analyzes user intent and selects the most appropriate tools
- Goes beyond simple keyword matching to understand context

### 2. **Complex Tool Chaining** 🔗
- LLM chains multiple tools in logical sequences
- Maintains context across tool calls

### 3. **Adaptive Tool Usage** 🔄
- LLM adapts tool usage based on results
- Dynamic decision-making based on real-time data

### 4. **Error Handling & Retry Logic** 🛡️
- Graceful handling of tool failures
- Alternative strategy execution

### 5. **Reasoning About Tool Outputs** 🧩
- High-level analysis and synthesis
- Insights generation from tool results

## 🚀 **Quick Start**

### 1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 2. **Configure Environment Variables**

#### **Azure OpenAI (Required)**
```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_DEPLOYMENT_NAME="gpt-4o"
```

#### **API Credentials (Choose one method)**

**Method 1: Environment Variables**
```bash
# Basic Authentication
export API_USERNAME="your-username"
export API_PASSWORD="your-password"

# API Key Authentication
export API_KEY_NAME="X-API-Key"
export API_KEY_VALUE="your-api-key"

# Optional: Custom URLs
export LOGIN_URL="https://your-api.com/login"
export FORCE_BASE_URL="https://your-api.com"
```

**Method 2: Web UI Configuration**
- Click the "🔐 Not Configured" status in the web interface
- Enter your credentials in the configuration dialog
- System automatically:
  1. Saves credentials to MCP server
  2. Performs login to get session ID (JSESSIONID)
  3. Uses session ID in headers for all API calls

**📋 See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) for detailed setup instructions**

### 3. **Launch Demo**
```bash
python launch_modern_demo.py
```

### 4. **Open Browser**
Navigate to `http://localhost:5000` and try these queries:
- "Check my account balance and recent transactions"
- "Get my financial summary and recommend investments"
- "Transfer money and invest in stocks"

## 📁 **Project Structure**

```
MCP_API/
├── mcp_server_fastmcp2.py    # MCP server with API tools
├── mcp_client.py             # MCP client for Azure GPT-4o
├── mcp_service.py            # Modern LLM service
├── web_ui_ws.py              # WebSocket web interface
├── modern_llm_demo.py        # Demo script
├── launch_modern_demo.py     # Launcher
├── templates/
│   └── chat_ws.html         # Chat interface
├── openapi_specs/           # API specifications
└── requirements.txt         # Dependencies
```

## 🏗 **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │  Flask WebSocket│    │  Modern LLM     │
│   (Real-time)   │◄──►│      UI         │◄──►│    Service      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │  Azure GPT-4o   │
                                               │ (Modern LLM)    │
                                               └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │   MCP Client    │
                                               │  (Tool Bridge)  │
                                               └─────────────────┘
                                                       │
                                                       ▼
                                               ┌─────────────────┐
                                               │   MCP Server    │
                                               │  (Tool Registry)│
                                               └─────────────────┘
```

## 🎨 **Visual Features**

### **Real-time Capability Indicators**
- 🧠 **Intelligent Selection** - Shows when LLM selects tools intelligently
- 🔗 **Tool Chaining** - Visualizes tool execution sequence
- 🔄 **Adaptive Usage** - Indicates when LLM adapts based on results
- 🛡️ **Error Handling** - Shows error recovery and retry logic
- 🧩 **Reasoning** - Displays when LLM reasons about outputs

### **Tool Chain Visualization**
```
Tool Chain: [get_balance] → [analyze_spending] → [recommend_budget]
```

## 🔧 **Available Tools**

The MCP server provides tools for:
- **Cash API**: Account balances, transactions, transfers
- **CLS API**: Payment status, settlement information
- **Mailbox API**: Message management, notifications
- **Securities API**: Portfolio management, trading

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Azure Authentication Failed**
   - Check your Azure credentials and permissions
   - Ensure the Azure OpenAI resource is accessible

2. **MCP Server Connection Failed**
   - Verify the server command in `mcp_service.py`
   - Check that `mcp_server_fastmcp2.py` is working

3. **Tool Calls Failing**
   - Check the OpenAPI specifications in `openapi_specs/`
   - Verify API endpoints are accessible

### **Debug Mode**

Run with debug logging:
```bash
export LOG_LEVEL=DEBUG
python launch_modern_demo.py
```

## 📝 **Development**

### **Adding New Tools**

1. Add OpenAPI specification to `openapi_specs/`
2. Update `mcp_server_fastmcp2.py` to include the new API
3. Restart the server

### **Customizing the UI**

Edit `templates/chat_ws.html` to modify the web interface appearance and behavior.

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 **Acknowledgments**

- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP implementation
- [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) for the language model
- [Flask](https://flask.palletsprojects.com/) for the web framework