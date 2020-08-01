# -*- coding: utf-8 -*-
from app import create_app
from app.modules.dbModule import fillDB, rebuildDB, db
import os

config = os.environ.get('CONFIG_MODULE')
db_name = os.environ.get('RDS_DB_NAME')
app = create_app(config)
db.init_app(app)

with app.app_context():
    db.engine.execute("USE "+db_name+";")
    rebuildDB()
    fillDB()