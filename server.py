from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
import json
import os

app = FastAPI(title="MT5 Bridge", description="Connect MT5 to Mobile App", version="1.0")

# Allow all origins (for testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store data in memory
trading_data = {
    "accounts": {},
    "trades": [],
    "commands": [],
    "heartbeats": {}
}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "MT5 Trading Bridge",
        "version": "1.0",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "GET /": "This health check",
            "POST /api/mt5": "MT5 EA sends data here",
            "GET /api/mt5": "Mobile app fetches data",
            "POST /api/command": "Send command to EA",
            "GET /api/commands": "EA polls for commands"
        }
    }

@app.post("/api/mt5")
async def receive_mt5_data(request: Request):
    """MT5 EA sends updates to this endpoint"""
    try:
        data = await request.json()
        
        # Validate required fields
        if "account" not in data:
            raise HTTPException(status_code=400, detail="Missing 'account' field")
        
        account_id = str(data["account"])
        
        # Store account data
        trading_data["accounts"][account_id] = {
            **data,
            "last_update": datetime.now().isoformat(),
            "server_timestamp": datetime.now().timestamp()
        }
        
        # Update heartbeat
        trading_data["heartbeats"][account_id] = datetime.now().timestamp()
        
        print(f"✅ MT5 Update: Account {account_id}")
        
        return {
            "status": "success",
            "account": account_id,
            "received_at": datetime.now().isoformat(),
            "message": "Data received successfully"
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mt5")
async def get_mt5_data(account: str = None):
    """Mobile app fetches data from this endpoint"""
    try:
        if account:
            # Return specific account
            if account in trading_data["accounts"]:
                return trading_data["accounts"][account]
            else:
                raise HTTPException(status_code=404, detail=f"Account {account} not found")
        else:
            # Return all accounts with status
            online_accounts = []
            offline_accounts = []
            
            for acc_id, heartbeat in trading_data["heartbeats"].items():
                is_online = (datetime.now().timestamp() - heartbeat) < 300  # 5 minutes
                account_data = trading_data["accounts"].get(acc_id, {})
                
                if is_online:
                    online_accounts.append({
                        "account": acc_id,
                        **account_data,
                        "status": "online"
                    })
                else:
                    offline_accounts.append({
                        "account": acc_id,
                        **account_data,
                        "status": "offline"
                    })
            
            return {
                "online": online_accounts,
                "offline": offline_accounts,
                "total": len(trading_data["accounts"])
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/command")
async def send_command(request: Request):
    """Mobile app sends commands to EA"""
    try:
        data = await request.json()
        
        # Validate
        required_fields = ["account", "action"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing '{field}' field")
        
        # Generate command ID
        import hashlib
        cmd_id = hashlib.md5(f"{data['account']}{datetime.now()}".encode()).hexdigest()[:8]
        
        command = {
            "id": cmd_id,
            **data,
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "executed": False
        }
        
        # Store command
        trading_data["commands"].append(command)
        
        # Keep only last 50 commands
        if len(trading_data["commands"]) > 50:
            trading_data["commands"].pop(0)
        
        print(f"📱 Command: {data['account']} - {data['action']}")
        
        return {
            "status": "queued",
            "command_id": cmd_id,
            "message": f"Command '{data['action']}' queued for account {data['account']}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/commands")
async def get_commands(account: str):
    """EA polls for commands from this endpoint"""
    try:
        if not account:
            raise HTTPException(status_code=400, detail="Missing 'account' parameter")
        
        # Find pending commands for this account
        pending_commands = [
            cmd for cmd in trading_data["commands"]
            if cmd["account"] == account and not cmd["executed"]
        ]
        
        # Mark as executed (EA will process them)
        for cmd in pending_commands:
            cmd["executed"] = True
            cmd["executed_at"] = datetime.now().isoformat()
        
        return {
            "account": account,
            "pending_count": len(pending_commands),
            "commands": pending_commands
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify server is working"""
    return {
        "message": "MT5 Bridge Server is working!",
        "timestamp": datetime.now().isoformat(),
        "sample_request": {
            "method": "POST",
            "url": "/api/mt5",
            "body": {
                "account": "123456",
                "balance": 10000.50,
                "equity": 10123.45,
                "profit": 123.45,
                "open_trades": 3,
                "event": "heartbeat"
            }
        }
    }

# Start server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    print(f"🚀 Starting MT5 Bridge Server on port {port}")
    print(f"📡 Server will be available at: http://localhost:{port}")
    print(f"⏰ Started at: {datetime.now().isoformat()}")
    uvicorn.run(app, host="0.0.0.0", port=port)
