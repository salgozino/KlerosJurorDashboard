# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 19:10:44 2020

@author: 60070385
"""
from app.modules import db
from .KlerosDB import *
from .kleros_eth import KlerosLiquid, logger
from .etherscan import CMC, Etherscan
from datetime import datetime

def createDB():
    db.create_all()
    
    kl = KlerosLiquid()
    nCourts = 9
    courtAddresses = {0: '0x0d67440946949fe293b45c52efd8a9b3d51e2522',
                      2: '0xebcf3bca271b26ae4b162ba560e243055af0e679',
                      3: '0x916deab80dfbc7030277047cd18b233b3ce5b4ab',
                      4: '0xcb4aae35333193232421e86cd2e9b6c91f3b125f'}
    for courtID in range(0,nCourts+1):
        try:
            courtInfo = kl.courtInfo(courtID)
            courtName = kl.mapCourtNames(courtID)
            if courtName == 'Unknown':
                logger.info(f"There is a new court with ID {courtID}! We need his name!")
        except:
            # there is no new court to create
            break
        try:
            courtaddress = courtAddresses[courtID]
        except:
            courtaddress = None
            
        db.session.add(Court(id = courtID,
                             parent = courtInfo['parent'],
                             name = courtName,
                             address = courtaddress,
                             voteStake = courtInfo['votesStake'] ,
                             feeForJuror = courtInfo['feeForJuror'],
                             minStake = courtInfo['minStake']))
        db.session.commit()
        logger.info(f"Court {courtID} added to the database")
    
    Config.set('dispute_search_block', kl.initial_block)
    Config.set('staking_search_block', kl.initial_block)
    Config.set('token_supply', kl.tokenSupply)
    
    db.session.add(Visitor())
    db.session.commit()
    logger.info("Tables created")
    
def rebuildDB():
    logger.info("Droping all the tables")
    # For MySQL
    db.engine.execute("SET FOREIGN_KEY_CHECKS = 0;")
    db.engine.execute("SET sql_mode='NO_AUTO_VALUE_ON_ZERO';")
    db.drop_all()
    logger.info("Creating Tables")
    createDB()
    

def fillDB():
    #db.session.rollback()
    #db.session.close_all()
    kl = KlerosLiquid()
    logger.info("Fetching all the stakes")
    kl.getStakes()
    logger.info("Fetching all the disputes")
    kl.getDisputes()
    logger.info("Fetching eth and pnk prices")
    updatePrices()
    updated = datetime.strftime(datetime.utcnow(),"%Y-%m-%d %H:%M:%S")
    Config.set('updated', updated)
    db.session.commit()
    
def updatePrices():
    pnkInfo = CMC().getCryptoInfo()
    Config.set('PNKvolume24h', pnkInfo['quote']['USD']['volume_24h'])
    Config.set('PNKpctchange24h', pnkInfo['quote']['USD']['percent_change_24h'])
    Config.set('PNKcirculating_supply', pnkInfo['circulating_supply'])
    Config.set('PNKprice', CMC().getPNKprice())
    Config.set('ETHprice', CMC().getETHprice())
    db.session.commit()

def fillDeposit():
    # Fetching deposits
    Deposit.query.delete()
    for court in Court.query.all():
        if court.address == "": continue
        print("Fetching deposits for %s" % court.name)
        for item in Etherscan.deposits(court.address):
            deposit = Deposit(
                address = item['from'],
                cdate = datetime.utcfromtimestamp(int(item['timeStamp'])),
                amount = int(item['value']) / 10**18,
                txid = item['hash'],
                token_contract = "XXX", # FIXME
                court_id = court.id
            )
            db.session.add(deposit)
    db.session.commit() 

if __name__ == '__main__':
    createDB()
    fillDB()


