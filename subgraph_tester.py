from app.modules.subgraph import Subgraph

network = 'test'

subgraph = Subgraph(network)

profile = '0x3590ac9cf1ec55d1fb86993718efabf9f1b9373a'
netreward = subgraph.getNetRewardProfile(profile)
print(netreward)
