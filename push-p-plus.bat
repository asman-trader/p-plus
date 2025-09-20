@echo off
:: ===========================
:: 🚀 Push خودکار به GitHub و آپلود به هاست
:: ===========================

:: مسیر پروژه لوکال
cd /d C:\Users\Aseman\OneDrive\Desktop\py-code\p-plus

:: commit خودکار با تاریخ و ساعت
set datetime=%date% %time%
git add .
git commit -m "Auto commit - %datetime%"
git push origin main

:: آپلود به هاست با WinSCP
set script_file=%cd%\upload_script.txt

:: ساخت فایل اسکریپت WinSCP
echo open ftp://USERNAME:PASSWORD@YOUR_HOST > %script_file%
echo lcd %cd% >> %script_file%
echo mirror -reverse -delete -verbose . /remote/path/on/host >> %script_file%
echo exit >> %script_file%

:: اجرای WinSCP (اطمینان از مسیر نصب درست)
"C:\Program Files (x86)\WinSCP\winscp.com" /script=%script_file%

:: پایان
exit
