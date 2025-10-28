import pandas as pd
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import asyncio

# Adjust import paths
import sys
sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.data.storage import DataStorage
from app.strategy.ema_atr import EmaAtrStrategy
from app.backtest.engine import BacktestEngine
from app.services.llm import LLMService

# --- File Paths ---
TRADES_LOG_FILE = Path(__file__).resolve().parents[2] / "trades_with_reasons.jsonl"


# --- FastAPI App Setup ---
app = FastAPI()
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)
llm_service = LLMService()

# --- (WebSocket Manager, HTML Endpoint, other APIs remain the same) ---
class ConnectionManager:
    def __init__(self): self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket): await websocket.accept(); self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket): self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for conn in self.active_connections: await conn.send_text(message)
manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request): return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/ohlcv")
async def get_ohlcv_data(symbol: str = "BTCUSDT", interval: str = "1h", start_date: str = "2023-01-01", end_date: str = "2023-12-31"):
    # ... (implementation is the same)
    storage = DataStorage()
    df = storage.read_ohlcv(symbol, interval, start_date, end_date)
    if df.empty: return []
    df.reset_index(inplace=True)
    df['time'] = df['timestamp'].apply(lambda x: int(x.timestamp()))
    return df[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records')


@app.get("/api/trades")
async def get_trade_signals(symbol: str = "BTCUSDT", interval: str = "1h", start_date: str = "2023-01-01", end_date: str = "2023-12-31"):
    # ... (implementation is the same)
    storage = DataStorage()
    df = storage.read_ohlcv(symbol, interval, start_date, end_date)
    if df.empty: return []
    strategy = EmaAtrStrategy()
    engine = BacktestEngine(df, strategy)
    engine.run()
    # This now returns trades with reasons, but we only need the markers for this endpoint
    trades = engine.trades
    if not trades: return []
    trade_markers = []
    for trade in trades:
        trade_markers.append({
            "time": int(trade['timestamp'].timestamp()),
            "position": "aboveBar" if trade['type'] == 'SELL' else "belowBar",
            "color": "#e91e63" if trade['type'] == 'SELL' else "#2196F3",
            "shape": "arrowDown" if trade['type'] == 'SELL' else "arrowUp",
            "text": f"{trade['type']} @ {trade['price']:.2f}"
        })
    return trade_markers


# --- NEW: Cognitive Endpoint ---
@app.get("/api/why_trade")
async def why_trade(trade_id: str):
    """
    Explains the reason for a specific trade in natural language.
    """
    if not TRADES_LOG_FILE.exists():
        raise HTTPException(status_code=404, detail="Trade log file not found.")

    found_trade = None
    with open(TRADES_LOG_FILE, 'r') as f:
        for line in f:
            try:
                trade_log = json.loads(line)
                if trade_log.get('trade_id') == trade_id:
                    found_trade = trade_log
                    break
            except json.JSONDecodeError:
                continue # Skip corrupted lines

    if not found_trade:
        raise HTTPException(status_code=404, detail=f"Trade with ID '{trade_id}' not found.")

    # Use the LLM service to explain the reason
    reason_dict = found_trade.get('reason', {})
    explanation = llm_service.explain_trade_reason(reason_dict)

    return JSONResponse(content={
        "trade_id": trade_id,
        "explanation": explanation,
        "raw_reason": reason_dict,
        "order_details": found_trade.get('order_details')
    })

# --- WebSocket Endpoint ---
@app.websocket("/ws/run_backtest")
async def websocket_backtest(websocket: WebSocket, symbol: str="BTCUSDT", interval: str="1h", start_date: str="2023-01-01", end_date: str="2023-12-31", fast_ema: int=12, slow_ema: int=26, atr_period: int=14):
    # ... (implementation is the same)
    await manager.connect(websocket)
    try:
        storage = DataStorage()
        df = storage.read_ohlcv(symbol, interval, start_date, end_date)
        if df.empty: await manager.broadcast(json.dumps({"type":"error", "message":"No data"})); return
        strategy = EmaAtrStrategy(fast_ema_period=fast_ema, slow_ema_period=slow_ema, atr_period=atr_period)
        signals_df = strategy.generate_signals(df)
        if signals_df.empty: await manager.broadcast(json.dumps({"type":"error", "message":"No signals"})); return
        engine = BacktestEngine(df, strategy)
        for ts, row in signals_df.iterrows():
            price, signal = row['close'], row['signal']
            if signal == 1 and engine.position_size==0: engine._execute_buy(ts, price, row['reason'])
            elif signal == -1 and engine.position_size > 0: engine._execute_sell(ts, price, row['reason'])
            val = engine.cash + (engine.position_size*price)
            kline = {"time":int(ts.timestamp()),"open":row['open'],"high":row['high'],"low":row['low'],"close":price}
            trade = engine.trades[-1] if engine.trades and engine.trades[-1]['timestamp']==ts else None
            msg = {"type":"update","kline":kline,"portfolio_value":val,"trade":trade}
            await manager.broadcast(json.dumps(msg)); await asyncio.sleep(0.05)
        await manager.broadcast(json.dumps({"type":"finished"}))
    except WebSocketDisconnect: print("Client disconnected")
    finally: manager.disconnect(websocket)
