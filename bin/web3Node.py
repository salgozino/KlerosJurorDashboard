# -*- coding: utf-8 -*-
"""
"""
from web3 import Web3
import json
import os

             
class web3Node():
    try:
        infura_node = os.environ['INFURA_NODE']
    except:
        print("NO OS INFURA_NODE VARIABLE FOUND")
        infura_node = json.load(open('../lib/infura_node.json','r'))['http']
    web3 = Web3(Web3.HTTPProvider(infura_node))
    
    @classmethod
    def getTransaction(cls, tx_hash):
        return cls.web3.eth.getTransaction(tx_hash)

class SmartContract(web3Node):
    def __init__(self, address, abi):
        self.contract = self.web3.eth.contract(abi=abi,
                                                address=address)