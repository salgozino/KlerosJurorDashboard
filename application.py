
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request
from plotters import disputesGraph, stakesJurorsGraph, disputesbyCourtGraph
from bin.KlerosDB import Visitor, Court, Config, Juror, Dispute
from bin.Kleros import StakesKleros
from bin import db
from datetime import datetime
import logging

# Elastic Beanstalk initalization
application = Flask(__name__)
application.config.from_object('config')
application.debug=True
db.init_app(application)
logger = logging.getLogger()

@application.route('/')
def index():
    Visitor().addVisit('dashboard')
    startTime = datetime.now()
    pnkStaked = Court(id=0).juror_stats()['total']
    tokenSupply =  float(Config().get('token_supply'))
    activeJurors = len(Juror.stakedJurors());
    drawnJurors = len(Juror.list())
    retention =  Juror.retention() / drawnJurors
    adoption = len(Juror.adoption())
    ruledCases = Dispute().ruledCases
    openCases = Dispute().openCases
    mostActiveCourt = Court.query.filter(Court.id==list(Dispute.mostActiveCourt().keys())[0]).first().name,
    pnkPrice = float(Config.get('PNKprice'))
    courtTable = StakesKleros.getCourtInfoTable()
    for c in courtTable.keys():
        courtTable[c]['Min Stake in USD'] = courtTable[c]['Min Stake']*pnkPrice
    logger.info(f"Load all the data from the DB takes: {(datetime.now()-startTime).seconds} seconds.")
    return render_template('main.html',
                           last_update= Config.get('updated'),
                           disputes= Dispute.query.order_by(Dispute.id.desc()).first().id,
                           activeJurors= activeJurors,
                           jurorsdrawn = drawnJurors,
                           retention= retention,
                           adoption= adoption,
                           most_active_court = mostActiveCourt[0],
                           cases_closed = ruledCases,
                           cases_rulling = openCases,
                           tokenSupply= tokenSupply,
                           pnkStaked= pnkStaked,
                           pnkStakedPercent= pnkStaked/tokenSupply,
                           ethPrice= float(Config.get('ETHprice')),
                           pnkPrice= pnkPrice,
                           pnkPctChange = float(Config.get('PNKpctchange24h'))/100,
                           pnkVol24= float(Config.get('PNKvolume24h')),
                           pnkCircSupply= float(Config.get('PNKcirculating_supply')),
                           courtTable = courtTable
                           )


@application.route('/support/')
def support():
    Visitor().addVisit('support')
    return render_template('support.html',
                           last_update= Config.get('updated'))

@application.route('/odds/', methods=['GET','POST'])
def odds():
    Visitor().addVisit('odds')
    pnkStaked = 100000
    if request.method == 'POST':
        # Form being submitted; grab data from form.
        try:
            pnkStaked = int(request.form['pnkStaked'])
        except:
            pnkStaked = 100000

    return render_template('odds.html',
                           last_update= Config.get('updated'),
                           pnkStaked= pnkStaked,
                           courtChances= StakesKleros.getAllCourtChances(pnkStaked))

@application.route('/kleros-map/')
def maps():
    Visitor().addVisit('map')
    return render_template('kleros-map.html',
                            last_update= Config.get('updated')
                            )

@application.route('/visitorMetrics/')
def visitorMetrics():
    visitors = Visitor()
    return render_template('visitors.html',
                           home=visitors.dashboard,
                           odds=visitors.odds,
                           map=visitors.map,
                           support=visitors.support,
                           last_update= Config.get('updated'),
                           )

@application.errorhandler(404)
def not_found(e):
    Visitor().addVisit('unknown')
    return render_template("404.html")


if __name__ == "__main__":
    application.run(debug=True)