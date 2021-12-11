import json
import os

from web3 import Web3


class web3Node():
    def __init__(self, network='mainnet'):
        self.network = network
        try:
            if self.network == 'kovan':
                infura_node = os.environ['INFURA_NODE_kovan']
            else:
                infura_node = os.environ['INFURA_NODE']
        except KeyError:
            print("NO OS INFURA_NODE VARIABLE FOUND")
            infura_node = json.load(open('app/lib/infura_node.json', 'r'))['http']
        self.web3 = Web3(Web3.HTTPProvider(infura_node))

    @classmethod
    def getTransaction(cls, tx_hash):
        return cls.web3.eth.getTransaction(tx_hash)

    def wei2eth(self, amount):
        return self.web3.fromWei(amount, 'ether')


class SmartContract(web3Node):
    def __init__(self, address, abi):
        self.contract = self.web3.eth.contract(abi=abi,
                                               address=address)


class KBSubscription(SmartContract):
    def __init__(self):
        # TODO: KOVAN ADDRESS!, this has to be changed
        self.abi = json.load(open('app/static/ABI/KlerosboardSuscription.json',
                                  'r'))
        super(KBSubscription, self).__init__(
            self.web3.toChecksumAddress(
                "0x9313F75F4C49a57D1D0158232C526e24Bb40f281".lower()),
            self.abi)

    @property
    def donationPerMont(self):
        return self.contract.functions.donationPerMonth().call()
