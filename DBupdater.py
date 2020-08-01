from app.modules.dbModule import fillDB, db
import os
from app import create_app

# Elastic Beanstalk initalization
settings_module = os.environ.get('CONFIG_MODULE')
application = create_app(settings_module)
db.init_app(application)

with application.app_context():
    fillDB()

