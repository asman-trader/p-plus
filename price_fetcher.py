import asyncio
import aiohttp
import json
import os
import time
from threading import Thread

# ------------------------------
# متغیرهای کش
# ------------------------------
CACHE_FILE = "price_cache.json"
price_cache = {
    "usdt_price": None, 
    "updated_at": None
}

# ------------------------------
# تابع Async برای گرفتن قیمت از والکس
# ------------------------------
async def fetch_usdt_price_from_wallex():
    """Fetch USDT price from Wallex"""
    try:
        async with aiohttp.ClientSession() as session:
            # Get USDT price from markets API
            markets_url = "https://api.wallex.ir/v1/markets"
            async with session.get(markets_url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    markets = data.get("result", {}).get("symbols", {})
                    
                    # Get USDT price
                    usdt_market = markets.get("USDTTMN")
                    if usdt_market:
                        last_price = usdt_market.get("stats", {}).get("lastPrice")
                        if last_price and last_price != "-":
                            return int(float(last_price))
    except Exception as e:
        print(f"Error fetching USDT price from Wallex: {e}")
    
    return None

# ------------------------------
# ذخیره/بازیابی کش در فایل
# ------------------------------
def load_cache():
    global price_cache
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                price_cache = json.load(f)
                # Ensure all keys exist
                if "usdt_price" not in price_cache:
                    price_cache["usdt_price"] = None
                if "updated_at" not in price_cache:
                    price_cache["updated_at"] = None
            except:
                price_cache = {
                    "usdt_price": None, 
                    "updated_at": None
                }

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(price_cache, f, ensure_ascii=False, indent=2)

# ------------------------------
# به‌روزرسانی قیمت هر ۳۰ ثانیه
# ------------------------------
async def update_price():
    global price_cache
    while True:
        try:
            usdt_price = await fetch_usdt_price_from_wallex()
            if usdt_price:
                price_cache["usdt_price"] = usdt_price
                price_cache["updated_at"] = int(time.time())
                save_cache()
                print(f"✅ قیمت USDT آپدیت شد: {usdt_price:,} تومان")
            else:
                print("❌ خطا در دریافت قیمت USDT از والکس")
        except Exception as e:
            print(f"❌ خطا در به‌روزرسانی قیمت: {e}")
        
        await asyncio.sleep(30)

def start_scheduler():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(update_price())

# ------------------------------
# تابع برای دریافت قیمت فعلی
# ------------------------------
def get_current_usdt_price():
    return price_cache.get("usdt_price")

def get_price_info():
    return {
        "usdt_price": price_cache.get("usdt_price"),
        "updated_at": price_cache.get("updated_at"),
        "usdt_formatted": f"{price_cache['usdt_price']:,} تومان" if price_cache.get("usdt_price") else "نامشخص"
    }

# ------------------------------
# شروع scheduler
# ------------------------------
def start_price_fetcher():
    load_cache()  # بارگذاری آخرین کش
    # اجرای Scheduler در یک Thread جدا
    Thread(target=start_scheduler, daemon=True).start()
    print("🚀 Price fetcher started")
