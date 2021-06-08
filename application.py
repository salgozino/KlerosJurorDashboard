# -*- coding: utf-8 -*-
"""application
Flask Application which runs the web server!.
Here all the website is created.
"""
import os
import logging
from datetime import datetime

from flask import render_template, request
from requests.api import get

from app import create_app
from app.modules.etherscan import CoinGecko
from app.modules.plotters import jurorHistogram
# from app.modules.plotters import disputesGraph, stakesJurorsGraph, \
#     disputesbyCourtGraph, disputesbyArbitratedGraph, treeMapGraph, jurorHistogram
from app.modules.kleros import get_all_court_chances
from app.modules.subgraph import getCourtName, getKlerosCounters, getLastDisputeInfo, getDispute, getCourt, getJurorsFromCourt, calculateVoteStake, getCourtTable, getProfile

# Elastic Beanstalk initalization
settings_module = os.environ.get('CONFIG_MODULE')
application = create_app(settings_module)

logger = logging.getLogger(__name__)


@application.template_filter()
def timedelta(date):
    if not isinstance(date, datetime):
        date = datetime.fromtimestamp(date)
    delta = date-datetime.now()
    return delta


@application.template_filter()
def courtName(courtID):
    return getCourtName(courtID)


@application.route('/')
def index():
    # Visitor().addVisit('dashboard')

    klerosCounters = getKlerosCounters()
    drawnJurors = 0 # len(Juror.list())
    retention = 0  # Juror.retention() / drawnJurors
    adoption = 0  # len(Juror.adoption())
    ruledCases = int(klerosCounters['closedDisputes'])
    openCases = int(klerosCounters['openDisputes'])
    mostActiveCourt = None
    if mostActiveCourt:
        mostActiveCourt = getCourtName(int(mostActiveCourt))
    else:
        mostActiveCourt = "No new cases in the last 7 days"
    # PNK & ETH Information
    coingecko = CoinGecko()
    pnkInfo = coingecko.getCryptoInfo()
    ethPrice = coingecko.getETHprice()
    pnkPrice = pnkInfo['market_data']['current_price']['usd']
    tokenSupply = pnkInfo['market_data']['total_supply']
    pnkPctChange = pnkInfo['market_data']['price_change_24h']
    pnkCircSupply = pnkInfo['market_data']['circulating_supply']
    pnkVol24 = pnkInfo['market_data']['total_volume']['usd']
    courtTable = getCourtTable()
    pnkStaked = float(klerosCounters['tokenStaked'])
    activeJurors = klerosCounters['activeJurors']
    return render_template('main.html',
                           last_update=datetime.now(),
                           disputes=klerosCounters['disputesCount'],
                           activeJurors=activeJurors,
                           jurorsdrawn=drawnJurors,
                           retention=retention,
                           adoption=adoption,
                           most_active_court=mostActiveCourt,
                           cases_closed=ruledCases,
                           cases_rulling=openCases,
                           tokenSupply=tokenSupply,
                           pnkStaked=pnkStaked,
                           pnkStakedPercent=pnkStaked/tokenSupply,
                           pnkStakedPercentSupply=pnkStaked/pnkCircSupply,
                           ethPrice=ethPrice,
                           pnkPrice=pnkPrice,
                           pnkPctChange=pnkPctChange,
                           pnkVol24=pnkVol24,
                           pnkCircSupply=pnkCircSupply,
                           fees_paid={'eth': 0,
                                      'pnk': 0},
                           courtTable=courtTable
                           )


@application.route('/graphs/')
def graphsMaker():
    return "Under construction"
"""
    # Visitor().addVisit('graphs')
    courtTable = getCourtTable()
    sjGraph = stakesJurorsGraph()
    return render_template('graphs.html',
                           last_update=Config.get('updated'),
                           stakedPNKgraph=sjGraph,
                           disputesgraph=disputesGraph(),
                           disputeCourtgraph=disputesbyCourtGraph(),
                           disputeCreatorgraph=disputesbyArbitratedGraph(),
                           treemapJurorsGraph=treeMapGraph(courtTable),
                           treemapStakedGraph=treeMapGraph(courtTable, 'Total Staked')
                           )
"""

