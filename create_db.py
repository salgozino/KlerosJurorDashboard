# -*- coding: utf-8 -*-
from bin.dbModule import createDB, fillDB, rebuildDB
from config import host, DB, SQLALCHEMY_DATABASE_URI
from flask_sqlalchemy import sqlalchemy

url = host
#engine = sqlalchemy.create_engine(url)  # connect to server
#create_str = "CREATE DATABASE IF NOT EXISTS {};".format(DB)
#engine.execute(create_str)
#engine.execute("USE {};".format(DB))
rebuildDB()
fillDB()