# Agentic Client Browser Demo

This folder contains scripts to demonstrate the agentic client example running in a browser interface.

## Prerequisites

Ensure all required servers are running:

1. OpenAPI MCP Server: `python openapi_mcp_server.py --transport http`
2. Mock API Server: `python mock_api_server.py --port 9001`
3. Chatbot App: `python -m uvicorn chatbot_app:app --host 0.0.0.0 --port 9081 --log-level info`

## Demo Options

### Option 1: Simple Browser Demo (No Additional Dependencies)

Run the simple demo script that opens your default browser:

```
python simple_agentic_demo.py
```

This script will:
- Open the Simple UI interface in your default browser
- Provide instructions for testing the agentic client functionality

### Option 2: Automated Playwright Demo

For an automated demonstration using Playwright:

#### Windows:

Run either:

```
run_agentic_demo.bat
```

Or with PowerShell:

```
.\run_agentic_demo.ps1
```

These scripts will:
1. Install Playwright requirements
2. Install Playwright browsers
3. Run the automated demo

#### Manual Setup:

If you prefer to install dependencies manually:

```
pip install -r playwright_requirements.txt
python -m playwright install
python agentic_client_demo.py
```

## What You'll See

The demo will showcase:

1. **Direct Assistant Mode**:
   - Queries with automatic tool execution
   - Examples: cash balance, transactions, and payments

This demonstrates how the agentic client from `agentic_client_example.py` is integrated with the browser interface, providing direct execution capabilities.