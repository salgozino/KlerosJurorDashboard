# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 19:10:44 2020

@author: 60070385
"""
from bin.KlerosDB import db, Court, Config, Visitor, Deposit
from bin.kleros_eth import KlerosLiquid, logger
from bin.etherscan import Etherscan, CMC
from datetime import datetime


def rebuildDB():
    logger.info("Droping all the tables")
    kl = KlerosLiquid()
    nCourts = len(db.session.query(Court).all())
    db.drop_all()
    db.create_all()
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
    
    Config.set('dispute_search_block', kl.initial_block)
    Config.set('staking_search_block', kl.initial_block)
    Config.set('token_supply', kl.tokenSupply)
    
    db.session.add(Visitor())
    db.session.commit()
    logger.info("Tables created")

def fillDB():
    db.session.rollback()
    db.session.close_all()
    kl = KlerosLiquid()
    logger.info("Fetching all the disputes")
    kl.getDisputes()
    logger.info("Fetching all the stakes")
    kl.getStakes()
    
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
    updated = datetime.strftime(datetime.now(),"%Y-%m-%d %H:%M:%S")
    Config.set('updated', updated)
    Config.set('PNKprice', CMC().getPNKprice())
    Config.set('ETHprice', CMC().getETHprice())
    db.session.commit()
    

if __name__ == '__main__':
    rebuildDB()
    fillDB()


