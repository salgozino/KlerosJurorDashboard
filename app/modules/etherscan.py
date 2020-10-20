# -*- coding: utf-8 -*-
"""
Script  clonned from https://github.com/marczeller/Kleros-Monitor-Bot
"""
import requests
import urllib
import json
from .web3Node import web3Node
import os


class Etherscan(web3Node):
    api_url = "https://api.etherscan.io/api?"
    try:
        api_key = os.environ['ETHERSCAN_KEY']
    except KeyError:
        print("NO OS ETHERSCAN_KEY VARIABLE FOUND")
        api_key = json.load(open('app/lib/etherscan_api_key.json', 'r'))['api_key']

    @classmethod
    def deposits(cls, address):

        api_options = {
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 7303600,
            'endblock': 'latest',
            'sort': 'asc',
            'apikey': cls.api_key
        }

        deposits_url = cls.api_url + urllib.parse.urlencode(api_options)
        response = requests.get(deposits_url)
        get_json = response.json()
        items = get_json['result']
        filtered_items = []
        for item in items:
            if item['isError'] != '1' and item['to'] == address:
                filtered_items.append(item)
        return filtered_items

    @classmethod
    def getContractName(cls, address):
        api_options = {
            'module': 'contract',
            'action': 'getsourcecode',
            'address': address,
            'apikey': cls.api_key
        }
        url = cls.api_url + urllib.parse.urlencode(api_options)
        response = requests.get(url).json()

        return response['result'][0]['ContractName']

    def getEventFromTo(self, contract_address, topic, fromblock=None, endblock=None):
        if fromblock is None:
            fromblock = 7315700
        if endblock is None:
            endblock = self.web3.eth.blockNumber
        # if endblock is None: endblock = 7324000
        step = 1000
        toblock = fromblock + step
        if endblock <= toblock:
            endblock = toblock + 1
        allItems = []
        while toblock < endblock:
            # print('etherscan:', fromblock, '-',toblock)
            api_options = {
                'module': 'logs',
                'action': 'getLogs',
                'fromBlock': fromblock,
                'toBlock': toblock,
                'address': contract_address,
                'topic0': topic,
                'apikey': self.api_key
                }

            url = self.api_url + urllib.parse.urlencode(api_options)
            response = requests.get(url)
            get_json = response.json()

            items = get_json['result']
            allItems += items
            fromblock = toblock + 1
            toblock = fromblock + step
        return allItems


class CMC():
    """
    Class for interaction with CoinMarketCap and get the ETH and PNK prices.
    """

    def __init__(self):
        self.api_url = "http://pro-api.coinmarketcap.com/v1/cryptocurrency/"
        try:
            self.api_key = os.environ['CMC_KEY']
        except KeyError:
            print("NO OS CMC_KEY VARIABLE FOUND")
            self.api_key = json.load(open('app/lib/coinmarketcap.json', 'r'))['api_key']

    def getCryptoInfo(self, id=3581):
        parameters = {'id': id}
        headers = {
          'Accepts': 'application/json',
          'Accept-Enconding': 'deflate, gzip',
          'X-CMC_PRO_API_KEY': self.api_key,
        }
        url = self.api_url + 'quotes/latest?' + urllib.parse.urlencode(parameters)
        response = requests.get(url, headers=headers)
        return response.json()['data'][str(id)]

    def getPNKprice(self):
        pnkId = 3581
        response = self.getCryptoInfo(id=pnkId)
        return response['quote']['USD']['price']

    def getETHprice(self):
        ethId = 1027
        response = self.getCryptoInfo(id=ethId)
        return response['quote']['USD']['price']

    def cryptoMap(self):
        headers = {
          'Accepts': 'application/json',
          'Accept-Enconding': 'deflate, gzip',
          'X-CMC_PRO_API_KEY': self.api_key,
        }
        url = self.api_url + 'map'
        response = requests.get(url, headers=headers)
        return response.json()


class CoinGecko():
    """
    Class for interaction with CoinGecko API and get the ETH and PNK prices.
    """

    def __init__(self):
        self.api_url = "https://api.coingecko.com/api/v3/"

    def getCryptoInfo(self, id="kleros"):
        parameters = {'localization': False,
                      'tickers': False,
                      'market_data': True,
                      'community_data': False,
                      'developer_data': False,
                      'sparkline': False}
        headers = {
          'Accepts': 'application/json',
        }
        url = self.api_url + 'coins/{}?'.format(id) + urllib.parse.urlencode(parameters)
        response = requests.get(url, headers=headers)
        return response.json()

    def getPNKprice(self):
        pnkId = "kleros"
        response = self.getCryptoInfo(id=pnkId)
        return response['market_data']['current_price']['usd']

    def getETHprice(self):
        ethId = "ethereum"
        response = self.getCryptoInfo(id=ethId)
        return response['market_data']['current_price']['usd']
