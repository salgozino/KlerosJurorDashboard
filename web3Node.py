# -*- coding: utf-8 -*-
"""
"""
from web3 import Web3
import json
import os
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

             
class web3Node():
    try:
        infura_node = os.environ['INFURA_NODE']
    except:
        print("NO OS ETHERSCAN_KEY VARIABLE FOUND")
        infura_node = json.load(open(os.path.join(THIS_FOLDER,'static/lib/infura_node.json'),'r'))['http']
    web3 = Web3(Web3.HTTPProvider(infura_node))
    
    @classmethod
    def getTransaction(cls, tx_hash):
        return cls.web3.eth.getTransaction(tx_hash)

class Contract(Web3):
    def __init__(self, address, abi, node_url):
        self.web3 = Web3(Web3.HTTPProvider(node_url))
        self.contract = self.web3.eth.contract(abi=abi,
                                                address=address)