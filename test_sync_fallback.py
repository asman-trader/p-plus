#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for sync fallback price fetcher
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from price_fetcher import fetch_price_sync_fallback, get_price_info, force_price_update

def test_sync_fallback():
    """Test the sync fallback price fetcher."""
    print("🚀 Testing Sync Fallback Price Fetcher")
    print("=" * 50)
    
    # Test 1: Current Price Info
    print("\n1. Current Price Info:")
    price_info = get_price_info()
    for key, value in price_info.items():
        print(f"   {key}: {value}")
    
    # Test 2: Sync Fallback Test
    print("\n2. Testing Sync Fallback:")
    result = fetch_price_sync_fallback()
    print(f"   Result: {result.source} - {result.usdt_price:,} Toman - {result.status.value}")
    if result.error:
        print(f"   Error: {result.error}")
    
    # Test 3: Force Update (with fallback)
    print("\n3. Testing Force Update with Fallback:")
    success = force_price_update()
    print(f"   Force update {'✅ successful' if success else '❌ failed'}")
    
    # Test 4: Updated Price Info
    print("\n4. Updated Price Info:")
    price_info = get_price_info()
    for key, value in price_info.items():
        print(f"   {key}: {value}")
    
    print("\n" + "=" * 50)
    print("✅ Sync Fallback Test completed!")

if __name__ == "__main__":
    test_sync_fallback()
