"""
Admin API endpoints
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from sqlalchemy import text
from app.core.database import get_db, get_redis, ModelPerformance
from app.services.ml_service import MLService
from app.services.data_ingestion import DataIngestionService
from app.services.alert_service import AlertService
from app.core.config import settings

router = APIRouter()

@router.get("/status")
async def get_system_status():
    """Get overall system status"""
    
    # Check Redis connection
    try:
        redis_client = get_redis()
        redis_client.ping()
        redis_status = "connected"
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    # Check database connection
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "system_status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "redis": redis_status,
            "data_ingestion": "running",
            "ml_service": "running",
            "alert_service": "running"
        },
        "configuration": {
            "supported_markets": settings.supported_markets,
            "forecast_horizon_days": settings.forecast_horizon_days,
            "volatility_window_days": settings.volatility_window_days,
            "model_update_interval": settings.model_update_interval
        }
    }

@router.get("/models/performance")
async def get_model_performance(
    market: Optional[str] = Query(None, description="Filter by market"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    days_back: int = Query(30, description="Days to look back"),
    db: Session = Depends(get_db)
):
    """Get ML model performance metrics"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    query = db.query(ModelPerformance).filter(
        ModelPerformance.evaluation_date >= cutoff_date
    )
    
    if market:
        query = query.filter(ModelPerformance.market == market)
    
    if model_name:
        query = query.filter(ModelPerformance.model_name == model_name)
    
    performance_data = query.order_by(ModelPerformance.evaluation_date.desc()).all()
    
    # Group by model and market
    grouped_data = {}
    for record in performance_data:
        key = f"{record.model_name}_{record.market}"
        if key not in grouped_data:
            grouped_data[key] = {
                "model_name": record.model_name,
                "market": record.market,
                "metrics": {}
            }
        
        grouped_data[key]["metrics"][record.metric_name] = {
            "value": record.metric_value,
            "evaluation_date": record.evaluation_date.isoformat(),
            "model_version": record.model_version
        }
    
    return {
        "performance_data": list(grouped_data.values()),
        "total_records": len(performance_data),
        "time_period_days": days_back,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.post("/models/retrain")
async def retrain_models(
    market: Optional[str] = Query(None, description="Specific market to retrain"),
    model_type: Optional[str] = Query(None, description="Specific model type"),
    background_tasks: BackgroundTasks = None
):
    """Trigger model retraining"""
    
    ml_service = MLService()
    
    if market and market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Start background retraining
    if market:
        background_tasks.add_task(ml_service.retrain_models, market, model_type)
    else:
        background_tasks.add_task(ml_service.retrain_all_models)
    
    return {
        "message": "Model retraining initiated",
        "market": market,
        "model_type": model_type,
        "initiated_at": datetime.utcnow().isoformat()
    }

@router.get("/data/stats")
async def get_data_statistics(
    market: Optional[str] = Query(None, description="Filter by market"),
    hours_back: int = Query(24, description="Hours to look back"),
    db: Session = Depends(get_db)
):
    """Get data ingestion statistics"""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    from app.core.database import MarketData
    
    query = db.query(MarketData).filter(MarketData.timestamp >= cutoff_time)
    
    if market:
        query = query.filter(MarketData.market == market)
    
    data = query.all()
    
    # Calculate statistics
    market_stats = {}
    source_stats = {}
    
    for record in data:
        # Market statistics
        if record.market not in market_stats:
            market_stats[record.market] = {"count": 0, "sources": set()}
        market_stats[record.market]["count"] += 1
        market_stats[record.market]["sources"].add(record.source)
        
        # Source statistics
        if record.source not in source_stats:
            source_stats[record.source] = {"count": 0, "markets": set()}
        source_stats[record.source]["count"] += 1
        source_stats[record.source]["markets"].add(record.market)
    
    # Convert sets to lists for JSON serialization
    for market_name in market_stats:
        market_stats[market_name]["sources"] = list(market_stats[market_name]["sources"])
    
    for source_name in source_stats:
        source_stats[source_name]["markets"] = list(source_stats[source_name]["markets"])
    
    return {
        "time_period_hours": hours_back,
        "total_records": len(data),
        "market_breakdown": market_stats,
        "source_breakdown": source_stats,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.post("/data/ingest")
async def trigger_data_ingestion(
    market: Optional[str] = Query(None, description="Specific market to ingest"),
    symbols: Optional[List[str]] = Query(None, description="Specific symbols"),
    background_tasks: BackgroundTasks = None
):
    """Trigger data ingestion"""
    
    data_service = DataIngestionService()
    
    if market and market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {market}")
    
    # Start background ingestion
    if market:
        background_tasks.add_task(data_service.ingest_market_data, market, symbols)
    else:
        background_tasks.add_task(data_service.ingest_all_markets)
    
    return {
        "message": "Data ingestion initiated",
        "market": market,
        "symbols": symbols,
        "initiated_at": datetime.utcnow().isoformat()
    }

@router.get("/alerts/stats")
async def get_alert_statistics(
    hours_back: int = Query(24, description="Hours to look back"),
    db: Session = Depends(get_db)
):
    """Get alert statistics"""
    
    from app.core.database import VolatilityAlert, UserAlert
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    # Get triggered alerts
    triggered_alerts = db.query(VolatilityAlert).filter(
        VolatilityAlert.triggered_at >= cutoff_time
    ).all()
    
    # Get user alerts
    user_alerts = db.query(UserAlert).filter(
        UserAlert.created_at >= cutoff_time
    ).all()
    
    # Calculate statistics
    alert_stats = {
        "triggered_alerts": {
            "total": len(triggered_alerts),
            "by_severity": {},
            "by_market": {},
            "by_type": {}
        },
        "user_alerts": {
            "total": len(user_alerts),
            "active": len([a for a in user_alerts if a.is_active]),
            "by_market": {},
            "by_type": {}
        }
    }
    
    # Group triggered alerts
    for alert in triggered_alerts:
        # By severity
        if alert.severity not in alert_stats["triggered_alerts"]["by_severity"]:
            alert_stats["triggered_alerts"]["by_severity"][alert.severity] = 0
        alert_stats["triggered_alerts"]["by_severity"][alert.severity] += 1
        
        # By market
        if alert.market not in alert_stats["triggered_alerts"]["by_market"]:
            alert_stats["triggered_alerts"]["by_market"][alert.market] = 0
        alert_stats["triggered_alerts"]["by_market"][alert.market] += 1
        
        # By type
        if alert.alert_type not in alert_stats["triggered_alerts"]["by_type"]:
            alert_stats["triggered_alerts"]["by_type"][alert.alert_type] = 0
        alert_stats["triggered_alerts"]["by_type"][alert.alert_type] += 1
    
    # Group user alerts
    for alert in user_alerts:
        # By market
        if alert.market not in alert_stats["user_alerts"]["by_market"]:
            alert_stats["user_alerts"]["by_market"][alert.market] = 0
        alert_stats["user_alerts"]["by_market"][alert.market] += 1
        
        # By type
        if alert.alert_type not in alert_stats["user_alerts"]["by_type"]:
            alert_stats["user_alerts"]["by_type"][alert.alert_type] = 0
        alert_stats["user_alerts"]["by_type"][alert.alert_type] += 1
    
    return {
        "time_period_hours": hours_back,
        "alert_statistics": alert_stats,
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/cache/status")
async def get_cache_status():
    """Get Redis cache status and statistics"""
    
    try:
        redis_client = get_redis()
        
        # Get cache info
        info = redis_client.info()
        
        # Get key counts by pattern
        forecast_keys = len(redis_client.keys("forecast:*"))
        volatility_keys = len(redis_client.keys("volatility:*"))
        threshold_keys = len(redis_client.keys("volatility_thresholds:*"))
        
        return {
            "status": "connected",
            "redis_info": {
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses")
            },
            "cache_keys": {
                "forecasts": forecast_keys,
                "volatility_scores": volatility_keys,
                "thresholds": threshold_keys,
                "total": forecast_keys + volatility_keys + threshold_keys
            },
            "generated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "generated_at": datetime.utcnow().isoformat()
        }

@router.post("/cache/clear")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="Cache pattern to clear (e.g., 'forecast:*')")
):
    """Clear Redis cache"""
    
    try:
        redis_client = get_redis()
        
        if pattern:
            keys = redis_client.keys(pattern)
            if keys:
                redis_client.delete(*keys)
                cleared_count = len(keys)
            else:
                cleared_count = 0
        else:
            # Clear all keys
            redis_client.flushdb()
            cleared_count = "all"
        
        return {
            "message": "Cache cleared successfully",
            "pattern": pattern,
            "cleared_keys": cleared_count,
            "cleared_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.get("/logs")
async def get_system_logs(
    level: str = Query("INFO", description="Log level: DEBUG, INFO, WARNING, ERROR"),
    lines: int = Query(100, description="Number of log lines to retrieve")
):
    """Get system logs (placeholder - would need proper logging setup)"""
    
    # This is a placeholder - in a real implementation, you'd read from log files
    return {
        "message": "Log retrieval not implemented",
        "level": level,
        "lines_requested": lines,
        "note": "Implement proper logging system for production use"
    }
