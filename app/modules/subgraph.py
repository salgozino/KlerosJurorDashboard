import requests
import os
from datetime import datetime, timedelta
from collections import defaultdict

from app.modules.oracles import CoinGecko
from app.modules.web3_node import web3Node

try:
    subgraph_id = os.getenv['SUBGRAPH_ID']
except TypeError:
    subgraph_id = 'QmWdc3kkTjT8fF8KusEQr2Pzh3iWxVo7KUxArtkxcm4qXu'
    # subgraph_id = 'QmWdc3kkTjT8fF8KusEQr2Pzh3iWxVo7KUxArtkxcm4qXu' # estable

# Node definitions
subgraph_node = 'https://api.thegraph.com/subgraphs/id/' + subgraph_id
try:
    ipfs_node = os.getenv['IPFS_NODE']
except TypeError:
    ipfs_node = 'https://ipfs.kleros.io'


def period2number(period):
    period_map = {
        'execution': 4,
        'appeal': 3,
        'vote': 2,
        'commit': 1,
        'evidence': 0}
    return period_map[period]


def gwei2eth(gwei):
    return float(gwei)*10**-18


def calculateVoteStake(minStake, alpha):
    return float(alpha)*(10**-4)*float(minStake)


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
    }}
    '''
    result = requests.post(subgraph_node, json={'query': query})
    return result.json()['data']['klerosCounters'][0]


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
        '        }'
        '    }'
        '}}'
    )

    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['disputes']) == 0:
        return None
    else:
        dispute = result.json()['data']['disputes'][0]
        subcourtID = dispute['subcourtID']['id']
        dispute['periodEnds'] = getWhenPeriodEnd(dispute,
                                                 int(subcourtID))

        vote_map = {'0': 'Refuse to Arbitrate',
                    '1': 'Yes',
                    '2': 'No',
                    '3': 'Pending'}

        vote_count = {}
        unique_vote_count = {'Yes': 0,
                             'No': 0,
                             'Refuse to Arbitrate': 0,
                             'Pending': 0}
        unique_jurors = set()

        for r in dispute['rounds']:
            vote_count[r['id']] = {'Yes': 0,
                                   'No': 0,
                                   'Refuse to Arbitrate': 0,
                                   'Pending': 0}
            votes = r['votes']
            for v in votes:
                vote_str = vote_map[v['choice']] if v['voted'] else 'Pending'
                v['vote_str'] = vote_str
                vote_count[r['id']][vote_str] += 1
                if v['address']['id'].lower() not in unique_jurors:
                    unique_vote_count[vote_str] += 1
                    unique_jurors.add(v['address']['id'].lower())
            r['votes'] = sorted(r['votes'], key=lambda x: x['address']['id'])
        dispute['vote_count'] = vote_count
        dispute['unique_vote_count'] = unique_vote_count
        dispute['unique_jurors'] = unique_jurors
        return dispute


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
    return disputes


def getAllDisputes():
    initDispute = 0
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
    for dispute in disputes:
            subcourtID = dispute['subcourtID']['id']
            dispute['periodEnds'] = getWhenPeriodEnd(dispute,
                                                     int(subcourtID),
                                                     courtTimePeriods[subcourtID])
    return disputes


def getLastDisputeInfo():
    query = (
        '{'
        'disputes(orderBy:disputeID, orderDirection:desc, first:1) {'
        '   id,'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['disputes']) == 0:
        return None
    else:
        return getDispute(int(result.json()['data']['disputes'][0]['id']))


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
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        timePeriods = {}
        for court in result.json()['data']['courts']:
            print(court)
            timePeriods[court['id']] = court['timePeriods']
        return timePeriods

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
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        court = result.json()['data']['courts'][0]
        court['tokenStaked'] = gwei2eth(court['tokenStaked'])
        court['disputes'] = getAllCourtDisputes(courtID)
        for dispute in court['disputes']:
            subcourtID = dispute['subcourtID']['id']
            dispute['periodEnds'] = getWhenPeriodEnd(dispute,
                                                     int(subcourtID),
                                                     court['timePeriods'])
            dispute['id'] = int(dispute['id'])

        return court


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
        return result.json()['data']['courts']


def getBlockNumberbefore(days=30):
    """
    Get the block number of n days ago. By default, 30 days.
    Now, it's simple considering an average time of 17 seconds.
    This should be improved
    """
    # TODO!, improve this function!
    averageBlockTime = 15  # in seconds
    currentBlockNumber = web3Node.web3.eth.blockNumber
    return int(currentBlockNumber - days*24*60*60/averageBlockTime)


def getAllCourtsDaysBefore(days=30):
    blockNumber = getBlockNumberbefore(days)
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


def getCourtDaysBefore(courtID, days=30):
    blockNumber = getBlockNumberbefore(days)
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
        return result.json()['data']['courts'][0]


def getCourtPolicy(courtID):
    policy = readPolicy(courtID)
    if policy is None:
        return None
    if 'https://' in policy['policy']:
        return None
    else:
        response = requests.get(ipfs_node+policy['policy'])
    return response.json()


def getCourtName(courtID):
    policy = getCourtPolicy(courtID)
    if policy:
        if 'name' in policy.keys():
            return policy['name']
    return str(courtID)


def readPolicy(courtID):
    query = (
        '{policyUpdates(where:{id:"'+str(courtID)+'"}) {'
        '    subcourtID,'
        '    policy,'
        '    contractAddress,'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['policyUpdates']) == 0:
        return None
    else:
        return result.json()['data']['policyUpdates'][0]


def getJurorsFromCourt(courtID):
    query = (
        '{'
        'courtStakes(where:{court:"'+str(courtID)+'"}) {'
        '    stake,'
        '    juror {id}'
        '}}'
    )

    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courtStakes']) == 0:
        return None
    else:
        rawJurors = result.json()['data']['courtStakes']
        jurors = []
        for juror in rawJurors:
            if int(juror['stake']) > 0:
                jurors.append({'address': juror['juror']['id'],
                               'stake': int(juror['stake'])*10**-18})
        return jurors


def getStakedByJuror(address):
    query = (
        '{'
        'courtStakes(where:{juror:"'+str(address)+'"}) {'
        '    stake,'
        '    court{id}'
        '    juror {id}'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['courtStakes']) == 0:
        return None
    else:
        rawStakes = result.json()['data']['courtStakes']
        stakes = []
        for stake in rawStakes:
            if float(stake['stake']) > 0:
                stakes.append({'court': stake['court']['id'],
                               'stake': gwei2eth(stake['stake'])})
        return stakes


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
        periodlength = int(timesPeriods[period2number(dispute['period'])])
        return lastPeriodChange + timedelta(seconds=periodlength)


def getCourtDisputesNumberBefore(days=30):
    blockNumber = getBlockNumberbefore(days)
    print(blockNumber)
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
        return result.json()['data']['courts']


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
        return result.json()['data']['courts']


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
        return gwei2eth(result.json()['data']['courts'][0]['tokenStaked'])


def getCourtTable():
    courtsInfo = {}
    oldcourtsInfo = {}
    courts = getAllCourts()
    pnkUSDprice = CoinGecko().getPNKprice()

    oldCourts = getCourtDisputesNumberBefore(30)
    if oldCourts is not None:
        for court in oldCourts:
            oldcourtsInfo[int(court['subcourtID'])] = int(court['disputesNum'])
    for court in courts:
        courtID = int(court['subcourtID'])
        courtsInfo[courtID] = court2table(court, pnkUSDprice)
        if oldCourts is not None:
            diff = courtsInfo[courtID]['Total Disputes']-oldcourtsInfo[courtID]
        else:
            diff = courtsInfo[courtID]['Total Disputes']
        courtsInfo[courtID]['Disputes in the last 30 days'] = diff
    # Until the total counters in the graph where fixed i will calculate them
    # for court in courtsInfo.keys():
    #    courtsInfo[court]['Total Staked'] =
    #       totalStakedInCourtAndChildrens(court)
    return courtsInfo


def court2table(court, pnkUSDPrice):
    minStake = gwei2eth(float(court['minStake']))
    feeForJuror = gwei2eth(court['feeForJuror'])
    return {'Jurors': int(court['activeJurors']),
            'Total Staked': gwei2eth(float(court['tokenStaked'])),
            'Min Stake': minStake,
            'Fee For Juror': feeForJuror,
            'Vote Stake': calculateVoteStake(minStake, court['alpha']),
            'Open Disputes': int(court['disputesOngoing']),
            'Min Stake in USD': minStake*pnkUSDPrice,
            'Total Disputes': int(court['disputesNum']),
            'id': int(court['subcourtID']),
            'Name': getCourtName(court['subcourtID'])
            }


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
        vote.update({'vote_str': getVoteStr(int(vote['choice']),
                                            vote['voted'],
                                            vote['dispute']['id'])})
    return votes


def getProfile(address):
    query = (
        '{jurors(where:{id:"'+str(address).lower()+'"}) {'
        '   currentStakes{court{id},stake,timestamp},'
        '   totalStaked,'
        '   activeJuror,'
        '   numberOfDisputesAsJuror,'
        '   numberOfDisputesCreated,'
        '   disputesAsCreator{id,currentRulling,startTime,ruled,txid}'
        '}}'
    )
    result = requests.post(subgraph_node, json={'query': query})
    if len(result.json()['data']['jurors']) == 0:
        return None
    else:
        rawProfileData = result.json()['data']['jurors'][0]
        profile = {}
        profile['numberOfDisputesAsJuror'] = rawProfileData[
            'numberOfDisputesAsJuror'
            ]
        profile['currentStakes'] = []
        for stake in rawProfileData['currentStakes']:
            profile['currentStakes'].append({'court': stake['court']['id'],
                                             'stake': gwei2eth(stake['stake']),
                                             'timestamp': int(
                                                 stake['timestamp']
                                                 ),
                                             'date': datetime.fromtimestamp(
                                                 int(stake['timestamp'])
                                                )}
                                            )
        profile['totalStaked'] = gwei2eth(rawProfileData['totalStaked'])
        profile['votes'] = []
        profile['coherent_votes'] = 0
        profile['ruled_cases'] = 0
        votes = getAllVotesFromJuror(address)
        for vote in votes:
            profile['votes'].append({
                'dispute': vote['dispute']['id'],
                'ruled': vote['dispute']['ruled'],
                'currentRulling': vote['dispute']['currentRulling'],
                'choice': vote['choice'],
                'roundID': vote['round']['id'],
                'roundNumber': vote['round']['id'].split('-')[1],
                'vote_str': vote['vote_str']}
                )
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
        profile['disputesAsCreator'] = []
        for dispute in rawProfileData['disputesAsCreator']:
            profile['disputesAsCreator'].append({
                'dispute': dispute['id'],
                'currentRulling': dispute['currentRulling'],
                'timestamp': dispute['startTime'],
                'txid': dispute['txid'],
            })
        return profile


def getVoteStr(choice, voted, dispute=None):
    """
    Return the text of the vote choice.
    TODO!, use the metadata of the dispute,
    currently it's just fixed to Refuse, Yes, No
    """
    if voted:
        vote_map = {0: 'Refuse to Arbitrate',
                    1: 'Yes',
                    2: 'No'}
        return vote_map[choice]
    else:
        return 'Pending'


def totalStakedInCourts():
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
                total += gwei2eth(courtStake['stake'])
                total_by_court[courtStake['court']['id']] += gwei2eth(
                    courtStake['stake'])
            if len(courtStakes)<1000:
                # no need to keep in the loop, all the items where queried
                break
            else:
                skip += len(courtStakes)
    return total, total_by_court


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


def totalStakedInCourtAndChildrens(courtID):
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
        print(query)
        result = requests.post(subgraph_node, json={'query': query})
        courtStakes = result.json()['data']['courtStakes']
        if len(courtStakes) == 0:
            break
        else:
            for courtStake in courtStakes:
                total += gwei2eth(courtStake['stake'])
            skip += len(courtStakes)
    return total


def getAdoption():
    "return the number of new jurors in the last 30 days"
    query = (
        '{klerosCounters{'
        '   activeJurors,'
        '   inactiveJurors'
        '}}'
    )
    current_result = requests.post(subgraph_node, json={'query': query})
    bn = getBlockNumberbefore(30)
    query = (
        '{klerosCounters(block:{number:'+str(bn)+'}){'
        '   activeJurors,'
        '   inactiveJurors'
        '}}'
    )
    before_result = requests.post(subgraph_node, json={'query': query})
    if len(current_result.json()['data']['klerosCounters']) == 0:
        return 0
    else:
        result = current_result.json()['data']['klerosCounters'][0]
        if 'data' in before_result.json().keys():
            old_result = before_result.json()['data']['klerosCounters'][0]
        else:
            return None
        newTotal = int(result['activeJurors']) + int(result['inactiveJurors'])
        oldTotal = int(old_result['activeJurors']) + int(old_result[
            'inactiveJurors'])
        return newTotal-oldTotal


def getMostActiveCourt(days=7):
    "return the most active court in the last days, by default, a week"
    old_courts_data = getCourtDisputesNumberBefore(7)
    courts_data = getCourtDisputesNumber()
    if (courts_data is None) or (old_courts_data is None):
        return None

    max_dispute_number = 0
    court_most_bussy = None
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
            court_most_bussy = int(courtID)
    return court_most_bussy
