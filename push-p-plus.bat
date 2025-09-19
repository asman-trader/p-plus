@echo off
setlocal enabledelayedexpansion
title Push p_plus-dashboard

:: مسیر پروژه
set "REPO_DIR=C:\Users\Aseman\OneDrive\Desktop\py-code\p-plus"

:: ریموت و شاخه
set "REMOTE_URL=https://github.com/asman-trader/p-plus.git"
set "BRANCH=main"

:: بارگذاری تنظیمات هاست
if exist "host-config.bat" (
  call host-config.bat
) else (
  :: تنظیمات پیش‌فرض
  set "HOST_USER=bztypmws"
  set "HOST_SERVER=pendar"
  set "HOST_PATH=/home/bztypmws/myapp"
  set "GIT_REMOTE_URL=https://github.com/asman-trader/p-plus.git"
  set "GIT_BRANCH=main"
  set "HOST_VENV_PATH=/home/bztypmws/virtualenv/myapp/3.10/bin/activate"
  set "HOST_POST_PULL_COMMANDS="
)

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

:: پوش به هاست
echo.
echo ================================
echo   Deploying to Host...
echo ================================
echo.

:: بررسی وجود SSH
where ssh >nul 2>&1
if %errorlevel% NEQ 0 (
  echo [!] SSH not found. Please install OpenSSH or Git for Windows.
  echo [!] Skipping host deployment.
  pause
  exit /b
)

:: اتصال به هاست و پول کردن
echo [*] Connecting to host and pulling changes...
echo [*] Host: %HOST_USER%@%HOST_SERVER%
echo [*] Path: %HOST_PATH%
echo [*] Git URL: %GIT_REMOTE_URL%

:: ساخت دستور کامل
set "SSH_COMMAND=cd %HOST_PATH% && source %HOST_VENV_PATH% && git remote set-url origin %GIT_REMOTE_URL% && git pull origin %GIT_BRANCH%"
if not "%HOST_POST_PULL_COMMANDS%"=="" (
  set "SSH_COMMAND=%SSH_COMMAND% && %HOST_POST_PULL_COMMANDS%"
)
set "SSH_COMMAND=%SSH_COMMAND% && echo 'Host updated successfully'"

:: اجرای دستور SSH
ssh %HOST_USER%@%HOST_SERVER% "%SSH_COMMAND%"

if %errorlevel% NEQ 0 (
  echo [!] خطا در اتصال به هاست یا پول کردن.
  echo [!] لطفاً دستی اتصال را بررسی کنید.
  echo.
  echo دستور دستی:
  echo ssh %HOST_USER%@%HOST_SERVER%
  echo cd %HOST_PATH%
  echo source /home/bztypmws/virtualenv/myapp/3.10/bin/activate
  echo git pull origin %BRANCH%
  echo.
) else (
  echo ✅ Host updated successfully!
)

echo.
echo ================================
echo   Deployment Complete!
echo ================================
echo.

:: بررسی نتیجه
if %errorlevel% EQU 0 (
  echo GitHub: ✅ Updated
  echo Host:   ✅ Updated
  echo.
  echo 🎉 All done! Your changes are live on the host.
) else (
  echo GitHub: ✅ Updated
  echo Host:   ❌ Failed
  echo.
  echo ⚠️  GitHub updated but host deployment failed.
  echo ⚠️  Please run test-ssh.bat to check SSH connection.
  echo ⚠️  Or deploy manually using the commands shown above.
)

echo.
echo ================================
echo   Next Steps:
echo ================================
echo 1. Check your website: https://your-domain.com
echo 2. Test the application functionality
echo 3. Check logs if needed: python view_logs.py
echo.
pause
endlocal
