import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


BASE = Path(__file__).resolve().parent
FRONTEND = BASE / "frontend"

app = FastAPI(title="EKO TRADE")


PAIR_SYMBOLS = {
    "EUR/USD OTC": "EURUSD_otc",
    "GBP/USD OTC": "GBPUSD_otc",
    "USD/JPY OTC": "USDJPY_otc",
    "AUD/USD OTC": "AUDUSD_otc",
    "USD/CHF OTC": "USDCHF_otc",
    "NZD/USD OTC": "NZDUSD_otc",
}

TIMEFRAMES = {
    1: 60,
    2: 120,
    5: 300,
    15: 900,
}


class AnalyzeRequest(BaseModel):
    pair: str
    duration: int


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

    return result


def rsi(values, period=14):
    if len(values) <= period:
        return 50

    gains = []
    losses = []

    for i in range(1, len(values)):
        change = values[i] - values[i - 1]

        if change >= 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def generate_signal(closes):
    if len(closes) < 40:
        raise ValueError("Not enough candle data")

    ema_fast = ema(closes, 9)
    ema_slow = ema(closes, 21)
    ema_short = ema(closes, 5)

    current_rsi = rsi(closes, 14)

    score = 0

    # Trend direction
    if ema_fast > ema_slow:
        score += 2
    elif ema_fast < ema_slow:
        score -= 2

    # Short-term momentum
    if ema_short > ema_fast:
        score += 1
    elif ema_short < ema_fast:
        score -= 1

    # Recent price momentum
    if closes[-1] > closes[-2] > closes[-3]:
        score += 1
    elif closes[-1] < closes[-2] < closes[-3]:
        score -= 1

    # RSI confirmation
    if 50 <= current_rsi <= 68:
        score += 1
    elif 32 <= current_rsi < 50:
        score -= 1

    # Avoid extreme RSI entries
    if current_rsi > 75:
        score -= 2
    elif current_rsi < 25:
        score += 2

    if score >= 2:
        return "BUY"

    return "SELL"

async def get_otc_candles(pair, duration):
    api_key = os.getenv("OTCHARTS_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="OTCHARTS_API_KEY is not configured",
        )

    if pair not in PAIR_SYMBOLS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported pair",
        )

    if duration not in TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported duration",
        )

    symbol = PAIR_SYMBOLS[pair]
    timeframe = TIMEFRAMES[duration]

    url = "https://otcharts.com/v1/candles"

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    params = {
        "venue": "otc",
        "symbol": symbol,
        "tf": timeframe,
        "limit": 200,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                url,
                headers=headers,
                params=params,
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"OTCharts error: {response.text}",
            )

        data = response.json()

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OTCharts connection error: {exc}",
        )

    candles = data.get("candles", [])

    if len(candles) < 30:
        raise HTTPException(
            status_code=502,
            detail="Not enough OTC candle data",
        )

    return candles


def candles_are_continuous(candles, timeframe):
    expected = timeframe

    for i in range(1, len(candles)):
        previous = int(candles[i - 1]["time"])
        current = int(candles[i]["time"])

        if current - previous != expected:
            return False

    return True


def run_backtest(candles, duration):
    timeframe = TIMEFRAMES[duration]

    wins = 0
    losses = 0
    skipped = 0

    for i in range(30, len(candles) - 1):
        window = candles[:i]

        if not candles_are_continuous(window[-30:], timeframe):
            skipped += 1
            continue

        closes = [
            float(candle["close"])
            for candle in window
        ]

        signal = generate_signal(closes)

        entry = float(candles[i]["close"])
        exit_price = float(candles[i + 1]["close"])

        if signal == "BUY":
            win = exit_price > entry
        else:
            win = exit_price < entry

        if win:
            wins += 1
        else:
            losses += 1

    total = wins + losses

    accuracy = (
        round((wins / total) * 100, 2)
        if total > 0
        else 0
    )

    return {
        "wins": wins,
        "losses": losses,
        "skipped": skipped,
        "total": total,
        "accuracy": accuracy,
        "duration": duration,
    }


@app.get("/")
async def home():
    return FileResponse(FRONTEND / "index.html")


@app.get("/styles.css")
async def styles():
    return FileResponse(FRONTEND / "styles.css")


@app.get("/app.js")
async def javascript():
    return FileResponse(FRONTEND / "app.js")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "data_source": "OTCharts Pocket Option OTC",
    }


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    candles = await get_otc_candles(
        req.pair,
        req.duration,
    )

    closes = [
        float(candle["close"])
        for candle in candles
    ]

    signal = generate_signal(closes)

    return {
        "signal": signal,
        "pair": req.pair,
        "duration": req.duration,
        "data_source": "Pocket Option OTC",
    }

