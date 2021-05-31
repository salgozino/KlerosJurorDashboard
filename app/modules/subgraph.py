import requests
import os
try:
    subgraph_id = os.getenv['SUBGRAPH_ID']
except:
    subgraph_id = 'QmYheX3RKZ9T5zLXrwNP4w5Ucj3aVcHeLHqoBWaeFuYkQX'

subgraph_node = 'https://api.thegraph.com/subgraphs/id/' + subgraph_id


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
    }}
    '''
    result = requests.post(subgraph_node, json={'query':query})
    return result.json()['data']['klerosCounters'][0]


def getCourt(courtID):
    query = (
    '{'
    'courts(where:{id:"'+str(courtID)+'"}) {'
    '   subcourtID,'
    '   disputesNum,'
    '   disputesClosed,'
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


def getDisputeInfo(disputeID):
    query = (
    '{'
    'disputes(where:{disputeID:'+str(disputeID)+'}) {'
    '   subcourtID{id, timePeriods},'
    '   disputeID,'
    '   arbitrable,'
    '   creator,'
    '   period,'
    '   rounds {id,winningChoice,startTime,votes {address,choice,voted}},'
    '   currentRulling,'
    '   lastPeriodChange,'
    '   ruled'
    '}}'
    )
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['disputes']) == 0:
        return None
    else:
        return result.json()['data']['disputes'][0]

def getLastDisputeInfo():
    query = (
    '{'
    'disputes(orderBy:disputeID, orderDirection:desc, first:1) {'
    '   subcourtID{id, timePeriods},'
    '   disputeID,'
    '   arbitrable,'
    '   creator,'
    '   period,'
    '   rounds {id,winningChoice,startTime,votes {address,choice,voted}},'
    '   currentRulling,'
    '   lastPeriodChange,'
    '   ruled'
    '}}'
    )
    result = requests.post(subgraph_node, json={'query':query})
    if len(result.json()['data']['disputes']) == 0:
        return None
    else:
        return result.json()['data']['disputes'][0]

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