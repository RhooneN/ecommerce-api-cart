#!/usr/bin/env python3
"""
Test script to verify communication between cart service and product service
Run this from your cart service project directory: python test_connection.py
"""

import requests
import json
from datetime import datetime

def test_product_service_connection():
    """Test basic connectivity to product service"""
    
    print("=" * 60)
    print(f"🧪 TESTING PRODUCT SERVICE CONNECTION")
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Configuration - adjust these to match your setup
    PRODUCT_SERVICE_BASE_URL = "http://localhost:8001"
    
    # Test endpoints to try
    test_endpoints = [
        f"{PRODUCT_SERVICE_BASE_URL}/",
        f"{PRODUCT_SERVICE_BASE_URL}/api/",
        f"{PRODUCT_SERVICE_BASE_URL}/products/",
        f"{PRODUCT_SERVICE_BASE_URL}/api/products/",
        f"{PRODUCT_SERVICE_BASE_URL}/api/v1/products/",
    ]
    
    print("\n📡 Testing basic connectivity...")
    
    for i, url in enumerate(test_endpoints, 1):
        print(f"\n{i}. Testing: {url}")
        try:
            response = requests.get(
                url, 
                timeout=(2, 5),  # (connect_timeout, read_timeout)
                headers={
                    'Accept': 'application/json',
                    'User-Agent': 'CartService-Test/1.0'
                }
            )
            
            print(f"   ✅ Status: {response.status_code}")
            print(f"   📄 Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            # Try to parse JSON if possible
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                    print(f"   📊 JSON Response Keys: {list(data.keys()) if isinstance(data, dict) else 'Non-dict JSON'}")
                else:
                    content_preview = response.text[:100].replace('\n', ' ')
                    print(f"   📝 Content Preview: {content_preview}...")
            except Exception as e:
                print(f"   ⚠️  Could not parse response: {str(e)[:50]}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ CONNECTION ERROR - Service might be down or wrong URL")
        except requests.exceptions.Timeout:
            print(f"   ⏰ TIMEOUT ERROR - Service is too slow to respond")
        except Exception as e:
            print(f"   💥 UNEXPECTED ERROR: {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print("🔍 TESTING SPECIFIC PRODUCT ENDPOINTS")
    print("=" * 60)
    
    # Test specific product endpoints
    product_test_urls = [
        f"{PRODUCT_SERVICE_BASE_URL}/api/products/1/",
        f"{PRODUCT_SERVICE_BASE_URL}/products/1/",
    ]
    
    for url in product_test_urls:
        print(f"\n🏷️  Testing product endpoint: {url}")
        try:
            response = requests.get(url, timeout=(2, 5))
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ SUCCESS! Product data keys: {list(data.keys())}")
                    
                    # Check for expected fields
                    expected_fields = ['id', 'name', 'price']
                    missing_fields = [field for field in expected_fields if field not in data]
                    
                    if missing_fields:
                        print(f"   ⚠️  Missing expected fields: {missing_fields}")
                    else:
                        print(f"   ✅ All expected fields present")
                        
                    print(f"   📋 Sample data: {json.dumps(data, indent=2)[:200]}...")
                    
                except ValueError:
                    print(f"   ❌ Response is not valid JSON")
                    
            elif response.status_code == 404:
                print(f"   ⚠️  Product not found (404) - This might be expected if product ID 1 doesn't exist")
            else:
                print(f"   ❌ Unexpected status code: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 ERROR: {str(e)}")
    
    print("\n" + "=" * 60)
    print("🔧 DEBUGGING INFORMATION")
    print("=" * 60)
    
    print("\n📋 Configuration to verify in your cart service settings.py:")
    print("   PRODUCT_SERVICE_URL = 'http://localhost:8001/api'  # or whatever works above")
    print("   PRODUCT_SERVICE_CONNECT_TIMEOUT = 2")
    print("   PRODUCT_SERVICE_READ_TIMEOUT = 5")
    print("   PRODUCT_SERVICE_MAX_RETRIES = 2")
    
    print("\n🚀 Next steps:")
    print("   1. Make sure your product service is running on localhost:8001")
    print("   2. Update PRODUCT_SERVICE_URL in cart service settings.py with working URL above")
    print("   3. Check your product service URLs/routes configuration")
    print("   4. Test again with the CartItemSerializer")
    
    print("\n" + "=" * 60)
    print("🎯 Test completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_product_service_connection()
