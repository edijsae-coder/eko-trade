import os
from pathlib import Path
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE = Path(__file__).resolve().parent
app = FastAPI(title="EKO TRADE")

PAIR_ALLOWLIST = {"EUR/USD OTC", "GBP/USD OTC", "USD/JPY OTC", "AUD/USD OTC", "USD/CHF OTC", "NZD/USD OTC"}
DURATION_ALLOWLIST = {1, 2, 5, 15}

class AnalyzeRequest(BaseModel):
    pair: str
    minutes: int = Field(ge=1, le=15)
    initData: str = ""

async def get_candles(pair: str, interval: str = "1min", outputsize: int = 120):
    key = os.getenv("TWELVE_DATA_API_KEY")
    if not key:
        raise HTTPException(503, "Market-data API key is not configured")

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": pair,
        "interval": interval,
        "outputsize": outputsize,
        "timezone": "UTC",
        "apikey": key,
    }
    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()

    if data.get("status") != "ok" or not data.get("values"):
        raise HTTPException(502, data.get("message", "Market data unavailable"))

    # API returns newest first; reverse for chronological calculations.
    return list(reversed(data["values"]))

def ema(values, period):
    k = 2 / (period + 1)
    out = [values[0]]
    for x in values[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out

def rsi(values, period=14):
    gains, losses = [], []
    for a, b in zip(values[:-1], values[1:]):
        d = b - a
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def generate_signal(candles, minutes):
    closes = [float(x["close"]) for x in candles]
    e9, e21 = ema(closes, 9), ema(closes, 21)
    current_rsi = rsi(closes, 14)

    # This is an initial, deliberately simple strategy.
    # It is NOT a 70% guarantee and must be backtested/forward-tested.
    score = 0
    score += 1 if e9[-1] > e21[-1] else -1
    score += 1 if closes[-1] > e9[-1] else -1
    if current_rsi > 52:
        score += 1
    elif current_rsi < 48:
        score -= 1

    return "BUY" if score > 0 else "SELL"

@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    if req.pair not in PAIR_ALLOWLIST:
        raise HTTPException(400, "Unsupported currency pair")
    if req.minutes not in DURATION_ALLOWLIST:
        raise HTTPException(400, "Unsupported duration")

    candles = await get_candles(req.pair.replace(" OTC", ""))
    signal = generate_signal(candles, req.minutes)
    return {"signal": signal, "pair": req.pair, "minutes": req.minutes}
    
app.mount("/static", StaticFiles(directory=BASE / "frontend"), name="static")

@app.get("/")
async def index():
    from fastapi.responses import FileResponse
    return FileResponse(BASE / "frontend" / "index.html")
