#!/usr/bin/env python3
"""
CrisisCast CLI - Terminal-based management tool
"""

import argparse
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import get_db, MarketData, Forecast, VolatilityAlert, UserAlert
from app.services.data_ingestion import DataIngestionService
from app.services.ml_service import MLService
from app.services.alert_service import AlertService
from app.core.config import settings

class CrisisCastCLI:
    """Command-line interface for CrisisCast"""
    
    def __init__(self):
        self.data_service = DataIngestionService()
        self.ml_service = MLService()
        self.alert_service = AlertService()
    
    async def run(self, args):
        """Run CLI command"""
        if args.command == "status":
            await self.show_status()
        elif args.command == "forecast":
            await self.get_forecast(args.market, args.symbol, args.horizon)
        elif args.command == "volatility":
            await self.get_volatility(args.market, args.symbol, args.timeframe)
        elif args.command == "ingest":
            await self.ingest_data(args.market, args.symbols)
        elif args.command == "train":
            await self.train_models(args.market)
        elif args.command == "alerts":
            await self.manage_alerts(args)
        elif args.command == "data":
            await self.show_data_stats(args.market, args.symbol, args.hours)
        elif args.command == "config":
            await self.show_config()
        else:
            print(f"Unknown command: {args.command}")
    
    async def show_status(self):
        """Show system status"""
        print("🔍 CrisisCast System Status")
        print("=" * 50)
        
        # Check database connection
        try:
            from sqlalchemy import text
            db = next(get_db())
            db.execute(text("SELECT 1"))
            print("✅ Database: Connected")
        except Exception as e:
            print(f"❌ Database: Error - {e}")
        finally:
            db.close()
        
        # Check Redis connection
        try:
            from app.core.database import get_redis
            redis_client = get_redis()
            redis_client.ping()
            print("✅ Redis: Connected")
        except Exception as e:
            print(f"❌ Redis: Error - {e}")
        
        # Check data availability
        try:
            db = next(get_db())
            total_records = db.query(MarketData).count()
            print(f"📊 Data Records: {total_records}")
            
            # Show data by market
            for market in settings.supported_markets:
                count = db.query(MarketData).filter(MarketData.market == market).count()
                print(f"   {market}: {count} records")
            
        except Exception as e:
            print(f"❌ Data Check: Error - {e}")
        finally:
            db.close()
        
        # Check models
        try:
            model_files = os.listdir("data/models") if os.path.exists("data/models") else []
            print(f"🤖 ML Models: {len(model_files)} files")
        except Exception as e:
            print(f"❌ Model Check: Error - {e}")
        
        print(f"⏰ Current Time: {datetime.utcnow().isoformat()}")
    
    async def get_forecast(self, market: str, symbol: str, horizon: int):
        """Get forecast for a symbol"""
        print(f"🔮 Generating forecast for {market}/{symbol}")
        print("=" * 50)
        
        try:
            forecast = await self.ml_service.generate_forecast(market, symbol, horizon)
            
            if "error" in forecast:
                print(f"❌ Error: {forecast['error']}")
                return
            
            print(f"📈 Current Price: ${forecast['current_price']:.2f}")
            print(f"🎯 Predicted Price: ${forecast['predicted_price']:.2f}")
            print(f"📊 Confidence Score: {forecast['confidence_score']:.2f}")
            print(f"📈 Trend Direction: {forecast['trend_direction']}")
            print(f"⚡ Volatility Score: {forecast['volatility_score']:.2f}")
            print(f"📅 Forecast Date: {forecast['forecast_date']}")
            print(f"⏰ Horizon: {forecast['horizon_days']} days")
            
            if forecast.get('ai_explanation'):
                print("\n🤖 AI Explanation:")
                print("-" * 30)
                print(forecast['ai_explanation'])
            
        except Exception as e:
            print(f"❌ Error generating forecast: {e}")
    
    async def get_volatility(self, market: str, symbol: str, timeframe: str):
        """Get volatility score for a symbol"""
        print(f"⚡ Volatility Analysis for {market}/{symbol}")
        print("=" * 50)
        
        try:
            volatility_score = await self.ml_service.calculate_volatility_score(market, symbol, timeframe)
            
            print(f"📊 Volatility Score: {volatility_score:.2f}")
            print(f"⏰ Timeframe: {timeframe}")
            
            # Interpret volatility
            if volatility_score > 0.7:
                level = "High"
                color = "🔴"
            elif volatility_score > 0.4:
                level = "Medium"
                color = "🟡"
            else:
                level = "Low"
                color = "🟢"
            
            print(f"{color} Risk Level: {level}")
            
        except Exception as e:
            print(f"❌ Error calculating volatility: {e}")
    
    async def ingest_data(self, market: str, symbols: List[str]):
        """Ingest data for a market"""
        print(f"📥 Ingesting data for {market}")
        print("=" * 50)
        
        try:
            if symbols:
                await self.data_service.ingest_market_data(market, symbols)
                print(f"✅ Ingested data for symbols: {', '.join(symbols)}")
            else:
                await self.data_service.ingest_market_data(market)
                print(f"✅ Ingested data for all {market} symbols")
            
        except Exception as e:
            print(f"❌ Error ingesting data: {e}")
    
    async def train_models(self, market: str):
        """Train ML models for a market"""
        print(f"🤖 Training models for {market}")
        print("=" * 50)
        
        try:
            if market:
                await self.ml_service.train_market_models(market)
                print(f"✅ Models trained for {market}")
            else:
                await self.ml_service.train_all_models()
                print("✅ Models trained for all markets")
            
        except Exception as e:
            print(f"❌ Error training models: {e}")
    
    async def manage_alerts(self, args):
        """Manage alerts"""
        if args.alert_action == "list":
            await self.list_alerts(args.user_id)
        elif args.alert_action == "create":
            await self.create_alert(args)
        elif args.alert_action == "test":
            await self.test_alert(args.alert_id)
        else:
            print(f"Unknown alert action: {args.alert_action}")
    
    async def list_alerts(self, user_id: str):
        """List alerts for a user"""
        print(f"🔔 Alerts for user: {user_id}")
        print("=" * 50)
        
        try:
            db = next(get_db())
            alerts = db.query(UserAlert).filter(UserAlert.user_id == user_id).all()
            
            if not alerts:
                print("No alerts found")
                return
            
            for alert in alerts:
                status = "🟢 Active" if alert.is_active else "🔴 Inactive"
                print(f"ID: {alert.id} | {alert.market}/{alert.symbol} | {alert.alert_type} | {status}")
                print(f"   Threshold: {alert.threshold_value} | Method: {alert.notification_method}")
                print(f"   Created: {alert.created_at.isoformat()}")
                print()
            
        except Exception as e:
            print(f"❌ Error listing alerts: {e}")
        finally:
            db.close()
    
    async def create_alert(self, args):
        """Create a new alert"""
        print(f"➕ Creating alert for {args.market}/{args.symbol}")
        print("=" * 50)
        
        try:
            db = next(get_db())
            
            alert = UserAlert(
                user_id=args.user_id,
                market=args.market,
                symbol=args.symbol,
                alert_type=args.alert_type,
                threshold_value=args.threshold_value,
                notification_method=args.notification_method,
                notification_endpoint=args.notification_endpoint
            )
            
            db.add(alert)
            db.commit()
            
            print(f"✅ Alert created with ID: {alert.id}")
            
        except Exception as e:
            print(f"❌ Error creating alert: {e}")
        finally:
            db.close()
    
    async def test_alert(self, alert_id: int):
        """Test an alert"""
        print(f"🧪 Testing alert ID: {alert_id}")
        print("=" * 50)
        
        try:
            db = next(get_db())
            alert = db.query(UserAlert).filter(UserAlert.id == alert_id).first()
            
            if not alert:
                print("❌ Alert not found")
                return
            
            result = await self.alert_service.send_test_notification(alert)
            
            if result["success"]:
                print("✅ Test notification sent successfully")
            else:
                print(f"❌ Test notification failed: {result['message']}")
            
        except Exception as e:
            print(f"❌ Error testing alert: {e}")
        finally:
            db.close()
    
    async def show_data_stats(self, market: str, symbol: str, hours: int):
        """Show data statistics"""
        print(f"📊 Data Statistics for {market}")
        if symbol:
            print(f"Symbol: {symbol}")
        print(f"Time Range: Last {hours} hours")
        print("=" * 50)
        
        try:
            db = next(get_db())
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            query = db.query(MarketData).filter(MarketData.timestamp >= cutoff_time)
            
            if market:
                query = query.filter(MarketData.market == market)
            
            if symbol:
                query = query.filter(MarketData.symbol == symbol)
            
            records = query.all()
            
            if not records:
                print("No data found")
                return
            
            print(f"Total Records: {len(records)}")
            
            # Group by source
            sources = {}
            for record in records:
                if record.source not in sources:
                    sources[record.source] = 0
                sources[record.source] += 1
            
            print("\nBy Source:")
            for source, count in sources.items():
                print(f"  {source}: {count}")
            
            # Group by symbol
            symbols = {}
            for record in records:
                if record.symbol not in symbols:
                    symbols[record.symbol] = 0
                symbols[record.symbol] += 1
            
            print("\nBy Symbol:")
            for symbol, count in symbols.items():
                print(f"  {symbol}: {count}")
            
            # Price statistics
            prices = [r.price for r in records if r.price is not None]
            if prices:
                print(f"\nPrice Statistics:")
                print(f"  Min: ${min(prices):.2f}")
                print(f"  Max: ${max(prices):.2f}")
                print(f"  Avg: ${sum(prices)/len(prices):.2f}")
            
        except Exception as e:
            print(f"❌ Error showing data stats: {e}")
        finally:
            db.close()
    
    async def show_config(self):
        """Show current configuration"""
        print("⚙️ CrisisCast Configuration")
        print("=" * 50)
        
        print(f"Supported Markets: {', '.join(settings.supported_markets)}")
        print(f"Forecast Horizon: {settings.forecast_horizon_days} days")
        print(f"Volatility Window: {settings.volatility_window_days} days")
        print(f"Model Update Interval: {settings.model_update_interval} seconds")
        print(f"Database URL: {settings.database_url}")
        print(f"Redis URL: {settings.redis_url}")
        
        # Check API keys
        print(f"\nAPI Keys:")
        print(f"  OpenAI: {'✅ Set' if settings.openai_api_key else '❌ Not set'}")
        print(f"  Alpha Vantage: {'✅ Set' if settings.alpha_vantage_api_key else '❌ Not set'}")
        print(f"  CoinMarketCap: {'✅ Set' if settings.coinmarketcap_api_key else '❌ Not set'}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="CrisisCast CLI - Terminal management tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    subparsers.add_parser("status", help="Show system status")
    
    # Forecast command
    forecast_parser = subparsers.add_parser("forecast", help="Get forecast for a symbol")
    forecast_parser.add_argument("market", help="Market type")
    forecast_parser.add_argument("symbol", help="Symbol to forecast")
    forecast_parser.add_argument("--horizon", type=int, default=180, help="Forecast horizon in days")
    
    # Volatility command
    volatility_parser = subparsers.add_parser("volatility", help="Get volatility score")
    volatility_parser.add_argument("market", help="Market type")
    volatility_parser.add_argument("symbol", help="Symbol to analyze")
    volatility_parser.add_argument("--timeframe", default="30d", help="Timeframe for analysis")
    
    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest data for a market")
    ingest_parser.add_argument("market", help="Market type")
    ingest_parser.add_argument("--symbols", nargs="+", help="Specific symbols to ingest")
    
    # Train command
    train_parser = subparsers.add_parser("train", help="Train ML models")
    train_parser.add_argument("--market", help="Specific market to train")
    
    # Alerts command
    alerts_parser = subparsers.add_parser("alerts", help="Manage alerts")
    alerts_parser.add_argument("alert_action", choices=["list", "create", "test"], help="Alert action")
    alerts_parser.add_argument("--user-id", help="User ID for alerts")
    alerts_parser.add_argument("--alert-id", type=int, help="Alert ID for testing")
    alerts_parser.add_argument("--market", help="Market for alert")
    alerts_parser.add_argument("--symbol", help="Symbol for alert")
    alerts_parser.add_argument("--alert-type", help="Alert type")
    alerts_parser.add_argument("--threshold-value", type=float, help="Threshold value")
    alerts_parser.add_argument("--notification-method", help="Notification method")
    alerts_parser.add_argument("--notification-endpoint", help="Notification endpoint")
    
    # Data command
    data_parser = subparsers.add_parser("data", help="Show data statistics")
    data_parser.add_argument("--market", help="Market to analyze")
    data_parser.add_argument("--symbol", help="Symbol to analyze")
    data_parser.add_argument("--hours", type=int, default=24, help="Hours to look back")
    
    # Config command
    subparsers.add_parser("config", help="Show configuration")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Run CLI
    cli = CrisisCastCLI()
    asyncio.run(cli.run(args))

if __name__ == "__main__":
    main()
