
# -*- coding: utf-8 -*-
from flask import Flask, render_template, request

from plotters import disputesGraph, stakesJurorsGraph, disputesbyCourtGraph
from bin.Kleros import KlerosLiquid, StakesKleros, DisputesEvents, courtNames
import json
import os

app = Flask(__name__)
THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
def addVisit(page):
    # TODO: This is so so so so basic.
    filename = os.path.join(THIS_FOLDER,'data/visitors.json')
    with open(filename, 'r') as f:
        visitors = json.load(f)
        try:
            visitors[page] += 1
        except:
            visitors["unknown"] += 1
    with open(filename, 'w') as f:
        json.dump(visitors, f)


@app.route('/')
def index():
    addVisit('home')
    DE = DisputesEvents()
    SK = StakesKleros()
    dfStaked = SK.historicStakesInCourts()
    dfJurors = SK.historicJurorsInCourts()
    dfCourts = SK.getstakedInCourts()
    allJurors = SK.getAllJurors()
    disputesEvents = DE.historicDisputes()
    pnkStaked = sum(dfCourts.meanStake * dfCourts.n_Jurors)
    tokenSupply =  KlerosLiquid().tokenSupply
    activeJurors = len(allJurors[(allJurors.T != 0).any()])
    drawnJurors = len(DE.drawnJurors())
    retention = DE.jurorsRetention() / drawnJurors
    adoption = SK.jurorAdoption()
    ruledCases = DE.ruledCases()
    mostActiveCourt = DE.mostActiveCourt()
    newNames = {'totalstaked':'Total Staked',
                'maxStake': 'Max. Stake',
                'meanStake': 'Mean Stake',
                'courtLabel': 'Court',
                'n_Jurors': 'Jurors'}
    return render_template('main.html',
                           last_update= KlerosLiquid().getLastUpdate(),
                           disputes= disputesEvents.iloc[-1],
                           activeJurors= activeJurors,
                           jurorsdrawn = drawnJurors,
                           retention= retention,
                           adoption= adoption,
                           most_active_court = mostActiveCourt,
                           cases_closed = ruledCases['ruled'],
                           cases_rulling = ruledCases['not_ruled'],
                           tokenSupply= tokenSupply,
                           pnkStaked= pnkStaked,
                           pnkStakedPercent= pnkStaked/tokenSupply,
                           courtTable= dfCourts[['courtLabel', 'n_Jurors', 'totalstaked', 'meanStake', 'maxStake']].rename(columns=newNames).sort_values('courtID',ascending=True).to_html(classes="table table-striped text-right",
                                                                                                                        border=0,
                                                                                                                        float_format='{:.0f}'.format,
                                                                                                                        index=False),
                           disputesgraph= disputesGraph(DisputesEvents()),
                           stakedPNKgraph= stakesJurorsGraph(dfStaked, dfJurors),
                           disputeCourtgraph=disputesbyCourtGraph(DisputesEvents())
                           )


@app.route('/support/')
def support():
    addVisit('support')
    return render_template('support.html',
                           last_update= KlerosLiquid().getLastUpdate(),)

@app.route('/odds/', methods=['GET','POST'])
def odds():
    addVisit('odds')
    pnkStaked = 100000
    if request.method == 'POST':
        # Form being submitted; grab data from form.
        try:
            pnkStaked = int(request.form['pnkStaked'])
        except:
            pnkStaked = 100000        
        

        
    return render_template('odds.html',
                           last_update= KlerosLiquid().getLastUpdate(),
                           courtNames= courtNames,
                           pnkStaked= pnkStaked,
                           courtChances= StakesKleros().getChancesInAllCourts(pnkStaked))

@app.route('/kleros-map/')
def maps():
    addVisit('map')
    return render_template('kleros-map.html',
                            last_update= KlerosLiquid().getLastUpdate(),
                            )

@app.route('/visitorMetrics/')
def visitorMetrics():
    filename = os.path.join(THIS_FOLDER,'data/visitors.json')
    with open(filename, 'r') as f:
        visitors = json.load(f)
    return render_template('visitors.html',
                           home=visitors["home"],
                           odds=visitors["odds"],
                           map=visitors["map"],
                           support=visitors["support"],
                           last_update= KlerosLiquid().getLastUpdate(),
                           )

@app.errorhandler(404) 
def not_found(e): 
    addVisit('unknown')
    return render_template("404.html") 


if __name__ == "__main__":
    app.run(debug=True)