from app.modules.dbModule import fillDB, db, updateStakesEvolution
import os
from app import create_app
from datetime import datetime

# Elastic Beanstalk initalization
settings_module = os.environ.get('CONFIG_MODULE')
application = create_app(settings_module)
db.init_app(application)

with application.app_context():
    fillDB()
    if datetime.now().hour == 0:
        updateStakesEvolution()
