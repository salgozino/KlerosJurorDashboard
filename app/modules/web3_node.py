# -*- coding: utf-8 -*-
"""web3_node
Module to create the web3 connection with the Node.
It's tested with infura node, I've no performed any other connection, but should
work with other node types, I guess.
"""
import json
import os

from web3 import Web3


class web3Node():
    try:
        infura_node = os.environ['INFURA_NODE']
    except KeyError:
        print("NO OS INFURA_NODE VARIABLE FOUND")
        infura_node = json.load(open('app/lib/infura_node.json', 'r'))['http']
    web3 = Web3(Web3.HTTPProvider(infura_node))

    @classmethod
    def getTransaction(cls, tx_hash):
        return cls.web3.eth.getTransaction(tx_hash)


class SmartContract(web3Node):
    def __init__(self, address, abi):
        self.contract = self.web3.eth.contract(abi=abi,
                                               address=address)