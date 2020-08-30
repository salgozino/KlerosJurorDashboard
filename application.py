# -*- coding: utf-8 -*-

import os
from app import create_app

from app.modules.plotters import disputesGraph, stakesJurorsGraph, \
    disputesbyCourtGraph, disputesbyCreatorGraph, treeMapGraph
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
    pnkStaked = courtTable['General']['Total Staked']
    activeJurors = courtTable['General']['Jurors']

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
                           courtTable=courtTable
                           )


@application.route('/graphs/')
def graphsMaker():
    Visitor().addVisit('graphs')
    courtTable = StakesKleros.getCourtInfoTable()
    sjGraph = stakesJurorsGraph()
    return render_template('graphs.html',
                           last_update=Config.get('updated')
                           stakedPNKgraph=sjGraph,
                           disputesgraph=disputesGraph(),
                           disputeCourtgraph=disputesbyCourtGraph(),
                           disputeCreatorgraph=disputesbyCreatorGraph(),
                           treemapJurorsGraph=treeMapGraph(courtTable),
                           treemapStakedGraph=treeMapGraph(courtTable, 'Total Staked'))


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


@application.route('/dispute/', methods=['POST', 'GET'])
def dispute():
    try:
        id = request.form['disputeID']
    except Exception:
        id = Dispute.query.order_by(Dispute.id.desc()).first().id
    vote_count = {}
    dispute = Dispute.query.get(id)
    dispute.rounds = dispute.rounds()
    for r in dispute.rounds:
        vote_count[r.id] = {'Yes': 0, 'No': 0, 'Refuse': 0, 'Pending': 0}
        r.votes = r.votes()
        for v in r.votes:
            if v.vote == 1:
                if v.choice == 1:
                    v.vote_str = 'Yes'
                    vote_count[r.id]['Yes'] += 1
                elif v.choice == 2:
                    v.vote_str = 'No'
                    vote_count[r.id]['No'] += 1
                elif v.choice == 0:
                    v.vote_str = 'Refuse'
                    vote_count[r.id]['Refuse'] += 1
            else:
                v.vote_str = 'Pending'
                vote_count[r.id]['Pending'] += 1
    return render_template('dispute.html',
                           dispute=dispute,
                           vote_count=vote_count,
                           last_update=Config.get('updated'),
                           )


@application.errorhandler(404)
def not_found(e):
    Visitor().addVisit('unknown')
    return render_template("404.html",
                           last_update=Config.get('updated'))


if __name__ == "__main__":
    application.run(debug=True)
