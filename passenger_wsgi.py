import os
import sys

# مسیر پروژه روی هاست
project_home = '/home/bztypmws/my-app'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# ایمپورت اپ Flask از app.py
from app import create_app
application = create_app()
