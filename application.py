# -*- coding: utf-8 -*-

import os
from app import create_app

from app.modules.plotters import disputesGraph, stakesJurorsGraph, \
    disputesbyCourtGraph, disputesbyArbitratedGraph, treeMapGraph, jurorHistogram
from app.modules.KlerosDB import Visitor, Court, Config, Juror, Dispute
from app.modules.Kleros import StakesKleros
from flask import render_template, request
import logging

# Elastic Beanstalk initalization
settings_module = os.environ.get('CONFIG_MODULE')
application = create_app(settings_module)

logger = logging.getLogger(__name__)


@application.route('/')
def index():
    Visitor().addVisit('dashboard')
    tokenSupply = float(Config().get('token_supply'))
    drawnJurors = len(Juror.list())
    retention = Juror.retention() / drawnJurors
    adoption = len(Juror.adoption())
    ruledCases = Dispute().ruledCases
    openCases = Dispute().openCases
    mostActiveCourt = Dispute.mostActiveCourt()
    if mostActiveCourt:
        mostActiveCourt = Court(id=int(list(mostActiveCourt.keys())[0])).map_name
    else:
        mostActiveCourt = "No new cases in the last 7 days"
    pnkPrice = float(Config.get('PNKprice'))
    courtTable = StakesKleros.getCourtInfoTable()
    pnkStaked = courtTable['General Court']['Total Staked']
    activeJurors = courtTable['General Court']['Jurors']

    return render_template('main.html',
                           last_update=Config.get('updated'),
                           disputes=Dispute.query.order_by(Dispute.id.desc()).first().id,
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
                           ethPrice=float(Config.get('ETHprice')),
                           pnkPrice=pnkPrice,
                           pnkPctChange=float(Config.get('PNKpctchange24h'))/100,
                           pnkVol24=float(Config.get('PNKvolume24h')),
                           pnkCircSupply=float(Config.get('PNKcirculating_supply')),
                           fees_paid={'eth': float(Config.get('fees_ETH')),
                                      'pnk': float(Config.get('PNK_redistributed'))},
                           courtTable=courtTable
                           )


@application.route('/graphs/')
def graphsMaker():
    Visitor().addVisit('graphs')
    courtTable = StakesKleros.getCourtInfoTable()
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
                           courtChances=StakesKleros.getAllCourtChances(pnkStaked))


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
        id = Dispute.query.order_by(Dispute.id.desc()).first().id

    vote_count = {}
    dispute = Dispute.query.get(id)
    try:
        rounds = dispute.rounds()
    except Exception:
        return render_template('dispute.html',
                               error="Error trying to reach the dispute data. This Dispute exist?",
                               dispute=dispute,
                               vote_count=None,
                               unique_vote_count=None,
                               last_update=Config.get('updated'),
                               )
    unique_vote_count = {'Yes': 0, 'No': 0, 'Refuse': 0, 'Pending': 0}
    unique_jurors = set()
    for r in rounds:
        vote_count[r.id] = {'Yes': 0, 'No': 0, 'Refuse': 0, 'Pending': 0}
        votes = r.votes()
        for v in votes:
            vote_str = v.vote_str
            vote_count[r.id][vote_str] += 1
            if v.account.lower() not in unique_jurors:
                unique_vote_count[vote_str] += 1
                unique_jurors.add(v.account.lower())

    return render_template('dispute.html',
                           dispute=dispute,
                           rounds=rounds,
                           error=None,
                           vote_count=vote_count,
                           unique_vote_count=unique_vote_count,
                           last_update=Config.get('updated'),
                           )


@application.route('/court/', methods=['GET'])
def court():
    id = request.args.get('id', type=int)
    if id is None:
        # if it's not specified, go to the general court
        id = 0
    court = Court.query.get(id)
    parent = court.parent
    if parent is not None:
        parent = Court(id=parent)
    disputes = court.disputes()
    winner_choice = {
            'Refuse to Arbitrate': 0,
            'Yes': 0,
            'No': 0,
            'Tie': 0,
            'Not Ruled yet': 0}
    # for dispute in disputes:
        # winner_choice[dispute.winner_choice_str] += 1
    childs = court.children_ids()
    court_childs = []
    for child in childs:
        court_childs.append(Court(id=child))
    jurors = court.jurors
    jurors = {k: v for k, v in sorted(jurors.items(),
                                      key=lambda item: item[1],
                                      reverse=True)}
    juror_hist = jurorHistogram(list(jurors.values()))

    return render_template('court.html',
                           court=court,
                           parent=parent,
                           childs=court_childs,
                           disputes=disputes,
                           winner_choice=winner_choice,
                           jurors=jurors,
                           juror_hist=juror_hist,
                           last_update=Config.get('updated'),
                           )


@application.route('/juror/<string:address>')
def juror(address):
    juror = Juror(address)
    disputes = Dispute.disputesByCreator(address)
    votes = juror.all_votes()
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


@application.errorhandler(404)
def not_found(e):
    Visitor().addVisit('unknown')
    return render_template("404.html",
                           last_update=Config.get('updated'))


if __name__ == "__main__":
    application.run(debug=True)
