"""
Volatility API endpoints
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from app.core.database import get_db, get_cached_volatility_score, cache_volatility_score
from app.services.ml_service import MLService
from app.core.config import settings

router = APIRouter()

@router.get("/")
async def get_volatility_scores(
    market: str = Query(..., description="Market type: crypto, logistics, real_estate, ecommerce"),
    symbol: Optional[str] = Query(None, description="Specific symbol"),
    timeframe: str = Query("30d", description="Timeframe: 7d, 30d, 90d"),
    db: Session = Depends(get_db)
):
    """Get real-time volatility scores for specified market and symbol"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Check cache first
    if symbol:
        cached_score = get_cached_volatility_score(market, symbol)
        if cached_score is not None:
            return {
                "market": market,
                "symbol": symbol,
                "volatility_score": cached_score,
                "timeframe": timeframe,
                "generated_at": datetime.utcnow().isoformat(),
                "cached": True
            }
    
    # Calculate new volatility score
    ml_service = MLService()
    volatility_data = await ml_service.calculate_volatility_score(market, symbol, timeframe)
    
    # Cache the result
    if symbol and "volatility_score" in volatility_data:
        cache_volatility_score(market, symbol, volatility_data["volatility_score"])
    
    return volatility_data

@router.get("/{market}/{symbol}")
async def get_symbol_volatility(
    market: str,
    symbol: str,
    timeframe: str = Query("30d", description="Timeframe: 7d, 30d, 90d"),
    include_breakdown: bool = Query(True, description="Include volatility breakdown by factors"),
    db: Session = Depends(get_db)
):
    """Get detailed volatility analysis for a specific symbol"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Check cache first
    cached_score = get_cached_volatility_score(market, symbol)
    if cached_score is not None and not include_breakdown:
        return {
            "market": market,
            "symbol": symbol,
            "volatility_score": cached_score,
            "timeframe": timeframe,
            "generated_at": datetime.utcnow().isoformat(),
            "cached": True
        }
    
    # Calculate detailed volatility analysis
    ml_service = MLService()
    volatility_data = await ml_service.calculate_detailed_volatility(
        market, symbol, timeframe, include_breakdown
    )
    
    # Cache the score
    if "volatility_score" in volatility_data:
        cache_volatility_score(market, symbol, volatility_data["volatility_score"])
    
    return volatility_data

@router.get("/alerts/active")
async def get_active_volatility_alerts(
    market: Optional[str] = Query(None, description="Filter by market"),
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high, critical"),
    db: Session = Depends(get_db)
):
    """Get active volatility alerts"""
    
    from app.core.database import VolatilityAlert
    
    query = db.query(VolatilityAlert).filter(VolatilityAlert.is_active == True)
    
    if market:
        query = query.filter(VolatilityAlert.market == market)
    
    if severity:
        query = query.filter(VolatilityAlert.severity == severity)
    
    alerts = query.order_by(VolatilityAlert.triggered_at.desc()).limit(100).all()
    
    return {
        "alerts": [
            {
                "id": alert.id,
                "market": alert.market,
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "threshold_value": alert.threshold_value,
                "current_value": alert.current_value,
                "message": alert.message,
                "triggered_at": alert.triggered_at.isoformat()
            }
            for alert in alerts
        ],
        "total_alerts": len(alerts),
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/comparison/{market}")
async def compare_volatility(
    market: str,
    symbols: List[str] = Query(..., description="List of symbols to compare"),
    timeframe: str = Query("30d", description="Timeframe for comparison"),
    db: Session = Depends(get_db)
):
    """Compare volatility scores across multiple symbols"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    if len(symbols) > 20:  # Limit comparison size
        raise HTTPException(status_code=400, detail="Maximum 20 symbols per comparison")
    
    ml_service = MLService()
    comparison_data = await ml_service.compare_volatility_scores(market, symbols, timeframe)
    
    return comparison_data

@router.get("/heatmap/{market}")
async def get_volatility_heatmap(
    market: str,
    timeframe: str = Query("30d", description="Timeframe for heatmap"),
    db: Session = Depends(get_db)
):
    """Get volatility heatmap data for market visualization"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    ml_service = MLService()
    heatmap_data = await ml_service.generate_volatility_heatmap(market, timeframe)
    
    return heatmap_data

@router.post("/thresholds")
async def set_volatility_thresholds(
    market: str,
    symbol: str,
    thresholds: Dict[str, float],
    db: Session = Depends(get_db)
):
    """Set custom volatility thresholds for alerts"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Store thresholds in Redis for quick access
    from app.core.database import get_redis
    
    redis_client = get_redis()
    threshold_key = f"volatility_thresholds:{market}:{symbol}"
    redis_client.setex(threshold_key, 86400, json.dumps(thresholds))  # 24 hour TTL
    
    return {
        "market": market,
        "symbol": symbol,
        "thresholds": thresholds,
        "set_at": datetime.utcnow().isoformat()
    }

@router.get("/thresholds/{market}/{symbol}")
async def get_volatility_thresholds(
    market: str,
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get current volatility thresholds for a symbol"""
    
    from app.core.database import get_redis
    
    redis_client = get_redis()
    threshold_key = f"volatility_thresholds:{market}:{symbol}"
    thresholds_data = redis_client.get(threshold_key)
    
    if not thresholds_data:
        return {
            "market": market,
            "symbol": symbol,
            "thresholds": None,
            "message": "No custom thresholds set"
        }
    
    thresholds = json.loads(thresholds_data)
    
    return {
        "market": market,
        "symbol": symbol,
        "thresholds": thresholds,
        "retrieved_at": datetime.utcnow().isoformat()
    }

@router.get("/history/{market}/{symbol}")
async def get_volatility_history(
    market: str,
    symbol: str,
    days_back: int = Query(30, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """Get historical volatility data"""
    
    if market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # This would typically query historical volatility data
    # For now, return a placeholder structure
    ml_service = MLService()
    history_data = await ml_service.get_volatility_history(market, symbol, days_back)
    
    return history_data
