# 💾 سیستم ذخیره‌سازی LocalStorage

## 🔧 ویژگی‌های جدید

### ✅ **ذخیره خودکار State**
- تمام تنظیمات و انتخاب‌ها در localStorage ذخیره می‌شوند
- با رفرش صفحه، اطلاعات حفظ می‌شوند
- نیازی به انتخاب مجدد ارزها نیست

### ✅ **ذخیره‌سازی موارد زیر:**
- **ارزهای انتخاب شده** - لیست ارزهای فعال
- **تنظیمات خرید/فروش** - آستانه‌های خرید و فروش
- **وضعیت lastBuy** - آخرین قیمت خرید هر ارز
- **تنظیمات صدا** - فعال/غیرفعال بودن اعلان‌ها

## 🚀 نحوه استفاده

### **خودکار:**
- تمام تغییرات خودکار ذخیره می‌شوند
- با رفرش صفحه، همه چیز بازگردانده می‌شود

### **دستی (از کنسول):**
```javascript
// مشاهده state فعلی
getState()

// ذخیره دستی state
saveState()

// بارگذاری state از localStorage
loadState()

// پاک کردن تمام اطلاعات
clearState()
```

### **دکمه پاک کردن:**
- دکمه "پاک کردن همه" در بخش انتخاب ارزها
- با تأیید، تمام اطلاعات پاک می‌شود

## 🔍 عیب‌یابی

### **مشکل: اطلاعات ذخیره نمی‌شود**
```javascript
// بررسی localStorage
localStorage.getItem('p-plus-state')

// بررسی state
getState()
```

### **مشکل: اطلاعات قدیمی نمایش داده می‌شود**
```javascript
// پاک کردن و بارگذاری مجدد
clearState()
loadState()
```

### **مشکل: localStorage پر شده**
```javascript
// پاک کردن تمام اطلاعات P-Plus
localStorage.removeItem('p-plus-state')
```

## 📊 ساختار داده

### **State Object:**
```javascript
{
  buyThreshold: 1.0,        // آستانه خرید
  sellThreshold: 1.5,       // آستانه فروش
  activeCoins: {            // ارزهای فعال
    "BTC": { lastBuy: 50000 },
    "ETH": { lastBuy: null }
  },
  notifs: []                // اعلان‌ها (موقت)
}
```

### **LocalStorage Key:**
- **Key:** `p-plus-state`
- **Format:** JSON string
- **Auto-save:** هر تغییر state

## ⚙️ تنظیمات پیشرفته

### **تغییر Key:**
```javascript
// در state.js
storage.save('custom-key', data)
```

### **اضافه کردن فیلد جدید:**
```javascript
// در saveState()
storage.save('p-plus-state', {
  buyThreshold: state.buyThreshold,
  sellThreshold: state.sellThreshold,
  activeCoins: state.activeCoins,
  newField: state.newField  // فیلد جدید
})
```

### **Backup/Restore:**
```javascript
// Backup
const backup = localStorage.getItem('p-plus-state')

// Restore
localStorage.setItem('p-plus-state', backup)
loadState()
```

## 🛡️ امنیت

### **محدودیت‌ها:**
- فقط در همان دامنه قابل دسترسی است
- کاربر می‌تواند آن را پاک کند
- برای اطلاعات حساس مناسب نیست

### **بهترین روش‌ها:**
- اطلاعات مهم را در سرور ذخیره کنید
- از localStorage فقط برای تنظیمات UI استفاده کنید
- به صورت دوره‌ای backup بگیرید

## 📱 سازگاری

### **مرورگرهای پشتیبانی شده:**
- ✅ Chrome 4+
- ✅ Firefox 3.5+
- ✅ Safari 4+
- ✅ Edge 12+
- ✅ IE 8+

### **محدودیت‌ها:**
- **حجم:** معمولاً 5-10MB
- **Private Mode:** ممکن است کار نکند
- **Mobile:** محدودیت‌های اضافی

## 🔄 Migration

### **از نسخه قدیمی:**
```javascript
// پاک کردن cache قدیمی
localStorage.removeItem('old-key')

// بارگذاری مجدد
loadState()
```

### **به نسخه جدید:**
- خودکار انجام می‌شود
- اطلاعات قدیمی حفظ می‌شود
- فیلدهای جدید اضافه می‌شوند
