@echo off
setlocal enabledelayedexpansion
title Push p_plus-dashboard

:: مسیر پروژه
set "REPO_DIR=C:\Users\Aseman\OneDrive\Desktop\py-code\p-plus"

:: ریموت و شاخه
set "REMOTE_URL=https://github.com/asman-trader/p_plus-dashboard.git"
set "BRANCH=main"

:: الگوهای فایل‌هایی که نباید پوش بشن
set "DATA_PATTERNS=app/data instance uploads logs *.db *.sqlite *.log .env"

echo.
echo ================================
echo   Project:  %REPO_DIR%
echo   Remote:   %REMOTE_URL%
echo   Branch:   %BRANCH%
echo ================================
echo.

:: رفتن به مسیر پروژه
cd /d "%REPO_DIR%" || (
  echo [!] مسیر پروژه یافت نشد.
  pause
  exit /b
)

:: اگر ریپو نیست → init کن
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [*] init repo ...
  git init
)

:: شاخه main
git branch -M %BRANCH%

:: تنظیم ریموت origin
git remote get-url origin >nul 2>&1
if %errorlevel%==0 (
  git remote set-url origin %REMOTE_URL%
) else (
  git remote add origin %REMOTE_URL%
)

:: کشیدن آخرین تغییرات
git pull --rebase origin %BRANCH% >nul 2>&1

:: استیج همه فایل‌ها
git add -A

:: فایل‌های دیتایی رو از استیج خارج کن
for %%P in (%DATA_PATTERNS%) do (
  git reset %%P >nul 2>&1
  git restore --staged %%P >nul 2>&1
)

:: اگر چیزی برای کامیت نیست
git diff --cached --quiet && (
  echo [-] هیچ تغییری برای commit نیست.
  pause
  exit /b
)

:: افزایش نسخه
set version=0
if exist version.txt set /p version=<version.txt
set /a version+=1
echo %version%>version.txt
git add version.txt

:: پیام کامیت
set "msg=Auto commit v%version%"

echo [*] Commit: %msg%
git commit -m "%msg%"

:: پوش
echo [*] Pushing to origin %BRANCH% ...
git push -u origin %BRANCH%

if %errorlevel% NEQ 0 (
  echo [!] خطا در push. اگر HTTPS استفاده می‌کنی باید Personal Access Token بزنی.
  pause
  exit /b
)

echo --------------------------
echo ✅ %msg% پوش شد.
echo --------------------------
pause
endlocal
