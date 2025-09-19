@echo off
:: فایل تنظیمات هاست
:: این فایل را برای تنظیم اطلاعات هاست خود ویرایش کنید

:: اطلاعات هاست
set "HOST_USER=bztypmws"
set "HOST_SERVER=pendar"
set "HOST_PATH=/home/bztypmws/myapp"

:: تنظیمات Git (HTTPS)
set "GIT_REMOTE_URL=https://github.com/asman-trader/p-plus.git"
set "GIT_BRANCH=main"

:: مسیر virtual environment روی هاست
set "HOST_VENV_PATH=/home/bztypmws/virtualenv/myapp/3.10/bin/activate"

:: دستورات اضافی بعد از pull (اختیاری)
set "HOST_POST_PULL_COMMANDS="

echo Host configuration loaded:
echo   User: %HOST_USER%
echo   Server: %HOST_SERVER%
echo   Path: %HOST_PATH%
echo   Git URL: %GIT_REMOTE_URL%
echo   Branch: %GIT_BRANCH%
echo   VEnv: %HOST_VENV_PATH%
echo.
