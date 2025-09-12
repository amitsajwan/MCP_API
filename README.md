# Intelligent MCP Bot with Azure GPT-4o

**Objective**: LLM understands user requirements and automatically executes the appropriate tools to fulfill them.

## 🧠 What This Does

The LLM intelligently:
- **Understands** your natural language requests
- **Selects** the right tools from 51 available APIs
- **Executes** tools automatically to fulfill your needs
- **Chains** multiple tools when needed
- **Handles** errors and retries gracefully

## 🚀 Quick Start

### Option 1: Demo Mode (No Azure Required)
```bash
python intelligent_bot_demo.py
```
- Works immediately without Azure credentials
- Shows intelligent tool selection and execution
- Demonstrates modern LLM capabilities

### Option 2: Full Mode (With Azure)
```bash
# Set Azure credentials
$env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
$env:AZURE_DEPLOYMENT_NAME="gpt-4o"
$env:AZURE_CLIENT_ID="your-client-id"
$env:AZURE_CLIENT_SECRET="your-client-secret"
$env:AZURE_TENANT_ID="your-tenant-id"

# Run the intelligent bot
python intelligent_bot.py
```

### Option 3: Web UI (Demo)
```bash
python web_ui_ws.py
```
- Open http://localhost:5000
- Configure credentials in the UI
- Chat with the intelligent bot
- Simplified single-user demo version

## 🎯 Example Interactions

```
You: "Show me all pending payments over $1000"
🧠 Analyzing your request...
🔧 Tools executed:
  - cash_api_getPayments: ✅ Success
    Args: {"status": "pending", "amount_min": 1000}
🤖 Response: I found 3 pending payments over $1000...

You: "I need to approve payment 12345 and create a CLS settlement"
🧠 Analyzing your request...
🔧 Tools executed:
  - cash_api_updatePayment: ✅ Success
    Args: {"payment_id": "12345", "status": "approved"}
  - cls_api_createSettlement: ✅ Success
    Args: {"payment_id": "12345", "amount": 5000}
🤖 Response: I've successfully approved payment 12345 and created a CLS settlement...
```

## 🔧 Available Tools

**51 tools** from 4 APIs:
- **Cash API**: Payments, transactions, approvals
- **CLS API**: Settlements, currency operations  
- **Mailbox API**: Message management
- **Securities API**: Trading, positions, orders

## 📁 Core Files

- `mcp_server_fastmcp2.py` - MCP server with 51 tools
- `mcp_client.py` - MCP client for Azure GPT-4o
- `mcp_service.py` - Modern LLM service
- `intelligent_bot.py` - Command-line intelligent bot
- `intelligent_bot_demo.py` - Demo version (no Azure required)
- `web_ui_ws.py` - WebSocket UI
- `templates/chat_ws.html` - Web UI template

## 🛠️ Installation

```bash
pip install -r requirements.txt
```

## 🎯 The Point

**This is NOT just a chat bot.** This is an intelligent system where:

1. **You ask** in natural language: "Show me all pending payments over $1000"
2. **LLM understands** what you need
3. **LLM selects** the right tool: `cash_api_getPayments`
4. **LLM executes** the tool with correct parameters
5. **LLM responds** with intelligent analysis of the results

**The LLM is the intelligence that orchestrates the tools to fulfill your requirements.**