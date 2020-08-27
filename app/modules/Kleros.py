# -*- coding: utf-8 -*-
# import os
import pandas as pd
from datetime import datetime, timedelta
import logging
from .KlerosDB import Court, Juror, Config, JurorStake, StakesEvolution
from app.modules import db

courtNames = {}
FORMAT = '%(asctime)-15s - %(message)s'
logging.basicConfig(format=FORMAT, filename='log.log', level='INFO')
logger = logging.getLogger()


class StakesKleros():
    data = pd.DataFrame()
    jurors = pd.DataFrame()

    @staticmethod
    def getAllJurors():
        allJurors = pd.DataFrame()
        nCourts = len(db.session.query(Court).all())
        for court in range(nCourts):
            query = Court(id=court).jurors_stakes_query()
            jurors = pd.read_sql_query(query.statement, query.session.bind)
            jurors = jurors[['address', 'setStake']].set_index('address')
            jurors.rename(columns={'setStake': court}, inplace=True)
            allJurors = pd.concat([allJurors, jurors], axis=1)
        allJurors['Total'] = allJurors.sum(axis=1)
        return allJurors.fillna(0)

    @classmethod
    def getstakedByAddress(cls, address):
        return Juror(address=address).current_stakings_per_court

    @classmethod
    def getChanceByCourt(cls, courtID, pnkstaked):
        if int(pnkstaked) > 0:
            total = cls.getstakedInCourts().loc[courtID].totalstaked
            chance = cls.chanceCalculator(pnkstaked, total)
        else:
            chance = 0
        return chance

    @classmethod
    def getChancesInAllCourts(cls, pnkStaked):
        chances = {}
        for court in courtNames.keys():
            chances[court] = cls.getChanceByCourt(int(court), float(pnkStaked))
        return chances

    @staticmethod
    def getCourtInfoTable():
        courts = Court.query.all()
        courtInfo = {}
        for c in courts:
            courtInfo[c.name] = {'Jurors': c.activeJurors,
                                 'Total Staked': c.totalStaked,
                                 'Min Stake': c.minStake,
                                 'Mean Staked': c.meanStaked,
                                 'Max Staked': c.maxStaked,
                                 'Disputes in the last 30 days': c.disputesLast30days,
                                 'Min Stake in USD': c.minStakeUSD
                                 }
        return courtInfo

    @classmethod
    def getAllCourtChances(cls, pnkStaked):
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
            odds = cls.chanceCalculator(pnkStaked, totalStaked)
            if odds == 0:
                chances = float('nan')
            else:
                chances = 1/odds
            courtChances[c.name] = {
                        'Jurors': stats['length'],
                        'Dispues in the last 30 days': len(c.disputes(30)),
                        'Odds': odds,
                        'Chances': chances,
                        'Reward (ETH)': rewardETH,
                        'Reward (USD)': rewardUSD,
                        'Vote Stake (PNK)': voteStakePNK,
                        'Vote Stake (USD)': voteStakeUSD,
                        'Risk/Reward': rewardUSD/voteStakeUSD
                        }
        return courtChances

    @staticmethod
    def chanceCalculator(amountStaked, totalStaked, nJurors=3):
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

    @staticmethod
    def calculateHistoricStakesInCourts():
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
OLD METHODS....

     @classmethod
     def getChanceByAddress(cls, address):
         stakedInCourts = cls.getstakedByAddress(address).reset_index().values
         chances = []
         for row in stakedInCourts:
             totalstakedInCourt = cls.totalStakedByCourt(row[0])
             chances.append({'courtID': row[0],
                             'courtLabel': row[2],
                             'chance': cls.chanceCalculator(row[1],
                                                            totalstakedInCourt)})


             # print("You have {:.3f}% of chances to been drawn in the court {}".format(
             #     row[1]/totalstakedInCourt*100,
             #     row[2]))
         return chances
     @classmethod
     def calculateStakedInCourts(cls):
         if cls.data.empty:
             cls.loadCSV(cls)
         courts = cls.data.subcourtID.unique()
         totalInCourts = []
         allJurors = cls.getAllJurors()
         for court in courts:
             courtChilds = KlerosLiquid().getAllCourtChilds(court)
             courtChilds.append(court)
             courtJurors = allJurors[(allJurors[courtChilds] > 0).any(axis=1)][courtChilds]
             totalInCourts.append({'courtID': court,
                                   'totalstaked': cls.totalStakedByCourt(int(court)),
                                   'courtLabel': courtNames[court],
                                   'n_Jurors': len(courtJurors),
                                   'meanStake': courtJurors.mean().mean(),
                                   'maxStake': courtJurors.max().max()})
         df = pd.DataFrame(totalInCourts)
         df = df.fillna(0)
         cls.dataToCSV(df,
                       os.path.join(DATA_PATH, 'StakedInCourts.csv'))
         return df

    # @staticmethod
    # def readHistoric(filename):
    #     filename = os.path.join(DATA_PATH, filename)
    #     df = pd.read_csv(filename, index_col=0)
    #     df.timestamp = pd.to_datetime(df.timestamp)
    #     df.set_index('timestamp', inplace=True)
    #     df.index = pd.to_datetime(df.index)
    #     return df

     @classmethod
     def historicStakesInCourts(cls):
         return cls.readHistoric('historicStakes.csv')

     @classmethod
     def historicJurorsInCourts(cls):
         return cls.readHistoric('historicJurors.csv')

