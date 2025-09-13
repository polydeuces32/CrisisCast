"""
Database configuration and models
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
from typing import Generator
import redis
import json
from datetime import datetime, timedelta

from app.core.config import settings

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Database Models
class MarketData(Base):
    """Raw market data from various sources"""
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(50), index=True)  # crypto, logistics, real_estate, ecommerce
    symbol = Column(String(100), index=True)  # BTC, ETH, etc.
    source = Column(String(100), index=True)  # coinmarketcap, zillow, etc.
    timestamp = Column(DateTime, default=func.now(), index=True)
    price = Column(Float)
    volume = Column(Float)
    market_cap = Column(Float)
    additional_data = Column(JSON)  # Store additional fields as JSON
    created_at = Column(DateTime, default=func.now())

class Forecast(Base):
    """6-month trend forecasts"""
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(50), index=True)
    symbol = Column(String(100), index=True)
    forecast_date = Column(DateTime, index=True)
    horizon_days = Column(Integer, default=180)
    predicted_price = Column(Float)
    confidence_score = Column(Float)  # 0-1
    trend_direction = Column(String(20))  # bullish, bearish, neutral
    volatility_score = Column(Float)  # 0-1
    model_version = Column(String(50))
    additional_metrics = Column(JSON)
    created_at = Column(DateTime, default=func.now())

class VolatilityAlert(Base):
    """Volatility alerts and thresholds"""
    __tablename__ = "volatility_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    market = Column(String(50), index=True)
    symbol = Column(String(100), index=True)
    alert_type = Column(String(50))  # high_volatility, trend_change, anomaly
    threshold_value = Column(Float)
    current_value = Column(Float)
    severity = Column(String(20))  # low, medium, high, critical
    message = Column(Text)
    is_active = Column(Boolean, default=True)
    triggered_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

class UserAlert(Base):
    """User-defined alerts and subscriptions"""
    __tablename__ = "user_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), index=True)
    market = Column(String(50), index=True)
    symbol = Column(String(100), index=True)
    alert_type = Column(String(50))
    threshold_value = Column(Float)
    is_active = Column(Boolean, default=True)
    notification_method = Column(String(50))  # email, webhook, sms
    notification_endpoint = Column(String(500))
    created_at = Column(DateTime, default=func.now())

class ModelPerformance(Base):
    """ML model performance tracking"""
    __tablename__ = "model_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), index=True)
    market = Column(String(50), index=True)
    symbol = Column(String(100), index=True)
    metric_name = Column(String(100))
    metric_value = Column(Float)
    evaluation_date = Column(DateTime, index=True)
    model_version = Column(String(50))
    created_at = Column(DateTime, default=func.now())

# Database dependency
def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Redis utilities
def get_redis() -> redis.Redis:
    """Get Redis client"""
    return redis_client

def cache_forecast(market: str, symbol: str, forecast_data: dict, ttl: int = 3600):
    """Cache forecast data in Redis"""
    key = f"forecast:{market}:{symbol}"
    redis_client.setex(key, ttl, json.dumps(forecast_data))

def get_cached_forecast(market: str, symbol: str) -> dict:
    """Get cached forecast data from Redis"""
    key = f"forecast:{market}:{symbol}"
    data = redis_client.get(key)
    return json.loads(data) if data else None

def cache_volatility_score(market: str, symbol: str, score: float, ttl: int = 1800):
    """Cache volatility score in Redis"""
    key = f"volatility:{market}:{symbol}"
    redis_client.setex(key, ttl, str(score))

def get_cached_volatility_score(market: str, symbol: str) -> float:
    """Get cached volatility score from Redis"""
    key = f"volatility:{market}:{symbol}"
    data = redis_client.get(key)
    return float(data) if data else None

# Initialize database
async def init_db():
    """Initialize database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        print("Continuing with limited functionality...")
        # Don't raise the exception, just log it
