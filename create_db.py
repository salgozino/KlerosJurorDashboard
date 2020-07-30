# -*- coding: utf-8 -*-
from flask import Flask
from app.modules.dbModule import fillDB, rebuildDB, db
import os

config = os.environ.get('CONFIG_MODULE')
db_name = os.environ.get('RDS_DB_NAME')
app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

with app.app_context():
    db.engine.execute("USE "+db_name+";")
    rebuildDB()
    fillDB()