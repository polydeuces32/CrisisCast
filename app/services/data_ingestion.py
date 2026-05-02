"""
Data ingestion service using Scrapy and various APIs
"""

from __future__ import annotations

import asyncio
import aiohttp
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
# import yfinance as yf  # Commented out due to Python 3.8 compatibility issues
import ccxt
import requests
from bs4 import BeautifulSoup
import pandas as pd

from app.core.config import settings
from app.core.database import get_db, MarketData

logger = logging.getLogger(__name__)

class DataIngestionService:
    """Service for ingesting data from various sources"""
    
    def __init__(self):
        self.session = None
        self.exchanges = {}
        self.running = False
        
    async def start_continuous_ingestion(self):
        """Start continuous data ingestion"""
        self.running = True
        logger.info("Starting continuous data ingestion...")
        
        # Initialize HTTP session
        self.session = aiohttp.ClientSession()
        
        # Initialize crypto exchanges
        self.exchanges = {
            'binance': ccxt.binance(),
            'coinbase': ccxt.coinbase(),
            'kraken': ccxt.kraken()
        }
        
        # Start ingestion tasks for each market
        tasks = []
        for market in settings.supported_markets:
            task = asyncio.create_task(self._continuous_ingestion_loop(market))
            tasks.append(task)
        
        # Wait for all tasks
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def stop_continuous_ingestion(self):
        """Stop continuous data ingestion"""
        self.running = False
        if self.session:
            await self.session.close()
        logger.info("Stopped continuous data ingestion")
    
    async def _continuous_ingestion_loop(self, market: str):
        """Continuous ingestion loop for a specific market"""
        while self.running:
            try:
                await self.ingest_market_data(market)
                await asyncio.sleep(settings.model_update_interval)  # Wait before next ingestion
            except Exception as e:
                logger.error(f"Error in continuous ingestion for {market}: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def ingest_market_data(self, market: str, symbols: Optional[List[str]] = None):
        """Ingest data for a specific market"""
        logger.info(f"Ingesting data for market: {market}")
        
        try:
            if market == "crypto":
                await self._ingest_crypto_data(symbols)
            elif market == "logistics":
                await self._ingest_logistics_data(symbols)
            elif market == "real_estate":
                await self._ingest_real_estate_data(symbols)
            elif market == "ecommerce":
                await self._ingest_ecommerce_data(symbols)
            else:
                logger.warning(f"Unknown market: {market}")
                
        except Exception as e:
            logger.error(f"Error ingesting data for {market}: {e}")
    
    async def ingest_all_markets(self):
        """Ingest data for all supported markets"""
        for market in settings.supported_markets:
            await self.ingest_market_data(market)
    
    async def _ingest_crypto_data(self, symbols: Optional[List[str]] = None):
        """Ingest cryptocurrency data"""
        logger.info("Ingesting crypto data...")
        
        # Default crypto symbols if none specified
        if not symbols:
            symbols = ['BTC', 'ETH', 'BNB', 'ADA', 'SOL', 'DOT', 'AVAX', 'MATIC']
        
        # Ingest from multiple exchanges
        for exchange_name, exchange in self.exchanges.items():
            try:
                await self._ingest_from_crypto_exchange(exchange_name, exchange, symbols)
            except Exception as e:
                logger.error(f"Error ingesting from {exchange_name}: {e}")
        
        # Ingest from CoinMarketCap API
        if settings.coinmarketcap_api_key:
            await self._ingest_from_coinmarketcap(symbols)
    
    async def _ingest_from_crypto_exchange(self, exchange_name: str, exchange, symbols: List[str]):
        """Ingest data from a crypto exchange"""
        try:
            # Get ticker data
            tickers = exchange.fetch_tickers()
            
            for symbol in symbols:
                if symbol in tickers:
                    ticker = tickers[symbol]
                    
                    # Store data
                    await self._store_market_data(
                        market="crypto",
                        symbol=symbol,
                        source=exchange_name,
                        price=ticker.get('last'),
                        volume=ticker.get('baseVolume'),
                        market_cap=None,  # Not available from exchange
                        additional_data={
                            'bid': ticker.get('bid'),
                            'ask': ticker.get('ask'),
                            'high': ticker.get('high'),
                            'low': ticker.get('low'),
                            'change': ticker.get('change'),
                            'percentage': ticker.get('percentage')
                        }
                    )
                    
        except Exception as e:
            logger.error(f"Error ingesting from {exchange_name}: {e}")
    
    async def _ingest_from_coinmarketcap(self, symbols: List[str]):
        """Ingest data from CoinMarketCap API"""
        if not settings.coinmarketcap_api_key:
            return
        
        try:
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
            headers = {
                'X-CMC_PRO_API_KEY': settings.coinmarketcap_api_key,
                'Accept': 'application/json'
            }
            
            params = {
                'symbol': ','.join(symbols),
                'convert': 'USD'
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for symbol, info in data.get('data', {}).items():
                        quote = info.get('quote', {}).get('USD', {})
                        
                        await self._store_market_data(
                            market="crypto",
                            symbol=symbol,
                            source="coinmarketcap",
                            price=quote.get('price'),
                            volume=quote.get('volume_24h'),
                            market_cap=quote.get('market_cap'),
                            additional_data={
                                'market_cap_dominance': quote.get('market_cap_dominance'),
                                'percent_change_1h': quote.get('percent_change_1h'),
                                'percent_change_24h': quote.get('percent_change_24h'),
                                'percent_change_7d': quote.get('percent_change_7d'),
                                'circulating_supply': info.get('circulating_supply'),
                                'total_supply': info.get('total_supply')
                            }
                        )
                        
        except Exception as e:
            logger.error(f"Error ingesting from CoinMarketCap: {e}")
    
    async def _ingest_logistics_data(self, symbols: Optional[List[str]] = None):
        """Ingest logistics and shipping data"""
        logger.info("Ingesting logistics data...")
        
        # Default logistics symbols
        if not symbols:
            symbols = ['FREIGHT_INDEX', 'SHIPPING_RATES', 'CONTAINER_COSTS']
        
        # Ingest from various logistics sources
        await self._ingest_freightos_data(symbols)
        await self._ingest_drewry_data(symbols)
    
    async def _ingest_freightos_data(self, symbols: List[str]):
        """Ingest data from Freightos"""
        try:
            # This is a placeholder - would need actual Freightos API integration
            for symbol in symbols:
                # Simulate freight rate data
                freight_rate = 2500 + (hash(symbol) % 1000)  # Simulated rate
                
                await self._store_market_data(
                    market="logistics",
                    symbol=symbol,
                    source="freightos",
                    price=freight_rate,
                    volume=None,
                    market_cap=None,
                    additional_data={
                        'route': 'Asia-Europe',
                        'container_type': '40ft',
                        'rate_type': 'spot'
                    }
                )
                
        except Exception as e:
            logger.error(f"Error ingesting Freightos data: {e}")
    
    async def _ingest_drewry_data(self, symbols: List[str]):
        """Ingest data from Drewry"""
        try:
            # This is a placeholder - would need actual Drewry API integration
            for symbol in symbols:
                # Simulate Drewry index data
                drewry_index = 1500 + (hash(symbol) % 500)  # Simulated index
                
                await self._store_market_data(
                    market="logistics",
                    symbol=symbol,
                    source="drewry",
                    price=drewry_index,
                    volume=None,
                    market_cap=None,
                    additional_data={
                        'index_type': 'freight',
                        'region': 'global',
                        'update_frequency': 'weekly'
                    }
                )
                
        except Exception as e:
            logger.error(f"Error ingesting Drewry data: {e}")
    
    async def _ingest_real_estate_data(self, symbols: Optional[List[str]] = None):
        """Ingest real estate data"""
        logger.info("Ingesting real estate data...")
        
        # Default real estate symbols
        if not symbols:
            symbols = ['ZILLOW_INDEX', 'CASE_SHILLER', 'RENTAL_INDEX']
        
        # Ingest from various real estate sources
        await self._ingest_zillow_data(symbols)
        await self._ingest_realtor_data(symbols)
    
    async def _ingest_zillow_data(self, symbols: List[str]):
        """Ingest data from Zillow"""
        try:
            # This is a placeholder - would need actual Zillow API integration
            for symbol in symbols:
                # Simulate Zillow home value data
                home_value = 400000 + (hash(symbol) % 200000)  # Simulated value
                
                await self._store_market_data(
                    market="real_estate",
                    symbol=symbol,
                    source="zillow",
                    price=home_value,
                    volume=None,
                    market_cap=None,
                    additional_data={
                        'property_type': 'single_family',
                        'region': 'national',
                        'value_type': 'zhvi'
                    }
                )
                
        except Exception as e:
            logger.error(f"Error ingesting Zillow data: {e}")
    
    async def _ingest_realtor_data(self, symbols: List[str]):
        """Ingest data from Realtor.com"""
        try:
            # This is a placeholder - would need actual Realtor API integration
            for symbol in symbols:
                # Simulate Realtor listing data
                listing_price = 350000 + (hash(symbol) % 150000)  # Simulated price
                
                await self._store_market_data(
                    market="real_estate",
                    symbol=symbol,
                    source="realtor",
                    price=listing_price,
                    volume=None,
                    market_cap=None,
                    additional_data={
                        'listing_type': 'for_sale',
                        'days_on_market': hash(symbol) % 90,
                        'price_per_sqft': listing_price / 2000  # Simulated
                    }
                )
                
        except Exception as e:
            logger.error(f"Error ingesting Realtor data: {e}")
    
    async def _ingest_ecommerce_data(self, symbols: Optional[List[str]] = None):
        """Ingest e-commerce data"""
        logger.info("Ingesting e-commerce data...")
        
        # Default e-commerce symbols
        if not symbols:
            symbols = ['SHOPIFY_GMV', 'AMAZON_SALES', 'EBAY_GMV']
        
        # Ingest from various e-commerce sources
        await self._ingest_shopify_data(symbols)
        await self._ingest_amazon_data(symbols)
    
    async def _ingest_shopify_data(self, symbols: List[str]):
        """Ingest data from Shopify"""
        try:
            # This is a placeholder - would need actual Shopify API integration
            for symbol in symbols:
                # Simulate Shopify GMV data
                gmv = 1000000 + (hash(symbol) % 500000)  # Simulated GMV
                
                await self._store_market_data(
                    market="ecommerce",
                    symbol=symbol,
                    source="shopify",
                    price=gmv,
                    volume=None,
                    market_cap=None,
                    additional_data={
                        'metric_type': 'gmv',
                        'period': 'monthly',
                        'currency': 'USD'
                    }
                )
                
        except Exception as e:
            logger.error(f"Error ingesting Shopify data: {e}")
    
    async def _ingest_amazon_data(self, symbols: List[str]):
        """Ingest data from Amazon"""
        try:
            # This is a placeholder - would need actual Amazon API integration
            for symbol in symbols:
                # Simulate Amazon sales data
                sales = 5000000 + (hash(symbol) % 2000000)  # Simulated sales
                
                await self._store_market_data(
                    market="ecommerce",
                    symbol=symbol,
                    source="amazon",
                    price=sales,
                    volume=None,
                    market_cap=None,
                    additional_data={
                        'metric_type': 'sales',
                        'period': 'monthly',
                        'currency': 'USD'
                    }
                )
                
        except Exception as e:
            logger.error(f"Error ingesting Amazon data: {e}")
    
    async def _store_market_data(self, market: str, symbol: str, source: str, 
                               price: Optional[float], volume: Optional[float], 
                               market_cap: Optional[float], additional_data: Dict[str, Any]):
        """Store market data in database"""
        try:
            db = next(get_db())
            
            market_data = MarketData(
                market=market,
                symbol=symbol,
                source=source,
                price=price,
                volume=volume,
                market_cap=market_cap,
                additional_data=additional_data
            )
            
            db.add(market_data)
            db.commit()
            
            logger.debug(f"Stored data: {market}/{symbol} from {source}")
            
        except Exception as e:
            logger.error(f"Error storing market data: {e}")
        finally:
            db.close()
