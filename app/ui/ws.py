import asyncio
import json
import random
from pathlib import Path
import sys
import pandas as pd

# --- PYTHONPATH fix ---
# Ensure the app's root directory is in the Python path.
# This is a workaround for issues with how Uvicorn might be launched.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.data.storage import DataStorage

# --- App Setup ---
app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# --- In-memory Data & Services ---
data_storage = DataStorage()

# --- Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Background Task for Broadcasting Data ---
async def broadcast_data():
    """Simulates a live data feed for OHLCV and agent signals."""
    last_price = 1.0
    try:
        df = data_storage.read_ohlcv('BTCUSDT', '1h')
        last_price = df['close'].iloc[-1] if not df.empty else 60000
    except Exception:
        last_price = 60000

    while True:
        await asyncio.sleep(2) # Broadcast every 2 seconds

        # 1. Simulate new OHLCV kline
        new_price = last_price * (1 + random.uniform(-0.001, 0.001))
        kline = {
            "time": pd.Timestamp.utcnow().isoformat(),
            "open": last_price, "high": max(last_price, new_price),
            "low": min(last_price, new_price), "close": new_price
        }
        await manager.broadcast(json.dumps({"type": "ohlcv_update", "kline": kline}))
        last_price = new_price

        # 2. Simulate agent signals randomly
        if random.random() < 0.1: # 10% chance of a signal
            agent = random.choice(['Agent_Grendel', 'Agent_Beowulf'])
            signal = random.choice(['buy', 'sell'])
            signal_data = {
                "type": "signal", "timestamp": kline['time'],
                "agent": agent, "signal": signal, "price": new_price
            }
            await manager.broadcast(json.dumps(signal_data))


@app.on_event("startup")
async def startup_event():
    # Start the background task
    asyncio.create_task(broadcast_data())

# --- HTTP Routes ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/{page_name}.html", response_class=HTMLResponse)
async def read_page(request: Request, page_name: str):
    """
    Serves any .html file from the templates directory.
    """
    try:
        return templates.TemplateResponse(f"{page_name}.html", {"request": request})
    except Exception:
        raise HTTPException(status_code=404, detail="Page not found")


@app.get("/api/ohlcv/{symbol}/{interval}")
async def get_ohlcv(symbol: str, interval: str):
    try:
        df = data_storage.read_ohlcv(symbol, interval)
        # Convert timestamp to string for JSON compatibility
        df.index = df.index.strftime('%Y-%m-%dT%H:%M:%SZ')
        return df.to_dict(orient='records')
    except Exception as e:
        return {"error": str(e)}

# --- WebSocket Route ---
@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "chat_message":
                # Simulate agent debate
                user_question = message.get("text", "")

                # Grendel's (Aggressive) response
                await asyncio.sleep(0.5)
                grendel_response = f"Volatility is my playground. I see a clear momentum signal. We should go all in. Target: {last_price * 1.05:.0f}."
                await manager.broadcast(json.dumps({
                    "type": "chat_response", "sender": "Grendel",
                    "text": grendel_response, "persona": "Agent_Grendel"
                }))

                # Beowulf's (Cautious) response
                await asyncio.sleep(1)
                beowulf_response = f"Caution is advised. The Z-score is neutral, and sentiment is unstable. A defensive stance is prudent. Wait for confirmation."
                await manager.broadcast(json.dumps({
                    "type": "chat_response", "sender": "Beowulf",
                    "text": beowulf_response, "persona": "Agent_Beowulf"
                }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
