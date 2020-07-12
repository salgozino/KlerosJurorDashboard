# -*- coding: utf-8 -*-
from bin.dbModule import fillDB, rebuildDB
from config import host, DB
from flask_sqlalchemy import sqlalchemy

url = host
engine = sqlalchemy.create_engine(url)  # connect to server
create_str = "CREATE DATABASE IF NOT EXISTS {};".format(DB)
engine.execute(create_str)
engine.execute("USE {};".format(DB))
rebuildDB()
fillDB()