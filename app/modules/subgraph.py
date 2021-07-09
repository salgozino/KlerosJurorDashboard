from weakref import KeyedRef
import requests
import os
import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict

from app.modules.oracles import CoinGecko
from app.modules.web3_node import web3Node

try:
    subgraph_id = os.environ['SUBGRAPH_ID']
except TypeError:
    print("No SUBGRAPH_ID found, using hardcoded value")
    subgraph_id = 'QmTTcbUgfcCXRKYvk7Yt23ys1fxNv1JuJLkasV57PATQts'

# Node definitions
subgraph_node = 'https://api.thegraph.com/subgraphs/id/' + subgraph_id
subgraph_index_node = 'https://api.thegraph.com/index-node/graphql'
try:
    ipfs_node = os.getenv['IPFS_NODE']
except TypeError:
    ipfs_node = 'https://ipfs.kleros.io'

logger = logging.getLogger(__name__)


def _calculateVoteStake(minStake, alpha):
    return float(alpha)*(10**-4)*float(minStake)


def _getBlockNumberbefore(days=30):
    """
    Get the block number of n days ago. By default, 30 days.
    Now, it's simple considering an average time of 17 seconds.
    This should be improved
    """
    # TODO!, improve this function!
    averageBlockTime = 15  # in seconds
    currentBlockNumber = web3Node.web3.eth.blockNumber
    return int(currentBlockNumber - days*24*60*60/averageBlockTime)


def _getRoundNumFromID(roundID):
    return int(roundID.split('-')[1])


def _parseCourt(court):
    # get a query of a courts and parse values to the correct format
    if court is None:
        return None
    keys = court.keys()
    if 'tokenStaked' in keys:
        court['tokenStaked'] = _wei2eth(court['tokenStaked'])
    if 'parent' in keys:
        if court['parent'] is not None:
            court['parent'] = int(court['parent']['id'])
        else:
            court['parent'] = None
    else:
        court['parent'] = None
    if 'activeJurors' in keys:
        court['activeJurors'] = int(court['activeJurors'])
    if 'minStake' in keys:
        court['minStake'] = _wei2eth(float(court['minStake']))
    if 'feeForJuror' in keys:
        court['feeForJuror'] = _wei2eth(court['feeForJuror'])
    if 'alpha' in keys:
        court['alpha'] = float(court['alpha'])
    if 'alpha' in keys and 'minStake' in keys:
        court['voteStake'] = _calculateVoteStake(court['minStake'],
                                                 court['alpha'])
    if 'disputesNum' in keys:
        court['disputesNum'] = int(court['disputesNum'])
    if 'disputesOngoing' in keys:
        court['disputesOngoing'] = int(court['disputesOngoing'])
    if 'disputesClosed' in keys:
        court['disputesClosed'] = int(court['disputesClosed'])
    if 'subcourtID' in keys:
        court['subcourtID'] = int(court['subcourtID'])
    if 'totalETHFees' in keys:
        court['totalETHFees'] = _wei2eth(court['totalETHFees'])
    if 'totalTokenRedistributed' in keys:
        court['totalTokenRedistributed'] = _wei2eth(
            court['totalTokenRedistributed'])
    if 'childs' in keys:
        if court['childs'] is not None:
            childs = []
            for child in court['childs']:
                childs.append(child['id'])
        court['childs'] = childs
    return court


def _parseDispute(dispute, timePeriods=None):
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
    if ('period' in keys) and ('subcourtID' in keys):
        dispute['periodEnds'] = getWhenPeriodEnd(dispute,
                                                 subcourtID,
                                                 timePeriods
                                                 )
    if 'startTime' in keys:
        dispute['startTime'] = int(dispute['startTime'])
    if 'rounds' in keys:
        vote_count = {}
        # initialize a dict with 0 as default value if the key doesn't exist
        unique_vote_count = defaultdict(int)
        unique_jurors = set()
        for round in dispute['rounds']:
            # initialize a dict with 0 as default value
            vote_count[round['id']] = defaultdict(int)
            votes = round['votes']
            for vote in votes:
                vote = _parseVote(vote)
                vote_count[round['id']][vote['vote_str']] += 1
                if vote['address'].lower() not in unique_jurors:
                    unique_vote_count[vote['vote_str']] += 1
                    unique_jurors.add(vote['address'].lower())
            # easier to read the jurors with multiple votes
            round['votes'] = sorted(round['votes'], key=lambda x: x['address'])
            if 'id' in round.keys():
                round['round_num'] = _getRoundNumFromID(round['id'])
        dispute['vote_count'] = vote_count
        dispute['unique_vote_count'] = unique_vote_count
        dispute['unique_jurors'] = unique_jurors
    return dispute


