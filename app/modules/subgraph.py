import requests
import os
from datetime import datetime, timedelta
from app.modules.web3_node import web3Node

from app.modules.etherscan import CoinGecko

try:
    subgraph_id = os.getenv['SUBGRAPH_ID']
except:
    subgraph_id = 'QmS3WaiRenqHmAPfjH9MPShSEb1mQegmMivh1vLg4Bi9UP'

subgraph_node = 'https://api.thegraph.com/subgraphs/id/' + subgraph_id


def period2number(period):
    period_map = {'execution':4,
    'appeal':3,
    'vote':2,
    'commit':1,
    'evidence':0}
    return period_map[period]

def gwei2eth(gwei):
    return gwei*10**-18


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
        tokenStaked
    }}
    '''
    result = requests.post(subgraph_node, json={'query':query})
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
    
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['disputes']) == 0:
        return None
    else:
        dispute = result.json()['data']['disputes'][0]
        print(dispute)
        dispute['periodEnds'] = getWhenPeriodEnd(dispute, int(dispute['subcourtID']['id']))
        
        vote_map = {'0': 'Refuse to Arbitrate',
            '1': 'Yes',
            '2': 'No',
            '3': 'Pending'}
        
        vote_count = {}
        unique_vote_count = {'Yes': 0, 'No': 0, 'Refuse to Arbitrate': 0, 'Pending': 0}
        unique_jurors = set()
        
        for r in dispute['rounds']:
            vote_count[r['id']] = {'Yes': 0, 'No': 0, 'Refuse to Arbitrate': 0, 'Pending': 0}
            votes = r['votes']
            for v in votes:
                vote_str = vote_map[v['choice']] if v['voted'] else 'Pending'
                v['vote_str'] = vote_str
                vote_count[r['id']][vote_str] += 1
                if v['address']['id'].lower() not in unique_jurors:
                    unique_vote_count[vote_str] += 1
                    unique_jurors.add(v['address']['id'].lower())
            r['votes'] = sorted(r['votes'], key=lambda x : x['address']['id'])
        dispute['vote_count'] = vote_count
        dispute['unique_vote_count'] = unique_vote_count
        dispute['unique_jurors'] = unique_jurors
        return dispute

def getLastDisputeInfo():
    query = (
    '{'
    'disputes(orderBy:disputeID, orderDirection:desc, first:1) {'
    '   id,'
    '}}'
    )
    result = requests.post(subgraph_node, json={'query':query})
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
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        return result.json()['data']['courts'][0]['timePeriods']

def getCourt(courtID):
    query = (
    '{'
    'courts(where:{id:"'+str(courtID)+'"}) {'
    '   id,'
    '   subcourtID,'
    '   disputesOngoing,'
    '   disputesClosed,'
    '   disputesNum,'
    '   disputes{id,subcourtID{id},ruled,period,currentRulling,lastPeriodChange},'
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
    
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        court = result.json()['data']['courts'][0]
        for dispute in court['disputes']:
            dispute['periodEnds'] = getWhenPeriodEnd(dispute, int(dispute['subcourtID']['id']),court['timePeriods'])
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
    
    result = requests.post(subgraph_node, json={'query':query})
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
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        return result.json()['data']['courts']

def getCourtDaysBefore(courtID, days=30):
    blockNumber = getBlockNumberbefore(days)
    query = (
    '{courts(block:{number:'+str(blockNumber)+'},where:{id:"'+str(courtID)+'"}){'
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
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['courts']) == 0:
        return None
    else:
        return result.json()['data']['courts'][0]

def getCourtName(courtID):
    # TODO!, not implemented yet
    return str(courtID)

def readPolicy(policyID):
    # TODO!, not implemented yet
    return None

def getJurorsFromCourt(courtID):
    query = (
    '{'
    'courtStakes(where:{court:"'+str(courtID)+'"}) {'
    '    stake,'
    '    juror {id}'
    '}}'
    )
    
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['courtStakes']) == 0:
        return None
    else:
        rawJurors = result.json()['data']['courtStakes']
        jurors = []
        for juror in rawJurors:
            if int(juror['stake'])>0:
                jurors.append({'address':juror['juror']['id'],
                                'stake': int(juror['stake'])*10**-18})
        return jurors


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
        lastPeriodChange = int(dispute['lastPeriodChange'])
        periodlength = int(timesPeriods[period2number(dispute['period'])])
        return datetime.fromtimestamp(lastPeriodChange) + timedelta(seconds=periodlength)


def getCourtTable():
    courtsInfo = {}
    oldcourtsInfo = {}
    courts = getAllCourts()
    pnkUSDprice = CoinGecko().getPNKprice()
    
    oldCourts = getAllCourtsDaysBefore(30)
    for court in oldCourts:
        oldcourtsInfo[str(court['subcourtID'])] = court2table(court, pnkUSDprice)
    
    for court in courts:
        courtID = str(court['subcourtID'])
        courtsInfo[courtID] = court2table(court, pnkUSDprice)
        diff = courtsInfo[courtID]['Total Disputes']-oldcourtsInfo[courtID]['Total Disputes']
        courtsInfo[courtID]['Disputes in the last 30 days'] = diff
    return courtsInfo


def court2table(court, pnkUSDPrice):
    
    minStake = gwei2eth(float(court['minStake']))
    return {'Jurors': int(court['activeJurors']),
            'Total Staked': gwei2eth(float(court['tokenStaked'])),
            'Min Stake': minStake,
            'Vote Stake': calculateVoteStake(minStake, court['alpha']),
            'Open Disputes': int(court['disputesOngoing']),
            'Min Stake in USD': minStake*pnkUSDPrice,
            'Total Disputes': int(court['disputesNum']),
            'id': int(court['subcourtID'])
            }