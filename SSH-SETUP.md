# راهنمای تنظیم Deploy خودکار با HTTPS

## 🔧 تنظیم Deploy

### 1. نصب OpenSSH (اگر نصب نیست)
```bash
# Windows 10/11
# OpenSSH معمولاً پیش‌نصب است، اگر نیست:
# Settings > Apps > Optional Features > Add Feature > OpenSSH Client
```

### 2. تنظیم فایل host-config.bat
```batch
:: اطلاعات هاست
set "HOST_USER=bztypmws"
set "HOST_SERVER=pendar"
set "HOST_PATH=/home/bztypmws/myapp"

:: تنظیمات Git (HTTPS)
set "GIT_REMOTE_URL=https://github.com/asman-trader/p-plus.git"
set "GIT_BRANCH=main"

:: مسیر virtual environment
set "HOST_VENV_PATH=/home/bztypmws/virtualenv/myapp/3.10/bin/activate"

:: دستورات اضافی بعد از pull
set "HOST_POST_PULL_COMMANDS=pip install -r requirements.txt"
```

### 3. تنظیم Git روی هاست (یک بار)
```bash
# روی هاست
ssh bztypmws@pendar
cd /home/bztypmws/myapp
git remote set-url origin https://github.com/asman-trader/p-plus.git
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

## 🚀 استفاده

### اجرای Deploy خودکار
```batch
push-p-plus.bat
```

### تست اتصال و Git
```batch
test-ssh.bat
```

### تست اتصال SSH دستی
```bash
ssh bztypmws@pendar
```

## 🔍 عیب‌یابی

### مشکل: SSH not found
**راه حل:** OpenSSH را نصب کنید یا Git for Windows را استفاده کنید

### مشکل: Git authentication failed
**راه حل:** 
1. روی هاست Git credentials را تنظیم کنید:
   ```bash
   git config --global credential.helper store
   git pull origin main  # وارد کردن username/password
   ```

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
git remote set-url origin https://github.com/asman-trader/p-plus.git
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
