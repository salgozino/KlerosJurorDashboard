from urllib.parse import non_hierarchical
import requests
import os
import json
import logging
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import pandas as pd

from app.modules.oracles import CoinGecko
from app.modules.web3_node import web3Node

try:
    ipfs_node = os.getenv['IPFS_NODE']
except TypeError:
    ipfs_node = 'https://ipfs.kleros.io'


class Subgraph():
    def __init__(self, network=None):
        self.logger = logging.getLogger(__name__)
        self.network = network.lower() if network is not None else 'mainnet'
        self.network = 'mainnet' if self.network == '' else self.network
        self.index_node = 'https://api.thegraph.com/index-node/graphql'
        self.subgraph_node = 'https://api.thegraph.com/subgraphs/name/'

    def _post_query(self, query):
        response = requests.post(self.subgraph_node, json={'query': query})
        data = response.json()
        try:
            data = data['data']
        except KeyError:
            self.logger.error(('Error trying to jsonise the response data of '
                              'this query: %s'),
                              query)
            self.logger.error(data['errors'])
            return None
        data_length = 0
        for key in data.keys():
            if len(data[key]) != 0:
                data_length += 1
                break
        if data_length > 0:
            return data
        else:
            return None

    @staticmethod
    def _wei2eth(gwei):
        return float(gwei) * 10**-18

    def getStatus(self):
        """
        Return the status of the subgraph. If xdai, return synced
        """
        query = """
        {
            _meta{
                block {
                number
                }
                deployment
            }
        }
        """
        result = self._post_query(query)
        meta = result['_meta']
        subgraph_block_number = int(meta['block']['number'])
        subgraph_id = meta['deployment']
        if self.network == 'xdai':
            return {'status': 'Updated',
                    'last_block': subgraph_block_number,
                    'deployment': subgraph_id}
        last_block_number = web3Node(self.network).web3.eth.blockNumber
        if abs(last_block_number - subgraph_block_number) < 120:
            # ~ 30 min of delay allowed
            return {'status': 'Updated',
                    'last_block': subgraph_block_number,
                    'deployment': subgraph_id}
        else:
            return {'status': 'Updating',
                    'last_block': subgraph_block_number,
                    'deployment': subgraph_id}


