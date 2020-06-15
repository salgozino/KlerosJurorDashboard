# -*- coding: utf-8 -*-

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from app import app, server
from layouts import layout_es, layout_en
import callbacks

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/es':
        return layout_es
    elif pathname == '/en':
        return layout_en
    else:
        return layout_es

if __name__ == '__main__':
    app.run_server(debug=True)