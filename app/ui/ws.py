import pandas as pd
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import asyncio
import sys

sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.storage import DataStorage
from app.strategy.ema_atr import EmaAtrStrategy
from app.backtest.engine import BacktestEngine
from app.services.llm import LLMService

TRADES_LOG_FILE = Path(__file__).resolve().parents[2] / "trades_with_reasons.jsonl"
SENTIMENT_FILE = Path(__file__).resolve().parents[2] / "data/derived/sentiment_feed.parquet"
ONCHAIN_FILE = Path(__file__).resolve().parents[2] / "data/derived/onchain_daily.parquet"

app = FastAPI()
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)
llm_service = LLMService()

class ConnectionManager:
    def __init__(self): self.active_connections: list[WebSocket] = []
    async def connect(self, ws: WebSocket): await ws.accept(); self.active_connections.append(ws)
    def disconnect(self, ws: WebSocket): self.active_connections.remove(ws)
    async def broadcast(self, msg: str):
        for conn in self.active_connections: await conn.send_text(msg)
manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/ohlcv")
async def get_ohlcv_data(symbol: str = "BTCUSDT", interval: str = "1h", start_date: str = "2023-01-01", end_date: str = "2023-12-31"):
    storage = DataStorage()
    df = storage.read_ohlcv(symbol, interval, start_date, end_date)
    if df.empty: return []
    df.reset_index(inplace=True)
    df['time'] = df['timestamp'].apply(lambda x: int(x.timestamp()))
    return df[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records')

@app.get("/api/sentiment")
async def get_sentiment_data():
    if not SENTIMENT_FILE.exists(): return []
    df = pd.read_parquet(SENTIMENT_FILE)
    df.set_index('timestamp', inplace=True)
    df_resampled = df['sentiment_score'].resample('h').mean().dropna().reset_index()
    df_resampled.columns = ['time', 'value']
    df_resampled['time'] = df_resampled['time'].apply(lambda x: int(x.timestamp()))
    return df_resampled.to_dict(orient='records')

@app.get("/api/onchain")
async def get_onchain_data(metric: str = "btc_active_addresses"):
    if not ONCHAIN_FILE.exists(): return []
    df = pd.read_parquet(ONCHAIN_FILE)
    if metric not in df.columns: return []
    df = df[['timestamp', metric]].copy()
    df.columns = ['time', 'value']
    df['time'] = df['time'].apply(lambda x: int(x.timestamp()))
    return df.to_dict(orient='records')

@app.get("/api/why_trade")
async def why_trade(trade_id: str):
    if not TRADES_LOG_FILE.exists(): raise HTTPException(404, "Log file not found.")
    with open(TRADES_LOG_FILE, 'r') as f:
        for line in f:
            trade_log = json.loads(line)
            if trade_log.get('trade_id') == trade_id:
                explanation = llm_service.explain_trade_reason(trade_log.get('reason', {}))
                return JSONResponse({"explanation": explanation, **trade_log})
    raise HTTPException(404, f"Trade '{trade_id}' not found.")

# WebSocket and other endpoints would remain here
# ...

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
