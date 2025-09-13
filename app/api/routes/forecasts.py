"""
Forecast API endpoints
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from app.core.database import get_db, get_cached_forecast, cache_forecast
from app.services.ml_service import MLService
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def get_forecasts(
    market: str = Query(..., description="Market type: crypto, logistics, real_estate, ecommerce"),
    symbol: Optional[str] = Query(None, description="Specific symbol (e.g., BTC, ETH)"),
    horizon_days: int = Query(180, description="Forecast horizon in days (default: 180)"),
    db: Session = Depends(get_db)
):
    """Get 6-month trend forecasts for specified market and symbol"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Check cache first
    if symbol:
        cached_forecast = get_cached_forecast(market, symbol)
        if cached_forecast:
            return cached_forecast
    
    # Generate new forecast
    ml_service = MLService()
    forecast_data = await ml_service.generate_forecast(market, symbol, horizon_days)
    
    # Cache the result
    if symbol:
        cache_forecast(market, symbol, forecast_data)
    
    return forecast_data

@router.get("/{market}/{symbol}")
async def get_symbol_forecast(
    market: str,
    symbol: str,
    horizon_days: int = Query(180, description="Forecast horizon in days"),
    include_ai_explanation: bool = Query(True, description="Include AI-generated explanation"),
    db: Session = Depends(get_db)
):
    """Get detailed forecast for a specific symbol"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Check cache first
    cached_forecast = get_cached_forecast(market, symbol)
    if cached_forecast and not include_ai_explanation:
        return cached_forecast
    
    # Generate new forecast
    ml_service = MLService()
    forecast_data = await ml_service.generate_forecast(
        market, symbol, horizon_days, include_ai_explanation
    )
    
    # Cache the result
    cache_forecast(market, symbol, forecast_data)
    
    return forecast_data

@router.get("/batch/")
async def get_batch_forecasts(
    market: str = Query(..., description="Market type"),
    symbols: List[str] = Query(..., description="List of symbols to forecast"),
    horizon_days: int = Query(180, description="Forecast horizon in days"),
    db: Session = Depends(get_db)
):
    """Get forecasts for multiple symbols in a single request"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    if len(symbols) > 50:  # Limit batch size
        raise HTTPException(status_code=400, detail="Maximum 50 symbols per batch request")
    
    ml_service = MLService()
    results = {}
    
    for symbol in symbols:
        try:
            # Check cache first
            cached_forecast = get_cached_forecast(market, symbol)
            if cached_forecast:
                results[symbol] = cached_forecast
            else:
                forecast_data = await ml_service.generate_forecast(market, symbol, horizon_days)
                results[symbol] = forecast_data
                cache_forecast(market, symbol, forecast_data)
        except Exception as e:
            results[symbol] = {"error": str(e)}
    
    return {
        "market": market,
        "forecasts": results,
        "generated_at": datetime.utcnow().isoformat(),
        "horizon_days": horizon_days
    }

@router.get("/trends/{market}")
async def get_market_trends(
    market: str,
    timeframe: str = Query("6m", description="Timeframe: 1m, 3m, 6m, 1y"),
    db: Session = Depends(get_db)
):
    """Get overall market trends and sentiment"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    ml_service = MLService()
    trends = await ml_service.get_market_trends(market, timeframe)
    
    return trends

@router.post("/custom")
async def create_custom_forecast(
    market: str,
    symbol: str,
    custom_parameters: Dict[str, Any],
    horizon_days: int = Query(180, description="Forecast horizon in days"),
    db: Session = Depends(get_db)
):
    """Create custom forecast with specific parameters"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    ml_service = MLService()
    forecast_data = await ml_service.generate_custom_forecast(
        market, symbol, custom_parameters, horizon_days
    )
    
    return forecast_data

@router.get("/history/{market}/{symbol}")
async def get_forecast_history(
    market: str,
    symbol: str,
    days_back: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get historical forecast accuracy and performance"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Query historical forecasts from database
    from app.core.database import Forecast
    from datetime import datetime, timedelta
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    historical_forecasts = db.query(Forecast).filter(
        Forecast.market == market,
        Forecast.symbol == symbol,
        Forecast.created_at >= cutoff_date
    ).order_by(Forecast.created_at.desc()).all()
    
    return {
        "market": market,
        "symbol": symbol,
        "forecasts": [
            {
                "forecast_date": f.created_at.isoformat(),
                "predicted_price": f.predicted_price,
                "confidence_score": f.confidence_score,
                "trend_direction": f.trend_direction,
                "volatility_score": f.volatility_score,
                "model_version": f.model_version
            }
            for f in historical_forecasts
        ],
        "total_forecasts": len(historical_forecasts)
    }
