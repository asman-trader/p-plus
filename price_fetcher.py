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
price_cache = {"price": None, "updated_at": None}

# ------------------------------
# تابع Async برای گرفتن قیمت از والکس
# ------------------------------
async def fetch_usdt_tmn_price():
    url = "https://api.wallex.ir/v1/markets"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                markets = data.get("result", {})
                usdt_market = markets.get("USDTTMN")
                if usdt_market:
                    last_price = usdt_market.get("stats", {}).get("lastPrice")
                    if last_price and last_price != "-":
                        return int(float(last_price))
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
            except:
                price_cache = {"price": None, "updated_at": None}

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
            price = await fetch_usdt_tmn_price()
            if price:
                price_cache["price"] = price
                price_cache["updated_at"] = int(time.time())
                save_cache()
                print(f"✅ قیمت USDT آپدیت شد: {price:,} تومان")
            else:
                print("❌ خطا در دریافت قیمت USDT")
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
def get_current_price():
    return price_cache.get("price")

def get_price_info():
    return {
        "price": price_cache.get("price"),
        "updated_at": price_cache.get("updated_at"),
        "formatted": f"{price_cache['price']:,} تومان" if price_cache.get("price") else "نامشخص"
    }

# ------------------------------
# شروع scheduler
# ------------------------------
def start_price_fetcher():
    load_cache()  # بارگذاری آخرین کش
    # اجرای Scheduler در یک Thread جدا
    Thread(target=start_scheduler, daemon=True).start()
    print("🚀 Price fetcher started")
