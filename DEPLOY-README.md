# 🚀 راهنمای Deploy خودکار P-Plus

## 📁 فایل‌های Deploy

- `push-p-plus.bat` - فایل اصلی Deploy
- `host-config.bat` - تنظیمات هاست
- `test-ssh.bat` - تست اتصال SSH
- `SSH-SETUP.md` - راهنمای تنظیم SSH

## ⚡ استفاده سریع

### 1. تنظیم اولیه
```batch
# ویرایش تنظیمات هاست
notepad host-config.bat
```

### 2. تست اتصال
```batch
test-ssh.bat
```

### 3. Deploy
```batch
push-p-plus.bat
```

## 🔧 تنظیمات

### فایل host-config.bat
```batch
:: اطلاعات هاست
set "HOST_USER=bztypmws"
set "HOST_SERVER=pendar"
set "HOST_PATH=/home/bztypmws/myapp"

:: مسیر SSH key (اختیاری)
set "HOST_SSH_KEY="

:: مسیر virtual environment
set "HOST_VENV_PATH=/home/bztypmws/virtualenv/myapp/3.10/bin/activate"

:: دستورات اضافی بعد از pull
set "HOST_POST_PULL_COMMANDS="
```

## 📋 مراحل Deploy

1. **Git Add & Commit** - اضافه کردن تغییرات
2. **Version Bump** - افزایش نسخه
3. **Push to GitHub** - آپلود به GitHub
4. **SSH to Host** - اتصال به هاست
5. **Pull Changes** - دریافت تغییرات
6. **Activate Venv** - فعال‌سازی محیط مجازی
7. **Run Commands** - اجرای دستورات اضافی

## 🛠️ عیب‌یابی

### مشکل: SSH not found
```batch
# نصب OpenSSH یا Git for Windows
# یا استفاده از WSL
```

### مشکل: Permission denied
```batch
# تنظیم SSH key یا استفاده از password
ssh-keygen -t rsa
ssh-copy-id bztypmws@pendar
```

### مشکل: Host not reachable
```batch
# بررسی اتصال
ping pendar
telnet pendar 22
```

## 📊 وضعیت Deploy

### موفق ✅
```
GitHub: ✅ Updated
Host:   ✅ Updated
🎉 All done! Your changes are live on the host.
```

### نیمه موفق ⚠️
```
GitHub: ✅ Updated
Host:   ❌ Failed
⚠️  GitHub updated but host deployment failed.
```

## 🔄 Deploy دستی

اگر Deploy خودکار کار نکرد:
```bash
# روی هاست
ssh bztypmws@pendar
cd /home/bztypmws/myapp
source /home/bztypmws/virtualenv/myapp/3.10/bin/activate
git pull origin main
pip install -r requirements.txt
```

## 📝 لاگ‌ها

### بررسی لاگ‌های اپلیکیشن
```bash
python view_logs.py
```

### بررسی لاگ‌های هاست
```bash
tail -f /var/log/apache2/error.log
tail -f /var/log/nginx/error.log
```

## ⚙️ تنظیمات پیشرفته

### SSH Config
فایل `~/.ssh/config`:
```
Host pendar
    HostName pendar
    User bztypmws
    Port 22
    IdentityFile ~/.ssh/id_rsa
```

### Git Hooks
```bash
# Pre-commit hook
echo "python -m py_compile app.py" > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## 🎯 نکات مهم

1. **همیشه قبل از Deploy تست کنید**
2. **SSH key را امن نگه دارید**
3. **Backup بگیرید قبل از تغییرات بزرگ**
4. **لاگ‌ها را بررسی کنید**
5. **نسخه‌ها را track کنید**

## 📞 پشتیبانی

اگر مشکلی داشتید:
1. `test-ssh.bat` را اجرا کنید
2. لاگ‌ها را بررسی کنید
3. Deploy دستی را امتحان کنید
4. تنظیمات SSH را بررسی کنید
