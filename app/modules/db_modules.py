# -*- coding: utf-8 -*-
"""In this module you can found different functions to create and update the
database. The scrapper (in the root folder) runs functions from this module to
update the database for example
"""
from datetime import datetime, timedelta
import logging
from app.modules import db
from .kleros_db import Court, Config, Visitor, Deposit, StakesEvolution, \
    JurorStake
from .kleros_eth import KlerosLiquid
from .etherscan import CoinGecko, Etherscan


logger = logging.getLogger(__name__)

# Smart Contracts of the Courts.
# TODO! -> need to get automatically this info from somewhere. Help Wanted!
courtAddresses = {0: '0x0d67440946949fe293b45c52efd8a9b3d51e2522',
                  2: '0xebcf3bca271b26ae4b162ba560e243055af0e679',
                  3: '0x916deab80dfbc7030277047cd18b233b3ce5b4ab',
                  4: '0xcb4aae35333193232421e86cd2e9b6c91f3b125f'}


def createDB():
    db.create_all()
    kl = KlerosLiquid()
    nCourts = 23
    for courtID in range(0, nCourts+1):
        try:
            courtInfo = kl.court_info(courtID)
            courtName = kl.map_court_names(courtID)
            if courtName == 'Unknown':
                logger.info(f"There is a new court with ID {courtID}! \
                            We need his name!")
        except Exception:
            # there is no new court to create
            break
        try:
            courtaddress = courtAddresses[courtID]
        except KeyError:
            courtaddress = None
        parent = courtInfo['parent']
        name = courtName,
        address = courtaddress,
        voteStake = courtInfo['votesStake'],
        feeForJuror = courtInfo['feeForJuror'],
        minStake = courtInfo['minStake']
        db.session.add(Court(id=courtID,
                             parent=parent,
                             name=name,
                             address=address,
                             voteStake=voteStake,
                             feeForJuror=feeForJuror,
                             minStake=minStake))
        logger.info(f"Court {courtID} added to the Court table")

    db.session.commit()
    Config.set('dispute_search_block', kl.initial_block)
    Config.set('staking_search_block', kl.initial_block)
    Config.set('token_supply', kl.token_supply)

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
    # db.session.rollback()
    # db.session.close_all()
    kl = KlerosLiquid()
    logger.info("Updating courts")
    updateCourtInfo()
    logger.info("Fetching all the stakes")
    kl.get_stakes()
    logger.info("Fetching all the disputes")
    kl.get_disputes()
    logger.info("Fetching eth and pnk prices")
    # Update current prices
    updatePrices()

    # Update Court Statistics
    Court.updateStatsAllCourts()
    # Update UpdatedField
    updated = datetime.strftime(datetime.utcnow(), "%Y-%m-%d %H:%M:%S")
    Config.set('updated', updated)
    db.session.commit()


def updatePrices():
    pnkInfo = CoinGecko().getCryptoInfo()
    Config.set('PNKvolume24h', pnkInfo['market_data']['total_volume']['usd'])
    Config.set('PNKpctchange24h', pnkInfo['market_data']['price_change_24h_in_currency']['usd']*100)
    Config.set('PNKcirculating_supply', pnkInfo['market_data']['circulating_supply'])
    Config.set('PNKprice', CoinGecko().getPNKprice())
    Config.set('ETHprice', CoinGecko().getETHprice())
    eth_fees = 0
    pnk_redistributed = 0
    for court in range(Court().ncourts):
        fees = Court(id=court).fees_paid()
        eth_fees += fees['eth']
        pnk_redistributed += fees['pnk']
    Config.set('fees_ETH', eth_fees)
    Config.set('PNK_redistributed', pnk_redistributed)
    db.session.commit()


def fillDeposit():
    # Fetching deposits
    Deposit.query.delete()
    for court in Court.query.all():
        if court.address == "":
            continue
        print("Fetching deposits for %s" % court.name)
        for item in Etherscan.deposits(court.address):
            deposit = Deposit(
                address=item['from'],
                cdate=datetime.utcfromtimestamp(int(item['timeStamp'])),
                amount=int(item['value']) / 10**18,
                txid=item['hash'],
                token_contract="XXX",  # FIXME
                court_id=court.id
            )
            db.session.add(deposit)
    db.session.commit()


def updateCourtInfo():
    logger.debug("Updating court info")
    kl = KlerosLiquid()
    courtID = 0
    while True:
        try:
            courtInfo = kl.court_info(courtID)
        except Exception:
            # there is no new court to create
            break
        courtName = kl.map_court_names(courtID)
        try:
            courtaddress = courtAddresses[courtID]
        except KeyError:
            courtaddress = None
        if db.session.query(Court).filter(Court.id == courtID).first():
            db.session.query(Court).filter(Court.id == courtID).update({'parent': courtInfo['parent'],
                                                                        'name': courtName,
                                                                        'address': courtaddress,
                                                                        'voteStake': courtInfo['votesStake'],
                                                                        'feeForJuror': courtInfo['feeForJuror'],
                                                                        'minStake': courtInfo['minStake']})
            logger.info(f"Court {courtID} updated")
        else:
            # is a new court
            db.session.add(Court(id=courtID,
                                 parent=courtInfo['parent'],
                                 name=courtName,
                                 address=courtaddress,
                                 voteStake=courtInfo['votesStake'],
                                 feeForJuror=courtInfo['feeForJuror'],
                                 minStake=courtInfo['minStake']))
            logger.info(f"Court {courtID} created")
        db.session.commit()
        # increase the court id number and check if can be updated or created
        courtID += 1


def updateStakesEvolution():
    try:
        end = StakesEvolution.query.order_by(StakesEvolution.id.desc()).first().timestamp
        end += timedelta(days=1)
    except Exception:
        # if couldn't reach the last value, it's because there is no items in
        # stakes_evolution table. Start at the begining of the stakes.
        end = JurorStake.query.order_by(JurorStake.id).first().timestamp
        logger.debug("Starting with the first stake, because was not found any StakeEvolution item")

    while end.date() < datetime.today().date():
        enddate = datetime.strftime(end, '%Y-%m-%d')
        logger.debug(f"Calculating the Stakes upto the date {enddate}")
        stakes = StakesEvolution.getStakes_ByCourt_ForEndDate(enddate)
        # print(stakes)
        logger.debug(f"Adding the values of date {stakes['timestamp']} to the StakesEvolution table")
        StakesEvolution.addDateValues(stakes)
        end += timedelta(days=1)
