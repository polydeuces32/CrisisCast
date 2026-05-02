"""
Alert API endpoints
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db, UserAlert, VolatilityAlert
from app.core.enums import MarketType, AlertType, NotificationMethod
from app.services.alert_service import AlertService
from app.core.config import settings

router = APIRouter()

# Pydantic models for request/response
class AlertCreate(BaseModel):
    user_id: str
    market: MarketType
    symbol: str
    alert_type: AlertType
    threshold_value: float
    notification_method: NotificationMethod
    notification_endpoint: str

class AlertUpdate(BaseModel):
    threshold_value: Optional[float] = None
    is_active: Optional[bool] = None
    notification_method: Optional[str] = None
    notification_endpoint: Optional[str] = None

@router.get("/")
async def get_user_alerts(
    user_id: str = Query(..., description="User ID"),
    market: Optional[str] = Query(None, description="Filter by market"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db)
):
    """Get all alerts for a user"""
    
    query = db.query(UserAlert).filter(UserAlert.user_id == user_id)
    
    if market:
        query = query.filter(UserAlert.market == market)
    
    if is_active is not None:
        query = query.filter(UserAlert.is_active == is_active)
    
    alerts = query.order_by(UserAlert.created_at.desc()).all()
    
    return {
        "user_id": user_id,
        "alerts": [
            {
                "id": alert.id,
                "market": alert.market,
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "threshold_value": alert.threshold_value,
                "is_active": alert.is_active,
                "notification_method": alert.notification_method,
                "notification_endpoint": alert.notification_endpoint,
                "created_at": alert.created_at.isoformat()
            }
            for alert in alerts
        ],
        "total_alerts": len(alerts)
    }

@router.post("/")
async def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db)
):
    """Create a new alert"""
    
    if alert_data.market not in settings.supported_markets:
        raise HTTPException(status_code=400, detail=f"Unsupported market: {alert_data.market}")
    
    # Check if similar alert already exists
    existing_alert = db.query(UserAlert).filter(
        UserAlert.user_id == alert_data.user_id,
        UserAlert.market == alert_data.market,
        UserAlert.symbol == alert_data.symbol,
        UserAlert.alert_type == alert_data.alert_type,
        UserAlert.is_active == True
    ).first()
    
    if existing_alert:
        raise HTTPException(status_code=400, detail="Similar active alert already exists")
    
    # Create new alert
    new_alert = UserAlert(
        user_id=alert_data.user_id,
        market=alert_data.market,
        symbol=alert_data.symbol,
        alert_type=alert_data.alert_type,
        threshold_value=alert_data.threshold_value,
        notification_method=alert_data.notification_method,
        notification_endpoint=alert_data.notification_endpoint
    )
    
    db.add(new_alert)
    db.commit()
    db.refresh(new_alert)
    
    return {
        "id": new_alert.id,
        "message": "Alert created successfully",
        "alert": {
            "user_id": new_alert.user_id,
            "market": new_alert.market,
            "symbol": new_alert.symbol,
            "alert_type": new_alert.alert_type,
            "threshold_value": new_alert.threshold_value,
            "notification_method": new_alert.notification_method,
            "notification_endpoint": new_alert.notification_endpoint,
            "created_at": new_alert.created_at.isoformat()
        }
    }

@router.put("/{alert_id}")
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing alert"""
    
    alert = db.query(UserAlert).filter(UserAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Update fields if provided
    if alert_update.threshold_value is not None:
        alert.threshold_value = alert_update.threshold_value
    
    if alert_update.is_active is not None:
        alert.is_active = alert_update.is_active
    
    if alert_update.notification_method is not None:
        alert.notification_method = alert_update.notification_method
    
    if alert_update.notification_endpoint is not None:
        alert.notification_endpoint = alert_update.notification_endpoint
    
    db.commit()
    db.refresh(alert)
    
    return {
        "id": alert.id,
        "message": "Alert updated successfully",
        "alert": {
            "user_id": alert.user_id,
            "market": alert.market,
            "symbol": alert.symbol,
            "alert_type": alert.alert_type,
            "threshold_value": alert.threshold_value,
            "is_active": alert.is_active,
            "notification_method": alert.notification_method,
            "notification_endpoint": alert.notification_endpoint,
            "created_at": alert.created_at.isoformat()
        }
    }

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Delete an alert"""
    
    alert = db.query(UserAlert).filter(UserAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db.delete(alert)
    db.commit()
    
    return {"message": "Alert deleted successfully"}

@router.get("/triggered")
async def get_triggered_alerts(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    market: Optional[str] = Query(None, description="Filter by market"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    hours_back: int = Query(24, description="Hours to look back"),
    db: Session = Depends(get_db)
):
    """Get recently triggered alerts"""
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
    
    query = db.query(VolatilityAlert).filter(
        VolatilityAlert.triggered_at >= cutoff_time
    )
    
    if user_id:
        pairs = (
            db.query(UserAlert.market, UserAlert.symbol)
            .filter(UserAlert.user_id == user_id)
            .distinct()
            .all()
        )
        if not pairs:
            return {"triggered_alerts": [], "total_triggered": 0, "time_range_hours": hours_back}
        query = query.filter(
            or_(*[and_(VolatilityAlert.market == m, VolatilityAlert.symbol == s) for m, s in pairs])
        )
    
    if market:
        query = query.filter(VolatilityAlert.market == market)
    
    if severity:
        query = query.filter(VolatilityAlert.severity == severity)
    
    alerts = query.order_by(VolatilityAlert.triggered_at.desc()).all()
    
    return {
        "triggered_alerts": [
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
        "total_triggered": len(alerts),
        "time_range_hours": hours_back
    }

@router.post("/test/{alert_id}")
async def test_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Test an alert by sending a test notification"""
    
    alert = db.query(UserAlert).filter(UserAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # Send test notification
    alert_service = AlertService()
    test_result = await alert_service.send_test_notification(alert)
    
    return {
        "alert_id": alert_id,
        "test_result": test_result,
        "tested_at": datetime.utcnow().isoformat()
    }

@router.get("/stats/{user_id}")
async def get_alert_stats(
    user_id: str,
    days_back: int = Query(30, description="Days to look back for stats"),
    db: Session = Depends(get_db)
):
    """Get alert statistics for a user"""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)
    
    # Get user alerts
    user_alerts = db.query(UserAlert).filter(
        UserAlert.user_id == user_id,
        UserAlert.created_at >= cutoff_date
    ).all()
    
    # Get triggered alerts (this would need proper user association)
    triggered_alerts = db.query(VolatilityAlert).filter(
        VolatilityAlert.triggered_at >= cutoff_date
    ).all()
    
    # Calculate stats
    total_alerts = len(user_alerts)
    active_alerts = len([a for a in user_alerts if a.is_active])
    triggered_count = len(triggered_alerts)
    
    # Group by market
    market_stats = {}
    for alert in user_alerts:
        if alert.market not in market_stats:
            market_stats[alert.market] = {"total": 0, "active": 0}
        market_stats[alert.market]["total"] += 1
        if alert.is_active:
            market_stats[alert.market]["active"] += 1
    
    return {
        "user_id": user_id,
        "time_period_days": days_back,
        "total_alerts": total_alerts,
        "active_alerts": active_alerts,
        "triggered_alerts": triggered_count,
        "market_breakdown": market_stats,
        "generated_at": datetime.utcnow().isoformat()
    }
