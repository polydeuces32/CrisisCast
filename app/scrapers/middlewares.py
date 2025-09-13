"""
Scrapy middlewares for CrisisCast
"""

import random
import logging
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message

logger = logging.getLogger(__name__)

class RotateUserAgentMiddleware(UserAgentMiddleware):
    """Middleware for rotating user agents"""
    
    def __init__(self, user_agent=''):
        self.user_agent = user_agent
        self.user_agent_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
        ]
    
    def process_request(self, request, spider):
        """Set a random user agent for each request"""
        ua = random.choice(self.user_agent_list)
        request.headers['User-Agent'] = ua
        return None

class ProxyMiddleware:
    """Middleware for rotating proxies"""
    
    def __init__(self):
        self.proxy_list = [
            # Add proxy servers here
            # 'http://proxy1:port',
            # 'http://proxy2:port',
        ]
        self.current_proxy = 0
    
    def process_request(self, request, spider):
        """Set proxy for request"""
        if self.proxy_list:
            proxy = self.proxy_list[self.current_proxy % len(self.proxy_list)]
            request.meta['proxy'] = proxy
            self.current_proxy += 1
        return None

class CustomRetryMiddleware(RetryMiddleware):
    """Custom retry middleware with exponential backoff"""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.retry_times = settings.getint('RETRY_TIMES')
        self.retry_http_codes = set(int(x) for x in settings.getlist('RETRY_HTTP_CODES'))
        self.priority_adjust = settings.getint('RETRY_PRIORITY_ADJUST')
    
    def retry(self, request, reason, spider):
        """Retry request with exponential backoff"""
        retries = request.meta.get('retry_times', 0) + 1
        
        if retries <= self.retry_times:
            # Calculate exponential backoff delay
            delay = 2 ** retries + random.uniform(0, 1)
            
            logger.info(f"Retrying {request} (attempt {retries}) after {delay:.2f} seconds")
            
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.meta['retry_delay'] = delay
            retryreq.dont_filter = True
            retryreq.priority = request.priority + self.priority_adjust
            
            return retryreq
        else:
            logger.error(f"Gave up retrying {request} (failed {retries} times): {reason}")
            return None

class RateLimitMiddleware:
    """Middleware for rate limiting requests"""
    
    def __init__(self, delay=1.0):
        self.delay = delay
        self.last_request_time = 0
    
    def process_request(self, request, spider):
        """Add delay between requests"""
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.delay:
            sleep_time = self.delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
        return None

class HeadersMiddleware:
    """Middleware for adding custom headers"""
    
    def process_request(self, request, spider):
        """Add custom headers to request"""
        request.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        request.headers['Accept-Language'] = 'en-US,en;q=0.5'
        request.headers['Accept-Encoding'] = 'gzip, deflate'
        request.headers['Connection'] = 'keep-alive'
        request.headers['Upgrade-Insecure-Requests'] = '1'
        return None

class ErrorHandlingMiddleware:
    """Middleware for handling errors"""
    
    def process_response(self, request, response, spider):
        """Handle response errors"""
        if response.status >= 400:
            logger.warning(f"HTTP {response.status} error for {request.url}")
            
            # Log additional error details
            if response.status == 429:  # Too Many Requests
                logger.warning("Rate limited - consider increasing delays")
            elif response.status == 403:  # Forbidden
                logger.warning("Access forbidden - check user agent and headers")
            elif response.status == 404:  # Not Found
                logger.warning("Page not found - check URL")
        
        return response
    
    def process_exception(self, request, exception, spider):
        """Handle request exceptions"""
        logger.error(f"Exception processing {request.url}: {exception}")
        return None
