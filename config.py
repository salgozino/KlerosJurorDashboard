# -*- coding: utf-8 -*-

# AWS
host = 'mysql+pymysql://salgozino:Algozin0!1485@klerosboarddb.cfqteljjiyhg.us-east-2.rds.amazonaws.com:3306'
DB = 'klerosboarddb'
SQLALCHEMY_DATABASE_URI = host + '/' + DB
# Uncomment the line below if you want to work with a local DB
#SQLALCHEMY_DATABASE_URI = 'sqlite:///../db/kleros.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_POOL_RECYCLE = 3600

WTF_CSRF_ENABLED = True
SECRET_KEY = 'klerosdev'
DEBUG = True