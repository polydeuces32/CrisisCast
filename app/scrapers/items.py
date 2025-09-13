"""
Scrapy items for CrisisCast
"""

import scrapy
from scrapy import Field

class MarketDataItem(scrapy.Item):
    """Item for storing market data"""
    
    # Basic fields
    market = Field()
    symbol = Field()
    source = Field()
    timestamp = Field()
    price = Field()
    volume = Field()
    market_cap = Field()
    
    # Additional data fields
    additional_data = Field()
    
    # Metadata
    scraped_at = Field()
    url = Field()
    spider_name = Field()

class CryptoDataItem(scrapy.Item):
    """Item for cryptocurrency data"""
    
    symbol = Field()
    name = Field()
    price = Field()
    price_change_24h = Field()
    price_change_percent_24h = Field()
    volume_24h = Field()
    market_cap = Field()
    market_cap_rank = Field()
    circulating_supply = Field()
    total_supply = Field()
    max_supply = Field()
    ath = Field()  # All-time high
    atl = Field()  # All-time low
    ath_change_percent = Field()
    atl_change_percent = Field()
    last_updated = Field()
    
    # Additional fields
    additional_data = Field()

class LogisticsDataItem(scrapy.Item):
    """Item for logistics and shipping data"""
    
    route = Field()
    container_type = Field()
    rate_type = Field()  # spot, contract
    price = Field()
    currency = Field()
    valid_from = Field()
    valid_to = Field()
    carrier = Field()
    service_type = Field()
    
    # Additional fields
    additional_data = Field()

class RealEstateDataItem(scrapy.Item):
    """Item for real estate data"""
    
    property_type = Field()
    location = Field()
    price = Field()
    price_per_sqft = Field()
    square_feet = Field()
    bedrooms = Field()
    bathrooms = Field()
    year_built = Field()
    days_on_market = Field()
    listing_type = Field()  # for_sale, for_rent
    zillow_zestimate = Field()
    
    # Additional fields
    additional_data = Field()

class EcommerceDataItem(scrapy.Item):
    """Item for e-commerce data"""
    
    platform = Field()
    metric_type = Field()  # gmv, sales, orders, etc.
    value = Field()
    currency = Field()
    period = Field()  # daily, weekly, monthly
    category = Field()
    region = Field()
    
    # Additional fields
    additional_data = Field()

class NewsItem(scrapy.Item):
    """Item for news and sentiment data"""
    
    title = Field()
    content = Field()
    url = Field()
    source = Field()
    published_at = Field()
    sentiment_score = Field()
    sentiment_label = Field()  # positive, negative, neutral
    market = Field()
    symbols = Field()  # List of symbols mentioned
    tags = Field()
    
    # Additional fields
    additional_data = Field()
