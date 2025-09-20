@echo off
echo ===========================
echo 🚀 شروع فرآیند Push به GitHub
echo ===========================

:: رفتن به مسیر پروژه
cd /d C:\Users\Aseman\OneDrive\Desktop\py-code\p-plus

:: گرفتن تاریخ و ساعت برای پیام commit
set datetime=%date% %time%
git add .
git commit -m "Auto commit - %datetime%"
git push origin main

echo ===========================
echo ✅ Push به GitHub انجام شد
echo ===========================

pause
