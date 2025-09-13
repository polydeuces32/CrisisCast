"""
Scrapy pipelines for CrisisCast
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any

from app.core.database import get_db, MarketData

logger = logging.getLogger(__name__)

class MarketDataPipeline:
    """Pipeline for processing market data items"""
    
    def __init__(self):
        self.db = None
    
    def open_spider(self, spider):
        """Initialize database connection when spider opens"""
        self.db = next(get_db())
        logger.info("MarketDataPipeline opened")
    
    def close_spider(self, spider):
        """Close database connection when spider closes"""
        if self.db:
            self.db.close()
        logger.info("MarketDataPipeline closed")
    
    def process_item(self, item, spider):
        """Process a market data item"""
        try:
            # Convert item to dictionary
            item_dict = dict(item)
            
            # Extract basic fields
            market = item_dict.get('market')
            symbol = item_dict.get('symbol')
            source = item_dict.get('source')
            price = item_dict.get('price')
            volume = item_dict.get('volume')
            market_cap = item_dict.get('market_cap')
            
            # Prepare additional data
            additional_data = {}
            for key, value in item_dict.items():
                if key not in ['market', 'symbol', 'source', 'price', 'volume', 'market_cap', 'timestamp', 'scraped_at', 'url', 'spider_name']:
                    additional_data[key] = value
            
            # Create MarketData record
            market_data = MarketData(
                market=market,
                symbol=symbol,
                source=source,
                price=float(price) if price else None,
                volume=float(volume) if volume else None,
                market_cap=float(market_cap) if market_cap else None,
                additional_data=additional_data,
                timestamp=datetime.utcnow()
            )
            
            # Save to database
            self.db.add(market_data)
            self.db.commit()
            
            logger.info(f"Saved market data: {market}/{symbol} from {source}")
            
        except Exception as e:
            logger.error(f"Error processing item: {e}")
            self.db.rollback()
        
        return item

class DataValidationPipeline:
    """Pipeline for validating scraped data"""
    
    def process_item(self, item, spider):
        """Validate item data"""
        try:
            # Check required fields
            required_fields = ['market', 'symbol', 'source']
            for field in required_fields:
                if not item.get(field):
                    logger.warning(f"Missing required field: {field}")
                    return None
            
            # Validate market
            valid_markets = ['crypto', 'logistics', 'real_estate', 'ecommerce']
            if item.get('market') not in valid_markets:
                logger.warning(f"Invalid market: {item.get('market')}")
                return None
            
            # Validate price if present
            price = item.get('price')
            if price is not None:
                try:
                    float(price)
                    if float(price) < 0:
                        logger.warning(f"Negative price: {price}")
                        return None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid price format: {price}")
                    return None
            
            # Validate volume if present
            volume = item.get('volume')
            if volume is not None:
                try:
                    float(volume)
                    if float(volume) < 0:
                        logger.warning(f"Negative volume: {volume}")
                        return None
                except (ValueError, TypeError):
                    logger.warning(f"Invalid volume format: {volume}")
                    return None
            
            logger.debug(f"Item validation passed: {item.get('market')}/{item.get('symbol')}")
            
        except Exception as e:
            logger.error(f"Error validating item: {e}")
            return None
        
        return item

class DuplicateFilterPipeline:
    """Pipeline for filtering duplicate items"""
    
    def __init__(self):
        self.seen_items = set()
    
    def process_item(self, item, spider):
        """Filter duplicate items"""
        try:
            # Create a unique key for the item
            item_key = f"{item.get('market')}_{item.get('symbol')}_{item.get('source')}_{item.get('price')}"
            
            if item_key in self.seen_items:
                logger.debug(f"Duplicate item filtered: {item_key}")
                return None
            
            self.seen_items.add(item_key)
            
        except Exception as e:
            logger.error(f"Error filtering duplicates: {e}")
        
        return item

class DataEnrichmentPipeline:
    """Pipeline for enriching scraped data"""
    
    def process_item(self, item, spider):
        """Enrich item with additional data"""
        try:
            # Add timestamp if not present
            if not item.get('timestamp'):
                item['timestamp'] = datetime.utcnow().isoformat()
            
            # Add scraped_at timestamp
            item['scraped_at'] = datetime.utcnow().isoformat()
            
            # Add spider name
            item['spider_name'] = spider.name
            
            # Add URL if available
            if hasattr(spider, 'start_urls') and spider.start_urls:
                item['url'] = spider.start_urls[0]
            
            # Enrich based on market type
            market = item.get('market')
            if market == 'crypto':
                self._enrich_crypto_item(item)
            elif market == 'logistics':
                self._enrich_logistics_item(item)
            elif market == 'real_estate':
                self._enrich_real_estate_item(item)
            elif market == 'ecommerce':
                self._enrich_ecommerce_item(item)
            
        except Exception as e:
            logger.error(f"Error enriching item: {e}")
        
        return item
    
    def _enrich_crypto_item(self, item):
        """Enrich cryptocurrency item"""
        # Add market cap calculation if not present
        if not item.get('market_cap') and item.get('price') and item.get('circulating_supply'):
            try:
                market_cap = float(item.get('price')) * float(item.get('circulating_supply'))
                item['market_cap'] = market_cap
            except (ValueError, TypeError):
                pass
    
    def _enrich_logistics_item(self, item):
        """Enrich logistics item"""
        # Add route information if not present
        if not item.get('route'):
            item['route'] = 'Unknown'
    
    def _enrich_real_estate_item(self, item):
        """Enrich real estate item"""
        # Add price per sqft calculation if not present
        if not item.get('price_per_sqft') and item.get('price') and item.get('square_feet'):
            try:
                price_per_sqft = float(item.get('price')) / float(item.get('square_feet'))
                item['price_per_sqft'] = price_per_sqft
            except (ValueError, TypeError):
                pass
    
    def _enrich_ecommerce_item(self, item):
        """Enrich e-commerce item"""
        # Add period information if not present
        if not item.get('period'):
            item['period'] = 'daily'
