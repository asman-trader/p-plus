@echo off
:: فایل تنظیمات هاست
:: این فایل را برای تنظیم اطلاعات هاست خود ویرایش کنید

:: اطلاعات هاست
set "HOST_USER=bztypmws"
set "HOST_SERVER=pendar"
set "HOST_PATH=/home/bztypmws/myapp"

:: مسیر SSH key (اختیاری - اگر خالی باشد از password استفاده می‌کند)
set "HOST_SSH_KEY="

:: مسیر virtual environment روی هاست
set "HOST_VENV_PATH=/home/bztypmws/virtualenv/myapp/3.10/bin/activate"

:: دستورات اضافی بعد از pull (اختیاری)
set "HOST_POST_PULL_COMMANDS="

echo Host configuration loaded:
echo   User: %HOST_USER%
echo   Server: %HOST_SERVER%
echo   Path: %HOST_PATH%
echo   SSH Key: %HOST_SSH_KEY%
echo   VEnv: %HOST_VENV_PATH%
echo.
