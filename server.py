# server.py - FastAPI server for MT5 bridge
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import json
import os
from datetime import datetime
import hashlib

app = FastAPI(title="MT5 Bridge Server", version="1.0")

# CORS for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (for testing)
# In production, connect to Supabase
storage = {
    "accounts": {},
    "trades": [],
    "commands": [],
    "heartbeats": {}
}

# Simple authentication (replace with Supabase in production)
API_KEYS = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "MT5 Trading Bridge",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "POST /api/mt5/update": "MT5 EA sends data",
            "GET /api/mt5/status": "Mobile app fetches data",
            "POST /api/mt5/command": "Mobile app sends commands",
            "GET /api/mt5/heartbeat": "Check server health"
        }
    }

@app.get("/api/mt5/heartbeat")
async def heartbeat():
    """Server health check"""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat(),
        "accounts_count": len(storage["accounts"]),
        "trades_count": len(storage["trades"])
    }

@app.post("/api/mt5/update")
async def receive_mt5_update(request: Request):
    """MT5 EA sends trading data here"""
    try:
        data = await request.json()
        
        # Required fields
        if "account" not in data:
            raise HTTPException(400, "Missing 'account' field")
        
        account_id = str(data["account"])
        
        # Store/update account data
        storage["accounts"][account_id] = {
            **data,
            "last_update": datetime.now().isoformat(),
            "server_received_at": datetime.now().timestamp()
        }
        
        # Store heartbeat
        storage["heartbeats"][account_id] = datetime.now().timestamp()
        
        # If trade data included, store it
        if "trade" in data:
            trade_data = {
                **data["trade"],
                "account": account_id,
                "server_timestamp": datetime.now().isoformat()
            }
            storage["trades"].append(trade_data)
            
            # Keep only last 100 trades
            if len(storage["trades"]) > 100:
                storage["trades"].pop(0)
        
        print(f"✅ MT5 Update: Account {account_id} - {data.get('event', 'update')}")
        
        return {
            "status": "success",
            "account": account_id,
            "received_at": datetime.now().isoformat(),
            "message": "Data received successfully"
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(500, f"Internal server error: {str(e)}")

@app.get("/api/mt5/status")
async def get_account_status(account: str = None):
    """Mobile app fetches account status"""
    try:
        if account:
            # Return specific account
            if account in storage["accounts"]:
                return storage["accounts"][account]
            else:
                raise HTTPException(404, f"Account {account} not found")
        else:
            # Return all accounts
            return {
                "accounts": storage["accounts"],
                "summary": {
                    "total_accounts": len(storage["accounts"]),
                    "online_accounts": sum(
                        1 for hb in storage["heartbeats"].values() 
                        if (datetime.now().timestamp() - hb) < 300  # 5 minutes
                    ),
                    "total_trades": len(storage["trades"])
                }
            }
            
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/mt5/command")
async def send_command(request: Request):
    """Mobile app sends commands to EA"""
    try:
        data = await request.json()
        
        # Validate command
        required_fields = ["account", "command", "action"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(400, f"Missing '{field}' field")
        
        # Store command for EA to poll
        command_id = hashlib.md5(f"{data['account']}{datetime.now()}".encode()).hexdigest()[:8]
        
        command_entry = {
            "id": command_id,
            **data,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "executed": False
        }
        
        storage["commands"].append(command_entry)
        
        # Keep only recent commands
        if len(storage["commands"]) > 50:
            storage["commands"].pop(0)
        
        print(f"📱 Command: {data['account']} - {data['command']} - {data['action']}")
        
        return {
            "status": "queued",
            "command_id": command_id,
            "message": f"Command '{data['action']}' queued for account {data['account']}"
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/mt5/commands")
async def get_pending_commands(account: str):
    """EA polls for pending commands"""
    try:
        pending = [
            cmd for cmd in storage["commands"] 
            if cmd["account"] == account and not cmd["executed"]
        ]
        
        # Mark as executed (EA will process)
        for cmd in pending:
            cmd["executed"] = True
            cmd["executed_at"] = datetime.now().isoformat()
        
        return {
            "account": account,
            "pending_commands": len(pending),
            "commands": pending
        }
        
    except Exception as e:
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"🚀 Starting MT5 Bridge Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
