# -*- coding: utf-8 -*-
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly
from plotly.express import colors as colormap

from .Kleros import courtNames

import json


def multiBar(df, columns = ['0','2','8','9']):
    fig = go.Figure()
    for column in df.columns.to_list():
        fig.add_trace(
            go.Bar(
                x = df.index,
                y = df[column],
                name = courtNames[int(column)],
                visible = True if column in columns else 'legendonly'
            )
        )

    fig.update_layout(barmode='stack',
                      legend= {'orientation':'h'}
                      )

    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def create_time_series(df, courts, colname=None):
    data = []
    colors = colormap.diverging.Picnic
    allCourts = df.columns.to_list()
    for i, court in enumerate(allCourts):
        if not colname:
            name = courtNames[int(court)]
        data.append(go.Bar(
                x=df.index,
                y=df[str(court)].astype(float),
                name = name,
                visible = True if str(court) in courts else 'legendonly',
                legendgroup = 'group'+str(court),
                marker_color=colors[i]))
    return data

def disputesGraph(dK, language="en"):
    if 'en' == language:
        ylabels = ['Disputes', 'Jurors Drawn']
        xlabel = 'Dates'
        title = 'Time Evolution of Disputes and Rounds in KLEROS'
    else:
        ylabels = ['Disputas', 'Jurados Seleccionados']
        xlabel = 'Fechas'
        title = 'Evolución de Disputas y Rondas en KLEROS'
        
    
    fig = make_subplots(rows=2, cols=1,
                        shared_xaxes=True, shared_yaxes=False,
                        vertical_spacing=0.001)
    df = dK.historicDisputes()
    fig.add_trace(go.Scatter(x=df.index,
                                y=df,
                                name=ylabels[0]),
                     row=1,
                     col=1)

    df = dK.historicJurorsDrawn()
    fig.add_trace(go.Scatter(x=df.index,
                            y=df['n_jurors_cum'],
                            name=ylabels[1]),
                     row=2,
                     col=1)
            
    fig['layout'].update(height= 500,
                         margin= {'l': 10, 'b': 50, 't': 30, 'r': 10},
                         title= title,
                         showlegend=False)
    fig.update_yaxes(title_text="N° "+ylabels[0], row=1, col=1)
    fig.update_yaxes(title_text="N° "+ylabels[1], row=2, col=1)
    fig.update_xaxes(title_text=xlabel, row=2, col=1)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def stakesJurorsGraph(dfStaked, dfJurors, courts=['0','2','8','9'], language='en'):
    if 'en' in language:
        title = 'Time evolution of Stakes in courts'
    else:
        title = 'Evolución de Depósitos por Corte'
    fig = make_subplots(rows=2, cols=1,
                        shared_xaxes=True, shared_yaxes=False,
                        vertical_spacing=0.05)
    traces = create_time_series(dfStaked, courts)
    for trace in traces:
        fig.append_trace(trace, row=1, col=1)
    
    traces = create_time_series(dfJurors, courts)
    for trace in traces:
        trace['showlegend']=False
        fig.append_trace(trace, row=2, col=1)
    fig['layout'].update(height= 500,
                         margin= {'l': 10, 'b': 50, 't': 30, 'r': 10},
                         title= title,
                         barmode= 'stack',
                         legend= {'orientation':'h'})
    if 'en' in language:
        fig.update_yaxes(title_text="PNK Staked", row=1, col=1)
        fig.update_yaxes(title_text="N° of Active Jurors", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)
    else:
        fig.update_yaxes(title_text="PNK Depositados", row=1, col=1)
        fig.update_yaxes(title_text="N° de Jurados Activos", row=2, col=1)
        fig.update_xaxes(title_text="Fecha", row=2, col=1)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def disputesbyCourtGraph(DisputesEvents, courts=['0','2','8','9'], language="en"):
    if 'en' == language:
        title = 'Time evolution: Disputes by Courts'
    else:
        title = 'Evolución tempomral: Disputas por Corte'
    fig = go.Figure()
    # colors = colormap.diverging.Picnic
    allCourts = ["{}".format(key) for key in courtNames.keys()]
    for i, court in enumerate(allCourts):
        df = DisputesEvents.historicDisputesbyCourt(int(court))
        fig.add_trace(go.Scatter(x= df.index,
                                 y= df['count'],
                                 showlegend= True,
                                 name= courtNames[int(court)],
                                 legendgroup= 'group'+str(court),
                                 # marker_color= colors[i],
                                 visible= True if str(court) in courts else 'legendonly')
                      )

    fig['layout'].update(barmode= 'stack',
                         title= title,
                         height= 300,
                         margin= {'l': 10, 'b': 50, 't': 30, 'r': 10},
                         legend= {'orientation':'h'})
    fig.update_yaxes(title_text='N°')
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
