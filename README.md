# MCP Bot - My Personal API Assistant

A smart assistant that understands what you need and automatically uses the right API tools to help you.

## 🧠 What This Does

My bot is smart and can:
- **Understand** what you're asking for in plain English
- **Pick** the right tools from 51 different APIs
- **Do** the work automatically for you
- **Chain** multiple tools together when needed
- **Handle** problems and try again if something goes wrong

## 🚀 Quick Start

### Easy Way (Recommended)
```bash
python start_bot.py
```
Just run this and pick what you want!

### Option 1: Web Interface
```bash
python web_ui_ws.py
```
- Open http://localhost:5000
- Set up your API credentials
- Start chatting with your bot
- Clean, simple interface

### Option 2: Full Mode (With Azure)
```bash
# Set Azure credentials first
$env:AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
$env:AZURE_DEPLOYMENT_NAME="gpt-4o"
$env:AZURE_CLIENT_ID="your-client-id"
$env:AZURE_CLIENT_SECRET="your-client-secret"
$env:AZURE_TENANT_ID="your-tenant-id"

# Then run
python intelligent_bot.py
```

### Option 3: Demo Mode (No Azure)
```bash
python intelligent_bot_demo.py
```
- Works immediately without Azure credentials
- Shows how tools work
- Good for testing

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

## 🎯 Why I Built This

This isn't just another chatbot. It's a smart assistant that actually does things for you:

1. **You tell me** what you need: "Show me all pending payments over $1000"
2. **I figure out** what tools to use
3. **I pick** the right API: `cash_api_getPayments`
4. **I run** the tool with the right settings
5. **I give you** a clear answer with the results

**I built this because I wanted a bot that actually helps instead of just talking.**