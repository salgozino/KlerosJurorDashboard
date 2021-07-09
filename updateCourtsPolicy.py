import json
import os
import logging
import sys

from app.modules.subgraph import Subgraph

logger = logging.getLogger(__name__)

"""
Create or update json file with the court policies updated.
This script should be run to update that json file located
in the lib folder
"""


if __name__ == '__main__':
    if not os.path.isdir('app/lib'):
        os.mkdir('app/lib')

    networks = ['mainnet',  'xdai']
    for network in networks:
        subgraph = Subgraph(network)
        kc = subgraph.getKlerosCounters()
        try:
            courtsCount = kc['courtsCount']
        except KeyError:
            logger.error('Error trying to read courtsCount from KlerosCounters')
            sys.exit()

        policies = {}
        for courtID in range(courtsCount):
            policy = subgraph.getCourtPolicy(courtID)
            policies.update({courtID: policy})

        with open(f'app/lib/court_policies_{network}.json', 'w') as f:
            json.dump(policies, f)
