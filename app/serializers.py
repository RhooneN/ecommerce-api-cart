from rest_framework import serializers
from .models import Panier, CartItem
import requests
from django.conf import settings
from decimal import Decimal
import logging
from datetime import datetime, timedelta
from django.core.cache import cache
from django.core.exceptions import ValidationError

# Configure logging
logger = logging.getLogger(__name__)

class CartItemSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    product_details = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ['id', 'product_id', 'quantity', 'name', 'price', 'subtotal', 'product_details']
    
    def get_name(self, obj):
        """Fetch product name from product service"""
        product_data = self._get_product_data(obj.product_id)
        return product_data.get('name', f'Product {obj.product_id}')
    
    def get_price(self, obj):
        """Fetch product price from product service"""
        product_data = self._get_product_data(obj.product_id)
        price_value = float(product_data.get('price', '0'))
        try:
            return Decimal(str(price_value))
        except (ValueError, TypeError, ValidationError):
            logger.warning(f"Invalid price format for product {obj.product_id}: {price_value}")
            return Decimal('0')
    
    def get_subtotal(self, obj):
        """Calculate subtotal dynamically"""
        price = self.get_price(obj)
        return price * obj.quantity
    
    def get_product_details(self, obj):
        """Return full product details"""
        return self._get_product_data(obj.product_id)
    
    def _get_product_data(self, product_id):
        """
        Helper method to fetch product data with robust caching, error handling, and fallback.
        
        Implements multiple levels of caching:
        1. Request-level cache (for single request efficiency)
        2. Django cache (for cross-request persistence)
        3. Fallback cache (for service failures)
        """
        
        # Level 1: Request-level cache to avoid multiple API calls within the same request
        request = self.context.get('request')
        if request and not hasattr(request, '_product_cache'):
            request._product_cache = {}
        
        request_cache = getattr(request, '_product_cache', {}) if request else {}
        
        if product_id in request_cache:
            logger.debug(f"Product {product_id} found in request cache")
            return request_cache[product_id]
        
        # Level 2: Django cache for cross-request persistence
        cache_key = f"product_data_{product_id}"
        fallback_cache_key = f"product_fallback_{product_id}"
        
        # Try to get from main cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug(f"Product {product_id} found in Django cache")
            if request:
                request_cache[product_id] = cached_data
            return cached_data
        
        # Level 3: Attempt to fetch from product service
        product_data = self._fetch_from_service(product_id)
        
        if product_data.get('success', False):
            # Success: cache the data with normal TTL
            cache.set(cache_key, product_data, timeout=getattr(settings, 'PRODUCT_CACHE_TTL', 300))  # 5 minutes default
            
            # Also update fallback cache with longer TTL
            cache.set(fallback_cache_key, product_data, timeout=getattr(settings, 'PRODUCT_FALLBACK_CACHE_TTL', 3600))  # 1 hour default
            
            if request:
                request_cache[product_id] = product_data
            
            logger.info(f"Product {product_id} fetched successfully from service")
            return product_data
        
        # ~ if not product_data.get("success", False) or product_data.get("price", 0.0) <= 0:
             # ~ return {"success": False, "id": product_id, "price": Decimal("0.00")}
            # ~ return {"message": f"Product {product_id} not available"}
            
        # Level 4: Fallback to stale cache if service fails
        fallback_data = cache.get(fallback_cache_key)
        if fallback_data:
            logger.warning(f"Using fallback cache for product {product_id} due to service failure")
            
            # Cache the fallback data for a short time to avoid repeated service calls
            cache.set(cache_key, fallback_data, timeout=60)  # 1 minute for failed service calls
            
            if request:
                request_cache[product_id] = fallback_data
            return fallback_data
        
        # Level 5: Final fallback - return minimal data structure
        logger.error(f"No product data available for product {product_id}, using minimal fallback")
        minimal_data = self._get_minimal_fallback_data(product_id)
        
        if request:
            request_cache[product_id] = minimal_data
        
        return minimal_data
    
    def _fetch_from_service(self, product_id):
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
                        # ~ return {"success": False, "id": product_id, "price": Decimal("0.00")}
                        return {'success': False, 'error': 'Product not found', 'status_code': 404}
                    
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
    
    def _validate_product_data(self, data):
        """
        Validate the structure of product data returned from the service.
        
        Args:
            data (dict): Product data to validate
            
        Returns:
            bool: True if data structure is valid
        """
        if not isinstance(data, dict):
            return False
        
        # Check for required fields
        required_fields = ['description', 'name']
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field '{field}' in product data")
                return False
        
        # Validate price if present
        if 'price' in data:
            try:
                Decimal(str(data['price']))
            except (ValueError, TypeError, ValidationError):
                logger.error(f"Invalid price format in product data: {data.get('price')}")
                return False
        
        return True
    
    def _get_minimal_fallback_data(self, product_id):
        """
        Generate minimal fallback data when all other methods fail.
        
        Args:
            product_id: The product ID
            
        Returns:
            dict: Minimal product data structure
        """
        return {
            'id': product_id,
            'name': f'Product {product_id}',
            'price': 0.00,
            'description': 'Product details temporarily unavailable',
            'available': False,
            'success': False,
            'error': 'Product data unavailable',
            'is_fallback': True,
            'fetched_at': datetime.now().isoformat()
        }
    
    def to_representation(self, instance):
        """
        Override to add error reporting in the serialized output.
        """
        data = super().to_representation(instance)
        
        # Add service status information if in debug mode
        if getattr(settings, 'DEBUG', False):
            product_data = self._get_product_data(instance.product_id)
            data['_service_info'] = {
                'service_success': product_data.get('success', False),
                'is_fallback': product_data.get('is_fallback', False),
                'error': product_data.get('error'),
                'fetched_at': product_data.get('fetched_at')
            }
        
        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Panier
        fields = ['id', 'user_id', 'items', 'total', 'items_count']

    def get_total(self, obj):
        """Calculate total using serializer methods for accurate pricing"""
        total = Decimal('0')
        for item in obj.items.all():
            # Use the serializer to get current prices
            item_serializer = CartItemSerializer(item, context=self.context)
            total += item_serializer.get_subtotal(item)
        return total

    def get_items_count(self, obj):
        return obj.items.count()

class ICartItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=1)

    class Meta:
        model = CartItem
        fields = ["product_id", "quantity", "price", "name", "subtotal"]
        extra_kwargs = {
            "product_price": {"required": False}
        }

class CartItemUpdateSerializer(serializers.ModelSerializer):
    # ~ details = ProductSerializer(read_only=True)
    class Meta:
        model = CartItem
        fields = ['quantity']
        


class CartItemDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        #fields = ['product', 'quantity']
        fields = '__all__'


