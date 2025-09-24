import asyncio
import json
import os
import time
from threading import Thread
from typing import Optional, Dict, Any
import aiohttp
import logging

# ------------------------------
# Configuration and logging
# ------------------------------
CACHE_FILE = "price_cache.json"
CACHE_DURATION = 30  # seconds
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# متغیرهای کش
# ------------------------------
price_cache: Dict[str, Any] = {
    "usdt_price": None, 
    "updated_at": None,
    "last_error": None
}

# ------------------------------
# تابع Async برای گرفتن قیمت از والکس
# ------------------------------
async def fetch_usdt_price_from_wallex() -> Optional[int]:
    """Fetch USDT price from Wallex with retry logic and better error handling."""
    for attempt in range(MAX_RETRIES):
        try:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # Get USDT price from markets API
                markets_url = "https://api.wallex.ir/v1/markets"
                async with session.get(markets_url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        markets = data.get("result", {}).get("symbols", {})
                        
                        # Get USDT price
                        usdt_market = markets.get("USDTTMN")
                        if usdt_market:
                            last_price = usdt_market.get("stats", {}).get("lastPrice")
                            if last_price and last_price != "-":
                                price = int(float(last_price))
                                logger.info(f"Successfully fetched USDT price: {price:,} Toman")
                                return price
                    else:
                        logger.warning(f"Wallex API returned status {resp.status}")
                        
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching USDT price (attempt {attempt + 1}/{MAX_RETRIES})")
        except Exception as e:
            logger.error(f"Error fetching USDT price from Wallex (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
        
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    return None

# ------------------------------
# ذخیره/بازیابی کش در فایل
# ------------------------------
def load_cache() -> None:
    """Load price cache from file with error handling."""
    global price_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                # Ensure all keys exist with proper types
                price_cache = {
                    "usdt_price": cached_data.get("usdt_price"),
                    "updated_at": cached_data.get("updated_at"),
                    "last_error": cached_data.get("last_error")
                }
                logger.info("Price cache loaded successfully")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading cache: {e}")
            price_cache = {
                "usdt_price": None, 
                "updated_at": None,
                "last_error": None
            }

def save_cache() -> None:
    """Save price cache to file with error handling."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(price_cache, f, ensure_ascii=False, indent=2)
        logger.debug("Price cache saved successfully")
    except IOError as e:
        logger.error(f"Error saving cache: {e}")

def is_cache_valid() -> bool:
    """Check if cache is still valid based on duration."""
    if not price_cache.get("updated_at"):
        return False
    return (time.time() - price_cache["updated_at"]) < CACHE_DURATION

# ------------------------------
# به‌روزرسانی قیمت هر ۳۰ ثانیه
# ------------------------------
async def update_price() -> None:
    """Main price update loop with improved error handling and logging."""
    global price_cache
    consecutive_errors = 0
    max_consecutive_errors = 5
    
    while True:
        try:
            # Skip update if cache is still valid
            if is_cache_valid():
                logger.debug("Cache is still valid, skipping update")
                await asyncio.sleep(5)
                continue
                
            usdt_price = await fetch_usdt_price_from_wallex()
            if usdt_price:
                price_cache["usdt_price"] = usdt_price
                price_cache["updated_at"] = int(time.time())
                price_cache["last_error"] = None
                save_cache()
                consecutive_errors = 0
                logger.info(f"✅ قیمت USDT آپدیت شد: {usdt_price:,} تومان")
            else:
                consecutive_errors += 1
                error_msg = "❌ خطا در دریافت قیمت USDT از والکس"
                price_cache["last_error"] = error_msg
                logger.warning(error_msg)
                
                # If too many consecutive errors, increase sleep time
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({consecutive_errors}), increasing sleep time")
                    await asyncio.sleep(60)  # Sleep for 1 minute
                    consecutive_errors = 0
                    continue
                    
        except Exception as e:
            consecutive_errors += 1
            error_msg = f"❌ خطا در به‌روزرسانی قیمت: {e}"
            price_cache["last_error"] = error_msg
            logger.error(error_msg)
        
        await asyncio.sleep(CACHE_DURATION)

def start_scheduler():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(update_price())

# ------------------------------
# تابع برای دریافت قیمت فعلی
# ------------------------------
def get_current_usdt_price() -> Optional[int]:
    """Get current USDT price from cache."""
    return price_cache.get("usdt_price")

def get_price_info() -> Dict[str, Any]:
    """Get comprehensive price information including error status."""
    usdt_price = price_cache.get("usdt_price")
    return {
        "usdt_price": usdt_price,
        "updated_at": price_cache.get("updated_at"),
        "usdt_formatted": f"{usdt_price:,} تومان" if usdt_price else "نامشخص",
        "last_error": price_cache.get("last_error"),
        "cache_valid": is_cache_valid()
    }

def get_current_usd_rate() -> Optional[float]:
    """Get current USD to Toman rate (USDT price * 10)."""
    usdt_price = get_current_usdt_price()
    if usdt_price:
        return usdt_price * 10
    return None

# ------------------------------
# شروع scheduler
# ------------------------------
def start_price_fetcher():
    load_cache()  # بارگذاری آخرین کش
    # اجرای Scheduler در یک Thread جدا
    Thread(target=start_scheduler, daemon=True).start()
    print("🚀 Price fetcher started")
