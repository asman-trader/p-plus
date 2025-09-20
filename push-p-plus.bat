@echo off
echo ===========================
echo 🚀 شروع فرآیند Push به GitHub
echo ===========================

:: رفتن به مسیر پروژه لوکال
cd /d C:\Users\Aseman\OneDrive\Desktop\py-code\p-plus

:: گرفتن تاریخ و ساعت برای پیام commit
set datetime=%date% %time%
git add .
git commit -m "Auto commit - %datetime%"
git push origin main

echo ===========================
echo ✅ Push به GitHub انجام شد
echo ===========================

:: آپدیت خودکار روی هاست
echo ===========================
echo 🌐 اتصال به هاست و آپدیت پروژه
echo ===========================
ssh bztypmws@pendar "cd /home/bztypmws/myapp && git reset --hard origin/main && git clean -fd && git pull origin main"

echo ===========================
echo ✅ پروژه روی هاست هم آپدیت شد
echo ===========================

pause