def _parseKlerosCounters(kc):
    float_fields = ['tokenStaked', 'totalETHFees', 'totalTokenRedistributed']
    for key, value in kc.items():
        if key in float_fields:
            kc[key] = _wei2eth(value)
        else:
            kc[key] = int(value)
    return kc


def _parseCourtStake(courtStake):
    keys = courtStake.keys()
    if 'stake' in keys:
        courtStake['stake'] = _wei2eth(courtStake['stake'])
    if 'court' in keys:
        courtID = int(courtStake['court']['id'])
        courtStake['court'] = courtID
    if 'juror' in keys:
        courtStake['address'] = courtStake['juror']['id']
    if 'timestamp' in keys:
        courtStake['timestamp'] = int(courtStake['timestamp'])
        courtStake['date'] = datetime.fromtimestamp(
            courtStake['timestamp']
            )
    return courtStake


def _parseProfile(profile):
    keys = profile.keys()
    if 'numberOfDisputesAsJuror' in keys:
        profile['numberOfDisputesAsJuror'] = profile[
            'numberOfDisputesAsJuror'
            ]
    if 'currentStakes' in keys:
        for stake in profile['currentStakes']:
            stake = _parseCourtStake(stake)
    if 'totalStaked' in keys:
        profile['totalStaked'] = _wei2eth(profile['totalStaked'])

    profile['coherent_votes'] = 0
    profile['ruled_cases'] = 0
    if 'votes' in keys:
        for vote in profile['votes']:
            vote = _parseVote(vote)
            if vote['dispute']['ruled']:
                if vote['dispute']['currentRulling'] == vote['choice']:
                    profile['coherent_votes'] = profile['coherent_votes'] + 1
                profile['ruled_cases'] += 1

    if profile['ruled_cases'] > 0:
        profile['coherency'] = profile['coherent_votes']/profile[
            'ruled_cases'
            ]
    else:
        profile['coherency'] = None

    disputes_as_creator = []
    if 'disputesAsCreator' in keys:
        for dispute in profile['disputesAsCreator']:
            disputes_as_creator.append(_parseDispute(dispute))
        profile['disputesAsCreator'] = disputes_as_creator
        print(profile['disputesAsCreator'])
    return profile


def _parseVote(vote):
    keys = vote.keys()
    print(vote)
    if 'address' in keys:
        vote['address'] = vote['address']['id']
    if 'choice' in keys:
        vote['choice'] = int(vote['choice'])
    if 'dispute' in keys:
        if isinstance(vote['dispute'], dict):
            vote['dispute'] = _parseDispute(vote['dispute'])
    if ('choice' in keys) and ('voted' in keys) and ('dispute' in keys):
        vote['vote_str'] = _vote_mapping(vote['choice'],
                                         vote['voted'],
                                         vote['dispute'])
    if 'round' in keys:
        if 'id' in vote['round'].keys():
            vote['roundNumber'] = _getRoundNumFromID(vote['round']['id'])
    return vote


def _period2number(period):
    period_map = {
        'execution': 4,
        'appeal': 3,
        'vote': 2,
        'commit': 1,
        'evidence': 0}
    return period_map[period]


def _post_query(query, subgraph_node=subgraph_node):
    response = requests.post(subgraph_node, json={'query': query})
    data = response.json()
    try:
        data = data['data']
    except KeyError:
        logger.error(('Error trying to jsonise the response data of this '
                     'query: %s'),
                     query)
        logger.error(data['errors'])
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


def _vote_mapping(choice, voted, dispute=None):
    """
    Return the text of the vote choice.
    TODO!, use the metaEvidence of the dispute,
    currently it's just fixed to Refuse, Yes, No or Pending
    """
    if voted:
        vote_map = {0: 'Refuse to Arbitrate',
                    1: 'Yes',
                    2: 'No'}
        return vote_map[choice]
    else:
        return 'Pending'


def _wei2eth(gwei):
    return float(gwei)*10**-18


