from dash.dependencies import Input, Output
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from plotly.express import colors as colormap
from Kleros import courtNames, StakesKleros, KlerosLiquid, DisputesEvents
from web3Node import web3Node
import pandas as pd

from app import app


# daybarwidth = 1000*60*60*24*0.8 # not used any more.
sk = StakesKleros()
kl = KlerosLiquid()
dK = DisputesEvents()
dfStaked = StakesKleros().historicStakesInCourts()
dfJurors = StakesKleros().historicJurorsInCourts()
dfCourts = StakesKleros().getstakedInCourts()
totalStaked = sum(dfCourts.meanStake * dfCourts.n_Jurors)
totalSupply = kl.tokenSupply
percentageStaked = totalStaked/totalSupply
allJurors = sk.getAllJurors()
totalJurors = len(allJurors[(allJurors.T != 0).any()])



def create_time_series(df, courts, colname=None):
    data = []
    colors = colormap.sequential.Viridis
    
    for i, court in enumerate(courts):
        if not colname:
            colname = courtNames[court]
        data.append(go.Bar(
                x=df.index,
                y=df[str(court)].astype(float),
                name = colname,
                legendgroup = 'group'+str(court),
                marker_color=colors[i]))
    return data

@app.callback(
    Output(component_id='disputes-graph', component_property='figure'),
    [Input('url', 'pathname')]
    )
def update_disputes_graph(pathname):
    if 'en' in pathname:
        ylabels = ['Disputes', 'Rounds', 'Jurors Drawn']
        xlabel = 'Dates'
        title = 'Disputes and Rounds in KLEROS time evolution'
    else:
        ylabels = ['Disputas', 'Rondas', 'Jurados Seleccionados']
        xlabel = 'Fechas'
        title = 'Evolución de Disputas y Rondas en KLEROS'
        
    
    fig = make_subplots(rows=3, cols=1,
                        shared_xaxes=True, shared_yaxes=False,
                        vertical_spacing=0.001)
    df = dK.historicDisputes()
    fig.add_trace(go.Scatter(x=df.index,
                                y=df,
                                name=ylabels[0]),
                     row=1,
                     col=1)

    df = dK.historicRounds()
    fig.add_trace(go.Scatter(x=df.index,
                            y=df['nRounds_cum'],
                            name=ylabels[1]),
                     row=2,
                     col=1)
    
    df = dK.historicJurorsDrawn()
    fig.add_trace(go.Scatter(x=df.index,
                            y=df['n_jurors_cum'],
                            name=ylabels[2]),
                     row=3,
                     col=1)
            
    fig['layout'].update(height= 500,
                         margin= {'l': 10, 'b': 50, 't': 50, 'r': 10},
                         title= title,
                         showlegend=False)
    fig.update_yaxes(title_text="N° "+ylabels[0], row=1, col=1)
    fig.update_yaxes(title_text="N° "+ylabels[1], row=2, col=1)
    fig.update_yaxes(title_text="N° "+ylabels[2], row=3, col=1)
    fig.update_xaxes(title_text=xlabel, row=3, col=1)
    return fig


@app.callback(
    Output(component_id='chanceInCourt', component_property='children'),
    [Input(component_id='cortes', component_property='value'),
     Input(component_id='pnkstaked', component_property='value'),
     Input('url', 'pathname')]
)
def getChanceInCourt(courtID, staked, pathname):
    chance = sk.getChanceByCourt(courtID, staked)
    # TODO! Where I can find the min number of Jurors by Court?
    nJurors = 3
    if 'en' in pathname:
        return 'With {:,} PNK staked in the Court "{}", your chances are 1 in {:.2f}. This means a {:.3%} chance to be drawn. I\'m assuming 3 jurors for the case, can be more in some courts.'.format(staked, courtNames[courtID], 1/(chance*nJurors), chance*nJurors)
    else:
        return 'Con {:,} PNK depositados en la corte "{}", tus chances de ser elegido es de 1 cada {:.2f}, es decir un {:.3%}. Estoy considerando 3 jurados para cada caso, pueden ser más en algunas cortes.'.format(staked, courtNames[courtID], 1/(chance*nJurors), nJurors*chance)
        

