# -*- coding: utf-8 -*-
import asyncio
import json
import os
import time
from threading import Thread
from typing import Optional, Dict, Any
import aiohttp
import logging
import requests

# ------------------------------
# Configuration
# ------------------------------
CACHE_FILE = "price_cache.json"
CACHE_DURATION = 30  # seconds
REQUEST_TIMEOUT = 10

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Global price cache
# ------------------------------
price_cache: Dict[str, Any] = {
    "usdt_price": None,
    "btc_price": None,
    "updated_at": None,
    "source": "unknown",
    "last_error": None
}

# ------------------------------
# Price fetching functions
# ------------------------------
def fetch_usdt_price() -> tuple[Optional[int], str]:
    """دریافت قیمت تتر از چندین منبع"""
    sources = [
        {
            "name": "wallex",
            "url": "https://api.wallex.ir/v1/markets",
            "parser": lambda data: int(float(data.get("result", {}).get("symbols", {}).get("USDTTMN", {}).get("stats", {}).get("lastPrice", 0)))
        },
        {
            "name": "nobitex", 
            "url": "https://api.nobitex.ir/market/stats",
            "method": "POST",
            "data": {"srcCurrency": "usdt", "dstCurrency": "rls"},
            "parser": lambda data: int(float(data.get("stats", {}).get("usdt-rls", {}).get("latest", 0)) / 10)
        },
        {
            "name": "bitpin",
            "url": "https://api.bitpin.ir/v1/mkt/currencies/",
            "parser": lambda data: int(float(next((item.get("price", 0) for item in data.get("results", []) if item.get("code") == "USDT"), 0)))
        }
    ]
    
    for source in sources:
        try:
            if source.get("method") == "POST":
                response = requests.post(source["url"], json=source.get("data", {}), timeout=REQUEST_TIMEOUT)
            else:
                response = requests.get(source["url"], timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                price = source["parser"](data)
                if price > 0:
                    return price, source["name"]
        except Exception as e:
            logger.warning(f"خطا در دریافت قیمت از {source['name']}: {e}")
            continue
    
    return None, "error"

def fetch_btc_price() -> tuple[Optional[float], str]:
    """دریافت قیمت بیت‌کوین"""
    sources = [
        {
            "name": "coindesk",
            "url": "https://api.coindesk.com/v1/bpi/currentprice/USD.json",
            "parser": lambda data: float(data.get("bpi", {}).get("USD", {}).get("rate_float", 0))
        },
        {
            "name": "binance",
            "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
            "parser": lambda data: float(data.get("price", 0))
        }
    ]
    
    for source in sources:
        try:
            response = requests.get(source["url"], timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                price = source["parser"](data)
                if price > 0:
                    return price, source["name"]
        except Exception as e:
            logger.warning(f"خطا در دریافت قیمت BTC از {source['name']}: {e}")
            continue
    
    return None, "error"

# ------------------------------
# Cache management
# ------------------------------
def load_cache() -> None:
    """بارگذاری کش از فایل"""
    global price_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                price_cache.update({
                    "usdt_price": cached_data.get("usdt_price"),
                    "btc_price": cached_data.get("btc_price"),
                    "updated_at": cached_data.get("updated_at"),
                    "source": cached_data.get("source", "unknown"),
                    "last_error": cached_data.get("last_error")
                })
                logger.info("کش قیمت‌ها بارگذاری شد")
        except Exception as e:
            logger.error(f"خطا در بارگذاری کش: {e}")

def save_cache() -> None:
    """ذخیره کش در فایل"""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(price_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا در ذخیره کش: {e}")

def is_cache_valid() -> bool:
    """بررسی اعتبار کش"""
    if not price_cache.get("updated_at"):
        return False
    return (time.time() - price_cache["updated_at"]) < CACHE_DURATION

# ------------------------------
# Main update function
# ------------------------------
def update_prices():
    """به‌روزرسانی قیمت‌ها"""
    global price_cache
    
    while True:
        try:
            # Skip if cache is still valid
            if is_cache_valid():
                time.sleep(5)
                continue
            
            # Fetch USDT price
            usdt_price, usdt_source = fetch_usdt_price()
            if usdt_price:
                price_cache["usdt_price"] = usdt_price
                price_cache["source"] = usdt_source
                logger.info(f"✅ قیمت تتر آپدیت شد: {usdt_price:,} تومان از {usdt_source}")
            
            # Fetch BTC price
            btc_price, btc_source = fetch_btc_price()
            if btc_price:
                price_cache["btc_price"] = btc_price
                logger.info(f"✅ قیمت بیت‌کوین آپدیت شد: ${btc_price:,.2f} از {btc_source}")
            
            price_cache["updated_at"] = int(time.time())
            price_cache["last_error"] = None
            save_cache()
            
        except Exception as e:
            error_msg = f"❌ خطا در به‌روزرسانی قیمت‌ها: {e}"
            price_cache["last_error"] = error_msg
            logger.error(error_msg)
        
        time.sleep(CACHE_DURATION)

# ------------------------------
# Public API functions
# ------------------------------
def get_current_usdt_price() -> Optional[int]:
    """دریافت قیمت فعلی تتر"""
    return price_cache.get("usdt_price")

def get_current_btc_price() -> Optional[float]:
    """دریافت قیمت فعلی بیت‌کوین"""
    return price_cache.get("btc_price")

def get_price_info() -> Dict[str, Any]:
    """دریافت اطلاعات کامل قیمت‌ها"""
    return {
        "usdt_price": price_cache.get("usdt_price"),
        "btc_price": price_cache.get("btc_price"),
        "updated_at": price_cache.get("updated_at"),
        "source": price_cache.get("source", "unknown"),
        "last_error": price_cache.get("last_error"),
        "cache_valid": is_cache_valid()
    }

def force_price_update() -> bool:
    """اجبار به‌روزرسانی فوری قیمت‌ها"""
    try:
        # Fetch USDT price
        usdt_price, usdt_source = fetch_usdt_price()
        if usdt_price:
            price_cache["usdt_price"] = usdt_price
            price_cache["source"] = usdt_source
        
        # Fetch BTC price
        btc_price, btc_source = fetch_btc_price()
        if btc_price:
            price_cache["btc_price"] = btc_price
            
        price_cache["updated_at"] = int(time.time())
        price_cache["last_error"] = None
        save_cache()
        
        return True
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی فوری: {e}")
        return False

def start_price_fetcher():
    """شروع فرآیند به‌روزرسانی قیمت‌ها"""
    load_cache()  # بارگذاری آخرین کش
    
    def run_updater():
        try:
            update_prices()
        except KeyboardInterrupt:
            logger.info("فرآیند به‌روزرسانی قیمت‌ها متوقف شد")
        except Exception as e:
            logger.error(f"خطا در فرآیند به‌روزرسانی: {e}")
    
    # اجرای به‌روزرسانی در thread جداگانه
    Thread(target=run_updater, daemon=True).start()
    logger.info("🚀 فرآیند به‌روزرسانی قیمت‌ها شروع شد")