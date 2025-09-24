import asyncio
import json
import os
import time
from threading import Thread
from typing import Optional, Dict, Any, List
import aiohttp
import logging
from dataclasses import dataclass
from enum import Enum
import requests

# ------------------------------
# Configuration and logging
# ------------------------------
CACHE_FILE = "price_cache.json"
CACHE_DURATION = 30  # seconds
MAX_RETRIES = 3
REQUEST_TIMEOUT = 10
CONNECTION_POOL_SIZE = 10
MAX_CONNECTIONS = 100

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"

@dataclass
class PriceData:
    usdt_price: Optional[int]
    updated_at: Optional[int]
    source: str
    status: APIStatus
    error: Optional[str] = None

@dataclass
class APIConfig:
    url: str
    name: str
    timeout: int
    retry_count: int
    priority: int

# ------------------------------
# API Configurations
# ------------------------------
API_CONFIGS = [
    APIConfig(
        url="https://api.wallex.ir/v1/markets",
        name="wallex",
        timeout=8,
        retry_count=3,
        priority=1
    ),
    APIConfig(
        url="https://api.nobitex.ir/market/stats",
        name="nobitex",
        timeout=8,
        retry_count=2,
        priority=2
    ),
    APIConfig(
        url="https://api.bitpin.ir/v1/mkt/currencies/",
        name="bitpin",
        timeout=8,
        retry_count=2,
        priority=3
    )
]

# ------------------------------
# متغیرهای کش و connection pool
# ------------------------------
price_cache: Dict[str, Any] = {
    "usdt_price": None, 
    "updated_at": None,
    "last_error": None,
    "source": "unknown",
    "api_stats": {}
}

# Global connection pool
_connector: Optional[aiohttp.TCPConnector] = None
_session: Optional[aiohttp.ClientSession] = None

