import pandas as pd
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
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

# --- FastAPI App Setup ---
app = FastAPI()
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_path)

# --- WebSocket Manager ---
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

# --- HTML Page Endpoint ---
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- REST API Endpoints ---
@app.get("/api/ohlcv")
async def get_ohlcv_data(symbol: str = "BTCUSDT", interval: str = "1h", start_date: str = "2023-01-01", end_date: str = "2023-12-31"):
    storage = DataStorage()
    df = storage.read_ohlcv(symbol, interval, start_date, end_date)
    if df.empty: return []
    df.reset_index(inplace=True)
    df['time'] = df['timestamp'].apply(lambda x: int(x.timestamp()))
    return df[['time', 'open', 'high', 'low', 'close']].to_dict(orient='records')

@app.get("/api/trades")
async def get_trade_signals(symbol: str = "BTCUSDT", interval: str = "1h", start_date: str = "2023-01-01", end_date: str = "2023-12-31"):
    storage = DataStorage()
    df = storage.read_ohlcv(symbol, interval, start_date, end_date)
    if df.empty: return []
    strategy = EmaAtrStrategy()
    engine = BacktestEngine(df, strategy)
    engine.run()
    if not engine.trades: return []
    trade_markers = []
    for trade in engine.trades:
        trade_markers.append({
            "time": int(trade['timestamp'].timestamp()),
            "position": "aboveBar" if trade['type'] == 'SELL' else "belowBar",
            "color": "#e91e63" if trade['type'] == 'SELL' else "#2196F3",
            "shape": "arrowDown" if trade['type'] == 'SELL' else "arrowUp",
            "text": f"{trade['type']} @ {trade['price']:.2f}"
        })
    return trade_markers

# --- WebSocket Backtest Simulation Endpoint ---
@app.websocket("/ws/run_backtest")
async def websocket_backtest(
    websocket: WebSocket,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    start_date: str = "2023-01-01",
    end_date: str = "2023-12-31",
    fast_ema: int = 12,
    slow_ema: int = 26,
    atr_period: int = 14
):
    await manager.connect(websocket)
    try:
        storage = DataStorage()
        df = storage.read_ohlcv(symbol, interval, start_date, end_date)
        if df.empty:
            await manager.broadcast(json.dumps({"type": "error", "message": "No data for parameters."}))
            return

        strategy = EmaAtrStrategy(fast_ema_period=fast_ema, slow_ema_period=slow_ema, atr_period=atr_period)
        signals_df = strategy.generate_signals(df)
        if signals_df.empty:
            await manager.broadcast(json.dumps({"type": "error", "message": "Could not generate signals."}))
            return

        engine = BacktestEngine(df, strategy)

        for timestamp, row in signals_df.iterrows():
            current_price, signal = row['close'], row['signal']
            if signal == 1 and engine.position_size == 0:
                engine._execute_buy(timestamp, current_price)
            elif signal == -1 and engine.position_size > 0:
                engine._execute_sell(timestamp, current_price)

            portfolio_value = engine.cash + (engine.position_size * current_price)
            kline_update = {"time": int(timestamp.timestamp()), "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close']}
            message = {"type": "update", "kline": kline_update, "portfolio_value": portfolio_value, "trade": engine.trades[-1] if engine.trades and engine.trades[-1]['timestamp'] == timestamp else None}
            await manager.broadcast(json.dumps(message))
            await asyncio.sleep(0.05)

        await manager.broadcast(json.dumps({"type": "finished", "message": "Backtest complete."}))
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in WebSocket: {e}")
        await manager.broadcast(json.dumps({"type": "error", "message": str(e)}))
    finally:
        manager.disconnect(websocket)