#     def calculateHistoricJurorsInCourts(self, freq = 'D'):
#         if self.data.empty:
#             self.loadCSV()
#         df = self.data.copy()
#         start = min(df.index)
#         end = max(df.index)
#         rango = pd.date_range(start=start, end=end, freq=freq)
#         data = pd.DataFrame(columns = [i for i in range(len(courtNames))])
#         for end in rango:
#             dff = df[(df.index >= start) & (df.index <= end)].copy()
#             dff = dff[~dff.duplicated(subset=['address', 'subcourtID'], keep='last')]
#             dff = dff[dff.setStake > 0]
#             dff = dff.groupby('subcourtID')['address'].count()
#             data.loc[end] = dff
#         data.fillna(0, inplace=True)
#         self.dataToCSV(data,
#                       os.path.join(DATA_PATH,'historicJurors.csv'))
#         return data


# class DisputesEvents():

#     def __init__(self):
#         self.data = self.loadCSV()

#     def loadCSV(self):
#         filename=os.path.join(DATA_PATH,'createDisputesLogs.csv')
#         df = pd.read_csv(filename, converters={'rounds': literal_eval}, index_col=0)
#         df.timestamp = pd.to_datetime(df.timestamp)
#         self.data = df.set_index('timestamp')
#         return self.data

#     def historicDisputes(self):
#         df = self.data.copy()
#         df = df['disputeID']
#         return df

#     def historicRounds(self):
#         df = self.data.copy()
#         df['nRounds'] = df.rounds.apply(len)
#         df['nRounds_cum'] = df.nRounds.cumsum()
#         return df

#     def mostLongCases(self):
#         df = self.data.copy()
#         df['nRounds'] = df.rounds.apply(len)
#         df = df[df['nRounds'] == max(df['nRounds'])]
#         return df[['disputeID', 'nRounds', 'subcourtID']].to_dict('records')

#     def historicDisputesbyCourt(self, court):
#         df = self.data.copy()
#         df = df[df.subcourtID == court]
#         df.reset_index(inplace=True)
#         df.index.rename('count', inplace=True)
#         df.reset_index(inplace=True)
#         df = df[['timestamp', 'count', 'disputeID']]
#         df.set_index('timestamp', inplace=True)
#         return df

#     def historicJurorsDrawn(self):
#         # Return the amount of jurors drawn by dispute and dates

#         df = self.data.copy()
#         df['n_jurors'] = df.rounds.apply(lambda x: sum([r['jury_size'] for r in x]))
#         df['n_jurors_cum'] = df.n_jurors.cumsum()
#         return df[['n_jurors','n_jurors_cum', 'disputeID']]

#     def historicJurorsDrawnByCourt(self, court):
#         df = self.data[self.data.subcourtID == court].copy()
#         df['n_jurors'] = df.rounds.apply(lambda x: sum([r['jury_size'] for r in x]))
#         df['n_jurors_cum'] = df.n_jurors.cumsum()
#         return df[['n_jurors','n_jurors_cum', 'disputeID']]
"""
