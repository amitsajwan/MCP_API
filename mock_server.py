#!/usr/bin/env python3
"""
Mock API Server - Clean Implementation
Simplified mock server for testing financial APIs.
"""

import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import config


# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mock_server")

app = FastAPI(title="Mock Financial API Server", version="1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mock data
MOCK_ACCOUNTS = [
    {
        "id": "ACC001",
        "name": "Main Checking Account",
        "type": "CHECKING",
        "balance": 15420.50,
        "currency": "USD",
        "status": "ACTIVE"
    },
    {
        "id": "ACC002", 
        "name": "Savings Account",
        "type": "SAVINGS",
        "balance": 45230.75,
        "currency": "USD",
        "status": "ACTIVE"
    },
    {
        "id": "ACC003",
        "name": "Investment Account",
        "type": "INVESTMENT",
        "balance": 125000.00,
        "currency": "USD",
        "status": "ACTIVE"
    }
]

MOCK_PAYMENTS = [
    {
        "id": "PAY001",
        "accountId": "ACC001",
        "amount": 1500.00,
        "currency": "USD",
        "description": "Rent Payment",
        "status": "PENDING",
        "dueDate": (datetime.now() + timedelta(days=5)).isoformat(),
        "recipient": "Landlord LLC"
    },
    {
        "id": "PAY002",
        "accountId": "ACC001",
        "amount": 250.00,
        "currency": "USD",
        "description": "Utility Bill",
        "status": "PENDING",
        "dueDate": (datetime.now() + timedelta(days=3)).isoformat(),
        "recipient": "City Utilities"
    },
    {
        "id": "PAY003",
        "accountId": "ACC002",
        "amount": 5000.00,
        "currency": "USD",
        "description": "Investment Transfer",
        "status": "COMPLETED",
        "dueDate": datetime.now().isoformat(),
        "recipient": "Investment Fund"
    }
]

MOCK_SECURITIES = [
    {
        "id": "SEC001",
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "type": "STOCK",
        "quantity": 100,
        "currentPrice": 175.50,
        "totalValue": 17550.00,
        "currency": "USD"
    },
    {
        "id": "SEC002",
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "type": "STOCK",
        "quantity": 50,
        "currentPrice": 320.25,
        "totalValue": 16012.50,
        "currency": "USD"
    },
    {
        "id": "SEC003",
        "symbol": "TSLA",
        "name": "Tesla Inc.",
        "type": "STOCK",
        "quantity": 25,
        "currentPrice": 245.80,
        "totalValue": 6145.00,
        "currency": "USD"
    }
]

MOCK_MESSAGES = [
    {
        "id": "MSG001",
        "subject": "Payment Confirmation",
        "sender": "system@bank.com",
        "recipient": "user@example.com",
        "content": "Your payment of $1500.00 has been processed successfully.",
        "timestamp": datetime.now().isoformat(),
        "read": False,
        "priority": "NORMAL"
    },
    {
        "id": "MSG002",
        "subject": "Security Alert",
        "sender": "security@bank.com",
        "recipient": "user@example.com",
        "content": "Unusual login activity detected. Please verify your account.",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
        "read": True,
        "priority": "HIGH"
    }
]


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Mock Financial API Server",
        "version": "1.0",
        "endpoints": [
            "/login",
            "/accounts",
            "/payments",
            "/securities",
            "/messages"
        ]
    }


@app.post("/login")
async def login(request: Request):
    """Mock login endpoint."""
    try:
        body = await request.json()
        username = body.get("username", "")
        password = body.get("password", "")
        
        # Simple mock authentication
        if username and password:
            return {
                "status": "success",
                "message": "Login successful",
                "sessionId": "mock_session_12345",
                "user": {
                    "id": "USER001",
                    "username": username,
                    "name": "Mock User"
                }
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/accounts")
async def get_accounts():
    """Get all accounts."""
    return {
        "accounts": MOCK_ACCOUNTS,
        "total": len(MOCK_ACCOUNTS),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/accounts/{account_id}")
async def get_account(account_id: str):
    """Get specific account."""
    account = next((acc for acc in MOCK_ACCOUNTS if acc["id"] == account_id), None)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@app.get("/payments")
async def get_payments(status: str = None, account_id: str = None):
    """Get payments with optional filtering."""
    payments = MOCK_PAYMENTS.copy()
    
    if status:
        payments = [p for p in payments if p["status"].lower() == status.lower()]
    
    if account_id:
        payments = [p for p in payments if p["accountId"] == account_id]
    
    return {
        "payments": payments,
        "total": len(payments),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    """Get specific payment."""
    payment = next((p for p in MOCK_PAYMENTS if p["id"] == payment_id), None)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.post("/payments")
async def create_payment(request: Request):
    """Create a new payment."""
    try:
        body = await request.json()
        
        new_payment = {
            "id": f"PAY{len(MOCK_PAYMENTS) + 1:03d}",
            "accountId": body.get("accountId"),
            "amount": body.get("amount"),
            "currency": body.get("currency", "USD"),
            "description": body.get("description"),
            "status": "PENDING",
            "dueDate": body.get("dueDate", datetime.now().isoformat()),
            "recipient": body.get("recipient")
        }
        
        MOCK_PAYMENTS.append(new_payment)
        
        return {
            "status": "success",
            "message": "Payment created successfully",
            "payment": new_payment
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/securities")
async def get_securities():
    """Get all securities."""
    return {
        "securities": MOCK_SECURITIES,
        "total": len(MOCK_SECURITIES),
        "totalValue": sum(sec["totalValue"] for sec in MOCK_SECURITIES),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/securities/{security_id}")
async def get_security(security_id: str):
    """Get specific security."""
    security = next((sec for sec in MOCK_SECURITIES if sec["id"] == security_id), None)
    if not security:
        raise HTTPException(status_code=404, detail="Security not found")
    return security


@app.get("/messages")
async def get_messages(read: bool = None, priority: str = None):
    """Get messages with optional filtering."""
    messages = MOCK_MESSAGES.copy()
    
    if read is not None:
        messages = [m for m in messages if m["read"] == read]
    
    if priority:
        messages = [m for m in messages if m["priority"].lower() == priority.lower()]
    
    return {
        "messages": messages,
        "total": len(messages),
        "unread": len([m for m in MOCK_MESSAGES if not m["read"]]),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/messages/{message_id}")
async def get_message(message_id: str):
    """Get specific message."""
    message = next((m for m in MOCK_MESSAGES if m["id"] == message_id), None)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@app.put("/messages/{message_id}/read")
async def mark_message_read(message_id: str):
    """Mark message as read."""
    message = next((m for m in MOCK_MESSAGES if m["id"] == message_id), None)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message["read"] = True
    
    return {
        "status": "success",
        "message": "Message marked as read",
        "message_id": message_id
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0"
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Mock Financial API Server")
    parser.add_argument("--host", default=config.MOCK_API_HOST)
    parser.add_argument("--port", type=int, default=config.MOCK_API_PORT)
    
    args = parser.parse_args()
    
    logger.info(f"Starting mock API server on {args.host}:{args.port}")
    logger.info("Available endpoints:")
    logger.info("  GET  / - Root endpoint")
    logger.info("  POST /login - Mock login")
    logger.info("  GET  /accounts - List accounts")
    logger.info("  GET  /payments - List payments")
    logger.info("  GET  /securities - List securities")
    logger.info("  GET  /messages - List messages")
    logger.info("  GET  /health - Health check")
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=config.LOG_LEVEL.lower()
    )
    
    return 0


if __name__ == "__main__":
    exit(main())
