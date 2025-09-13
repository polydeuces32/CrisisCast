"""
Scrapy settings for CrisisCast scrapers
"""

BOT_NAME = 'crisiscast'

SPIDER_MODULES = ['app.scrapers.spiders']
NEWSPIDER_MODULE = 'app.scrapers.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure delays
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = 0.5

# Configure concurrent requests
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8

# Configure user agent
USER_AGENT = 'CrisisCast/1.0 (+https://crisiscast.com/bot)'

# Configure pipelines
ITEM_PIPELINES = {
    'app.scrapers.pipelines.MarketDataPipeline': 300,
}

# Configure middlewares
DOWNLOADER_MIDDLEWARES = {
    'app.scrapers.middlewares.RotateUserAgentMiddleware': 400,
    'app.scrapers.middlewares.ProxyMiddleware': 410,
}

# Configure extensions
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# Configure logging
LOG_LEVEL = 'INFO'

# Configure cookies
COOKIES_ENABLED = True

# Configure caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600

# Configure retries
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# Configure download timeout
DOWNLOAD_TIMEOUT = 30

# Configure redirects
REDIRECT_MAX_TIMES = 5

# Configure AJAX
AJAXCRAWL_ENABLED = True

# Configure memory usage
MEMDEBUG_ENABLED = True
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 2048
MEMUSAGE_WARNING_MB = 1024

# Custom settings
CUSTOM_SETTINGS = {
    'FEEDS': {
        'data/raw/%(name)s_%(time)s.json': {
            'format': 'json',
            'encoding': 'utf8',
            'store_empty': False,
            'indent': 2,
        },
    },
    'FEED_EXPORT_ENCODING': 'utf-8',
    'FEED_STORE_EMPTY': False,
    'FEED_EXPORT_INDENT': 2,
}
