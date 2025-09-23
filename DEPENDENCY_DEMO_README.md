# Dependency-Aware MCP Server Demo

## 🎯 **The Problem**

When a user asks "Get my emails", the current MCP server fails because it doesn't understand that `getMails` needs an `account_id` parameter that must be obtained from `getAccounts` first.

## 🚀 **The Solution**

A **dependency-aware MCP server** that:
- ✅ **Understands prerequisites** for each tool
- ✅ **Provides clear guidance** on what's needed
- ✅ **Offers smart tools** that can resolve dependencies automatically
- ✅ **Gives MCP clients** all the information they need to make intelligent decisions

## 🧪 **Demo Results**

### **Scenario 1: User asks "Get my emails"**
```json
{
  "status": "prerequisite_required",
  "message": "account_id is required to get emails",
  "prerequisite": {
    "operation": "getAccounts",
    "purpose": "Get account_id for email retrieval"
  },
  "suggested_workflow": [
    "1. Call getAccounts() to get available accounts",
    "2. Select account_id from the results", 
    "3. Call getMails(account_id='acc_123') with the selected account_id"
  ]
}
```

### **Scenario 2: MCP Client gets accounts first**
```json
{
  "status": "success",
  "data": [
    {"id": "acc_1", "name": "Personal Account", "type": "checking"},
    {"id": "acc_2", "name": "Business Account", "type": "business"}
  ],
  "message": "Found 3 accounts"
}
```

### **Scenario 3: MCP Client calls getMails with account_id**
```json
{
  "status": "success",
  "data": [
    {"id": "mail_1", "subject": "Welcome Email", "from": "system@bank.com"},
    {"id": "mail_2", "subject": "Account Statement", "from": "statements@bank.com"}
  ],
  "message": "Found 2 emails for account acc_1"
}
```

## 🔄 **Complete Workflow**

```
User Query: "Get my emails"
    ↓
MCP Client calls get_mails() without parameters
    ↓
Result: Prerequisite required - need account_id
    ↓
MCP Client calls get_accounts() to get available accounts
    ↓
Result: Returns list of accounts with IDs
    ↓
MCP Client calls get_mails(account_id='acc_1')
    ↓
Result: Returns emails for the specified account
```

## 🎯 **Key Benefits**

### **For MCP Server:**
- 🧠 **Understands dependencies** between API endpoints
- 📊 **Provides rich metadata** about prerequisites
- 🔗 **Maps relationships** between tools
- 🎨 **Creates smart tools** with auto-resolution

### **For MCP Client:**
- ⚡ **Clear guidance** on what's needed
- 🔄 **Intelligent workflow** orchestration
- 🎯 **Smart parameter** handling
- 📈 **Efficient API** usage

## 🚀 **Smart Tool Features**

### **1. Dependency Detection**
- Automatically detects when parameters need other endpoints
- Maps relationships between API operations
- Provides prerequisite information

### **2. Smart Parameter Resolution**
- Can resolve `account_id` from `user_id`
- Can resolve `account_id` from account name
- Handles multiple identifier types

### **3. Intelligent Guidance**
- Suggests next steps when prerequisites are missing
- Provides example usage patterns
- Shows available options

## 🛠️ **Implementation**

### **Files Created:**
- `simple_dependency_mcp_server.py` - Working MCP server with dependency awareness
- `demo_dependency_concept.py` - Simple demo without MCP complexity
- `test_dependency_flow.py` - Test client for the MCP server

### **Run the Demo:**
```bash
python3 demo_dependency_concept.py
```

### **Key Components:**
1. **Dependency Analyzer** - Detects prerequisites from OpenAPI specs
2. **Smart Tool Creator** - Creates tools that understand their dependencies
3. **Intelligent Response Handler** - Provides guidance when prerequisites are missing

## 🎯 **Next Steps**

This simple implementation demonstrates the core concept. The next step would be to enhance it with:

1. **Gen AI Integration** - Use LLM to analyze complex OpenAPI specs
2. **Advanced Dependency Detection** - Handle more complex relationship patterns
3. **Smart Parameter Inference** - Automatically resolve parameters from context
4. **Workflow Automation** - Automatically chain related operations

## 🎉 **Conclusion**

This demo shows that **dependency-aware MCP servers** are not only possible but provide significant value by:
- Understanding API relationships
- Providing intelligent guidance
- Enabling smart workflow orchestration
- Making APIs more accessible and user-friendly

The concept works and can be extended to handle any level of API complexity!