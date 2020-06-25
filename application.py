# -*- coding: utf-8 -*-
from flask import Flask, render_template, request

from plotters import disputesGraph, stakesJurorsGraph, disputesbyCourtGraph
from bin.Kleros import KlerosLiquid, StakesKleros, DisputesEvents, courtNames

app = Flask(__name__)




@app.route('/')
def index():
    dfStaked = StakesKleros().historicStakesInCourts()
    dfJurors = StakesKleros().historicJurorsInCourts()
    dfCourts = StakesKleros().getstakedInCourts()
    allJurors = StakesKleros().getAllJurors()
    disputesEvents = DisputesEvents().historicDisputes()
    pnkStaked = sum(dfCourts.meanStake * dfCourts.n_Jurors)
    tokenSupply =  KlerosLiquid().tokenSupply
    activeJurors = len(allJurors[(allJurors.T != 0).any()])
    
    return render_template('main.html',
                           last_update= KlerosLiquid().getLastUpdate(),
                           disputes= disputesEvents.iloc[-1],
                           activeJurors= activeJurors,
                           retention= " Soon ",
                           adoption= " Soon ",
                           most_active_court = " Soon ",
                           cases_closed = " Soon ",
                           cases_rulling = " Soon ",
                           tokenSupply= tokenSupply,
                           pnkStaked= pnkStaked,
                           pnkStakedPercent= pnkStaked/tokenSupply,
                           courtTable= dfCourts.sort_values('courtID',ascending=True).reset_index().to_html(classes="table table-striped",
                                                                                                            border=0,
                                                                                                            float_format='{:.0f}'.format,
                                                                                                            index=False),
                           disputesgraph= disputesGraph(DisputesEvents()),
                           stakedPNKgraph= stakesJurorsGraph(dfStaked, dfJurors),
                           disputeCourtgraph=disputesbyCourtGraph(DisputesEvents())
                           )


@app.route('/support/')
@app.route('/support-donate/')
def support():
    return render_template('support.html',
                           last_update= KlerosLiquid().getLastUpdate(),)

@app.route('/odds/', methods=['GET','POST'])
def odds():
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
def map():
    return render_template('kleros-map.html',
                            last_update= KlerosLiquid().getLastUpdate(),
                            )

@app.errorhandler(404) 
def not_found(e): 
  return render_template("404.html") 

if __name__ == "__main__":
    app.run(debug=True)