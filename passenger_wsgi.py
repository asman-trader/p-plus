import sys
import os

# Ensure the app directory is on the path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Import the Flask app object
from webhook import app as application

