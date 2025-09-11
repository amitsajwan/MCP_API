# 🔍 Comprehensive Logging Guide

This guide explains the logging system implemented across all MCP components to help you understand the flow and debug issues.

## 📁 Log Files

The system creates separate log files for each component:

- **`web_ui.log`** - Web UI (Flask-SocketIO) logs
- **`mcp_service.log`** - MCP Service (LLM orchestration) logs  
- **`mcp_client.log`** - MCP Client (Azure OpenAI) logs
- **`mcp_server.log`** - MCP Server (API tools) logs

## 🔄 Complete Flow Logging

### 1. **Web UI → MCP Service → MCP Client → MCP Server**

```
[UI] Client connected: session123
[UI] Initializing MCP service for session123
[MCP_SERVICE] Starting initialization...
[MCP_SERVICE] Creating Azure client...
[MCP_CLIENT] Creating Azure OpenAI client...
[MCP_CLIENT] Azure OpenAI client created
[MCP_SERVICE] Azure client created
[MCP_SERVICE] Parsing MCP server command: python mcp_server_fastmcp2.py --transport stdio
[MCP_SERVICE] Creating PythonStdioTransport...
[MCP_SERVICE] Transport created
[MCP_SERVICE] Creating MCP client...
[MCP_SERVICE] MCP client created
[MCP_SERVICE] Connecting to MCP server...
[MCP_SERVER] 🚀 Initializing FastMCP 2.0 Server...
[MCP_SERVER] 📂 Loading API specifications...
[MCP_SERVER] 🔧 Registering FastMCP 2.0 tools...
[MCP_SERVER] ✅ FastMCP 2.0 Server initialized with 4 API specs
[MCP_SERVICE] Connected to MCP server
[MCP_SERVICE] Loading tools...
[MCP_CLIENT] Fetching tools from MCP server...
[MCP_CLIENT] Received 51 tools from MCP server
[MCP_CLIENT] Processing tool 1/51: cash_api_getPayments
[MCP_CLIENT] Processing tool 2/51: cash_api_createPayment
...
[MCP_CLIENT] Loaded 51 tools from MCP server
[MCP_SERVICE] Loaded 51 tools
[MCP_SERVICE] Modern LLM Service initialized successfully
[UI] MCP Service initialized successfully
```

### 2. **Credential Configuration Flow**

```
[UI] Setting credentials for session123
[UI] Updating environment variables for session123
[UI] Set API_USERNAME for session123
[UI] Set API_PASSWORD for session123
[UI] Set LOGIN_URL for session123
[UI] Starting login process for session123
[UI] Calling set_credentials tool for session123
[MCP_SERVICE] Calling MCP tool: set_credentials
[MCP_SERVER] 🔐 Credentials stored successfully for user: myuser
[UI] set_credentials tool completed for session123
[UI] Calling perform_login tool for session123
[MCP_SERVICE] Calling MCP tool: perform_login
[MCP_SERVER] 🔐 Attempting login to http://localhost:8080/auth/login
[MCP_SERVER] ✅ Authentication successful
[UI] perform_login tool completed for session123
[UI] Login successful for session123, session: abc123...
```

### 3. **Message Processing Flow**

```
[UI] Received message from session123: 'Show me all pending payments over $1000'
[UI] Processing message with MCP service for session123
[MCP_SERVICE] Processing message: 'Show me all pending payments over $1000...'
[MCP_SERVICE] Building conversation context...
[MCP_SERVICE] Total messages: 2
[MCP_SERVICE] Calling Azure OpenAI...
[MCP_SERVICE] Azure OpenAI response received
[MCP_SERVICE] LLM requested 1 tool calls
[MCP_SERVICE] Executing tool 1/1: cash_api_getPayments
[MCP_SERVICE] Tool args: {'status': 'pending', 'amount_min': 1000}
[MCP_SERVICE] Calling MCP tool: cash_api_getPayments
[MCP_SERVER] 🔧 Executing tool: cash_api_getPayments
[MCP_SERVER] 🔧 Spec: cash_api, Method: get, Path: /payments
[MCP_SERVER] 🔧 Arguments: ['status', 'amount_min']
[MCP_SERVER] 🔐 Checking authentication for cash_api_getPayments
[MCP_SERVER] ✅ Authentication successful for cash_api_getPayments
[MCP_SERVER] 🔗 Base URL: http://localhost:8080, Final URL: http://localhost:8080/payments
[MCP_SERVER] ❓ Query param: status = pending
[MCP_SERVER] ❓ Query param: amount_min = 1000
[MCP_SERVER] 🌐 Making get request to http://localhost:8080/payments
[MCP_SERVER] 📡 Response status: 200
[MCP_SERVER] ✅ JSON response parsed successfully
[MCP_SERVER] ✅ Tool cash_api_getPayments executed successfully
[MCP_SERVICE] ✅ Tool cash_api_getPayments completed successfully
[MCP_SERVICE] Tool result truncated: 1500 chars
[MCP_SERVICE] Getting final response from LLM...
[MCP_SERVICE] Final response received
[MCP_SERVICE] Analyzing capabilities...
[MCP_SERVICE] Capabilities: ['🧠 Intelligent Tool Selection', '🔄 Adaptive Tool Usage']
[MCP_SERVICE] Message processing completed successfully
[UI] MCP processing completed for session123
[UI] Executed 1 tools for session123
[UI] Tool 1/1: cash_api_getPayments - ✅ Success
[UI] Capabilities demonstrated for session123: ['🧠 Intelligent Tool Selection', '🔄 Adaptive Tool Usage']
[UI] Sending response to session123: 'I found 3 pending payments over $1000...'
```

