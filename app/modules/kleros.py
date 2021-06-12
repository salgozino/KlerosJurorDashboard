# -*- coding: utf-8 -*-
# import os
import pandas as pd
from datetime import datetime, timedelta
from .subgraph import getCourtTable, getTimePeriods, gwei2eth
from .oracles import CoinGecko


import logging
logger = logging.getLogger(__name__)

def period2number(period):
    period_map = {'execution':4,
    'appeal':3,
    'vote':2,
    'commit':1,
    'evidence':0}
    return period_map[period]


def get_all_court_chances(pnkStaked):
    courts = getCourtTable()
    print(courts)
    courtChances = {}
    pnkPrice = CoinGecko().getPNKprice()
    ethPrice = CoinGecko().getETHprice()
    for c in courts.keys():
        print(c)
        print(courts[c]['Fee For Juror'])
        rewardETH = courts[c]['Fee For Juror']
        rewardUSD = rewardETH * ethPrice
        voteStakePNK = courts[c]['Vote Stake']
        voteStakeUSD = voteStakePNK * pnkPrice
        activeJurors = courts[c]['Jurors']
        totalStaked = courts[c]['Total Staked']
        odds = chance_calculator(pnkStaked, totalStaked)
        if odds == 0:
            chances = float('nan')
        else:
            chances = 1/odds
        courtChances[courts[c]['Name']] = {
                    'Jurors': activeJurors,
                    'Disputes in the last 30 days': courts[c]['Disputes in the last 30 days'],
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

"""
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
"""

def getWhenPeriodEnd(dispute, courtID):
    """
    Return the datetime when ends current period of the dispute.
    Returns None if dispute it's in execution period
    """
    if dispute['period'] == 'execution':
        return None
    else:
        timesPeriods = getTimePeriods(courtID)
        lastPeriodChange = int(dispute['lastPeriodChange'])
        periodlength = int(timesPeriods[period2number(dispute['period'])])
        now = datetime.now()
        return datetime.fromtimestamp(lastPeriodChange) + timedelta(seconds=periodlength)
        
