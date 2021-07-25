# -*- coding: utf-8 -*-
"""application
Flask Application which runs the web server!.
Here all the website is created.
"""
import logging
from datetime import datetime, timedelta

from flask import render_template, request, jsonify
from numpy.lib.nanfunctions import _nanpercentile_dispatcher

from app import create_app
from app.modules.plotters import disputesGraph, disputesbyCourtGraph, \
    disputesbyArbitratedGraph, treeMapGraph, jurorHistogram
from app.modules.kleros import get_all_court_chances
from app.modules.subgraph import Subgraph
from app.modules.vagarish import get_evidences


# Elastic Beanstalk initalization
# settings_module = os.environ.get('CONFIG_MODULE')
application = create_app()

logger = logging.getLogger(__name__)


@application.template_filter()
def timedelta_now(date):
    if not isinstance(date, datetime):
        date = datetime.fromtimestamp(date)
    delta = date-datetime.now()
    return str(delta).split(".")[0]


@application.template_filter()
def timeperiod_format(time_period):
    return timedelta(seconds=time_period)


@application.template_filter()
def courtName(courtID, network=None):
    return Subgraph(network).getCourtName(courtID)


@application.template_filter()
def arbitrableName(address, network=None):
    return Subgraph(network).getArbitrableName(address)


@application.template_filter()
def timestamp2datetime(value):
    if value is None:
        return ""
    format = "%Y-%m-%d %H:%M"
    value = datetime.utcfromtimestamp(int(value))
    return value.strftime(format)


@application.template_filter()
def filter_wei_2_eth(gwei):
    return Subgraph()._wei2eth(gwei)