@app.callback(
    Output(component_id='chanceByAddress', component_property='children'),
    [Input(component_id='wallet', component_property='value'),
     Input('url', 'pathname')]
)
def getChanceByWallet(wallet, pathname):
    # TODO! Where I can find the min number of Jurors by Court?
    nJurors = 3
    if 'en' in pathname:
        text = 'Input a valid wallet address'
    else:
        text = 'Ingrese una dirección de billetera válida'
    if wallet:
        if web3Node.web3.isAddress(wallet):
            chances = sk.getChanceByAddress(wallet)
            if len(chances) == 0:
                if 'es' in pathname:
                    text = 'Ups!, parece que no hay información de esta wallet en la base de datos'
                else:
                    text = 'Ups!, There is no information of your wallet in the database'
            else:
                text = ''
            for chance in chances:
                if chance['chance']!=0:
                    if 'es' in pathname:
                        text += "En la corte {} tienes la chance de 1 cada {:.2f} casos, osea un {:.3%}. Estoy asumiendo 3 jurados por caso.\n".format(chance['courtLabel'], 1/(chance['chance']*nJurors), nJurors*chance['chance'])
                    else:
                        text += "In the Court {} you has 1 each {:.2f} cases chance, this means a {:.3%} to be drawn in a case. I\'m assuming 3 jurors by case.\n".format(chance['courtLabel'], 1/(chance['chance']*nJurors), nJurors*chance['chance'])
        else:
            if 'es' in pathname:
                text = 'Por favor ingrese una dirección correcta'
            else:
                text = 'Please input a valid wallet'
    return text



@app.callback(
     Output(component_id='cortes-graph', component_property='figure'),
     [Input(component_id='cortes-graph-dropdown', component_property='value'),
      Input(component_id='cortes-graph-range', component_property='value'),
      Input('url', 'pathname')]
)
def update_graphs(courts, dates_range, pathname):
    if 'en' in pathname:
        title = 'Stakes along time'
    else:
        title = 'Evolución de Depósitos'
            
    fig = make_subplots(rows=2, cols=1,
                        shared_xaxes=True, shared_yaxes=False,
                        vertical_spacing=0.001)
    traces = create_time_series(dfStaked.iloc[dates_range[0]:dates_range[1]], courts)
    for trace in traces:
        fig.append_trace(trace, row=1, col=1)
    
    traces = create_time_series(dfJurors.iloc[dates_range[0]:dates_range[1]], courts)
    for trace in traces:
        trace['showlegend']=False
        fig.append_trace(trace, row=2, col=1)
    fig['layout'].update(height= 500,
                         margin= {'l': 10, 'b': 50, 't': 30, 'r': 10},
                         title= title,
                         barmode= 'stack',
                         legend= {'orientation':'h'})
    if 'en' in pathname:
        fig.update_yaxes(title_text="PNK Staked", row=1, col=1)
        fig.update_yaxes(title_text="N° of Active Jurors", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)
    else:
        fig.update_yaxes(title_text="PNK Depositados", row=1, col=1)
        fig.update_yaxes(title_text="N° de Jurados Activos", row=2, col=1)
        fig.update_xaxes(title_text="Fecha", row=2, col=1)
    return fig

@app.callback(
     Output(component_id='disputes-court-graph', component_property='figure'),
     [Input(component_id='disputes-graph-dropdown', component_property='value'),
      Input('url', 'pathname')]
)
def update_dispute_courts_graphs(courts, pathname):
    fig = go.Figure()
    colors = colormap.diverging.Picnic
    for i, court in enumerate(courts):
        df = dK.historicDisputesbyCourt(court)
        fig.add_trace(go.Scatter(x=df.index,
                             y=df['count'],
                             showlegend=False,
                             legendgroup = 'group'+str(court),
                             marker_color=colors[i]
                             ))
        fig.add_trace(go.Scatter(x=df.index,
                                 y=df['count'],
                                 mode='markers',
                                 name=courtNames[court],
                                 legendgroup = 'group'+str(court),
                                 marker_color=colors[i]))
    if 'en' in pathname:
        title = 'Disputes in the Selected Courts'
        label = 'Disputes'
    else:
        title = 'Disputas en las cortes seleccionadas'
        label = 'Disputas'

    fig['layout'].update(barmode= 'stack',
                         title= title,
                         height= 300,
                         margin= {'l': 10, 'b': 50, 't': 30, 'r': 10},
                         legend= {'orientation':'h'})
    fig.update_yaxes(title_text=label)
    return fig
    
@app.callback(
    Output(component_id='hidden', component_property='children'),
    [Input(component_id='copy-to-clipboard', component_property='value')]
)
def copy_to_clipboard(value):
    pd.DataFrame({'text':"0x1d48668E22dE59C2177532d624AA981567401D2a"}, index=[0]).to_clipboard(index=False, header=False)
    return None