# ------------------------------
# Connection Pool Management
# ------------------------------
async def get_session() -> aiohttp.ClientSession:
    """Get or create a shared session with connection pooling."""
    global _session, _connector
    
    if _session is None or _session.closed:
        _connector = aiohttp.TCPConnector(
            limit=MAX_CONNECTIONS,
            limit_per_host=CONNECTION_POOL_SIZE,
            ttl_dns_cache=300,  # 5 minutes DNS cache
            use_dns_cache=True,
            enable_cleanup_closed=True,
            force_close=True  # Force close connections
            # Removed AsyncResolver to avoid aiodns dependency
            # Removed keepalive_timeout due to force_close conflict
        )
        
        timeout = aiohttp.ClientTimeout(
            total=REQUEST_TIMEOUT,
            connect=5,
            sock_read=5
        )
        
        _session = aiohttp.ClientSession(
            connector=_connector,
            timeout=timeout,
            headers={
                'User-Agent': 'P+ Portfolio Manager/1.0',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        )
    
    return _session

async def close_session():
    """Close the global session."""
    global _session, _connector
    if _session and not _session.closed:
        await _session.close()
    if _connector:
        await _connector.close()
    _session = None
    _connector = None

# ------------------------------
# API Price Fetchers
# ------------------------------
async def fetch_from_wallex(session: aiohttp.ClientSession) -> PriceData:
    """Fetch USDT price from Wallex API."""
    try:
        async with session.get(API_CONFIGS[0].url) as resp:
            if resp.status == 200:
                data = await resp.json()
                markets = data.get("result", {}).get("symbols", {})
                usdt_market = markets.get("USDTTMN")
                
                if usdt_market:
                    last_price = usdt_market.get("stats", {}).get("lastPrice")
                    if last_price and last_price != "-":
                        price = int(float(last_price))
                        return PriceData(
                            usdt_price=price,
                            updated_at=int(time.time()),
                            source="wallex",
                            status=APIStatus.SUCCESS
                        )
            
            return PriceData(
                usdt_price=None,
                updated_at=None,
                source="wallex",
                status=APIStatus.FAILED,
                error=f"HTTP {resp.status}"
            )
    except asyncio.TimeoutError:
        return PriceData(
            usdt_price=None,
            updated_at=None,
            source="wallex",
            status=APIStatus.TIMEOUT,
            error="Request timeout"
        )
    except Exception as e:
        return PriceData(
            usdt_price=None,
            updated_at=None,
            source="wallex",
            status=APIStatus.FAILED,
            error=str(e)
        )

async def fetch_from_nobitex(session: aiohttp.ClientSession) -> PriceData:
    """Fetch USDT price from Nobitex API."""
    try:
        payload = {"srcCurrency": "usdt", "dstCurrency": "rls"}
        async with session.post(API_CONFIGS[1].url, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                stats = data.get("stats", {}).get("usdt-rls", {})
                last_price = stats.get("latest")
                
                if last_price:
                    # Convert from RLS to Toman (divide by 10)
                    price = int(float(last_price) / 10)
                    return PriceData(
                        usdt_price=price,
                        updated_at=int(time.time()),
                        source="nobitex",
                        status=APIStatus.SUCCESS
                    )
            
            return PriceData(
                usdt_price=None,
                updated_at=None,
                source="nobitex",
                status=APIStatus.FAILED,
                error=f"HTTP {resp.status}"
            )
    except asyncio.TimeoutError:
        return PriceData(
            usdt_price=None,
            updated_at=None,
            source="nobitex",
            status=APIStatus.TIMEOUT,
            error="Request timeout"
        )
    except Exception as e:
        return PriceData(
            usdt_price=None,
            updated_at=None,
            source="nobitex",
            status=APIStatus.FAILED,
            error=str(e)
        )

async def fetch_from_bitpin(session: aiohttp.ClientSession) -> PriceData:
    """Fetch USDT price from Bitpin API."""
    try:
        async with session.get(API_CONFIGS[2].url) as resp:
            if resp.status == 200:
                data = await resp.json()
                currencies = data.get("results", [])
                
                for currency in currencies:
                    if currency.get("code") == "USDT":
                        price = currency.get("price")
                        if price:
                            return PriceData(
                                usdt_price=int(float(price)),
                                updated_at=int(time.time()),
                                source="bitpin",
                                status=APIStatus.SUCCESS
                            )
            
            return PriceData(
                usdt_price=None,
                updated_at=None,
                source="bitpin",
                status=APIStatus.FAILED,
                error=f"HTTP {resp.status}"
            )
    except asyncio.TimeoutError:
        return PriceData(
            usdt_price=None,
            updated_at=None,
            source="bitpin",
            status=APIStatus.TIMEOUT,
            error="Request timeout"
        )
    except Exception as e:
        return PriceData(
            usdt_price=None,
            updated_at=None,
            source="bitpin",
            status=APIStatus.FAILED,
            error=str(e)
        )

# ------------------------------
# Main Price Fetching Function
# ------------------------------
async def fetch_usdt_price_optimized() -> PriceData:
    """Fetch USDT price from multiple APIs with fallback and optimization."""
    session = await get_session()
    
    # Try APIs in priority order
    api_functions = [
        fetch_from_wallex,
        fetch_from_nobitex,
        fetch_from_bitpin
    ]
    
    # Run all APIs concurrently
    tasks = [func(session) for func in api_functions]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successful_results = []
    api_stats = {}
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            api_stats[API_CONFIGS[i].name] = {
                "status": "error",
                "error": str(result),
                "timestamp": int(time.time())
            }
            continue
            
        api_stats[result.source] = {
            "status": result.status.value,
            "error": result.error,
            "timestamp": int(time.time())
        }
        
        if result.status == APIStatus.SUCCESS and result.usdt_price:
            successful_results.append(result)
    
    # Update API stats in cache
    price_cache["api_stats"] = api_stats
    
    # Return the first successful result
    if successful_results:
        best_result = successful_results[0]
        logger.info(f"Successfully fetched USDT price from {best_result.source}: {best_result.usdt_price:,} Toman")
        return best_result
    
    # If no API succeeded, return the last error
    last_error = "All APIs failed"
    for result in results:
        if not isinstance(result, Exception) and result.error:
            last_error = f"{result.source}: {result.error}"
            break
    
    return PriceData(
        usdt_price=None,
        updated_at=None,
        source="all_failed",
        status=APIStatus.FAILED,
        error=last_error
    )

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
    adaptive_sleep = CACHE_DURATION
    
    while True:
        try:
            # Skip update if cache is still valid
            if is_cache_valid():
                logger.debug("Cache is still valid, skipping update")
                await asyncio.sleep(5)
                continue
                
            # Fetch price from multiple APIs
            price_data = await fetch_usdt_price_optimized()
            
            if price_data.status == APIStatus.SUCCESS and price_data.usdt_price:
                price_cache["usdt_price"] = price_data.usdt_price
                price_cache["updated_at"] = price_data.updated_at
                price_cache["source"] = price_data.source
                price_cache["last_error"] = None
                save_cache()
                consecutive_errors = 0
                adaptive_sleep = CACHE_DURATION  # Reset to normal interval
                logger.info(f"✅ قیمت USDT آپدیت شد از {price_data.source}: {price_data.usdt_price:,} تومان")
            else:
                # Try sync fallback
                logger.warning("Async APIs failed, trying sync fallback")
                sync_result = fetch_price_sync_fallback()
                
                if sync_result.status == APIStatus.SUCCESS and sync_result.usdt_price:
                    price_cache["usdt_price"] = sync_result.usdt_price
                    price_cache["updated_at"] = sync_result.updated_at
                    price_cache["source"] = sync_result.source
                    price_cache["last_error"] = None
                    save_cache()
                    consecutive_errors = 0
                    adaptive_sleep = CACHE_DURATION
                    logger.info(f"✅ قیمت USDT آپدیت شد از {sync_result.source} (sync): {sync_result.usdt_price:,} تومان")
                else:
                    consecutive_errors += 1
                    error_msg = f"❌ خطا در دریافت قیمت USDT: {price_data.error or sync_result.error or 'Unknown error'}"
                    price_cache["last_error"] = error_msg
                    price_cache["source"] = price_data.source
                    logger.warning(error_msg)
                    
                    # Adaptive sleep based on consecutive errors
                    if consecutive_errors >= max_consecutive_errors:
                        adaptive_sleep = min(adaptive_sleep * 2, 300)  # Max 5 minutes
                        logger.error(f"Too many consecutive errors ({consecutive_errors}), increasing sleep to {adaptive_sleep}s")
                        consecutive_errors = 0
                    else:
                        adaptive_sleep = min(adaptive_sleep * 1.5, 120)  # Max 2 minutes
                    
        except Exception as e:
            consecutive_errors += 1
            error_msg = f"❌ خطا در به‌روزرسانی قیمت: {e}"
            price_cache["last_error"] = error_msg
            logger.error(error_msg)
            adaptive_sleep = min(adaptive_sleep * 2, 300)
        
        await asyncio.sleep(adaptive_sleep)

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
        "source": price_cache.get("source", "unknown"),
        "cache_valid": is_cache_valid(),
        "api_stats": price_cache.get("api_stats", {})
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
    """Start the optimized price fetcher with proper cleanup."""
    load_cache()  # بارگذاری آخرین کش
    
    def run_scheduler():
        """Run the scheduler with proper cleanup."""
        try:
            start_scheduler()
        except KeyboardInterrupt:
            logger.info("Price fetcher stopped by user")
        except Exception as e:
            logger.error(f"Price fetcher error: {e}")
        finally:
            # Cleanup on exit
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(close_session())
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
    
    # اجرای Scheduler در یک Thread جدا
    Thread(target=run_scheduler, daemon=True).start()
    logger.info("🚀 Optimized price fetcher started with multiple APIs")

# ------------------------------
# API Monitoring Functions
# ------------------------------
def get_api_health() -> Dict[str, Any]:
    """Get health status of all APIs."""
    api_stats = price_cache.get("api_stats", {})
    health_status = {}
    
    for api_name in ["wallex", "nobitex", "bitpin"]:
        stats = api_stats.get(api_name, {})
        if stats:
            health_status[api_name] = {
                "status": stats.get("status", "unknown"),
                "last_check": stats.get("timestamp", 0),
                "error": stats.get("error"),
                "is_healthy": stats.get("status") == "success"
            }
        else:
            health_status[api_name] = {
                "status": "not_checked",
                "last_check": 0,
                "error": None,
                "is_healthy": False
            }
    
    return health_status

def get_best_api() -> str:
    """Get the name of the best performing API."""
    api_stats = price_cache.get("api_stats", {})
    best_api = "wallex"  # Default
    
    for api_name, stats in api_stats.items():
        if stats.get("status") == "success":
            best_api = api_name
            break
    
    return best_api

def fetch_price_sync_fallback() -> PriceData:
    """Fallback synchronous price fetching using requests."""
    # Try Wallex first
    try:
        response = requests.get(
            "https://api.wallex.ir/v1/markets",
            timeout=10,
            headers={
                'User-Agent': 'P+ Portfolio Manager/1.0',
                'Accept': 'application/json'
            }
        )
        if response.status_code == 200:
            data = response.json()
            markets = data.get("result", {}).get("symbols", {})
            usdt_market = markets.get("USDTTMN")
            
            if usdt_market:
                last_price = usdt_market.get("stats", {}).get("lastPrice")
                if last_price and last_price != "-":
                    price = int(float(last_price))
                    return PriceData(
                        usdt_price=price,
                        updated_at=int(time.time()),
                        source="wallex_sync",
                        status=APIStatus.SUCCESS
                    )
    except Exception as e:
        logger.warning(f"Wallex sync fallback failed: {e}")
    
    # Try Nobitex
    try:
        response = requests.post(
            "https://api.nobitex.ir/market/stats",
            json={"srcCurrency": "usdt", "dstCurrency": "rls"},
            timeout=10,
            headers={
                'User-Agent': 'P+ Portfolio Manager/1.0',
                'Accept': 'application/json'
            }
        )
        if response.status_code == 200:
            data = response.json()
            stats = data.get("stats", {}).get("usdt-rls", {})
            last_price = stats.get("latest")
            
            if last_price:
                price = int(float(last_price) / 10)
                return PriceData(
                    usdt_price=price,
                    updated_at=int(time.time()),
                    source="nobitex_sync",
                    status=APIStatus.SUCCESS
                )
    except Exception as e:
        logger.warning(f"Nobitex sync fallback failed: {e}")
    
    return PriceData(
        usdt_price=None,
        updated_at=None,
        source="all_failed",
        status=APIStatus.FAILED,
        error="All sync APIs failed"
    )

def force_price_update() -> bool:
    """Force an immediate price update (for testing)."""
    try:
        # First try async method
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, fetch_usdt_price_optimized())
                    result = future.result(timeout=30)
            except RuntimeError:
                # No event loop running, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(fetch_usdt_price_optimized())
                finally:
                    loop.close()
            
            if result.status == APIStatus.SUCCESS and result.usdt_price:
                price_cache["usdt_price"] = result.usdt_price
                price_cache["updated_at"] = result.updated_at
                price_cache["source"] = result.source
                price_cache["last_error"] = None
                save_cache()
                return True
        except Exception as e:
            logger.warning(f"Async price update failed: {e}")
        
        # Fallback to sync method
        logger.info("Trying sync fallback for price update")
        result = fetch_price_sync_fallback()
        
        if result.status == APIStatus.SUCCESS and result.usdt_price:
            price_cache["usdt_price"] = result.usdt_price
            price_cache["updated_at"] = result.updated_at
            price_cache["source"] = result.source
            price_cache["last_error"] = None
            save_cache()
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error in force update: {e}")
        return False
