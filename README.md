# EKO TRADE — Telegram Mini App MVP

This is the first working project skeleton for the EKO TRADE Mini App.

## What is included

- Dark neon EKO TRADE mobile UI
- Currency selection
- 1/2/5/15 minute selection
- ANALYZE button
- BUY/SELL result screen
- Telegram Mini App JavaScript integration
- FastAPI backend
- Twelve Data market-data adapter
- Initial EMA/RSI signal engine
- Telegram bot that opens the Mini App

## Important

The included signal engine is only an initial strategy. It does NOT guarantee 70% profitable trades.

Also, if Pocket Option is showing an OTC instrument, a standard forex feed such as EUR/USD may not match Pocket Option's exact candles. For OTC signals, use a data source matching that instrument/feed.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set:

- BOT_TOKEN — token from @BotFather
- WEBAPP_URL — public HTTPS URL where the Mini App is hosted
- TWELVE_DATA_API_KEY — market data API key

Run the web server:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Run the Telegram bot in a second terminal:

```bash
python backend/bot.py
```

## Telegram setup

Telegram supports Mini Apps launched from a bot menu/button. Configure the Mini App URL through @BotFather and use the public HTTPS URL.

For production, also validate Telegram `initData` on the backend before trusting user identity.

## Next development stage

1. Connect the exact market feed needed for the chosen Pocket Option instruments.
2. Build a proper historical backtester.
3. Test multiple strategies and expiry times.
4. Use out-of-sample and forward testing.
5. Only then consider real-money use.

Never treat a backtest as a guarantee of future performance.
