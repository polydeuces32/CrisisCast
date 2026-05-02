# CrisisCast

[![CI](https://github.com/polydeuces32/CrisisCast/actions/workflows/ci.yml/badge.svg)](https://github.com/polydeuces32/CrisisCast/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**CrisisCast** is an API-first SaaS platform that delivers trend forecasts and real-time volatility insights across four niche markets: cryptocurrency, logistics, real estate, and e-commerce.

The platform ingests multi-source market data, trains ensemble ML models on a rolling basis, and exposes everything through a clean REST API — with optional AI-generated explanations powered by OpenAI.

---

## Features

- **Trend forecasting** — Ensemble ML models (Random Forest, Gradient Boosting, Ridge) trained on rolling market data with chronological train/test splitting
- **Volatility scoring** — 0–1 normalized score per symbol, cached in Redis and recalculated on a configurable schedule
- **Alert engine** — Price, volatility, and volume-spike alerts with per-user thresholds, 60-minute deduplication, and email/webhook/SMS delivery
- **AI explanations** — OpenAI `gpt-4o-mini` narrative for each forecast (falls back to a structured template when no key is set)
- **API-key auth** — All data endpoints require `X-API-Key`
- **Docker-ready** — Single `docker-compose up` brings up the app + Redis

---

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/polydeuces32/CrisisCast.git
cd CrisisCast
cp config.env.example .env   # add your API keys
docker-compose up -d
```

### Manual

```bash
git clone https://github.com/polydeuces32/CrisisCast.git
cd CrisisCast
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config.env.example .env
python run.py
```

Once running:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Interactive Swagger UI |
| `http://localhost:8000/health` | Health check (no auth) |
| `http://localhost:8000/redoc` | ReDoc documentation |

---

## API Usage

All data endpoints require the `X-API-Key` header. The default dev key is `crisiscast-dev-key` (set `API_KEY` in `.env` for production).

### Get a forecast

```bash
curl -H "X-API-Key: crisiscast-dev-key" \
  "http://localhost:8000/api/v1/forecasts/crypto/BTC"
```

```json
{
  "market": "crypto",
  "symbol": "BTC",
  "current_price": 43250.00,
  "predicted_price": 44100.00,
  "confidence_score": 0.72,
  "trend_direction": "bullish",
  "volatility_score": 0.38,
  "ai_explanation": "..."
}
```

### Get volatility score

```bash
curl -H "X-API-Key: crisiscast-dev-key" \
  "http://localhost:8000/api/v1/volatility/crypto/BTC?timeframe=30d"
```

### Batch forecasts

```bash
curl -H "X-API-Key: crisiscast-dev-key" \
  "http://localhost:8000/api/v1/forecasts/batch/?market=crypto&symbols=BTC&symbols=ETH&symbols=BNB"
```

### Create an alert

```bash
curl -X POST -H "X-API-Key: crisiscast-dev-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "market": "crypto",
    "symbol": "BTC",
    "alert_type": "price_above",
    "threshold_value": 50000,
    "notification_method": "webhook",
    "notification_endpoint": "https://your-app.com/webhook"
  }' \
  "http://localhost:8000/api/v1/alerts/"
```

---

## Supported Markets

| Market | Default symbols | Data sources |
|--------|----------------|--------------|
| `crypto` | BTC, ETH, BNB, ADA, SOL | Binance, Coinbase, Kraken, CoinMarketCap |
| `logistics` | FREIGHT_INDEX, SHIPPING_RATES | Freightos, Drewry (stub — bring your own key) |
| `real_estate` | ZILLOW_INDEX, CASE_SHILLER | Zillow, Realtor.com (stub — bring your own key) |
| `ecommerce` | SHOPIFY_GMV, AMAZON_SALES | Shopify, Amazon (stub — bring your own key) |

> Crypto data via [ccxt](https://github.com/ccxt/ccxt) is production-ready. Logistics, real estate, and e-commerce sources are scaffolded stubs that can be swapped for real API keys.

---

## Configuration

Copy `config.env.example` to `.env` and fill in:

```env
# Auth
API_KEY=your-production-key

# Database (defaults to SQLite for local dev)
DATABASE_URL=postgresql://user:pass@host/crisiscast

# Redis
REDIS_URL=redis://localhost:6379/0

# Optional: enables AI explanations on forecasts
OPENAI_API_KEY=sk-...

# Optional: enables live crypto prices
COINMARKETCAP_API_KEY=...

# Intervals
MODEL_UPDATE_INTERVAL=3600      # retrain every hour
DATA_INGESTION_INTERVAL=300     # ingest every 5 minutes
```

---

## Running Tests

```bash
pip install -r requirements.txt
pytest --tb=short -q
```

Tests cover alert severity logic, ML feature preparation, chronological train/test splitting, API auth enforcement, and enum input validation. No external services required — Redis and DB are mocked automatically.

---

## Demo Script

```bash
# Uses crisiscast-dev-key by default
python demo.py

# Or pass your own key
API_KEY=your-key python demo.py
```

---

## Architecture

```
FastAPI app
├── /api/v1/forecasts    — Trend forecasting endpoints
├── /api/v1/volatility   — Volatility scoring endpoints
├── /api/v1/alerts       — User alert CRUD + notification delivery
├── /api/v1/markets      — Market metadata and raw data
└── /api/v1/admin        — Model retraining, cache management, stats

Services (background)
├── DataIngestionService — Pulls data from exchanges and APIs on a schedule
├── MLService            — Trains and updates ensemble models per symbol
└── AlertService         — Polls active alerts every 60s with cooldown logic

Storage
├── SQLAlchemy ORM       — MarketData, Forecasts, Alerts, ModelPerformance
└── Redis                — Forecast and volatility score cache
```

---

## License

MIT — see [LICENSE](LICENSE).
