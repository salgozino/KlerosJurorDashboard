# -*- coding: utf-8 -*-
"""
Script  clonned from https://github.com/marczeller/Kleros-Monitor-Bot
"""
import requests
import urllib
import json
from .web3_node import web3Node
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


