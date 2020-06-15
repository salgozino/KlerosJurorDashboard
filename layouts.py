import dash_table
import dash_core_components as dcc
import dash_html_components as html
from callbacks import kl, dfCourts, dfStaked, totalJurors, totalSupply, totalStaked, percentageStaked, update_disputes_graph
from Kleros import courtNames
from static.lib.translations import es_es, en_en


def get_marks(f, max_marks=15):
    """
    get the dates mark from the timestamps
    """
    dates = {}
    n = round(len(f.index)/max_marks)
    for z in f.index[::n]:
        # dates[f.index.get_loc(z)] = {}
        dates[f.index.get_loc(z)] = f"{z.year}-{z.month}-{z.day}"
    return dates


layout_es = html.Div(className="container",
                      children=[
                          html.Div(className='Title',
                              children=[
                                  html.H1(id='title', children=es_es['header']['title']),
                                  html.A('English Version', href='/en', className='two-cols'),
                                  html.A('Version en Español', href='/es', className='two-cols'),
                                  html.Hr(),
                                  dcc.Markdown(children=es_es['header']['description']),
                                  html.Div(id='updateTime', children=[es_es['header']['updateTime'],kl.getLastUpdate()]),
                                  html.Hr(),
                              ]),
                           html.Div(id='chanceByCourt', className='two-cols',
                               children=[
                                   html.H3(id='title', children=es_es['chanceByCourt']['title']),
                                   html.Div(children=[es_es['chanceByCourt']['court'],
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
                            html.Div(id='yourChances', className='two-col',
                                     children=[
                                        html.H3(id='title', children=es_es['yourChances']['title']),
                                        html.Div(
                                            children=[es_es['yourChances']['wallet'],
                                                      dcc.Input(id='wallet',
                                                                type='text')]),
                                        html.Div(id='chanceByAddress')
                                        ]),

                            html.H3(id='StakedInCourts', className='one-col',
                                children=es_es['StakedInCourts']['title']),
                            dash_table.DataTable(
                                id='stakedTable',
                                columns=[{"name": i, "id": i} for i in dfCourts.columns],
                                data=dfCourts.sort_values('courtID',ascending=True).to_dict('rows'),
                                style_cell={'textAlign': 'left'},
                                style_as_list_view=True,
                                sort_action="native"
                            ),
                            html.Div(id="totalJurors", children=[es_es['totalJurors'].format(totalJurors)]),
                            html.Div(id="Staked-TotalSupply", children=[es_es['Staked-TotalSupply'].format(totalSupply, totalStaked, percentageStaked)]),
                            html.H3(id='StakedEvolution', className='one-col',
                                children=es_es['StakedEvolution']['title']),
                            dcc.Dropdown(
                                       id='cortes-graph-dropdown',
                                       options=[{'label': courtNames[corte], 'value': corte} for corte in courtNames],
                                       value = [0, 2, 8],
                                       multi=True,
                                       ),
                            dcc.Graph(id='cortes-graph'),
                            html.Div([dcc.RangeSlider(
                                                id='cortes-graph-range',
                                                updatemode='mouseup',
                                                min=0,
                                                max=len(dfStaked.index) - 1,
                                                count=1,
                                                step=1,
                                                value=[0, len(dfStaked.index) - 1],
                                                marks=get_marks(dfStaked),
                                            )
                                        ]),
                            html.Hr(),
                            dcc.Graph(id='disputes-graph'),
                            dcc.Dropdown(
                                       id='disputes-graph-dropdown',
                                       options=[{'label': courtNames[corte], 'value': corte} for corte in courtNames],
                                       value = [0, 2, 8],
                                       multi=True,
                                       ),
                            dcc.Graph(id='disputes-court-graph'),
                            html.Footer(id='footer', children=[
                                            dcc.Markdown(es_es['footer']['description']),
                                             html.Button(es_es['footer']['button'], id='copy-to-clipboard', n_clicks=0),
                                             html.Div(id='hidden')
                                             ]
                                         )
                        ])

layout_en = html.Div(className="container",
                      children=[
                          html.Div(className='Title',
                              children=[
                                  html.H1(id='title', children=en_en['header']['title']),
                                  html.A('English Version', href='/en', className='two-cols'),
                                  html.A('Version en Español', href='/es', className='two-cols'),
                                  html.Hr(),
                                  dcc.Markdown(children=en_en['header']['description']),
                                  html.Div(id='updateTime', children=[en_en['header']['updateTime'],kl.getLastUpdate()]),
                                  html.Hr()
                              ]),
                           html.Div(id='chanceByCourt', className='two-cols',
                               children=[
                                   html.H3(id='title', children=en_en['chanceByCourt']['title']),
                                   html.Div(children=[en_en['chanceByCourt']['court'],
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
                            html.Div(id='yourChances', className='two-col',
                                     children=[
                                        html.H3(id='title', children=en_en['yourChances']['title']),
                                        html.Div(
                                            children=[en_en['yourChances']['wallet'],
                                                      dcc.Input(id='wallet',
                                                                type='text')]),
                                        html.Div(id='chanceByAddress')
                                        ]),

                            html.H3(id='StakedInCourts', className='one-col',
                                children=en_en['StakedInCourts']['title']),
                            dash_table.DataTable(
                                id='stakedTable',
                                columns=[{"name": i, "id": i} for i in dfCourts.columns],
                                data=dfCourts.sort_values('courtID',ascending=True).to_dict('rows'),
                                style_cell={'textAlign': 'left'},
                                style_as_list_view=True,
                                sort_action="native"
                            ),
                            html.Div(id="totalJurors", children=[en_en['totalJurors'].format(totalJurors)]),
                            html.Div(id="Staked-TotalSupply", children=[en_en['Staked-TotalSupply'].format(totalSupply, totalStaked, percentageStaked)]),
                            html.H3(id='StakedEvolution', className='one-col',
                                children=en_en['StakedEvolution']['title']),
                            dcc.Dropdown(
                                       id='cortes-graph-dropdown',
                                       options=[{'label': courtNames[corte], 'value': corte} for corte in courtNames],
                                       value = [0, 2, 8],
                                       multi=True,
                                       ),
                            dcc.Graph(id='cortes-graph'),
                            html.Div([dcc.RangeSlider(
                                                id='cortes-graph-range',
                                                updatemode='mouseup',
                                                min=0,
                                                max=len(dfStaked.index) - 1,
                                                count=1,
                                                step=1,
                                                value=[0, len(dfStaked.index) - 1],
                                                marks=get_marks(dfStaked),
                                            )
                                        ]),
                            html.Hr(),
                            dcc.Graph(id='disputes-graph'),
                            dcc.Dropdown(
                                       id='disputes-graph-dropdown',
                                       options=[{'label': courtNames[corte], 'value': corte} for corte in courtNames],
                                       value = [0, 2, 8],
                                       multi=True,
                                       ),
                            dcc.Graph(id='disputes-court-graph'),
                            html.Footer(id='footer', children=[
                                            dcc.Markdown(en_en['footer']['description']),
                                             html.Button(en_en['footer']['button'], id='copy-to-clipboard', n_clicks=0),
                                             html.Div(id='hidden')
                                             ]
                                         )
                        ])