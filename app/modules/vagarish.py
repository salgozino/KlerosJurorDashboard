import requests
import logging

_endpoint = 'https://vagarish.forer.es/api/search'
logger = logging.getLogger(__name__)


def get_evidences(disputeID):
    try:
        _ = int(disputeID)
    except TypeError:
        logger.error("wrong dispute input")
        return []
    query_endpoint = _endpoint + '?id={}'.format(disputeID)
    try:
        response = requests.get(query_endpoint)
    except Exception:
        return []
    return _parse_evidences(response.json())


def _parse_evidences(response):
    """
    From a response from get_evidence, parse the evidences
    """
    try:
        result = response[0]
        return result['matchedEvidence']
    except Exception:
        return []


if __name__ == '__main__':
    evidences = get_evidences(784)
    print(len(evidences))
    print(evidences)
