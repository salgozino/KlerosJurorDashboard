# -*- coding: utf-8 -*-
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from plotly.subplots import make_subplots
from plotly.express import colors as colormap
from dash.dependencies import Input, Output
from datetime import datetime
from Kleros import *
from flask import Flask
import json

sk = StakesKleros()
sk.loadCSV()
dfStaked = sk.historicStakesInCourts()
dfJurors = sk.historicJurorsInCourts()
dfCourts = sk.getstakedInCourts()
cols_to_format = ['totalstaked', 'meanStack', 'maxStack']
for col in cols_to_format:
    dfCourts[col]=dfCourts[col].map("{:,.1f}".format)
totalJurors = len(sk.getAllJurors())

server = Flask(__name__)
app = dash.Dash(__name__, 
                server=server)
app.title='Juror Stakes Dashboard'
app.layout = html.Div(className="container",
                      children=[
                          html.Div(className='Title',
                              children=[
                                  html.H1(children='Kleros Stakes DashBoard!'),
                                  dcc.Markdown(children='''
                                    Esta app te permitirá conocer cuales son tus chances de ser elegido como jurado.
                                    Es una versión beta, ante cualquier duda, escribime en [telegram](https://t.me/kokialgo).
                                    
                                    El campo wallet revisa en nuestra base de datos los montos stakeados, nunca interactua con su wallet. Si quiere verificarlo, ingrese a la web sin metamask.
                                    
                                    Kleros es un sistema de disputas descentralizado, para más información visite [kleros.io](https://kleros.io)
                                    '''),
                                  html.Div(id='updateTime', children=[sk.getLastUpdate()]),
                                  html.Hr()
                              ]),
                           html.Div(className='two-cols',
                               children=[
                                   html.H3(children="Por Corte y Monto"),
                                   html.Div(children=['Corte: ',
                                   dcc.Dropdown(
                                       id='cortes',
                                       options=[{'label': courtNames[corte], 'value': corte} for corte in courtNames],
                                       value=8
                                       )]),
                                   'staked: ',
                                    dcc.Input(id='pnkstaked',
                                              value=100000,
                                              type='number',
                                              min=0, 
                                              step=1),
                                    html.Div(id='chanceInCourt')
                                    ]),
                            html.Div(className='two-col',
                                     children=[
                                        html.H3(children="Tus chances!"),
                                        html.Div(
                                            children=['Tu dirección de Wallet: ',
                                                      dcc.Input(id='wallet',
                                                                type='text')]),
                                        html.Div(id='chanceByAddress')
                                        ]),

                            html.H3(className='one-col',
                                children='Cantidad de PNK stakeados por corte'),
                            dash_table.DataTable(
                                id='stakedTable',
                                columns=[{"name": i, "id": i} for i in dfCourts.columns],
                                data=dfCourts.sort_values('courtID',ascending=True).to_dict('rows'),
                                style_cell={'textAlign': 'left'},
                                style_as_list_view=True,
                                sort_action="native"
                            ),
                            html.Div(id="totalJurors", children=[f'Hay un total de {totalJurors} jurados activos en las cortes.' ]),
                            html.H3(className='one-col',
                                children='Evolución de los depósitos en las cortes'),
                            dcc.Dropdown(
                                       id='cortes-graph',
                                       options=[{'label': courtNames[corte], 'value': corte} for corte in courtNames],
                                       # value=[i for i in range(len(courtNames))],
                                       value = [0, 2, 8],
                                       multi=True,
                                       ),
                            # dcc.Graph(id='stakedgraph-time', animate=True),
                            # dcc.Graph(id='jurorsgraph-time', animate=True),
                            dcc.Graph(id='courts-graphs'),
                        ])
             
@app.callback(
    Output(component_id='chanceInCourt', component_property='children'),
    [Input(component_id='cortes', component_property='value'),
     Input(component_id='pnkstaked', component_property='value')]
)
def getChanceInCourt(courtID, staked):
    chance = sk.getChanceByCourt(courtID, staked)
    return 'Con {:,} PNK depositados en la corte "{}", tus chances son 1 de cada {:.2f} casos, osea un {:.3%}'.format(staked, courtNames[courtID], 1/chance, chance)

@app.callback(
    Output(component_id='chanceByAddress', component_property='children'),
    [Input(component_id='wallet', component_property='value')]
)
def getChanceByWallet(wallet):
    text = ''
    if wallet:
        if web3Node.web3.isAddress(wallet):
            chances = sk.getChanceByAddress(wallet)
            for chance in chances:
                if chance['chance']!=0:
                    text += "En la corte {} tienes la chance de 1 cada {:.2f} casos, osea un {:.3%}.\n".format(chance['courtLabel'], 1/chance['chance'], chance['chance'])
        else:
            text = 'Por favor ingrese una dirección correcta'
    return text


def create_time_series(df, courts):
    data = []
    showlegend = True
    colors = colormap.sequential.Plasma
    for court in courts:
        data.append(go.Bar(
                x=df.index,
                y=df[court],
                name=courtNames[court],
                legendgroup = 'group'+str(court),
                marker_color=colors[court]))
    return data


@app.callback(
     Output(component_id='courts-graphs', component_property='figure'),
        [Input(component_id='cortes-graph', component_property='value')]
)
def update_graphs(courts):
    fig = make_subplots(rows=2, cols=1,
                        shared_xaxes=True, shared_yaxes=False,
                        vertical_spacing=0.001)
    traces = create_time_series(dfStaked, courts)
    for trace in traces:
        fig.append_trace(trace, row=1, col=1)
    traces = create_time_series(dfJurors, courts)
    for trace in traces:
        trace['showlegend']=False
        fig.append_trace(trace, row=2, col=1)
    fig['layout'].update(height= 500,
                         margin= {'l': 10, 'b': 50, 't': 30, 'r': 10},
                         title= 'Stakes along time',
                         barmode= 'stack',
                         legend= {'orientation':'h'})
    return fig


if __name__ == '__main__':
    app.run_server(debug=True, port=8080)
    # app.run_server()


