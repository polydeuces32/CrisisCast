"""
Cryptocurrency data spider
"""

import scrapy
import json
import re
from datetime import datetime
from app.scrapers.items import CryptoDataItem, MarketDataItem

class CryptoSpider(scrapy.Spider):
    """Spider for scraping cryptocurrency data"""
    
    name = 'crypto'
    allowed_domains = ['coinmarketcap.com', 'coingecko.com', 'binance.com']
    
    def start_requests(self):
        """Generate initial requests"""
        urls = [
            'https://coinmarketcap.com/',
            'https://www.coingecko.com/en',
        ]
        
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)
    
    def parse(self, response):
        """Parse cryptocurrency data from CoinMarketCap"""
        if 'coinmarketcap.com' in response.url:
            yield from self.parse_coinmarketcap(response)
        elif 'coingecko.com' in response.url:
            yield from self.parse_coingecko(response)
    
    def parse_coinmarketcap(self, response):
        """Parse data from CoinMarketCap"""
        # This is a simplified parser - in practice, you'd need to handle the actual HTML structure
        
        # Look for cryptocurrency data in the page
        crypto_data = response.css('tr.cmc-table-row')
        
        for crypto in crypto_data[:20]:  # Limit to top 20
            try:
                # Extract symbol
                symbol = crypto.css('td:nth-child(3) div::text').get()
                if not symbol:
                    continue
                
                # Extract name
                name = crypto.css('td:nth-child(3) p::text').get()
                
                # Extract price
                price_text = crypto.css('td:nth-child(4) div::text').get()
                price = self._extract_number(price_text)
                
                # Extract market cap
                market_cap_text = crypto.css('td:nth-child(5) div::text').get()
                market_cap = self._extract_number(market_cap_text)
                
                # Extract volume
                volume_text = crypto.css('td:nth-child(6) div::text').get()
                volume = self._extract_number(volume_text)
                
                # Extract price change
                change_text = crypto.css('td:nth-child(5) div::text').get()
                price_change = self._extract_number(change_text)
                
                # Create item
                item = CryptoDataItem()
                item['symbol'] = symbol.strip()
                item['name'] = name.strip() if name else symbol.strip()
                item['price'] = price
                item['price_change_24h'] = price_change
                item['volume_24h'] = volume
                item['market_cap'] = market_cap
                item['last_updated'] = datetime.utcnow().isoformat()
                
                # Additional data
                item['additional_data'] = {
                    'source': 'coinmarketcap',
                    'scraped_at': datetime.utcnow().isoformat(),
                    'url': response.url
                }
                
                yield item
                
                # Also create a MarketDataItem for compatibility
                market_item = MarketDataItem()
                market_item['market'] = 'crypto'
                market_item['symbol'] = symbol.strip()
                market_item['source'] = 'coinmarketcap'
                market_item['price'] = price
                market_item['volume'] = volume
                market_item['market_cap'] = market_cap
                market_item['additional_data'] = {
                    'name': name.strip() if name else symbol.strip(),
                    'price_change_24h': price_change,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                yield market_item
                
            except Exception as e:
                self.logger.error(f"Error parsing crypto data: {e}")
    
    def parse_coingecko(self, response):
        """Parse data from CoinGecko"""
        # This is a simplified parser - in practice, you'd need to handle the actual HTML structure
        
        # Look for cryptocurrency data in the page
        crypto_data = response.css('tr')
        
        for crypto in crypto_data[:20]:  # Limit to top 20
            try:
                # Extract symbol and name
                symbol_elem = crypto.css('td:nth-child(3) span::text').get()
                if not symbol_elem:
                    continue
                
                symbol = symbol_elem.strip().upper()
                
                # Extract price
                price_text = crypto.css('td:nth-child(4) span::text').get()
                price = self._extract_number(price_text)
                
                # Extract market cap
                market_cap_text = crypto.css('td:nth-child(5) span::text').get()
                market_cap = self._extract_number(market_cap_text)
                
                # Extract volume
                volume_text = crypto.css('td:nth-child(6) span::text').get()
                volume = self._extract_number(volume_text)
                
                # Create item
                item = CryptoDataItem()
                item['symbol'] = symbol
                item['name'] = symbol  # CoinGecko doesn't always have full names in this view
                item['price'] = price
                item['volume_24h'] = volume
                item['market_cap'] = market_cap
                item['last_updated'] = datetime.utcnow().isoformat()
                
                # Additional data
                item['additional_data'] = {
                    'source': 'coingecko',
                    'scraped_at': datetime.utcnow().isoformat(),
                    'url': response.url
                }
                
                yield item
                
                # Also create a MarketDataItem for compatibility
                market_item = MarketDataItem()
                market_item['market'] = 'crypto'
                market_item['symbol'] = symbol
                market_item['source'] = 'coingecko'
                market_item['price'] = price
                market_item['volume'] = volume
                market_item['market_cap'] = market_cap
                market_item['additional_data'] = {
                    'name': symbol,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                yield market_item
                
            except Exception as e:
                self.logger.error(f"Error parsing CoinGecko data: {e}")
    
    def _extract_number(self, text):
        """Extract number from text, handling various formats"""
        if not text:
            return None
        
        # Remove common currency symbols and text
        text = re.sub(r'[^\d.,\-+]', '', text)
        
        # Handle different number formats
        if 'B' in text.upper():
            # Billions
            number = float(re.sub(r'[^\d.,\-+]', '', text))
            return number * 1_000_000_000
        elif 'M' in text.upper():
            # Millions
            number = float(re.sub(r'[^\d.,\-+]', '', text))
            return number * 1_000_000
        elif 'K' in text.upper():
            # Thousands
            number = float(re.sub(r'[^\d.,\-+]', '', text))
            return number * 1_000
        else:
            # Regular number
            try:
                return float(re.sub(r'[^\d.,\-+]', '', text))
            except ValueError:
                return None
