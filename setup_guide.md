# OpenAPI MCP Server Setup Guide

This guide will help you set up and use the OpenAPI MCP Server to expose your REST APIs as MCP tools for chatbot integration.

## Overview

The OpenAPI MCP Server dynamically loads OpenAPI specifications and exposes them as MCP tools, enabling:
- **Parallel API Execution**: Execute multiple APIs simultaneously
- **Intelligent Routing**: Automatically find relevant APIs based on natural language queries
- **Financial Summaries**: Get comprehensive summaries across cash, securities, CLS, and mailbox APIs
- **Payment Approvals**: Check approval status across all relevant APIs
- **Dynamic Tool Generation**: Automatically create MCP tools from OpenAPI specs

## Prerequisites

- Python 3.8+
- pip (Python package manager)

## Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import fastmcp, yaml, requests; print('Dependencies installed successfully!')"
   ```

## Project Structure

```
MCP_API/
├── openapi_mcp_server.py      # Main MCP server
├── requirements.txt           # Python dependencies
├── setup_guide.md            # This guide
├── example_usage.py          # Example usage script
├── api_specs/                # OpenAPI specifications
│   ├── cash_api.yaml         # Cash management API
│   ├── securities_api.yaml   # Securities trading API
│   ├── cls_api.yaml          # CLS settlement API
│   └── mailbox_api.yaml      # Mailbox API
└── README.md                 # Project documentation
```

## Quick Start

### 1. Start the MCP Server

```bash
python openapi_mcp_server.py
```

The server will start on `http://localhost:8000` by default.

### 2. Load API Specifications

Once the server is running, you can load OpenAPI specifications using the MCP tools:

```python
# Example: Load cash API
load_openapi_spec(
    spec_name="cash",
    yaml_path="api_specs/cash_api.yaml",
    base_url="https://api.company.com/cash/v1",
    auth_type="bearer",
    token="your_token_here"
)

# Example: Load securities API
load_openapi_spec(
    spec_name="securities",
    yaml_path="api_specs/securities_api.yaml",
    base_url="https://api.company.com/securities/v1",
    auth_type="basic",
    username="your_username",
    password="your_password"
)
```

## API Specifications

### Available APIs

1. **Cash Management API** (`cash_api.yaml`)
   - Payment management
   - Transaction history
   - Approval workflows
   - Cash summaries

2. **Securities Trading API** (`securities_api.yaml`)
   - Portfolio management
   - Trading operations
   - Settlement tracking
   - Security information

3. **CLS Settlement API** (`cls_api.yaml`)
   - Settlement instructions
   - Clearing status
   - Risk metrics
   - Position management

4. **Mailbox API** (`mailbox_api.yaml`)
   - Message management
   - Notifications
   - Alerts
   - Activity summaries

### Adding Your Own APIs

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

## Core MCP Tools

### 1. `load_openapi_spec`
Load and validate an OpenAPI specification.

**Parameters**:
- `spec_name`: Name for the API specification
- `yaml_path`: Path to OpenAPI YAML file
- `base_url`: Base URL for the API
- `auth_type`: Authentication type (none, basic, bearer, oauth2)
- `username`: Username for basic auth (optional)
- `password`: Password for basic auth (optional)
- `token`: Bearer token (optional)
- `priority`: Priority for this API (optional)

### 2. `list_api_tools`
List all available API tools with descriptions.

### 3. `execute_parallel_apis`
Execute multiple API calls in parallel.

**Parameters**:
- `tool_calls`: List of tool calls to execute

### 4. `intelligent_api_router`
Intelligently route queries to relevant APIs.

**Parameters**:
- `query`: Natural language query
- `max_parallel`: Maximum parallel API calls (default: 5)

### 5. `get_financial_summary`
Get comprehensive financial summary across multiple APIs.

**Parameters**:
- `date_range`: Date range for summary (optional)
- `include_pending`: Include pending approvals (default: true)
- `include_approved`: Include approved transactions (default: true)

### 6. `check_payment_approvals`
Check payment approval status across all relevant APIs.

**Parameters**:
- `payment_id`: Specific payment ID to check (optional)
- `status_filter`: Filter by status (pending, approved, rejected, all)

## Usage Examples

### Example 1: Basic API Loading and Querying

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

### Example 2: Financial Summary

```python
# Get comprehensive financial summary
summary = get_financial_summary(
    date_range="last_7_days",
    include_pending=True,
    include_approved=True
)
print(summary)
```

### Example 3: Payment Approval Check

```python
# Check payment approvals
approvals = check_payment_approvals(
    status_filter="pending"
)
print(approvals)
```

### Example 4: Parallel API Execution

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

## Natural Language Queries

The intelligent router supports various natural language queries:

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

## Authentication

### Supported Authentication Types

1. **None**: No authentication required
2. **Basic**: Username/password authentication
3. **Bearer**: Token-based authentication
4. **OAuth2**: OAuth 2.0 authentication (basic support)

### Example Authentication Setup

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

## Error Handling

The MCP server includes comprehensive error handling:

- **OpenAPI Validation**: Validates specifications before loading
- **API Call Errors**: Returns detailed error information
- **Authentication Errors**: Handles auth failures gracefully
- **Network Errors**: Manages connection issues

## Performance Considerations

- **Parallel Execution**: Up to 5 parallel API calls by default
- **Connection Pooling**: Reuses HTTP connections
- **Caching**: Session-based caching for authentication
- **Timeout Handling**: Configurable request timeouts

## Troubleshooting

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

Enable debug logging by modifying the logging level in `openapi_mcp_server.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Integration with Chatbots

### Claude Integration

```python
# Example Claude prompt
prompt = """
You have access to financial APIs through MCP tools. 
Use these tools to answer user questions about:
- Cash payments and transactions
- Securities trading and portfolio
- CLS settlements and clearing
- Mailbox messages and notifications

Available tools: {list of available tools}

User question: {user_question}
"""
```

### ChatGPT Integration

```python
# Example ChatGPT function calling
functions = [
    {
        "name": "intelligent_api_router",
        "description": "Route queries to relevant APIs",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural language query"},
                "max_parallel": {"type": "integer", "description": "Max parallel calls"}
            },
            "required": ["query"]
        }
    }
]
```

## Security Considerations

1. **Token Management**: Store tokens securely, not in code
2. **API Access**: Use least privilege principle for API access
3. **Network Security**: Use HTTPS for all API communications
4. **Input Validation**: Validate all user inputs before API calls

## Support and Contributing

For issues or contributions:
1. Check the troubleshooting section
2. Review the error logs
3. Ensure your OpenAPI spec is valid
4. Test with the provided examples

## Next Steps

1. **Customize APIs**: Add your own OpenAPI specifications
2. **Enhance Routing**: Improve the intelligent routing logic
3. **Add Caching**: Implement response caching for better performance
4. **Extend Authentication**: Add support for more auth methods
5. **Monitoring**: Add metrics and monitoring capabilities
