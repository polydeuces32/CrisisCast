from enum import Enum


class MarketType(str, Enum):
    crypto = "crypto"
    logistics = "logistics"
    real_estate = "real_estate"
    ecommerce = "ecommerce"


class AlertType(str, Enum):
    price_above = "price_above"
    price_below = "price_below"
    volatility_high = "volatility_high"
    volume_spike = "volume_spike"


class NotificationMethod(str, Enum):
    email = "email"
    webhook = "webhook"
    sms = "sms"


class Timeframe(str, Enum):
    seven_days = "7d"
    thirty_days = "30d"
    ninety_days = "90d"
