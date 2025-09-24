# 🔧 حل مشکل DNS و اتصال

## 🚨 مشکل شناسایی شده
```
Error fetching USDT price from Wallex: Cannot connect to host api.wallex.ir:443 ssl:default [getaddrinfo failed]
```

## 🔍 علل احتمالی

### 1. **مشکل DNS**
- DNS server در دسترس نیست
- فیلترینگ DNS
- مشکل در تنظیمات شبکه

### 2. **مشکل اتصال**
- فایروال مسدود کننده
- Proxy settings
- SSL/TLS issues

### 3. **مشکل API**
- API والکس در دسترس نیست
- Rate limiting
- تغییر در endpoint

## ✅ راه‌حل‌های اعمال شده

### 1. **Sync Fallback**
- اضافه کردن fallback با `requests` library
- پشتیبانی از والکس و نوبیتکس
- عدم وابستگی به async operations

### 2. **Multiple API Support**
- والکس (اولویت 1)
- نوبیتکس (اولویت 2) 
- بیت‌پین (اولویت 3)

### 3. **Improved Error Handling**
- تشخیص نوع خطا
- Fallback خودکار
- Logging بهتر

## 🧪 تست کردن

### تست Sync Fallback:
```bash
python test_sync_fallback.py
```

### تست کامل:
```bash
python test_price_fetcher.py
```

### تست API Health:
```bash
curl http://localhost:5000/api/api-health
```

## 🔧 راه‌حل‌های اضافی

### 1. **تغییر DNS Server**
```bash
# Windows
netsh interface ip set dns "Wi-Fi" static 8.8.8.8
netsh interface ip add dns "Wi-Fi" 8.8.4.4 index=2

# Linux/Mac
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf
```

### 2. **استفاده از Proxy**
```python
# در price_fetcher.py
proxies = {
    'http': 'http://proxy:port',
    'https': 'https://proxy:port'
}
```

### 3. **تست اتصال دستی**
```bash
# تست DNS
nslookup api.wallex.ir

# تست اتصال
ping api.wallex.ir

# تست HTTPS
curl -I https://api.wallex.ir/v1/markets
```

## 📊 وضعیت فعلی

### ✅ **کار می‌کند:**
- Sync fallback با requests
- Multiple API support
- Error handling بهتر
- Logging کامل

### ⚠️ **نیاز به بررسی:**
- DNS resolution
- Network connectivity
- Firewall settings

## 🚀 استفاده

### 1. **اجرای برنامه:**
```bash
python app.py
```

### 2. **تست API:**
```bash
# دریافت قیمت
curl http://localhost:5000/api/usdt-price

# وضعیت API ها
curl http://localhost:5000/api/api-health

# اجبار به‌روزرسانی
curl -X POST http://localhost:5000/api/force-update
```

### 3. **Monitoring:**
- لاگ‌ها در console نمایش داده می‌شوند
- وضعیت API ها در `/api/api-health` قابل مشاهده است
- کش در `price_cache.json` ذخیره می‌شود

## 🔍 Debugging

### 1. **بررسی لاگ‌ها:**
```bash
# اجرا با verbose logging
python app.py 2>&1 | grep -E "(ERROR|WARNING|INFO)"
```

### 2. **بررسی کش:**
```bash
cat price_cache.json
```

### 3. **تست دستی API:**
```python
import requests
response = requests.get("https://api.wallex.ir/v1/markets")
print(response.status_code)
print(response.json())
```

## 📈 Performance

### قبل از بهینه‌سازی:
- ❌ وابسته به async operations
- ❌ تک API (والکس)
- ❌ مشکل DNS blocking

### بعد از بهینه‌سازی:
- ✅ Sync fallback
- ✅ Multiple APIs
- ✅ DNS independent
- ✅ Better error handling
- ✅ Automatic fallback
