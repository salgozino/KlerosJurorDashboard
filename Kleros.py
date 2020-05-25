# -*- coding: utf-8 -*-
from etherscan import Etherscan
from web3Node import web3Node, Contract
import pandas as pd
import requests
import urllib
from eth_abi import decode_abi
import json
import os
from datetime import datetime
import logging
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))


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
              8:'Ongoing'}


class KlerosLiquid(Contract, web3Node):


    def __init__(self):
        with open(os.path.join(THIS_FOLDER,'static/lib/ABI_KlerosLiquid.json'),'r') as f:
            contract_abi = json.loads(f.read())['result']
        address = "0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069"
        self.contract = web3Node.web3.eth.contract(abi=contract_abi,
                                                   address=address)

    def getCourtChildrens(self, courtID):
        return self.contract.functions.getSubcourt(courtID).call()[0]


    def getAllChilds(self, courtID):
        childs = set(self.getCourtChildrens(courtID))
        allChilds = []
        while childs:
            child = childs.pop()
            allChilds.append(child)
            childs.update(self.getCourtChildrens(child))
        return allChilds


    def filtering(self,topic):
        print(topic)


class StakesKleros(Etherscan, web3Node):
    data = pd.DataFrame()
    jurors = pd.DataFrame()
    
    setStake_topic = '0x8f753321c98641397daaca5e8abf8881fff1fd7a7bc229924a012e2cb61763d5'
    
    
    @classmethod
    def loadCSV(cls, filename=os.path.join(THIS_FOLDER,'static/data/setStakesLogs.csv')):
        df = pd.read_csv(filename, index_col=0)
        df.timestamp = pd.to_datetime(df.timestamp)
        df.set_index('timestamp', inplace=True)
        df.index = pd.to_datetime(df.index)
        # filter to get the last stake by court of each juror.
        cls.data = df[~df.duplicated(subset=['address', 'subcourtID'], keep='last')]
        return cls.data

    @classmethod
    def updateData(cls):
        try:
            cls.loadCSV()
            fromblock = cls.data.blockNumber.max()
        except:
            fromblock = 7303600
            cls.data = pd.DataFrame()
            
        endblock = cls.web3.eth.blockNumber+1

        allItems = cls.getStakesFromTo(fromblock=fromblock, endblock=endblock)
        if len(allItems) > 0:
            newData = pd.DataFrame(allItems).set_index('timestamp')
            cls.data = pd.concat([cls.data, newData])
            cls.data['subcourtLabel'] = cls.data['subcourtID'].map(courtNames)
            cls.data.drop_duplicates(keep='last',inplace=True)
            cls.dataToCSV()
        logger.info('The Stakes Database was updated')
        return cls.data


    @classmethod
    def dataToCSV(cls, filename=os.path.join(THIS_FOLDER,'static/data/setStakesLogs.csv')):
        df = cls.data.copy()
        if isinstance(df.index, pd.DatetimeIndex):
            df.index.set_names(['timestamp'], inplace=True)
            df.reset_index(inplace=True)
        df.to_csv(filename)
        return df


    @classmethod
    def getStakesFromTo(cls, fromblock=None, endblock=None):
        if fromblock is None:
            fromblock = 7303600
        if endblock is None:
            endblock = cls.web3.eth.blockNumber+1
        elif isinstance(endblock, str):
            if endblock == 'latest':
                endblock = cls.web3.eth.blockNumber+1

        toblock = fromblock + 5000
        step = 10000
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
                'address':"0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069",
                'topic0':cls.setStake_topic,
                'apikey': cls.api_key
                }
    
            setStake_url = cls.api_url + urllib.parse.urlencode(api_options)
            response = requests.get(setStake_url)
            get_json = response.json()
            
            items = get_json['result']
            if len(items) == 1000:
                print("Ups!, maybe there are missed items, slow down the iterations")
                toblock = fromblock + round(step/3)
                continue

            for item in items:
                try:
                    decodedData = decode_abi(('uint96','uint128','int256'),
                                             web3Node.web3.toBytes(hexstr=item['data']))
                    dataWanted = {}
                    dataWanted['subcourtID'] = decodedData[0]
                    dataWanted['setStake'] = float(decodedData[1]/1e18)
                    dataWanted['newTotalStake'] = float(decodedData[2]/1e18)
                    dataWanted['address'] = cls.topic_to_address(item['topics'][1])
                    dataWanted['blockNumber'] = cls.web3.toInt(hexstr=item['blockNumber'])
                    dataWanted['timestamp'] = datetime.utcfromtimestamp(cls.web3.toInt(hexstr=item['timeStamp']))
                    allItems.append(dataWanted)
                except:
                    logger.info("error processing the information. {}".format(item))

            fromblock = toblock + 1
            toblock = fromblock + step
        return allItems


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


    @classmethod
    def plotStatsforCourts(cls):
        raise NotImplementedError('Plot is not implemented')


    @classmethod
    def getAllJurors(cls):
        if cls.data.empty:
            cls.loadCSV()
        cls.allJurors = pd.DataFrame()
        for court in range(len(courtNames)):
            jurors = cls.getJurorsByCourt(court)
            jurors.name = court
            cls.allJurors = pd.concat([cls.allJurors, jurors],axis=1)
        cls.allJurors['Total'] = cls.allJurors.sum(axis=1)
        return cls.allJurors


    @classmethod
    def getJurorsByCourt(cls, courtID):
        if cls.data.empty:
            cls.loadCSV()
        df = cls.data.copy()
        df_nonZero = df.loc[(df.newTotalStake>0) & (df.subcourtID == courtID)]
        df_nonZero = df_nonZero[~df_nonZero.duplicated(subset=['address', 'subcourtID'], keep='last')]
        jurors = df_nonZero.groupby('address')['newTotalStake'].last()
        jurors = jurors.sort_values(ascending=False)
        return jurors


    @classmethod
    def getstakedByAddress(cls, address):
        if cls.data.empty:
            cls.loadCSV()
        df_nonZero = cls.data.loc[(cls.data.address==address.lower())]
        cls.jurors = df_nonZero.groupby('subcourtID')[['newTotalStake','subcourtLabel']].last()
        cls.jurors = cls.jurors.sort_values(by='subcourtID',ascending=False)
        return cls.jurors


    @classmethod
    def getChanceByCourt(cls, courtID, pnkstaked):
        if int(pnkstaked) > 0:
            total = cls.totalStakedByCourt(courtID)
            chance = pnkstaked/total
            print("You have {:.3%} of chances to been drawn".format(
                chance, 
                pnkstaked,
                courtNames[courtID]))
        else:
            chance = 0
        return chance


    @classmethod
    def getChanceByAddress(cls, address):
        stakedInCourts = cls.getstakedByAddress(address).reset_index().values
        chances = []
        for row in stakedInCourts:
            totalstakedInCourt = cls.totalStakedByCourt(row[0])
            chances.append({'courtID':row[0],
                            'courtLabel':row[2],
                            'chance':row[1]/totalstakedInCourt})
        
            
            print("You have {:.3f}% of chances to been drawn in the court {}".format(
                row[1]/totalstakedInCourt*100, 
                row[2]))
        return chances


    @classmethod
    def getstakedInCourts(cls):
        if cls.data.empty:
            cls.loadCSV()
        courts = cls.data.subcourtID.unique()
        totalInCourts = []
        for court in courts:
            jurors = cls.getJurorsByCourt(court)
            totalInCourts.append({'courtID':court,
                                  'totalstaked':cls.totalStakedByCourt(int(court)),
                                  'courtLabel':courtNames[court],
                                  'n_Jurors':jurors.count(),
                                  'meanStack':jurors.mean(),
                                  'maxStack':jurors.max()})
        df = pd.DataFrame(totalInCourts)
        return df


    @classmethod
    def getChanceByAddressAndCourt(cls, address, court):
        # TODO
        raise NotImplementedError("not yet implemented")


    @classmethod
    def historicStakesInCourts(cls, freq = 'D'):
        if cls.data.empty:
            cls.loadCSV()
        df = cls.data.copy()
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
            dff = dff.groupby('subcourtID')['newTotalStake'].sum()
            data.loc[end] = dff
        return data.fillna(0)

    @classmethod
    def historicJurorsInCourts(cls, freq = 'D'):
        if cls.data.empty:
            cls.loadCSV()
        df = cls.data.copy()
        start = min(df.index).replace(hour=0, minute=0, second=0)
        end = max(df.index).replace(hour=23, minute=59, second=59)
        rango = pd.date_range(start=start, end=end, freq=freq)
        data = pd.DataFrame(columns = [i for i in range(len(courtNames))])
        for end in rango:
            dff = df[(df.index >= start) & (df.index <= end)].copy()
            dff = dff[~dff.duplicated(subset=['address', 'subcourtID'], keep='last')]
            dff = dff[dff.newTotalStake > 0]
            dff = dff.groupby('subcourtID')['address'].count()
            data.loc[end] = dff
        return data.fillna(0)


    @classmethod
    def stakedInCourts(cls):
        if cls.data.empty:
            cls.loadCSV()
        df = cls.data.copy()
        df = df[~df.duplicated(subset=['address', 'subcourtID'], keep='last')]
        df = df.groupby('subcourtID')['newTotalStake'].sum()
        return df


    @classmethod
    def stakedByCourt(cls, court):
        df = cls.stakedInCourts()
        return df[court]


    @classmethod
    def totalStakedByCourt(cls, court):
        childs = KlerosLiquid().getAllChilds(court)
        total = cls.stakedByCourt(court)
        for child in childs:
            total += cls.stakedByCourt(child)
        return total
    
    @classmethod
    def getJurors(cls, court):
        if cls.data.empty:
            cls.loadCSV()
        df = cls.data.copy()
        # df.timestamp = pd.to_datetime(df.timestamp)
        # df.set_index('timestamp', inplace=True)
        df = df[~df.duplicated(subset=['address', 'subcourtID'], keep='last')]
        return df
            
        