@application.route('/support/')
def support():
    # Visitor().addVisit('support')
    return render_template('support.html',
                           last_update=datetime.now())


@application.route('/odds/', methods=['GET', 'POST'])
def odds():
    # Visitor().addVisit('odds')
    pnkStaked = 100000
    if request.method == 'POST':
        # Form being submitted; grab data from form.
        try:
            pnkStaked = int(request.form['pnkStaked'])
        except Exception:
            pnkStaked = 100000

    return render_template('odds.html',
                           last_update=datetime.now(),
                           pnkStaked=pnkStaked,
                           courtChances=get_all_court_chances(pnkStaked))


@application.route('/kleros-map/')
def maps():
    # Visitor().addVisit('map')
    return render_template('kleros-map.html',
                           last_update=datetime.now()
                           )


@application.route('/visitorMetrics/')
def visitorMetrics():
    # visitor = Visitor()
    return render_template('visitors.html',
                           home=0,
                           odds=0,
                           map=0,
                           support=0,
                           last_update=datetime.now(),
                           )


@application.route('/dispute/', methods=['GET'])
def dispute():
    id = request.args.get('id', type=int)
    if id is None:
        dispute = getLastDisputeInfo()
    else:
        dispute = getDispute(id)
        if dispute is None:
            return render_template('dispute.html',
                               error="Error trying to reach the dispute data. This Dispute exist?",
                               dispute=dispute,
                               vote_count=None,
                               unique_vote_count=None,
                               last_update=datetime.now(),
                               )
        return render_template('dispute.html',
                           dispute=dispute,
                           error=None,
                           vote_count=dispute['vote_count'],
                           unique_vote_count=dispute['unique_vote_count'],
                           last_update=datetime.now(),
                           )


@application.route('/court/', methods=['GET'])
def court():
    id = request.args.get('id', type=int)
    if id is None:
        id = 0
    court = getCourt(id)
    if court['parent']:
        parent = getCourt(int(court['parent']['id']))
    else:
        parent = None
    
    disputes = court['disputes']

    court_childs = []
    for child in court['childs']:
        court_childs.append(getCourt(int(child['id'])))

    
    jurors = getJurorsFromCourt(id)
    sorted_jurors = sorted(jurors,
                           key=lambda item: item['stake'],
                           reverse=True)
    juror_hist = jurorHistogram([juror['stake'] for juror in jurors])

    return render_template('court.html',
                           court=court,
                           parent=parent,
                           childs=court_childs,
                           disputes=disputes,
                           n_jurors=len(jurors),
                           jurors=sorted_jurors,
                           juror_hist=juror_hist,
                           open_cases=int(court['disputesOngoing']),
                           ruled_cases=int(court['disputesClosed']),
                           fees={'eth':0, 'pnk':0},
                           min_stake=float(court['minStake'])*(10**-18),
                           vote_stake=calculateVoteStake(float(court['minStake'])*10**-18,court['alpha']),
                           last_update=datetime.now(),
                           current_juror_page=0
                           )


@application.route('/profile/<string:address>', methods=['GET'])
def profile(address):
    profile = getProfile(address)
    if profile is None:
        return render_template('profile.html',
                           address=address,
                           disputes=[],
                           stakes=[],
                           votes=[],
                           totalStaked=0,
                           coherency=0,
                           last_update=datetime.now(),
                           )
    else:
        return render_template('profile.html',
                            address=address,
                            disputes=profile['disputesAsCreator'],
                            stakes=profile['currentStakes'],
                            votes=profile['votes'],
                            totalStaked=profile['totalStaked'],
                            coherency=profile['coherency'],
                            last_update=datetime.now(),
                            )


@application.route('/getCourtJurors/<int:courtID>', methods=['GET'])
def courtJurors(courtID):
    court = Court(id=courtID)
    return court.jurors

@application.errorhandler(404)
def not_found(e):
    Visitor().addVisit('unknown')
    return render_template("404.html",
                           last_update=Config.get('updated'))


if __name__ == "__main__":
    application.run(debug=True)
