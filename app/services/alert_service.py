"""
Alert service for monitoring and notifications
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from app.core.database import get_db, UserAlert, VolatilityAlert
from app.core.config import settings

logger = logging.getLogger(__name__)

class AlertService:
    """Service for managing alerts and notifications"""
    
    def __init__(self):
        self.running = False
        self.alert_checks = {}
    
    async def start_alert_monitoring(self):
        """Start monitoring for alert conditions"""
        self.running = True
        logger.info("Starting alert monitoring...")
        
        while self.running:
            try:
                await self.check_all_alerts()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retry
    
    async def stop_alert_monitoring(self):
        """Stop alert monitoring"""
        self.running = False
        logger.info("Stopped alert monitoring")
    
    async def check_all_alerts(self):
        """Check all active alerts"""
        try:
            db = next(get_db())
            
            # Get all active user alerts
            active_alerts = db.query(UserAlert).filter(UserAlert.is_active == True).all()
            
            for alert in active_alerts:
                try:
                    await self.check_alert(alert)
                except Exception as e:
                    logger.error(f"Error checking alert {alert.id}: {e}")
            
        except Exception as e:
            logger.error(f"Error checking alerts: {e}")
        finally:
            db.close()
    
    async def check_alert(self, alert: UserAlert):
        """Check a specific alert"""
        try:
            # Get current market data
            current_value = await self._get_current_value(alert.market, alert.symbol)
            
            if current_value is None:
                logger.warning(f"Could not get current value for {alert.market}/{alert.symbol}")
                return
            
            # Check if alert condition is met
            alert_triggered = False
            message = ""
            
            if alert.alert_type == "price_above":
                if current_value > alert.threshold_value:
                    alert_triggered = True
                    message = f"Price alert: {alert.symbol} is now ${current_value:.2f}, above threshold of ${alert.threshold_value:.2f}"
            
            elif alert.alert_type == "price_below":
                if current_value < alert.threshold_value:
                    alert_triggered = True
                    message = f"Price alert: {alert.symbol} is now ${current_value:.2f}, below threshold of ${alert.threshold_value:.2f}"
            
            elif alert.alert_type == "volatility_high":
                volatility_score = await self._get_volatility_score(alert.market, alert.symbol)
                if volatility_score > alert.threshold_value:
                    alert_triggered = True
                    message = f"Volatility alert: {alert.symbol} volatility is {volatility_score:.2f}, above threshold of {alert.threshold_value:.2f}"
            
            elif alert.alert_type == "volume_spike":
                volume_change = await self._get_volume_change(alert.market, alert.symbol)
                if volume_change > alert.threshold_value:
                    alert_triggered = True
                    message = f"Volume alert: {alert.symbol} volume increased by {volume_change:.1f}%, above threshold of {alert.threshold_value:.1f}%"
            
            # Trigger alert if condition is met
            if alert_triggered:
                await self._trigger_alert(alert, current_value, message)
            
        except Exception as e:
            logger.error(f"Error checking alert {alert.id}: {e}")
    
    async def _get_current_value(self, market: str, symbol: str) -> Optional[float]:
        """Get current value for a symbol"""
        try:
            db = next(get_db())
            
            # Get latest price data
            latest_data = db.query(MarketData).filter(
                MarketData.market == market,
                MarketData.symbol == symbol
            ).order_by(MarketData.timestamp.desc()).first()
            
            if latest_data and latest_data.price:
                return float(latest_data.price)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting current value: {e}")
            return None
        finally:
            db.close()
    
    async def _get_volatility_score(self, market: str, symbol: str) -> float:
        """Get current volatility score for a symbol"""
        try:
            # This would integrate with the ML service
            # For now, return a simulated value
            import random
            return random.uniform(0.1, 0.9)
            
        except Exception as e:
            logger.error(f"Error getting volatility score: {e}")
            return 0.5
    
    async def _get_volume_change(self, market: str, symbol: str) -> float:
        """Get volume change percentage for a symbol"""
        try:
            db = next(get_db())
            
            # Get recent volume data
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            recent_data = db.query(MarketData).filter(
                MarketData.market == market,
                MarketData.symbol == symbol,
                MarketData.timestamp >= cutoff_time
            ).order_by(MarketData.timestamp.asc()).all()
            
            if len(recent_data) < 2:
                return 0.0
            
            # Calculate volume change
            current_volume = recent_data[-1].volume or 0
            previous_volume = recent_data[0].volume or 0
            
            if previous_volume == 0:
                return 0.0
            
            volume_change = ((current_volume - previous_volume) / previous_volume) * 100
            return volume_change
            
        except Exception as e:
            logger.error(f"Error getting volume change: {e}")
            return 0.0
        finally:
            db.close()
    
    async def _trigger_alert(self, alert: UserAlert, current_value: float, message: str):
        """Trigger an alert"""
        try:
            db = next(get_db())
            
            # Create volatility alert record
            volatility_alert = VolatilityAlert(
                market=alert.market,
                symbol=alert.symbol,
                alert_type=alert.alert_type,
                threshold_value=alert.threshold_value,
                current_value=current_value,
                severity=self._determine_severity(alert.alert_type, current_value, alert.threshold_value),
                message=message,
                is_active=True
            )
            
            db.add(volatility_alert)
            db.commit()
            
            # Send notification
            await self._send_notification(alert, message)
            
            logger.info(f"Alert triggered: {alert.market}/{alert.symbol} - {message}")
            
        except Exception as e:
            logger.error(f"Error triggering alert: {e}")
        finally:
            db.close()
    
    def _determine_severity(self, alert_type: str, current_value: float, threshold_value: float) -> str:
        """Determine alert severity"""
        try:
            if alert_type in ["price_above", "price_below"]:
                # Calculate percentage deviation
                deviation = abs(current_value - threshold_value) / threshold_value
                
                if deviation > 0.2:  # 20% deviation
                    return "critical"
                elif deviation > 0.1:  # 10% deviation
                    return "high"
                elif deviation > 0.05:  # 5% deviation
                    return "medium"
                else:
                    return "low"
            
            elif alert_type == "volatility_high":
                if current_value > 0.8:
                    return "critical"
                elif current_value > 0.6:
                    return "high"
                elif current_value > 0.4:
                    return "medium"
                else:
                    return "low"
            
            elif alert_type == "volume_spike":
                if current_value > 200:  # 200% increase
                    return "critical"
                elif current_value > 100:  # 100% increase
                    return "high"
                elif current_value > 50:  # 50% increase
                    return "medium"
                else:
                    return "low"
            
            return "medium"
            
        except Exception as e:
            logger.error(f"Error determining severity: {e}")
            return "medium"
    
    async def _send_notification(self, alert: UserAlert, message: str):
        """Send notification based on alert configuration"""
        try:
            if alert.notification_method == "email":
                await self._send_email_notification(alert, message)
            elif alert.notification_method == "webhook":
                await self._send_webhook_notification(alert, message)
            elif alert.notification_method == "sms":
                await self._send_sms_notification(alert, message)
            else:
                logger.warning(f"Unknown notification method: {alert.notification_method}")
                
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def _send_email_notification(self, alert: UserAlert, message: str):
        """Send email notification"""
        try:
            if not settings.alert_email_username or not settings.alert_email_password:
                logger.warning("Email credentials not configured")
                return
            
            # Create message
            msg = MimeMultipart()
            msg['From'] = settings.alert_email_username
            msg['To'] = alert.notification_endpoint
            msg['Subject'] = f"CrisisCast Alert: {alert.market}/{alert.symbol}"
            
            # Create email body
            body = f"""
            CrisisCast Alert Notification
            
            {message}
            
            Alert Details:
            - Market: {alert.market}
            - Symbol: {alert.symbol}
            - Alert Type: {alert.alert_type}
            - Threshold: {alert.threshold_value}
            - Time: {datetime.utcnow().isoformat()}
            
            This is an automated alert from CrisisCast.
            """
            
            msg.attach(MimeText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(settings.alert_email_smtp_server, settings.alert_email_port)
            server.starttls()
            server.login(settings.alert_email_username, settings.alert_email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent to {alert.notification_endpoint}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    async def _send_webhook_notification(self, alert: UserAlert, message: str):
        """Send webhook notification"""
        try:
            payload = {
                "alert_id": alert.id,
                "market": alert.market,
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "message": message,
                "threshold_value": alert.threshold_value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = requests.post(
                alert.notification_endpoint,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Webhook notification sent to {alert.notification_endpoint}")
            else:
                logger.warning(f"Webhook notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
    
    async def _send_sms_notification(self, alert: UserAlert, message: str):
        """Send SMS notification (placeholder)"""
        try:
            # This would integrate with an SMS service like Twilio
            logger.info(f"SMS notification would be sent to {alert.notification_endpoint}: {message}")
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
    
    async def send_test_notification(self, alert: UserAlert) -> Dict[str, Any]:
        """Send test notification for an alert"""
        try:
            test_message = f"Test notification for {alert.market}/{alert.symbol} alert"
            
            await self._send_notification(alert, test_message)
            
            return {
                "success": True,
                "message": "Test notification sent successfully",
                "notification_method": alert.notification_method,
                "endpoint": alert.notification_endpoint
            }
            
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            return {
                "success": False,
                "message": f"Error sending test notification: {str(e)}",
                "notification_method": alert.notification_method,
                "endpoint": alert.notification_endpoint
            }
    
    async def get_alert_statistics(self, user_id: str, days_back: int = 30) -> Dict[str, Any]:
        """Get alert statistics for a user"""
        try:
            db = next(get_db())
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            # Get user alerts
            user_alerts = db.query(UserAlert).filter(
                UserAlert.user_id == user_id,
                UserAlert.created_at >= cutoff_date
            ).all()
            
            # Get triggered alerts
            triggered_alerts = db.query(VolatilityAlert).filter(
                VolatilityAlert.triggered_at >= cutoff_date
            ).all()
            
            # Calculate statistics
            stats = {
                "total_alerts": len(user_alerts),
                "active_alerts": len([a for a in user_alerts if a.is_active]),
                "triggered_alerts": len(triggered_alerts),
                "alerts_by_market": {},
                "alerts_by_type": {},
                "triggered_by_severity": {}
            }
            
            # Group by market
            for alert in user_alerts:
                if alert.market not in stats["alerts_by_market"]:
                    stats["alerts_by_market"][alert.market] = 0
                stats["alerts_by_market"][alert.market] += 1
            
            # Group by type
            for alert in user_alerts:
                if alert.alert_type not in stats["alerts_by_type"]:
                    stats["alerts_by_type"][alert.alert_type] = 0
                stats["alerts_by_type"][alert.alert_type] += 1
            
            # Group triggered alerts by severity
            for alert in triggered_alerts:
                if alert.severity not in stats["triggered_by_severity"]:
                    stats["triggered_by_severity"][alert.severity] = 0
                stats["triggered_by_severity"][alert.severity] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {}
        finally:
            db.close()