def strategy_test_signal(closes, strategy):
    if len(closes) < 40:
        return None

    fast = ema(closes, strategy["fast"])
    slow = ema(closes, strategy["slow"])
    current_rsi = rsi(closes, strategy["rsi"])

    if fast is None or slow is None:
        return None

    score = 0

    # Trend
    if fast > slow:
        score += 1
    elif fast < slow:
        score -= 1

    # Momentum
    if closes[-1] > closes[-2] > closes[-3]:
        score += 1
    elif closes[-1] < closes[-2] < closes[-3]:
        score -= 1

    # RSI
    if current_rsi < strategy["rsi_low"]:
        score += 1
    elif current_rsi > strategy["rsi_high"]:
        score -= 1

    # Strong signal only
    threshold = strategy.get("threshold", 2)

    if score >= threshold:
        return "BUY"

    if score <= -threshold:
        return "SELL"

    return None
    if len(closes) < 40:
        return None

    fast = ema(closes, strategy["fast"])
    slow = ema(closes, strategy["slow"])
    current_rsi = rsi(closes, strategy["rsi"])

    if fast is None or slow is None:
        return None

    score = 0

    if fast > slow:
        score += 1
    else:
        score -= 1

    if closes[-1] > closes[-2]:
        score += 1
    else:
        score -= 1

    if current_rsi < strategy["rsi_low"]:
        score += 1
    elif current_rsi > strategy["rsi_high"]:
        score -= 1

    return "BUY" if score > 0 else "SELL"


STRATEGIES = [
    {
        "name": "Strong 2/3",
        "fast": 9,
        "slow": 21,
        "rsi": 14,
        "rsi_low": 30,
        "rsi_high": 70,
        "threshold": 2,
    },
    {
        "name": "Strong 3/3",
        "fast": 9,
        "slow": 21,
        "rsi": 14,
        "rsi_low": 30,
        "rsi_high": 70,
        "threshold": 3,
    },
    {
        "name": "Strong RSI 35/65",
        "fast": 9,
        "slow": 21,
        "rsi": 14,
        "rsi_low": 35,
        "rsi_high": 65,
        "threshold": 2,
    },
    {
        "name": "Strong EMA 8/21",
        "fast": 8,
        "slow": 21,
        "rsi": 14,
        "rsi_low": 30,
        "rsi_high": 70,
        "threshold": 2,
    },
    {
        "name": "Strong EMA 10/25",
        "fast": 10,
        "slow": 25,
        "rsi": 14,
        "rsi_low": 30,
        "rsi_high": 70,
        "threshold": 2,
    },
]
def test_strategy(candles, duration, strategy):
    wins = 0
    losses = 0

    for i in range(40, len(candles) - 1):
        closes = [
            float(candle["close"])
            for candle in candles[:i]
        ]

        signal = strategy_test_signal(
            closes,
            strategy,
        )

        if signal is None:
            continue

        entry = float(candles[i]["close"])
        exit_price = float(candles[i + 1]["close"])

        if signal == "BUY":
            win = exit_price > entry
        else:
            win = exit_price < entry

        if win:
            wins += 1
        else:
            losses += 1

    total = wins + losses

    accuracy = (
        round((wins / total) * 100, 2)
        if total
        else 0
    )

    return {
        "strategy": strategy["name"],
        "wins": wins,
        "losses": losses,
        "total": total,
        "accuracy": accuracy,
    }


@app.get("/api/strategy-test")
async def strategy_test(
    pair: str = "EUR/USD OTC",
    duration: int = 2,
):
    candles = await get_otc_candles(
        pair,
        duration,
    )

    results = []

    for strategy in STRATEGIES:
        results.append(
            test_strategy(
                candles,
                duration,
                strategy,
            )
        )

    results.sort(
        key=lambda x: x["accuracy"],
        reverse=True,
    )

    return {
        "pair": pair,
        "duration": duration,
        "data_source": "Pocket Option OTC",
        "results": results,
    }
@app.get("/api/backtest")
async def backtest(
    pair: str = "EUR/USD OTC",
    duration: int = 1,
):
    candles = await get_otc_candles(
        pair,
        duration,
    )

    result = run_backtest(
        candles,
        duration,
    )

    result["pair"] = pair
    result["data_source"] = "Pocket Option OTC"

    return result
