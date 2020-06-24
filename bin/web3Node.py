# -*- coding: utf-8 -*-
"""
"""
from web3 import Web3
import json
import os
import os, sys
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
UPPER_FOLDER = os.path.split(THIS_FOLDER)[0]

             
class web3Node():
    try:
        infura_node = os.environ['INFURA_NODE']
    except:
        print("NO OS ETHERSCAN_KEY VARIABLE FOUND")
        infura_node = json.load(open(os.path.join(UPPER_FOLDER,'lib/infura_node.json'),'r'))['http']
        # infura_node = json.load(open(os.path.join(UPPER_FOLDER,'lib/infura_node.json'),'r'))['wss']
    web3 = Web3(Web3.HTTPProvider(infura_node))
    # web3 = Web3(Web3.WebsocketProvider(infura_node))
    
    @classmethod
    def getTransaction(cls, tx_hash):
        return cls.web3.eth.getTransaction(tx_hash)

class Contract(web3Node):
    def __init__(self, address, abi):
        self.contract = self.web3.eth.contract(abi=abi,
                                                address=address)