@application.route('/', methods=['GET'])
def index():
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    dashboard = subgraph.getDashboard()
    return render_template('main.html',
                           dashboard=dashboard,
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


@application.route('/graphs/')
def graphsMaker():
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    court_table = subgraph.getCourtTree()
    disputes = subgraph.getAllDisputes()
    treeMapJurors = treeMapGraph(court_table, 'activeJurors')
    treeMapToken = treeMapGraph(court_table, 'tokenStaked')
    return render_template('graphs.html',
                           stakedPNKgraph=[],
                           disputesgraph=disputesGraph(disputes, network),
                           disputeCourtgraph=disputesbyCourtGraph(disputes,
                                                                  network),
                           disputeCreatorgraph=disputesbyArbitratedGraph(
                               disputes, network),
                           treemapJurorsGraph=treeMapJurors,
                           treemapStakedGraph=treeMapToken,
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


@application.route('/support/')
def support():
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    return render_template('support.html',
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


@application.route('/odds/', methods=['GET', 'POST'])
def odds():
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
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
                           pnkStaked=pnkStaked,
                           n_votes=n_votes,
                           courtChances=get_all_court_chances(pnkStaked,
                                                              n_votes,
                                                              network),
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network)


@application.route('/kleros-map/')
def maps():
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    return render_template('kleros-map.html',
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


@application.route('/visitorMetrics/')
def visitorMetrics():
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    return render_template('visitors.html',
                           home=0,
                           odds=0,
                           map=0,
                           support=0,
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


@application.route('/dispute/', methods=['GET'])
def dispute():
    id = request.args.get('id', type=int)
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    if id is None:
        disputes = subgraph.getAllDisputes()
        return render_template('allDisputes.html',
                               error=None,
                               disputes=disputes,
                               subgraph_status=subgraph.getStatus(),
                               network=subgraph.network
                               )

    else:
        dispute = subgraph.getDispute(id)
        if dispute is None:
            error_msg = ("Error trying to reach the dispute data."
                         "This Dispute exist?"
                         )
            return render_template('dispute.html',
                                   error=error_msg,
                                   subgraph_status=subgraph.getStatus(),
                                   network=subgraph.network
                                   )
        if subgraph.network == 'mainnet':
            dispute['evidences'] = get_evidences(id)
        else:
            # there is no evidence provider in other networks
            dispute['evidences'] = []
        return render_template('dispute.html',
                               dispute=dispute,
                               error=None,
                               subgraph_status=subgraph.getStatus(),
                               network=subgraph.network
                               )


@application.route('/court/', methods=['GET'])
def court():
    id = request.args.get('id', type=int)
    if id is None:
        id = 0
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    court = subgraph.getCourtWithDisputes(id)
    if court is None:
        return "Error!, court not found"
    disputes = court['disputes']

    jurors = subgraph.getActiveJurorsFromCourt(id)
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
                           current_juror_page=0,
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network,
                           court_list=subgraph.getCourtList()
                           )


@application.route('/profile/<string:address>', methods=['GET'])
def profile(address):
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    profile = subgraph.getProfile(address)
    if profile is None:
        profile = {'id': address}
    return render_template('profile.html',
                           profile=profile,
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


@application.route('/arbitrable/', defaults={'address': ""})
@application.route('/arbitrable/<string:address>', methods=['GET'])
def arbitrable(address):
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    if address is None or address == "":
        arbitrables = subgraph.getAllArbitrables()
        return render_template('allArbitrables.html',
                               arbitrables=arbitrables,
                               subgraph_status=subgraph.getStatus(),
                               network=subgraph.network
                               )

    else:
        arbitrable = subgraph.getArbitrable(address)
        if arbitrable is None:
            arbitrable = {'id': address,
                          'numberOfDisputes': 0,
                          'ethFees': 0.,
                          'disputes': []}
        return render_template('arbitrable.html',
                               arbitrable=arbitrable,
                               subgraph_status=subgraph.getStatus(),
                               network=subgraph.network
                               )


@application.route('/stakes', methods=['GET'])
def stakes():
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    return render_template('allStakes.html',
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


@application.route('/_getCourtTable')
def getCourtTable():
    network = request.args.get('network', None, type=str)
    return jsonify(Subgraph(network).getCourtTable())


@application.route('/_getAdoption')
def getAdoption():
    network = request.args.get('network', None, type=str)
    return jsonify(Subgraph(network).getAdoption())


@application.route('/_getAllStakes',
                   methods=['GET'])
def getAllStakes():
    network = request.args.get('network', None, type=str)
    subgraph = Subgraph(network)
    stakes = subgraph.getAllStakeSets()
    return jsonify(stakes)


@application.route('/_getRetention')
def getRetention():
    network = request.args.get('network', None, type=str)
    return jsonify(Subgraph(network).getRetention())


@application.route('/_getMostActiveCourt')
def getMostActiveCourt():
    network = request.args.get('network', None, type=str)
    return jsonify(Subgraph(network).getMostActiveCourt())


@application.route('/_getUSDThroughArbitrable/<string:address>',
                   methods=['GET'])
def getUSDArbitrable(address):
    network = request.args.get('network', None, type=str)
    subgraph = Subgraph(network)
    return jsonify(subgraph.getUSDThroughArbitrable(address))


@application.route('/_getUSDThroughCourt/<int:courtId>',
                   methods=['GET'])
def getUSDCourt(courtId):
    network = request.args.get('network', None, type=str)
    subgraph = Subgraph(network)
    return jsonify(subgraph.getUSDThroughCourt(courtId))


@application.route('/_getUSDThroughProfile/<string:address>',
                   methods=['GET'])
def getUSDProfile(address):
    network = request.args.get('network', None, type=str)
    subgraph = Subgraph(network)
    return jsonify(subgraph.getUSDThroughProfile(address))


@application.route('/_getProfileGasCost/<string:address>',
                   methods=['GET'])
def getProfileGasCost(address):
    network = request.args.get('network', None, type=str)
    subgraph = Subgraph(network)
    return jsonify(subgraph.getProfileGasCost(address))


@application.route('/_getProfileNetReward/<string:address>',
                   methods=['GET'])
def getProfileNetReward(address):
    network = request.args.get('network', None, type=str)
    subgraph = Subgraph(network)
    net_reward = subgraph.getNetRewardProfile(address)
    return jsonify(net_reward)


@application.route('/_getTotalUSD')
def getTotalUSD():
    network = request.args.get('network', None, type=str)
    subgraph = Subgraph(network)
    return jsonify(subgraph.getTotalUSD())


@application.errorhandler(404)
def not_found(e):
    network = request.args.get('network', type=str)
    subgraph = Subgraph(network)
    return render_template("404.html",
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )


"""
@application.errorhandler(Exception)
def error_exception(e):
    subgraph = Subgraph()
    return render_template("500_generic.html",
                           error=e,
                           subgraph_status=subgraph.getStatus(),
                           network=subgraph.network
                           )
"""

if __name__ == "__main__":
    application.run(debug=True)
