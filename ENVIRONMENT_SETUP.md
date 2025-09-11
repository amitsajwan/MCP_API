# Environment Variables Setup Guide

## 🔐 **Required Environment Variables**

### **Azure OpenAI Configuration**
```bash
# Required for LLM functionality
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_DEPLOYMENT_NAME="gpt-4o"

# Optional for Azure AD authentication
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

### **API Credentials (Choose one method)**

#### **Method 1: Environment Variables (Recommended)**
```bash
# Basic authentication
export API_USERNAME="your-username"
export API_PASSWORD="your-password"

# API Key authentication
export API_KEY_NAME="X-API-Key"  # or whatever header name your API uses
export API_KEY_VALUE="your-api-key-value"

# Login URL (if different from default)
export LOGIN_URL="https://your-api.com/login"

# Force specific base URL (optional)
export FORCE_BASE_URL="https://your-api.com"
```

#### **Method 2: Runtime Configuration**
If you don't set environment variables, you can configure credentials at runtime using the `set_credentials` tool in the web interface.

### **Optional Configuration**
```bash
# Logging level
export LOG_LEVEL="INFO"  # DEBUG, INFO, WARNING, ERROR

# Custom OpenAPI directory (if not using default)
export OPENAPI_DIR="./openapi_specs"
```

## 🚀 **Quick Setup**

### **1. Create .env file (Recommended)**
Create a `.env` file in your project root:

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_DEPLOYMENT_NAME=gpt-4o

# API Credentials
API_USERNAME=your-username
API_PASSWORD=your-password
API_KEY_NAME=X-API-Key
API_KEY_VALUE=your-api-key
LOGIN_URL=https://your-api.com/login

# Optional
LOG_LEVEL=INFO
```

### **2. Load .env file**
```bash
# Install python-dotenv
pip install python-dotenv

# Load environment variables
source .env  # Linux/Mac
# or
set -a; source .env; set +a  # Linux/Mac
# or
Get-Content .env | ForEach-Object { $name, $value = $_.split('='); Set-Item -Path "env:$name" -Value $value }  # Windows PowerShell
```

### **3. Launch the demo**
```bash
python launch_modern_demo.py
```

## 🔧 **API-Specific Configuration**

### **Cash API**
```bash
export API_USERNAME="cash_api_user"
export API_PASSWORD="cash_api_password"
export LOGIN_URL="https://cash-api.example.com/auth"
```

### **CLS API**
```bash
export API_KEY_NAME="Authorization"
export API_KEY_VALUE="Bearer your-cls-token"
export FORCE_BASE_URL="https://cls-api.example.com"
```

### **Mailbox API**
```bash
export API_USERNAME="mailbox_user"
export API_PASSWORD="mailbox_password"
export API_KEY_NAME="X-Mailbox-Token"
export API_KEY_VALUE="your-mailbox-token"
```

### **Securities API**
```bash
export API_KEY_NAME="X-Securities-Key"
export API_KEY_VALUE="your-securities-key"
export FORCE_BASE_URL="https://securities-api.example.com"
```

## 🛡️ **Security Best Practices**

### **1. Never commit credentials to version control**
```bash
# Add to .gitignore
.env
*.env
.env.local
.env.production
```

### **2. Use different credentials for different environments**
```bash
# Development
.env.development

# Production
.env.production
```

### **3. Rotate credentials regularly**
- Update API keys periodically
- Use environment-specific credentials
- Monitor credential usage

## 🚨 **Troubleshooting**

### **Common Issues**

1. **"No credentials found in environment"**
   - Check if environment variables are set: `echo $API_USERNAME`
   - Verify .env file is loaded correctly
   - Use the `set_credentials` tool in the web interface

2. **"Azure OpenAI not configured"**
   - Verify `AZURE_OPENAI_ENDPOINT` is set correctly
   - Check `AZURE_DEPLOYMENT_NAME` matches your deployment
   - Ensure Azure credentials are valid

3. **"API authentication failed"**
   - Verify username/password or API key
   - Check if `LOGIN_URL` is correct
   - Ensure `FORCE_BASE_URL` points to correct API endpoint

### **Debug Mode**
```bash
export LOG_LEVEL=DEBUG
python launch_modern_demo.py
```

## 📝 **Example Complete Setup**

```bash
# 1. Create .env file
cat > .env << EOF
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://my-openai.openai.azure.com/
AZURE_DEPLOYMENT_NAME=gpt-4o

# API Credentials
API_USERNAME=myuser
API_PASSWORD=mypassword
API_KEY_NAME=X-API-Key
API_KEY_VALUE=abc123def456
LOGIN_URL=https://api.example.com/login

# Optional
LOG_LEVEL=INFO
EOF

# 2. Load environment
source .env

# 3. Launch demo
python launch_modern_demo.py
```

This setup will provide all necessary credentials for the modern LLM tool capabilities demo to work with your APIs.
