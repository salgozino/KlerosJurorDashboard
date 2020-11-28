# -*- coding: utf-8 -*-
"""
En este modulo se define la Clase KlerosLiquid la cual genera la conexió con el
contrato inteligente KlerosLiquid de Kleros, donde se concentra toda la
información de las distintas cortes y stakes de los jurados.
Tambien se define PolicyRegistry para poder obtener la metadata de las cortes.
"""

import json
import urllib
import requests
from datetime import datetime
import logging

from eth_abi import decode_abi

from app.modules import db
from .etherscan import Etherscan
from .web3_node import SmartContract
from .kleros_db import Config, JurorStake, Dispute, Vote, Round


logger = logging.getLogger(__name__)


class KlerosLiquid(Etherscan):
    stakes_event_topic = "0x8f753321c98641397daaca5e8abf8881fff1fd7a7bc229924a012e2cb61763d5"
    create_dispute_event_topic = "0x141dfc18aa6a56fc816f44f0e9e2f1ebc92b15ab167770e17db5b084c10ed995"
    address = "0x988b3A538b618C7A603e1c11Ab82Cd16dbE28069"
    with open('app/lib/ABI_KlerosLiquid.json', 'r') as f:
        abi = json.loads(f.read())['result']

    def __init__(self, initial_block=None):
        self.contract = self.web3.eth.contract(abi=self.abi,
                                               address=self.address)
        try:
            self.tokenSupply = self.get_token_supply()
        except Exception as e:
            logger.error('Error getting the Token Supply at %s', 'division',
                         exc_info=e)
            self.tokenSupply = 0

        if initial_block:
            self.initial_block = initial_block
        else:
            self.initial_block = 7315700

    @classmethod
    def get_token_supply(cls):
        api_options = {
                'module': 'stats',
                'action': 'tokensupply',
                'contractaddress': '0x93ed3fbe21207ec2e8f2d3c3de6e058cb73bc04d',  # pinakion contract
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
        while topic.startswith('00') and len(topic) > 40:
            topic = topic[2:]
        address = '0x'+topic
        # print(address)
        if cls.web3.isAddress(address):
            return address
        else:
            raise Exception("Error in the address")

    @classmethod
    def parse_stakes_event(cls, item):
        """
        Parser to convert the information from the stake event as cames from
        the smart contract to the format in the data base.

        Parameters
        ----------
        item : dict
            Dict with the event information.

        Returns
        -------
        dict
            Dictionary with more information.
        """
        decodedData = decode_abi(('uint96', 'uint128', 'int256'),
                                 cls.web3.toBytes(hexstr=item['data']))
        dataWanted = {}
        dataWanted['subcourtID'] = decodedData[0]
        dataWanted['setStake'] = float(decodedData[1]/1e18)
        dataWanted['txid'] = item['transactionHash']
        dataWanted['address'] = cls.topic_to_address(item['topics'][1])
        dataWanted['blockNumber'] = cls.web3.toInt(hexstr=item['blockNumber'])
        dataWanted['timestamp'] = datetime.utcfromtimestamp(cls.web3.toInt(hexstr=item['timeStamp']))
        return dataWanted

    def get_stakes(self):
        logger.info("Start of the updating process in the Stakes DB")
        try:
            fromblock = int(Config.get('staking_search_block'))
        except Exception:
            fromblock = self.initial_block
        step = 1000
        endblock = fromblock + step
        allItems = []
        while endblock < self.web3.eth.blockNumber+step-1:
            logger.debug(f"{fromblock} - {endblock}")
            items = self.getEventFromTo(fromblock=fromblock,
                                        contract_address=self.address,
                                        topic=self.stakes_event_topic,
                                        endblock=endblock)

            if len(items) > 0:
                for item in items:
                    try:
                        stake = self.parse_stakes_event(item)
                        staking = JurorStake(address=stake['address'],
                                             subcourtID=stake['subcourtID'],
                                             timestamp=stake['timestamp'],
                                             setStake=stake['setStake'],
                                             txid=stake['txid'],
                                             blocknumber=stake['blockNumber'])
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

    def parse_dispute_event(self, item):
        """
        Parser to convert the information between the dispute item as cames from
        the smart contract to the format in the data base.

        Parameters
        ----------
        item : dict
            Dict with the event information.

        Returns
        -------
        set
            Expanded dictionary with more information.

        """
        dataWanted = {}
        dataWanted['disputeID'] = self.web3.toInt(hexstr=item['topics'][1])
        dataWanted['creator'] = self.web3.eth.getTransaction(transaction_hash=item['transactionHash'])['from']
        dataWanted['blockNumber'] = self.web3.toInt(hexstr=item['blockNumber'])
        dataWanted['timestamp'] = datetime.utcfromtimestamp(self.web3.toInt(hexstr=item['timeStamp']))
        dataWanted['txid'] = item['transactionHash']
        disputeData = self.dispute_data(dataWanted['disputeID'])
        return {**dataWanted, **disputeData}

    def dispute_data(self, dispute_id):
        """
        Ask to the KlerosLiquid smart contract the dispute data with specified
        id.

        Returns a Dict with all the information

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
        Return the rounds information of a dispute from it's id.
        The return object it's a list of dicts, where each dict it's the round
        information.

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
                jurors_info.append({'address': juror_info[0],
                                    'commit': self.web3.toInt(juror_info[1]),
                                    'choice': juror_info[2],
                                    'voted': juror_info[3]})
            rounds.append({
                'jury_size': juror_size,
                'tokens_at_stake_per_juror': rounds_raw_data[1][i] / 10**18,
                'total_fees': rounds_raw_data[2][i]/10**18,
                'votes': rounds_raw_data[3][i],
                'repartition': rounds_raw_data[4][i],
                'penalties': rounds_raw_data[5][i] / 10**18,
                'jurors': jurors_info
            })
        return rounds

    def get_disputes(self):
        try:
            fromblock = int(Config.get('dispute_search_block'))
        except Exception:
            fromblock = self.initial_block
        step = 1000
        endblock = fromblock + step
        allItems = []
        open_dispute_blockNumbers = []

        logger.info(f"Start of the updating process in the Disputes DB from block number {fromblock}")
        while endblock < self.web3.eth.blockNumber+step-1:
            # print(f"{fromblock} - {endblock}")
            items = self.getEventFromTo(fromblock=fromblock,
                                        contract_address=self.address,
                                        topic=self.create_dispute_event_topic,
                                        endblock=endblock)
            if len(items):
                for item in items:
                    dispute_eth = self.parse_dispute_event(item)
                    try:
                        dispute_in_db = Dispute.query.get(dispute_eth['disputeID'])
                    except Exception as e:
                        logger.exception('Error trying to get the dispute data from DB.',
                                         exc_info=e)
                        dispute_in_db = None
                    logger.info(f"Checking the dispute {dispute_eth['disputeID']}")

                    # Create the dispute to check if changes are needed
                    new_dispute = Dispute(id=dispute_eth['disputeID'],
                                          creator=dispute_eth['creator'],
                                          timestamp=dispute_eth['timestamp'],
                                          txid=dispute_eth['txid'],
                                          ruled=dispute_eth['ruled'],
                                          subcourtID=dispute_eth['subcourtID'],
                                          current_ruling=dispute_eth['ruling'],
                                          period=dispute_eth['period'],
                                          last_period_change=dispute_eth['last_period_change'],
                                          blocknumber=dispute_eth['blockNumber'],
                                          arbitrated=dispute_eth['arbitrated'],
                                          status=dispute_eth['current_status'],
                                          number_of_choices=dispute_eth['number_of_choices']
                                          )
                    if dispute_in_db is None:
                        # this is a new dispute
                        bn = self.create_dispute(new_dispute)
                        # There is no need to check the round and votes info
                        open_dispute_blockNumbers.append(bn)
                        continue
                    elif dispute_in_db.ruled:
                        # The dispute is ruled, no need to update it
                        logger.debug(f'Dispute {dispute_in_db.id} is already ruled.')
                        continue
                    else:
                        # it's an open dispute that is not new.
                        # add the block number to store the minimum value in the DB
                        open_dispute_blockNumbers.append(dispute_in_db.blocknumber)

                    # Update dispute info if changed.
                    if dispute_in_db != new_dispute:
                        # update current dispute
                        logger.info(f'Updating the dispute {new_dispute.id}')
                        (db.session.query(Dispute)
                         .filter(Dispute.id == new_dispute.id)
                         .update({'status': new_dispute.status,
                                  'current_ruling': new_dispute.current_ruling,
                                  'period': new_dispute.period,
                                  'last_period_change': new_dispute.last_period_change,
                                  'ruled': new_dispute.ruled})
                         )
                        db.session.commit()

                    # check if new rounds / new votes
                    rounds = self.dispute_rounds(new_dispute.id)
                    for r, round in enumerate(rounds):
                        round_in_db = Round.query.filter_by(disputeID=new_dispute.id).filter_by(round_num=r).first()
                        new_round = Round(disputeID=new_dispute.id,
                                          round_num=r,
                                          draws_in_round=round['jury_size'],
                                          tokens_at_stake_per_juror=round['tokens_at_stake_per_juror'],
                                          total_fees_for_jurors=round['total_fees'],
                                          commits_in_round=round['votes'],
                                          repartitions_in_each_round=round['repartition'],
                                          penalties_in_each_round=round['penalties'],
                                          subcourtID=new_dispute.subcourtID
                                          )
                        # check changes with the DB
                        if round_in_db is None:
                            # I don't think this ever happend...
                            logger.debug('Creating round with dispute already in the DB :-?')
                            self.create_round(new_dispute, r, round)
                            self.create_votes_from_round(new_dispute.id, r, new_round)
                            # don't need to check if votes has changed
                            continue
                        elif round_in_db != new_round:
                            # Update round in db.
                            # Just rewrite the fields that could have changed
                            logger.info(f'Updating the round {r} of dispute {new_dispute.id}')
                            (db.session.query(Round)
                             .filter(Round.round_num == r)
                             .filter(Round.disputeID == new_dispute.id)
                             .update({'penalties_in_each_round': round['penalties'],
                                      'commits_in_round': round['votes'],
                                      'repartitions_in_each_round': round['repartition']})
                             )
                            db.session.commit()

                        # update votes in round, if needed
                        votes_in_db = Vote.query.filter_by(round_id=round_in_db.id).all()
                        for v, vote in enumerate(round['jurors']):
                            new_vote = Vote(account=vote['address'],
                                            commit=vote['commit'],
                                            choice=vote['choice'],
                                            vote=vote['voted'])
                            vote_db = votes_in_db[v]
                            if new_vote != vote_db:
                                # the vote need update
                                logger.info(f'Updating the vote #{v} from the round {r} of the dispute {new_dispute.id}')
                                (db.session.query(Vote)
                                 .filter(Vote.id == vote_db.id)
                                 .update({'commit': new_vote.commit,
                                          'choice': new_vote.choice,
                                          'vote': new_vote.vote})
                                 )
                                db.session.commit()
            fromblock = endblock + 1
            endblock = fromblock + step
            allItems += items
        bn = min(x for x in open_dispute_blockNumbers if x is not None)-1
        Config.set('dispute_search_block', bn)
        db.session.commit()
        return allItems

    def create_dispute(self, dispute):
        """
        Create a dispute in the database

        Parameters
        ----------
        dispute : Dispute Object
            Dispute object with all it's information. The ID it's a required
            field.

        Returns
        -------
        int
            If no error raised, return the dispute block number.
        """
        logger.debug(f'Creating dispute {dispute.id}')
        try:
            # Fix for the case n° 149
            if dispute.number_of_choices > 511:
                logger.error(f"Changing the number_of_choices from the dispute {dispute.id} to 2 because is greater than 511 and could not be")
                dispute.number_of_choices = 2

            db.session.add(dispute)
            db.session.commit()
            rounds = dispute.rounds()
            for i, round_eth in enumerate(rounds):
                self.create_round(dispute, i, round)
                self.create_votes_from_round(dispute.id, i, Round(round_eth))
            return dispute.blocknumber
        except Exception as e:
            logger.exception("Error trying to add a Dispute into the database",
                             exc_info=e)
            logger.error(dispute)

    def create_round(self, dispute, round_num, round_eth):
        """
        Create a new round in the database

        Parameters
        ----------
        dispute : Dispute Object
            The dispute object where the round belongs
        round_num : int
            Round number
        round_eth : dict
            Round information from the parser.

        Returns
        -------
        the Round object created.

        """
        round = Round(disputeID=dispute.id,
                      round_num=round_num,
                      draws_in_round=round_eth['jury_size'],
                      tokens_at_stake_per_juror=round_eth['tokens_at_stake_per_juror'],
                      total_fees_for_jurors=round_eth['total_fees'],
                      commits_in_round=round_eth['votes'],
                      repartitions_in_each_round=round_eth['repartition'],
                      penalties_in_each_round=round_eth['penalties'],
                      subcourtID=dispute.subcourtID
                      )
        db.session.add(round)
        db.session.commit()
        return round

    def create_votes_from_round(self, dispute_id, round_num, round):
        """
        Create the votes from a round in the database

        Parameters
        ----------
        dispute_id : int
            Dispute Number
        round_num : int
            Round number in the dispute
        round : Round Object
            Round object from the database

        Returns
        -------
        None.

        """
        for vote_num in range(0, round.draws_in_round):
            vote_eth = self.vote(dispute_id, round_num, vote_num)
            vote = Vote(
                        round_id=round.id,
                        account=vote_eth['address'],
                        commit=vote_eth['commit'],
                        choice=vote_eth['choice'],
                        vote=vote_eth['vote']
                        )
            db.session.add(vote)
        db.session.commit()

    def court_info(self, courtID):
        """
        Get the court information from the smart contract

        Parameters
        ----------
        courtID : int
            Court ID

        Returns
        -------
        dict
            Dictionary with the fields of the court.

        """
        courtData = self.contract.functions.courts(courtID).call()
        return {'parent': None if courtData[0] == courtID else courtData[0],
                'hiddenVotes': courtData[1],
                'minStake': courtData[2]/10**18,
                'alpha': courtData[3],
                'feeForJuror': courtData[4]/10**18,
                'jurorsForCourtJump': courtData[5],
                'votesStake': (courtData[2]/10**18) * (courtData[3]/10**4)}

    def map_court_names(self, courtID):
        """
        Map the court information from the Policy Registry Smart Contract.
        With the courtID asks to the smart contract the metadata of the court,
        as it's fancy name etc. In this function we return just it''s name

        Parameters
        ----------
        courtID : int
            Court Id

        Returns
        -------
        str
            Court name as defined in the Policy Registry Smart Contract
        """
        courtInfo = PolicyRegistry().get_subcourt_info(courtID)
        if courtInfo:
            try:
                return courtInfo['name']
            except KeyError:
                logger.exception('Error trying to return the Court name')
                return 'Court ' + courtID
        else:
            # this should never happend, but is just in case.
            return 'Court ' + courtID


class PolicyRegistry(SmartContract):

    def __init__(self, address='0xCf1f07713d5193FaE5c1653C9f61953D048BECe4'):
        self.address = address
        with open('app/lib/ABI_PolicyRegistry.json', 'r') as f:
            self.abi = json.loads(f.read())['result']

        self.contract = self.web3.eth.contract(abi=self.abi,
                                               address=self.address)

    def get_subcourt_info(self, id):
        """
        Get the subcourt details.
        With the subcourt id, read the PolicyRegistry to get the ipfs route,
        then request the info to the ipfs.

        policy_is the return of the smart contract call to the policy function.
        for example: '/ipfs/QmYMdCkb7WULmiK6aQrgsayGG3VYisQwsHSLC3TLkzEHCm'
        which is the ipfs route to the General Court information. Then, a
        request to the ipfs.kleros.io proxy is made to get the info of the
        court.
        """
        policy_id = self.contract.functions.policies(int(id)).call()
        if len(policy_id) > 0:
            host = 'https://ipfs.kleros.io'
            # polocy_id should be '/ipfs/xxxxxxxxxxxxx'
            response = requests.get(host + policy_id)
            return response.json()
        else:
            return None
