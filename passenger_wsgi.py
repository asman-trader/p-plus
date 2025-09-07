# passenger_wsgi.py
import sys, os

# مسیر پروژه روی هاست (دقیقاً همونی که تو cPanel زدی)
project_home = '/home/bztypmws/p-plus'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ایمپورت اپلیکیشن از app.py
from app import create_app

# Passenger دنبال این متغیر می‌گرده
application = create_app()
