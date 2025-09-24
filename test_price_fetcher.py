#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for optimized price fetcher
"""

import asyncio
import time
from price_fetcher import (
    fetch_usdt_price_optimized, 
    get_price_info, 
    get_api_health,
    get_best_api,
    force_price_update
)

async def test_price_fetcher():
    """Test the optimized price fetcher."""
    print("🚀 Testing Optimized Price Fetcher")
    print("=" * 50)
    
    # Test 1: Get current price info
    print("\n1. Current Price Info:")
    price_info = get_price_info()
    for key, value in price_info.items():
        print(f"   {key}: {value}")
    
    # Test 2: API Health Status
    print("\n2. API Health Status:")
    health = get_api_health()
    for api_name, status in health.items():
        print(f"   {api_name}: {status['status']} - {'✅' if status['is_healthy'] else '❌'}")
    
    # Test 3: Best API
    print(f"\n3. Best Performing API: {get_best_api()}")
    
    # Test 4: Force Update
    print("\n4. Testing Force Update:")
    success = force_price_update()
    print(f"   Force update {'✅ successful' if success else '❌ failed'}")
    
    # Test 5: Direct API Test
    print("\n5. Testing Direct API Calls:")
    try:
        result = await fetch_usdt_price_optimized()
        print(f"   Result: {result.source} - {result.usdt_price:,} Toman - {result.status.value}")
    except Exception as e:
        print(f"   Async test failed: {e}")
    
    # Test 6: Sync Fallback Test
    print("\n6. Testing Sync Fallback:")
    from price_fetcher import fetch_price_sync_fallback
    sync_result = fetch_price_sync_fallback()
    print(f"   Sync Result: {sync_result.source} - {sync_result.usdt_price:,} Toman - {sync_result.status.value}")
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(test_price_fetcher())
