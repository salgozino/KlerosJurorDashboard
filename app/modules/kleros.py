# -*- coding: utf-8 -*-
# import os
import pandas as pd
from datetime import datetime, timedelta
from .kleros_db import Court, Juror, Config, JurorStake, StakesEvolution
from app.modules import db

import logging
logger = logging.getLogger(__name__)


def get_staked_by_address(address):
    return Juror(address=address).current_stakings_per_court


def get_court_info_table():
    courts = Court.query.all()
    courtInfo = {}
    for c in courts:
        courtInfo[c.name] = {'Jurors': c.activeJurors,
                             'Total Staked': c.totalStaked,
                             'Min Stake': c.minStake,
                             'Locked Stake': c.voteStake,
                             'Mean Staked': c.meanStaked,
                             'Max Staked': c.maxStaked,
                             'Disputes in the last 30 days': c.disputesLast30days,
                             'Open Disputes': c.openCases,
                             'Min Stake in USD': c.minStakeUSD,
                             'id': c.id
                             }
    return courtInfo


def get_all_court_chances(pnkStaked):
    courts = Court.query.all()
    courtChances = {}
    pnkPrice = float(Config.get('PNKprice'))
    ethPrice = float(Config.get('ETHprice'))
    for c in courts:
        rewardETH = c.feeForJuror
        rewardUSD = rewardETH * ethPrice
        voteStakePNK = c.voteStake
        voteStakeUSD = voteStakePNK * pnkPrice
        stats = c.juror_stats()
        totalStaked = c.totalStaked
        odds = chance_calculator(pnkStaked, totalStaked)
        if odds == 0:
            chances = float('nan')
        else:
            chances = 1/odds
        courtChances[c.name] = {
                    'Jurors': stats['length'],
                    'Disputes in the last 30 days': len(c.disputes(30)),
                    'Odds': odds,
                    'Chances': chances,
                    'Reward (ETH)': rewardETH,
                    'Reward (USD)': rewardUSD,
                    'Vote Stake (PNK)': voteStakePNK,
                    'Vote Stake (USD)': voteStakeUSD,
                    'Reward/Risk': rewardUSD/voteStakeUSD
                    }
    return courtChances


def chance_calculator(amountStaked, totalStaked, nJurors=3):
    """
    Calculate the chance of been drawn according to the formula of Dr.
    William George
    """
    totalStaked = float(totalStaked)
    amountStaked = float(amountStaked)
    if totalStaked == 0:
        return 0
    else:
        p = amountStaked/totalStaked
        noDrawn = (1 - p)**nJurors
        chanceDrawnOnce = 1 - noDrawn
        return chanceDrawnOnce


def calculate_historic_stakes_in_courts():
    try:
        end = StakesEvolution.query.order_by(StakesEvolution.id.desc()).first().timestamp
    except Exception:
        # if couldn't reach the last value, it's because there is no items in
        # stakes_evolution table. Start at the begining of the stakes.
        end = JurorStake.query.order_by(JurorStake.id).first().timestamp
        logger.debug("Starting with the first stake, because was not found any StakeEvolution item")

    while end < datetime.today():
        enddate = datetime.strftime(end, '%Y-%m-%d')
        logger.debug(f"Calculating the Stakes upto the date {enddate}")
        stakes = StakesEvolution.getStakes_ByCourt_ForEndDate(enddate)
        # print(stakes)
        # logger.debug(f"Adding the values {stakes} to the StakesEvolution table")
        StakesEvolution.addDateValues(stakes)
    end += timedelta(days=1)
