#!/usr/bin/env python3
"""
CrisisCast Demo Script
Demonstrates the core capabilities of the CrisisCast platform.

Usage:
    API_KEY=your-key python demo.py
    python demo.py --key your-key
"""

import argparse
import os
import requests
import json

BASE_URL = "http://localhost:8000"


def get_headers(api_key: str) -> dict:
    return {"X-API-Key": api_key}


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_section(title: str):
    print(f"\n--- {title} ---")


def demo_health_check():
    print_section("Health Check (no auth required)")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        print(f"  Status   : {data['status']}")
        print(f"  Timestamp: {data['timestamp']}")
    except Exception as e:
        print(f"  ERROR: {e}")


def demo_markets(headers: dict):
    print_section("Supported Markets")
    try:
        r = requests.get(f"{BASE_URL}/api/v1/markets/", headers=headers, timeout=5)
        if r.status_code == 200:
            markets = r.json().get("supported_markets", [])
            for m in markets:
                print(f"  - {m}")
        else:
            print(f"  HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"  ERROR: {e}")


def demo_forecast(headers: dict, market: str = "crypto", symbol: str = "BTC"):
    print_section(f"Forecast — {symbol} ({market})")
    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/forecasts/{market}/{symbol}",
            headers=headers,
            timeout=30,
        )
        if r.status_code == 200:
            data = r.json()
            if "error" in data:
                print(f"  Note: {data['error']} (no training data yet)")
                return
            print(f"  Current price   : ${data.get('current_price', 'N/A'):,.2f}")
            print(f"  Predicted (next): ${data.get('predicted_price', 'N/A'):,.2f}")
            print(f"  Confidence      : {data.get('confidence_score', 0):.0%}")
            print(f"  Trend           : {data.get('trend_direction', 'N/A')}")
            print(f"  Volatility      : {data.get('volatility_score', 0):.0%}")
            if data.get("ai_explanation"):
                print(f"\n  AI Analysis:\n  {data['ai_explanation'][:300]}")
        else:
            print(f"  HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"  ERROR: {e}")


def demo_volatility(headers: dict, market: str = "crypto", symbol: str = "BTC"):
    print_section(f"Volatility — {symbol} ({market})")
    try:
        r = requests.get(
            f"{BASE_URL}/api/v1/volatility/{market}/{symbol}",
            headers=headers,
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  Volatility score : {data.get('volatility_score', 0):.2f} / 1.00")
            print(f"  Timeframe        : {data.get('timeframe', 'N/A')}")
            print(f"  Cached           : {data.get('cached', False)}")
        else:
            print(f"  HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"  ERROR: {e}")


def demo_batch_forecast(headers: dict, market: str = "crypto"):
    symbols = ["BTC", "ETH", "BNB"]
    print_section(f"Batch Forecast — {market}: {', '.join(symbols)}")
    try:
        params = {"market": market, "symbols": symbols}
        r = requests.get(
            f"{BASE_URL}/api/v1/forecasts/batch/",
            headers=headers,
            params=params,
            timeout=60,
        )
        if r.status_code == 200:
            data = r.json()
            for sym, forecast in data.get("forecasts", {}).items():
                if "error" in forecast:
                    print(f"  {sym}: {forecast['error']}")
                else:
                    direction = forecast.get("trend_direction", "N/A")
                    price = forecast.get("predicted_price", 0)
                    print(f"  {sym}: ${price:,.2f}  ({direction})")
        else:
            print(f"  HTTP {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"  ERROR: {e}")


def demo_docs():
    print_section("Interactive API Docs")
    print(f"  Swagger UI : {BASE_URL}/docs")
    print(f"  ReDoc      : {BASE_URL}/redoc")
    print(f"  Health     : {BASE_URL}/health")


def main():
    parser = argparse.ArgumentParser(description="CrisisCast demo")
    parser.add_argument("--key", default=os.getenv("API_KEY", "crisiscast-dev-key"),
                        help="API key (or set API_KEY env var)")
    parser.add_argument("--url", default=BASE_URL, help="Base URL of the running server")
    args = parser.parse_args()

    global BASE_URL
    BASE_URL = args.url
    headers = get_headers(args.key)

    print_header("CrisisCast Demo")
    print(f"  Server : {BASE_URL}")
    print(f"  API key: {args.key[:8]}...")

    # Verify server is up
    try:
        requests.get(f"{BASE_URL}/health", timeout=3)
    except Exception:
        print("\n  Server is not running. Start it with:")
        print("    docker-compose up -d")
        print("    # or: python run.py")
        return

    demo_health_check()
    demo_markets(headers)
    demo_forecast(headers)
    demo_volatility(headers)
    demo_batch_forecast(headers)
    demo_docs()

    print_header("Done")
    print(f"  Explore the full API at {BASE_URL}/docs")
    print(f"  Pass your API key as X-API-Key header on every request.")


if __name__ == "__main__":
    main()
