from app.modules.subgraph import *

#print(totalStakedInCourts())
#print(getKlerosCounters())
print(totalStakedInCourts())
print(gwei2eth(getKlerosCounters()['tokenStaked']))
print(getCourtTable()[0]['Total Staked'])

