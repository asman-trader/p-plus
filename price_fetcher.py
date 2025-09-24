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
    "usd_rate": None, 
    "updated_at": None
}

# ------------------------------
# تابع Async برای گرفتن قیمت از والکس
# ------------------------------
async def fetch_prices_from_wallex():
    """Fetch both USDT price and USD rate from Wallex"""
    url = "https://api.wallex.ir/v1/markets"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    markets = data.get("result", {}).get("symbols", {})
                    
                    # Get USDT price
                    usdt_market = markets.get("USDTTMN")
                    usdt_price = None
                    if usdt_market:
                        last_price = usdt_market.get("stats", {}).get("lastPrice")
                        if last_price and last_price != "-":
                            usdt_price = int(float(last_price))
                    
                    # Get USD rate (USD/IRT)
                    usd_market = markets.get("USDIRT")
                    usd_rate = None
                    if usd_market:
                        last_price = usd_market.get("stats", {}).get("lastPrice")
                        if last_price and last_price != "-":
                            usd_rate = float(last_price)
                    
                    return usdt_price, usd_rate
    except Exception as e:
        print(f"Error fetching prices from Wallex: {e}")
    
    return None, None

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
                if "usd_rate" not in price_cache:
                    price_cache["usd_rate"] = None
                if "updated_at" not in price_cache:
                    price_cache["updated_at"] = None
            except:
                price_cache = {
                    "usdt_price": None, 
                    "usd_rate": None, 
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
            usdt_price, usd_rate = await fetch_prices_from_wallex()
            if usdt_price or usd_rate:
                if usdt_price:
                    price_cache["usdt_price"] = usdt_price
                if usd_rate:
                    price_cache["usd_rate"] = usd_rate
                price_cache["updated_at"] = int(time.time())
                save_cache()
                
                if usdt_price:
                    print(f"✅ قیمت USDT آپدیت شد: {usdt_price:,} تومان")
                if usd_rate:
                    print(f"✅ نرخ USD آپدیت شد: {usd_rate:,.0f} ریال")
            else:
                print("❌ خطا در دریافت قیمت‌ها از والکس")
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

def get_current_usd_rate():
    return price_cache.get("usd_rate")

def get_price_info():
    return {
        "usdt_price": price_cache.get("usdt_price"),
        "usd_rate": price_cache.get("usd_rate"),
        "updated_at": price_cache.get("updated_at"),
        "usdt_formatted": f"{price_cache['usdt_price']:,} تومان" if price_cache.get("usdt_price") else "نامشخص",
        "usd_formatted": f"{price_cache['usd_rate']:,.0f} ریال" if price_cache.get("usd_rate") else "نامشخص"
    }

# ------------------------------
# شروع scheduler
# ------------------------------
def start_price_fetcher():
    load_cache()  # بارگذاری آخرین کش
    # اجرای Scheduler در یک Thread جدا
    Thread(target=start_scheduler, daemon=True).start()
    print("🚀 Price fetcher started")
