# utils/product_client.py
import requests
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor
import functools
from decimal import Decimal
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.core.exceptions import ValidationError
# Configure logging
logger = logging.getLogger(__name__)

class ProductClient:
    def __init__(self):
        self.timeout = settings.PRODUCT_SERVICE_READ_TIMEOUT
        self.base_url = settings.PRODUCT_SERVICE_URL

    def get_product(self, product_id):
        try:
            response = requests.get(
                f"{self.base_url}/products/{product_id}/",
                timeout=self.timeout,
                headers={'Authorization': f'Bearer {settings.PRODUCT_SERVICE_TOKEN}'}
            )
            return response.json() if response.status_code == 200 else {}
        except requests.RequestException:
            return {}

    def get_products_batch(self, product_ids):
        """Fetch multiple products in parallel"""
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(self.get_product, product_ids))
        return dict(zip(product_ids, results))

# Singleton instance
product_client = ProductClient()

import jwt, datetime
from django.conf import settings

def generate_cart_token(cart_id, user_id=None):
    payload = {
        "cart_id": cart_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        "scope": "cart"
    }
    if user_id:  # only add if known
        payload["user_id"] = user_id
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def verify_cart_token(token):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ValueError("Expired cart token")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid cart token")
        
def fetch_from_service(product_id):
        """
        Fetch product data from the external service with comprehensive error handling.
        
        Returns:
            dict: Product data with 'success' key indicating fetch status
        """
        try:
            # Validate product_id
            if not product_id:
                logger.error("Empty product_id provided")
                return {'success': False, 'error': 'Invalid product ID'}
            
            # Build request URL
            base_url = getattr(settings, 'PRODUCT_SERVICE_URL', '').rstrip('/')
            if not base_url:
                logger.error("PRODUCT_SERVICE_URL not configured")
                return {'success': False, 'error': 'Product service URL not configured'}
            
            url = f"{base_url}/products/{product_id}/"
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'CartService/1.0'
            }
            
            # Add authentication if configured
            auth_token = getattr(settings, 'PRODUCT_SERVICE_TOKEN', '')
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
            
            # Make the request with timeouts and retries
            timeout_config = (
                getattr(settings, 'PRODUCT_SERVICE_CONNECT_TIMEOUT', 2),  # Connect timeout
                getattr(settings, 'PRODUCT_SERVICE_READ_TIMEOUT', 5)      # Read timeout
            )
            
            max_retries = getattr(settings, 'PRODUCT_SERVICE_MAX_RETRIES', 2)
            
            for attempt in range(max_retries + 1):
                try:
                    logger.debug(f"Fetching product {product_id}, attempt {attempt + 1}/{max_retries + 1}")
                    
                    response = requests.get(
                        url,
                        headers=headers,
                        timeout=timeout_config,
                        allow_redirects=True
                    )
                    
                    # Handle different response codes
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            # Validate response structure
                            if self._validate_product_data(data):
                                data['success'] = True
                                data['fetched_at'] = datetime.now().isoformat()
                                return data
                            else:
                                logger.error(f"Invalid product data structure for product {product_id}")
                                return {'success': False, 'error': 'Invalid product data structure'}
                        
                        except ValueError as e:
                            logger.error(f"Invalid JSON response for product {product_id}: {e}")
                            return {'success': False, 'error': 'Invalid JSON response'}
                    
                    elif response.status_code == 404:
                        print("status", response.status_code)
                        logger.warning(f"Product {product_id} not found (404)")
                        return {"success": False, "id": product_id, "price": Decimal("0.00")}
                        # ~ return {'success': False, 'error': 'Product not found', 'status_code': 404}
                    
                    elif response.status_code in [429, 503]:  # Rate limited or service unavailable
                        if attempt < max_retries:
                            wait_time = (2 ** attempt)  # Exponential backoff
                            logger.warning(f"Rate limited/Service unavailable for product {product_id}, retrying in {wait_time}s")
                            import time
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error(f"Service unavailable for product {product_id} after {max_retries + 1} attempts")
                            return {'success': False, 'error': 'Service unavailable', 'status_code': response.status_code}
                    
                    else:
                        logger.error(f"Unexpected response code {response.status_code} for product {product_id}")
                        return {'success': False, 'error': f'HTTP {response.status_code}', 'status_code': response.status_code}
                
                except requests.exceptions.ConnectTimeout:
                    logger.warning(f"Connection timeout for product {product_id}, attempt {attempt + 1}")
                    if attempt >= max_retries:
                        return {'success': False, 'error': 'Connection timeout'}
                
                except requests.exceptions.ReadTimeout:
                    logger.warning(f"Read timeout for product {product_id}, attempt {attempt + 1}")
                    if attempt >= max_retries:
                        return {'success': False, 'error': 'Read timeout'}
                
                except requests.exceptions.ConnectionError as e:
                    logger.warning(f"Connection error for product {product_id}: {e}")
                    if attempt >= max_retries:
                        return {'success': False, 'error': 'Connection error'}
                
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error for product {product_id}: {e}")
                    if attempt >= max_retries:
                        return {'success': False, 'error': f'Request error: {str(e)}'}
        
        except Exception as e:
            logger.error(f"Unexpected error fetching product {product_id}: {e}")
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}
    

