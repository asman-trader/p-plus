@echo off
:: تست اتصال SSH به هاست

:: بارگذاری تنظیمات هاست
if exist "host-config.bat" (
  call host-config.bat
) else (
  echo [!] فایل host-config.bat یافت نشد.
  echo [!] لطفاً ابتدا فایل تنظیمات را ایجاد کنید.
  pause
  exit /b
)

:: تنظیمات پیش‌فرض اگر فایل config وجود نداشت
if not defined GIT_REMOTE_URL (
  set "GIT_REMOTE_URL=https://github.com/asman-trader/p-plus.git"
  set "GIT_BRANCH=main"
)

echo.
echo ================================
echo   Testing SSH Connection
echo ================================
echo.
echo Host: %HOST_USER%@%HOST_SERVER%
echo Path: %HOST_PATH%
echo.

:: بررسی وجود SSH
where ssh >nul 2>&1
if %errorlevel% NEQ 0 (
  echo [!] SSH not found. Please install OpenSSH or Git for Windows.
  pause
  exit /b
)

echo [*] Testing SSH connection...
echo.

:: تست اتصال ساده
if "%HOST_SSH_KEY%"=="" (
  ssh %HOST_USER%@%HOST_SERVER% "echo 'SSH connection successful' && pwd && whoami"
) else (
  ssh -i "%HOST_SSH_KEY%" %HOST_USER%@%HOST_SERVER% "echo 'SSH connection successful' && pwd && whoami"
)

if %errorlevel% NEQ 0 (
  echo.
  echo [!] SSH connection failed!
  echo [!] Please check your SSH settings in host-config.bat
  echo.
  echo Manual test:
  echo ssh %HOST_USER%@%HOST_SERVER%
) else (
  echo.
  echo ✅ SSH connection successful!
  echo.
  echo [*] Testing project directory...
  
  :: تست دسترسی به پروژه
  ssh %HOST_USER%@%HOST_SERVER% "cd %HOST_PATH% && pwd && ls -la"
  
  if %errorlevel% NEQ 0 (
    echo [!] Cannot access project directory: %HOST_PATH%
  ) else (
    echo ✅ Project directory accessible!
    echo.
    echo [*] Testing Git configuration...
    
    :: تست تنظیمات Git
    ssh %HOST_USER%@%HOST_SERVER% "cd %HOST_PATH% && git remote -v && git status"
    
    if %errorlevel% NEQ 0 (
      echo [!] Git configuration issue
    ) else (
      echo ✅ Git configuration OK!
      echo.
      echo [*] Testing Git pull...
      
      :: تست Git pull
      ssh %HOST_USER%@%HOST_SERVER% "cd %HOST_PATH% && git remote set-url origin %GIT_REMOTE_URL% && git pull origin %GIT_BRANCH% --dry-run"
      
      if %errorlevel% NEQ 0 (
        echo [!] Git pull test failed
      ) else (
        echo ✅ Git pull test successful!
      )
    )
  )
)

echo.
pause
