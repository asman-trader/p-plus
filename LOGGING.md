# سیستم لاگ‌گیری P-Plus

## 📋 فایل‌های لاگ

### `logs/app.log`
- **محتوای**: تمام فعالیت‌های عادی اپلیکیشن
- **سطح**: INFO و بالاتر
- **شامل**: درخواست‌ها، پاسخ‌ها، و رویدادهای مهم

### `logs/errors.log`
- **محتوای**: فقط خطاها و استثناها
- **سطح**: ERROR
- **شامل**: stack trace کامل خطاها

## 🔧 نحوه استفاده

### مشاهده لاگ‌ها
```bash
python view_logs.py
```

### لاگ‌گیری در کد
```python
from flask import current_app

# لاگ اطلاعاتی
current_app.logger.info('پیام اطلاعاتی')

# لاگ هشدار
current_app.logger.warning('پیام هشدار')

# لاگ خطا
current_app.logger.error('پیام خطا')
```

## 📊 انواع لاگ‌ها

### 1. لاگ‌های خودکار
- شروع اپلیکیشن
- ثبت blueprint ها
- خطاهای 404 و 500
- استثناهای غیرمنتظره

### 2. لاگ‌های API
- درخواست‌های قیمت ارز
- درخواست‌های سیگنال
- خطاهای API خارجی

### 3. لاگ‌های عملیات
- ذخیره تنظیمات
- ثبت معاملات
- عملیات فایل

## 🛠️ تنظیمات

### تغییر سطح لاگ
در `app.py` در تابع `setup_logging`:

```python
# برای لاگ فایل
file_handler.setLevel(logging.INFO)  # DEBUG, INFO, WARNING, ERROR

# برای کنسول
console_handler.setLevel(logging.WARNING)
```

### اضافه کردن لاگ جدید
```python
# در هر route
@blueprint.route('/endpoint')
def my_endpoint():
    current_app.logger.info(f'درخواست به {request.endpoint}')
    try:
        # کد شما
        current_app.logger.info('عملیات موفق')
    except Exception as e:
        current_app.logger.error(f'خطا: {str(e)}')
```

## 📁 ساختار فایل‌ها

```
logs/
├── app.log      # لاگ اصلی
└── errors.log   # لاگ خطاها
```

## 🔍 مثال‌های عملی

### لاگ درخواست قیمت
```
2025-09-19 22:14:00,051 - coins_routes - INFO - Price request for symbol: BTC
2025-09-19 22:14:00,060 - coins_routes - INFO - Fetching price from CMC for BTC
2025-09-19 22:14:01,941 - coins_routes - INFO - Successfully fetched price for BTC: 115608.04
```

### لاگ خطا
```
2025-09-19 22:14:01,941 - app - ERROR - Unhandled exception: list indices must be integers or slices, not str
Traceback (most recent call last):
  File "routes/signals_routes.py", line 20, in _ensure_symbol
    data["history"].setdefault(sym, [])
TypeError: list indices must be integers or slices, not str
```

## ⚠️ نکات مهم

1. **حجم فایل**: لاگ‌ها ممکن است بزرگ شوند، بهتر است به صورت دوره‌ای پاک شوند
2. **امنیت**: اطلاعات حساس را در لاگ‌ها قرار ندهید
3. **عملکرد**: لاگ‌گیری زیاد ممکن است سرعت را کاهش دهد
4. **پشتیبان‌گیری**: لاگ‌ها را به صورت منظم بک‌آپ بگیرید
