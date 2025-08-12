#!/usr/bin/env python3
"""Mock Financial APIs (Cash) for local development.
Serves simplified JSON for endpoints defined in cash_api spec.
Run: python mock_api_server.py --port 9001
Then set FORCE_BASE_URL_CASH=http://localhost:9001 (or use launcher --with-mock) before starting openapi_mcp_server.py.
"""
import random, string, argparse, uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Mock Cash API", version="1.0")

# --- Models (minimal) ---
class Payment(BaseModel):
    id: str
    amount: float
    currency: str = "USD"
    status: str
    created_at: str
    updated_at: str
    description: Optional[str] = None
    recipient: Optional[str] = None
    requester_id: Optional[str] = None
    approver_id: Optional[str] = None

class PaymentRequest(BaseModel):
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    recipient: str
    requester_id: str

class PaymentUpdate(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None
    recipient: Optional[str] = None

class Transaction(BaseModel):
    id: str
    type: str
    amount: float
    currency: str = "USD"
    description: Optional[str] = None
    timestamp: str
    balance_after: float

payments_store: dict = {}
transactions_store: List[Transaction] = []

# seed some sample data
for i in range(5):
    pid = f"P{i+1:03d}"
    now = datetime.utcnow().isoformat()
    payments_store[pid] = Payment(
        id=pid,
        amount=round(random.uniform(100, 2500),2),
        status=random.choice(["pending","approved","rejected","completed"]),
        created_at=now,
        updated_at=now,
        description=f"Seed payment {i+1}",
        recipient=f"Vendor {i+1}",
        requester_id="REQ1"
    )

balance = 10000.0
for i in range(10):
    t_amount = round(random.uniform(50,500),2)
    t_type = random.choice(["credit","debit"])
    balance = balance + t_amount if t_type=="credit" else balance - t_amount
    transactions_store.append(Transaction(
        id=f"T{i+1:03d}",
        type=t_type,
        amount=t_amount,
        description=f"Seed transaction {i+1}",
        timestamp=(datetime.utcnow()-timedelta(minutes=i*10)).isoformat(),
        balance_after=round(balance,2)
    ))

@app.get("/payments")
def get_payments(status: Optional[str] = None):
    data = list(payments_store.values())
    if status:
        data = [p for p in data if p.status == status]
    return {"payments": data, "total_count": len(data)}

@app.post("/payments", status_code=201)
def create_payment(req: PaymentRequest):
    pid = ''.join(random.choices(string.ascii_uppercase+string.digits, k=8))
    now = datetime.utcnow().isoformat()
    payment = Payment(id=pid, amount=req.amount, currency=req.currency, status="pending", created_at=now, updated_at=now, description=req.description, recipient=req.recipient, requester_id=req.requester_id)
    payments_store[pid] = payment
    return payment

@app.get("/payments/{payment_id}")
def get_payment(payment_id: str):
    p = payments_store.get(payment_id)
    if not p: raise HTTPException(404, "Payment not found")
    return p

@app.put("/payments/{payment_id}")
def update_payment(payment_id: str, upd: PaymentUpdate):
    p = payments_store.get(payment_id)
    if not p: raise HTTPException(404, "Payment not found")
    data = p.dict()
    for field, value in upd.dict(exclude_unset=True).items():
        data[field] = value
    data['updated_at'] = datetime.utcnow().isoformat()
    new_p = Payment(**data)
    payments_store[payment_id] = new_p
    return new_p

@app.post("/payments/{payment_id}/approve")
def approve_payment(payment_id: str, approver_id: str, comments: str | None = None):
    p = payments_store.get(payment_id)
    if not p: raise HTTPException(404, "Payment not found")
    p.status = "approved"; p.approver_id = approver_id; p.updated_at = datetime.utcnow().isoformat()
    return p

@app.post("/payments/{payment_id}/reject")
def reject_payment(payment_id: str, rejector_id: str, reason: str | None = None):
    p = payments_store.get(payment_id)
    if not p: raise HTTPException(404, "Payment not found")
    p.status = "rejected"; p.approver_id = rejector_id; p.updated_at = datetime.utcnow().isoformat()
    return p

@app.get("/transactions")
def get_transactions(type: str | None = None):
    data = list(transactions_store)
    if type:
        data = [t for t in data if t.type == type]
    return {"transactions": data, "total_count": len(data)}

@app.get("/summary")
def cash_summary(date_range: str | None = None, include_pending: bool = True):
    pending = [p for p in payments_store.values() if p.status == "pending"]
    total_balance = transactions_store[-1].balance_after if transactions_store else 10000.0
    return {
        "total_balance": total_balance,
        "currency": "USD",
        "pending_approvals": len(pending),
        "pending_amount": round(sum(p.amount for p in pending),2),
        "recent_transactions": transactions_store[:5]
    }

if __name__ == "__main__":
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    env_port = os.environ.get('MOCK_API_PORT')
    default_port = int(env_port) if env_port and env_port.isdigit() else 9001
    parser.add_argument('--port', type=int, default=default_port)
    args = parser.parse_args()
    uvicorn.run("mock_api_server:app", host=args.host, port=args.port, reload=False)
