# -*- coding: utf-8 -*-
import os
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
UPPER_FOLDER = os.path.split(THIS_FOLDER)[0]
DATA_PATH = os.path.join(UPPER_FOLDER, "data")

from bin.etherscan import Etherscan
from bin.web3Node import web3Node, Contract
import pandas as pd
import requests
import urllib
from eth_abi import decode_abi
import json

from datetime import datetime, timedelta
import logging
from ast import literal_eval



FORMAT = '%(asctime)-15s - %(message)s'
logging.basicConfig(format=FORMAT, filename='log.log', level='INFO')
logger = logging.getLogger()
courtNames = {0:'General', 
              1:'Blockchain',
              2:'Blockchain>NonTechnical',
              3:'Blockchain>NonTechnical>TokenListing',
              4:'Blockchain>Technical',
              5:'Marketing Services',
              6:'English Language',
              7:'Video Production',
              8:'Onboarding',
              9:'Curation'}
disputePeriods = {0: 'Evidence', 
                  1: 'Commit', 
                  2: 'Vote',
                  3: 'Appeal',
                  4: 'Execution'}


class KlerosLiquid(Contract, web3Node, Etherscan):
    stakes_event_topic = "0x8f753321c98641397daaca5e8abf8881fff1fd7a7bc229924a012e2cb61763d5"
    create_dispute_event_topic = "0x141dfc18aa6a56fc816f44f0e9e2f1ebc92b15ab167770e17db5b084c10ed995"
    
    def __init__(self):
        with open(os.path.join(UPPER_FOLDER,'lib/ABI_KlerosLiquid.json'),'r') as f:
            contract_abi = json.loads(f.read())['result']
        address = "0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069"
        self.contract = web3Node.web3.eth.contract(abi=contract_abi,
                                                   address=address)
        try:
            with open(os.path.join(DATA_PATH,'PNKSupply.json'),'r') as f:
                self.tokenSupply = json.loads(f.read())['tokenSupply']
        except:
            self.tokenSupply = 0
        
       
    def getTokenSupply(self):
        api_options = {
                'module':'stats',
                'action':'tokensupply',
                'contractaddress':'0x93ed3fbe21207ec2e8f2d3c3de6e058cb73bc04d',
                'apikey': self.api_key
                }
        url = self.api_url + urllib.parse.urlencode(api_options)
        response = requests.get(url)
        get_json = response.json()
        if get_json['status']:
            tokenSupply = float(get_json['result'])/10**18
        else:
            raise "Error trying to get the token supply" + get_json['message']
        return tokenSupply


    def getCourtChildrens(self, courtID):
        return self.contract.functions.getSubcourt(courtID).call()[0]


    def getAllCourtChilds(self, courtID):
        childs = set(self.getCourtChildrens(courtID))
        allChilds = []
        while childs:
            child = childs.pop()
            allChilds.append(child)
            childs.update(self.getCourtChildrens(child))
        return allChilds


    def getEventFromTo(self, event='stake', fromblock=None):
        if event == 'stake':
            topic = self.stakes_event_topic
        elif (event == 'dispute') or (event == 'disputes'):
            event = 'dispute'
            topic = self.create_dispute_event_topic
        else:
            raise Exception("Error, the event is not defined")

        if fromblock is None:
            # fromblock = 7303690
            fromblock = 7315700
        endblock = self.web3.eth.blockNumber
        step = 1000
        toblock = fromblock + step
        if endblock < toblock:
            endblock = toblock + 1
        allItems = []
        while toblock < endblock:
            print(fromblock, '-',toblock)
            api_options = {
                'module':'logs',
                'action':'getLogs',
                'fromBlock':fromblock,
                'toBlock':toblock,
                'address':self.contract.address,
                'topic0':topic,
                'apikey': self.api_key
                }
    
            url = self.api_url + urllib.parse.urlencode(api_options)
            response = requests.get(url)
            get_json = response.json()
            
            items = get_json['result']
            if len(items) == 1000:
                print("Ups!, maybe there are missed items, slow down the iterations")
                toblock = fromblock + round(step/3)
                continue

            for item in items:
                try:
                    if event == 'stake':
                        dataWanted = self.parseStakesEvent(item)
                    elif event == 'dispute':
                        dataWanted = self.parseDisputeEvent(item)
                        # dataWanted = item
                    allItems.append(dataWanted)
                except:
                    logger.info("error processing the information. {}".format(item))

            fromblock = toblock + 1
            toblock = fromblock + step
        return allItems

    @classmethod
    def parseStakesEvent(cls, item):
        decodedData = decode_abi(('uint96','uint128','int256'),
                                             web3Node.web3.toBytes(hexstr=item['data']))
        dataWanted = {}
        dataWanted['subcourtID'] = decodedData[0]
        dataWanted['setStake'] = float(decodedData[1]/1e18)
        dataWanted['newTotalStake'] = float(decodedData[2]/1e18)
        dataWanted['address'] = cls.topic_to_address(item['topics'][1])
        dataWanted['blockNumber'] = cls.web3.toInt(hexstr=item['blockNumber'])
        dataWanted['timestamp'] = datetime.utcfromtimestamp(cls.web3.toInt(hexstr=item['timeStamp']))
        return dataWanted


    def parseDisputeEvent(self, item):
        dataWanted = {}
        dataWanted['disputeID'] = web3Node.web3.toInt(hexstr=item['topics'][1])
        dataWanted['creator'] = self.topic_to_address(item['topics'][2])
        dataWanted['blockNumber'] = self.web3.toInt(hexstr=item['blockNumber'])
        dataWanted['timestamp'] = datetime.utcfromtimestamp(self.web3.toInt(hexstr=item['timeStamp']))
        dataWanted['txid'] = item['transactionHash']
        
        detailedData = self.dispute_data(dataWanted['disputeID'])
        rounds = {'rounds':self.dispute_rounds(dataWanted['disputeID'])}
        
        return {**dataWanted, **detailedData, **rounds}


    def dispute_data(self, dispute_id):
        """
        This function was made by Marc Zeller
        https://github.com/marczeller/Kleros-Monitor-Bot
        """
        raw_dispute = self.contract.functions.disputes(dispute_id).call()
        ruling = self.contract.functions.currentRuling(dispute_id).call()
        current_status = self.contract.functions.disputeStatus(dispute_id).call()
        return {
            'subcourtID': int(raw_dispute[0]),
            'arbitrated': raw_dispute[1],
            'number_of_choices': int(raw_dispute[2]),
            'period': disputePeriods[int(raw_dispute[3])],
            'last_period_change': datetime.utcfromtimestamp(int(raw_dispute[4])),
            'draws_in_round': int(raw_dispute[5]),
            'commits_in_round': int(raw_dispute[6]),
            'ruled': bool(raw_dispute[7]),
            'ruling': ruling,
            'current_status': current_status
        }


    def dispute_rounds(self, dispute_id):
        """
        This function was made by Marc Zeller
        https://github.com/marczeller/Kleros-Monitor-Bot
        """
        rounds_raw_data = self.contract.functions.getDispute(dispute_id).call()
        rounds = []
        for i in range(0, len(rounds_raw_data[0])):
            rounds.append({
                'jury_size': rounds_raw_data[0][i],
                'tokens_at_stake_per_juror': rounds_raw_data[1][i] / 10**18,
                'total_fees': rounds_raw_data[2][i]/ 10**18,
                'votes': rounds_raw_data[3][i],
                'repartition': rounds_raw_data[4][i],
                'penalties': rounds_raw_data[5][i] / 10**18
            })
        return rounds


    @staticmethod
    def topic_to_address(topic):
        # TODO: Seach for a better way to do this.
        if topic.startswith('0x'):
            topic = topic[2:]
        while topic.startswith('00'):
            topic = topic[2:]
        address = '0x'+topic
        #print(address)
        if web3Node.web3.isAddress(address):
            return address
        else:
            raise Exception("Error in the address")


    def getStakes(self):
        logger.info("Start of the updating process in the Disputes DB")
        filename = os.path.join(DATA_PATH,'setStakesLogs.csv')
        try:
            df = pd.read_csv(filename, index_col=0)
            fromblock = df.blockNumber.max() + 1
        except:
            fromblock = None
            df = pd.DataFrame()
        allItems = self.getEventFromTo(fromblock=fromblock, 
                                       event='stake')
        if len(allItems) > 0:
            newData = pd.DataFrame(allItems)
            df = pd.concat([df, newData]).reset_index(drop=True)
            df['subcourtLabel'] = df['subcourtID'].map(courtNames, na_action='ignore')
            # if there is some duplicates
            df.drop_duplicates(keep='last',
                               inplace=True)
            df.to_csv(filename)
        logger.info('The Stakes Database was updated')
        return df

    
    def getDisputes(self):
        logger.info("Start of the updating process in the Disputes DB")
        filename = os.path.join(DATA_PATH,'createDisputesLogs.csv')
        try:
            df = pd.read_csv(filename, index_col=0)
            fromblock = df.blockNumber.max() + 1
        except:
            fromblock = None
            df = pd.DataFrame()
        allItems = self.getEventFromTo(fromblock=fromblock, 
                                       event='dispute')
        if len(allItems) > 0:
            newData = pd.DataFrame(allItems)
            newData['subcourtLabel'] = newData['subcourtID'].map(courtNames, na_action='ignore')
            df = pd.concat([df, newData]).reset_index(drop=True)
            df.to_csv(filename)
        logger.info('The Disputes Database was updated')
        return df
        
    def updateDB(self):
        self.getDisputes()
        self.getStakes()
        with open(os.path.join(DATA_PATH,'last_update.json'), 'w') as fp:
            json.dump({'last_update':datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, fp)
        logger.info("Updated last_update field")
        with open(os.path.join(DATA_PATH,'PNKSupply.json'), 'w') as fp:
            json.dump({'tokenSupply':self.getTokenSupply()}, fp)
        logger.info("Updated tokenSupply field")
        
            
    @staticmethod
    def getLastUpdate():
        return json.load(open(os.path.join(DATA_PATH,'last_update.json'),'r'))['last_update']


# class StakesKleros(Etherscan, web3Node):
class StakesKleros():
    data = pd.DataFrame()
    jurors = pd.DataFrame()
    
    def __init__(self):
        self.loadCSV()
    
    def loadCSV(self):
        filename=os.path.join(DATA_PATH,'setStakesLogs.csv')
        df = pd.read_csv(filename, index_col=0)
        df.timestamp = pd.to_datetime(df.timestamp)
        df.set_index('timestamp', inplace=True)
        self.data = df
        # filter to get the last stake by court of each juror.
        # self.data = df[~df.duplicated(subset=['address', 'subcourtID'], keep='last')]
        return self.data
        
    @staticmethod
    def dataToCSV(data, filename='setStakesLogs.csv'):
        df = data.copy()
        filename = os.path.join(DATA_PATH,filename)
        if isinstance(df.index, pd.DatetimeIndex):
            df.index.set_names(['timestamp'], inplace=True)
            df.reset_index(inplace=True)
        df.to_csv(filename)
        return df

    @classmethod
    def getAllJurors(cls):
        if cls.data.empty:
            cls.loadCSV(cls)
        cls.allJurors = pd.DataFrame()
        for court in range(len(courtNames)):
            jurors = cls.getJurorsByCourt(court)
            jurors.name = court
            cls.allJurors = pd.concat([cls.allJurors, jurors],axis=1)
        cls.allJurors['Total'] = cls.allJurors.sum(axis=1)
        return cls.allJurors.fillna(0)

    @classmethod
    def getJurorsByCourt(cls, courtID):
        if cls.data.empty:
            cls.loadCSV(cls)
        df = cls.data.copy()
        df_nonZero = df.loc[df.subcourtID == courtID]
        jurors = df_nonZero.groupby('address')['setStake'].last()
        jurors = jurors.sort_values(ascending=False)
        return jurors

    @classmethod
    def getstakedByAddress(cls, address):
        if cls.data.empty:
            cls.loadCSV(cls)
        df_nonZero = cls.data.loc[(cls.data.address==address.lower())]
        jurors = df_nonZero.groupby('subcourtID')[['setStake','subcourtLabel']].last()
        jurors = jurors.sort_values(by='subcourtID',ascending=False)
        return jurors

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
        for court in courts:
            jurors = cls.getJurorsByCourt(court)
            totalInCourts.append({'courtID': court,
                                  'totalstaked': cls.totalStakedByCourt(int(court)),
                                  'courtLabel': courtNames[court],
                                  'n_Jurors': jurors.loc[jurors>0].count(),
                                  'meanStake': jurors.loc[jurors>0].mean(),
                                  'maxStake': jurors.loc[jurors>0].max()})
        df = pd.DataFrame(totalInCourts)
        df = df.fillna(0)
        cls.dataToCSV(df, 
                      os.path.join(DATA_PATH, 'StakedInCourts.csv'))
        return df
    
    @staticmethod
    def getstakedInCourts():
        filename = os.path.join(DATA_PATH, 'StakedInCourts.csv')
        df = pd.read_csv(filename, index_col=0)
        df.set_index('courtID', inplace=True)
        return df

    @staticmethod
    def readHistoric(filename):
        filename = os.path.join(DATA_PATH, filename)
        df = pd.read_csv(filename, index_col=0)
        df.timestamp = pd.to_datetime(df.timestamp)
        df.set_index('timestamp', inplace=True)
        df.index = pd.to_datetime(df.index)
        return df
        
    @classmethod
    def historicStakesInCourts(cls):
        return cls.readHistoric('historicStakes.csv')   
    
    @classmethod
    def historicJurorsInCourts(cls):
        return cls.readHistoric('historicJurors.csv')

    def calculateHistoricStakesInCourts(self, freq = 'D'):
        if self.data.empty:
            self.loadCSV()
        df = self.data.copy()
        # df.timestamp = pd.to_datetime(df.timestamp)
        # df.set_index('timestamp', inplace=True)
        start = min(df.index)
        end = max(df.index)
        # end = datetime(2019, 4, 30)
        rango = pd.date_range(start=start, end=end, freq=freq)
        data = pd.DataFrame(columns = [i for i in range(len(courtNames))])
        for end in rango:
            dff = df[(df.index >= start) & (df.index <= end)].copy()
            dff = dff[~dff.duplicated(subset=['address', 'subcourtID'], keep='last')]
            dff = dff.groupby('subcourtID')['setStake'].sum()
            data.loc[end] = dff
        data = data.fillna(0)
        self.dataToCSV(data, 
                      os.path.join(DATA_PATH, 'historicStakes.csv'))
        return data

    def calculateHistoricJurorsInCourts(self, freq = 'D'):
        if self.data.empty:
            self.loadCSV()
        df = self.data.copy()
        start = min(df.index)
        end = max(df.index)
        rango = pd.date_range(start=start, end=end, freq=freq)
        data = pd.DataFrame(columns = [i for i in range(len(courtNames))])
        for end in rango:
            dff = df[(df.index >= start) & (df.index <= end)].copy()
            dff = dff[~dff.duplicated(subset=['address', 'subcourtID'], keep='last')]
            dff = dff[dff.setStake > 0]
            dff = dff.groupby('subcourtID')['address'].count()
            data.loc[end] = dff
        data.fillna(0, inplace=True)
        self.dataToCSV(data,
                      os.path.join(DATA_PATH,'historicJurors.csv'))
        return data

    @classmethod
    def stakedInCourts(cls):
        if cls.data.empty:
            cls.loadCSV(cls)
        df = cls.data.copy()
        df = df[~df.duplicated(subset=['address', 'subcourtID'], keep='last')]
        df = df.groupby('subcourtID')['setStake'].sum()
        return df

    @classmethod
    def stakedByCourt(cls, court):
        df = cls.stakedInCourts()
        return df[court]

    @classmethod
    def totalStakedByCourt(cls, court):
        childs = KlerosLiquid().getAllCourtChilds(court)
        total = cls.stakedByCourt(court)
        for child in childs:
            total += cls.stakedByCourt(child)
        return total
    
    @classmethod
    def getJurors(cls, court):
        if cls.data.empty:
            cls.loadCSV(cls)
        df = cls.data.copy()
        df = df[~df.duplicated(subset=['address', 'subcourtID'], keep='last')]
        return df
    
    @staticmethod
    def chanceCalculator(amountStaked, totalStaked, nJurors = 3):
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
            
        
class DisputesEvents():
    
    def __init__(self):
        self.data = self.loadCSV()

    def loadCSV(self):
        filename=os.path.join(DATA_PATH,'createDisputesLogs.csv')
        df = pd.read_csv(filename, converters={'rounds': literal_eval}, index_col=0)
        df.timestamp = pd.to_datetime(df.timestamp)
        self.data = df.set_index('timestamp')
        return self.data
    
    def historicDisputes(self):
        df = self.data.copy()
        df = df['disputeID']
        return df
    
    def historicRounds(self):
        df = self.data.copy()
        df['nRounds'] = df.rounds.apply(len)
        df['nRounds_cum'] = df.nRounds.cumsum()
        return df
    
    def mostLongCases(self):
        df = self.data.copy()
        df['nRounds'] = df.rounds.apply(len)
        df = df[df['nRounds'] == max(df['nRounds'])]
        return df[['disputeID', 'nRounds', 'subcourtID']].to_dict('records')
    
    def historicDisputesbyCourt(self, court):
        df = self.data.copy()
        df = df[df.subcourtID == court]
        df.reset_index(inplace=True)
        df.index.rename('count', inplace=True)
        df.reset_index(inplace=True)
        df = df[['timestamp', 'count', 'disputeID']]
        df.set_index('timestamp', inplace=True)
        return df
    
    def historicJurorsDrawn(self):
        """
        Return the amount of jurors drawn by dispute and dates
        """
        df = self.data.copy()
        df['n_jurors'] = df.rounds.apply(lambda x: sum([r['jury_size'] for r in x]))
        df['n_jurors_cum'] = df.n_jurors.cumsum()
        return df[['n_jurors','n_jurors_cum', 'disputeID']]
    
    def historicJurorsDrawnByCourt(self, court):
        df = self.data[self.data.subcourtID == court].copy()
        df['n_jurors'] = df.rounds.apply(lambda x: sum([r['jury_size'] for r in x]))
        df['n_jurors_cum'] = df.n_jurors.cumsum()
        return df[['n_jurors','n_jurors_cum', 'disputeID']]
    
    def ruledCases(self):
        df = self.data.copy()
        not_ruled = df[df.ruled == False].ruled.count()
        ruled = df[df.ruled == True].ruled.count()
        return {'ruled':ruled,
                'not_ruled':not_ruled}
    
    def mostActiveCourt(self):
        df = self.data.copy()
        oneweekbefore = datetime.today() - timedelta(days=7)
        df = df[df.index >= oneweekbefore]
        dfgrouped = df.groupby('subcourtLabel')['disputeID'].count()
        dfgrouped = dfgrouped[dfgrouped==max(dfgrouped)].to_dict()
        if len(dfgrouped) == 0:
            return "There were no cases this week"
        elif len(dfgrouped) == 2:
            courts = list(dfgrouped.keys())
            cases = list(dfgrouped.values())
            return 'There is a tie between {} and {} at {} cases'.format(courts[0], courts[1], cases[0])
        elif len(dfgrouped) > 2:
            item = dfgrouped.popitem()
            return "{} Court with {} cases. There are more courts with the same amount".format(item[0], item[1])
        else:
            item = dfgrouped.popitem()
            return "{} Court with {} cases".format(item[0], item[1])