#!/usr/bin/env python3
"""
CrisisCast Demo Script
Shows the capabilities of the CrisisCast platform
"""

import requests
import json
import time
from datetime import datetime

def print_header(title):
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def print_section(title):
    print(f"\n📊 {title}")
    print("-" * 40)

def demo_health_check():
    """Demo the health check endpoint"""
    print_section("Health Check")
    try:
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"⏰ Timestamp: {data['timestamp']}")
            print("🔧 Services:")
            for service, status in data['services'].items():
                print(f"   • {service}: {status}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_forecast():
    """Demo the forecast endpoint"""
    print_section("6-Month BTC Forecast")
    try:
        response = requests.get("http://localhost:8000/api/v1/forecasts?market=crypto&symbol=BTC")
        if response.status_code == 200:
            data = response.json()
            print(f"🎯 Market: {data.get('market', 'N/A')}")
            print(f"💰 Symbol: {data.get('symbol', 'N/A')}")
            print(f"📈 Current Price: ${data.get('current_price', 'N/A'):,.2f}")
            print(f"🔮 Predicted Price: ${data.get('predicted_price', 'N/A'):,.2f}")
            print(f"📊 Confidence: {data.get('confidence_score', 'N/A'):.1%}")
            print(f"📈 Trend: {data.get('trend_direction', 'N/A')}")
            print(f"⚡ Volatility: {data.get('volatility_score', 'N/A'):.1%}")
            
            if 'ai_explanation' in data:
                print(f"\n🤖 AI Explanation:")
                print(f"   {data['ai_explanation'][:200]}...")
        else:
            print(f"❌ Forecast failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_volatility():
    """Demo the volatility endpoint"""
    print_section("Volatility Analysis")
    try:
        response = requests.get("http://localhost:8000/api/v1/volatility?market=crypto&symbol=BTC")
        if response.status_code == 200:
            data = response.json()
            print(f"🎯 Market: {data.get('market', 'N/A')}")
            print(f"💰 Symbol: {data.get('symbol', 'N/A')}")
            print(f"⚡ Volatility Score: {data.get('volatility_score', 'N/A'):.1%}")
            print(f"⏰ Timeframe: {data.get('timeframe', 'N/A')}")
            print(f"🕐 Generated: {data.get('generated_at', 'N/A')}")
        else:
            print(f"❌ Volatility check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_batch_forecast():
    """Demo batch forecasting"""
    print_section("Batch Forecasting")
    try:
        symbols = ["BTC", "ETH", "BNB"]
        response = requests.get(f"http://localhost:8000/api/v1/forecasts/batch/?market=crypto&symbols={','.join(symbols)}")
        if response.status_code == 200:
            data = response.json()
            print(f"🎯 Market: {data.get('market', 'N/A')}")
            print(f"📊 Forecasts Generated: {len(data.get('forecasts', {}))}")
            print(f"⏰ Generated At: {data.get('generated_at', 'N/A')}")
            
            print("\n📈 Individual Forecasts:")
            for symbol, forecast in data.get('forecasts', {}).items():
                if 'error' not in forecast:
                    print(f"   • {symbol}: ${forecast.get('predicted_price', 'N/A'):,.2f} ({forecast.get('trend_direction', 'N/A')})")
                else:
                    print(f"   • {symbol}: Error - {forecast['error']}")
        else:
            print(f"❌ Batch forecast failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

def demo_api_docs():
    """Show API documentation info"""
    print_section("API Documentation")
    print("📚 Interactive API Documentation available at:")
    print("   http://localhost:8000/docs")
    print("\n🔗 Available Endpoints:")
    print("   • GET  /api/v1/forecasts - Get forecasts")
    print("   • GET  /api/v1/volatility - Get volatility scores")
    print("   • GET  /api/v1/alerts - Manage alerts")
    print("   • GET  /api/v1/markets - Market data")
    print("   • GET  /health - Health check")

def main():
    """Run the demo"""
    print_header("CrisisCast Demo")
    print("This demo shows the capabilities of CrisisCast")
    print("Make sure the server is running on http://localhost:8000")
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("\n❌ Server is not running. Please start it first:")
            print("   ./start.sh  # Linux/Mac")
            print("   start.bat   # Windows")
            print("   python run.py  # Manual")
            return
    except:
        print("\n❌ Server is not running. Please start it first:")
        print("   ./start.sh  # Linux/Mac")
        print("   start.bat   # Windows")
        print("   python run.py  # Manual")
        return
    
    # Run demos
    demo_health_check()
    demo_forecast()
    demo_volatility()
    demo_batch_forecast()
    demo_api_docs()
    
    print_header("Demo Complete")
    print("🎉 Thanks for trying CrisisCast!")
    print("📚 Explore more at: http://localhost:8000/docs")
    print("💡 Try the CLI: python scripts/crisiscast_cli.py --help")

if __name__ == "__main__":
    main()
