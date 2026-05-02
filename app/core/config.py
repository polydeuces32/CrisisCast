"""
Configuration settings for CrisisCast
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    api_key: str = Field(default="crisiscast-dev-key", env="API_KEY")
    secret_key: str = Field(default="crisiscast-secret-key", env="SECRET_KEY")
    
    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./crisiscast.db", 
        env="DATABASE_URL"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # External API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    alpha_vantage_api_key: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_API_KEY")
    coinmarketcap_api_key: Optional[str] = Field(default=None, env="COINMARKETCAP_API_KEY")
    
    # Scrapy Settings
    scrapy_delay: int = Field(default=1, env="SCRAPY_DELAY")
    scrapy_concurrent_requests: int = Field(default=16, env="SCRAPY_CONCURRENT_REQUESTS")
    scrapy_concurrent_requests_per_domain: int = Field(default=8, env="SCRAPY_CONCURRENT_REQUESTS_PER_DOMAIN")
    
    # Model Settings
    model_update_interval: int = Field(default=3600, env="MODEL_UPDATE_INTERVAL")  # seconds
    data_ingestion_interval: int = Field(default=300, env="DATA_INGESTION_INTERVAL")  # seconds (5 min)
    forecast_horizon_days: int = Field(default=180, env="FORECAST_HORIZON_DAYS")  # 6 months
    volatility_window_days: int = Field(default=30, env="VOLATILITY_WINDOW_DAYS")
    
    # Alert Settings
    alert_email_smtp_server: str = Field(default="smtp.gmail.com", env="ALERT_EMAIL_SMTP_SERVER")
    alert_email_port: int = Field(default=587, env="ALERT_EMAIL_PORT")
    alert_email_username: Optional[str] = Field(default=None, env="ALERT_EMAIL_USERNAME")
    alert_email_password: Optional[str] = Field(default=None, env="ALERT_EMAIL_PASSWORD")
    
    # Market Configuration
    supported_markets: list = [
        "crypto",
        "logistics", 
        "real_estate",
        "ecommerce"
    ]
    
    # Data Sources
    crypto_sources: list = [
        "coinmarketcap",
        "coingecko",
        "binance",
        "coinbase"
    ]
    
    logistics_sources: list = [
        "freightos",
        "drewry",
        "worldshipping",
        "maritime-executive"
    ]
    
    real_estate_sources: list = [
        "zillow",
        "realtor",
        "redfin",
        "apartment-list"
    ]
    
    ecommerce_sources: list = [
        "shopify",
        "amazon",
        "ebay",
        "etsy"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        protected_namespaces = ('settings_',)

# Create settings instance
settings = Settings()
