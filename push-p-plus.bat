@echo off
setlocal enabledelayedexpansion

:: ===========================
:: 🚀 Push خودکار به GitHub
:: ===========================

:: حرکت به مسیر اسکریپت
cd /d "%~dp0"

:: بررسی اینکه داخل مخزن گیت هستیم
git rev-parse --is-inside-work-tree >nul 2>&1 || (
    echo ⚠️ این مسیر یک مخزن Git نیست.
    pause
    exit /b 1
)

:: شاخه فعلی
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
if "%BRANCH%"=="" set BRANCH=main

:: جلوگیری از استیج شدن فایل‌های حساس/داده
git restore --staged app/data instance uploads logs app/static/uploads app/data/uploads *.db *.sqlite* *.log .env .env.* *.pem *.key *.crt >nul 2>&1

:: به‌روزرسانی مخزن با rebase و autostash
git pull --rebase --autostash origin %BRANCH%

:: استیج کردن همه تغییرات
git add -A

:: دوباره فایل‌های حساس را از استیج خارج کن
git reset app/data instance uploads logs app/static/uploads app/data/uploads *.db *.sqlite* *.log .env .env.* *.pem *.key *.crt >nul 2>&1

:: بررسی اگر چیزی برای کامیت نیست
git diff --cached --quiet && (
    echo هیچ تغییری برای پوش وجود ندارد.
    pause
    exit /b 0
)

:: نسخه‌گذاری ساده
set version=0
if exist version.txt set /p version=<version.txt
for /f "delims=0123456789" %%x in ("%version%") do set version=0
set /a version+=1
echo %version%>version.txt
git add version.txt

:: پیام کامیت
set msg=
if not "%~1"=="" (
    set msg=%*
) else (
    set msg=Auto commit v%version%
)

:: نمایش خلاصه تغییرات
echo --------------------------
git status --short
echo --------------------------

:: کامیت و پوش به شاخه فعلی
git commit -m "%msg%"
git push origin %BRANCH%

echo --------------------------
echo ✅ %msg% روی شاخه %BRANCH% پوش شد.
pause