def court2table(court, pnkUSDPrice):
    """
    Fields of the Table used in the main view of klerosboard
    """
    return {'Jurors': court['activeJurors'],
            'Total Staked': court['tokenStaked'],
            'Min Stake': court['minStake'],
            'Fee For Juror': court['feeForJuror'],
            'Vote Stake': court['voteStake'],
            'Open Disputes': court['disputesOngoing'],
            'Min Stake in USD': court['minStake']*pnkUSDPrice,
            'Total Disputes': court['disputesNum'],
            'id': court['subcourtID'],
            'Name': getCourtName(court['subcourtID'])
            }


def getAdoption():
    "return the number of new jurors in the last 30 days"
    query = (
        '{klerosCounters{'
        '   activeJurors,'
        '   inactiveJurors'
        '}}'
    )
    current_result = _post_query(query)
    if current_result is None:
        return 0
    result = current_result['klerosCounters'][0]

    bn = _getBlockNumberbefore(30)
    query = (
        '{klerosCounters(block:{number:'+str(bn)+'}){'
        '   activeJurors,'
        '   inactiveJurors'
        '}}'
    )
    # before_result = requests.post(subgraph_node, json={'query': query})
    before_result = _post_query(query)
    if before_result is not None:
        old_result = before_result['klerosCounters'][0]
    else:
        return 0
    newTotal = int(result['activeJurors']) + int(result['inactiveJurors'])
    oldTotal = int(old_result['activeJurors']) + int(old_result[
        'inactiveJurors'])
    return newTotal-oldTotal


def getAllCourts():
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
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        courts = []
        for court in result.json()['data']['courts']:
            courts.append(_parseCourt(court))
        return courts


