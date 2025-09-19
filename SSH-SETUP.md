# راهنمای تنظیم SSH برای Deploy خودکار

## 🔧 تنظیم SSH

### 1. نصب OpenSSH (اگر نصب نیست)
```bash
# Windows 10/11
# OpenSSH معمولاً پیش‌نصب است، اگر نیست:
# Settings > Apps > Optional Features > Add Feature > OpenSSH Client
```

### 2. تولید SSH Key (اختیاری - برای امنیت بیشتر)
```bash
# تولید کلید SSH
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"

# کپی کردن کلید عمومی به هاست
ssh-copy-id bztypmws@pendar
```

### 3. تنظیم فایل host-config.bat
```batch
:: اطلاعات هاست
set "HOST_USER=bztypmws"
set "HOST_SERVER=pendar"
set "HOST_PATH=/home/bztypmws/myapp"

:: مسیر SSH key (اختیاری)
set "HOST_SSH_KEY=C:\Users\Aseman\.ssh\id_rsa"

:: مسیر virtual environment
set "HOST_VENV_PATH=/home/bztypmws/virtualenv/myapp/3.10/bin/activate"

:: دستورات اضافی بعد از pull
set "HOST_POST_PULL_COMMANDS=pip install -r requirements.txt"
```

## 🚀 استفاده

### اجرای Deploy خودکار
```batch
push-p-plus.bat
```

### تست اتصال SSH
```bash
ssh bztypmws@pendar
```

## 🔍 عیب‌یابی

### مشکل: SSH not found
**راه حل:** OpenSSH را نصب کنید یا Git for Windows را استفاده کنید

### مشکل: Permission denied
**راه حل:** 
1. SSH key را تنظیم کنید
2. یا password را وارد کنید

### مشکل: Host not reachable
**راه حل:**
1. اتصال اینترنت را بررسی کنید
2. آدرس هاست را بررسی کنید
3. فایروال را بررسی کنید

## 📋 دستورات دستی

اگر Deploy خودکار کار نکرد:
```bash
ssh bztypmws@pendar
cd /home/bztypmws/myapp
source /home/bztypmws/virtualenv/myapp/3.10/bin/activate
git pull origin main
pip install -r requirements.txt
```

## ⚙️ تنظیمات پیشرفته

### استفاده از SSH Config
فایل `~/.ssh/config` ایجاد کنید:
```
Host pendar
    HostName pendar
    User bztypmws
    Port 22
    IdentityFile ~/.ssh/id_rsa
```

### استفاده از SSH Agent
```bash
# شروع SSH Agent
ssh-agent
ssh-add ~/.ssh/id_rsa
```
