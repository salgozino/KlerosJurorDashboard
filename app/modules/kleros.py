# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from .subgraph import Subgraph
from .oracles import CoinGecko


import logging
logger = logging.getLogger(__name__)


def period2number(period):
    period_map = {'execution': 4,
                  'appeal': 3,
                  'vote': 2,
                  'commit': 1,
                  'evidence': 0}
    return period_map[period]


def get_all_court_chances(pnkStaked, n_votes=3, network='mainnet'):
    courts = Subgraph(network).getCourtTable()
    courtChances = {}
    pnkPrice = CoinGecko().getPNKprice()
    if network == 'xdai':
        ethPrice = 1.
    else:
        ethPrice = CoinGecko().getETHprice()
    for c in courts.keys():
        rewardETH = courts[c]['Fee For Juror']
        rewardUSD = rewardETH * ethPrice
        voteStakePNK = courts[c]['Vote Stake']
        voteStakeUSD = voteStakePNK * pnkPrice
        activeJurors = courts[c]['Jurors']
        totalStaked = courts[c]['Total Staked']
        odds = chance_calculator(pnkStaked, totalStaked, n_votes)
        if odds == 0:
            chances = float('nan')
            share = float('nan')
        else:
            chances = 1/odds
            share = pnkStaked/totalStaked
        reward_currency = 'xDAI' if network == 'xdai' else 'ETH'
        courtChances[courts[c]['Name']] = {
                    'Jurors': activeJurors,
                    'Total Staked': totalStaked,
                    'Stake share': share,
                    'Disputes in the last 30 days': courts[c][
                        'Disputes in the last 30 days'],
                    'Odds': odds,
                    'Chances': chances,
                    f'Reward ({reward_currency})': rewardETH,
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


def getWhenPeriodEnd(dispute, courtID):
    """
    Return the datetime when ends current period of the dispute.
    Returns None if dispute it's in execution period
    """
    if dispute['period'] == 'execution':
        return None
    else:
        timesPeriods = Subgraph.getTimePeriods(courtID)
        lastPeriodChange = int(dispute['lastPeriodChange'])
        periodlength = int(timesPeriods[period2number(dispute['period'])])
        return datetime.fromtimestamp(lastPeriodChange) + \
            timedelta(seconds=periodlength)
