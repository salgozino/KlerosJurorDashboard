# config/default.py
import os
# Define the application directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WTF_CSRF_ENABLED = True
SECRET_KEY = os.environ.get("SECRET_KEY")
DEBUG = False

# App environments
APP_ENV_LOCAL = 'local'
APP_ENV_TESTING = 'testing'
APP_ENV_DEVELOPMENT = 'development'
APP_ENV_STAGING = 'staging'
APP_ENV_PRODUCTION = 'production'
APP_ENV = APP_ENV_DEVELOPMENT
