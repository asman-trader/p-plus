import os
import sys
from dotenv import load_dotenv

# مسیر پروژه روی هاست
project_home = '/home/bztypmws/my-app'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# بارگذاری متغیرهای محیطی از فایل .env در ریشه پروژه
load_dotenv(os.path.join(project_home, '.env'))

# ایمپورت اپ Flask از app.py
from app import create_app
application = create_app()
