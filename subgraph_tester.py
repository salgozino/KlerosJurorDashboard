#%%
from app.modules.kleros import get_all_court_chances
from app.modules.subgraph import *
#print(getTimePeriodsAllCourts())
#print(getMostActiveCourt())

#print(getKlerosCounters())
print(getTotalStakedInCourts())
print(_wei2eth(getKlerosCounters()['tokenStaked']))
print(getCourtTable()[0]['Total Staked'])

# print(str(list(getCourtChildrens(2))).replace("'",'"'))
# print(totalStakedInCourtAndChildrens(3))

#print(getCourtName(3))
#print(getCourt(0))

#%%
"""
from app.modules.kleros import get_all_court_chances
courtChances = get_all_court_chances(100000)
print(courtChances[list(courtChances.keys())[0]].keys())
"""
#%%
"""
from app.modules.subgraph import *
total, total_by_court =  totalStakedInCourts()
print(total_by_court)
print('totalStaked In Courts',total)
print('totalStaked In Courts',sum([value for value in total_by_court.values()]))
print('KC tokenStaked', gwei2eth(getKlerosCounters()['tokenStaked']))

print('Court 0 total staked', getCourtTable()[0]['Total Staked'])
"""