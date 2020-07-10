# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 19:10:44 2020

@author: 60070385
"""
from KlerosDB import db, Court, Config, Visitor
from kleros_eth import KlerosLiquid, logger
from datetime import datetime

def rebuildDB():
    logger.info("Droping all the tables")
    kl = KlerosLiquid()
    db.drop_all()
    db.create_all()
    db.session.add(Court( id = 0, parent = None, name = "General", address = "0x0d67440946949fe293b45c52efd8a9b3d51e2522"))
    db.session.add(Court( id = 1, parent = 0, name = "Blockchain", address = ""))
    db.session.add(Court( id = 2, parent = 1, name = "Blockchain>NonTechnical", address = "0xebcf3bca271b26ae4b162ba560e243055af0e679"))
    db.session.add(Court( id = 3, parent = 2, name = "Blockchain>NonTechnical>TokenListing", address = "0x916deab80dfbc7030277047cd18b233b3ce5b4ab"))
    db.session.add(Court( id = 4, parent = 1, name = "Blockchain>Technical", address = "0xcb4aae35333193232421e86cd2e9b6c91f3b125f"))
    db.session.add(Court( id = 5, parent = 0, name = "Marketing Services", address = ""))
    db.session.add(Court( id = 6, parent = 0, name = "English Language", address = ""))
    db.session.add(Court( id = 7, parent = 0, name = "Video Production", address = ""))
    db.session.add(Court( id = 8, parent = 0, name = "Onboarding", address = ""))
    db.session.add(Court( id = 9, parent = 0, name = "Curation", address = ""))
    Config.set('dispute_search_block', kl.initial_block)
    Config.set('staking_search_block', kl.initial_block)
    Config.set('token_supply', kl.tokenSupply)
    
    db.session.add(Visitor())
    db.session.commit()
    logger.info("Tables created")

def fillDB():
    kl = KlerosLiquid()
    logger.info("Fetching all the disputes")
    kl.getDisputes()
    logger.info("Fetching all the stakes")
    kl.getStakes()
    updated = datetime.strftime("%Y-%m-%d %H:%M:%S", datetime.now())
    Config.set('updated', updated)
    
if __name__ == '__main__':
    rebuildDB()
    fillDB()