## 🎯 Log Categories

### **UI Logs** `[UI]`
- Client connections/disconnections
- Message reception and processing
- MCP service initialization
- Credential configuration
- Tool execution visualization

### **MCP Service Logs** `[MCP_SERVICE]`
- Service initialization
- Azure client creation
- MCP client connection
- Tool loading and preparation
- Message processing with LLM
- Tool execution orchestration

### **MCP Client Logs** `[MCP_CLIENT]`
- Azure OpenAI client creation
- Tool fetching from MCP server
- Tool processing and formatting

### **MCP Server Logs** `[MCP_SERVER]`
- Server initialization
- API specification loading
- Tool registration
- Authentication and login
- API request execution
- Response processing

## 🔍 Debugging Common Issues

### **Authentication Issues**
Look for these log patterns:
```
[MCP_SERVER] ❌ Authentication failed for tool_name
[MCP_SERVER] No credentials set for authentication
[MCP_SERVER] Authentication failed: [error details]
```

### **Tool Execution Issues**
Look for these log patterns:
```
[MCP_SERVER] ❌ API request failed for tool_name: [error details]
[MCP_SERVICE] ❌ Tool call failed: tool_name - [error details]
[UI] ❌ Tool error: [error details]
```

### **Connection Issues**
Look for these log patterns:
```
[MCP_SERVICE] ❌ Failed to initialize Modern LLM Service: [error details]
[MCP_CLIENT] ❌ Error in async initialization: [error details]
[UI] ❌ Error initializing MCP service: [error details]
```

### **LLM Issues**
Look for these log patterns:
```
[MCP_SERVICE] ❌ Error processing message: [error details]
[MCP_SERVICE] ❌ Tool call failed: [error details]
```

## 🛠️ Log Viewing Tools

### **1. View All Logs in Real-time**
```bash
python view_logs.py
# Choose option 1
```

### **2. View Specific Log File**
```bash
python view_logs.py
# Choose option 2, then select file
```

### **3. Search for Specific Issues**
```bash
python view_logs.py
# Choose option 4, then enter search term
```

### **4. Manual Log Viewing**
```bash
# View all logs
tail -f web_ui.log mcp_service.log mcp_client.log mcp_server.log

# View specific log
tail -f web_ui.log

# Search for errors
grep -i "error" *.log

# Search for specific tool
grep -i "cash_api_getPayments" *.log
```

## 📊 Log Analysis Tips

### **1. Follow the Flow**
Start from `[UI]` logs and follow the flow through each component.

### **2. Look for Error Patterns**
- `❌` indicates errors
- `⚠️` indicates warnings
- `✅` indicates success

### **3. Check Timing**
Look for long delays between log entries to identify bottlenecks.

### **4. Trace Tool Execution**
Follow a specific tool call from UI → Service → Client → Server.

### **5. Monitor Authentication**
Check if credentials are being set and login is successful.

## 🚀 Quick Debugging Commands

```bash
# Check if all components are running
ps aux | grep python

# View recent errors
grep -i "error" *.log | tail -20

# Check authentication status
grep -i "authentication\|login" *.log | tail -10

# Monitor tool execution
grep -i "executing tool" *.log | tail -10

# Check MCP service status
grep -i "mcp service" *.log | tail -10
```

This comprehensive logging system will help you understand exactly what's happening at each step of the process and quickly identify and fix any issues! 🎉
