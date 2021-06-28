# -*- coding: utf-8 -*-
"""application
Flask Application which runs the web server!.
Here all the website is created.
"""
import os
import logging
from datetime import datetime

from flask import render_template, request

from app import create_app
from app.modules.oracles import CoinGecko
from app.modules.plotters import jurorHistogram
# from app.modules.plotters import disputesGraph, stakesJurorsGraph, \
#     disputesbyCourtGraph, disputesbyArbitratedGraph, treeMapGraph, \
#     jurorHistogram
from app.modules.kleros import get_all_court_chances
from app.modules.subgraph import getCourtWithDisputes, getMostActiveCourt, \
    getAdoption, getCourtName, getKlerosCounters, \
    getDispute, getCourt, getActiveJurorsFromCourt, \
    getCourtTable, getProfile, _wei2eth, getAllDisputes

# Elastic Beanstalk initalization
settings_module = os.environ.get('CONFIG_MODULE')
application = create_app(settings_module)

logger = logging.getLogger(__name__)


@application.template_filter()
def timedelta(date):
    if not isinstance(date, datetime):
        date = datetime.fromtimestamp(date)
    delta = date-datetime.now()
    return str(delta).split(".")[0]


@application.template_filter()
def courtName(courtID):
    return getCourtName(courtID)


@application.template_filter()
def timestamp2datetime(value):
    if value is None:
        return ""
    format = "%Y-%m-%d %H:%M"
    value = datetime.utcfromtimestamp(int(value))
    return value.strftime(format)


@application.template_filter()
def filter_wei_2_eth(gwei):
    return _wei2eth(gwei)


@application.route('/')
def index():
    klerosCounters = getKlerosCounters()
    drawnJurors = int(klerosCounters['drawnJurors'])
    retention = 0  # Juror.retention() / drawnJurors
    adoption = getAdoption()
    ruledCases = int(klerosCounters['closedDisputes'])
    openCases = int(klerosCounters['openDisputes'])
    mostActiveCourt = getMostActiveCourt()
    if mostActiveCourt is not None:
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
    pnkStaked = _wei2eth(klerosCounters['tokenStaked'])
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
    return render_template('graphs.html',
                           stakedPNKgraph=[],
                           disputesgraph=[],
                           disputeCourtgraph=[],
                           disputeCreatorgraph=[],
                           treemapJurorsGraph=[],
                           treemapStakedGraph=[],
                           )


@application.route('/support/')
def support():
    # Visitor().addVisit('support')
    return render_template('support.html',
                           last_update=datetime.now())


@application.route('/odds/', methods=['GET', 'POST'])
def odds():
    # Visitor().addVisit('odds')
    pnkStaked = 100000
    n_votes = 3
    if request.method == 'POST':
        # Form being submitted; grab data from form.
        try:
            pnkStaked = int(request.form['pnkStaked'])
        except Exception:
            pnkStaked = 100000
        try:
            n_votes = abs(int(request.form['n_votes']))
        except Exception:
            n_votes = 3

    return render_template('odds.html',
                           last_update=datetime.now(),
                           pnkStaked=pnkStaked,
                           n_votes=n_votes,
                           courtChances=get_all_court_chances(pnkStaked, n_votes))


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
        disputes = getAllDisputes()
        return render_template('allDisputes.html',
                               error=None,
                               disputes=disputes,
                               last_update=datetime.now(),
                               )

    else:
        dispute = getDispute(id)
        if dispute is None:
            error_msg = ("Error trying to reach the dispute data."
                         "This Dispute exist?"
                         )
            return render_template('dispute.html',
                                   error=error_msg,
                                   dispute=dispute,
                                   vote_count=None,
                                   unique_vote_count=None,
                                   last_update=datetime.now(),
                                   )
    print(dispute)
    return render_template('dispute.html',
                           dispute=dispute,
                           error=None
                           )


@application.route('/court/', methods=['GET'])
def court():
    id = request.args.get('id', type=int)
    if id is None:
        id = 0
    court = getCourtWithDisputes(id)
    if court is None:
        return "Error!, court not found"
    disputes = court['disputes']

    jurors = getActiveJurorsFromCourt(id)
    sorted_jurors = sorted(jurors,
                            key=lambda item: item['stake'],
                            reverse=True)
    juror_hist = jurorHistogram([juror['stake'] for juror in sorted_jurors])
    staked_in_this_court = sum(juror['stake'] for juror in sorted_jurors)
    return render_template('court.html',
                           court=court,
                           disputes=disputes,
                           n_jurors=len(sorted_jurors),
                           staked_in_this_court=staked_in_this_court,
                           jurors=sorted_jurors,
                           juror_hist=juror_hist,
                           open_cases=court['disputesOngoing'],
                           ruled_cases=court['disputesClosed'],
                           fees={'eth': 0, 'pnk': 0},
                           min_stake=court['minStake'],
                           vote_stake=court['voteStake'],
                           last_update=datetime.now(),
                           current_juror_page=0
                           )


@application.route('/profile/<string:address>', methods=['GET'])
def profile(address):
    profile = getProfile(address)
    if profile is None:
        profile = {'address':address}
        return render_template('profile.html',
                               profile=profile
                               )
    else:
        return render_template('profile.html',
                               profile=profile
                               )


@application.route('/getCourtJurors/<int:courtID>', methods=['GET'])
def courtJurors(courtID):
    court = getCourt(id=courtID)
    return court


@application.errorhandler(404)
def not_found(e):
    # Visitor().addVisit('unknown')
    return render_template("404.html",
                           last_update=datetime.now())


if __name__ == "__main__":
    application.run(debug=True)