class KlerosBoardSubgraph(Subgraph):
    def __init__(self, network=None):
        super(KlerosBoardSubgraph, self).__init__(network)
        self.logger = logging.getLogger(__name__)

        # Node definitions
        if self.network == 'xdai':
            self.subgraph_name = 'salgozino/klerosboard-xdai'
        elif self.network == 'test-xdai':
            self.subgraph_name = 'salgozino/sarasa'
        elif self.network == 'test':
            self.subgraph_name = 'salgozino/sarasa-mainnet'
        else:
            self.subgraph_name = 'salgozino/klerosboard'
        self.subgraph_node += self.subgraph_name

    @staticmethod
    def _calculateVoteStake(minStake, alpha):
        return float(alpha) * (10 ** -4) * float(minStake)

    def _getBlockNumberbefore(self, days=30):
        """
        Get the block number of n days ago. By default, 30 days.
        Now, it's simple considering an average time of 17 seconds.
        This should be improved
        """
        # TODO!, improve this function!
        if self.network == 'xdai':
            query = '{indexingStatusForCurrentVersion(subgraphName: "' + \
                self.subgraph_name + '"){' + \
                'chains{chainHeadBlock{number},latestBlock{number}}}}'
            response = requests.post(self.index_node, json={'query': query})
            currentBlockNumber = int(response.json()['data'][
                'indexingStatusForCurrentVersion']['chains'][0][
                    'chainHeadBlock']['number'])
            averageBlockTime = 5  # in seconds
        else:
            averageBlockTime = 15  # in seconds
            currentBlockNumber = web3Node(self.network).web3.eth.blockNumber
        return int(currentBlockNumber - days * 24 * 60 * 60 / averageBlockTime)

    @staticmethod
    def _getOldPrice(timestamp, network='mainnet'):
        pnk_price = CoinGecko().getPNKoldPrice(timestamp)
        if 'xdai' in network:
            return {'reward_currency': 1., 'token': pnk_price}
        else:
            return {'reward_currency': CoinGecko().getETHoldPrice(timestamp),
                    'token': pnk_price}

    @staticmethod
    def _getHistoricPrices(timestamp_from, network='mainnet'):
        now = datetime.now()
        days_to_oldest = timedelta(seconds=now.timestamp()
                                   - timestamp_from).days + 2
        pnk_historic_price = CoinGecko().getPNKhistoricPrice(
            days_to_oldest)
        df_price_pnk = pd.DataFrame(pnk_historic_price,
                                    columns=['timestamp',
                                             'pnk_price'])
        df_price_pnk['timestamp'] /= 1000
        if 'xdai' not in network:
            eth_historic_price = CoinGecko().getETHhistoricPrice()
            df_price_eth = pd.DataFrame(eth_historic_price,
                                        columns=['timestamp',
                                                 'eth_price'])
            df_price_eth['timestamp'] /= 1000
            df_price = pd.concat([df_price_eth, df_price_pnk])
        else:
            df_price = df_price_pnk.copy()
            df_price['eth_price'] = 1.
        df_price['date'] = pd.to_datetime(
            df_price['timestamp'], unit='s').dt.date
        df_price.set_index('date', inplace=True)
        df_price.sort_index(inplace=True)
        # fill nan with forward values
        df_price.fillna(method='ffill', inplace=True)
        # fill nan in the first row if exist
        df_price.fillna(method='backfill', inplace=True)
        df_price = df_price[~df_price.index.duplicated(keep='last')]
        return df_price

    @staticmethod
    def _getRoundNumFromID(roundID):
        return int(roundID.split('-')[1])

    def _getTotalUSDGasCostInVotes(self, votes):
        if len(votes) == 0:
            return 0.0
        df_votes = pd.DataFrame(votes)
        df_votes['date'] = pd.to_datetime(df_votes['timestamp'],
                                          unit='s')
        oldest_timestamp = df_votes['timestamp'].min()
        # group by day with the sum of ETH transfers
        df_votes = df_votes.groupby(
            by=df_votes['date'].dt.date)['totalGasCost'].sum()
        if 'xdai' in self.network:
            return df_votes.sum()

        if len(df_votes) > 1:
            now = datetime.now()
            days_to_oldest = timedelta(seconds=now.timestamp()
                                       - oldest_timestamp).days + 2
            historic_price = CoinGecko().getETHhistoricPrice(days_to_oldest)
            df_price = pd.DataFrame(historic_price,
                                    columns=['timestamp',
                                             'eth_price'])
            df_price['timestamp'] = df_price['timestamp'] / 1000
            df_price['date'] = pd.to_datetime(
                df_price['timestamp'], unit='s').dt.date
            df_price.set_index('date', inplace=True)
            df_price = df_price[~df_price.index.duplicated(keep='first')]
            df = pd.concat([df_votes, df_price], axis=1)
            df.dropna(axis=0, how='any', inplace=True)
            df['usd_amount'] = df['totalGasCost'] * df['eth_price']
            eth_amount = df['usd_amount'].sum()
        else:
            eth_price = CoinGecko().getETHoldPrice(oldest_timestamp)
            eth_amount = df_votes.values[0] * eth_price
        return eth_amount

    def _getTotalUSDThroughTransfers(self, transfers):
        if len(transfers) == 0:
            return 0.0
        df_transfers = pd.DataFrame(transfers)
        df_transfers['date'] = pd.to_datetime(df_transfers['timestamp'],
                                              unit='s')
        oldest_timestamp = df_transfers['timestamp'].min()
        # group by day with the sum of ETH transfers
        df_transfers = df_transfers.groupby(
            by=df_transfers['date'].dt.date)[['ETHAmount',
                                              'tokenAmount']].sum()

        if len(df_transfers) > 1:
            df_price = self._getHistoricPrices(oldest_timestamp,
                                               network=self.network)
            df = pd.concat([df_transfers, df_price], axis=1)
            df.dropna(axis=0, how='any', inplace=True)
            df['usd_amount'] = df['ETHAmount'] * df['eth_price'] + \
                df['tokenAmount'] * df['pnk_price']
            usd_amount = df['usd_amount'].sum()
        else:
            prices = self._getOldPrice(oldest_timestamp, self.network)
            usd_amount = (df_transfers['ETHAmount'] * prices['reward_currency']
                          + df_transfers['tokenAmount']
                          * prices['token']
                          ).to_list()[0]
        return usd_amount

    def _parseArbitrable(self, arbitrable):
        if arbitrable is None:
            return None
        keys = arbitrable.keys()
        if 'disputesCount' in keys:
            arbitrable['disputesCount'] = int(arbitrable['disputesCount'])
        if 'ethFees' in keys:
            arbitrable['ethFees'] = self._wei2eth(arbitrable['ethFees'])
        if 'disputes' in keys:
            arbitrable['disputes'] = [self._parseDispute(dispute)
                                      for dispute in arbitrable['disputes']]
        return arbitrable

    def _parseCourt(self, court):
        # get a query of a courts and parse values to the correct format
        if court is None:
            return None
        keys = court.keys()
        if 'tokenStaked' in keys:
            court['tokenStaked'] = self._wei2eth(court['tokenStaked'])
        if 'parent' in keys:
            if court['parent'] is not None:
                court['parent'] = int(court['parent']['id'])
            else:
                court['parent'] = None
        if 'activeJurors' in keys:
            court['activeJurors'] = int(court['activeJurors'])
        if 'minStake' in keys:
            court['minStake'] = self._wei2eth(float(court['minStake']))
        if 'feeForJuror' in keys:
            court['feeForJuror'] = self._wei2eth(court['feeForJuror'])
        if 'alpha' in keys:
            court['alpha'] = float(court['alpha'])
        if 'alpha' in keys and 'minStake' in keys:
            court['voteStake'] = self._calculateVoteStake(court['minStake'],
                                                          court['alpha'])
        if 'disputesNum' in keys:
            court['disputesNum'] = int(court['disputesNum'])
        if 'disputesOngoing' in keys:
            court['disputesOngoing'] = int(court['disputesOngoing'])
        if 'disputesClosed' in keys:
            court['disputesClosed'] = int(court['disputesClosed'])
        if 'subcourtID' in keys:
            court['subcourtID'] = int(court['subcourtID'])
        if 'timePeriods' in keys:
            periods = []
            for period in court['timePeriods']:
                periods.append(int(period))
            court['timePeriods'] = periods
        if 'totalETHFees' in keys:
            court['totalETHFees'] = self._wei2eth(court['totalETHFees'])
        if 'totalTokenRedistributed' in keys:
            court['totalTokenRedistributed'] = self._wei2eth(
                court['totalTokenRedistributed'])
        if 'childs' in keys:
            if court['childs'] is not None:
                childs = []
                for child in court['childs']:
                    childs.append(child['id'])
            court['childs'] = childs
        return court

    def _parseCourtStake(self, courtStake):
        keys = courtStake.keys()
        if 'stake' in keys:
            courtStake['stake'] = self._wei2eth(courtStake['stake'])
        if 'court' in keys:
            courtID = int(courtStake['court']['id'])
            courtStake['court'] = courtID
        if 'juror' in keys:
            courtStake['address'] = courtStake['juror']['id']
        if 'timestamp' in keys:
            courtStake['timestamp'] = int(courtStake['timestamp'])
            courtStake['date'] = datetime.fromtimestamp(
                courtStake['timestamp'])
        return courtStake

    def _parseDispute(self, dispute, timePeriods=None):
        # get a query response from one dispute and return parsed the votes
        # and values in the correct format. if the timePeriods of a court are
        # inputed, it's used to get the timePeriodEnds without need to request
        # the timePeriods of that court (speeds up the process)
        keys = dispute.keys()
        if 'id' in keys:
            dispute['id'] = int(dispute['id'])
        if 'subcourtID' in keys:
            if 'id' in dispute['subcourtID']:
                subcourtID = int(dispute['subcourtID']['id'])
                dispute['subcourtID'] = subcourtID
        if 'disputeID' in keys:
            dispute['disputeID'] = int(dispute['disputeID'])
        if 'currentRulling' in keys:
            if dispute['currentRulling'] is not None:
                dispute['currentRulling'] = int(dispute['currentRulling'])
        if 'lastPeriodChange' in keys:
            dispute['lastPeriodChange'] = int(dispute['lastPeriodChange'])
        if 'creator' in keys:
            dispute['creator'] = dispute['creator']['id']
        if 'arbitrable' in keys:
            if 'id' in dispute['arbitrable'].keys():
                dispute['arbitrable'] = dispute['arbitrable']['id']
        if ('period' in keys) and ('subcourtID' in keys):
            dispute['periodEnds'] = self.getWhenPeriodEnd(dispute,
                                                          subcourtID,
                                                          timePeriods
                                                          )
        if 'startTime' in keys:
            dispute['startTime'] = int(dispute['startTime'])
        if 'numberOfChoices' in keys:
            dispute['numberOfChoices'] = int(dispute['numberOfChoices'])
        else:
            dispute['numberOfChoices'] = None
        if 'TokenAndETHShifts' in keys:
            for transfer in dispute['TokenAndETHShifts']:
                transfer = self._parseTransfer(transfer)
        if 'rounds' in keys:
            vote_count = {}
            # initialize a dict with 0 as default value
            unique_vote_count = defaultdict(int)
            unique_jurors = set()
            for round in dispute['rounds']:
                # initialize a dict with 0 as default value
                vote_count[round['id']] = defaultdict(int)
                votes = round['votes']
                for vote in votes:
                    vote = self._parseVote(vote, dispute['numberOfChoices'])
                    vote_count[round['id']][vote['vote_str']] += 1
                    if vote['address'].lower() not in unique_jurors:
                        unique_vote_count[vote['vote_str']] += 1
                        unique_jurors.add(vote['address'].lower())
                # easier to read the jurors with multiple votes
                round['votes'] = sorted(round['votes'], key=lambda x: x[
                    'address'])
                if 'id' in round.keys():
                    round['round_num'] = self._getRoundNumFromID(round['id'])
            dispute['vote_count'] = vote_count
            dispute['unique_vote_count'] = unique_vote_count
            dispute['unique_jurors'] = unique_jurors
        return dispute

    def _parseKlerosCounters(self, kc):
        float_fields = ['tokenStaked', 'totalETHFees',
                        'totalTokenRedistributed']
        for key, value in kc.items():
            if key in float_fields:
                kc[key] = self._wei2eth(value)
            else:
                kc[key] = int(value)
        return kc

    def _parseProfile(self, profile):
        keys = profile.keys()
        if 'numberOfDisputesAsJuror' in keys:
            profile['numberOfDisputesAsJuror'] = int(profile[
                'numberOfDisputesAsJuror'])
        if 'numberOfDisputesAsCreator' in keys:
            profile['numberOfDisputesAsCreator'] = int(profile[
                'numberOfDisputesAsCreator'])
        if 'currentStakes' in keys:
            for stake in profile['currentStakes']:
                stake = self._parseCourtStake(stake)
        if 'totalStaked' in keys:
            profile['totalStaked'] = self._wei2eth(profile['totalStaked'])
        else:
            profile['totalStaked'] = 0.0
        if 'tokenAndETHShifts' in keys:
            for transfer in profile['tokenAndETHShifts']:
                transfer = self._parseTransfer(transfer)
        else:
            profile['transfers'] = []
        if 'allStakes' in keys:
            for stake in profile['allStakes']:
                stake = self._parseStakeSet(stake)
        else:
            profile['allStakes'] = []
        # vote parsing
        profile['coherent_votes'] = 0
        profile['ruled_cases'] = 0
        if 'votes' in keys:
            for vote in profile['votes']:
                vote = self._parseVote(vote,
                                       vote['dispute']['numberOfChoices'])
                if vote['dispute']['ruled']:
                    if vote['dispute']['currentRulling'] == vote['choice']:
                        profile['coherent_votes'] = profile['coherent_votes'] \
                            + 1
                    profile['ruled_cases'] += 1

        if profile['ruled_cases'] > 0:
            profile['coherency'] = profile['coherent_votes'] / profile[
                'ruled_cases']
        else:
            profile['coherency'] = None

        disputes_as_creator = []
        if 'disputesAsCreator' in keys:
            for dispute in profile['disputesAsCreator']:
                disputes_as_creator.append(self._parseDispute(dispute))
            profile['disputesAsCreator'] = disputes_as_creator

        if 'ethRewards' in keys:
            profile['ethRewards'] = self._wei2eth(profile['ethRewards'])
        else:
            profile['ethRewards'] = 0
        if 'tokenRewards' in keys:
            profile['tokenRewards'] = self._wei2eth(profile['tokenRewards'])
        else:
            profile['tokenRewards'] = 0
        return profile

    def _parseStakeSet(self, stake_set):
        keys = stake_set.keys()
        if 'subcourtID' in keys:
            stake_set['subcourtID'] = int(stake_set['subcourtID'])
        if 'stake' in keys:
            stake_set['stake'] = self._wei2eth(stake_set['stake'])
        if 'newTotalStake' in keys:
            stake_set['newTotalStake'] = self._wei2eth(stake_set[
                'newTotalStake'])
        if 'address' in keys:
            stake_set['address'] = stake_set['address']['id']
        if 'timestamp' in keys:
            stake_set['timestamp'] = int(stake_set['timestamp'])
        if 'blocknumber' in keys:
            stake_set['blocknumber'] = int(stake_set['blocknumber'])
        if 'gasCost' in keys:
            stake_set['gasCost'] = self._wei2eth(stake_set['gasCost'])
        return stake_set

    def _parseTransfer(self, transfer):
        keys = transfer.keys()
        if 'ETHAmount' in keys:
            transfer['ETHAmount'] = self._wei2eth(transfer['ETHAmount'])
        if 'tokenAmount' in keys:
            transfer['tokenAmount'] = self._wei2eth(transfer['tokenAmount'])
        if 'timestamp' in keys:
            transfer['timestamp'] = int(transfer['timestamp'])
        if 'blocknumber' in keys:
            transfer['blocknumber'] = int(transfer['blocknumber'])
        return transfer

    def _parseVote(self, vote, number_of_choices=None):
        keys = vote.keys()
        if 'address' in keys:
            vote['address'] = vote['address']['id']
        if 'choice' in keys:
            if vote['choice'] is not None:
                vote['choice'] = int(vote['choice'])
        if 'dispute' in keys:
            if isinstance(vote['dispute'], dict):
                vote['dispute'] = self._parseDispute(vote['dispute'])
        if 'timestamp' in keys:
            try:
                vote['timestamp'] = int(vote['timestamp'])
            except TypeError:
                vote['timestamp'] = None
        if 'commitGasUsed' in keys:
            vote['commitGasUsed'] = int(vote['commitGasUsed'])
        if 'commitGasPrice' in keys:
            vote['commitGasPrice'] = self._wei2eth(vote['commitGasPrice'])
        if 'commitGasCost' in keys:
            vote['commitGasCost'] = self._wei2eth(vote['commitGasCost'])
        if 'castGasUsed' in keys:
            vote['castGasUsed'] = int(vote['castGasUsed'])
        if 'castGasPrice' in keys:
            vote['ccastasPrice'] = self._wei2eth(vote['castGasPrice'])
        if 'castGasCost' in keys:
            vote['castGasCost'] = self._wei2eth(vote['castGasCost'])
        if 'totalGasCost' in keys:
            vote['totalGasCost'] = self._wei2eth(vote['totalGasCost'])

        if ('choice' in keys) and ('voted' in keys) and ('dispute' in keys):
            vote['vote_str'] = self._vote_mapping(vote['choice'],
                                                  vote['voted'],
                                                  vote['dispute'],
                                                  number_of_choices)
        if 'round' in keys:
            if 'id' in vote['round'].keys():
                vote['roundNumber'] = self._getRoundNumFromID(vote[
                    'round']['id'])
        return vote

    @staticmethod
    def _period2number(period):
        period_map = {
            'execution': 4,
            'appeal': 3,
            'vote': 2,
            'commit': 1,
            'evidence': 0}
        return period_map[period]

    @staticmethod
    def _vote_mapping(choice, voted, dispute=None, number_of_choices=2):
        """
        Return the text of the vote choice.
        TODO!, use the metaEvidence of the dispute,
        currently it's just fixed to Refuse, Yes, No or Pending
        """
        if voted:
            if choice is None:
                return 'Vote not revealed yet'
            if number_of_choices is None:
                return str(choice)
            # Disable this option until metadata it's integrated
            # if int(number_of_choices) > 2:
            #     return str(choice)
            if choice > 2:
                return str(choice)
            vote_map = {0: 'Refuse to Arbitrate',
                        1: 'Yes',
                        2: 'No'}
            return vote_map[choice]
        else:
            return 'Pending'

    def court2table(self, court, pnkUSDPrice, rewardUSDPrice):
        """
        Fields of the Table used in the main view of klerosboard
        """
        return {'Jurors': court['activeJurors'],
                'Total Staked': court['tokenStaked'],
                'Min Stake': court['minStake'],
                'Fee For Juror': court['feeForJuror'],
                'Fee For Juror USD': court['feeForJuror'] * rewardUSDPrice,
                'Vote Stake': court['voteStake'],
                'Open Disputes': court['disputesOngoing'],
                'Min Stake in USD': court['minStake'] * pnkUSDPrice,
                'Total Disputes': court['disputesNum'],
                'id': court['subcourtID'],
                'Name': self.getCourtName(court['subcourtID'])
                }

    def getActiveJurorsFromCourt(self, courtID):
        query = (
            '{'
            'courtStakes(where:{court:"' + str(courtID) + '",stake_gt:0}, '
            'first:1000){'
            '    stake,'
            '    juror {id}'
            '}}'
        )

        result = self._post_query(query)
        if result is None:
            return []
        else:
            courtStakes = result['courtStakes']
            return [self._parseCourtStake(cs) for cs in courtStakes]

    def getAdoption(self):
        "return the number of new jurors in the last 30 days"
        query = (
            '{klerosCounters{'
            '   activeJurors,'
            '   inactiveJurors'
            '}}'
        )
        current_result = self._post_query(query)
        if current_result is None:
            result = {'activeJurors': 0, 'inactiveJurors': 0}
        else:
            result = current_result['klerosCounters'][0]

        bn = self._getBlockNumberbefore(30)
        query = (
            '{klerosCounters(block:{number:' + str(bn) + '}){'
            '   activeJurors,'
            '   inactiveJurors'
            '}}'
        )
        before_result = self._post_query(query)
        if before_result is not None:
            old_result = before_result['klerosCounters'][0]
        else:
            old_result = {'activeJurors': 0, 'inactiveJurors': 0}
        newTotal = int(result['activeJurors']) + int(result['inactiveJurors'])
        oldTotal = int(old_result['activeJurors']) + int(old_result[
            'inactiveJurors'])
        return newTotal - oldTotal

    def getAllArbitrables(self):
        initArbitrable = ""
        arbitrables = []
        while True:
            query = (
                '{arbitrables(where:{id_gt:"' + str(initArbitrable) + '"},'
                'orderBy:id, orderDirection:asc, first:1000){'
                'id,disputesCount,ethFees'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentarbitrables = result['arbitrables']
                arbitrables.extend(currentarbitrables)
                if len(currentarbitrables) < 1000:
                    break
                initArbitrable = currentarbitrables[-1]['id']
        return [self._parseArbitrable(arbitrable)
                for arbitrable in arbitrables]

    def getAllCourts(self):
        query = (
            '''{
            courts{
                id
                subcourtID,
                disputesOngoing,
                disputesClosed,
                disputesNum,
                childs{id},
                parent{id},
                policy{policy},
                activeJurors,
                tokenStaked,
                hiddenVotes,
                minStake,
                alpha,
                feeForJuror,
                jurorsForCourtJump,
                timePeriods,
            }}'''
        )
        result = self._post_query(query)
        if result is None:
            return result
        else:
            courts = []
            for court in result['courts']:
                courts.append(self._parseCourt(court))
            return courts

    def getAllCourtsDaysBefore(self, days=30):
        blockNumber = self._getBlockNumberbefore(days)
        query = (
            '{courts(block:{number:' + str(blockNumber) + '}){'
            '   subcourtID,'
            '   disputesOngoing,'
            '   disputesClosed,'
            '   disputesNum'
            '   childs{id},'
            '   parent{id},'
            '   policy{policy},'
            '   activeJurors,'
            '   tokenStaked,'
            '   hiddenVotes,'
            '   minStake,'
            '   alpha,'
            '   feeForJuror,'
            '   jurorsForCourtJump,'
            '   timePeriods,'
            '}}'
        )

        result = self._post_query(query)
        if 'errors' in result.json().keys():
            return None
        if result is None:
            return result
        else:
            return result['courts']

    def getAllCourtDisputes(self, courtID):
        initDispute = -1
        disputes = []
        while True:
            query = (
                '{disputes(where:{subcourtID:"' + str(courtID)
                + '", disputeID_gt:' + str(initDispute)
                + '}, orderBy:disputeID,orderDirection:asc){'
                'id,subcourtID{id},currentRulling,ruled,startTime,'
                'period,lastPeriodChange'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            elif len(result['disputes']) == 0:
                break
            else:
                currentDisputes = result['disputes']
                disputes.extend(currentDisputes)
                initDispute = int(currentDisputes[-1]['id'])
                if len(currentDisputes) < 100:
                    break

        parsed_disputes = []
        for dispute in disputes:
            parsed_disputes.append(self._parseDispute(dispute))
        return parsed_disputes

    def getAllDisputes(self):
        initDispute = -1
        disputes = []
        while True:
            query = (
                '{disputes(where:{disputeID_gt:' + str(initDispute) + '},'
                ' orderDirection:asc, orderBy:disputeID){'
                'id,subcourtID{id},currentRulling,ruled,startTime,'
                'period,lastPeriodChange,arbitrable{id}'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentDisputes = result['disputes']
                disputes.extend(currentDisputes)
                initDispute = int(currentDisputes[-1]['id'])
                if len(currentDisputes) < 100:
                    break
        courtTimePeriods = self.getTimePeriodsAllCourts()
        parsed_disputes = []
        for dispute in disputes:
            subcourtID = dispute['subcourtID']['id']
            parsed_disputes.append(self._parseDispute(dispute,
                                                      courtTimePeriods[
                                                          subcourtID]))
        return parsed_disputes

    def getAllOpenDisputes(self):
        initDispute = -1
        disputes = []
        while True:
            query = (
                '{disputes(where:{disputeID_gt:' + str(initDispute)
                + ', ruled:false},'
                ' orderDirection:asc, orderBy:disputeID){'
                'id,subcourtID{id},currentRulling,ruled,startTime,'
                'period,lastPeriodChange,arbitrable{id}'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentDisputes = result['disputes']
                disputes.extend(currentDisputes)
                initDispute = int(currentDisputes[-1]['id'])
                if len(currentDisputes) < 100:
                    break
        courtTimePeriods = self.getTimePeriodsAllCourts()
        parsed_disputes = []
        for dispute in disputes:
            subcourtID = dispute['subcourtID']['id']
            parsed_disputes.append(self._parseDispute(dispute,
                                                      courtTimePeriods[
                                                          subcourtID]))
        return parsed_disputes

    def getAllStakeSets(self):
        initStakes = ""
        stakes = []
        while True:
            query = (
                '{stakeSets(where:{id_gt:"' + str(initStakes) + '"},'
                'orderBy:id, orderDirection:asc, first:1000){'
                'id,address{id},subcourtID,stake,newTotalStake,timestamp'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentStakes = result['stakeSets']
                stakes.extend(currentStakes)
                if len(currentStakes) < 1000:
                    break
                initStakes = currentStakes[-1]['id']
        return [self._parseStakeSet(stake)
                for stake in stakes]

    def getAllTransfers(self):
        initTransfer = ""
        transfers = []
        while True:
            query = (
                '{tokenAndETHShifts(where:{id_gt:"' + str(initTransfer) + '"'
                ',ETHAmount_gt:0},'
                'orderBy:id, orderDirection:asc, first:1000){'
                'id,ETHAmount,tokenAmount,blockNumber,timestamp'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currenttransfers = result['tokenAndETHShifts']
                transfers.extend(currenttransfers)
                if len(currenttransfers) < 1000:
                    break
                initTransfer = currenttransfers[-1]['id']
        return [self._parseTransfer(transfer)
                for transfer in transfers]

    def getAllVotesFromJuror(self, address):
        query = ('{votes(where:{address:"'
                 + str(address) + '"},first:1000){'
                 'dispute{id,currentRulling,ruled,startTime,numberOfChoices},'
                 'choice,voted,round{id}'
                 '}}'
                 )
        result = self._post_query(query)

        if result is None:
            return []
        votes = result['votes']
        return [self._parseVote(vote, vote['dispute']['numberOfChoices'])
                for vote in votes]

    def getAllJurors(self):
        skipJurors = 0
        profiles = []
        while True:
            query = (
                '{jurors(skip:' + str(skipJurors) + ', first:1000, orderBy:id,'
                'orderDirection:asc){id,totalStaked,numberOfDisputesAsJuror'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentProfiles = result['jurors']
                profiles.extend(currentProfiles)
                skipJurors += len(currentProfiles)

        parsed_disputes = [self._parseProfile(profile) for profile in profiles]
        return parsed_disputes

    def getArbitrable(self, address):
        query = (
            '{arbitrables(where:{id:"' + str(address).lower() + '"}) {'
            '   id,'
            '   disputesCount,'
            '   openDisputes,'
            '   closedDisputes,'
            '   evidencePhaseDisputes,'
            '   commitPhaseDisputes,'
            '   votingPhaseDisputes,'
            '   appealPhaseDisputes,'
            '   ethFees,'
            '   disputes(orderBy:id, orderDirection:desc, limit:1000){'
            'id, period, startTime, ruled, currentRulling, txid}'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return result
        return self._parseArbitrable(result['arbitrables'][0])

    def getArbitrableName(self, arbitrable):
        if self.network == 'test2':
            file_path = 'app/lib/dapp_index_mainnet.json'
        else:
            file_path = f'app/lib/dapp_index_{self.network}.json'
        arbitrable = str(arbitrable).lower()
        if os.path.isfile(file_path):
            with open(file_path) as jsonFile:
                dapp_index = json.load(jsonFile)
                if arbitrable in dapp_index.keys():
                    if dapp_index[arbitrable] is not None:
                        if 'Dapp name' in dapp_index[arbitrable]:
                            return dapp_index[arbitrable]['Dapp name']
        return arbitrable

    def getCourt(self, courtID):
        query = (
            '{'
            'courts(where:{id:"' + str(courtID) + '"}) {'
            '   id,'
            '   subcourtID,'
            '   disputesOngoing,'
            '   disputesClosed,'
            '   disputesNum,'
            '   childs{id},'
            '   parent{id},'
            '   policy{policy},'
            '   jurors{id, totalStaked},'
            '   activeJurors,'
            '   tokenStaked,'
            '   hiddenVotes,'
            '   minStake,'
            '   alpha,'
            '   feeForJuror,'
            '   jurorsForCourtJump,'
            '   timePeriods,'
            '   totalETHFees,'
            '   totalTokenRedistributed,'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return None
        else:
            court = result['courts'][0]
            return self._parseCourt(court)

    def getCourtChildrens(self, courtID):
        childrens = set()
        search_courts = set([str(courtID)])
        while len(search_courts) > 0:
            query = (
                '{courts(where:{id:"' + str(search_courts.pop()) + '"}){'
                '   childs{id},'
                '}}'
            )
            result = self._post_query(query)
            if len(result['courts']) > 0:
                data = result.json()['data']['courts'][0]
                for child in data['childs']:
                    childrens.add(child['id'])
                    search_courts.add(child['id'])
        return childrens

    def getCourtDaysBefore(self, courtID, days=30):
        blockNumber = self._getBlockNumberbefore(days)
        query = (
            '{courts(block:{number:'
            + str(blockNumber) + '},where:{id:"'
            + str(courtID)
            + '"}){'
            '   subcourtID,'
            '   disputesOngoing,'
            '   disputesClosed,'
            '   disputesNum'
            '   childs{id},'
            '   parent{id},'
            '   policy{policy},'
            '   activeJurors,'
            '   tokenStaked,'
            '   hiddenVotes,'
            '   minStake,'
            '   alpha,'
            '   feeForJuror,'
            '   jurorsForCourtJump,'
            '   timePeriods,'
            '}}'
        )
        result = self._post_query(query)
        if len(result['courts']) == 0:
            return None
        else:
            return self._parseCourt(result['courts'][0])

    def getCourtDisputesNumber(self):
        query = (
            '{courts{'
            '   disputesNum'
            '   subcourtID'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return None
        if len(result['courts']) == 0:
            return None
        else:
            courts = []
            for court in result['courts']:
                courts.append(self._parseCourt(court))
            return courts

    def getCourtList(self):
        query = (
            '''{
            courts{
                subcourtID,
            }}'''
        )
        result = self._post_query(query)
        if result is None:
            return []
        else:
            return [self._parseCourt(court) for court in result['courts']]

    def getCourtPolicy(self, courtID):
        policy = self.readPolicy(courtID)
        if policy is None:
            return None
        if 'https://' in policy['policy']:
            # prevent errors
            return None
        else:
            response = requests.get(ipfs_node + policy['policy'])
        return response.json()

    def getCourtTable(self):
        courtsInfo = {}
        oldcourtsDisputes = {}
        courts = self.getAllCourts()
        cg = CoinGecko()
        pnkUSDprice = cg.getPNKprice()
        rewardUSDprice = cg.getETHprice() if self.network == 'mainnet' else 1.0
        oldCourts = self.getCourtDisputesNumberBefore(30)
        if oldCourts is not None:
            for court in oldCourts:
                oldcourtsDisputes[court['subcourtID']] = court['disputesNum']
        for court in courts:
            courtID = court['subcourtID']
            courtsInfo[courtID] = self.court2table(court,
                                                   pnkUSDprice,
                                                   rewardUSDprice)
            diff = courtsInfo[courtID]['Total Disputes']
            if oldcourtsDisputes is not None:
                if courtID in oldcourtsDisputes.keys():
                    diff = courtsInfo[courtID]['Total Disputes'] \
                        - oldcourtsDisputes[courtID]
            courtsInfo[courtID]['Disputes in the last 30 days'] = diff
        return courtsInfo

    def getCourtTotalStaked(self, courtID):
        query = (
            '{courts(where:{id:"' + str(courtID) + '"}){'
            '   tokenStaked,'
            '}}'
        )
        result = self._post_query(query)
        if len(result['courts']) == 0:
            return None
        else:
            return self._wei2eth(result['data'][
                'courts'][0]['tokenStaked'])

    def getCourtWithDisputes(self, courtID):
        court = self.getCourt(courtID)
        if court is None:
            return None
        court['disputes'] = self.getAllCourtDisputes(courtID)
        return court

    def getCourtDisputesNumberBefore(self, days=30):
        blockNumber = self._getBlockNumberbefore(days)
        query = (
            '{courts(block:{number:' + str(blockNumber) + '}){'
            '   disputesNum'
            '   subcourtID'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return None
        if len(result['courts']) == 0:
            return None
        else:
            courts = result['courts']
            parsed_courts = []
            for court in courts:
                parsed_courts.append(self._parseCourt(court))
            return parsed_courts

    def getCourtName(self, courtID):
        file_path = f'app/lib/court_policies_{self.network}.json'
        courtID = str(courtID)
        if os.path.isfile(file_path):
            with open(file_path) as jsonFile:
                policies = json.load(jsonFile)
                if courtID in policies.keys():
                    if policies[courtID] is not None:
                        if 'name' in policies[courtID]:
                            return policies[courtID]['name']
        return str(courtID)

    def getCourtTree(self):
        query = (
            '''{
            courts{
                subcourtID,
                parent{id},
                activeJurors,
                tokenStaked,
            }}''')
        result = self._post_query(query)
        if len(result['courts']) == 0:
            return None
        else:
            courts = defaultdict()
            for court in result['courts']:
                _court = self._parseCourt(court)
                courts[_court['subcourtID']] = {'parent': _court['parent'],
                                                'activeJurors': _court[
                                                    'activeJurors'],
                                                'tokenStaked': _court[
                                                    'tokenStaked'],
                                                'name': self.getCourtName(
                                                    _court['subcourtID'])}
            return courts

    def getDashboard(self):
        dashboard = self.getKlerosCounters()
        # PNK & ETH Information
        coingecko = CoinGecko()
        pnkInfo = coingecko.getCryptoInfo()

        if pnkInfo is None:
            dashboard['pnkPrice'] = 0
            dashboard['tokenSupply'] = 0,
            dashboard['pnkPctChange'] = 0,
            dashboard['pnkVol24'] = 0,
            dashboard['pnkCircSupply'] = 0,
            dashboard['pnkStakedPercentSupply'] = 0,
            dashboard['pnkStakedPercent'] = 0,
        else:
            dashboard['pnkPrice'] = pnkInfo['market_data']['current_price'][
                'usd']
            dashboard['tokenSupply'] = pnkInfo['market_data']['total_supply']
            dashboard['pnkPctChange'] = pnkInfo['market_data'][
                'price_change_24h']
            dashboard['pnkCircSupply'] = pnkInfo['market_data'][
                'circulating_supply']
            dashboard['pnkVol24'] = pnkInfo['market_data']['total_volume'][
                'usd']
            if dashboard['pnkCircSupply'] > 0:
                dashboard['pnkStakedPercentSupply'] = dashboard[
                    'tokenStaked'] / dashboard['pnkCircSupply']
            else:
                dashboard['pnkStakedPercentSupply'] = None
            if dashboard['tokenSupply'] > 0:
                dashboard['pnkStakedPercent'] = dashboard['tokenStaked'] /\
                    dashboard['tokenSupply']
            else:
                dashboard['pnkStakedPercent'] = None
            # dashboard['courtTable'] = self.getCourtTable()

        if self.network == 'xdai':
            dashboard['ethPrice'] = 1
        else:
            dashboard['ethPrice'] = coingecko.getETHprice()
        return dashboard

    def getDispute(self, disputeNumber):
        query = (
            '{'
            'disputes(where:{id:"' + str(disputeNumber) + '"}) {'
            '    id,'
            '    disputeID,'
            '    arbitrable{id},'
            '    ruled,'
            '    creator{id},'
            '    subcourtID{id},'
            '    currentRulling,'
            '    startTime,'
            '    lastPeriodChange'
            '    period,'
            '    numberOfChoices,'
            '    txid,'
            '    rounds{,'
            '        id,'
            '        winningChoice,'
            '        startTime,'
            '        votes{'
            '            address{id},'
            '            choice,'
            '            voted,'
            '            dispute{id},'
            '            timestamp,'
            '        }'
            '    }'
            '}}'
        )

        result = self._post_query(query)
        if result is None:
            return result
        else:
            dispute = result['disputes'][0]
            return self._parseDispute(dispute)

    def getKlerosCounters(self):
        query = '''{
        klerosCounters {
            disputesCount
            openDisputes
            closedDisputes
            appealPhaseDisputes
            votingPhaseDisputes
            evidencePhaseDisputes
            courtsCount
            numberOfArbitrables
            activeJurors
            inactiveJurors
            drawnJurors
            tokenStaked
            totalTokenRedistributed
            totalETHFees
            totalUSDthroughContract
        }}
        '''
        result = self._post_query(query)
        if result is not None:
            return self._parseKlerosCounters(result['klerosCounters'][0])
        else:
            return result

    def getLastDisputeInfo(self):
        query = (
            '{'
            'disputes(orderBy:disputeID, orderDirection:desc, first:1) {'
            '    id,'
            '    disputeID,'
            '    arbitrable,'
            '    ruled,'
            '    creator{id},'
            '    subcourtID{id},'
            '    currentRulling,'
            '    lastPeriodChange'
            '    numberOfChoices'
            '    period,'
            '    txid,'
            '    rounds{,'
            '        id,'
            '        winningChoice,'
            '        startTime,'
            '        votes{,'
            '            address{id},'
            '            choice,'
            '            voted,'
            '        }'
            '    }'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return result
        else:
            return self._parseDispute(result['disputes'][0])

    def getMostActiveCourt(self, days=7):
        "return the most active court in the last days, by default, a week"
        old_courts_data = self.getCourtDisputesNumberBefore(7)
        courts_data = self.getCourtDisputesNumber()
        if (courts_data is None) and (old_courts_data is None):
            return None

        max_dispute_number = 0
        court_bussiest = None
        for court in courts_data:
            courtID = court['subcourtID']
            oldDisputesNum = 0
            if old_courts_data is not None:
                for oldcourt in old_courts_data:
                    if courtID == oldcourt['subcourtID']:
                        oldDisputesNum = int(oldcourt['disputesNum'])
                        break
            DisputesNum = int(court['disputesNum'])
            delta = DisputesNum - oldDisputesNum
            if delta > max_dispute_number:
                max_dispute_number = delta
                court_bussiest = int(courtID)
        if court_bussiest is not None:
            return self.getCourtName(int(court_bussiest))
        else:
            return None

    def getNetRewardProfile(self, address):
        query = ('{jurors(where: {id: "' + str(address) + '"}) {'
                 + '''tokenAndETHShifts(where:{id_not:""}){
                            ETHAmount,
                            tokenAmount,
                            blockNumber,
                            timestamp
                        }
                    }}
                    '''
                 )
        result = self._post_query(query)
        if result is None:
            return result
        juror = self._parseProfile(result['jurors'][0])
        transfers = juror['tokenAndETHShifts']
        reward = self._getTotalUSDThroughTransfers(transfers)
        usd_gas_cost = self.getProfileGasCost(address)
        return reward - usd_gas_cost

    def getProfile(self, address):
        query = (
            '{jurors(where:{id:"' + str(address).lower() + '"}) {'
            '   id,'
            '   currentStakes{court{id},stake,timestamp,txid},'
            '   totalStaked,'
            '   numberOfDisputesAsJuror,'
            '   numberOfDisputesCreated,'
            '   disputesAsCreator{id,currentRulling,startTime,ruled,txid,'
            '   numberOfChoices}'
            '   allStakes{subcourtID, stake, newTotalStake, timestamp}'
            '   ethRewards, tokenRewards'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return result

        profile_data = result['jurors'][0]
        profile_data['votes'] = self.getAllVotesFromJuror(profile_data['id'])
        return self._parseProfile(profile_data)

    def getProfileGasCost(self, address):
        query = ('{votes(where: {address: "' + str(address) + '"}){'
                 + '''
                    totalGasCost,
                    timestamp
                    }
                    }
                    ''')
        result = self._post_query(query)
        if result is None:
            return 0.
        votes = [self._parseVote(vote) for vote in result['votes']]
        return self._getTotalUSDGasCostInVotes(votes)

    def getRetention(self):
        jurors = self.getAllJurors()
        drawnJurors = []
        still_active_juror = 0
        for juror in jurors:
            if juror['numberOfDisputesAsJuror'] > 0:
                drawnJurors.append(juror)
                if juror['totalStaked'] > 0:
                    still_active_juror += 1

        return still_active_juror / len(drawnJurors) if len(drawnJurors) > 0 \
            else None

    def getStakedByJuror(self, address):
        query = (
            '{'
            'courtStakes(where:{juror:"' + str(address) + '"}) {'
            '    stake,'
            '    court{id}'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return result
        else:
            rawStakes = result['courtStakes']
            stakes = []
            for stake in rawStakes:
                if float(stake['stake']) > 0:
                    stakes.append({'court': int(stake['court']['id']),
                                   'stake': self._wei2eth(stake['stake'])})
            return stakes

    def getTimePeriods(self, courtID):
        query = (
            '{'
            'courts(where:{id:"' + str(courtID) + '"}) {'
            '   timePeriods,'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return result
        else:
            return result['courts'][0]['timePeriods']

    def getTimePeriodsAllCourts(self):
        query = (
            '{'
            'courts {'
            '   id,timePeriods,'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return result
        else:
            timePeriods = {}
            for court in result['courts']:
                timePeriods[court['id']] = court['timePeriods']
            return timePeriods

    def getTotalStakedInCourts(self):
        "Just has to be used to compare with KlerosCounters[tokenStaked]"
        skip = 0
        total = 0
        total_by_court = defaultdict(int)
        while True:
            query = (
                '{courtStakes(first:1000, skip:' + str(skip) + '){'
                '   stake'
                '   court{id}'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                return None
            courtStakes = result['courtStakes']
            if len(courtStakes) == 0:
                break
            else:
                for courtStake in courtStakes:
                    total += self._wei2eth(courtStake['stake'])
                    total_by_court[courtStake['court']['id']] += self._wei2eth(
                        courtStake['stake'])
                if len(courtStakes) < 1000:
                    # no need to keep in the loop, all the items where queried
                    break
                else:
                    skip += len(courtStakes)
        return total, total_by_court

    def getTotalStakedInCourtAndChildrens(self, courtID):
        "Just has to be used to compare with KlerosCounters[tokenStaked]"
        allcourts = self.getCourtChildrens(courtID)
        allcourts.add(str(courtID))

        skip = 0
        total = 0
        while True:
            query = (
                '{courtStakes(first:1000, skip:'
                + str(skip) + ',where:{court_in:'
                + str(list(allcourts)).replace("'", '"')
                + '}){'
                '   stake'
                '   court{id}'
                '}}'
            )
            result = self._post_query(query)
            courtStakes = result['courtStakes']
            if len(courtStakes) == 0:
                break
            else:
                for courtStake in courtStakes:
                    total += self._wei2eth(courtStake['stake'])
                skip += len(courtStakes)
        return total

    def getTotalUSD(self):
        transfers = self.getAllTransfers()
        if transfers is None:
            return 0
        return self._getTotalUSDThroughTransfers(transfers)

    def getTransfersFromArbitrable(self, address):
        query = ('{arbitrables(where: {id: "' + str(address) + '"}) {'
                 + '''
                    disputes {
                        id,
                        TokenAndETHShifts(where:{id_not:""}){
                            ETHAmount,
                            tokenAmount,
                            blockNumber,
                            timestamp
                        }
                    }
                    }
                }''')
        result = self._post_query(query)
        if result is None:
            return result
        arbitrables_disputes = result['arbitrables'][0]
        transfers = []
        for dispute in arbitrables_disputes['disputes']:
            dispute = self._parseDispute(dispute)
            transfers.extend(dispute['TokenAndETHShifts'])
        return transfers

    def getTransfersFromCourt(self, courtID):
        query = ('{courts(where: {id: "' + str(courtID) + '"}) {'
                 + '''
                    disputes {
                        id,
                        TokenAndETHShifts(where:{id_not:""}){
                            ETHAmount,
                            tokenAmount,
                            blockNumber,
                            timestamp
                        }
                    }
                    }
                }''')
        result = self._post_query(query)
        if result is None:
            return result
        court_disputes = result['courts'][0]
        transfers = []
        for dispute in court_disputes['disputes']:
            dispute = self._parseDispute(dispute)
            transfers.extend(dispute['TokenAndETHShifts'])
        return transfers

    def getTransfersFromProfile(self, address):
        query = ('{jurors(where: {id: "' + str(address) + '"}) {'
                 + '''tokenAndETHShifts(where:{id_not:""}){
                            ETHAmount,
                            tokenAmount,
                            blockNumber,
                            timestamp
                        }
                    }
                    }
                    ''')
        result = self._post_query(query)
        if result is None:
            return result
        juror = self._parseProfile(result['jurors'][0])
        return juror['tokenAndETHShifts']

    def getUSDThroughArbitrable(self, arbitrable):
        transfers = self.getTransfersFromArbitrable(arbitrable)
        if transfers is None:
            return 0
        return self._getTotalUSDThroughTransfers(transfers)

    def getUSDThroughCourt(self, courtID):
        transfers = self.getTransfersFromCourt(courtID)
        if transfers is None:
            return 0
        return self._getTotalUSDThroughTransfers(transfers)

    def getUSDThroughProfile(self, address):
        transfers = self.getTransfersFromProfile(address)
        if transfers is None:
            return 0
        return self._getTotalUSDThroughTransfers(transfers)

    def getWhenPeriodEnd(self, dispute, courtID, timesPeriods=None):
        """
        Return the datetime when ends current period of the dispute.
        Returns None if dispute it's in execution period
        """
        if dispute['period'] == 'execution':
            return 'Already Executed'
        else:
            if timesPeriods is None:
                timesPeriods = self.getTimePeriods(int(courtID))
            lastPeriodChange = datetime.fromtimestamp(
                int(dispute['lastPeriodChange']))
            periodlength = int(timesPeriods[self._period2number(dispute[
                'period'])])
            return lastPeriodChange + timedelta(seconds=periodlength)

    def readPolicy(self, courtID):
        query = (
            '{policyUpdates(where:{id:"' + str(courtID) + '"}) {'
            '    subcourtID,'
            '    policy,'
            '    contractAddress,'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return result
        else:
            return result['policyUpdates'][0]


class KBSubscriptionsSubgraph(Subgraph):
    def __init__(self, network='kovan'):
        super(KBSubscriptionsSubgraph, self).__init__(network)
        self.subgraph_name = 'salgozino/klerosboard-subscriptions'
        self.subgraph_node += self.subgraph_name
        self.year_donor_factor = 20  # Dividor of monthly fee to allow a donor for a year

    def _parseDonation(self, donation):
        keys = donation.keys()
        if 'donor' in keys:
            donation['donor'] = donation['donor']['id']
        if 'amount' in keys:
            donation['amount'] = self._wei2eth(donation['amount'])
        if 'ethToUBIBurner' in keys:
            donation['ethToUBIBurner'] = self._wei2eth(
                donation['ethToUBIBurner'])
        if 'ethToMaintainance' in keys:
            donation['ethToMaintainance'] = self._wei2eth(
                donation['ethToMaintainance'])
        if 'timestamp' in keys:
            try:
                donation['timestamp'] = int(donation['timestamp'])
            except TypeError:
                donation['timestamp'] = None
        return donation

    def _parseDonor(self, donor):
        keys = donor.keys()
        if 'totalDonated' in keys:
            donor['totalDonated'] = self._wei2eth(donor['totalDonated'])
        if 'lastDonated' in keys:
            donor['lastDonated'] = self._wei2eth(donor['lastDonated'])
        if 'lastDonatedTimestamp' in keys:
            try:
                donor['lastDonatedTimestamp'] = int(
                    donor['lastDonatedTimestamp'])
            except TypeError:
                donor['lastDonatedTimestamp'] = None
        if 'totalETHToUBIBurner' in keys:
            donor['totalETHToUBIBurner'] = self._wei2eth(
                donor['totalETHToUBIBurner']
            )
        if 'donations' in keys:
            donations = donor['donations']
            for donation in donations:
                donation = self._parseDonation(donation)
        return donor

    def _parseParameters(self, parameters):
        keys = parameters.keys()
        if 'totalDonated' in keys:
            parameters['totalDonated'] = self._wei2eth(parameters[
                'totalDonated'])
        if 'totalETHToUBIBurner' in keys:
            parameters['totalETHToUBIBurner'] = self._wei2eth(
                parameters['totalETHToUBIBurner'])
        if 'maintenanceFeeMultiplier' in keys:
            parameters['maintenanceFeeMultiplier'] = int(
                parameters['maintenanceFeeMultiplier'])
        if 'donationPerMonth' in keys:
            parameters['donationPerMonth'] = self._wei2eth(
                parameters['donationPerMonth'])
        return parameters

    def getAllDonors(self):
        initDonor = ""
        donors = []
        while True:
            query = (
                '{donors(where:{id_gt:"' + str(initDonor) + '"},'
                'orderBy:id, orderDirection:asc, first:1000){'
                'id,totalDonated,lastDonated,lastDonatedTimestamp,'
                'totalETHToUBIBurner,'
                'donations{id,amount,timestamp}'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentDonors = result['donors']
                donors.extend(currentDonors)
                if len(currentDonors) < 1000:
                    break
                initDonor = currentDonors[-1]['id']
        return [self._parseDonor(donor)
                for donor in donors]

    def getDonor(self, address):
        query = (
            '{donors(where:{id:"' + str(address.lower()) + '"}){'
            'id,totalDonated,lastDonated,lastDonatedTimestamp,'
            'totalETHToUBIBurner,'
            'donations{id,amount,timestamp}'
            '}}'
        )
        result = self._post_query(query)
        if result is None:
            return None
        return self._parseDonor(result['donors'][0])

    def getDonorLastDonations(self, month=datetime.today().month):
        first_day = datetime.today().replace(
            month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        initDonation = int(first_day.replace(tzinfo=timezone.utc).timestamp())
        donations = []
        while True:
            query = (
                '{donations(where:{timestamp_gte:"' + str(initDonation) + '"},'
                'orderBy:timestamp, orderDirection:asc, first:1000, ){'
                'amount,timestamp,donor{id}'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentDonations = result['donations']
                donations.extend(currentDonations)
                if len(currentDonations) < 1000:
                    break
                initDonation = currentDonations[-1]['timestamp']
        donations_parsed = [self._parseDonation(donor)
                            for donor in donations]
        totalDonated = 0
        for donation in donations_parsed:
            totalDonated += donation['amount']
        return totalDonated

    def getDonorLastYearDonorDonations(self, address):
        year_go = datetime.today() - timedelta(days=365)
        initDonation = int(year_go.replace(tzinfo=timezone.utc).timestamp())
        donations = []
        while True:
            query = (
                '{donations(where:{timestamp_gt:"' + str(initDonation)
                + '", donor:"' + str(address.lower()) + '"},'
                'orderBy:timestamp, orderDirection:asc, first:1000, ){'
                'amount,timestamp,donor{id}'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentDonations = result['donations']
                donations.extend(currentDonations)
                if len(currentDonations) < 1000:
                    break
                initDonation = currentDonations[-1]['timestamp']
        donations_parsed = [self._parseDonation(donor)
                            for donor in donations]
        totalDonated = 0
        for donation in donations_parsed:
            totalDonated += donation['amount']
        return totalDonated

    def getParameters(self):
        query = ('''
                {kbsubscriptions(first:1) {
                totalDonated,
                totalETHToUBIBurner,
                maintenanceFeeMultiplier,
                owner,
                maintainer,
                donationPerMonth,
                }}
                '''
                 )
        result = self._post_query(query)
        if result is None:
            return None
        return self._parseParameters(result['kbsubscriptions'][0])

    def getMonthDonations(self,
                          month=datetime.today().month,
                          year=datetime.today().year):
        first_day = datetime.today().replace(
            year=year,
            month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        initDonation = int(first_day.replace(tzinfo=timezone.utc).timestamp())
        donations = []
        while True:
            query = (
                '{donations(where:{timestamp_gte:"' + str(initDonation) + '"},'
                'orderBy:timestamp, orderDirection:asc, first:1000, ){'
                'amount,timestamp,donor{id}'
                '}}'
            )
            result = self._post_query(query)
            if result is None:
                break
            else:
                currentDonations = result['donations']
                donations.extend(currentDonations)
                if len(currentDonations) < 1000:
                    break
                initDonation = currentDonations[-1]['id']
        donations_parsed = [self._parseDonation(donor)
                            for donor in donations]
        totalDonated = 0
        for donation in donations_parsed:
            totalDonated += donation['amount']
        return totalDonated

    def getDonationPerMonth(self):
        query = ('''
                {kbsubscriptions(first:1) {
                donationPerMonth,
                }}
                '''
                 )
        result = self._post_query(query)
        if result is None:
            return None
        params = self._parseParameters(result['kbsubscriptions'][0])
        return params['donationPerMonth']

    def donationLastMonthStatus(self):
        donationPerMonth = self.getDonationPerMonth()
        today = datetime.today()
        year = today.year
        month = today.month - 1
        if month == 0:
            month = 12
            year -= 1
        totalDonatedInMonth = self.getMonthDonations(
            month=month, year=year)
        return {'donationPerMonth': donationPerMonth,
                'totalDonatedInMonth': totalDonatedInMonth,
                'percentage': totalDonatedInMonth / donationPerMonth * 100}

    def donationMonthStatus(self):
        donationPerMonth = self.getDonationPerMonth()
        totalDonatedInMonth = self.getMonthDonations()
        return {'donationPerMonth': donationPerMonth,
                'totalDonatedInMonth': totalDonatedInMonth,
                'percentage': totalDonatedInMonth / donationPerMonth * 100}

    def getMaintainanceFee(self):
        query = ('''
                {kbsubscriptions(first:1) {
                maintenanceFeeMultiplier,
                }}
                '''
                 )
        result = self._post_query(query)
        if result is None:
            return None
        params = self._parseParameters(result['kbsubscriptions'][0])
        return params['maintenanceFeeMultiplier'] / 10000

    def isDonor(self, address):
        total_donated = self.getDonorLastYearDonorDonations(address)
        donation_per_month = self.getDonationPerMonth()
        if donation_per_month is None:
            # If there is an error getting the value, return False
            return False
        return total_donated >= donation_per_month / self.year_donor_factor
