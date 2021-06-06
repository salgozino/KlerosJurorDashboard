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
from app.modules.plotters import disputesGraph, stakesJurorsGraph, \
    disputesbyCourtGraph, disputesbyArbitratedGraph, treeMapGraph, jurorHistogram
from app.modules.kleros_db import Visitor, Court, Config, Juror, Dispute
from app.modules.kleros import get_court_info_table, get_all_court_chances
from app.modules.subgraph import getCourtName, getKlerosCounters, getLastDisputeInfo, getDispute, getCourt, getJurorsFromCourt, calculateVoteStake, getCourtTable

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
    Visitor().addVisit('dashboard')

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
    Visitor().addVisit('graphs')
    courtTable = get_court_info_table()
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


@application.route('/support/')
def support():
    Visitor().addVisit('support')
    return render_template('support.html',
                           last_update=Config.get('updated'))


@application.route('/odds/', methods=['GET', 'POST'])
def odds():
    Visitor().addVisit('odds')
    pnkStaked = 100000
    if request.method == 'POST':
        # Form being submitted; grab data from form.
        try:
            pnkStaked = int(request.form['pnkStaked'])
        except Exception:
            pnkStaked = 100000

    return render_template('odds.html',
                           last_update=Config.get('updated'),
                           pnkStaked=pnkStaked,
                           courtChances=get_all_court_chances(pnkStaked))


@application.route('/kleros-map/')
def maps():
    Visitor().addVisit('map')
    return render_template('kleros-map.html',
                           last_update=Config.get('updated')
                           )


@application.route('/visitorMetrics/')
def visitorMetrics():
    visitors = Visitor()
    return render_template('visitors.html',
                           home=visitors.dashboard,
                           odds=visitors.odds,
                           map=visitors.map,
                           support=visitors.support,
                           last_update=Config.get('updated'),
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
                               last_update=Config.get('updated'),
                               )
    print(dispute)
    return render_template('dispute.html',
                           dispute=dispute,
                           error=None,
                           vote_count=dispute['vote_count'],
                           unique_vote_count=dispute['unique_vote_count'],
                           last_update=Config.get('updated'),
                           )


@application.route('/court/', methods=['GET'])
def court():
    id = request.args.get('id', type=int)
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


@application.route('/juror/<string:address>', methods=['GET'])
def juror(address):
    juror = Juror(address)
    page_disputes = request.args.get('page_disputes', type=int)
    page_votes = request.args.get('page_votes', type=int)
    disputes = Dispute.disputesByCreator_paginated(address, page_disputes)
    votes = juror.all_votes_paginated(page_votes)
    juror_stakes = juror.current_stakings_per_court
    stakes = []
    for court, stake in juror_stakes.items():
        stakes.append((Court(id=court).map_name, stake))
    return render_template('juror.html',
                           address=address,
                           disputes=disputes,
                           stakes=stakes,
                           votes=votes,
                           last_update=Config.get('updated'),
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
