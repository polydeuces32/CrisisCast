"""
Market data API endpoints
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.database import get_db, MarketData
from app.services.data_ingestion import DataIngestionService
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def get_supported_markets():
    """Get list of supported markets"""
    return {
        "supported_markets": settings.supported_markets,
        "market_details": {
            "crypto": {
                "name": "Cryptocurrency",
                "description": "Digital currencies and blockchain assets",
                "sources": settings.crypto_sources,
                "key_metrics": ["price", "volume", "market_cap", "volatility"]
            },
            "logistics": {
                "name": "Logistics & Shipping",
                "description": "Freight rates, shipping costs, and supply chain metrics",
                "sources": settings.logistics_sources,
                "key_metrics": ["freight_rates", "shipping_costs", "capacity", "demand"]
            },
            "real_estate": {
                "name": "Real Estate",
                "description": "Property prices, rental rates, and market trends",
                "sources": settings.real_estate_sources,
                "key_metrics": ["price_per_sqft", "rental_yield", "inventory", "days_on_market"]
            },
            "ecommerce": {
                "name": "E-commerce",
                "description": "Online retail metrics and platform performance",
                "sources": settings.ecommerce_sources,
                "key_metrics": ["gmv", "conversion_rate", "aov", "customer_acquisition_cost"]
            }
        }
    }

@router.get("/{market}/symbols")
async def get_market_symbols(
    market: str,
    limit: int = Query(100, description="Maximum number of symbols to return"),
    db: Session = Depends(get_db)
):
    """Get available symbols for a market"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Get unique symbols from database
    symbols = db.query(MarketData.symbol).filter(
        MarketData.market == market
    ).distinct().limit(limit).all()
    
    return {
        "market": market,
        "symbols": [symbol[0] for symbol in symbols],
        "total_symbols": len(symbols),
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/{market}/data")
async def get_market_data(
    market: str,
    symbol: Optional[str] = Query(None, description="Specific symbol"),
    source: Optional[str] = Query(None, description="Data source"),
    hours_back: int = Query(24, description="Hours of data to retrieve"),
    limit: int = Query(1000, description="Maximum number of records"),
    db: Session = Depends(get_db)
):
    """Get raw market data"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    query = db.query(MarketData).filter(
        MarketData.market == market,
        MarketData.timestamp >= cutoff_time
    )
    
    if symbol:
        query = query.filter(MarketData.symbol == symbol)
    
    if source:
        query = query.filter(MarketData.source == source)
    
    data = query.order_by(MarketData.timestamp.desc()).limit(limit).all()
    
    return {
        "market": market,
        "symbol": symbol,
        "source": source,
        "data": [
            {
                "id": record.id,
                "symbol": record.symbol,
                "source": record.source,
                "timestamp": record.timestamp.isoformat(),
                "price": record.price,
                "volume": record.volume,
                "market_cap": record.market_cap,
                "additional_data": record.additional_data
            }
            for record in data
        ],
        "total_records": len(data),
        "time_range_hours": hours_back
    }

@router.get("/{market}/summary")
async def get_market_summary(
    market: str,
    symbol: Optional[str] = Query(None, description="Specific symbol"),
    db: Session = Depends(get_db)
):
    """Get market summary statistics"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Get recent data for summary
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    query = db.query(MarketData).filter(
        MarketData.market == market,
        MarketData.timestamp >= cutoff_time
    )
    
    if symbol:
        query = query.filter(MarketData.symbol == symbol)
    
    data = query.all()
    
    if not data:
        return {
            "market": market,
            "symbol": symbol,
            "message": "No data available for the specified criteria"
        }
    
    # Calculate summary statistics
    prices = [d.price for d in data if d.price is not None]
    volumes = [d.volume for d in data if d.volume is not None]
    
    if prices:
        price_stats = {
            "current": prices[0] if prices else None,
            "min": min(prices),
            "max": max(prices),
            "avg": sum(prices) / len(prices),
            "count": len(prices)
        }
    else:
        price_stats = None
    
    if volumes:
        volume_stats = {
            "current": volumes[0] if volumes else None,
            "min": min(volumes),
            "max": max(volumes),
            "avg": sum(volumes) / len(volumes),
            "count": len(volumes)
        }
    else:
        volume_stats = None
    
    return {
        "market": market,
        "symbol": symbol,
        "time_range": "24h",
        "price_stats": price_stats,
        "volume_stats": volume_stats,
        "total_records": len(data),
        "generated_at": datetime.utcnow().isoformat()
    }

@router.post("/{market}/refresh")
async def refresh_market_data(
    market: str,
    symbols: Optional[List[str]] = Query(None, description="Specific symbols to refresh"),
    background_tasks: BackgroundTasks = None
):
    """Trigger data refresh for a market"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Start background data ingestion
    data_service = DataIngestionService()
    
    if symbols:
        background_tasks.add_task(data_service.ingest_market_data, market, symbols)
    else:
        background_tasks.add_task(data_service.ingest_market_data, market)
    
    return {
        "market": market,
        "symbols": symbols,
        "message": "Data refresh initiated",
        "initiated_at": datetime.utcnow().isoformat()
    }

@router.get("/{market}/sources")
async def get_market_sources(
    market: str,
    db: Session = Depends(get_db)
):
    """Get available data sources for a market"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Get sources from config
    if market == "crypto":
        sources = settings.crypto_sources
    elif market == "logistics":
        sources = settings.logistics_sources
    elif market == "real_estate":
        sources = settings.real_estate_sources
    elif market == "ecommerce":
        sources = settings.ecommerce_sources
    else:
        sources = []
    
    # Get source status from database
    source_status = {}
    for source in sources:
        latest_data = db.query(MarketData).filter(
            MarketData.market == market,
            MarketData.source == source
        ).order_by(MarketData.timestamp.desc()).first()
        
        source_status[source] = {
            "available": latest_data is not None,
            "last_update": latest_data.timestamp.isoformat() if latest_data else None,
            "status": "active" if latest_data else "inactive"
        }
    
    return {
        "market": market,
        "sources": source_status,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/{market}/trends")
async def get_market_trends(
    market: str,
    timeframe: str = Query("7d", description="Timeframe: 1d, 7d, 30d"),
    db: Session = Depends(get_db)
):
    """Get market trend analysis"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Calculate timeframe
    if timeframe == "1d":
        hours_back = 24
    elif timeframe == "7d":
        hours_back = 168
    elif timeframe == "30d":
        hours_back = 720
    else:
        hours_back = 168  # Default to 7 days
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    # Get data for trend analysis
    data = db.query(MarketData).filter(
        MarketData.market == market,
        MarketData.timestamp >= cutoff_time
    ).order_by(MarketData.timestamp.asc()).all()
    
    if not data:
        return {
            "market": market,
            "timeframe": timeframe,
            "message": "Insufficient data for trend analysis"
        }
    
    # Simple trend calculation (price change over time)
    prices = [d.price for d in data if d.price is not None]
    
    if len(prices) < 2:
        return {
            "market": market,
            "timeframe": timeframe,
            "message": "Insufficient price data for trend analysis"
        }
    
    price_change = ((prices[-1] - prices[0]) / prices[0]) * 100
    trend_direction = "bullish" if price_change > 0 else "bearish" if price_change < 0 else "neutral"
    
    return {
        "market": market,
        "timeframe": timeframe,
        "trend_direction": trend_direction,
        "price_change_percent": round(price_change, 2),
        "price_start": prices[0],
        "price_end": prices[-1],
        "data_points": len(prices),
        "generated_at": datetime.utcnow().isoformat()
    }
