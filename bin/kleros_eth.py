# -*- coding: utf-8 -*-

import json, urllib, requests
from eth_abi import decode_abi
from datetime import datetime
import logging
from bin.etherscan import Etherscan
from bin.KlerosDB import Config, JurorStake, Dispute, Vote, Round
from bin import db

FORMAT = '%(asctime)-15s - %(message)s'
logging.basicConfig(format=FORMAT, filename='log.log', level='INFO')
logger = logging.getLogger()

class KlerosLiquid(Etherscan):
    stakes_event_topic = "0x8f753321c98641397daaca5e8abf8881fff1fd7a7bc229924a012e2cb61763d5"
    create_dispute_event_topic = "0x141dfc18aa6a56fc816f44f0e9e2f1ebc92b15ab167770e17db5b084c10ed995"
    address = "0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069"
    with open('lib/ABI_KlerosLiquid.json','r') as f:
            abi = json.loads(f.read())['result']

    def __init__(self, initial_block = None):
        self.contract = self.web3.eth.contract(abi=self.abi,
                                               address=self.address)
        try:
            self.tokenSupply = self.getTokenSupply()
        except Exception as e:
            logger.error('Error getting the Token Supply at %s', 'division', exc_info=e)
            self.tokenSupply = 0

        if initial_block:
            self.initial_block = initial_block
        else:
            self.initial_block = 7315700

    @classmethod
    def getTokenSupply(cls):
        api_options = {
                'module':'stats',
                'action':'tokensupply',
                'contractaddress':'0x93ed3fbe21207ec2e8f2d3c3de6e058cb73bc04d',
                'apikey': cls.api_key
                }
        url = cls.api_url + urllib.parse.urlencode(api_options)
        response = requests.get(url)
        get_json = response.json()
        if get_json['status']:
            tokenSupply = float(get_json['result'])/10**18
        else:
            raise "Error trying to get the token supply" + get_json['message']
        return tokenSupply

    def vote(self, dispute_id, round, vote_id):
        raw_vote = self.contract.functions.getVote(dispute_id, round, vote_id).call()
        return {
            'address': raw_vote[0],
            'commit': raw_vote[1].hex(),
            'choice': int(raw_vote[2]),
            'vote': bool(raw_vote[3])
        }

    @classmethod
    def topic_to_address(cls, topic):
        # TODO: Seach for a better way to do this.
        if topic.startswith('0x'):
            topic = topic[2:]
        while topic.startswith('00') and len(topic)>40:
            topic = topic[2:]
        address = '0x'+topic
        #print(address)
        if cls.web3.isAddress(address):
            return address
        else:
            raise Exception("Error in the address")

    @classmethod
    def parseStakesEvent(cls, item):
        decodedData = decode_abi(('uint96','uint128','int256'),
                                 cls.web3.toBytes(hexstr=item['data']))
        dataWanted = {}
        dataWanted['subcourtID'] = decodedData[0]
        dataWanted['setStake'] = float(decodedData[1]/1e18)
        dataWanted['txid'] = item['transactionHash']
        dataWanted['address'] = cls.topic_to_address(item['topics'][1])
        dataWanted['blockNumber'] = cls.web3.toInt(hexstr=item['blockNumber'])
        dataWanted['timestamp'] = datetime.utcfromtimestamp(cls.web3.toInt(hexstr=item['timeStamp']))
        return dataWanted

    def getStakes(self):
        logger.info("Start of the updating process in the Stakes DB")
        try:
            fromblock = int(Config.get('staking_search_block'))
        except:
            fromblock = self.initial_block
        step = 1000
        endblock = fromblock + step
        allItems = []
        while endblock < self.web3.eth.blockNumber+step-1:
            logger.debug(f"{fromblock} - {endblock}")
            items = self.getEventFromTo(fromblock=fromblock,
                                           contract_address=self.address,
                                           topic=self.stakes_event_topic,
                                           endblock= endblock)
            
            if len(items) > 0:
                for item in items:
                    try:
                        stake = self.parseStakesEvent(item)
                        staking = JurorStake(address = stake['address'],
                                             subcourtID = stake['subcourtID'],
                                             timestamp = stake['timestamp'],
                                             setStake = stake['setStake'],
                                             txid = stake['txid'],
                                             blocknumber = stake['blockNumber'])
                        db.session.add(staking)
                    except Exception as e:
                        logger.error("Error trying to add a Stake into the database")
                        logger.error(e)
                        logger.error(item)
                        
                db.session.commit()
            fromblock = endblock + 1
            endblock = fromblock + step
            allItems += items
            Config.set('staking_search_block', stake['blockNumber'])
            db.session.commit()
            
        logger.info('The Stakes Database was updated')
        return allItems

    
    def parseDisputeEvent(self, item):
        dataWanted = {}
        dataWanted['disputeID'] = self.web3.toInt(hexstr=item['topics'][1])
        dataWanted['creator'] = self.topic_to_address(item['topics'][2])
        dataWanted['blockNumber'] = self.web3.toInt(hexstr=item['blockNumber'])
        dataWanted['timestamp'] = datetime.utcfromtimestamp(self.web3.toInt(hexstr=item['timeStamp']))
        dataWanted['txid'] = item['transactionHash']
        disputeData = self.dispute_data(dataWanted['disputeID'])
        
        return {**dataWanted, **disputeData}


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
            'period': int(raw_dispute[3]),
            'last_period_change': datetime.utcfromtimestamp(int(raw_dispute[4])),
            'draws_in_round': int(raw_dispute[5]),
            'commits_in_round': int(raw_dispute[6]),
            'ruled': bool(raw_dispute[7]),
            'ruling': ruling,
            'current_status': current_status,
        }


    def dispute_rounds(self, dispute_id):
        """
        This function was made by Marc Zeller
        https://github.com/marczeller/Kleros-Monitor-Bot
        """
        rounds_raw_data = self.contract.functions.getDispute(dispute_id).call()
        rounds = []
        for i in range(0, len(rounds_raw_data[0])):
            juror_size = rounds_raw_data[0][i]
            jurors_info = []
            for j in range(0, juror_size):
                # Get juror address and vote.
                # getVote of dispute, round, vote_ID
                juror_info = self.contract.functions.getVote(dispute_id, i, j).call()
                jurors_info.append({'address':juror_info[0],
                                  'commit':self.web3.toInt(juror_info[1]),
                                  'choice':juror_info[2],
                                  'voted':juror_info[3]})
            rounds.append({
                'jury_size': juror_size,
                'tokens_at_stake_per_juror': rounds_raw_data[1][i] / 10**18,
                'total_fees': rounds_raw_data[2][i]/ 10**18,
                'votes': rounds_raw_data[3][i],
                'repartition': rounds_raw_data[4][i],
                'penalties': rounds_raw_data[5][i] / 10**18,
                'jurors':jurors_info,
            })
        return rounds

    def getDisputes(self):
        logger.info("Start of the updating process in the Disputes DB")
        try:
            fromblock = int(Config.get('dispute_search_block'))+1
        except:
            fromblock = self.initial_block    
        step = 1000
        endblock = fromblock + step
        allItems = []
        while endblock < self.web3.eth.blockNumber+step-1:
            # print(f"{fromblock} - {endblock}")
            items = self.getEventFromTo(fromblock=fromblock,
                                        contract_address=self.address,
                                        topic=self.create_dispute_event_topic,
                                        endblock=endblock)
            if len(items):
                for item in items:
                    self.create_dispute(self.parseDisputeEvent(item))
            fromblock = endblock + 1
            endblock = fromblock + step
            allItems += items
        return allItems


    def create_dispute(self, dispute_eth):
        found_open_dispute = False
        logger.info("Creating dispute %s" % dispute_eth['disputeID'])
        # search if the dispute already exist
        dispute = Dispute.query.get(dispute_eth['disputeID'])
        logger.info(f"Dispute {dispute}")
        if dispute != None:
            if dispute.ruled:
                # if this dispute is already ruled, don't need to do anything
                return
            # delete current dispute, and create the new one with new information
            logger.info(f"Deleting the old Dispute {dispute_eth['disputeID']}")
            dispute.delete_recursive()
        print("Creating dispute %s" % dispute_eth['disputeID'])
        try:
            dispute = Dispute(
                id = dispute_eth['disputeID'],
                creator = dispute_eth['creator'],
                timestamp = dispute_eth['timestamp'],
                txid = dispute_eth['txid'],
                ruled = dispute_eth['ruled'],
                subcourtID = dispute_eth['subcourtID'],
                current_ruling = dispute_eth['ruling'],
                period = dispute_eth['period'],
                last_period_change = dispute_eth['last_period_change'],
                blocknumber = dispute_eth['blockNumber'],
                arbitrated = dispute_eth['arbitrated'],
                status = dispute_eth['current_status'],
                number_of_choices = dispute_eth['number_of_choices']
            )
            # Fix for the case n° 149
            if dispute.number_of_choices > 100:
                logger.error(f"Changing the number_of_choices from the dispute {dispute.id} to 2 because is greater than 100")
                dispute.number_of_choices = 2
        
            db.session.add(dispute)
            db.session.commit()


            rounds = self.dispute_rounds(dispute_eth['disputeID'])
        
            for round_num in range(0, len(rounds)):
                round_eth = rounds[round_num]
        
                round = Round(
                    disputeID = dispute_eth['disputeID'],
                    round_num = round_num,
                    draws_in_round = round_eth['jury_size'],
                    tokens_at_stake_per_juror = round_eth['tokens_at_stake_per_juror'],
                    total_fees_for_jurors = round_eth['total_fees'],
                    commits_in_round = round_eth['votes'],
                    repartitions_in_each_round = round_eth['repartition'],
                    penalties_in_each_round = round_eth['penalties'],
                    subcourtID = dispute_eth['subcourtID']
                )
        
                db.session.add(round)
                db.session.commit()
        
                for vote_num in range(0, round.draws_in_round):
                    vote_eth = self.vote(dispute_eth['disputeID'], round_num, vote_num)
        
                    vote = Vote(
                        round_id = round.id,
                        account = vote_eth['address'],
                        commit = vote_eth['commit'],
                        choice = vote_eth['choice'],
                        vote = vote_eth['vote']
                    )
        
                    db.session.add(vote)
                    db.session.commit()
            if int(dispute_eth['disputeID']) not in (105,107,108): # Broken cases
                if(not dispute_eth['ruled']):
                    found_open_dispute = True
            if not found_open_dispute:
                Config.set('dispute_search_block', dispute_eth['blockNumber'] - 1)
            db.session.commit()
        except Exception as e:
            logger.error("Error trying to add a Dispute into the database")
            logger.error(e)
            logger.error(dispute_eth)

    def courtInfo(self, courtID):
        courtData = self.contract.functions.courts(courtID).call()
        return {'parent':None if courtData[0] == courtID else courtData[0],
                'hiddenVotes':courtData[1],
                'minStake':courtData[2]/10**18,
                'alpha':courtData[3],
                'feeForJuror':courtData[4]/10**18,
                'jurorsForCourtJump':courtData[5],
                'votesStake': (courtData[2]/10**18) * (courtData[3]/10**4)}
        
    def mapCourtNames(self, courtID):
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
        try:
            return courtNames[courtID]
        except:
            logger.error(f"Could not found the Court ID {courtID}")
            return "Unknown"