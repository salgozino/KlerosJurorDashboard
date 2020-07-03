# -*- coding: utf-8 -*-
"""
Script  clonned from https://github.com/marczeller/Kleros-Monitor-Bot
"""
import requests
import urllib
import json

import os
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
UPPER_FOLDER = os.path.split(THIS_FOLDER)[0]

class Etherscan():

    api_url = "https://api.etherscan.io/api?"
    try:
        api_key = os.environ['ETHERSCAN_KEY']
    except:
        print("NO OS ETHERSCAN_KEY VARIABLE FOUND")
        api_key = json.load(open(os.path.join(UPPER_FOLDER,'lib/etherscan_api_key.json'),'r'))['api_key']


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
            if item['isError'] != '1' and item['to'] == address : filtered_items.append(item)
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