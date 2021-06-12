import requests
import urllib

class CMC():
    """
    Class for interaction with CoinMarketCap and get the ETH and PNK prices.
    """

    def __init__(self):
        self.api_url = "http://pro-api.coinmarketcap.com/v1/cryptocurrency/"
        try:
            self.api_key = os.environ['CMC_KEY']
        except KeyError:
            print("NO OS CMC_KEY VARIABLE FOUND")
            self.api_key = json.load(open('app/lib/coinmarketcap.json', 'r'))['api_key']

    def getCryptoInfo(self, id=3581):
        parameters = {'id': id}
        headers = {
          'Accepts': 'application/json',
          'Accept-Enconding': 'deflate, gzip',
          'X-CMC_PRO_API_KEY': self.api_key,
        }
        url = self.api_url + 'quotes/latest?' + urllib.parse.urlencode(parameters)
        response = requests.get(url, headers=headers)
        return response.json()['data'][str(id)]

    def getPNKprice(self):
        pnkId = 3581
        response = self.getCryptoInfo(id=pnkId)
        return response['quote']['USD']['price']

    def getETHprice(self):
        ethId = 1027
        response = self.getCryptoInfo(id=ethId)
        return response['quote']['USD']['price']

    def cryptoMap(self):
        headers = {
          'Accepts': 'application/json',
          'Accept-Enconding': 'deflate, gzip',
          'X-CMC_PRO_API_KEY': self.api_key,
        }
        url = self.api_url + 'map'
        response = requests.get(url, headers=headers)
        return response.json()


class CoinGecko():
    """
    Class for interaction with CoinGecko API and get the ETH and PNK prices.
    """

    def __init__(self):
        self.api_url = "https://api.coingecko.com/api/v3/"

    def getCryptoInfo(self, id="kleros"):
        parameters = {'localization': False,
                      'tickers': False,
                      'market_data': True,
                      'community_data': False,
                      'developer_data': False,
                      'sparkline': False}
        headers = {
          'Accepts': 'application/json',
        }
        url = self.api_url + 'coins/{}?'.format(id) + urllib.parse.urlencode(parameters)
        response = requests.get(url, headers=headers)
        return response.json()

    def getPNKprice(self):
        pnkId = "kleros"
        response = self.getCryptoInfo(id=pnkId)
        return response['market_data']['current_price']['usd']
    
    def getPNKPctChange(self):
        pnkId = "kleros"
        response = self.getCryptoInfo(id=pnkId)
        return response['market_data']['price_change_24h']

    def getPNKVol24hs(self):
        pnkId = "kleros"
        response = self.getCryptoInfo(id=pnkId)
        return response['market_data']['total_volume']['usd']
    
    def getPNKcircSupply(self):
        pnkId = "kleros"
        response = self.getCryptoInfo(id=pnkId)
        return response['market_data']['total_volume']['usd']

    def getETHprice(self):
        ethId = "ethereum"
        response = self.getCryptoInfo(id=ethId)
        return response['market_data']['current_price']['usd']
