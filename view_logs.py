#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ابزار مشاهده لاگ‌ها
"""
import os
from datetime import datetime

def view_logs():
    log_dir = 'logs'
    
    if not os.path.exists(log_dir):
        print("❌ پوشه logs وجود ندارد")
        return
    
    print("📋 فایل‌های لاگ موجود:")
    print("-" * 50)
    
    for filename in os.listdir(log_dir):
        if filename.endswith('.log'):
            filepath = os.path.join(log_dir, filename)
            size = os.path.getsize(filepath)
            modified = datetime.fromtimestamp(os.path.getmtime(filepath))
            print(f"📄 {filename} ({size} bytes) - {modified.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n" + "="*50)
    
    # نمایش آخرین خطوط errors.log
    error_log = os.path.join(log_dir, 'errors.log')
    if os.path.exists(error_log):
        print("🔴 آخرین خطاها:")
        print("-" * 30)
        try:
            with open(error_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-10:]:  # آخرین 10 خط
                    print(line.strip())
        except Exception as e:
            print(f"خطا در خواندن فایل: {e}")
    
    # نمایش آخرین خطوط app.log
    app_log = os.path.join(log_dir, 'app.log')
    if os.path.exists(app_log):
        print("\n📝 آخرین فعالیت‌ها:")
        print("-" * 30)
        try:
            with open(app_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-5:]:  # آخرین 5 خط
                    print(line.strip())
        except Exception as e:
            print(f"خطا در خواندن فایل: {e}")

if __name__ == "__main__":
    view_logs()