def getAllCourtsDaysBefore(days=30):
    blockNumber = _getBlockNumberbefore(days)
    query = (
        '{courts(block:{number:'+str(blockNumber)+'}){'
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
    result = requests.post(subgraph_node, json={'query': query})
    if 'errors' in result.json().keys():
        return None
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        return result.json()['data']['courts']


def getAllCourtDisputes(courtID):
    initDispute = 0
    disputes = []
    while True:
        query = (
            '{disputes(where:{subcourtID:"' +
            str(courtID) +
            '",id_gt:'+str(initDispute)+'}){'
            'id,subcourtID{id},currentRulling,ruled,startTime,'
            'period,lastPeriodChange'
            '}}'
        )
        result = requests.post(subgraph_node, json={'query': query})
        if len(result.json()['data']['disputes']) == 0:
            break
        else:
            currentDisputes = result.json()['data']['disputes']
            disputes.extend(currentDisputes)
            initDispute = int(currentDisputes[-1]['id'])

    parsed_disputes = []
    for dispute in disputes:
        parsed_disputes.append(_parseDispute(dispute))
    return parsed_disputes


def getAllDisputes():
    initDispute = -1
    disputes = []
    while True:
        query = (
            '{disputes(where:{id_gt:'+str(initDispute)+'}){'
            'id,subcourtID{id},currentRulling,ruled,startTime,'
            'period,lastPeriodChange'
            '}}'
        )
        result = requests.post(subgraph_node, json={'query': query})
        if len(result.json()['data']['disputes']) == 0:
            break
        else:
            currentDisputes = result.json()['data']['disputes']
            disputes.extend(currentDisputes)
            initDispute = int(currentDisputes[-1]['id'])
    courtTimePeriods = getTimePeriodsAllCourts()
    parsed_disputes = []
    for dispute in disputes:
        subcourtID = dispute['subcourtID']['id']
        parsed_disputes.append(_parseDispute(dispute,
                                             courtTimePeriods[subcourtID]))
    return parsed_disputes


def getAllVotesFromJuror(address):
    initDispute = 0
    votes = []
    while True:
        query = ('{votes(where:{address:"' +
                 str(address)+'",dispute_gt:"' +
                 str(initDispute) +
                 '"}){'
                 'dispute{id,currentRulling,ruled,startTime},choice,voted'
                 ',round{id}'
                 '}}'
                 )
        result = requests.post(subgraph_node, json={'query': query})

        if len(result.json()['data']['votes']) == 0:
            break
        else:
            currentVotes = result.json()['data']['votes']
            votes.extend(currentVotes)
            initDispute = int(currentVotes[-1]['dispute']['id'])
    for vote in votes:
        vote = _parseVote(vote)
    return votes


def getCourt(courtID):
    query = (
        '{'
        'courts(where:{id:"'+str(courtID)+'"}) {'
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
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        court = result.json()['data']['courts'][0]
        return _parseCourt(court)


def getCourtChildrens(courtID):
    childrens = set()
    search_courts = set([str(courtID)])
    while len(search_courts) > 0:
        query = (
            '{courts(where:{id:"'+str(search_courts.pop())+'"}){'
            '   childs{id},'
            '}}'
        )
        result = requests.post(subgraph_node, json={'query': query})
        if len(result.json()['data']['courts']) > 0:
            data = result.json()['data']['courts'][0]
            for child in data['childs']:
                childrens.add(child['id'])
                search_courts.add(child['id'])
    return childrens


def getCourtDaysBefore(courtID, days=30):
    blockNumber = _getBlockNumberbefore(days)
    query = (
        '{courts(block:{number:' +
        str(blockNumber)+'},where:{id:"' +
        str(courtID) +
        '"}){'
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
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        return _parseCourt(result.json()['data']['courts'][0])


def getCourtDisputesNumber():
    query = (
        '{courts{'
        '   disputesNum'
        '   subcourtID'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if 'errors' in result.json().keys():
        return None
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        courts = []
        for court in result.json()['data']['courts']:
            courts.append(_parseCourt(court))
        return courts


def getCourtPolicy(courtID):
    policy = readPolicy(courtID)
    if policy is None:
        return None
    if 'https://' in policy['policy']:
        # prevent errors
        return None
    else:
        response = requests.get(ipfs_node+policy['policy'])
    return response.json()


def getCourtTable():
    courtsInfo = {}
    oldcourtsDisputes = {}
    courts = getAllCourts()
    pnkUSDprice = CoinGecko().getPNKprice()

    oldCourts = getCourtDisputesNumberBefore(30)
    if oldCourts is not None:
        for court in oldCourts:
            oldcourtsDisputes[court['subcourtID']] = court['disputesNum']
    for court in courts:
        courtID = court['subcourtID']
        courtsInfo[courtID] = court2table(court, pnkUSDprice)
        if oldCourts is not None:
            diff = courtsInfo[courtID]['Total Disputes'] - \
                    oldcourtsDisputes[courtID]
        else:
            diff = courtsInfo[courtID]['Total Disputes']
        courtsInfo[courtID]['Disputes in the last 30 days'] = diff
    return courtsInfo


def getCourtTotalStaked(courtID):
    query = (
        '{courts(where:{id:"'+str(courtID)+'"}){'
        '   tokenStaked,'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        return _wei2eth(result.json()['data']['courts'][0]['tokenStaked'])


def getCourtWithDisputes(courtID):
    court = getCourt(courtID)
    if court is None:
        return None
    court['disputes'] = getAllCourtDisputes(courtID)
    return court


def getCourtDisputesNumberBefore(days=30):
    blockNumber = _getBlockNumberbefore(days)
    query = (
        '{courts(block:{number:'+str(blockNumber)+'}){'
        '   disputesNum'
        '   subcourtID'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if 'errors' in result.json().keys():
        return None
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        courts = result.json()['data']['courts']
        parsed_courts = []
        for court in courts:
            parsed_courts.append(_parseCourt(court))
        return parsed_courts


def getCourtName(courtID):
    file_path = 'app/lib/court_policies.json'
    courtID = str(courtID)
    if os.path.isfile(file_path):
        with open(file_path) as jsonFile:
            policies = json.load(jsonFile)
            if courtID in policies.keys():
                if 'name' in policies[courtID]:
                    return policies[courtID]['name']
    return str(courtID)


def getDashboard():
    dashboard = getKlerosCounters()
    dashboard['retention'] = getRetention()
    dashboard['adoption'] = getAdoption()
    mostActiveCourt = getMostActiveCourt()
    if mostActiveCourt is not None:
        mostActiveCourt = getCourtName(int(mostActiveCourt))
    else:
        mostActiveCourt = "No new cases in the last 7 days"
    dashboard['mostActiveCourt'] = mostActiveCourt
    # PNK & ETH Information
    coingecko = CoinGecko()
    pnkInfo = coingecko.getCryptoInfo()
    dashboard['ethPrice'] = coingecko.getETHprice()
    dashboard['pnkPrice'] = pnkInfo['market_data']['current_price']['usd']
    dashboard['tokenSupply'] = pnkInfo['market_data']['total_supply']
    dashboard['pnkPctChange'] = pnkInfo['market_data']['price_change_24h']
    dashboard['pnkCircSupply'] = pnkInfo['market_data']['circulating_supply']
    dashboard['pnkVol24'] = pnkInfo['market_data']['total_volume']['usd']
    if dashboard['pnkCircSupply'] > 0:
        dashboard['pnkStakedPercentSupply'] = dashboard['tokenStaked'] / \
         dashboard['pnkCircSupply']
    else:
        dashboard['pnkStakedPercentSupply'] = None
    if dashboard['tokenSupply'] > 0:
        dashboard['pnkStakedPercent'] = dashboard['tokenStaked'] /\
            dashboard['tokenSupply']
    else:
        dashboard['pnkStakedPercent'] = None
    dashboard['courtTable'] = getCourtTable()
    return dashboard


def getDispute(disputeNumber):
    query = (
        '{'
        'disputes(where:{id:"'+str(disputeNumber)+'"}) {'
        '    id,'
        '    disputeID,'
        '    arbitrable,'
        '    ruled,'
        '    creator{id},'
        '    subcourtID{id},'
        '    currentRulling,'
        '    lastPeriodChange'
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
        '            dispute{id},'
        '        }'
        '    }'
        '}}'
    )

    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['disputes']) == 0:
        return None
    else:
        dispute = result.json()['data']['disputes'][0]
        return _parseDispute(dispute)


def getActiveJurorsFromCourt(courtID):
    query = (
        '{'
        'courtStakes(where:{court:"'+str(courtID)+'",stake_gt:0}, first:1000){'
        '    stake,'
        '    juror {id}'
        '}}'
    )

    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courtStakes']) == 0:
        return []
    else:
        courtStakes = result.json()['data']['courtStakes']
        return [_parseCourtStake(cs) for cs in courtStakes]


def getKlerosCounters():
    query = '''{
    klerosCounters {
        disputesCount
        openDisputes
        closedDisputes
        appealPhaseDisputes
        votingPhaseDisputes
        evidencePhaseDisputes
        courtsCount
        activeJurors
        inactiveJurors
        drawnJurors
        tokenStaked
        totalTokenRedistributed
        totalETHFees
        totalUSDthroughContract
    }}
    '''
    # result = requests.post(subgraph_node, json={'query': query})
    result = _post_query(query)
    return _parseKlerosCounters(result['klerosCounters'][0])


def getLastDisputeInfo():
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
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['disputes']) == 0:
        return None
    else:
        return _parseDispute(result.json()['data']['disputes'][0])


def getMostActiveCourt(days=7):
    "return the most active court in the last days, by default, a week"
    old_courts_data = getCourtDisputesNumberBefore(7)
    courts_data = getCourtDisputesNumber()
    if (courts_data is None) or (old_courts_data is None):
        return None

    max_dispute_number = 0
    court_bussiest = None
    for court in courts_data:
        courtID = court['subcourtID']
        oldDisputesNum = 0
        for oldcourt in old_courts_data:
            if courtID == oldcourt['subcourtID']:
                oldDisputesNum = int(oldcourt['disputesNum'])
        DisputesNum = int(court['disputesNum'])
        delta = DisputesNum - oldDisputesNum
        if delta > max_dispute_number:
            max_dispute_number = delta
            court_bussiest = int(courtID)
    return court_bussiest


def getProfile(address):
    query = (
        '{jurors(where:{id:"'+str(address).lower()+'"}) {'
        '   id,'
        '   currentStakes{court{id},stake,timestamp,txid},'
        '   totalStaked,'
        '   numberOfDisputesAsJuror,'
        '   numberOfDisputesCreated,'
        '   disputesAsCreator{id,currentRulling,startTime,ruled,txid}'
        '}}'
    )
    result = _post_query(query)
    if result is None:
        return result

    profile_data = result['jurors'][0]
    profile_data['votes'] = getAllVotesFromJuror(profile_data['id'])
    return _parseProfile(profile_data)


def getRetention():
    # TODO!
    return None


def getStakedByJuror(address):
    query = (
        '{'
        'courtStakes(where:{juror:"'+str(address)+'"}) {'
        '    stake,'
        '    court{id}'
        '}}'
    )
    # result = requests.post(subgraph_node, json={'query': query})
    result = _post_query(query)
    if result is None:
        return result
    else:
        rawStakes = result['courtStakes']
        stakes = []
        for stake in rawStakes:
            if float(stake['stake']) > 0:
                stakes.append({'court': int(stake['court']['id']),
                               'stake': _wei2eth(stake['stake'])})
        return stakes


def getStatus():
    """
    Return the status of the subgraph
    """
    query = """
    {
    indexingStatusForCurrentVersion(subgraphName: "salgozino/klerosboard") {
        synced
        health
        fatalError {
        message
        block {
            number
            hash
        }
        handler
        }
        chains {
        chainHeadBlock {
            number
        }
        latestBlock {
            number
        }
        }
        }
    }
    """
    result = _post_query(query=query, subgraph_node=subgraph_index_node)
    if result is None:
        return {'status': ' Updated',
                'last_block': 0,
                'deployment': 0,
                'error': 'Error querying the index-node for status'}
    result = result['indexingStatusForCurrentVersion']
    last_block_number = int(result['chains'][0]['chainHeadBlock']['number'])
    subgraph_block_number = int(result['chains'][0]['latestBlock']['number'])
    if abs(last_block_number - subgraph_block_number) < 20:
        # ~ 5 min of delay allowed
        return {'status': ' Updated',
                'last_block': subgraph_block_number,
                'error': result['fatalError']}
    else:
        return {'status': 'Updating',
                'last_block': subgraph_block_number,
                'error': result['fatalError']}


def getTimePeriods(courtID):
    query = (
        '{'
        'courts(where:{id:"'+str(courtID)+'"}) {'
        '   timePeriods,'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        return result.json()['data']['courts'][0]['timePeriods']


def getTimePeriodsAllCourts():
    query = (
        '{'
        'courts {'
        '   id,timePeriods,'
        '}}'
    )
    # result = requests.post(subgraph_node, json={'query': query})
    result = _post_query(query)
    if result is None:
        return result
    else:
        timePeriods = {}
        for court in result['courts']:
            timePeriods[court['id']] = court['timePeriods']
        return timePeriods


def getTotalStakedInCourts():
    "Just has to be used to compare with KlerosCounters[tokenStaked]"
    skip = 0
    total = 0
    total_by_court = defaultdict(int)
    while True:
        query = (
            '{courtStakes(first:1000, skip:'+str(skip)+'){'
            '   stake'
            '   court{id}'
            '}}'
        )
        result = requests.post(subgraph_node, json={'query': query})
        courtStakes = result.json()['data']['courtStakes']
        if len(courtStakes) == 0:
            break
        else:
            for courtStake in courtStakes:
                total += _wei2eth(courtStake['stake'])
                total_by_court[courtStake['court']['id']] += _wei2eth(
                    courtStake['stake'])
            if len(courtStakes) < 1000:
                # no need to keep in the loop, all the items where queried
                break
            else:
                skip += len(courtStakes)
    return total, total_by_court


def getTotalStakedInCourtAndChildrens(courtID):
    "Just has to be used to compare with KlerosCounters[tokenStaked]"
    allcourts = getCourtChildrens(courtID)
    allcourts.add(str(courtID))

    skip = 0
    total = 0
    while True:
        query = (
            '{courtStakes(first:1000, skip:' +
            str(skip) +
            ',where:{court_in:' +
            str(list(allcourts)).replace("'", '"') +
            '}){'
            '   stake'
            '   court{id}'
            '}}'
        )
        result = requests.post(subgraph_node, json={'query': query})
        courtStakes = result.json()['data']['courtStakes']
        if len(courtStakes) == 0:
            break
        else:
            for courtStake in courtStakes:
                total += _wei2eth(courtStake['stake'])
            skip += len(courtStakes)
    return total


def getWhenPeriodEnd(dispute, courtID, timesPeriods=None):
    """
    Return the datetime when ends current period of the dispute.
    Returns None if dispute it's in execution period
    """
    if dispute['period'] == 'execution':
        return 'Already Executed'
    else:
        if timesPeriods is None:
            timesPeriods = getTimePeriods(int(courtID))
        lastPeriodChange = datetime.fromtimestamp(
            int(dispute['lastPeriodChange'])
            )
        periodlength = int(timesPeriods[_period2number(dispute['period'])])
        return lastPeriodChange + timedelta(seconds=periodlength)


def readPolicy(courtID):
    query = (
        '{policyUpdates(where:{id:"'+str(courtID)+'"}) {'
        '    subcourtID,'
        '    policy,'
        '    contractAddress,'
        '}}'
    )
    # result = requests.post(subgraph_node, json={'query': query})
    result = _post_query(query)
    if result is None:
        return result
    else:
        return result['policyUpdates'][0]
