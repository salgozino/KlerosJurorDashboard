from flask_sqlalchemy import SQLAlchemy
from app import create_app
import os

settings_module = os.environ.get('FLASK_ENV')
application = create_app(settings_module)
#db = SQLAlchemy(application)
